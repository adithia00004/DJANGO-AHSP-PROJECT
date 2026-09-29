"""Langkah 0.1 (doc 40/41) — jaring pengaman transfer data progres.

Backup JSON -> restore dan duplikasi proyek harus mempertahankan seluruh baris
`PekerjaanProgressWeekly` (rencana, realisasi, biaya aktual, catatan, nomor &
tanggal minggu) beserta metadata timeline proyek. Tes ini menjadi jaring
pengaman bolak-balik untuk langkah 0.1–0.3.
"""
import json
import unittest
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
    TahapPelaksanaan,
)
from detail_project.progress_utils import build_week_buckets
from detail_project.services import DeepCopyService
from detail_project.progress_write_service import write_progress

User = get_user_model()

# Minggu 6 Sep 2026 s.d. Minggu 13 Sep 2026, minggu berakhir hari Minggu:
# M1 = 6 Sep (satu hari), M2 = 7-13 Sep. Dua minggu kanonik, padahal
# ceil((13-6)/7) = 1.
START = date(2026, 9, 6)
END = date(2026, 9, 13)


class _TransferFixtureMixin:
    def setUp(self):
        self.owner = User.objects.create_user(
            username="transfer-roundtrip",
            password="StrongPass123!",
            subscription_status=User.SubscriptionStatus.PRO,
            subscription_end_date=timezone.now() + timedelta(days=30),
        )
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Proyek Transfer",
            sumber_dana="APBD",
            lokasi_project="Mataram",
            nama_client="Dinas",
            anggaran_owner=Decimal("1000000"),
            tanggal_mulai=START,
            tanggal_selesai=END,
            week_start_day=0,
            week_end_day=6,
        )
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1,
        )
        self.p1 = self._pekerjaan(sub, "P-001", "Galian", 1)
        self.p2 = self._pekerjaan(sub, "P-002", "Urugan", 2)

        buckets = {n: (s, e) for n, s, e in build_week_buckets(START, END, 6)}
        assert len(buckets) == 2, buckets

        def row(pek, week, planned, actual, cost, notes):
            start, end = buckets[week]
            PekerjaanProgressWeekly.objects.create(
                project=self.project, pekerjaan=pek, week_number=week,
                week_start_date=start, week_end_date=end,
                planned_proportion=Decimal(planned), actual_proportion=Decimal(actual),
                actual_cost=cost, notes=notes,
            )

        # M1: biaya & catatan (temuan C); biaya 0 harus tetap 0, bukan kosong.
        row(self.p1, 1, "20", "15", Decimal("5000"), "catatan lapangan")
        row(self.p2, 1, "10", "0", Decimal("0"), "")
        # M2: minggu terakhir yang sah (temuan B).
        row(self.p1, 2, "80", "30", None, "")
        row(self.p2, 2, "90", "10", None, "")

        TahapPelaksanaan.objects.bulk_create([
            TahapPelaksanaan(
                project=self.project,
                nama=f"Week {week}",
                urutan=week - 1,
                tanggal_mulai=buckets[week][0],
                tanggal_selesai=buckets[week][1],
                is_auto_generated=True,
                generation_mode="weekly",
            )
            for week in buckets
        ])

        self.client.force_login(self.owner)

    @staticmethod
    def _pekerjaan(sub, kode, uraian, order):
        return Pekerjaan.objects.create(
            project=sub.project, sub_klasifikasi=sub, source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode=kode, snapshot_uraian=uraian, snapshot_satuan="m3",
            ordering_index=order,
        )

    @staticmethod
    def _rows(project):
        """Baris progres kanonik, dikunci oleh kode pekerjaan agar lintas proyek."""
        return {
            (pw.pekerjaan.snapshot_kode, pw.week_number): (
                pw.week_start_date, pw.week_end_date,
                pw.planned_proportion, pw.actual_proportion, pw.actual_cost, pw.notes or "",
            )
            for pw in PekerjaanProgressWeekly.objects.filter(project=project).select_related("pekerjaan")
        }

    @staticmethod
    def _progress_values(rows):
        """Tanpa tanggal & biaya/catatan: isolasi temuan B dari C."""
        return {key: (value[2], value[3]) for key, value in rows.items()}

    def _backup_payload(self):
        export = self.client.get(
            reverse("detail_project:export_project_full_json", args=[self.project.id]),
            {"include_progress": "1"},
        )
        self.assertEqual(export.status_code, 200, export.content[:300])
        return json.loads(export.content)

    def _restore_payload(self, payload):
        imported = self.client.post(
            reverse("detail_project:import_project_from_json"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(imported.status_code, 200, imported.content[:500])
        return Project.objects.get(pk=json.loads(imported.content)["project_id"])

    def _backup_restore(self):
        return self._restore_payload(self._backup_payload())


class BackupRestoreRoundtripTests(_TransferFixtureMixin, TestCase):
    def test_restore_keeps_timeline_metadata(self):
        restored = self._backup_restore()
        self.assertEqual(
            (restored.tanggal_mulai, restored.tanggal_selesai, restored.week_start_day, restored.week_end_day),
            (START, END, 0, 6),
        )

    def test_backup_restore_keeps_additional_end(self):
        self.project.tanggal_akhir_tambahan = date(2026, 9, 20)
        self.project.save(update_fields=["tanggal_akhir_tambahan", "updated_at"])
        payload = self._backup_payload()
        self.assertEqual(payload["project"]["tanggal_akhir_tambahan"], "2026-09-20")
        restored = self._restore_payload(payload)
        self.assertEqual(restored.tanggal_akhir_tambahan, date(2026, 9, 20))

    def test_legacy_backup_without_additional_end_restores_without_extension(self):
        payload = self._backup_payload()
        payload["project"].pop("tanggal_akhir_tambahan", None)
        restored = self._restore_payload(payload)
        self.assertIsNone(restored.tanggal_akhir_tambahan)

    def test_restore_keeps_last_short_week(self):
        restored = self._backup_restore()
        self.assertEqual(
            self._progress_values(self._rows(restored)),
            self._progress_values(self._rows(self.project)),
        )

    def test_export_stats_use_canonical_week_count(self):
        payload = self._backup_payload()
        self.assertEqual(payload["stats"]["total_project_weeks"], 2)

    def test_restore_legacy_rows_without_week_dates_uses_canonical_buckets(self):
        payload = self._backup_payload()
        for row in payload["progress_weekly"]:
            row.pop("week_start_date", None)
            row.pop("week_end_date", None)
        restored = self._restore_payload(payload)
        source = self._rows(self.project)
        result = self._rows(restored)
        self.assertEqual(
            {key: value[:2] for key, value in result.items()},
            {key: value[:2] for key, value in source.items()},
        )

    def test_restore_keeps_actual_cost_and_notes(self):
        restored = self._backup_restore()
        rows = self._rows(restored)
        self.assertEqual(rows[("P-001", 1)][4], Decimal("5000"))
        self.assertEqual(rows[("P-001", 1)][5], "catatan lapangan")
        self.assertEqual(rows[("P-002", 1)][4], Decimal("0"))  # 0, bukan kosong

    def test_restore_keeps_every_weekly_row_exactly(self):
        restored = self._backup_restore()
        self.assertEqual(self._rows(restored), self._rows(self.project))


class DuplicateRoundtripTests(_TransferFixtureMixin, TestCase):
    def _service_copy(self, **kwargs):
        return DeepCopyService(self.project).copy(
            new_owner=self.owner, new_name="Proyek Transfer (salinan)", **kwargs,
        )

    def test_service_copy_copies_every_weekly_row(self):
        copied = self._service_copy(copy_jadwal=True)
        self.assertEqual(self._rows(copied), self._rows(self.project))

    def test_service_copy_copies_timeline_metadata(self):
        self.project.tanggal_akhir_tambahan = date(2026, 9, 20)
        self.project.save(update_fields=["tanggal_akhir_tambahan", "updated_at"])
        copied = self._service_copy(copy_jadwal=True)
        self.assertEqual(
            (
                copied.tanggal_mulai, copied.tanggal_selesai,
                copied.tanggal_akhir_tambahan, copied.week_start_day, copied.week_end_day,
            ),
            (START, END, date(2026, 9, 20), 0, 6),
        )

    def test_service_copy_without_jadwal_copies_no_weekly_rows(self):
        copied = self._service_copy(copy_jadwal=False)
        self.assertEqual(self._rows(copied), {})

    def test_api_deep_copy_copies_every_weekly_row(self):
        self.project.tanggal_akhir_tambahan = date(2026, 9, 20)
        self.project.save(update_fields=["tanggal_akhir_tambahan", "updated_at"])
        response = self.client.post(
            reverse("detail_project:api_deep_copy_project", args=[self.project.id]),
            data=json.dumps({"new_name": "Proyek Transfer (API)", "copy_jadwal": True}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content[:500])
        payload = json.loads(response.content)
        copied = Project.objects.get(pk=payload["new_project"]["id"])
        self.assertEqual(self._rows(copied), self._rows(self.project))
        self.assertEqual(payload["new_project"]["tanggal_akhir_tambahan"], "2026-09-20")

    def test_dashboard_form_copy_copies_every_weekly_row(self):
        self.project.tanggal_akhir_tambahan = date(2026, 9, 20)
        self.project.save(update_fields=["tanggal_akhir_tambahan", "updated_at"])
        response = self.client.post(
            reverse("dashboard:project_duplicate", kwargs={"pk": self.project.pk}),
            {
                "nama": "Proyek Transfer (form)",
                "tanggal_mulai": START.isoformat(),
                "tanggal_selesai": END.isoformat(),
                "durasi_hari": str((END - START).days + 1),
                "sumber_dana": "APBD",
                "lokasi_project": "Mataram",
                "nama_client": "Dinas",
                "anggaran_owner": "1000000",
            },
        )
        self.assertEqual(response.status_code, 302, response.content[:500])
        copied = Project.objects.get(owner=self.owner, nama="Proyek Transfer (form)")
        self.assertEqual(self._rows(copied), self._rows(self.project))
        self.assertEqual(copied.tanggal_akhir_tambahan, date(2026, 9, 20))

    def test_copy_with_new_start_keeps_week_ordinals_and_rebuilds_dates(self):
        self.project.tanggal_akhir_tambahan = date(2026, 9, 20)
        self.project.save(update_fields=["tanggal_akhir_tambahan", "updated_at"])
        new_start = date(2026, 9, 20)
        new_end = date(2026, 9, 27)
        copied = self._service_copy(
            new_tanggal_mulai=new_start,
            new_tanggal_selesai=new_end,
        )
        source_rows = self._rows(self.project)
        copied_rows = self._rows(copied)
        self.assertEqual(set(copied_rows), set(source_rows))
        self.assertEqual(copied_rows[("P-001", 1)][:2], (new_start, new_start))
        self.assertEqual(copied_rows[("P-001", 2)][:2], (date(2026, 9, 21), new_end))
        self.assertEqual(copied_rows[("P-001", 2)][2:], source_rows[("P-001", 2)][2:])
        self.assertEqual(copied.tanggal_akhir_tambahan, date(2026, 10, 4))

    def test_shorter_api_copy_reports_progress_weeks_that_do_not_fit(self):
        response = self.client.post(
            reverse("detail_project:api_deep_copy_project", args=[self.project.id]),
            data=json.dumps({
                "new_name": "Proyek Transfer (rentang pendek)",
                "new_tanggal_mulai": START.isoformat(),
                "new_tanggal_selesai": START.isoformat(),
                "copy_jadwal": True,
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 201, response.content[:500])
        payload = json.loads(response.content)
        copied = Project.objects.get(pk=payload["new_project"]["id"])
        self.assertEqual(set(self._rows(copied)), {("P-001", 1), ("P-002", 1)})
        self.assertEqual(payload["skipped_items"]["jadwal"], 2)
        self.assertEqual(payload["warnings"][0]["details"]["weeks_outside_target_timeline"], 2)
        self.assertEqual(
            copied.tahapan.filter(is_auto_generated=True, generation_mode="weekly").count(),
            1,
        )


class NonSundayBoundaryBackupRestoreTests(_TransferFixtureMixin, TestCase):
    """Round-trip juga harus memakai hari batas minggu pilihan proyek."""

    def setUp(self):
        super().setUp()
        # Minggu dimulai pada hari Minggu dan berakhir Jumat. Rentang 6–13 Sep
        # tetap dua minggu canonical: 6–11 Sep dan 12–13 Sep.
        self.project.week_start_day = 6
        self.project.week_end_day = 4
        self.project.save(update_fields=["week_start_day", "week_end_day", "updated_at"])
        buckets = {
            n: (start, end)
            for n, start, end in build_week_buckets(START, END, 4)
        }
        self.assertEqual(len(buckets), 2, buckets)
        for row in PekerjaanProgressWeekly.objects.filter(project=self.project):
            row.week_start_date, row.week_end_date = buckets[row.week_number]
            row.save(update_fields=["week_start_date", "week_end_date", "updated_at"])

    def test_restore_keeps_last_week_with_non_sunday_boundary(self):
        restored = self._backup_restore()
        self.assertEqual(
            self._progress_values(self._rows(restored)),
            self._progress_values(self._rows(self.project)),
        )


class ProgressWriteServiceTests(_TransferFixtureMixin, TestCase):
    def _cell(self, **overrides):
        start, end = build_week_buckets(START, END, 6)[0][1:]
        return {
            "pekerjaan_id": self.p1.id,
            "week_number": 1,
            "week_start_date": start,
            "week_end_date": end,
            **overrides,
        }

    def test_planned_write_preserves_actual_and_cost(self):
        result = write_progress(
            self.project,
            [self._cell(planned_proportion=Decimal("25"), notes="")],
            kind="planned_new",
        )
        row = result[0]["record"]
        self.assertEqual(row.planned_proportion, Decimal("25"))
        self.assertEqual(row.actual_proportion, Decimal("15"))
        self.assertEqual(row.actual_cost, Decimal("5000"))

    def test_actual_write_preserves_planned_and_unspecified_cost(self):
        result = write_progress(
            self.project,
            [self._cell(actual_proportion=Decimal("40"), notes="")],
            kind="actual",
        )
        row = result[0]["record"]
        self.assertEqual(row.planned_proportion, Decimal("20"))
        self.assertEqual(row.actual_proportion, Decimal("40"))
        self.assertEqual(row.actual_cost, Decimal("5000"))

    def test_actual_write_can_clear_cost_without_changing_planned(self):
        result = write_progress(
            self.project,
            [self._cell(
                actual_proportion=Decimal("15"),
                actual_cost=None,
                has_actual_cost=True,
                clear_actual_cost=True,
                notes="",
            )],
            kind="actual",
        )
        row = result[0]["record"]
        self.assertEqual(row.planned_proportion, Decimal("20"))
        self.assertIsNone(row.actual_cost)

    def test_historical_write_restores_zero_cost_and_notes(self):
        result = write_progress(
            self.project,
            [self._cell(
                planned_proportion=Decimal("30"),
                actual_proportion=Decimal("0"),
                actual_cost=Decimal("0"),
                notes="historical note",
            )],
            kind="historical",
        )
        row = result[0]["record"]
        self.assertEqual(row.actual_cost, Decimal("0"))
        self.assertEqual(row.notes, "historical note")

    def test_user_move_changes_planned_only(self):
        result = write_progress(
            self.project,
            [self._cell(planned_proportion=Decimal("45"))],
            kind="user_move",
        )
        row = result[0]["record"]
        self.assertEqual(row.planned_proportion, Decimal("45"))
        self.assertEqual(row.actual_proportion, Decimal("15"))
        self.assertEqual(row.actual_cost, Decimal("5000"))

    def test_unknown_write_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            write_progress(self.project, [], kind="unsupported")
