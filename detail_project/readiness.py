"""WP-B4 — Canonical project readiness & missing-value diagnostics.

Single source of truth for "can this project be computed/reported, and if not,
which pekerjaan/item is the cause". Consumers (Rekap RAB, Rincian, Template,
Jadwal, Kebutuhan) READ this schema and merely display it; they must not
recompute readiness on their own (locked decision B-4 / audit A-8, A-9, D-06).

Caching policy (inc-2.2):
    There is NO cross-request cache. A count/sum digest is not collision-free —
    swapping two coefficients with an unchanged total left the signature
    identical and served stale data — and a row-exact digest costs as much as
    just recomputing. So we recompute from live DB state every call (bounded by
    a query-budget test) and only memoize WITHIN a single request via the
    optional ``request`` argument, so two consumers in one request share one
    computation.

Diagnostic entry shape (uniform, traceable — D-RK-07 / D-06):

    {
        "pekerjaan_id":  int | None,
        "harga_item_id": int (price only),
        "source_detail_id": int (detail/expansion only),
        "kode":   str,
        "uraian": str,
        "source_table": str,
        "source_page":  str,
        "issue":  str,
        # plus optional "actual" / "expected" / "affected_pekerjaan"
    }

Counts are NOT stored — derive them from the arrays.

null-vs-zero (locked by the underlying model facts):

  * missing_volume       : a ``VolumePekerjaan`` row is ABSENT (``quantity`` is
                           NOT NULL → absence is the only "belum diisi" state; an
                           explicit ``0`` is intentional and is NOT flagged).
  * missing_price        : ``HargaItemProject.harga_satuan IS NULL`` for an item
                           used in the calculation path. ``0.00`` is explicit free.
  * invalid_coefficient  : ``koefisien < 0`` (defensive — WP-B3 rejects on save).
  * expansion (D-06)     : analysed per ``source_detail``:
                             - no expanded component         -> ``missing_expansion``
                             - raw newer than its expansion  -> ``stale_expansion``
                             - fewer components than expected -> ``incomplete_expansion``
                             - extra components beyond expected -> ``excess_expansion``
                           Expected counts: direct row = 1; ``ref_pekerjaan`` bundle
                           = the referenced pekerjaan's expanded-component count
                           (exact); ``ref_ahsp`` bundle = the referensi's rincian
                           count (best-effort — only used to report, never to raise
                           a partial flag, to avoid false positives on nested LAIN).
                           A PARTIALLY expanded pekerjaan is the dangerous case:
                           ``compute_rekap_for_project`` reads only its expanded
                           rows and silently drops the unexpanded raw -> undercount.
  * expanded_ready       : no ``expansion_not_ready`` entry exists.

Stale-expansion detection (inc-4b): each ``DetailAHSPExpanded`` stores a
``source_signature`` (content hash of its raw source row, captured at expansion).
Readiness recomputes the raw row's signature at read time and flags
``stale_expansion`` on mismatch — bypass-proof against ``QuerySet.update()`` /
``bulk_update()`` that skip ``updated_at``. Legacy rows without a stored signature
fall back to the ``updated_at`` heuristic until re-expanded.

Jadwal-derived signals are LIVE since inc-4a (computed from the weekly canonical
``PekerjaanProgressWeekly``):
  * incomplete_planned_allocation : pekerjaan with 0 < Σ planned_proportion < 100
                                    (Σ=0 excluded — not scheduled, not "incomplete").
  * allocation_without_volume      : Σ planned_proportion > 0 but volume absent/0.
  * timeline_stale (bool)          : a weekly row falls outside the current project
                                    window [tanggal_mulai, tanggal_selesai].
``PENDING_SIGNALS`` is now empty.
"""
from __future__ import annotations

import hashlib
from decimal import Decimal

from django.db.models import Count, Max, Q, Sum

from .models import (
    Pekerjaan,
    VolumePekerjaan,
    DetailAHSPProject,
    DetailAHSPExpanded,
    HargaItemProject,
    PekerjaanProgressWeekly,
)

SCHEMA_VERSION = "b4.5"  # b4.5 = reference_update_available signal (B7b)

# All signals are now computed; nothing pending.
PENDING_SIGNALS = ()

# Tolerance for planned-proportion comparisons (percent).
_ALLOC_TOL = Decimal("0.01")

PAGE_VOLUME = "volume"
PAGE_HARGA = "harga_items"
PAGE_DETAIL = "template_ahsp"
PAGE_JADWAL = "jadwal"

# 12 decimal places — matches DetailAHSPProject.koefisien precision so the
# signature is identical whether computed at write time or read time.
_KOEF_QUANT = Decimal("1.000000000000")


def source_signature(
    kategori,
    kode,
    koefisien,
    ref_pekerjaan_id,
    ref_ahsp_id,
    harga_item_id=None,
):
    """Content signature of a raw ``DetailAHSPProject`` row (WP-B4 inc-4b).

    Captured on each ``DetailAHSPExpanded`` at expansion time and recomputed at
    readiness time; a mismatch means the raw row changed without re-expansion
    (``stale_expansion``). Computed from actual values → not bypassable by
    ``QuerySet.update()`` / ``bulk_update()``.
    """
    try:
        koef = Decimal(koefisien if koefisien is not None else 0).quantize(_KOEF_QUANT)
    except Exception:
        koef = Decimal("0").quantize(_KOEF_QUANT)
    raw = "|".join([
        str(kategori or ""),
        str(kode or ""),
        f"{koef}",
        str(ref_pekerjaan_id or ""),
        str(ref_ahsp_id or ""),
        str(harga_item_id or ""),
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def master_reference_signature(ref_ahsp_id):
    """Content signature of a master AHSP's components (WP-B7a).

    Computed from ``RincianReferensi`` rows of the referenced master AHSP — each
    row's ``kategori``, ``kode_item``, ``koefisien`` (quantized 12dp),
    ``satuan_item`` and ``uraian_item``, in a deterministic order. Stamped on the
    raw ``DetailAHSPProject`` bundle row at expansion time (``ref_snapshot_signature``)
    and recomputed at readiness time; a mismatch means the chosen master version
    was corrected in place since the project last expanded it
    (``reference_update_available``, D-05). Returns ``None`` if the master is
    missing or has no rincian.
    """
    if not ref_ahsp_id:
        return None
    from referensi.models import RincianReferensi

    rows = list(
        RincianReferensi.objects.filter(ahsp_id=ref_ahsp_id)
        .values("kategori", "kode_item", "koefisien", "satuan_item", "uraian_item")
        .order_by("kategori", "kode_item", "uraian_item", "satuan_item")
    )
    return _master_sig_from_rows(rows)


def _master_sig_from_rows(rows):
    """Signature from already-fetched RincianReferensi rows (ordered).

    Shared by ``master_reference_signature`` (single master) and ``_compute``
    (bulk, one query for all referenced masters — preserves the query budget).
    Returns ``None`` for an empty master.
    """
    if not rows:
        return None
    parts = []
    for r in rows:
        try:
            koef = Decimal(r["koefisien"] if r["koefisien"] is not None else 0).quantize(_KOEF_QUANT)
        except Exception:
            koef = Decimal("0").quantize(_KOEF_QUANT)
        parts.append("|".join([
            str(r["kategori"] or ""),
            str(r["kode_item"] or ""),
            f"{koef}",
            str(r["satuan_item"] or ""),
            str(r["uraian_item"] or ""),
        ]))
    raw = "\n".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def compute_project_readiness(project, request=None):
    """Return the canonical readiness schema for ``project``.

    Always recomputes from live DB state (no cross-request cache). If ``request``
    is given, the result is memoized on it so repeated calls within one request
    are free.
    """
    if request is not None:
        store = getattr(request, "_b4_readiness", None)
        if store is None:
            store = {}
            request._b4_readiness = store
        if project.id in store:
            return store[project.id]

    data = _compute(project)

    if request is not None:
        request._b4_readiness[project.id] = data
    return data


def _compute(project):
    pekerjaan_meta = {
        p["id"]: p
        for p in Pekerjaan.objects.filter(project=project).values(
            "id", "snapshot_kode", "snapshot_uraian"
        )
    }
    all_job_ids = set(pekerjaan_meta.keys())

    def _pkj(pkj_id):
        m = pekerjaan_meta.get(pkj_id, {})
        return m.get("snapshot_kode") or "", m.get("snapshot_uraian") or ""

    # --- missing_volume: pekerjaan with NO VolumePekerjaan row.
    vol_job_ids = set(
        VolumePekerjaan.objects.filter(project=project).values_list(
            "pekerjaan_id", flat=True
        )
    )
    missing_volume = []
    for pkj_id in sorted(all_job_ids - vol_job_ids):
        kode, uraian = _pkj(pkj_id)
        missing_volume.append(
            {
                "pekerjaan_id": pkj_id,
                "kode": kode,
                "uraian": uraian,
                "source_table": "VolumePekerjaan",
                "source_page": PAGE_VOLUME,
                "issue": "missing_volume",
            }
        )

    # --- expansion analysis per source_detail (D-06).
    raw_rows = list(
        DetailAHSPProject.objects.filter(project=project).values(
            "id", "pekerjaan_id", "kode", "uraian", "kategori",
            "koefisien", "updated_at", "ref_pekerjaan_id", "ref_ahsp_id",
            "harga_item_id", "ref_snapshot_signature",
        )
    )
    exp_groups = {
        g["source_detail_id"]: g
        for g in DetailAHSPExpanded.objects.filter(project=project)
        .values("source_detail_id")
        .annotate(
            n=Count("id"),
            last=Max("updated_at"),
            sig=Max("source_signature"),
            signed_n=Count("source_signature"),
            sig_n=Count("source_signature", distinct=True),
        )
    }
    # expanded-component count per pekerjaan (exact expected for ref_pekerjaan).
    exp_count_by_pkj = {
        r["pekerjaan_id"]: r["n"]
        for r in DetailAHSPExpanded.objects.filter(project=project)
        .values("pekerjaan_id")
        .annotate(n=Count("id"))
    }
    # referensi rincian per referenced AHSP — ONE query yields both the
    # best-effort component count (for expansion analysis) and the master content
    # signature (for B7b reference_update_available). Grouped in Python to keep
    # the query budget constant regardless of the number of distinct masters.
    ref_ahsp_ids = {r["ref_ahsp_id"] for r in raw_rows if r["ref_ahsp_id"]}
    rincian_count_by_ahsp = {}
    master_sig_by_ahsp = {}
    if ref_ahsp_ids:
        from collections import defaultdict as _defaultdict
        from referensi.models import RincianReferensi

        _rows_by_ahsp = _defaultdict(list)
        for r in (
            RincianReferensi.objects.filter(ahsp_id__in=ref_ahsp_ids)
            .values("ahsp_id", "kategori", "kode_item", "koefisien", "satuan_item", "uraian_item")
            .order_by("ahsp_id", "kategori", "kode_item", "uraian_item", "satuan_item")
        ):
            _rows_by_ahsp[r["ahsp_id"]].append(r)
        for _aid, _rws in _rows_by_ahsp.items():
            rincian_count_by_ahsp[_aid] = len(_rws)
            master_sig_by_ahsp[_aid] = _master_sig_from_rows(_rws)

    expansion_not_ready = []
    invalid_coefficient = []
    for row in raw_rows:
        kode = row["kode"] or ""
        uraian = row["uraian"] or ""
        if row["koefisien"] is not None and row["koefisien"] < 0:
            invalid_coefficient.append(
                {
                    "pekerjaan_id": row["pekerjaan_id"],
                    "source_detail_id": row["id"],
                    "kode": kode,
                    "uraian": uraian,
                    "source_table": "DetailAHSPProject",
                    "source_page": PAGE_DETAIL,
                    "issue": "invalid_coefficient",
                    "actual": str(row["koefisien"]),
                }
            )

        is_bundle = row["kategori"] == "LAIN" and (
            row["ref_pekerjaan_id"] is not None or row["ref_ahsp_id"] is not None
        )
        if not is_bundle:
            expected, expected_exact = 1, True
        elif row["ref_pekerjaan_id"] is not None:
            expected = exp_count_by_pkj.get(row["ref_pekerjaan_id"], 0)
            expected_exact = True
        else:  # ref_ahsp — best-effort, not used to raise partial flags
            expected = rincian_count_by_ahsp.get(row["ref_ahsp_id"])
            expected_exact = False

        g = exp_groups.get(row["id"])
        actual = g["n"] if g else 0

        def _entry(issue):
            return {
                "pekerjaan_id": row["pekerjaan_id"],
                "source_detail_id": row["id"],
                "kode": kode,
                "uraian": uraian,
                "source_table": "DetailAHSPProject",
                "source_page": PAGE_DETAIL,
                "issue": issue,
                "expected": expected,
                "actual": actual,
            }

        # Stale detection (inc-4b): compare the source row's CURRENT signature to
        # the one captured at expansion time (bypass-proof). Legacy rows with no
        # stored signature (sig is None) fall back to the updated_at heuristic.
        stored_sig = g["sig"] if g else None
        if g and g["signed_n"] not in (0, g["n"]):
            # A source must never have a mixture of signed and legacy rows.
            is_stale = True
        elif g and g["sig_n"] > 1:
            # All expanded rows produced from one raw source must carry one
            # identical signature. Mixed signatures mean a partial rewrite.
            is_stale = True
        elif stored_sig is not None:
            current_sig = source_signature(
                row["kategori"], row["kode"], row["koefisien"],
                row["ref_pekerjaan_id"], row["ref_ahsp_id"],
                row["harga_item_id"],
            )
            is_stale = stored_sig != current_sig
        else:
            is_stale = (
                g is not None
                and g["last"] is not None
                and row["updated_at"] is not None
                and g["last"] < row["updated_at"]
            )

        if actual == 0:
            expansion_not_ready.append(_entry("missing_expansion"))
        elif is_stale:
            expansion_not_ready.append(_entry("stale_expansion"))
        elif expected_exact and actual != expected:
            issue = "incomplete_expansion" if actual < expected else "excess_expansion"
            expansion_not_ready.append(_entry(issue))

    # negative coefficient that only exists in expanded rows (defensive).
    for e in DetailAHSPExpanded.objects.filter(
        project=project, koefisien__lt=0
    ).values("pekerjaan_id", "source_detail_id", "kode", "uraian", "koefisien"):
        invalid_coefficient.append(
            {
                "pekerjaan_id": e["pekerjaan_id"],
                "source_detail_id": e["source_detail_id"],
                "kode": e["kode"] or "",
                "uraian": e["uraian"] or "",
                "source_table": "DetailAHSPExpanded",
                "source_page": PAGE_DETAIL,
                "issue": "invalid_coefficient",
                "actual": str(e["koefisien"]),
            }
        )

    expanded_ready = not expansion_not_ready

    # --- reference_update_available (B7b, D-05): a bundle row references a master
    #     AHSP whose content was corrected in place since this project last
    #     expanded it (stored snapshot signature != master's current signature).
    #     A new yearly version (different `sumber`) is a NEW master row and does
    #     NOT trigger this — the project stays pinned to its chosen version.
    #     Rows never stamped (legacy) or whose master is gone are skipped to
    #     avoid false positives (the latter surfaces via expansion signals).
    reference_update_available = []
    for row in raw_rows:
        if not row["ref_ahsp_id"]:
            continue
        stored = row["ref_snapshot_signature"]
        if stored is None:
            continue
        current = master_sig_by_ahsp.get(row["ref_ahsp_id"])
        if current is None or stored == current:
            continue
        reference_update_available.append(
            {
                "pekerjaan_id": row["pekerjaan_id"],
                "source_detail_id": row["id"],
                "kode": row["kode"] or "",
                "uraian": row["uraian"] or "",
                "ref_ahsp_id": row["ref_ahsp_id"],
                "source_table": "DetailAHSPProject",
                "source_page": PAGE_DETAIL,
                "issue": "reference_update_available",
            }
        )
    reference_update_available.sort(key=lambda e: e["source_detail_id"])

    # --- missing_price: harga_satuan IS NULL on an item used in the calc path.
    expanded_job_ids = set(exp_count_by_pkj.keys())
    raw_fallback_job_ids = all_job_ids - expanded_job_ids

    missing_price_map = {}
    rows_price = list(
        DetailAHSPExpanded.objects.filter(
            project=project, harga_item__harga_satuan__isnull=True
        ).values_list(
            "harga_item_id", "harga_item__kode_item", "harga_item__uraian", "pekerjaan_id"
        )
    ) + list(
        DetailAHSPProject.objects.filter(
            project=project,
            pekerjaan_id__in=raw_fallback_job_ids,
            harga_item__harga_satuan__isnull=True,
        ).values_list(
            "harga_item_id", "harga_item__kode_item", "harga_item__uraian", "pekerjaan_id"
        )
    )
    for hi_id, kode, uraian, pkj_id in rows_price:
        entry = missing_price_map.setdefault(
            hi_id,
            {
                "harga_item_id": hi_id,
                "kode": kode or "",
                "uraian": uraian or "",
                "source_table": "HargaItemProject",
                "source_page": PAGE_HARGA,
                "issue": "missing_price",
                "affected_pekerjaan": set(),
            },
        )
        entry["affected_pekerjaan"].add(pkj_id)
    missing_price = [
        {**e, "affected_pekerjaan": sorted(e["affected_pekerjaan"])}
        for e in sorted(missing_price_map.values(), key=lambda x: (x["kode"] or ""))
    ]

    # --- canonical item index (Master Plan minimum contract): items needing
    #     attention, lightweight {harga_item_id, kode}. Full detail lives in
    #     missing_price entries.
    affected_items = [
        {"harga_item_id": e["harga_item_id"], "kode": e["kode"]} for e in missing_price
    ]

    # --- jadwal-derived signals (inc-4a), from the weekly canonical.
    planned_totals = {
        r["pekerjaan_id"]: (r["total"] or Decimal("0"))
        for r in PekerjaanProgressWeekly.objects.filter(project=project)
        .values("pekerjaan_id")
        .annotate(total=Sum("planned_proportion"))
    }
    vol_qty = dict(
        VolumePekerjaan.objects.filter(project=project).values_list(
            "pekerjaan_id", "quantity"
        )
    )

    incomplete_planned_allocation = []
    allocation_without_volume = []
    for pkj_id, total in planned_totals.items():
        if total <= 0:
            continue  # not scheduled at all — excluded (not "incomplete")
        kode, uraian = _pkj(pkj_id)
        # scheduled but no/zero volume — work planned without capacity.
        qty = vol_qty.get(pkj_id)
        if qty is None or qty == 0:
            allocation_without_volume.append({
                "pekerjaan_id": pkj_id, "kode": kode, "uraian": uraian,
                "source_table": "PekerjaanProgressWeekly+VolumePekerjaan",
                "source_page": PAGE_JADWAL,
                "issue": "allocation_without_volume", "actual": f"{total}",
            })
        # partially scheduled — total planned below 100%.
        if total < (Decimal("100") - _ALLOC_TOL):
            incomplete_planned_allocation.append({
                "pekerjaan_id": pkj_id, "kode": kode, "uraian": uraian,
                "source_table": "PekerjaanProgressWeekly",
                "source_page": PAGE_JADWAL,
                "issue": "incomplete_planned_allocation", "actual": f"{total}",
            })
    incomplete_planned_allocation.sort(key=lambda e: e["pekerjaan_id"])
    allocation_without_volume.sort(key=lambda e: e["pekerjaan_id"])

    # timeline_stale: any weekly row falls OUTSIDE the current project window
    # (e.g. project dates were changed after the schedule was built).
    timeline_stale = False
    start = getattr(project, "tanggal_mulai", None)
    end = getattr(project, "tanggal_selesai", None)
    if start and end:
        timeline_stale = (
            PekerjaanProgressWeekly.objects.filter(project=project)
            .filter(Q(week_start_date__lt=start) | Q(week_end_date__gt=end))
            .exists()
        )

    # --- pekerjaan index into the rich entries above (UI highlighting).
    affected_pekerjaan = {e["pekerjaan_id"] for e in missing_volume}
    affected_pekerjaan.update(e["pekerjaan_id"] for e in expansion_not_ready)
    affected_pekerjaan.update(
        e["pekerjaan_id"] for e in invalid_coefficient if e["pekerjaan_id"] is not None
    )
    for e in missing_price:
        affected_pekerjaan.update(e["affected_pekerjaan"])
    affected_pekerjaan.update(e["pekerjaan_id"] for e in incomplete_planned_allocation)
    affected_pekerjaan.update(e["pekerjaan_id"] for e in allocation_without_volume)
    affected_pekerjaan.update(e["pekerjaan_id"] for e in reference_update_available)

    return {
        "schema_version": SCHEMA_VERSION,
        "expanded_ready": expanded_ready,
        "missing_volume": missing_volume,
        "missing_price": missing_price,
        "invalid_coefficient": invalid_coefficient,
        "expansion_not_ready": expansion_not_ready,
        # Jadwal-derived — live since inc-4a.
        "incomplete_planned_allocation": incomplete_planned_allocation,
        "allocation_without_volume": allocation_without_volume,
        "timeline_stale": timeline_stale,
        # CUSTOM master reference sync (B7b) — advisory, non-blocking.
        "reference_update_available": reference_update_available,
        "pending_signals": list(PENDING_SIGNALS),
        "affected_pekerjaan": sorted(affected_pekerjaan),
        "affected_items": affected_items,
    }
