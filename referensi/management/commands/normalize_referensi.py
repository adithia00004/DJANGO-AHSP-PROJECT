from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from referensi.models import RincianReferensi

# PHASE 2: Use KategoriNormalizer for single source of truth (eliminates code duplication)
from referensi.services.normalizers import KategoriNormalizer


class Command(BaseCommand):
    help = "Normalize kategori (TK/BHN/ALT/LAIN), trim string, dan dedup RincianReferensi."

    def handle(self, *args, **options):
        self.stdout.write("Normalizing & deduplicating RincianReferensi...")

        with transaction.atomic():
            for r in RincianReferensi.objects.only("id","kategori","kode_item","uraian_item","satuan_item").iterator():
                # PHASE 2: Use KategoriNormalizer instead of inline map_kat function
                new_kat = KategoriNormalizer.normalize(r.kategori)
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
