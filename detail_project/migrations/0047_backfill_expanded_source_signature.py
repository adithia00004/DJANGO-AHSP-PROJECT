"""WP-B4 inc-4b: backfill DetailAHSPExpanded.source_signature for existing rows.

Computes the content signature from each expanded row's source_detail so that
post-deploy there are no NULL signatures and readiness can rely on signature-based
stale detection. Logic is inlined (frozen) — must match
``detail_project.readiness.source_signature`` at the time of writing.
"""
import hashlib
from decimal import Decimal

from django.db import migrations

_KOEF_QUANT = Decimal("1.000000000000")


def _sig(kategori, kode, koefisien, ref_pekerjaan_id, ref_ahsp_id):
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
    ])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def backfill(apps, schema_editor):
    Expanded = apps.get_model("detail_project", "DetailAHSPExpanded")
    qs = (
        Expanded.objects.select_related("source_detail")
        .filter(source_signature__isnull=True)
    )
    batch = []
    for obj in qs.iterator(chunk_size=1000):
        sd = obj.source_detail
        if sd is None:
            continue
        obj.source_signature = _sig(
            sd.kategori, sd.kode, sd.koefisien,
            sd.ref_pekerjaan_id, sd.ref_ahsp_id,
        )
        batch.append(obj)
        if len(batch) >= 1000:
            Expanded.objects.bulk_update(batch, ["source_signature"])
            batch = []
    if batch:
        Expanded.objects.bulk_update(batch, ["source_signature"])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("detail_project", "0046_add_expanded_source_signature"),
    ]

    operations = [
        migrations.RunPython(backfill, noop),
    ]
