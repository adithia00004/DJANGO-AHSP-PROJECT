"""Repair and strengthen WP-B4 expanded source signatures.

Migration 0047 stamped the current raw value on every legacy expanded row. For
rows whose raw source was already newer than its expansion, that could hide a
stale condition. This migration preserves those known-stale groups as NULL so
runtime readiness uses its timestamp fallback, and upgrades fresh groups to the
signature format that also includes harga_item_id.
"""
import hashlib
from decimal import Decimal

from django.db import migrations

_KOEF_QUANT = Decimal("1.000000000000")


def _sig(
    kategori,
    kode,
    koefisien,
    ref_pekerjaan_id,
    ref_ahsp_id,
    harga_item_id,
):
    try:
        koef = Decimal(koefisien if koefisien is not None else 0).quantize(
            _KOEF_QUANT
        )
    except Exception:
        koef = Decimal("0").quantize(_KOEF_QUANT)
    raw = "|".join(
        [
            str(kategori or ""),
            str(kode or ""),
            f"{koef}",
            str(ref_pekerjaan_id or ""),
            str(ref_ahsp_id or ""),
            str(harga_item_id or ""),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def repair_backfill(apps, schema_editor):
    Expanded = apps.get_model("detail_project", "DetailAHSPExpanded")

    current_source_id = None
    group = []
    pending = []

    def flush(rows):
        if not rows:
            return
        source = rows[0].source_detail
        newest_expanded = max(row.updated_at for row in rows)
        known_stale = (
            source.updated_at is not None
            and newest_expanded is not None
            and newest_expanded < source.updated_at
        )
        signature = None
        if not known_stale:
            signature = _sig(
                source.kategori,
                source.kode,
                source.koefisien,
                source.ref_pekerjaan_id,
                source.ref_ahsp_id,
                source.harga_item_id,
            )
        for row in rows:
            row.source_signature = signature
        pending.extend(rows)
        if len(pending) >= 1000:
            Expanded.objects.bulk_update(
                pending, ["source_signature"], batch_size=1000
            )
            pending.clear()

    queryset = (
        Expanded.objects.select_related("source_detail")
        .order_by("source_detail_id", "id")
    )
    for obj in queryset.iterator(chunk_size=1000):
        if current_source_id is None:
            current_source_id = obj.source_detail_id
        if obj.source_detail_id != current_source_id:
            flush(group)
            group = []
            current_source_id = obj.source_detail_id
        group.append(obj)
    flush(group)
    if pending:
        Expanded.objects.bulk_update(
            pending, ["source_signature"], batch_size=1000
        )


class Migration(migrations.Migration):

    dependencies = [
        ("detail_project", "0047_backfill_expanded_source_signature"),
    ]

    operations = [
        migrations.RunPython(repair_backfill, migrations.RunPython.noop),
    ]
