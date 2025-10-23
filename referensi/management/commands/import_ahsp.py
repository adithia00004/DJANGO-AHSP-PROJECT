# referensi/management/commands/import_ahsp.py
import os
from decimal import Decimal
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from referensi.models import AHSPReferensi, RincianReferensi
from referensi.services.import_utils import (
    normalize_num,
    norm_text,
    pick_first_col,
)


class Command(BaseCommand):
    help = "Import AHSP Referensi dari Excel (wajib kolom 'sumber_ahsp', Decimal kanonik)"

    def add_arguments(self, parser):
        parser.add_argument("excel_path", type=str, help="Path ke file Excel AHSP")

    def handle(self, *args, **kwargs):
        excel_path = kwargs["excel_path"]

        # Baca sebagai string agar tidak ada auto-konversi koma/titik.
        # Biarkan pd.read_excel yang melempar jika file tidak ada – ini
        # kompatibel dengan test yang memonkeypatch read_excel.
        try:
            df = pd.read_excel(excel_path, header=0, dtype=str, keep_default_na=False)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ File tidak ditemukan: {excel_path}"))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Gagal membaca Excel: {e}"))
            return

        # Wajib: sumber_ahsp, kode_ahsp, nama_ahsp
        col_sumber = pick_first_col(df, ["sumber_ahsp"])  # standar wajib
        col_kode = pick_first_col(df, ["kode_ahsp", "kode"])
        col_nama = pick_first_col(df, ["nama_ahsp", "nama"])
        col_kategori = pick_first_col(df, ["kategori"])
        col_kode_item = pick_first_col(df, ["kode_item_lookup", "kode_item"])
        col_item = pick_first_col(df, ["item", "uraian_item"])
        col_satuan = pick_first_col(df, ["satuan", "satuan_item"])
        col_koef = pick_first_col(df, ["koefisien", "koef", "qty"])

        missing = [
            n
            for n, c in [
                ("sumber_ahsp", col_sumber),
                ("kode_ahsp", col_kode),
                ("nama_ahsp", col_nama),
            ]
            if c is None
        ]
        if missing:
            self.stdout.write(self.style.ERROR(f"❌ Kolom wajib hilang: {', '.join(missing)}"))
            self.stdout.write(
                "   Pastikan header Excel minimal: sumber_ahsp, kode_ahsp, nama_ahsp"
            )
            return

        total_pekerjaan = 0
        total_rincian = 0

        current_src = None
        current_pekerjaan = None

        with transaction.atomic():
            for i, row in df.iterrows():
                sumber_ahsp = norm_text(row.get(col_sumber, ""))
                if sumber_ahsp:
                    current_src = sumber_ahsp  # forward-fill ke baris berikutnya
                kode = norm_text(row.get(col_kode, ""))
                nama = norm_text(row.get(col_nama, ""))

                # Header pekerjaan: ada kode & nama
                if kode and nama:
                    if not current_src:
                        raise ValueError(
                            f"Baris {i}: 'sumber_ahsp' kosong untuk pekerjaan {kode} - {nama}"
                        )

                    # Upsert per (sumber_ahsp, kode_ahsp) dan REPLACE rincian
                    existing = AHSPReferensi.objects.filter(
                        sumber=current_src, kode_ahsp=kode
                    ).first()
                    if existing:
                        current_pekerjaan = existing
                        if existing.nama_ahsp != nama:
                            existing.nama_ahsp = nama
                            existing.save(update_fields=["nama_ahsp"])
                        # reset rincian (replace semantics)
                        RincianReferensi.objects.filter(ahsp=current_pekerjaan).delete()
                    else:
                        current_pekerjaan = AHSPReferensi.objects.create(
                            kode_ahsp=kode,
                            nama_ahsp=nama,
                            satuan="",
                            sumber=current_src,
                            source_file=os.path.basename(excel_path),
                        )
                        total_pekerjaan += 1

                    # Info log ringan
                    self.stdout.write(f"➡️  [{current_src}] {kode} - {nama}")
                    continue  # lanjut ke baris berikut (rincian)

                # Rincian item
                if not current_pekerjaan:
                    continue  # lewati noise sebelum header pertama

                kategori = norm_text(row.get(col_kategori, "")) if col_kategori else ""
                kode_item = norm_text(row.get(col_kode_item, "")) if col_kode_item else ""
                uraian_item = norm_text(row.get(col_item, "")) if col_item else ""
                satuan_item = norm_text(row.get(col_satuan, "")) if col_satuan else ""
                koef = normalize_num(row.get(col_koef, "")) if col_koef else None
                if koef is None:
                    koef = Decimal("0")

                if kategori and uraian_item:
                    try:
                        # Dukung dua skema field model
                        fields_a = dict(
                            ahsp=current_pekerjaan,
                            kategori=kategori,
                            kode_item=kode_item,
                            uraian_item=uraian_item,
                            satuan_item=satuan_item,
                            koefisien=koef,
                        )
                        fields_b = dict(
                            ahsp=current_pekerjaan,
                            kategori=kategori,
                            kode_item_lookup=kode_item,
                            item=uraian_item,
                            satuan=satuan_item,
                            koefisien=koef,
                        )
                        if hasattr(RincianReferensi, "uraian_item"):
                            RincianReferensi.objects.create(**fields_a)
                        else:
                            RincianReferensi.objects.create(**fields_b)
                        total_rincian += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"⚠️  Gagal import baris {i}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Import selesai. Pekerjaan baru: {total_pekerjaan}, Total rincian ditulis: {total_rincian}"
            )
        )

