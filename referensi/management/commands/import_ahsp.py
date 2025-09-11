import os
import pandas as pd
from django.core.management.base import BaseCommand
from referensi.models import AHSPReferensi, RincianReferensi

class Command(BaseCommand):
    help = 'Import data AHSP SNI 2025 dari file Excel ke database'

    def add_arguments(self, parser):
        parser.add_argument('excel_path', type=str, help='Path ke file Excel SNI 2025')

    def handle(self, *args, **kwargs):
        excel_path = kwargs['excel_path']

        if not os.path.exists(excel_path):
            self.stdout.write(self.style.ERROR(f'❌ File tidak ditemukan: {excel_path}'))
            return

        self.stdout.write(self.style.NOTICE(f'📘 Membaca file: {excel_path}'))
        df = pd.read_excel(excel_path, header=0)  # baris 0 = nama kolom

        total_pekerjaan = 0
        total_rincian = 0
        current_kode = None
        current_pekerjaan = None

        for i, row in df.iterrows():
            kode = str(row['kode_ahsp']).strip() if pd.notna(row['kode_ahsp']) else ''
            nama = str(row['nama_ahsp']).strip() if pd.notna(row['nama_ahsp']) else ''

            if kode != current_kode and kode and nama:
                # Buat pekerjaan baru
                current_pekerjaan = AHSPReferensi.objects.create(
                    kode_ahsp=kode,
                    nama_ahsp=nama,
                    satuan='',  # Belum tersedia di file
                    sumber='AHSP 2025',
                    source_file=os.path.basename(excel_path),
                )
                current_kode = kode
                total_pekerjaan += 1
                self.stdout.write(f'🛠️  Pekerjaan: {kode} - {nama}')

            if current_pekerjaan and pd.notna(row['kategori']) and pd.notna(row['item']):
                try:
                    RincianReferensi.objects.create(
                        ahsp=current_pekerjaan,
                        kategori=str(row['kategori']).strip(),
                        kode_item_lookup=str(row['kode_item_lookup']).strip(),
                        item=str(row['item']).strip(),
                        satuan=str(row['satuan']).strip() if pd.notna(row['satuan']) else '',
                        koefisien=float(row['koefisien']) if pd.notna(row['koefisien']) else 0,
                    )
                    total_rincian += 1
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f"⚠️ Gagal import baris {i}: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f'✅ Import selesai. Total pekerjaan: {total_pekerjaan}, Total rincian: {total_rincian}'
        ))
