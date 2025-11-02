# referensi/management/commands/import_ahsp.py
import os
from django.core.management.base import BaseCommand

from referensi.services.ahsp_parser import parse_excel_dataframe, parse_excel_stream
from referensi.services.import_writer import write_parse_result_to_db


class Command(BaseCommand):
    help = "Import AHSP Referensi dari Excel (wajib kolom 'sumber_ahsp', Decimal kanonik)"

    def add_arguments(self, parser):
        parser.add_argument("excel_path", type=str, help="Path ke file Excel AHSP")

    def handle(self, *args, **kwargs):
        excel_path = kwargs["excel_path"]

        parse_result = None
        streaming_note: str | None = None

        try:
            with open(excel_path, "rb") as handle:
                parse_result = parse_excel_stream(handle)
        except FileNotFoundError:
            streaming_note = f"Berkas '{excel_path}' tidak ditemukan; mencoba fallback pandas."
        except ModuleNotFoundError:
            streaming_note = "Parser streaming membutuhkan paket openpyxl."
        except Exception as exc:
            streaming_note = f"Parser streaming gagal: {exc}"

        if parse_result is None:
            try:
                import pandas as pd  # type: ignore
            except ModuleNotFoundError:
                self.stdout.write(self.style.ERROR("[x] Dependensi pandas belum terpasang."))
                if streaming_note:
                    self.stdout.write(self.style.WARNING(streaming_note))
                return

            try:
                df = pd.read_excel(excel_path, header=0, dtype=str, keep_default_na=False)
            except Exception as exc:
                self.stdout.write(self.style.ERROR(f"[x] Gagal membaca Excel: {exc}"))
                if streaming_note:
                    self.stdout.write(self.style.WARNING(streaming_note))
                return

            parse_result = parse_excel_dataframe(df)
            if streaming_note:
                parse_result.warnings.insert(0, streaming_note)
        elif streaming_note:
            parse_result.warnings.insert(0, streaming_note)

        if parse_result.errors:
            for error in parse_result.errors:
                self.stdout.write(self.style.ERROR(f"[x] {error}"))
            return

        for warning in parse_result.warnings:
            self.stdout.write(self.style.WARNING(f"[!] {warning}"))

        summary = write_parse_result_to_db(
            parse_result,
            os.path.basename(excel_path),
            stdout=self.stdout,
        )

        for detail_error in summary.detail_errors:
            self.stdout.write(self.style.WARNING(detail_error))

        self.stdout.write(
            self.style.SUCCESS(
                "[OK] Import selesai. "
                f"Pekerjaan baru: {summary.jobs_created}, "
                f"Pekerjaan diperbarui: {summary.jobs_updated}, "
                f"Total rincian ditulis: {summary.rincian_written}"
            )
        )
