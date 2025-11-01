# referensi/management/commands/import_ahsp.py
import os
import pandas as pd
from django.core.management.base import BaseCommand

from referensi.services.ahsp_parser import parse_excel_dataframe
from referensi.services.import_writer import write_parse_result_to_db


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

        parse_result = parse_excel_dataframe(df)

        if parse_result.errors:
            for error in parse_result.errors:
                self.stdout.write(self.style.ERROR(f"❌ {error}"))
            return

        for warning in parse_result.warnings:
            self.stdout.write(self.style.WARNING(f"⚠️  {warning}"))

        summary = write_parse_result_to_db(
            parse_result,
            os.path.basename(excel_path),
            stdout=self.stdout,
        )

        for detail_error in summary.detail_errors:
            self.stdout.write(self.style.WARNING(detail_error))

        self.stdout.write(
            self.style.SUCCESS(
                "✅ Import selesai. "
                f"Pekerjaan baru: {summary.jobs_created}, "
                f"Pekerjaan diperbarui: {summary.jobs_updated}, "
                f"Total rincian ditulis: {summary.rincian_written}"
            )
        )

