"""WP-B7a: backfill DetailAHSPProject.ref_snapshot_signature for existing bundles.

For every raw bundle row that references a master AHSP (``ref_ahsp_id`` set), stamp
the master's current content signature and mark it synced "now". This assumes
existing projects are in sync with the master at deploy time, so the new
``reference_update_available`` signal only fires for changes made AFTER deploy
(no false-positive flood on first load). Logic is inlined (frozen) — must match
``detail_project.readiness.master_reference_signature`` at the time of writing.
"""
import hashlib
from decimal import Decimal

from django.db import migrations
from django.utils import timezone

_KOEF_QUANT = Decimal("1.000000000000")


def _master_sig(RincianReferensi, ref_ahsp_id):
    if not ref_ahsp_id:
        return None
    rows = list(
        RincianReferensi.objects.filter(ahsp_id=ref_ahsp_id)
        .values("kategori", "kode_item", "koefisien", "satuan_item", "uraian_item")
        .order_by("kategori", "kode_item", "uraian_item", "satuan_item")
    )
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


def backfill(apps, schema_editor):
    Detail = apps.get_model("detail_project", "DetailAHSPProject")
    RincianReferensi = apps.get_model("referensi", "RincianReferensi")
    now = timezone.now()
    qs = Detail.objects.filter(ref_ahsp_id__isnull=False, ref_snapshot_signature__isnull=True)
    batch = []
    for obj in qs.iterator(chunk_size=1000):
        sig = _master_sig(RincianReferensi, obj.ref_ahsp_id)
        if sig is None:
            continue
        obj.ref_snapshot_signature = sig
        obj.ref_synced_at = now
        batch.append(obj)
        if len(batch) >= 1000:
            Detail.objects.bulk_update(batch, ["ref_snapshot_signature", "ref_synced_at"])
            batch = []
    if batch:
        Detail.objects.bulk_update(batch, ["ref_snapshot_signature", "ref_synced_at"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("detail_project", "0049_add_ref_snapshot_signature"),
        # Latest referensi migration so the frozen RincianReferensi has its
        # final field names (kode_item/uraian_item/satuan_item renamed post-0001).
        ("referensi", "0024_alter_ahspimportstaging_segment_type"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
