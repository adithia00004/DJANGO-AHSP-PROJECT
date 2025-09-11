from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from referensi.models import RincianReferensi

class Command(BaseCommand):
    help = "Normalize kategori (TK/BHN/ALT/LAIN), trim string, dan dedup RincianReferensi."

    def handle(self, *args, **options):
        self.stdout.write("Normalizing & deduplicating RincianReferensi...")

        def map_kat(val: str) -> str:
            if not val: return "LAIN"
            s = val.strip().lower()
            if s in ("tk","tenaga","tenaga kerja","upah","pekerja","labor") or s.startswith("tk") or "tenaga" in s or "upah" in s: return "TK"
            if s in ("bhn","bahan","material","mat") or "bahan" in s or "material" in s: return "BHN"
            if s in ("alt","alat","peralatan","equipment","equip","mesin") or "alat" in s or "peralatan" in s or "equipment" in s: return "ALT"
            return "LAIN"

        with transaction.atomic():
            for r in RincianReferensi.objects.only("id","kategori","kode_item","uraian_item","satuan_item").iterator():
                new_kat = map_kat(r.kategori)
                kode = (r.kode_item or "").strip()
                ura  = (r.uraian_item or "").strip()
                sat  = (r.satuan_item or "").strip()
                changed = False
                if r.kategori != new_kat: r.kategori = new_kat; changed = True
                if r.kode_item != kode:   r.kode_item = kode;   changed = True
                if r.uraian_item != ura:  r.uraian_item = ura;  changed = True
                if r.satuan_item != sat:  r.satuan_item = sat;  changed = True
                if changed:
                    r.save(update_fields=["kategori","kode_item","uraian_item","satuan_item"])

            dups = (RincianReferensi.objects
                    .values("ahsp_id","kategori","kode_item","uraian_item","satuan_item")
                    .annotate(c=Count("id")).filter(c__gt=1))
            removed = 0
            for g in dups:
                rows = list(RincianReferensi.objects
                            .filter(ahsp_id=g["ahsp_id"],
                                    kategori=g["kategori"],
                                    kode_item=g["kode_item"],
                                    uraian_item=g["uraian_item"],
                                    satuan_item=g["satuan_item"])
                            .order_by("id"))
                for r in rows[1:]:
                    r.delete()
                    removed += 1

        self.stdout.write(self.style.SUCCESS(f"Done. Removed duplicates: {removed}"))
