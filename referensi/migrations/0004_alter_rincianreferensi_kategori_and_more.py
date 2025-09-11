from django.db import migrations, models, transaction
from django.db.models import Count, Q

def normalize_and_dedup(apps, schema_editor):
    RincianReferensi = apps.get_model('referensi', 'RincianReferensi')

    def map_kat(val: str) -> str:
        if not val:
            return "LAIN"
        s = val.strip().lower()
        # TK
        if s in ("tk", "tenaga", "tenaga kerja", "upah", "pekerja", "labor") or s.startswith("tk") or "tenaga" in s or "upah" in s:
            return "TK"
        # BHN
        if s in ("bhn", "bahan", "material", "mat") or "bahan" in s or "material" in s:
            return "BHN"
        # ALT
        if s in ("alt", "alat", "peralatan", "equipment", "equip", "mesin") or "alat" in s or "peralatan" in s or "equipment" in s:
            return "ALT"
        return "LAIN"

    # 1) Normalisasi nilai string + kategori
    with transaction.atomic():
        qs = RincianReferensi.objects.only("id", "kategori", "kode_item", "uraian_item", "satuan_item")
        for r in qs.iterator():
            new_kat = map_kat(r.kategori)
            # penting: field kode_item TIDAK null=True, jadi jangan set None
            kode = (r.kode_item or "").strip()
            ura  = (r.uraian_item or "").strip()
            sat  = (r.satuan_item or "").strip()

            changed = False
            if r.kategori != new_kat:
                r.kategori = new_kat; changed = True
            if r.kode_item != kode:
                r.kode_item = kode; changed = True
            if r.uraian_item != ura:
                r.uraian_item = ura; changed = True
            if r.satuan_item != sat:
                r.satuan_item = sat; changed = True
            if changed:
                r.save(update_fields=["kategori","kode_item","uraian_item","satuan_item"])

    # 2) Dedup setelah mapping (keep id terkecil)
    with transaction.atomic():
        dups = (RincianReferensi.objects
                .values("ahsp_id","kategori","kode_item","uraian_item","satuan_item")
                .annotate(c=Count("id")).filter(c__gt=1))
        for g in dups:
            rows = list(RincianReferensi.objects
                        .filter(ahsp_id=g["ahsp_id"],
                                kategori=g["kategori"],
                                kode_item=g["kode_item"],
                                uraian_item=g["uraian_item"],
                                satuan_item=g["satuan_item"])
                        .order_by("id"))
            # simpan row pertama, hapus sisanya
            for r in rows[1:]:
                r.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("referensi", "0003_alter_ahspreferensi_options_and_more"),
    ]

    operations = [
        # Bersihkan dulu → lalu baru pasang constraint
        migrations.RunPython(normalize_and_dedup, migrations.RunPython.noop),

        # Pasang UniqueConstraint (nama harus sama dengan di Meta models.py)
        migrations.AddConstraint(
            model_name="rincianreferensi",
            constraint=models.UniqueConstraint(
                fields=["ahsp", "kategori", "kode_item", "uraian_item", "satuan_item"],
                name="uniq_rincian_ref_per_ahsp",
            ),
        ),
        # (Opsional) Kalau mau harden DB biar hanya 4 kode ini yang valid:
        # migrations.AddConstraint(
        #     model_name="rincianreferensi",
        #     constraint=models.CheckConstraint(
        #         check=Q(kategori__in=["TK","BHN","ALT","LAIN"]),
        #         name="kategori_is_valid_code",
        #     ),
        # ),
    ]
