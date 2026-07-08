"""Image-diff PNG antar dua folder baseline export (Doc 32 Fase 0.5).

Membandingkan render PNG per halaman (hasil scripts/export_baseline.py) antara
dua run — mis. SEBELUM vs SESUDAH Fase 1. Gate Fase 1 = semua halaman IDENTIK.

Pemakaian:
    .\\env\\Scripts\\python.exe scripts\\export_visual_diff.py ^
        export_baseline\\SEBELUM_20260708 export_baseline\\SESUDAH_20260708

Exit code: 0 = semua identik; 1 = ada perbedaan/halaman hilang.
Artefak beda disimpan ke <dir_b>/diff/ (gambar selisih yang diperkuat).

Catatan: DOCX tidak di-diff visual (butuh LibreOffice untuk konversi ke PDF —
belum terpasang di mesin ini); perubahan Word diverifikasi via review manual +
test suite.
"""
import argparse
import csv
import sys
from pathlib import Path

from PIL import Image, ImageChops


def compare_pair(path_a: Path, path_b: Path, diff_dir: Path):
    img_a = Image.open(path_a).convert('RGB')
    img_b = Image.open(path_b).convert('RGB')
    if img_a.size != img_b.size:
        return 'SIZE-DIFF', f"{img_a.size} vs {img_b.size}"

    diff = ImageChops.difference(img_a, img_b)
    bbox = diff.getbbox()
    if bbox is None:
        return 'IDENTIK', ''

    gray = diff.convert('L')
    nonzero = sum(gray.histogram()[1:])
    total = img_a.size[0] * img_a.size[1]
    pct = 100.0 * nonzero / total

    diff_dir.mkdir(parents=True, exist_ok=True)
    # Simpan selisih yang diperkuat agar mudah dilihat mata
    amplified = gray.point(lambda v: 255 if v > 0 else 0)
    amplified.save(diff_dir / f"DIFF_{path_a.name}")
    return 'BEDA', f"{nonzero} px ({pct:.3f}%), bbox={bbox}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('dir_a', type=Path, help='folder baseline A (acuan)')
    parser.add_argument('dir_b', type=Path, help='folder baseline B (pembanding)')
    args = parser.parse_args()

    png_a = args.dir_a / 'png'
    png_b = args.dir_b / 'png'
    if not png_a.is_dir() or not png_b.is_dir():
        print(f"Folder png/ tidak ditemukan di salah satu sisi: {png_a} | {png_b}")
        return 2

    names_a = {p.name for p in png_a.glob('*.png')}
    names_b = {p.name for p in png_b.glob('*.png')}
    diff_dir = args.dir_b / 'diff'

    rows = []
    any_problem = False
    for name in sorted(names_a | names_b):
        if name not in names_a:
            rows.append([name, 'HANYA-DI-B', ''])
            any_problem = True
            continue
        if name not in names_b:
            rows.append([name, 'HANYA-DI-A', ''])
            any_problem = True
            continue
        status, detail = compare_pair(png_a / name, png_b / name, diff_dir)
        rows.append([name, status, detail])
        if status != 'IDENTIK':
            any_problem = True

    report = args.dir_b / 'visual_diff_report.csv'
    with open(report, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.writer(fh)
        writer.writerow(['halaman', 'status', 'detail'])
        writer.writerows(rows)

    n_identik = sum(1 for r in rows if r[1] == 'IDENTIK')
    print(f"\n{n_identik}/{len(rows)} halaman IDENTIK. Laporan: {report}")
    for name, status, detail in rows:
        if status != 'IDENTIK':
            print(f"  {status:10s} {name}  {detail}")

    return 1 if any_problem else 0


if __name__ == '__main__':
    sys.exit(main())
