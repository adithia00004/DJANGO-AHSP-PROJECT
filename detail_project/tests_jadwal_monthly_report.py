"""Laporan Bulanan/Mingguan Jadwal — regresi review 2026-09-27.

Mengunci:
- jumlah periode = periode nyata proyek (tanpa minimum 12 minggu / 3 bulan),
  satu sumber untuk modal export, validasi backend, dan kolom adapter;
- "Kumulatif Bulan Lalu" = W1..akhir bulan lalu (bukan hanya bulan lalu),
  sehingga TOTAL tabel Rincian = Akumulasi di Ringkasan Progress;
- PDF: tanpa halaman kosong, angka id-ID tidak terpotong, satuan terisi,
  tanpa jabatan "Direktur" karangan, label identitas sesuai isinya.
"""
import base64
import re
import zlib
from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from dashboard.models import Project
from detail_project.exports.errors import ExportValidationError
from detail_project.exports.export_manager import ExportManager
from detail_project.exports.jadwal_pekerjaan_adapter import JadwalPekerjaanExportAdapter
from detail_project.exports.pdf_exporter import PDFExporter, SegmentMarker
from detail_project.models import (
    DetailAHSPExpanded,
    DetailAHSPProject,
    HargaItemProject,
    Klasifikasi,
    Pekerjaan,
    PekerjaanProgressWeekly,
    SubKlasifikasi,
    VolumePekerjaan,
)
from detail_project.timeline_utils import project_report_period_counts


class _MonthlyFixtureMixin:
    """Proyek 12 minggu (Sen 5 Jan - Min 29 Mar 2026).

    - Beton: harga besar (bobot dominan), realisasi 50% W1 + 50% W2.
    - Bekisting: realisasi 10%/minggu W3..W12, volume 1.234,5.
    """

    START = date(2026, 1, 5)
    END = date(2026, 3, 29)

    def setUp(self):
        self.owner = get_user_model().objects.create_user("wp-monthly-owner", password="x")
        self.project = Project.objects.create(
            owner=self.owner,
            nama="Monthly PDF",
            sumber_dana="APBD",
            lokasi_project="Lokasi",
            nama_client="Owner Bulanan",
            anggaran_owner=Decimal("1000000.00"),
            nama_kontraktor="Kontraktor Bulanan",
            nama_konsultan_pengawas="Pengawas Bulanan",
            tanggal_mulai=self.START,
            tanggal_selesai=self.END,
            week_start_day=0,
            week_end_day=6,
        )
        klas = Klasifikasi.objects.create(project=self.project, name="K", ordering_index=1)
        self.sub = SubKlasifikasi.objects.create(
            project=self.project, klasifikasi=klas, name="S", ordering_index=1,
        )
        self.beton = self._make_pekerjaan("Beton", "m3", Decimal("200000"), Decimal("30000"), 1)
        # Bobot ±83% (beton) / ±17% (bekisting) — keduanya ikut menentukan total.
        self.bekisting = self._make_pekerjaan("Bekisting", "m2", Decimal("1000000"), Decimal("1234.5"), 2)

        for wk in range(1, 13):
            planned_beton = actual_beton = Decimal("50") if wk <= 2 else Decimal("0")
            bekisting_value = Decimal("10") if wk >= 3 else Decimal("0")
            for pek, planned, actual in (
                (self.beton, planned_beton, actual_beton),
                (self.bekisting, bekisting_value, bekisting_value),
            ):
                start = self.START + timedelta(days=(wk - 1) * 7)
                PekerjaanProgressWeekly.objects.create(
                    project=self.project,
                    pekerjaan=pek,
                    week_number=wk,
                    week_start_date=start,
                    week_end_date=start + timedelta(days=6),
                    planned_proportion=planned,
                    actual_proportion=actual,
                )

    def _make_pekerjaan(self, uraian, satuan, harga_satuan, volume, ordering):
        pek = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.sub,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode=f"P-{ordering:03d}",
            snapshot_uraian=uraian,
            snapshot_satuan=satuan,
            ordering_index=ordering,
        )
        item = HargaItemProject.objects.create(
            project=self.project,
            kode_item=f"BHN-{ordering}",
            kategori="BHN",
            uraian=f"Bahan {uraian}",
            satuan=satuan,
            harga_satuan=harga_satuan,
        )
        src = DetailAHSPProject.objects.create(
            project=self.project, pekerjaan=pek, harga_item=item, kategori="BHN",
            kode=f"BHN-{ordering}", uraian="B", satuan=satuan, koefisien=Decimal("1.000000"),
        )
        DetailAHSPExpanded.objects.create(
            project=self.project, pekerjaan=pek, source_detail=src, harga_item=item,
            kategori="BHN", kode=f"BHN-{ordering}", uraian="B", satuan=satuan,
            koefisien=Decimal("1.000000"), expansion_depth=0,
        )
        VolumePekerjaan.objects.create(project=self.project, pekerjaan=pek, quantity=volume)
        return pek

    def _monthly_pdf_pages(self, month):
        response = ExportManager(self.project, self.owner).export_jadwal_professional(
            "pdf", report_type="monthly", months=[month],
        )
        return pdf_page_texts(response.content)


_PDF_STREAM = re.compile(rb"/Filter \[ /ASCII85Decode /FlateDecode \] /Length (\d+)\s*>>\s*stream\r?\n")
_PDF_TEXT = re.compile(rb"\(((?:\\.|[^\\)])*)\)\s*Tj")
_PDF_ESCAPE = re.compile(rb"\\(.)")


def pdf_page_streams(content: bytes) -> list[bytes]:
    """Content stream per halaman (terdekompresi) dari PDF ReportLab.

    ReportLab menulis satu content stream (ASCII85+Flate) per halaman, urut
    halaman — tanpa perlu dependensi PDF reader.
    """
    streams = []
    for match in _PDF_STREAM.finditer(content):
        # Batas stream dari penanda akhir ASCII85 '~>' (bukan /Length, yang tidak
        # selalu cocok dengan byte sebenarnya); dekompresi toleran.
        end = content.index(b"~>", match.end())
        encoded = content[match.end():end].strip()
        data = zlib.decompressobj().decompress(base64.a85decode(encoded, adobe=False))
        if b"BT" in data:
            streams.append(data)
    return streams


def pdf_page_texts(content: bytes) -> list[str]:
    """Teks per halaman; teks ada di operator ``(...) Tj``."""
    return [
        "\n".join(_PDF_ESCAPE.sub(rb"\1", m.group(1)).decode("latin-1") for m in _PDF_TEXT.finditer(data))
        for data in pdf_page_streams(content)
    ]


class ReportPeriodCountTests(_MonthlyFixtureMixin, TestCase):
    def test_counts_follow_real_project_duration(self):
        self.assertEqual(project_report_period_counts(self.project), (12, 3))

    def test_short_project_has_no_artificial_minimum(self):
        # Kasus proyek 217: 41 hari mulai Senin = 6 minggu = 2 bulan (bukan 12/3).
        self.project.tanggal_mulai = date(2026, 8, 10)
        self.project.tanggal_selesai = date(2026, 9, 19)
        self.assertEqual(project_report_period_counts(self.project), (6, 2))

    def test_partial_first_week_counts_as_a_week(self):
        # Mulai Kamis: 1-4 Jan adalah minggu ke-1 tersendiri -> 5 minggu, bukan ceil(28/7)=4.
        self.project.tanggal_mulai = date(2026, 1, 1)
        self.project.tanggal_selesai = date(2026, 1, 28)
        self.assertEqual(project_report_period_counts(self.project), (5, 2))

    def test_adapter_weekly_columns_match_period_count(self):
        self.project.tanggal_mulai = date(2026, 1, 1)
        self.project.tanggal_selesai = date(2026, 1, 28)
        self.project.save()
        # Tanpa data progress (yang bisa memperpanjang tanggal akhir): murni tanggal proyek.
        PekerjaanProgressWeekly.objects.filter(project=self.project).delete()
        data = JadwalPekerjaanExportAdapter(self.project).get_monthly_comparison_data(1)
        self.assertEqual(len(data["all_weekly_columns"]), 5)

    def test_jadwal_page_offers_only_real_periods(self):
        self.project.tanggal_selesai = date(2026, 2, 15)  # 6 minggu
        self.project.save()
        self.client.force_login(self.owner)
        response = self.client.get(reverse("detail_project:jadwal_pekerjaan", args=[self.project.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_weeks"], 6)
        self.assertEqual(response.context["total_months"], 2)


class ReportPeriodValidationTests(_MonthlyFixtureMixin, TestCase):
    def test_rejects_month_outside_project(self):
        with self.assertRaisesMessage(ExportValidationError, "Bulan 4 di luar masa proyek"):
            ExportManager(self.project, self.owner).export_jadwal_professional(
                "pdf", report_type="monthly", months=[3, 4],
            )

    def test_rejects_week_outside_project(self):
        with self.assertRaisesMessage(ExportValidationError, "Minggu 13 di luar masa proyek"):
            ExportManager(self.project, self.owner).export_jadwal_professional(
                "xlsx", report_type="weekly", weeks=[13],
            )

    def test_rejects_single_period_parameter_too(self):
        with self.assertRaises(ExportValidationError):
            ExportManager(self.project, self.owner).export_jadwal_professional(
                "pdf", report_type="monthly", period=4,
            )


class MonthlyCumulativeProgressTests(_MonthlyFixtureMixin, TestCase):
    def test_previous_month_column_is_cumulative_from_week_one(self):
        data = JadwalPekerjaanExportAdapter(self.project).get_monthly_comparison_data(3)
        rows = {r["name"]: r for r in data["hierarchy_progress"] if r["type"] == "pekerjaan"}
        beton, bekisting = rows["Beton"], rows["Bekisting"]
        # Beton selesai di W1-W2: kumulatif s.d. bulan lalu (W1..W8) = 100% x bobot.
        self.assertAlmostEqual(beton["progress_bulan_lalu"], beton["bobot"], places=6)
        self.assertAlmostEqual(beton["progress_bulan_ini"], 0.0, places=6)
        # Bekisting: W3..W8 = 60% lalu, W9..W12 = 40% bulan ini.
        self.assertAlmostEqual(bekisting["progress_bulan_lalu"], 0.60 * bekisting["bobot"], places=6)
        self.assertAlmostEqual(bekisting["progress_bulan_ini"], 0.40 * bekisting["bobot"], places=6)

    def test_table_total_equals_summary_cumulative(self):
        data = JadwalPekerjaanExportAdapter(self.project).get_monthly_comparison_data(3)
        pekerjaan = [r for r in data["hierarchy_progress"] if r["type"] == "pekerjaan"]
        total = sum(r["progress_bulan_lalu"] + r["progress_bulan_ini"] for r in pekerjaan)
        self.assertAlmostEqual(total, data["current_data"]["cumulative_actual"], places=6)
        self.assertAlmostEqual(total, 100.0, places=6)

    def test_rows_carry_satuan_and_volume_without_per_row_query(self):
        adapter = JadwalPekerjaanExportAdapter(self.project)
        base_rows, hierarchy = adapter._build_base_rows()
        pm, _ = adapter._build_progress_map()
        am = adapter._build_actual_progress_map()
        adapter._get_bobot_maps(base_rows)  # warm caches
        with CaptureQueriesContext(connection) as ctx:
            rows = adapter._build_hierarchy_progress(base_rows, hierarchy, pm, am, 3, 9, 12)
        # Hanya _load_volume_map (dulu 1 query VolumePekerjaan PER baris). EXPLAIN dari
        # instrumen pemantau query (aktif di suite penuh) bukan query aplikasi.
        app_queries = [q["sql"] for q in ctx.captured_queries if not q["sql"].startswith("EXPLAIN")]
        self.assertEqual(len(app_queries), 1, app_queries)
        bekisting = next(r for r in rows if r.get("name") == "Bekisting")
        self.assertEqual(bekisting["satuan"], "m2")
        self.assertEqual(bekisting["volume"], 1234.5)


class MonthlyPdfRenderTests(_MonthlyFixtureMixin, TestCase):
    def test_no_blank_pages(self):
        pages = self._monthly_pdf_pages(3)
        for index, text in enumerate(pages, start=1):
            body = [
                line for line in text.splitlines()
                if line.strip() and line.strip() not in ("Monthly PDF", "Dashboard-RAB.com")
                and " - Halaman " not in line
            ]
            self.assertTrue(body, f"halaman {index} kosong (hanya header/footer)")

    def test_summary_and_table_total_agree_in_pdf(self):
        # Bug lama: Ringkasan 94.31% vs TOTAL tabel 0.11% di halaman yang sama.
        text = "\n".join(self._monthly_pdf_pages(3))
        lines = text.splitlines()
        akumulasi = lines[lines.index("Akumulasi Actual") + 2]
        total_row = lines[lines.index("TOTAL") + 1:lines.index("TOTAL") + 6]
        # TOTAL: [total harga, bobot, kum. lalu, progress ini, kum. ini]
        self.assertEqual(akumulasi, "100.00%")
        self.assertEqual(total_row[4], akumulasi)
        self.assertNotEqual(total_row[2], "100.00%")  # bekisting masih berjalan di bulan ini

    def test_numbers_are_id_locale_and_not_truncated(self):
        text = "\n".join(self._monthly_pdf_pages(3))
        self.assertIn("1.234,50", text)          # volume id-ID (bukan 1.234.50)
        self.assertNotIn("1.234.50", text)
        self.assertIn("\n30.000,00\n", text)     # tidak patah jadi "30.000,0" + "0"
        self.assertIn("Rp 6.600.000.000", text)  # total harga utuh (dulu dipotong 14 karakter)
        self.assertNotIn("\nRp6.600.000.00\n", text)

    def test_identity_labels_and_signature_jabatan(self):
        text = "\n".join(self._monthly_pdf_pages(3))
        self.assertIn("Sumber Dana", text)
        self.assertNotIn("Ket. Project 1", text)  # field Dashboard kosong -> tidak tampil
        self.assertNotIn("Direktur", text)

    LONG_NAME = (
        "Perencanaan Pembangunan Kandang Ternak Kelompok Tani Ternak Beriuk Rajin "
        "Bedugul Daya & Sarana Pendukung"
    )
    LONG_LOKASI = "Desa Bedugul, Kecamatan Sambelia, Kabupaten Lombok Timur, Nusa Tenggara Barat"

    def _assert_identity_wrapped(self, pages_text):
        lines = pages_text.splitlines()
        # Dulu satu baris utuh yang meluber keluar bingkai; kini dibungkus beberapa baris.
        self.assertNotIn(self.LONG_NAME, lines)
        self.assertNotIn(self.LONG_LOKASI, lines)
        joined = " ".join(line.strip() for line in lines)
        self.assertIn("Beriuk Rajin", joined)
        self.assertIn("Daya & Sarana", joined)  # '&' di-escape, tidak merusak Paragraph
        self.assertIn("Nusa Tenggara Barat", joined)

    def test_long_identity_values_wrap_monthly_and_weekly(self):
        Project.objects.filter(pk=self.project.pk).update(
            nama=self.LONG_NAME, lokasi_project=self.LONG_LOKASI,
        )
        self.project.refresh_from_db()
        self._assert_identity_wrapped("\n".join(self._monthly_pdf_pages(3)))

        weekly = ExportManager(self.project, self.owner).export_jadwal_professional(
            "pdf", report_type="weekly", weeks=[3],
        )
        self._assert_identity_wrapped("\n".join(pdf_page_texts(weekly.content)))

    def test_cover_is_simple_without_logo_box_or_glyph_divider(self):
        Project.objects.filter(pk=self.project.pk).update(nama="Gedung A & B")
        self.project.refresh_from_db()
        for report_type, periods in (("monthly", {"months": [3]}), ("weekly", {"weeks": [3]})):
            response = ExportManager(self.project, self.owner).export_jadwal_professional(
                "pdf", report_type=report_type, **periods,
            )
            cover = pdf_page_texts(response.content)[0].splitlines()
            # Dulu: '─' * 35 (tidak ada di Helvetica) tercetak sebagai deret kotak.
            self.assertFalse([line for line in cover if len(set(line.strip())) == 1 and len(line.strip()) > 5])
            self.assertIn("Gedung A & B", cover)  # nama proyek di-escape
            self.assertTrue(cover[0].startswith("LAPORAN "))
            # Kotak logo lama = rect 40x25mm (113.3858 x 70.86614 pt) di stream cover.
            self.assertNotIn(b"113.3858 -70.86614 re", pdf_page_streams(response.content)[0])

    def test_ket_project_shown_when_filled(self):
        Project.objects.filter(pk=self.project.pk).update(ket_project1="Tahun Anggaran 2026")
        self.project.refresh_from_db()
        text = "\n".join(self._monthly_pdf_pages(3))
        self.assertIn("Ket. Project 1", text)
        self.assertIn("Tahun Anggaran 2026", text)


class CollapseRedundantPageBreakTests(TestCase):
    def _names(self, story):
        return [x if isinstance(x, str) else type(x).__name__ for x in story]

    def test_double_break_keeps_template_before_and_marker_after(self):
        from reportlab.platypus import NextPageTemplate, PageBreak

        story = ["A", PageBreak(), NextPageTemplate("landscape"), PageBreak(), SegmentMarker("x"), "B"]
        self.assertEqual(
            self._names(PDFExporter._collapse_redundant_page_breaks(story)),
            ["A", "NextPageTemplate", "PageBreak", "SegmentMarker", "B"],
        )

    def test_trailing_break_dropped_and_single_breaks_kept(self):
        from reportlab.platypus import PageBreak

        story = ["A", PageBreak(), "B", PageBreak()]
        self.assertEqual(
            self._names(PDFExporter._collapse_redundant_page_breaks(story)),
            ["A", "PageBreak", "B"],
        )
