# referensi/management/commands/import_ahsp.py
import os
from decimal import Decimal
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from referensi.models import AHSPReferensi, RincianReferensi

# Helper dari services (akan kita buat di langkah 2)
from referensi.services.import_utils import (
    normalize_num,
    norm_text,
    pick_first_col,
)

class Command(BaseCommand):
    help = "Import data AHSP SNI 2025 dari file Excel ke database (locale-safe, Decimal)."

    def add_arguments(self, parser):
        parser.add_argument("excel_path", type=str, help="Path ke file Excel SNI 2025")

    def handle(self, *args, **kwargs):
        excel_path = kwargs["excel_path"]

        if not os.path.exists(excel_path):
            self.stdout.write(self.style.ERROR(f"❌ File tidak ditemukan: {excel_path}"))
            return

        self.stdout.write(self.style.NOTICE(f"📘 Membaca file: {excel_path}"))

        # BACA sebagai STRING agar tidak ada auto-parsing koma/titik oleh pandas
        # keep_default_na=False agar sel kosong jadi '' (bukan NaN)
        df = pd.read_excel(excel_path, header=0, dtype=str, keep_default_na=False)

        # Map alias kolom Excel → nama standar di DataFrame
        # (bolehkan beberapa kemungkinan header)
        col_kode_ahsp = pick_first_col(df, ["kode_ahsp", "kode", "kode_pekerjaan"])
        col_nama_ahsp = pick_first_col(df, ["nama_ahsp", "nama", "uraian_pekerjaan"])
        col_kategori  = pick_first_col(df, ["kategori", "kat", "jenis"])
        col_kode_item = pick_first_col(df, ["kode_item_lookup", "kode_item", "kode_material", "kode_bahan"])
        col_item      = pick_first_col(df, ["item", "uraian_item", "uraian", "deskripsi"])
        col_satuan    = pick_first_col(df, ["satuan", "satuan_item", "unit"])
        col_koef      = pick_first_col(df, ["koefisien", "koef", "qty", "koef_item"])

        # Validasi minimum
        required = [col_kode_ahsp, col_nama_ahsp]
        if any(c is None for c in required):
            missing = [("kode_ahsp", col_kode_ahsp), ("nama_ahsp", col_nama_ahsp)]
            missing = [exp for exp, got in missing if got is None]
            self.stdout.write(self.style.ERROR(f"❌ Kolom wajib hilang di Excel: {', '.join(missing)}"))
            return

        total_pekerjaan = 0
        total_rincian = 0
        current_kode = None
        current_pekerjaan = None

        # Transaksi agar konsisten
        with transaction.atomic():
            for i, row in df.iterrows():
                kode = norm_text(row.get(col_kode_ahsp, ""))
                nama = norm_text(row.get(col_nama_ahsp, ""))

                # Deteksi baris pekerjaan (header kelompok)
                if kode and nama and kode != current_kode:
                    current_pekerjaan = AHSPReferensi.objects.create(
                        kode_ahsp=kode,
                        nama_ahsp=nama,
                        # kolom lain disesuaikan dengan modelmu
                        satuan="",
                        sumber="AHSP 2025",
                        source_file=os.path.basename(excel_path),
                    )
                    current_kode = kode
                    total_pekerjaan += 1
                    self.stdout.write(f"🛠️  Pekerjaan: {kode} - {nama}")

                # Baris rincian (item)
                if not current_pekerjaan:
                    continue  # belum ada pekerjaan aktif

                kategori = norm_text(row.get(col_kategori, "")) if col_kategori else ""
                kode_item = norm_text(row.get(col_kode_item, "")) if col_kode_item else ""
                uraian_item = norm_text(row.get(col_item, "")) if col_item else ""
                satuan_item = norm_text(row.get(col_satuan, "")) if col_satuan else ""
                koef = normalize_num(row.get(col_koef, "")) if col_koef else None
                if koef is None:
                    # Jika kosong atau tak valid, normalisasikan ke Decimal(0)
                    koef = Decimal("0")

                # Minimal syarat: ada kategori & uraian item (boleh kosong kode/satuan)
                if kategori and uraian_item:
                    try:
                        # Kompatibilitas nama field: dukung dua skema model
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
                        # Jika model punya atribut 'uraian_item', pakai fields_a; kalau tidak, fallback fields_b
                        if hasattr(RincianReferensi, "uraian_item"):
                            RincianReferensi.objects.create(**fields_a)
                        else:
                            RincianReferensi.objects.create(**fields_b)
                        total_rincian += 1
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"⚠️ Gagal import baris {i}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"✅ Import selesai. Total pekerjaan: {total_pekerjaan}, Total rincian: {total_rincian}"
        ))
