"""
Import Error Analyzer - Extract useful information from import errors.

Provides detailed error analysis to help users understand what went wrong.
"""

from __future__ import annotations
import re
import traceback
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class ErrorAnalysis:
    """Detailed analysis of an import error."""

    error_type: str  # Exception class name
    error_message: str  # Original error message
    user_message: str  # User-friendly explanation
    suggestions: List[str]  # Actionable suggestions
    affected_rows: List[int]  # Row numbers with issues
    affected_fields: List[str]  # Field names with issues
    severity: str  # 'critical', 'warning', 'info'
    technical_details: str  # Full traceback for debugging


def analyze_import_exception(exc: Exception, parse_result=None, summary=None) -> ErrorAnalysis:
    """
    Analyze an import exception and provide detailed user-friendly information.

    Args:
        exc: The exception that occurred
        parse_result: The ParseResult object (if available)
        summary: The ImportSummary object (if available)

    Returns:
        ErrorAnalysis with detailed information
    """
    error_type = type(exc).__name__
    error_message = str(exc)
    suggestions = []
    affected_rows = []
    affected_fields = []
    severity = 'critical'

    # Extract traceback
    technical_details = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    # Analyze based on error type
    if 'TransactionManagementError' in error_type:
        user_message = (
            "Terjadi kesalahan dalam pengelolaan transaksi database. "
            "Ini biasanya disebabkan oleh data yang tidak valid atau konflik data."
        )

        # Try to extract which operation failed
        if 'materialized view' in error_message.lower() or 'materialized view' in technical_details.lower():
            suggestions.append("❌ Gagal me-refresh statistik database (materialized view)")
            suggestions.append("💡 Data Anda mungkin sudah tersimpan, tapi statistik belum ter-update")
            suggestions.append("💡 Coba refresh halaman atau hubungi administrator")
            severity = 'warning'
        elif 'cache' in error_message.lower() or 'cache' in technical_details.lower():
            suggestions.append("❌ Gagal membersihkan cache database")
            suggestions.append("💡 Data mungkin sudah tersimpan tapi cache belum dibersihkan")
            severity = 'warning'
        else:
            # Extract error details from summary if available
            if summary and summary.detail_errors:
                # Parse detail errors for row numbers
                for error in summary.detail_errors[:5]:  # Show first 5 errors
                    match = re.search(r'baris (\d+)', error, re.IGNORECASE)
                    if match:
                        row_num = int(match.group(1))
                        if row_num not in affected_rows:
                            affected_rows.append(row_num)
                    suggestions.append(f"⚠️ {error}")

                if len(summary.detail_errors) > 5:
                    suggestions.append(f"⚠️ ... dan {len(summary.detail_errors) - 5} error lainnya")

            if affected_rows:
                suggestions.append(f"\n📍 Baris yang bermasalah: {', '.join(map(str, sorted(affected_rows)[:10]))}")
                suggestions.append("💡 Periksa data pada baris-baris tersebut di file Excel Anda")
            else:
                suggestions.append("💡 Periksa log server untuk detail lengkap")
                suggestions.append("💡 Coba import dengan file yang lebih kecil (1000 baris) untuk isolasi masalah")

    elif 'IntegrityError' in error_type:
        user_message = "Data yang diimpor konflik dengan data yang sudah ada di database."

        # Extract field name and value from error message
        if 'UNIQUE constraint' in error_message:
            # Try to extract field name
            unique_match = re.search(r'UNIQUE constraint failed: \w+\.(\w+)', error_message)
            if unique_match:
                field = unique_match.group(1)
                affected_fields.append(field)
                suggestions.append(f"❌ Duplikat pada field: {field}")

            suggestions.append("💡 Ada data dengan kode/ID yang sama sudah ada di database")
            suggestions.append("💡 Periksa apakah Anda mencoba import data yang sama 2x")
            suggestions.append("💡 Atau ada duplikat dalam file Excel Anda sendiri")

        elif 'FOREIGN KEY constraint' in error_message:
            suggestions.append("❌ Referensi data tidak valid (foreign key error)")
            suggestions.append("💡 Data yang direferensikan tidak ada di database")

        # Check summary for detail errors
        if summary and summary.detail_errors:
            for error in summary.detail_errors[:3]:
                match = re.search(r'baris (\d+)', error, re.IGNORECASE)
                if match:
                    affected_rows.append(int(match.group(1)))

            if affected_rows:
                suggestions.append(f"\n📍 Baris yang bermasalah: {', '.join(map(str, sorted(affected_rows)))}")

    elif 'OperationalError' in error_type:
        user_message = "Terjadi masalah operasional dengan database."

        if 'timeout' in error_message.lower() or 'time' in error_message.lower():
            suggestions.append("❌ Database timeout - file terlalu besar atau server sibuk")
            suggestions.append("💡 Coba pecah file menjadi bagian lebih kecil:")
            suggestions.append("   - Maksimal 5000 baris per file untuk import cepat")
            suggestions.append("   - Atau maksimal 2000 baris jika server lambat")
        elif 'lock' in error_message.lower():
            suggestions.append("❌ Database sedang dikunci (locked)")
            suggestions.append("💡 Mungkin ada proses import lain yang sedang berjalan")
            suggestions.append("💡 Tunggu beberapa saat dan coba lagi")
        else:
            suggestions.append(f"❌ Error operasional: {error_message}")
            suggestions.append("💡 Hubungi administrator sistem")

    elif 'ValidationError' in error_type:
        user_message = "Data tidak valid berdasarkan aturan validasi."

        # Parse validation errors
        if 'koefisien' in error_message.lower():
            affected_fields.append('koefisien')
            suggestions.append("❌ Nilai koefisien tidak valid")
            suggestions.append("💡 Koefisien harus berupa angka positif")
            suggestions.append("💡 Format yang diterima: 0.5, 1.25, 8e-05, dll")

        # Extract row numbers from summary
        if summary and summary.detail_errors:
            for error in summary.detail_errors[:5]:
                match = re.search(r'baris (\d+)', error, re.IGNORECASE)
                if match:
                    affected_rows.append(int(match.group(1)))
                suggestions.append(f"⚠️ {error}")

            if affected_rows:
                suggestions.append(f"\n📍 Baris yang bermasalah: {', '.join(map(str, sorted(affected_rows)))}")

    else:
        # Generic error
        user_message = f"Terjadi kesalahan: {error_type}"
        suggestions.append(f"❌ {error_message}")
        suggestions.append("💡 Screenshot error ini dan hubungi administrator")
        suggestions.append("💡 Atau coba dengan file yang lebih kecil untuk testing")

    # Add general suggestions based on parse_result
    if parse_result:
        total_jobs = len(parse_result.jobs) if hasattr(parse_result, 'jobs') else 0
        total_rincian = parse_result.total_rincian if hasattr(parse_result, 'total_rincian') else 0

        if total_rincian > 10000:
            suggestions.append(f"\n📊 File Anda berisi {total_jobs} pekerjaan dengan {total_rincian} rincian")
            suggestions.append("💡 Ini adalah file besar. Pertimbangkan untuk:")
            suggestions.append("   - Pecah menjadi beberapa file kecil (5000 rincian per file)")
            suggestions.append("   - Atau import saat server tidak sibuk (malam/dini hari)")

    # Add summary info if available
    if summary:
        if hasattr(summary, 'jobs_created') and summary.jobs_created > 0:
            suggestions.append(f"\n✅ Berhasil membuat {summary.jobs_created} pekerjaan baru")
        if hasattr(summary, 'jobs_updated') and summary.jobs_updated > 0:
            suggestions.append(f"✅ Berhasil update {summary.jobs_updated} pekerjaan")
        if hasattr(summary, 'rincian_written') and summary.rincian_written > 0:
            suggestions.append(f"✅ Berhasil menulis {summary.rincian_written} rincian")

        if hasattr(summary, 'detail_errors') and summary.detail_errors:
            error_count = len(summary.detail_errors)
            if error_count > 0:
                suggestions.append(f"\n⚠️ Total {error_count} rincian gagal diimport")

    return ErrorAnalysis(
        error_type=error_type,
        error_message=error_message,
        user_message=user_message,
        suggestions=suggestions,
        affected_rows=sorted(list(set(affected_rows)))[:20],  # Max 20 rows
        affected_fields=list(set(affected_fields)),
        severity=severity,
        technical_details=technical_details
    )


def format_error_for_user(analysis: ErrorAnalysis) -> List[str]:
    """
    Format error analysis as user-friendly messages.

    Returns:
        List of message strings to display to user
    """
    messages = []

    # Main error message
    if analysis.severity == 'critical':
        messages.append(f"❌ {analysis.user_message}")
    elif analysis.severity == 'warning':
        messages.append(f"⚠️ {analysis.user_message}")
    else:
        messages.append(f"ℹ️ {analysis.user_message}")

    # Technical details (collapsed)
    if analysis.error_type != 'Unknown':
        messages.append(f"\n🔧 Tipe Error: {analysis.error_type}")

    # Affected rows
    if analysis.affected_rows:
        rows_str = ', '.join(map(str, analysis.affected_rows[:10]))
        if len(analysis.affected_rows) > 10:
            rows_str += f", ... (+{len(analysis.affected_rows) - 10} lainnya)"
        messages.append(f"\n📍 Baris Excel yang bermasalah: {rows_str}")

    # Affected fields
    if analysis.affected_fields:
        messages.append(f"📝 Field yang bermasalah: {', '.join(analysis.affected_fields)}")

    # Suggestions
    if analysis.suggestions:
        messages.append("\n💡 Langkah-langkah perbaikan:")
        for suggestion in analysis.suggestions:
            if not suggestion.startswith(('❌', '⚠️', '✅', '💡', '📍', '📊')):
                messages.append(f"   • {suggestion}")
            else:
                messages.append(suggestion)

    return messages


__all__ = [
    'ErrorAnalysis',
    'analyze_import_exception',
    'format_error_for_user'
]
