"""Dev-only baseline untuk Doc 32 Fase 0.2/0.3 (export visual refinement).

Menjalankan export jalur-A (Rekap RAB, Rekap Kebutuhan, Volume, Harga Items,
Rincian AHSP) terhadap proyek fixture, menyimpan artefak "SEBELUM" + metrik
durasi/ukuran ke CSV, dan (bila pymupdf terpasang) merender PDF ke PNG per
halaman sebagai basis image-diff Fase 1.

Pemakaian (dari root repo, venv aktif tidak wajib):
    .\\env\\Scripts\\python.exe scripts\\export_baseline.py [--tag SEBELUM]

Output: export_baseline/<tag>_<YYYYMMDD>/
Catatan: memakai config.settings.test (SQLite test_db.sqlite3) — TIDAK menyentuh
database pengembangan/produksi.
"""
import argparse
import csv
import hashlib
import os
import sys
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.test')

import django  # noqa: E402

django.setup()

from django.core.management import call_command  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402

from dashboard.models import Project  # noqa: E402
from detail_project.models import (  # noqa: E402
    Klasifikasi,
    SubKlasifikasi,
    Pekerjaan,
    HargaItemProject,
    DetailAHSPProject,
    DetailAHSPExpanded,
    VolumePekerjaan,
)
from detail_project.exports.export_manager import ExportManager  # noqa: E402

FIXTURE_PROJECT_NAME = "__BASELINE_EXPORT_VISUAL__"

EXT_MAP = {'pdf': 'pdf', 'word': 'docx', 'xlsx': 'xlsx', 'csv': 'csv'}

# (report_key, callable-name, formats). PDF+Word = scope doc 32; xlsx/csv ikut
# direkam untuk kelengkapan metrik (di luar scope perubahan visual).
REPORTS = [
    ('rekap_rab', 'export_rekap_rab', ['pdf', 'word', 'xlsx', 'csv']),
    ('rekap_kebutuhan', 'export_rekap_kebutuhan', ['pdf', 'word', 'xlsx', 'csv']),
    ('volume_pekerjaan', 'export_volume_pekerjaan', ['pdf', 'word', 'xlsx', 'csv']),
    ('harga_items', 'export_harga_items', ['pdf', 'word', 'xlsx', 'csv']),
    ('rincian_ahsp', 'export_rincian_ahsp', ['pdf', 'word', 'xlsx', 'csv']),
]


def build_fixture(owner):
    """Proyek uji cukup kaya untuk menilai visual: hierarki 2 klasifikasi,
    3 kategori item (TK/BHN/ALT), uraian panjang (uji wrap), volume desimal."""
    Project.objects.filter(nama=FIXTURE_PROJECT_NAME).delete()
    project = Project.objects.create(
        owner=owner,
        nama=FIXTURE_PROJECT_NAME,
    )

    items = {
        'TK': HargaItemProject.objects.create(
            project=project, kode_item="TK-001", kategori="TK",
            uraian="Pekerja terampil", satuan="OH", harga_satuan=Decimal("125000.00"),
        ),
        'BHN': HargaItemProject.objects.create(
            project=project, kode_item="BHN-001", kategori="BHN",
            uraian="Semen portland 50 kg", satuan="zak", harga_satuan=Decimal("78500.00"),
        ),
        'BHN2': HargaItemProject.objects.create(
            project=project, kode_item="BHN-002", kategori="BHN",
            uraian="Pasir pasang (berat sedang, sudah termasuk ongkos angkut ke lokasi)",
            satuan="m3", harga_satuan=Decimal("315250.50"),
        ),
        'ALT': HargaItemProject.objects.create(
            project=project, kode_item="ALT-001", kategori="ALT",
            uraian="Concrete mixer 0.3-0.6 m3", satuan="sewa-hari",
            harga_satuan=Decimal("450000.00"),
        ),
    }

    spec = [
        ("Pekerjaan Persiapan", [
            ("Pembersihan Lahan", [
                ("P-001", "Pembersihan dan perataan lahan", "m2",
                 Decimal("250.000"), [('TK', "0.050000"), ('ALT', "0.010000")]),
                ("P-002", "Pengukuran dan pemasangan bouwplank dengan patok kayu "
                          "dan papan kelas III termasuk perlengkapan lainnya", "m",
                 Decimal("48.500"), [('TK', "0.100000"), ('BHN2', "0.012000")]),
            ]),
        ]),
        ("Pekerjaan Struktur", [
            ("Pondasi", [
                ("S-001", "Pasangan pondasi batu belah 1:4", "m3",
                 Decimal("12.750"), [('TK', "1.500000"), ('BHN', "3.260000"),
                                     ('BHN2', "0.520000")]),
            ]),
            ("Beton", [
                ("S-002", "Beton mutu f'c = 21,7 MPa (K250)", "m3",
                 Decimal("8.125"), [('TK', "2.100000"), ('BHN', "7.776000"),
                                    ('ALT', "0.250000")]),
            ]),
        ]),
    ]

    # ordering_index unik per-project (bukan per-parent) → pakai counter global
    sub_counter = 0
    pek_counter = 0
    for k_idx, (klas_name, subs) in enumerate(spec, start=1):
        klas = Klasifikasi.objects.create(
            project=project, name=klas_name, ordering_index=k_idx)
        for sub_name, peks in subs:
            sub_counter += 1
            sub = SubKlasifikasi.objects.create(
                project=project, klasifikasi=klas, name=sub_name,
                ordering_index=sub_counter)
            for kode, uraian, satuan, volume, details in peks:
                pek_counter += 1
                pek = Pekerjaan.objects.create(
                    project=project, sub_klasifikasi=sub,
                    source_type=Pekerjaan.SOURCE_CUSTOM,
                    snapshot_kode=kode, snapshot_uraian=uraian,
                    snapshot_satuan=satuan, ordering_index=pek_counter,
                )
                for item_key, koef in details:
                    item = items[item_key]
                    src = DetailAHSPProject.objects.create(
                        project=project, pekerjaan=pek, harga_item=item,
                        kategori=item.kategori, kode=item.kode_item,
                        uraian=item.uraian, satuan=item.satuan,
                        koefisien=Decimal(koef),
                    )
                    DetailAHSPExpanded.objects.create(
                        project=project, pekerjaan=pek, source_detail=src,
                        harga_item=item, kategori=item.kategori,
                        kode=item.kode_item, uraian=item.uraian,
                        satuan=item.satuan, koefisien=Decimal(koef),
                        expansion_depth=0,
                    )
                VolumePekerjaan.objects.create(
                    project=project, pekerjaan=pek, quantity=volume)

    return project


def render_pdf_pages(pdf_path: Path, out_dir: Path) -> int:
    """Render PDF ke PNG per halaman (150 dpi). Return jumlah halaman; -1 bila
    pymupdf tidak tersedia."""
    try:
        import fitz  # pymupdf
    except ImportError:
        return -1
    doc = fitz.open(pdf_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=150)
        pix.save(out_dir / f"{pdf_path.stem}_p{i:02d}.png")
    n = doc.page_count
    doc.close()
    return n


def trace_pdf_builders(manager):
    """Fase 0.4 (doc 32 Lampiran A): konfirmasi empiris builder PDF per report.

    Monkeypatch sementara method builder PDFExporter dengan counter, jalankan
    export PDF tiap report, laporkan builder yang benar-benar terpanggil.
    """
    import functools
    from detail_project.exports.pdf_exporter import PDFExporter

    targets = [
        '_build_simple_table', '_build_table', '_build_pengesahan_table',
        '_build_pekerjaan_section', '_build_footer_table', '_build_signatures',
    ]
    counts = {}
    originals = {name: getattr(PDFExporter, name) for name in targets}

    def make_wrapper(name, orig):
        @functools.wraps(orig)
        def wrapper(self, *a, **k):
            counts[name] = counts.get(name, 0) + 1
            return orig(self, *a, **k)
        return wrapper

    try:
        for name, orig in originals.items():
            setattr(PDFExporter, name, make_wrapper(name, orig))

        print("\n=== TRACE BUILDER PDF (Fase 0.4) ===")
        for report_key, method_name, _ in REPORTS:
            counts.clear()
            try:
                getattr(manager, method_name)('pdf')
                summary = ', '.join(f"{k}×{v}" for k, v in sorted(counts.items())) or '(tidak ada builder tercatat — jalur inline)'
            except Exception as e:
                summary = f"ERROR {type(e).__name__}: {e}"
            print(f"  {report_key}: {summary}")
    finally:
        for name, orig in originals.items():
            setattr(PDFExporter, name, orig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', default='SEBELUM')
    parser.add_argument('--trace', action='store_true',
                        help='jalankan trace builder PDF (Fase 0.4) setelah baseline')
    args = parser.parse_args()

    out_root = BASE_DIR / 'export_baseline' / f"{args.tag}_{date.today():%Y%m%d}"
    out_root.mkdir(parents=True, exist_ok=True)
    png_root = out_root / 'png'

    # config.settings.test memakai DisableMigrations — tabel dibuat langsung dari
    # model via run_syncdb (pola yang sama dengan Django test runner). DB scratch
    # dihapus tiap run agar baseline deterministik.
    from django.conf import settings as dj_settings
    db_path = Path(dj_settings.DATABASES['default']['NAME'])
    if db_path.exists():
        db_path.unlink()
    print(f"Buat skema (run_syncdb, SQLite scratch: {db_path.name})...")
    call_command('migrate', verbosity=0, interactive=False, run_syncdb=True)

    User = get_user_model()
    owner, _ = User.objects.get_or_create(
        username='baseline-export-owner', defaults={'is_active': True})

    print("Seed fixture proyek...")
    project = build_fixture(owner)
    manager = ExportManager(project, owner)

    rows = []
    for report_key, method_name, formats in REPORTS:
        method = getattr(manager, method_name)
        for fmt in formats:
            label = f"{report_key} [{fmt}]"
            try:
                t0 = time.perf_counter()
                response = method(fmt)
                # CSV exporter mengembalikan StreamingHttpResponse
                if getattr(response, 'streaming', False):
                    content = b''.join(response.streaming_content)
                else:
                    content = response.content
                dt = time.perf_counter() - t0
                ext = EXT_MAP[fmt]
                fpath = out_root / f"{report_key}.{ext}"
                fpath.write_bytes(content)
                sha = hashlib.sha256(content).hexdigest()[:12]
                pages = ''
                if fmt == 'pdf':
                    n = render_pdf_pages(fpath, png_root)
                    pages = n if n >= 0 else 'pymupdf-missing'
                rows.append([report_key, fmt, f"{dt:.3f}", len(content), pages, sha])
                print(f"  OK   {label}: {dt:.3f}s, {len(content):,} B"
                      + (f", {pages} hal." if fmt == 'pdf' else ""))
            except Exception as e:  # jangan hentikan baseline karena 1 kegagalan
                rows.append([report_key, fmt, 'ERROR', '', '', type(e).__name__])
                print(f"  FAIL {label}: {type(e).__name__}: {e}")

    csv_path = out_root / 'baseline_metrics.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(['report', 'format', 'duration_s', 'size_bytes',
                         'pdf_pages', 'sha256_12'])
        writer.writerows(rows)

    print(f"\nSelesai. Artefak: {out_root}")
    print(f"Metrik: {csv_path}")

    if args.trace:
        trace_pdf_builders(manager)


if __name__ == '__main__':
    main()
