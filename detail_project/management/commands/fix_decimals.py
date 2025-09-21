# detail_project/management/commands/fix_decimals.py
from __future__ import annotations
from decimal import Decimal
from typing import Iterable, Optional

from django.core.management.base import BaseCommand
from django.db import transaction

from detail_project.models import DetailAHSPProject, VolumePekerjaan, HargaItemProject
from detail_project.numeric import DECIMAL_SPEC, quantize_half_up

class Command(BaseCommand):
    help = (
        "Scan & (opsional) perbaiki nilai numerik yang diduga salah skala.\n"
        "Default DRY-RUN (tidak menulis). Gunakan --apply untuk benar-benar menulis."
    )

    def add_arguments(self, parser):
        parser.add_argument("--project", type=int, help="Filter: project_id spesifik")
        parser.add_argument("--model", choices=["koef", "vol", "harga", "all"], default="koef",
                            help="Target model/kolom (default: koef)")

        # Ambang deteksi sederhana (threshold)
        parser.add_argument("--koef-min", type=str, default="1000",
                            help="Ambang deteksi koefisien (Decimal). Default=1000")
        parser.add_argument("--vol-min", type=str, default="1000000",  # sangat besar agar tidak tersentuh tanpa niat
                            help="Ambang deteksi volume (Decimal). Default=1,000,000")
        parser.add_argument("--harga-min", type=str, default="1000000000000", # 1e12
                            help="Ambang deteksi harga (Decimal). Default sangat besar")

        # Faktor koreksi (kalikan nilai lama dengan faktor ini)
        parser.add_argument("--koef-factor", type=str, default=None,
                            help="Faktor koreksi koef (mis. 0.0001 untuk 27275 -> 2.7275)")
        parser.add_argument("--vol-factor", type=str, default=None,
                            help="Faktor koreksi volume")
        parser.add_argument("--harga-factor", type=str, default=None,
                            help="Faktor koreksi harga")

        # Mode eksekusi
        parser.add_argument("--apply", action="store_true", help="Terapkan perubahan (tanpa ini hanya DRY-RUN)")
        parser.add_argument("--limit", type=int, default=50, help="Batas preview yang ditampilkan")
        parser.add_argument("--quiet", action="store_true", help="Minimalkan output")

    def _to_dec(self, s: Optional[str]) -> Optional[Decimal]:
        if s is None:
            return None
        try:
            return Decimal(s)
        except Exception:
            return None

    def handle(self, *args, **opts):
        project_id = opts.get("project")
        model = opts["model"]
        apply_changes = opts["apply"]
        quiet = opts["quiet"]
        limit = opts["limit"]

        # ambang
        koef_min = self._to_dec(opts["koef_min"]) or Decimal("1000")
        vol_min = self._to_dec(opts["vol_min"]) or Decimal("1000000")
        harga_min = self._to_dec(opts["harga_min"]) or Decimal("1000000000000")

        # faktor
        koef_factor = self._to_dec(opts["koef_factor"])
        vol_factor = self._to_dec(opts["vol_factor"])
        harga_factor = self._to_dec(opts["harga_factor"])

        total_preview = 0
        total_fix = 0

        if model in ("koef", "all"):
            fixed, prev = self._process_koef(project_id, koef_min, koef_factor, apply_changes, limit, quiet)
            total_fix += fixed
            total_preview += prev

        if model in ("vol", "all"):
            fixed, prev = self._process_vol(project_id, vol_min, vol_factor, apply_changes, limit, quiet)
            total_fix += fixed
            total_preview += prev

        if model in ("harga", "all"):
            fixed, prev = self._process_harga(project_id, harga_min, harga_factor, apply_changes, limit, quiet)
            total_fix += fixed
            total_preview += prev

        if not quiet:
            self.stdout.write(self.style.SUCCESS(
                f"Done. Previewed={total_preview}, Fixed={total_fix}, Apply={apply_changes}"
            ))

    def _process_koef(self, project_id: Optional[int], min_val: Decimal,
                      factor: Optional[Decimal], apply_changes: bool, limit: int, quiet: bool):
        qs = DetailAHSPProject.objects.all()
        if project_id:
            qs = qs.filter(project_id=project_id)
        qs = qs.order_by("project_id", "pekerjaan_id", "kode")

        dp = DECIMAL_SPEC["KOEF"].dp
        preview = 0
        fixed = 0

        # Kriteria kandidat: koefisien >= ambang
        candidates = qs.filter(koefisien__gte=min_val)

        if not quiet:
            self.stdout.write(f"[KOEF] Candidates: {candidates.count()} (min>={min_val})"
                              + (f", factor={factor}" if factor else ", factor=None (scan only)"))

        with transaction.atomic():
            for obj in candidates.iterator(chunk_size=1000):
                old = obj.koefisien
                if not quiet and preview < limit:
                    self.stdout.write(f" - pid={obj.project_id} pkj={obj.pekerjaan_id} kode={obj.kode} old={old}")

                if apply_changes and factor:
                    new_val = quantize_half_up(old * factor, dp)
                    obj.koefisien = new_val
                    obj.save(update_fields=["koefisien", "updated_at"])
                    fixed += 1

                preview += 1

            if not apply_changes:
                transaction.set_rollback(True)  # DRY-RUN

        return fixed, preview

    def _process_vol(self, project_id: Optional[int], min_val: Decimal,
                     factor: Optional[Decimal], apply_changes: bool, limit: int, quiet: bool):
        qs = VolumePekerjaan.objects.all()
        if project_id:
            qs = qs.filter(project_id=project_id)
        qs = qs.order_by("project_id", "pekerjaan_id")

        dp = DECIMAL_SPEC["VOL"].dp
        preview = 0
        fixed = 0

        candidates = qs.filter(quantity__gte=min_val)

        if not quiet:
            self.stdout.write(f"[VOL] Candidates: {candidates.count()} (min>={min_val})"
                              + (f", factor={factor}" if factor else ", factor=None (scan only)"))

        with transaction.atomic():
            for obj in candidates.iterator(chunk_size=1000):
                old = obj.quantity
                if not quiet and preview < limit:
                    self.stdout.write(f" - pid={obj.project_id} pkj={obj.pekerjaan_id} old={old}")

                if apply_changes and factor:
                    new_val = quantize_half_up(old * factor, dp)
                    obj.quantity = new_val
                    obj.save(update_fields=["quantity", "updated_at"])
                    fixed += 1

                preview += 1

            if not apply_changes:
                transaction.set_rollback(True)

        return fixed, preview

    def _process_harga(self, project_id: Optional[int], min_val: Decimal,
                       factor: Optional[Decimal], apply_changes: bool, limit: int, quiet: bool):
        qs = HargaItemProject.objects.all()
        if project_id:
            qs = qs.filter(project_id=project_id)
        qs = qs.order_by("project_id", "kode_item")

        dp = DECIMAL_SPEC["HARGA"].dp
        preview = 0
        fixed = 0

        candidates = qs.filter(harga_satuan__isnull=False, harga_satuan__gte=min_val)

        if not quiet:
            self.stdout.write(f"[HARGA] Candidates: {candidates.count()} (min>={min_val})"
                              + (f", factor={factor}" if factor else ", factor=None (scan only)"))

        with transaction.atomic():
            for obj in candidates.iterator(chunk_size=1000):
                old = obj.harga_satuan
                if not quiet and preview < limit:
                    self.stdout.write(f" - pid={obj.project_id} kode_item={obj.kode_item} old={old}")

                if apply_changes and factor:
                    new_val = quantize_half_up(old * factor, dp)
                    obj.harga_satuan = new_val
                    obj.save(update_fields=["harga_satuan", "updated_at"])
                    fixed += 1

                preview += 1

            if not apply_changes:
                transaction.set_rollback(True)

        return fixed, preview
