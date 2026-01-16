"""
Quick-and-dirty benchmark helper for referensi import pipeline.

Usage (from project root):
    python scripts/benchmark_referensi.py --jobs 200 --details 5

The script generates a synthetic Excel file in a temporary directory, then
measures the time needed to parse the preview via `load_preview_from_file`
and run `assign_item_codes`. Results are printed to stdout so we can compare
before/after optimisation work.
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import django


@dataclass
class BenchmarkResult:
    jobs: int
    rincian: int
    parse_seconds: float
    assign_seconds: float


def setup_django() -> None:
    project_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project_root))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


@contextmanager
def synthetic_excel(num_jobs: int, details_per_job: int):
    try:
        from openpyxl import Workbook
    except ModuleNotFoundError as exc:  # pragma: no cover - tooling dependency
        raise SystemExit("openpyxl is required for the benchmark script") from exc

    header = [
        "sumber_ahsp",
        "kode_ahsp",
        "nama_ahsp",
        "klasifikasi",
        "sub_klasifikasi",
        "satuan_pekerjaan",
        "kategori",
        "kode_item",
        "uraian_item",
        "satuan_item",
        "koefisien",
    ]

    wb = Workbook(write_only=True)
    ws = wb.create_sheet(title="AHSP Benchmark")
    ws.append(header)

    for job_index in range(num_jobs):
        sumber = f"Sumber {job_index % 5}"
        kode = f"JOB-{job_index:04d}"
        nama = f"Pekerjaan sintetis #{job_index}"
        klas = f"Klas-{job_index % 3}"
        sub_klas = f"Sub-{job_index % 7}"
        satuan = "m3"

        for detail_index in range(details_per_job):
            kategori = ["TK", "BHN", "ALT", "LAIN"][detail_index % 4]
            kode_item = f"{kategori}-{job_index:04d}-{detail_index:03d}"
            uraian = f"Item {detail_index} untuk job {job_index}"
            satuan_item = "UNIT"
            koef = 1 + (detail_index % 5) * 0.1

            if detail_index == 0:
                row = [
                    sumber,
                    kode,
                    nama,
                    klas,
                    sub_klas,
                    satuan,
                    kategori,
                    kode_item,
                    uraian,
                    satuan_item,
                    koef,
                ]
            else:
                row = [
                    "",
                    "",
                    "",
                    "",
                    "",
                    "",
                    kategori,
                    kode_item,
                    uraian,
                    satuan_item,
                    koef,
                ]
            ws.append(row)

    tmp = tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False)
    wb.save(tmp.name)
    wb.close()

    try:
        yield Path(tmp.name)
    finally:
        tmp.close()
        Path(tmp.name).unlink(missing_ok=True)


def run_benchmark(num_jobs: int, details_per_job: int) -> BenchmarkResult:
    from referensi.services.ahsp_parser import load_preview_from_file
    from referensi.services.item_code_registry import assign_item_codes

    with synthetic_excel(num_jobs, details_per_job) as excel_path:
        with excel_path.open("rb") as handle:
            uploaded = io.BytesIO(handle.read())
            uploaded.name = excel_path.name

        start = time.perf_counter()
        parse_result = load_preview_from_file(uploaded)
        parse_seconds = time.perf_counter() - start

        start = time.perf_counter()
        assign_item_codes(parse_result)
        assign_seconds = time.perf_counter() - start

    return BenchmarkResult(
        jobs=parse_result.total_jobs,
        rincian=parse_result.total_rincian,
        parse_seconds=parse_seconds,
        assign_seconds=assign_seconds,
    )


def main():
    parser = argparse.ArgumentParser(description="Benchmark referensi import preview")
    parser.add_argument("--jobs", type=int, default=200, help="Jumlah pekerjaan sintetis")
    parser.add_argument(
        "--details",
        type=int,
        default=5,
        help="Jumlah rincian per pekerjaan sintetis",
    )
    args = parser.parse_args()

    setup_django()
    result = run_benchmark(args.jobs, args.details)
    print(
        "Benchmark selesai: jobs=%d rincian=%d parse=%.3fs assign=%.3fs"
        % (result.jobs, result.rincian, result.parse_seconds, result.assign_seconds)
    )


if __name__ == "__main__":
    main()
