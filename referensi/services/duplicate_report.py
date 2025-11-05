"""
Service untuk generate laporan duplikat saat import XLSX.

User perlu tahu PERSIS baris mana yang dianggap duplikat dan kenapa.
"""

import csv
import os
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Tuple

from django.conf import settings


@dataclass
class DuplicateEntry:
    """Single duplicate entry detail."""
    row_number: int
    ahsp_kode: str
    ahsp_nama: str
    kategori: str
    kode_item: str
    uraian_item: str
    satuan_item: str
    koefisien: str
    duplicate_of_row: int  # Which row is this a duplicate of
    reason: str = "Kombinasi kategori + kode_item + uraian + satuan sama"


@dataclass
class SkippedEntry:
    """Single skipped entry detail."""
    row_number: int
    ahsp_kode: str
    ahsp_nama: str
    kategori: str
    kode_item: str
    uraian_item: str
    satuan_item: str
    koefisien: str
    reason: str


@dataclass
class ImportReport:
    """Laporan lengkap import."""
    duplicates: List[DuplicateEntry] = field(default_factory=list)
    skipped: List[SkippedEntry] = field(default_factory=list)
    filename: str = ""
    timestamp: str = ""


def generate_duplicate_report_csv(report: ImportReport, source_filename: str) -> str:
    """
    Generate CSV report untuk duplikat dan baris yang di-skip.

    Returns:
        str: Path relatif dari MEDIA_ROOT ke file CSV
    """
    # Create reports directory
    reports_dir = os.path.join(settings.MEDIA_ROOT, 'import_reports')
    os.makedirs(reports_dir, exist_ok=True)

    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_source = source_filename.replace('.xlsx', '').replace('.xls', '')
    safe_source = ''.join(c if c.isalnum() or c in ('_', '-') else '_' for c in safe_source)
    csv_filename = f'duplicate_report_{safe_source}_{timestamp}.csv'
    csv_path = os.path.join(reports_dir, csv_filename)

    # Write CSV
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
        writer = csv.writer(csvfile)

        # Header
        writer.writerow([
            'Tipe',
            'Baris Excel',
            'Kode AHSP',
            'Nama AHSP',
            'Kategori',
            'Kode Item',
            'Uraian Item',
            'Satuan',
            'Koefisien',
            'Duplikat dari Baris',
            'Alasan'
        ])

        # Write duplicates
        for dup in report.duplicates:
            writer.writerow([
                'DUPLIKAT',
                dup.row_number,
                dup.ahsp_kode,
                dup.ahsp_nama,
                dup.kategori,
                dup.kode_item,
                dup.uraian_item,
                dup.satuan_item,
                dup.koefisien,
                dup.duplicate_of_row,
                dup.reason
            ])

        # Write skipped
        for skip in report.skipped:
            writer.writerow([
                'DIABAIKAN',
                skip.row_number,
                skip.ahsp_kode,
                skip.ahsp_nama,
                skip.kategori,
                skip.kode_item,
                skip.uraian_item,
                skip.satuan_item,
                skip.koefisien,
                '',  # No duplicate_of_row for skipped
                skip.reason
            ])

    # Return relative path from MEDIA_ROOT
    return os.path.relpath(csv_path, settings.MEDIA_ROOT)


def cleanup_old_reports(max_age_days=7):
    """
    Cleanup old duplicate reports older than max_age_days.

    Args:
        max_age_days: Maximum age in days before deletion
    """
    import time

    reports_dir = os.path.join(settings.MEDIA_ROOT, 'import_reports')
    if not os.path.exists(reports_dir):
        return 0

    deleted_count = 0
    cutoff_time = time.time() - (max_age_days * 86400)

    for filename in os.listdir(reports_dir):
        if not filename.startswith('duplicate_report_'):
            continue

        filepath = os.path.join(reports_dir, filename)
        try:
            if os.path.getmtime(filepath) < cutoff_time:
                os.remove(filepath)
                deleted_count += 1
        except Exception:
            pass

    return deleted_count


__all__ = [
    'DuplicateEntry',
    'SkippedEntry',
    'ImportReport',
    'generate_duplicate_report_csv',
    'cleanup_old_reports',
]
