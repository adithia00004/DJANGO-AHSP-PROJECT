"""Project timeline safety helpers for the Jadwal Pekerjaan workflow.

The weekly table is canonical.  This module keeps timeline impact analysis and
the mutation path in one place so the project form and API cannot implement
different trimming rules.
"""

from collections import defaultdict
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction
from types import SimpleNamespace

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Max, Q

from detail_project.models import (
    DetailAHSPAudit,
    Pekerjaan,
    PekerjaanProgressWeekly,
    TahapPelaksanaan,
)
from detail_project.progress_utils import (
    _build_weekly_tahapan_instances,
    build_week_buckets,
    sync_weekly_to_tahapan,
)


# --- Resolusi ---------------------------------------------------------------
#
# Legacy: arti dipertahankan persis seperti sebelum mesin resolusi ada, supaya
# `tests_timeline_crud_hardening.py` tetap hijau tanpa dimodifikasi (doc 37 §6).
# `trim_planned` kini disupersede oleh `follow_date` dan tidak lagi ditawarkan
# di UI setelah Fase 2 — ia hanya me-nol-kan nilai dan meninggalkan barisnya
# (T-06), sedangkan resolusi mesin membereskan barisnya.
RESOLUTION_NONE = 'none'
RESOLUTION_TRIM_PLANNED = 'trim_planned'

# Mesin resolusi (doc 38 §3).
RESOLUTION_KEEP_ORDINAL = 'keep_ordinal'          # "Pertahankan urutan minggu"
RESOLUTION_ACCUMULATE_EDGE = 'accumulate_edge'    # "Padatkan ke minggu batas"
RESOLUTION_FOLLOW_DATE = 'follow_date'            # "Hapus yang di luar jadwal baru"
RESOLUTION_MOVE_PLANNED_TO_BOUNDARY = 'move_planned_to_boundary'

LEGACY_RESOLUTIONS = frozenset({RESOLUTION_NONE, RESOLUTION_TRIM_PLANNED})
ENGINE_RESOLUTIONS = frozenset({
    RESOLUTION_KEEP_ORDINAL,
    RESOLUTION_ACCUMULATE_EDGE,
    RESOLUTION_FOLLOW_DATE,
})
ALL_RESOLUTIONS = LEGACY_RESOLUTIONS | ENGINE_RESOLUTIONS | {
    RESOLUTION_MOVE_PLANNED_TO_BOUNDARY,
}

# Baris diparkir ke rentang week_number di luar jangkauan sebelum ditata ulang,
# supaya UNIQUE (pekerjaan, week_number) tidak pernah bentrok di tengah operasi.
_PARK_OFFSET = 100000

_PERCENT_MAX = Decimal('100.00')
_PERCENT_TOLERANCE = Decimal('0.01')


class TimelineChangeError(ValidationError):
    """Validation error carrying a serializable impact payload."""

    def __init__(self, message, impact=None):
        super().__init__(message)
        self.impact = impact or {}


def _actual_filter():
    return Q(actual_proportion__gt=0) | Q(actual_cost__isnull=False)


def _overlap_days(a_start, a_end, b_start, b_end):
    """Jumlah hari tumpang tindih antara dua rentang tanggal inklusif."""
    lo = max(a_start, b_start)
    hi = min(a_end, b_end)
    return (hi - lo).days + 1 if hi >= lo else 0


def _distribute(value, weights):
    """Bagi ``value`` menurut ``weights`` dengan jumlah 2 desimal terjaga persis.

    Metode sisa terbesar (largest remainder): kuantisasi ke sen, alokasikan
    proporsional dengan pembulatan ke bawah, lalu bagikan sisa sen ke bagian
    pecahan terbesar. Pembulatan per bagian akan menggeser total; cara ini tidak.
    """
    count = len(weights)
    if count == 0:
        return []
    if value is None:
        return [None] * count

    total_weight = sum(weights)
    if total_weight <= 0:
        return [Decimal('0.00')] * count

    cents = int((Decimal(value) * 100).to_integral_value(rounding=ROUND_HALF_UP))
    if cents == 0:
        return [Decimal('0.00')] * count

    exact = [Fraction(cents * weight, total_weight) for weight in weights]
    floors = [int(part) for part in exact]
    leftover = cents - sum(floors)
    if leftover:
        order = sorted(
            range(count),
            key=lambda i: (exact[i] - floors[i], -i),
            reverse=True,
        )
        for i in order[:leftover]:
            floors[i] += 1

    return [(Decimal(cent) / 100).quantize(Decimal('0.01')) for cent in floors]


def expected_week_count(project_start, project_end, week_end_day=6):
    """Return the number of canonical weekly buckets for a date range."""
    if not project_start or not project_end or project_end < project_start:
        return 0

    week_end_day = int(week_end_day if week_end_day is not None else 6) % 7
    first_week_end = project_start + timedelta(
        days=(week_end_day - project_start.weekday()) % 7
    )
    if project_end <= first_week_end:
        return 1
    return 1 + ((project_end - first_week_end).days + 6) // 7


def work_period_end(project):
    """Akhir rentang pencatatan: tambahan bila valid, selain itu akhir kontrak."""
    contract_end = getattr(project, 'tanggal_selesai', None)
    additional_end = getattr(project, 'tanggal_akhir_tambahan', None)
    if contract_end and additional_end and additional_end > contract_end:
        return additional_end
    return contract_end


def contract_boundary_week(project):
    """Nomor minggu yang memuat akhir kontrak, memakai aturan minggu kanonik."""
    return expected_week_count(
        getattr(project, 'tanggal_mulai', None),
        getattr(project, 'tanggal_selesai', None),
        getattr(project, 'week_end_day', 6),
    )


def is_extension_week(project, week_number):
    """True hanya untuk minggu sesudah minggu batas kontrak saat ada tambahan."""
    if not getattr(project, 'tanggal_akhir_tambahan', None):
        return False
    try:
        boundary = contract_boundary_week(project)
        return boundary > 0 and int(week_number) > boundary
    except (TypeError, ValueError):
        return False


def is_extension_day(project, target_date):
    """True untuk hari sesudah kontrak yang masih berada dalam tambahan aktif."""
    contract_end = getattr(project, 'tanggal_selesai', None)
    additional_end = getattr(project, 'tanggal_akhir_tambahan', None)
    return bool(
        contract_end and additional_end and target_date and
        contract_end < target_date <= additional_end
    )


def analyze_week_boundary_contract_impact(project, new_week_end_day):
    """List planned rows that become additional when the week boundary changes."""
    start = getattr(project, 'tanggal_mulai', None)
    contract_end = getattr(project, 'tanggal_selesai', None)
    additional_end = getattr(project, 'tanggal_akhir_tambahan', None)
    old_week_end = project.week_end_day if project.week_end_day is not None else 6
    new_week_end_day = int(new_week_end_day) % 7
    old_boundary = expected_week_count(start, contract_end, old_week_end)
    new_boundary = expected_week_count(start, contract_end, new_week_end_day)
    old_work_week_count = expected_week_count(
        start, work_period_end(project), old_week_end
    )
    new_work_week_count = expected_week_count(
        start, work_period_end(project), new_week_end_day
    )
    planned_rows = []
    if additional_end and new_boundary < old_boundary:
        planned_rows = list(
            PekerjaanProgressWeekly.objects.filter(
                project=project,
                planned_proportion__gt=0,
                week_number__gt=new_boundary,
                week_number__lte=min(old_boundary, new_work_week_count),
            )
            .select_related('pekerjaan')
            .order_by('week_number', 'pekerjaan_id')
        )
    out_of_range_rows = []
    if new_work_week_count < old_work_week_count:
        out_of_range_rows = list(
            PekerjaanProgressWeekly.objects.filter(
                project=project,
                week_number__gt=new_work_week_count,
                week_number__lte=old_work_week_count,
            )
            .exclude(
                planned_proportion=0,
                actual_proportion=0,
                actual_cost__isnull=True,
                notes='',
            )
            .select_related('pekerjaan')
            .order_by('week_number', 'pekerjaan_id')
        )
    _, old_contract_end, _ = _persisted_project_dates(project)
    return {
        'old_boundary_week': old_boundary,
        'new_boundary_week': new_boundary,
        'old_work_week_count': old_work_week_count,
        'new_work_week_count': new_work_week_count,
        'boundary_changed': old_boundary != new_boundary,
        'old_contract_end': old_contract_end.isoformat() if old_contract_end else None,
        'new_contract_end': contract_end.isoformat() if contract_end else None,
        'planned_extension_records': len(planned_rows),
        'planned_extension_rows': [
            {
                'pekerjaan_id': row.pekerjaan_id,
                'kode': row.pekerjaan.snapshot_kode or '',
                'uraian': row.pekerjaan.snapshot_uraian or '',
                'week_number': row.week_number,
                'planned_proportion': str(row.planned_proportion),
            }
            for row in planned_rows
        ],
        'progress_outside_new_work_period_records': len(out_of_range_rows),
        'progress_outside_new_work_period_rows': [
            {
                'pekerjaan_id': row.pekerjaan_id,
                'kode': row.pekerjaan.snapshot_kode or '',
                'uraian': row.pekerjaan.snapshot_uraian or '',
                'week_number': row.week_number,
                'planned_proportion': str(row.planned_proportion),
                'actual_proportion': str(row.actual_proportion),
                'has_actual_cost': row.actual_cost is not None,
            }
            for row in out_of_range_rows
        ],
    }


REPORT_WEEKS_PER_MONTH = 4


def project_report_period_counts(project):
    """Jumlah periode laporan proyek: ``(total_weeks, total_months)``.

    SATU sumber untuk pilihan periode di modal export, validasi export, dan
    kolom mingguan adapter — jangan hitung ulang di tempat lain (bug lama: view
    memaksa minimal 12 minggu/3 bulan, adapter memakai ceil(hari/7) yang
    mengabaikan batas minggu). "Bulan" laporan = 4 minggu.
    """
    start = getattr(project, 'tanggal_mulai', None)
    end = work_period_end(project)
    weeks = expected_week_count(start, end, getattr(project, 'week_end_day', 6))
    if not weeks:
        # Tanggal proyek belum lengkap: pakai struktur/data mingguan yang ada.
        weeks = TahapPelaksanaan.objects.filter(
            project=project, is_auto_generated=True, generation_mode='weekly',
        ).count()
    if not weeks:
        weeks = PekerjaanProgressWeekly.objects.filter(project=project).aggregate(
            max_week=Max('week_number'),
        )['max_week'] or 0
    weeks = max(1, weeks)
    months = -(-weeks // REPORT_WEEKS_PER_MONTH)
    return weeks, months


def invalidate_schedule_caches(project_id, pekerjaan_ids=None):
    """Invalidate all known Jadwal v2 read caches for a project."""
    if pekerjaan_ids is None:
        pekerjaan_ids = Pekerjaan.objects.filter(project_id=project_id).values_list(
            'id', flat=True
        )

    for pekerjaan_id in pekerjaan_ids:
        cache.delete(f"v2_weekly_progress:{project_id}:{pekerjaan_id}:v1")
        for mode in ('daily', 'weekly', 'monthly', 'custom'):
            cache.delete(
                f"v2_pekerjaan_assignments:{project_id}:{pekerjaan_id}:{mode}:v1"
            )

    cache.delete(f"v2_assignments:{project_id}:v1")


def _persisted_timeline(project):
    """Tanggal proyek versi DATABASE, bukan versi in-memory.

    `ModelForm.is_valid()` menempelkan `cleaned_data` ke `form.instance` lewat
    `_post_clean`, jadi pemanggil yang meneruskan instance form akan membawa
    tanggal BARU di atributnya. Membandingkan tanggal baru dengan tanggal baru
    membuat `start_changed` selalu False — dan gerbang realisasi ikut salah pilih
    cabang. Karena itu tanggal lama selalu dibaca ulang di sini, bukan dipercaya
    dari atribut instance.
    """
    start, contract_end, additional_end = _persisted_project_dates(project)
    effective_end = (
        additional_end
        if contract_end and additional_end and additional_end > contract_end
        else contract_end
    )
    return start, effective_end


def _persisted_project_dates(project):
    """Read persisted contract fields; ModelForm may have mutated the instance."""
    if not getattr(project, 'pk', None):
        return (
            project.tanggal_mulai,
            project.tanggal_selesai,
            getattr(project, 'tanggal_akhir_tambahan', None),
        )
    persisted = (
        type(project).objects
        .filter(pk=project.pk)
        .values('tanggal_mulai', 'tanggal_selesai', 'tanggal_akhir_tambahan')
        .first()
    )
    if not persisted:
        return (
            project.tanggal_mulai,
            project.tanggal_selesai,
            getattr(project, 'tanggal_akhir_tambahan', None),
        )
    return (
        persisted['tanggal_mulai'],
        persisted['tanggal_selesai'],
        persisted['tanggal_akhir_tambahan'],
    )


def _proposed_project_dates(project, new_start, new_end, target_field):
    """Resolve the contract fields and effective grid end for one timeline action."""
    allowed_targets = {'tanggal_selesai', 'tanggal_akhir_tambahan'}
    if target_field not in allowed_targets:
        raise TimelineChangeError(
            'Target perubahan timeline tidak valid.',
            {'safe': False, 'reason': 'invalid_target_field', 'target_field': target_field},
        )
    persisted_start, current_contract_end, current_additional_end = _persisted_project_dates(project)

    if target_field == 'tanggal_selesai':
        if not new_end:
            raise TimelineChangeError(
                'Akhir waktu kerja harus diisi.',
                {'safe': False, 'reason': 'incomplete_timeline'},
            )
        contract_end = new_end
        additional_end = (
            current_additional_end
            if current_additional_end and current_additional_end > contract_end
            else None
        )
    else:
        if new_start != persisted_start:
            raise TimelineChangeError(
                'Perubahan tambahan waktu kerja tidak boleh mengubah tanggal mulai proyek.',
                {
                    'safe': False,
                    'reason': 'additional_timeline_start_changed',
                    'persisted_start': persisted_start.isoformat() if persisted_start else None,
                    'requested_start': new_start.isoformat() if new_start else None,
                    'target_field': target_field,
                },
            )
        contract_end = current_contract_end
        additional_end = new_end
        if additional_end and (not contract_end or additional_end <= contract_end):
            raise TimelineChangeError(
                'Akhir tambahan harus setelah akhir waktu kerja.',
                {
                    'safe': False,
                    'reason': 'additional_end_not_after_contract',
                    'contract_end': contract_end.isoformat() if contract_end else None,
                },
            )

    if not contract_end or contract_end < new_start:
        raise TimelineChangeError(
            'Akhir waktu kerja harus sama dengan atau setelah tanggal mulai.',
            {'safe': False, 'reason': 'invalid_order'},
        )
    work_end = additional_end or contract_end
    return contract_end, additional_end, work_end


def analyze_project_timeline_change(project, new_start, new_end, *, target_field='tanggal_selesai'):
    """Analyze a proposed timeline without mutating project or progress data."""
    if not new_start:
        raise TimelineChangeError(
            'Tanggal mulai wajib diisi.',
            {'safe': False, 'reason': 'incomplete_timeline'},
        )
    contract_end, additional_end, new_work_end = _proposed_project_dates(
        project, new_start, new_end, target_field
    )
    old_start, old_end = _persisted_timeline(project)
    _, old_contract_end, old_additional_end = _persisted_project_dates(project)
    old_week_count = expected_week_count(
        old_start, old_end, getattr(project, 'week_end_day', 6)
    )
    records = PekerjaanProgressWeekly.objects.filter(project=project)
    start_changed = (old_start or None) != new_start
    end_changed = (old_end or None) != new_work_end
    new_week_count = expected_week_count(
        new_start, new_work_end, getattr(project, 'week_end_day', 6)
    )
    planned_extension_rows = []
    contract_boundary = expected_week_count(
        new_start, contract_end, getattr(project, 'week_end_day', 6)
    )
    contract_boundary_changed = (
        target_field == 'tanggal_selesai'
        and (start_changed or (old_contract_end or None) != contract_end)
    )
    if contract_boundary_changed and additional_end and contract_boundary < new_week_count:
        planned_extension_rows = list(
            records.filter(
                planned_proportion__gt=0,
                week_number__gt=contract_boundary,
                week_number__lte=new_week_count,
            )
            .select_related('pekerjaan')
            .order_by('week_number', 'pekerjaan_id')
        )
    change_type = None
    if target_field == 'tanggal_akhir_tambahan':
        if not new_end:
            change_type = 'hapus' if old_additional_end else 'tidak_berubah'
        elif new_end == old_additional_end:
            change_type = 'tidak_berubah'
        elif new_work_end < old_end:
            change_type = 'pengurangan'
        else:
            old_week_count = expected_week_count(
                old_start, old_end, getattr(project, 'week_end_day', 6)
            )
            change_type = 'tipe_1' if new_week_count == old_week_count else 'tipe_2'
    if start_changed:
        affected = records.filter(
            Q(planned_proportion__gt=0)
            | Q(actual_proportion__gt=0)
            | Q(actual_cost__isnull=False)
        )
    elif end_changed:
        # Weekly progress is indivisible. Shortening a partial final bucket
        # keeps that whole week/value; only complete ordinal buckets past the
        # new end are at risk.
        affected = records.filter(week_number__gt=new_week_count)
    else:
        # A user can open the guided repair dialog precisely because stored
        # weekly dates have drifted beyond the current project window. Even
        # when the requested dates match the project, inspect those stale rows
        # so preview/commit can offer the normal repair choices.
        affected = records.filter(
            Q(week_start_date__lt=new_start)
            | Q(week_end_date__gt=new_work_end)
        )
    planned = affected.filter(planned_proportion__gt=0)
    actual = affected.filter(
        Q(actual_proportion__gt=0) | Q(actual_cost__isnull=False)
    )

    values = list(
        affected.filter(Q(planned_proportion__gt=0) | Q(actual_proportion__gt=0) | Q(actual_cost__isnull=False))
        .values('week_number', 'week_start_date', 'week_end_date')
        .order_by('week_number')
    )
    week_numbers = sorted({int(row['week_number']) for row in values})
    start_dates = [row['week_start_date'] for row in values if row['week_start_date']]
    end_dates = [row['week_end_date'] for row in values if row['week_end_date']]

    # A start-date change changes the meaning of every relative week number.
    # Do not silently shift or reset existing values until a dedicated shift
    # policy is agreed. Empty/zero rows are safe to rebuild.
    nonzero_count = records.filter(
        Q(planned_proportion__gt=0)
        | Q(actual_proportion__gt=0)
        | Q(actual_cost__isnull=False)
    ).count()
    start_requires_policy = start_changed and nonzero_count > 0

    # --- K-1: gerbang realisasi (tracker doc 39 §0 K-1) ----------------------
    # Tolak hanya bila operasi memang akan MEMINDAHKAN atau MENGHAPUS realisasi,
    # bukan sekadar karena realisasi ada:
    #   * tanggal mulai bergeser -> seluruh batas minggu dihitung ulang, jadi
    #     realisasi di mana pun ikut berpindah tanggal;
    #   * tanggal selesai saja   -> hanya baris di luar jendela baru terancam;
    #   * repair tanpa edit tanggal -> actual stale di minggu yang tidak muat
    #     tetap diblokir, sementara actual pada bucket yang masih muat dijaga;
    #   * ujung diperpanjang     -> tidak ada baris yang berubah, selalu aman.
    if start_changed:
        blocking_qs = records.filter(_actual_filter())
        blocking_reason = 'actual_present_start_shift' if blocking_qs.exists() else None
    else:
        # Protect actual values both when a proposed end shortens the range and
        # when the guided repair is asked to fix an already-stale unchanged
        # range. In both cases only whole weeks beyond the new window are lost.
        blocking_qs = actual.filter(week_number__gt=new_week_count)
        blocking_reason = 'actual_out_of_window' if blocking_qs.exists() else None
    if (
        not blocking_reason
        and planned_extension_rows
        and (start_requires_policy or planned.count() > 0)
    ):
        blocking_reason = 'mixed_planned_extension_and_range_change'
    if target_field == 'tanggal_akhir_tambahan' and end_changed and not blocking_reason:
        notes_outside = records.filter(week_number__gt=new_week_count, notes__gt='')
        if notes_outside.exists():
            blocking_qs = notes_outside
            blocking_reason = 'notes_out_of_window'

    blocking_week_numbers = (
        sorted({
            int(number)
            for number in blocking_qs.values_list('week_number', flat=True)
        })
        if blocking_reason else []
    )

    # Opsi yang sah untuk bentuk perubahan ini (doc 37 §4.6, dipersempit ke tiga
    # resolusi rilis pertama). UI tidak boleh menghitung ini sendiri.
    if blocking_reason:
        allowed_resolutions = []
        recommended_resolution = None
    elif planned_extension_rows:
        allowed_resolutions = [RESOLUTION_MOVE_PLANNED_TO_BOUNDARY]
        recommended_resolution = RESOLUTION_MOVE_PLANNED_TO_BOUNDARY
    elif start_requires_policy:
        allowed_resolutions = [
            RESOLUTION_KEEP_ORDINAL,
            RESOLUTION_ACCUMULATE_EDGE,
            RESOLUTION_FOLLOW_DATE,
        ]
        recommended_resolution = RESOLUTION_KEEP_ORDINAL
    elif planned.exists():
        if (
            target_field == 'tanggal_akhir_tambahan'
            and additional_end
            and contract_boundary < new_week_count
        ):
            # The final work-period week is still an extension week. The
            # accumulate-edge strategy would move planned into a prohibited
            # week and be rejected by _guard_target, so offer only the safe
            # option while that additional period remains active.
            allowed_resolutions = [RESOLUTION_FOLLOW_DATE]
            recommended_resolution = RESOLUTION_FOLLOW_DATE
        else:
            allowed_resolutions = [
                RESOLUTION_ACCUMULATE_EDGE,
                RESOLUTION_FOLLOW_DATE,
            ]
            recommended_resolution = RESOLUTION_ACCUMULATE_EDGE
    else:
        allowed_resolutions = [RESOLUTION_NONE]
        recommended_resolution = RESOLUTION_NONE

    return {
        'safe': (
            not start_requires_policy
            and actual.count() == 0
            and planned.count() == 0
            and not planned_extension_rows
        ),
        'start_changed': start_changed,
        'end_changed': end_changed,
        'start_requires_policy': start_requires_policy,
        'blocking_reason': blocking_reason,
        'blocking_week_numbers': blocking_week_numbers,
        'allowed_resolutions': allowed_resolutions,
        'recommended_resolution': recommended_resolution,
        'planned_records': planned.count(),
        'planned_extension_records': len(planned_extension_rows),
        'planned_extension_rows': [
            {
                'pekerjaan_id': row.pekerjaan_id,
                'kode': row.pekerjaan.snapshot_kode or '',
                'uraian': row.pekerjaan.snapshot_uraian or '',
                'week_number': row.week_number,
                'planned_proportion': str(row.planned_proportion),
            }
            for row in planned_extension_rows
        ],
        'contract_boundary_week': contract_boundary,
        'actual_records': actual.count(),
        'affected_records': len(values),
        'affected_week_numbers': week_numbers,
        'affected_week_start': min(start_dates).isoformat() if start_dates else None,
        'affected_week_end': max(end_dates).isoformat() if end_dates else None,
        'old_start': old_start.isoformat() if old_start else None,
        'old_end': old_end.isoformat() if old_end else None,
        'old_week_count': old_week_count,
        'new_start': new_start.isoformat(),
        'new_end': new_work_end.isoformat(),
        'target_field': target_field,
        'jenis': change_type,
        'target_value': new_end.isoformat() if new_end else None,
        'new_contract_end': contract_end.isoformat(),
        'new_additional_end': additional_end.isoformat() if additional_end else None,
        'new_week_count': new_week_count,
    }


def _snapshot_rows(rows):
    """Snapshot penuh untuk audit — cukup untuk memulihkan keadaan sebelumnya.

    `trim_planned` hanya menyimpan nilai planned lama; resolusi mesin dapat
    memindahkan, menggabung, atau menghapus baris, jadi audit harus memuat
    seluruh field yang dapat berubah (doc 37 §4.8).
    """
    return [
        {
            'pekerjaan_id': row.pekerjaan_id,
            'week_number': row.week_number,
            'week_start_date': row.week_start_date.isoformat() if row.week_start_date else None,
            'week_end_date': row.week_end_date.isoformat() if row.week_end_date else None,
            'planned_proportion': str(row.planned_proportion),
            'actual_proportion': str(row.actual_proportion),
            'actual_cost': str(row.actual_cost) if row.actual_cost is not None else None,
            'notes': row.notes or '',
        }
        for row in rows
    ]


def plan_timeline_resolution(rows, buckets, new_start, resolution):
    """Hitung keadaan canonical tujuan. Murni — tidak menyentuh database.

    Mengembalikan ``(target, counts)`` di mana ``target`` memetakan
    ``(pekerjaan_id, week_number)`` ke nilai gabungan, dan ``counts`` merangkum
    nasib setiap baris sumber.
    """
    bucket_dates = {number: (start, end) for number, start, end in buckets}
    first_number = buckets[0][0]
    last_number = buckets[-1][0]

    target = {}
    counts = defaultdict(int)

    def _add(pekerjaan_id, week_number, planned, actual, actual_cost):
        cell = target.setdefault((pekerjaan_id, week_number), {
            'planned': Decimal('0.00'),
            'actual': Decimal('0.00'),
            'actual_cost': None,
        })
        cell['planned'] += planned
        cell['actual'] += actual
        if actual_cost is not None:
            cell['actual_cost'] = (cell['actual_cost'] or Decimal('0.00')) + actual_cost

    for row in rows:
        planned = row.planned_proportion or Decimal('0.00')
        actual = row.actual_proportion or Decimal('0.00')
        actual_cost = row.actual_cost

        if resolution == RESOLUTION_KEEP_ORDINAL:
            # Minggu ke-N tetap minggu ke-N; hanya tanggalnya dihitung ulang.
            # Luapan saat durasi memendek DIHAPUS (keputusan owner G0-2).
            if row.week_number in bucket_dates:
                _add(row.pekerjaan_id, row.week_number, planned, actual, actual_cost)
                counts['kept'] += 1
            else:
                counts['dropped'] += 1
            continue

        # Keluarga BY_DATE: nilai menempel pada tanggal kalendernya.
        overlaps = [
            (number, days)
            for number, bucket_start, bucket_end in buckets
            if (days := _overlap_days(
                row.week_start_date, row.week_end_date, bucket_start, bucket_end
            ))
        ]

        if overlaps:
            weights = [days for _, days in overlaps]
            if resolution == RESOLUTION_FOLLOW_DATE:
                # Porsi baris yang jatuh di luar jendela baru memang dibuang;
                # slot tambahan ini menampungnya lalu tidak dipakai.
                row_days = (row.week_end_date - row.week_start_date).days + 1
                outside_days = row_days - sum(weights)
                if outside_days > 0:
                    weights = weights + [outside_days]

            planned_parts = _distribute(planned, weights)
            actual_parts = _distribute(actual, weights)
            cost_parts = _distribute(actual_cost, weights)

            for index, (number, _) in enumerate(overlaps):
                _add(
                    row.pekerjaan_id,
                    number,
                    planned_parts[index],
                    actual_parts[index],
                    cost_parts[index],
                )
            counts['split' if len(overlaps) > 1 else 'kept'] += 1
        elif resolution == RESOLUTION_ACCUMULATE_EDGE:
            # Seluruhnya di luar jendela: tumpuk ke minggu batas terdekat.
            number = first_number if row.week_end_date < new_start else last_number
            _add(row.pekerjaan_id, number, planned, actual, actual_cost)
            counts['accumulated'] += 1
        else:
            counts['dropped'] += 1

    return target, dict(counts)


RESOLUTION_LABELS = {
    RESOLUTION_KEEP_ORDINAL: 'Pertahankan urutan minggu',
    RESOLUTION_ACCUMULATE_EDGE: 'Padatkan ke minggu batas',
    RESOLUTION_FOLLOW_DATE: 'Hapus yang di luar jadwal baru',
    RESOLUTION_MOVE_PLANNED_TO_BOUNDARY: 'Pindahkan rencana ke minggu batas kontrak',
    RESOLUTION_NONE: 'Simpan langsung',
}

RESOLUTION_HELP = {
    RESOLUTION_KEEP_ORDINAL:
        'Minggu ke-1 tetap minggu ke-1; hanya tanggalnya yang berubah. '
        'Bila jadwal baru lebih pendek, minggu yang tidak lagi muat dihapus.',
    RESOLUTION_ACCUMULATE_EDGE:
        'Progress yang jatuh di luar jadwal baru ditumpuk ke minggu pertama '
        'atau minggu terakhir. Total tidak berubah, hanya sebarannya.',
    RESOLUTION_FOLLOW_DATE:
        'Progress mengikuti tanggal kalendernya. Yang jatuh di luar jadwal baru '
        'dibuang; yang di dalam tidak tersentuh.',
    RESOLUTION_MOVE_PLANNED_TO_BOUNDARY:
        'Pindahkan planned dari minggu yang kini melewati kontrak ke minggu batas. '
        'Realisasi dan biaya aktual tetap di minggu semula.',
    RESOLUTION_NONE:
        'Tidak ada rencana progress yang terdampak; jadwal cukup dibangun ulang.',
}


def build_resolution_preview(
    project, new_start, new_end, resolution, *, target_field='tanggal_selesai'
):
    """Proyeksikan hasil sebuah resolusi TANPA menyentuh database.

    Dialog dampak memakai fungsi ini supaya angka yang dilihat user berasal dari
    planner yang sama dengan yang nanti melakukan commit — bukan perkiraan kedua
    yang bisa menyimpang.
    """
    impact = analyze_project_timeline_change(
        project, new_start, new_end, target_field=target_field
    )
    week_end_day = project.week_end_day if project.week_end_day is not None else 6
    old_start, old_end = _persisted_timeline(project)
    new_buckets = build_week_buckets(
        new_start, date.fromisoformat(impact['new_end']), week_end_day
    )
    old_buckets = build_week_buckets(old_start, old_end, week_end_day)

    rows = list(
        PekerjaanProgressWeekly.objects
        .filter(project=project)
        .order_by('pekerjaan_id', 'week_number')
    )

    before_by_week = defaultdict(lambda: Decimal('0.00'))
    for row in rows:
        before_by_week[row.week_number] += row.planned_proportion or Decimal('0.00')

    counts = {}
    moved_planned = []
    after_by_week = defaultdict(lambda: Decimal('0.00'))
    if resolution in ENGINE_RESOLUTIONS and new_buckets:
        target, counts = plan_timeline_resolution(
            rows, new_buckets, new_start, resolution
        )
        for (_, week_number), cell in target.items():
            after_by_week[week_number] += cell['planned']
    elif resolution == RESOLUTION_MOVE_PLANNED_TO_BOUNDARY:
        boundary_week = impact['contract_boundary_week']
        for week_number, value in before_by_week.items():
            after_by_week[week_number] = value
        for row in impact['planned_extension_rows']:
            planned = Decimal(row['planned_proportion'])
            after_by_week[row['week_number']] -= planned
            after_by_week[boundary_week] += planned
            moved_planned.append({
                **row,
                'boundary_week': boundary_week,
            })
        counts = {'planned_rows_moved': len(moved_planned)}
    elif resolution == RESOLUTION_NONE:
        # Tidak ada penataan: nilai bertahan pada nomor minggunya.
        for week_number, value in before_by_week.items():
            after_by_week[week_number] = value

    old_dates = {number: (start, end) for number, start, end in old_buckets}
    new_dates = {number: (start, end) for number, start, end in new_buckets}

    weeks = []
    for number in range(1, max(len(old_buckets), len(new_buckets)) + 1):
        old_range = old_dates.get(number)
        new_range = new_dates.get(number)
        weeks.append({
            'week_number': number,
            'old_start': old_range[0] if old_range else None,
            'old_end': old_range[1] if old_range else None,
            'new_start': new_range[0] if new_range else None,
            'new_end': new_range[1] if new_range else None,
            'exists_after': new_range is not None,
            'planned_before': before_by_week[number],
            'planned_after': after_by_week[number],
            'changed': before_by_week[number] != after_by_week[number],
        })

    total_before = sum(before_by_week.values(), Decimal('0.00'))
    total_after = sum(after_by_week.values(), Decimal('0.00'))

    return {
        'resolution': resolution,
        'label': RESOLUTION_LABELS.get(resolution, resolution),
        'help': RESOLUTION_HELP.get(resolution, ''),
        'weeks': weeks,
        'old_week_count': len(old_buckets),
        'new_week_count': len(new_buckets),
        'total_planned_before': total_before,
        'total_planned_after': total_after,
        # K-2: `keep_ordinal` tidak lagi selalu lossless, jadi kehilangan harus
        # ditampilkan eksplisit alih-alih disimpulkan user dari dua angka total.
        'planned_lost': total_before - total_after,
        'counts': counts,
        'moved_planned': moved_planned,
    }


def _guard_target(target, impact, project, source_rows):
    """Post-condition R-6: batas kuantitas diperiksa, bukan diasumsikan.

    Batas "total planned per pekerjaan <= 100%" hanya ditegakkan di
    `api_assign_pekerjaan_weekly`; ia bukan constraint database, dan
    `MaxValueValidator` hanya berjalan lewat `full_clean()` yang tidak dipakai
    oleh `update()`/`bulk_update()`/`bulk_create()`. Baris yang melanggar bisa
    sudah ada sejak copy service atau migrasi canonical, jadi hasil resolusi
    diverifikasi di sini alih-alih dipercaya.
    """
    totals = defaultdict(lambda: {'planned': Decimal('0.00'), 'actual': Decimal('0.00')})
    source_planned = defaultdict(lambda: Decimal('0.00'))
    for row in source_rows:
        source_planned[(row.pekerjaan_id, row.week_number)] += (
            row.planned_proportion or Decimal('0.00')
        )

    # Resolution engines also write canonical rows in bulk. Do not let a
    # user-selected placement introduce planned progress into a new extension
    # week; unchanged historical planned values remain available for review.
    from detail_project.progress_write_service import (
        PlannedProgressOutsideWorkPeriod,
        validate_progress_write,
    )
    policy_project = SimpleNamespace(
        tanggal_mulai=date.fromisoformat(impact['new_start']),
        tanggal_selesai=date.fromisoformat(impact['new_contract_end']),
        tanggal_akhir_tambahan=(
            date.fromisoformat(impact['new_additional_end'])
            if impact['new_additional_end'] else None
        ),
        week_end_day=project.week_end_day,
    )

    for (pekerjaan_id, week_number), cell in target.items():
        if cell['planned'] > source_planned[(pekerjaan_id, week_number)]:
            try:
                validate_progress_write(
                    policy_project,
                    kind='user_move',
                    week_number=week_number,
                    planned=cell['planned'],
                )
            except PlannedProgressOutsideWorkPeriod as exc:
                raise TimelineChangeError(
                    str(exc),
                    {
                        **impact,
                        'blocking_reason': 'planned_in_extension',
                        'blocking_week_numbers': [week_number],
                    },
                ) from exc
        for field in ('planned', 'actual'):
            if cell[field] > _PERCENT_MAX + _PERCENT_TOLERANCE:
                raise TimelineChangeError(
                    f'Hasil penataan melebihi 100% pada satu minggu '
                    f'(pekerjaan {pekerjaan_id}, minggu {week_number}). '
                    f'Perubahan dibatalkan.',
                    {**impact, 'blocking_reason': 'quantity_limit_exceeded'},
                )
            totals[pekerjaan_id][field] += cell[field]

    for pekerjaan_id, total in totals.items():
        for field in ('planned', 'actual'):
            if total[field] > _PERCENT_MAX + _PERCENT_TOLERANCE:
                raise TimelineChangeError(
                    f'Total progress pekerjaan {pekerjaan_id} menjadi '
                    f'{total[field]}% setelah penataan (maksimum 100%). '
                    f'Perubahan dibatalkan.',
                    {**impact, 'blocking_reason': 'quantity_limit_exceeded'},
                )


def _write_target(project, rows, target, buckets):
    """Tata ulang baris canonical ke keadaan tujuan.

    Pola dua fase untuk `unique_together = (pekerjaan, week_number)`: seluruh
    baris diparkir ke rentang di luar jangkauan lebih dulu dalam satu statement,
    sehingga tidak ada pasangan yang bentrok saat nomor minggu ditata ulang.
    Baris yang ada dipakai ulang agar `created_at` tidak hilang.
    """
    bucket_dates = {number: (start, end) for number, start, end in buckets}

    PekerjaanProgressWeekly.objects.filter(project=project).update(
        week_number=F('week_number') + _PARK_OFFSET
    )

    pool = defaultdict(list)
    for row in rows:
        pool[row.pekerjaan_id].append(row)
    cursor = defaultdict(int)

    to_update = []
    to_create = []
    reused_ids = set()

    for (pekerjaan_id, week_number), cell in sorted(target.items()):
        week_start, week_end = bucket_dates[week_number]
        index = cursor[pekerjaan_id]
        row = None
        if index < len(pool[pekerjaan_id]):
            row = pool[pekerjaan_id][index]
            cursor[pekerjaan_id] = index + 1

        if row is not None:
            row.week_number = week_number
            row.week_start_date = week_start
            row.week_end_date = week_end
            row.planned_proportion = cell['planned']
            row.actual_proportion = cell['actual']
            row.actual_cost = cell['actual_cost']
            to_update.append(row)
            reused_ids.add(row.id)
        else:
            to_create.append(PekerjaanProgressWeekly(
                project=project,
                pekerjaan_id=pekerjaan_id,
                week_number=week_number,
                week_start_date=week_start,
                week_end_date=week_end,
                planned_proportion=cell['planned'],
                actual_proportion=cell['actual'],
                actual_cost=cell['actual_cost'],
            ))

    leftover_ids = [row.id for row in rows if row.id not in reused_ids]
    if leftover_ids:
        PekerjaanProgressWeekly.objects.filter(id__in=leftover_ids).delete()

    if to_update:
        PekerjaanProgressWeekly.objects.bulk_update(
            to_update,
            [
                'week_number',
                'week_start_date',
                'week_end_date',
                'planned_proportion',
                'actual_proportion',
                'actual_cost',
            ],
            batch_size=500,
        )
    if to_create:
        PekerjaanProgressWeekly.objects.bulk_create(to_create, batch_size=500)


def _regenerate_weekly_structure(project):
    """Rebuild auto-generated weekly stages and keep the projection aligned."""
    TahapPelaksanaan.objects.filter(
        project=project,
        is_auto_generated=True,
        generation_mode='weekly',
    ).delete()
    stages = _build_weekly_tahapan_instances(
        project,
        week_start_day=project.week_start_day or 0,
        week_end_day=project.week_end_day if project.week_end_day is not None else 6,
    )
    if stages:
        TahapPelaksanaan.objects.bulk_create(stages)
    sync_weekly_to_tahapan(
        project.id,
        mode='weekly',
        week_end_day=project.week_end_day if project.week_end_day is not None else 6,
    )


def _align_weekly_row_dates(project, new_start, new_end, week_end_day):
    """Align stored dates to canonical buckets without changing progress values."""
    buckets = {
        number: (start, end)
        for number, start, end in build_week_buckets(new_start, new_end, week_end_day)
    }
    rows = list(
        PekerjaanProgressWeekly.objects
        .filter(project=project, week_number__in=buckets)
        .order_by('pekerjaan_id', 'week_number')
    )
    changed = []
    for row in rows:
        start, end = buckets[row.week_number]
        if (row.week_start_date, row.week_end_date) == (start, end):
            continue
        changed.append((row, start, end))
    snapshot = _snapshot_rows([row for row, _, _ in changed]) if changed else []
    for row, start, end in changed:
        row.week_start_date = start
        row.week_end_date = end
    if changed:
        PekerjaanProgressWeekly.objects.bulk_update(
            [row for row, _, _ in changed],
            ['week_start_date', 'week_end_date'],
            batch_size=500,
        )
    return len(changed), snapshot


def _move_planned_to_contract_boundary(
    project, contract_week, work_week_count, *, week_end_day=None,
    source_max_week=None,
):
    """Move only selected planned values from new extension weeks to boundary."""
    source_query = PekerjaanProgressWeekly.objects.filter(
        project=project,
        planned_proportion__gt=0,
        week_number__gt=contract_week,
        week_number__lte=work_week_count,
    )
    if source_max_week is not None:
        source_query = source_query.filter(week_number__lte=source_max_week)
    source_rows = list(source_query.order_by('pekerjaan_id', 'week_number'))
    if not source_rows:
        return [], 0

    planned_by_job = defaultdict(lambda: Decimal('0.00'))
    for row in source_rows:
        planned_by_job[row.pekerjaan_id] += row.planned_proportion or Decimal('0.00')
    job_ids = list(planned_by_job)
    boundary_rows = {
        row.pekerjaan_id: row
        for row in PekerjaanProgressWeekly.objects.filter(
            project=project,
            pekerjaan_id__in=job_ids,
            week_number=contract_week,
        )
    }
    for pekerjaan_id, planned in planned_by_job.items():
        boundary_row = boundary_rows.get(pekerjaan_id)
        current = boundary_row.planned_proportion if boundary_row else Decimal('0.00')
        if current + planned > _PERCENT_MAX + _PERCENT_TOLERANCE:
            raise TimelineChangeError(
                f'Rencana pekerjaan {pekerjaan_id} di minggu batas akan melebihi 100%.',
                {
                    'safe': False,
                    'reason': 'planned_boundary_limit_exceeded',
                    'pekerjaan_id': pekerjaan_id,
                    'boundary_week': contract_week,
                },
            )

    if week_end_day is None:
        week_end_day = project.week_end_day if project.week_end_day is not None else 6
    boundary_dates = {
        number: (start, end)
        for number, start, end in build_week_buckets(
            project.tanggal_mulai, work_period_end(project), week_end_day
        )
    }.get(contract_week)
    if boundary_dates is None:
        raise TimelineChangeError(
            'Minggu batas kontrak tidak tersedia dalam rentang jadwal.',
            {'safe': False, 'reason': 'contract_boundary_outside_schedule'},
        )

    rows_before = source_rows + list(boundary_rows.values())
    snapshot = _snapshot_rows(rows_before)
    for row in source_rows:
        row.planned_proportion = Decimal('0.00')
    PekerjaanProgressWeekly.objects.bulk_update(
        source_rows, ['planned_proportion'], batch_size=500
    )

    missing_boundaries = []
    for pekerjaan_id, planned in planned_by_job.items():
        boundary_row = boundary_rows.get(pekerjaan_id)
        if boundary_row:
            boundary_row.planned_proportion = (
                boundary_row.planned_proportion or Decimal('0.00')
            ) + planned
            boundary_row.save(update_fields=['planned_proportion', 'updated_at'])
        else:
            missing_boundaries.append(PekerjaanProgressWeekly(
                project=project,
                pekerjaan_id=pekerjaan_id,
                week_number=contract_week,
                week_start_date=boundary_dates[0],
                week_end_date=boundary_dates[1],
                planned_proportion=planned,
                actual_proportion=Decimal('0.00'),
                actual_cost=None,
                notes='',
            ))
    if missing_boundaries:
        PekerjaanProgressWeekly.objects.bulk_create(missing_boundaries, batch_size=500)
    return snapshot, len(source_rows)


@transaction.atomic
def apply_project_timeline_change(
    project,
    new_start,
    new_end,
    resolution='none',
    user=None,
    expected_revision=None,
    target_field='tanggal_selesai',
):
    """Apply an approved timeline change as one transaction.

    Dua keluarga resolusi:

    * **Legacy** (``none``, ``trim_planned``) — arti dipertahankan persis seperti
      sebelumnya demi kompatibilitas (doc 37 §6). ``trim_planned`` hanya me-nol-kan
      nilai planned dan meninggalkan barisnya, sehingga jadwal tetap basi setelahnya
      (T-06). Disupersede oleh ``follow_date``; tidak ditawarkan lagi di UI.
    * **Mesin resolusi** (``keep_ordinal``, ``accumulate_edge``, ``follow_date``) —
      menuntaskan nasib setiap baris sehingga tidak ada sisa di luar jendela baru.

    Realisasi dilindungi lebih dulu oleh gerbang K-1 (lihat
    `analyze_project_timeline_change`), apa pun resolusinya.
    """
    project = type(project).objects.select_for_update().get(pk=project.pk)
    if expected_revision is not None and project.schedule_revision != expected_revision:
        raise TimelineChangeError(
            'Struktur jadwal sudah berubah. Muat ulang halaman sebelum menyimpan.',
            {
                'safe': False,
                'reason': 'schedule_revision_conflict',
                'schedule_revision': project.schedule_revision,
            },
        )

    impact = analyze_project_timeline_change(
        project, new_start, new_end, target_field=target_field
    )
    new_work_end = date.fromisoformat(impact['new_end'])
    new_contract_end = date.fromisoformat(impact['new_contract_end'])
    new_additional_end = (
        date.fromisoformat(impact['new_additional_end'])
        if impact['new_additional_end'] else None
    )

    if resolution not in ALL_RESOLUTIONS:
        raise TimelineChangeError('Resolusi timeline tidak valid.', impact)

    # --- Gerbang K-1: realisasi dilindungi lebih dulu, apa pun resolusinya ---
    if impact['blocking_reason'] == 'actual_present_start_shift':
        raise TimelineChangeError(
            'Perubahan tanggal mulai menggeser seluruh batas minggu, sedangkan '
            'proyek ini sudah memiliki realisasi. Realisasi tidak pernah '
            'dipindahkan otomatis, jadi perubahan dibatalkan.',
            impact,
        )
    if impact['blocking_reason'] == 'actual_out_of_window':
        raise TimelineChangeError(
            'Tanggal baru melewati minggu yang memiliki actual progress atau biaya aktual. Perubahan dibatalkan.',
            impact,
        )
    if impact['blocking_reason'] == 'notes_out_of_window':
        raise TimelineChangeError(
            'Tanggal akhir tambahan melewati minggu yang masih memiliki catatan. '
            'Pindahkan atau hapus catatan tersebut terlebih dahulu.',
            impact,
        )

    trimmed = []
    resolution_counts = {}
    requested_resolution = resolution
    planned_move_snapshot = []
    planned_moved_count = 0
    if resolution == RESOLUTION_MOVE_PLANNED_TO_BOUNDARY:
        if (
            target_field != 'tanggal_selesai'
            or impact['start_changed']
            or impact['end_changed']
            or not impact['planned_extension_records']
        ):
            raise TimelineChangeError(
                'Pemindahan planned ke minggu batas tidak cocok dengan perubahan timeline ini.',
                {**impact, 'blocking_reason': 'planned_boundary_move_not_applicable'},
            )
        planned_move_snapshot, planned_moved_count = _move_planned_to_contract_boundary(
            project,
            impact['contract_boundary_week'],
            impact['new_week_count'],
        )
        resolution_counts = {'planned_moved': planned_moved_count}
        # Rentang pencatatan tidak berubah; setelah memindahkan planned saja,
        # selesaikan mutasi proyek melalui jalur no-op timeline yang sama.
        resolution = RESOLUTION_NONE

    if resolution in LEGACY_RESOLUTIONS:
        if impact['start_requires_policy']:
            raise TimelineChangeError(
                'Perubahan tanggal mulai memengaruhi progress existing. Pilih '
                'salah satu resolusi penataan minggu terlebih dahulu.',
                impact,
            )
        if impact['planned_records'] and resolution != RESOLUTION_TRIM_PLANNED:
            raise TimelineChangeError(
                'Tanggal baru melewati planned progress. Pilih tindakan pada ringkasan dampak terlebih dahulu.',
                impact,
            )

        if resolution == RESOLUTION_TRIM_PLANNED and impact['planned_records']:
            rows = PekerjaanProgressWeekly.objects.filter(
                project=project,
                week_number__gt=impact['new_week_count'],
                planned_proportion__gt=0,
            )
            for row in rows:
                trimmed.append({
                    'pekerjaan_id': row.pekerjaan_id,
                    'week_number': row.week_number,
                    'old_planned_proportion': str(row.planned_proportion),
                })
            rows.update(planned_proportion=0)

        rows_before = []
        if resolution == RESOLUTION_NONE:
            # Baris di luar jendela baru yang tidak membawa data apa pun tidak
            # memerlukan keputusan siapa pun: menghapusnya tidak menghilangkan
            # nilai, sedangkan membiarkannya membuat jadwal langsung basi setelah
            # perubahan yang sukses (T-06). Ini kasus doc 38 §6.1 #2 — "tanggal
            # selesai diperpendek, minggu terbuang kosong" — dan juga yang
            # membuat tombol perbaikan di halaman Jadwal dapat menuntaskan
            # kolom sisa yang kosong tanpa bertanya apa pun.
            #
            # `trim_planned` sengaja TIDAK ikut: ia jalur legacy yang kontraknya
            # justru meninggalkan baris ber-nilai 0 (lihat docstring fungsi).
            empty_outside = (
                PekerjaanProgressWeekly.objects
                .filter(project=project)
                .filter(week_number__gt=impact['new_week_count'])
                .filter(
                    planned_proportion=0,
                    actual_proportion=0,
                    actual_cost__isnull=True,
                    notes='',
                )
            )
            rows_before = planned_move_snapshot + _snapshot_rows(empty_outside)
            empty_outside.delete()
    else:
        allowed = impact['allowed_resolutions']
        if resolution not in allowed:
            raise TimelineChangeError(
                'Resolusi tersebut tidak berlaku untuk bentuk perubahan ini.',
                impact,
            )

        week_end_day = project.week_end_day if project.week_end_day is not None else 6
        buckets = build_week_buckets(new_start, new_work_end, week_end_day)
        if not buckets:
            raise TimelineChangeError(
                'Rentang tanggal baru tidak menghasilkan satu pun minggu.',
                impact,
            )

        rows = list(
            PekerjaanProgressWeekly.objects
            .filter(project=project)
            .order_by('pekerjaan_id', 'week_number')
        )
        target, resolution_counts = plan_timeline_resolution(
            rows, buckets, new_start, resolution
        )
        _guard_target(target, impact, project, rows)
        rows_before = _snapshot_rows(rows)
        _write_target(project, rows, target, buckets)

    old_timeline = {
        'tanggal_mulai': project.tanggal_mulai.isoformat() if project.tanggal_mulai else None,
        'tanggal_selesai': project.tanggal_selesai.isoformat() if project.tanggal_selesai else None,
        'tanggal_akhir_tambahan': (
            project.tanggal_akhir_tambahan.isoformat()
            if project.tanggal_akhir_tambahan else None
        ),
    }
    project.tanggal_mulai = new_start
    project.tanggal_selesai = new_contract_end
    project.tanggal_akhir_tambahan = new_additional_end
    if target_field == 'tanggal_selesai':
        project.durasi_hari = (new_contract_end - new_start).days + 1
    project.save()
    aligned_row_count, date_alignment_snapshot = _align_weekly_row_dates(
        project,
        new_start,
        new_work_end,
        project.week_end_day if project.week_end_day is not None else 6,
    )
    if date_alignment_snapshot and resolution in LEGACY_RESOLUTIONS:
        rows_before.extend(date_alignment_snapshot)
    _regenerate_weekly_structure(project)
    invalidate_schedule_caches(project.id)

    try:
        DetailAHSPAudit.objects.create(
            project=project,
            pekerjaan=None,
            action=DetailAHSPAudit.ACTION_UPDATE,
            old_data={
                'timeline': old_timeline,
                'trimmed_planned': trimmed,
                # Snapshot penuh: resolusi mesin dapat memindahkan, menggabung,
                # atau menghapus baris, sehingga pemulihan manual butuh seluruh
                # field yang dapat berubah (doc 37 §4.8).
                'rows_before': rows_before,
            },
            new_data={
                'timeline': {
                    'tanggal_mulai': new_start.isoformat(),
                    'tanggal_selesai': new_contract_end.isoformat(),
                    'tanggal_akhir_tambahan': (
                        new_additional_end.isoformat() if new_additional_end else None
                    ),
                    'work_period_end': new_work_end.isoformat(),
                    'target_field': target_field,
                },
                'resolution': requested_resolution,
                'trimmed_count': len(trimmed),
                'resolution_counts': resolution_counts,
                'weekly_date_rows_aligned': aligned_row_count,
            },
            triggered_by='user',
            user=user if getattr(user, 'id', None) else None,
            change_summary=(
                f'Perubahan timeline {old_timeline["tanggal_mulai"]}–{old_timeline["tanggal_selesai"]} '
                f'→ {new_start.isoformat()}–{new_work_end.isoformat()} ({resolution})'
            ),
        )
    except Exception:
        # Audit must never undo a valid timeline transaction.
        pass

    return {
        **impact,
        'resolution': requested_resolution,
        'trimmed_count': len(trimmed),
        'planned_moved_count': planned_moved_count,
        'resolution_counts': resolution_counts,
        'weekly_date_rows_aligned': aligned_row_count,
        'schedule_revision': project.schedule_revision,
    }
