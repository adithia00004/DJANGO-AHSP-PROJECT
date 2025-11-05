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

    # Extract traceback for technical details
    technical_details = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))

    # Extract affected rows from summary first (if available)
    if summary and hasattr(summary, 'detail_errors') and summary.detail_errors:
        for error in summary.detail_errors:
            match = re.search(r'baris (\d+)', error, re.IGNORECASE)
            if match:
                row_num = int(match.group(1))
                if row_num not in affected_rows:
                    affected_rows.append(row_num)

    # ============================================================
    # ANALYZE BASED ON ERROR TYPE - User-friendly messages
    # ============================================================

    if 'TransactionManagementError' in error_type:
        user_message = "⚠️ Terjadi masalah saat menyimpan data ke database"

        # Check if this is a secondary operation failure (view refresh, cache)
        if 'materialized view' in error_message.lower() or 'materialized view' in technical_details.lower():
            user_message = "🔧 MASALAH SISTEM: Gagal refresh statistik database"
            suggestions.append("\n✅ KABAR BAIK: Data Anda kemungkinan SUDAH TERSIMPAN!")
            suggestions.append("⚙️ JENIS MASALAH: Sistem (bukan kesalahan file atau data Anda)")
            suggestions.append("🔍 PENJELASAN: Statistik database gagal di-update, tapi data sudah masuk")
            suggestions.append("\n📝 Yang harus Anda lakukan:")
            suggestions.append("   1. Refresh halaman browser (tekan F5)")
            suggestions.append("   2. Cek apakah data Anda sudah muncul di daftar AHSP")
            suggestions.append("   3. Jika data BELUM ada, coba import ulang")
            suggestions.append("   4. Jika data SUDAH ada, berarti import berhasil (abaikan error ini)")
            severity = 'warning'

        elif 'cache' in error_message.lower() or 'cache' in technical_details.lower():
            user_message = "🔧 MASALAH SISTEM: Gagal membersihkan cache"
            suggestions.append("\n✅ KABAR BAIK: Data Anda kemungkinan SUDAH TERSIMPAN!")
            suggestions.append("⚙️ JENIS MASALAH: Sistem (bukan kesalahan file atau data Anda)")
            suggestions.append("🔍 PENJELASAN: Cache sistem gagal dibersihkan, tapi data sudah masuk")
            suggestions.append("\n📝 Yang harus Anda lakukan:")
            suggestions.append("   1. Logout dan login kembali")
            suggestions.append("   2. Atau tunggu 5-10 menit (cache akan auto-refresh)")
            suggestions.append("   3. Data Anda sudah tersimpan dengan aman")
            severity = 'warning'

        else:
            # This is an actual data import failure
            suggestions.append("\n📝 JENIS MASALAH: Data Anda")
            suggestions.append("❌ Ada masalah dengan data yang Anda upload")

            # Show detail errors if available
            if summary and hasattr(summary, 'detail_errors') and summary.detail_errors:
                suggestions.append("\n📋 Detail error yang ditemukan:")
                for i, error in enumerate(summary.detail_errors[:5], 1):
                    suggestions.append(f"   {i}. {error}")

                if len(summary.detail_errors) > 5:
                    remaining = len(summary.detail_errors) - 5
                    suggestions.append(f"   ... dan {remaining} error lainnya")

            # Show affected rows if found
            if affected_rows:
                rows_display = ', '.join(map(str, sorted(affected_rows)[:15]))
                if len(affected_rows) > 15:
                    rows_display += f" ... (+{len(affected_rows)-15} baris lainnya)"
                suggestions.append(f"\n📍 Baris Excel yang bermasalah:")
                suggestions.append(f"   {rows_display}")

                suggestions.append("\n📝 Langkah perbaikan:")
                suggestions.append("   1. Buka file Excel Anda")
                suggestions.append(f"   2. Cari dan periksa baris: {', '.join(map(str, sorted(affected_rows)[:5]))}")
                suggestions.append("   3. Perbaiki data yang bermasalah")
                suggestions.append("   4. Save dan upload ulang")
            else:
                suggestions.append("\n📝 Langkah troubleshooting:")
                suggestions.append("   1. Coba import file dengan jumlah lebih kecil (500-1000 baris)")
                suggestions.append("   2. Periksa format data sesuai template")
                suggestions.append("   3. Hubungi administrator jika masalah berlanjut")

    elif 'IntegrityError' in error_type:
        user_message = "💾 TABRAKAN DATABASE: Data sudah ada sebelumnya"
        suggestions.append("⚙️ JENIS MASALAH: Database (data yang sama sudah pernah diinput)")
        suggestions.append("🔍 PENJELASAN: File Anda benar, tapi data dengan kode yang sama sudah ada di database")

        # Extract field name and value from error message
        # Support both SQLite and PostgreSQL formats
        unique_constraint_found = False

        # PostgreSQL format: duplicate key value violates unique constraint "constraint_name"
        # DETAIL:  Key (field1, field2)=(value1, value2) already exists.
        if 'duplicate key value' in error_message or 'unique constraint' in error_message.lower():
            unique_constraint_found = True

            # Try to extract constraint name
            constraint_match = re.search(r'unique constraint ["\'](\w+)["\']', error_message, re.IGNORECASE)
            if constraint_match:
                constraint_name = constraint_match.group(1)
                affected_fields.append(constraint_name)

            # Try to extract field names from DETAIL line (PostgreSQL)
            fields_match = re.search(r'Key \(([^)]+)\)=\(([^)]+)\)', error_message)
            if fields_match:
                field_names_str = fields_match.group(1)
                field_values_str = fields_match.group(2)

                # Parse fields and values
                field_list = [f.strip() for f in field_names_str.split(',')]
                value_list = [v.strip() for v in field_values_str.split(',')]

                # User-friendly field names
                friendly_names = {
                    'ahsp_id': 'ID AHSP',
                    'kode_ahsp': 'Kode AHSP',
                    'kode_item': 'Kode Item',
                    'nama_ahsp': 'Nama Pekerjaan',
                    'uraian_item': 'Uraian Item',
                    'satuan_item': 'Satuan',
                    'kategori': 'Kategori'
                }

                suggestions.append("\n❌ PENYEBAB ERROR:")
                suggestions.append("   Data dengan kombinasi nilai berikut SUDAH ADA di database:")
                suggestions.append("")
                for field, value in zip(field_list, value_list):
                    friendly = friendly_names.get(field, field)
                    suggestions.append(f"      • {friendly}: {value}")

                suggestions.append("\n🔍 KEMUNGKINAN PENYEBAB:")
                suggestions.append("   1. ✅ Anda sudah pernah import file ini sebelumnya")
                suggestions.append("   2. ✅ Data ini sudah ada dari import sebelumnya")
                suggestions.append("   3. ⚠️ File Excel memiliki duplikat internal")

                suggestions.append("\n📝 SOLUSI - Pilih salah satu:")
                suggestions.append("")
                suggestions.append("   OPSI 1: Hapus data lama terlebih dahulu")
                suggestions.append("   -------")
                suggestions.append("   1. Buka menu Master Data AHSP")
                suggestions.append("   2. Cari dan hapus data yang duplikat")
                suggestions.append("   3. Kemudian import ulang file Anda")
                suggestions.append("")
                suggestions.append("   OPSI 2: Upload file dengan data BARU")
                suggestions.append("   -------")
                suggestions.append("   1. Pastikan file berisi data yang belum pernah diimport")
                suggestions.append("   2. Atau edit file untuk mengubah kode/nilai yang duplikat")
                suggestions.append("")
                suggestions.append("   OPSI 3: Abaikan jika data sudah benar")
                suggestions.append("   -------")
                suggestions.append("   • Jika data memang sudah ada dan benar, tidak perlu import ulang")

        # SQLite format: UNIQUE constraint failed: table.field
        elif 'UNIQUE constraint failed' in error_message:
            unique_constraint_found = True
            unique_match = re.search(r'UNIQUE constraint failed: \w+\.(\w+)', error_message)
            if unique_match:
                field = unique_match.group(1)
                affected_fields.append(field)

                # User-friendly field names
                field_names = {
                    'kode_ahsp': 'Kode AHSP',
                    'kode_item': 'Kode Item',
                    'nama_ahsp': 'Nama Pekerjaan',
                    'uraian_item': 'Uraian Item'
                }
                friendly_field = field_names.get(field, field)

                suggestions.append(f"\n❌ Data duplikat ditemukan pada kolom: {friendly_field}")
                suggestions.append("\n🔍 Kemungkinan penyebab:")
                suggestions.append("   • Data dengan kode yang sama sudah ada di database")
                suggestions.append("   • Anda mencoba import file yang sama 2 kali")
                suggestions.append("   • Ada duplikat dalam file Excel itu sendiri")

                if affected_rows:
                    rows_display = ', '.join(map(str, sorted(affected_rows)[:10]))
                    if len(affected_rows) > 10:
                        rows_display += f" ... (+{len(affected_rows)-10} lainnya)"
                    suggestions.append(f"\n📍 Baris yang duplikat: {rows_display}")

                suggestions.append("\n📝 Cara memperbaiki:")
                suggestions.append(f"   1. Buka file Excel Anda")
                suggestions.append(f"   2. Cari kolom '{friendly_field}'")
                if affected_rows:
                    suggestions.append(f"   3. Periksa baris {', '.join(map(str, sorted(affected_rows)[:5]))}")
                suggestions.append("   4. Hapus atau ubah nilai yang duplikat")
                suggestions.append("   5. Save dan upload ulang")

        # Handle FOREIGN KEY constraints
        if 'FOREIGN KEY constraint' in error_message:
            suggestions.append("\n❌ Data referensi tidak valid")
            suggestions.append("\n🔍 Masalahnya:")
            suggestions.append("   • Ada data yang merujuk ke data lain yang tidak ada")
            suggestions.append("   • Contoh: Kode item yang direferensikan belum ada di master")
            suggestions.append("\n📝 Cara memperbaiki:")
            suggestions.append("   1. Pastikan semua master data sudah ada")
            suggestions.append("   2. Atau import master data terlebih dahulu")
            suggestions.append("   3. Baru import data detail")

        # If no specific constraint info found, show generic message
        elif not unique_constraint_found and not suggestions:
            # Generic integrity error
            suggestions.append("\n❌ Data tidak sesuai dengan aturan database")
            if affected_rows:
                rows_display = ', '.join(map(str, sorted(affected_rows)[:10]))
                suggestions.append(f"\n📍 Baris yang bermasalah: {rows_display}")
            suggestions.append("\n📝 Periksa:")
            suggestions.append("   • Format data sesuai template")
            suggestions.append("   • Tidak ada duplikat")
            suggestions.append("   • Semua field wajib terisi")

    elif 'OperationalError' in error_type:
        user_message = "🔧 MASALAH SISTEM: Database timeout atau overload"

        if 'timeout' in error_message.lower() or 'time' in error_message.lower():
            suggestions.append("⚙️ JENIS MASALAH: Sistem/Server (waktu proses terlalu lama)")
            suggestions.append("🔍 PENJELASAN: Server kehabisan waktu saat memproses file Anda")
            suggestions.append("\n❌ Kemungkinan penyebab:")
            suggestions.append("   • File Anda terlalu besar untuk kapasitas server")
            suggestions.append("   • Server database sedang sibuk (banyak user aktif)")
            suggestions.append("   • Koneksi internet Anda lambat/tidak stabil")

            # Check file size from parse_result
            if parse_result and hasattr(parse_result, 'total_rincian'):
                total = parse_result.total_rincian
                suggestions.append(f"\n📊 File Anda: {total} rincian")

                if total > 10000:
                    num_files = (total // 5000) + 1
                    suggestions.append(f"   ⚠️ Ini file BESAR! Sebaiknya dipecah jadi {num_files} file")
                elif total > 5000:
                    suggestions.append("   ⚠️ File cukup besar, pertimbangkan dipecah")

            suggestions.append("\n📝 Solusi:")
            suggestions.append("   1. PECAH FILE menjadi bagian lebih kecil:")
            suggestions.append("      • Ideal: 2000-3000 baris per file")
            suggestions.append("      • Maksimal: 5000 baris per file")
            suggestions.append("   2. Import saat server tidak sibuk (malam/dini hari)")
            suggestions.append("   3. Pastikan koneksi internet stabil")

        elif 'lock' in error_message.lower():
            suggestions.append("⚙️ JENIS MASALAH: Sistem/Server (database sedang digunakan)")
            suggestions.append("🔍 PENJELASAN: Database sedang dikunci oleh proses lain")
            suggestions.append("\n❌ Kemungkinan penyebab:")
            suggestions.append("   • Ada user lain yang sedang import data")
            suggestions.append("   • Proses backup database sedang berjalan")
            suggestions.append("   • Maintenance sistem sedang berlangsung")
            suggestions.append("\n📝 Yang harus Anda lakukan:")
            suggestions.append("   1. Tunggu 2-5 menit")
            suggestions.append("   2. Refresh halaman dan coba lagi")
            suggestions.append("   3. Koordinasi dengan tim agar tidak import bersamaan")
            suggestions.append("   4. Hubungi administrator jika masih terkunci setelah 10 menit")

        elif 'disk' in error_message.lower() or 'space' in error_message.lower():
            suggestions.append("⚙️ JENIS MASALAH: Sistem/Server (kapasitas penuh)")
            suggestions.append("🔍 PENJELASAN: Server kehabisan ruang penyimpanan")
            suggestions.append("\n❌ INI BUKAN KESALAHAN ANDA!")
            suggestions.append("   • File Anda tidak bermasalah")
            suggestions.append("   • Server perlu dibersihkan atau upgrade storage")
            suggestions.append("\n📝 Yang harus Anda lakukan:")
            suggestions.append("   1. Screenshot error ini")
            suggestions.append("   2. SEGERA hubungi administrator sistem")
            suggestions.append("   3. Sertakan screenshot saat melapor")
            suggestions.append("   4. Tunggu admin membersihkan storage server")

        else:
            suggestions.append(f"\n❌ Error operasional database")
            suggestions.append(f"\n🔧 Detail: {error_message[:200]}")
            suggestions.append("\n📝 Solusi:")
            suggestions.append("   1. Screenshot error ini")
            suggestions.append("   2. Hubungi administrator sistem")
            suggestions.append("   3. Sertakan screenshot saat melapor")

    elif 'ValidationError' in error_type or 'ValueError' in error_type:
        user_message = "📝 MASALAH FILE ANDA: Format data tidak valid"
        suggestions.append("⚙️ JENIS MASALAH: File yang Anda upload (format atau isi data salah)")
        suggestions.append("🔍 PENJELASAN: Ada data di file Excel Anda yang tidak sesuai format yang dibutuhkan")

        # Parse validation errors
        if 'koefisien' in error_message.lower():
            affected_fields.append('koefisien')
            suggestions.append("\n❌ Nilai koefisien tidak valid")
            suggestions.append("\n🔍 Masalah pada kolom: Koefisien")
            suggestions.append("   • Koefisien harus berupa angka")
            suggestions.append("   • Harus positif (tidak boleh negatif)")
            suggestions.append("   • Tidak boleh berisi huruf atau karakter khusus")
            suggestions.append("\n✅ Format yang BENAR:")
            suggestions.append("   • 0.5")
            suggestions.append("   • 1.25")
            suggestions.append("   • 0.00008 atau 8e-05")
            suggestions.append("   • 2.5")
            suggestions.append("\n❌ Format yang SALAH:")
            suggestions.append("   • abc (huruf)")
            suggestions.append("   • -1.5 (negatif)")
            suggestions.append("   • 1,234,567 (pakai separator ribuan)")

        elif 'decimal' in error_message.lower() or 'numeric' in error_message.lower():
            suggestions.append("\n❌ Format angka tidak valid")
            suggestions.append("\n📝 Tips:")
            suggestions.append("   • Gunakan titik (.) untuk desimal, bukan koma")
            suggestions.append("   • Contoh benar: 1.5 bukan 1,5")
            suggestions.append("   • Tidak boleh ada spasi")
            suggestions.append("   • Tidak boleh ada huruf")

        # Extract row numbers from summary
        if summary and hasattr(summary, 'detail_errors') and summary.detail_errors:
            suggestions.append("\n📋 Detail error:")
            for i, error in enumerate(summary.detail_errors[:5], 1):
                suggestions.append(f"   {i}. {error}")

            if len(summary.detail_errors) > 5:
                remaining = len(summary.detail_errors) - 5
                suggestions.append(f"   ... dan {remaining} error lainnya")

        if affected_rows:
            rows_display = ', '.join(map(str, sorted(affected_rows)[:10]))
            if len(affected_rows) > 10:
                rows_display += f" ... (+{len(affected_rows)-10} lainnya)"
            suggestions.append(f"\n📍 Baris yang bermasalah: {rows_display}")

            suggestions.append("\n📝 Cara memperbaiki:")
            suggestions.append("   1. Buka file Excel Anda")
            suggestions.append(f"   2. Periksa baris {', '.join(map(str, sorted(affected_rows)[:5]))}")
            if affected_fields:
                suggestions.append(f"   3. Fokus ke kolom: {', '.join(affected_fields)}")
            suggestions.append("   4. Perbaiki format data sesuai contoh di atas")
            suggestions.append("   5. Save dan upload ulang")

    elif 'AttributeError' in error_type or 'TypeError' in error_type:
        user_message = "🔧 MASALAH SISTEM: Bug atau error teknis internal"
        suggestions.append("⚙️ JENIS MASALAH: Sistem (bug aplikasi atau format tidak terduga)")
        suggestions.append("🔍 PENJELASAN: Terjadi kesalahan teknis di dalam aplikasi")
        suggestions.append("\n❌ INI BUKAN KESALAHAN ANDA!")
        suggestions.append("   • Kemungkinan ada bug di sistem")
        suggestions.append("   • Atau format file Anda di luar ekspektasi sistem")
        suggestions.append("   • File Anda mungkin valid, tapi sistem belum mendukungnya")
        suggestions.append("\n📝 Yang harus Anda lakukan:")
        suggestions.append("   1. Screenshot error ini LENGKAP (termasuk detail teknis)")
        suggestions.append("   2. Simpan file Excel yang Anda upload")
        suggestions.append("   3. Hubungi administrator/developer dengan informasi:")
        suggestions.append("      • Screenshot error yang Anda dapat")
        suggestions.append("      • File Excel yang diupload (kirim ke admin)")
        suggestions.append("      • Waktu kejadian error")
        suggestions.append("      • Langkah-langkah yang Anda lakukan")

    elif 'MemoryError' in error_type:
        user_message = "🔧 MASALAH SISTEM: Server kehabisan memori"
        suggestions.append("⚙️ JENIS MASALAH: Kombinasi File + Server (file terlalu besar untuk kapasitas server)")
        suggestions.append("🔍 PENJELASAN: File Anda terlalu besar untuk kapasitas RAM server")
        if parse_result and hasattr(parse_result, 'total_rincian'):
            total = parse_result.total_rincian
            suggestions.append(f"\n📊 Ukuran file Anda: {total} rincian")
            if total > 20000:
                suggestions.append("   ⚠️ File SANGAT BESAR!")
        suggestions.append("\n❌ File Anda tidak salah, tapi terlalu besar!")
        suggestions.append("\n📝 Solusi WAJIB:")
        suggestions.append("   1. PECAH file menjadi beberapa file lebih kecil")
        suggestions.append("   2. Target: maksimal 2.000-3.000 baris per file")
        suggestions.append("   3. Import file satu per satu secara bertahap")
        suggestions.append("   4. Atau minta admin untuk upgrade kapasitas server")

    elif 'PermissionError' in error_type or 'PermissionDenied' in error_type:
        user_message = "🔒 MASALAH AKSES: Anda tidak punya izin"
        suggestions.append("⚙️ JENIS MASALAH: Hak akses (user Anda tidak memiliki permission)")
        suggestions.append("🔍 PENJELASAN: Akun Anda tidak memiliki izin untuk melakukan import data")
        suggestions.append("\n❌ INI BUKAN KESALAHAN FILE ANDA!")
        suggestions.append("   • File Anda benar")
        suggestions.append("   • Tapi akun Anda tidak diberi hak akses import")
        suggestions.append("\n📝 Yang harus Anda lakukan:")
        suggestions.append("   1. Hubungi administrator sistem")
        suggestions.append("   2. Minta diberikan hak akses/permission untuk import AHSP")
        suggestions.append("   3. Atau login dengan akun user lain yang memiliki akses")
        suggestions.append("   4. Setelah diberi akses, coba import ulang file Anda")

    else:
        # Generic catch-all error handler
        user_message = f"❌ Terjadi kesalahan: {error_type}"

        # Try to make it more user-friendly
        if 'cannot' in error_message.lower() or 'failed' in error_message.lower():
            suggestions.append("\n❌ Operasi gagal dijalankan")
        elif 'invalid' in error_message.lower():
            suggestions.append("\n❌ Ada data yang tidak valid")
        elif 'missing' in error_message.lower() or 'not found' in error_message.lower():
            suggestions.append("\n❌ Ada data yang hilang atau tidak ditemukan")
        else:
            suggestions.append(f"\n❌ {error_message[:200]}")

        suggestions.append("\n📝 Langkah troubleshooting:")
        suggestions.append("   1. Screenshot error ini (termasuk detail lengkap)")
        suggestions.append("   2. Simpan file Excel yang Anda coba upload")
        suggestions.append("   3. Coba dengan file lebih kecil (500 baris) untuk testing")
        suggestions.append("   4. Jika masih error, hubungi administrator dengan:")
        suggestions.append("      • Screenshot error")
        suggestions.append("      • File Excel")
        suggestions.append("      • Langkah-langkah yang Anda lakukan")

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


def format_error_as_html(analysis: ErrorAnalysis) -> str:
    """
    Format error analysis as clean, user-friendly HTML.

    Returns:
        Single HTML string with beautiful formatting
    """
    html_parts = []

    # Main error message with icon
    icon_map = {
        'critical': '🔴',
        'warning': '⚠️',
        'info': 'ℹ️'
    }
    icon = icon_map.get(analysis.severity, 'ℹ️')

    html_parts.append(f'<div class="error-message-container">')
    html_parts.append(f'<h5 class="error-title">{icon} {analysis.user_message}</h5>')

    # Parse suggestions which contain structured data
    if analysis.suggestions:
        suggestion_text = '\n'.join(analysis.suggestions)

        # Check if it's an IntegrityError with duplicate data
        if 'PENYEBAB ERROR:' in suggestion_text and 'Key' not in suggestion_text:
            # Extract duplicate field values
            lines = suggestion_text.split('\n')

            current_section = None
            for line in lines:
                line = line.strip()

                if '❌ PENYEBAB ERROR:' in line:
                    html_parts.append('<div class="error-section">')
                    html_parts.append('<h6 class="section-title">❌ Penyebab Error:</h6>')
                    current_section = 'cause'
                    continue

                elif 'Data dengan kombinasi nilai berikut SUDAH ADA' in line:
                    html_parts.append('<p class="section-desc">Data dengan kombinasi nilai berikut <strong>SUDAH ADA</strong> di database:</p>')
                    html_parts.append('<div class="duplicate-data-box">')
                    current_section = 'data'
                    continue

                elif '🔍 KEMUNGKINAN PENYEBAB:' in line:
                    if current_section == 'data':
                        html_parts.append('</div>')  # Close duplicate-data-box
                    html_parts.append('</div>')  # Close error-section
                    html_parts.append('<div class="error-section">')
                    html_parts.append('<h6 class="section-title">🔍 Kemungkinan Penyebab:</h6>')
                    html_parts.append('<ul class="cause-list">')
                    current_section = 'reason'
                    continue

                elif '📝 SOLUSI - Pilih salah satu:' in line:
                    if current_section == 'reason':
                        html_parts.append('</ul>')
                    html_parts.append('</div>')  # Close error-section
                    html_parts.append('<div class="error-section">')
                    html_parts.append('<h6 class="section-title">📝 Solusi - Pilih Salah Satu:</h6>')
                    current_section = 'solution'
                    continue

                elif 'OPSI' in line:
                    # Extract option number and title
                    if 'OPSI 1' in line:
                        html_parts.append('<div class="solution-option">')
                        html_parts.append('<div class="option-header">Opsi 1: Hapus data lama terlebih dahulu</div>')
                        html_parts.append('<ol class="option-steps">')
                        current_section = 'option1'
                    elif 'OPSI 2' in line:
                        html_parts.append('</ol></div>')  # Close previous option
                        html_parts.append('<div class="solution-option">')
                        html_parts.append('<div class="option-header">Opsi 2: Upload file dengan data BARU</div>')
                        html_parts.append('<ol class="option-steps">')
                        current_section = 'option2'
                    elif 'OPSI 3' in line:
                        html_parts.append('</ol></div>')  # Close previous option
                        html_parts.append('<div class="solution-option">')
                        html_parts.append('<div class="option-header">Opsi 3: Abaikan jika data sudah benar</div>')
                        html_parts.append('<ul class="option-steps">')
                        current_section = 'option3'
                    continue

                elif line.startswith('-------') or not line:
                    continue

                # Content lines
                if current_section == 'data' and line.startswith('•'):
                    # Duplicate data field
                    html_parts.append(f'<div class="field-value">{line}</div>')

                elif current_section == 'reason' and line.startswith(('1.', '2.', '3.')):
                    # Remove number and checkmark/warning icon
                    clean_line = line[3:].strip()
                    if clean_line.startswith('✅'):
                        clean_line = clean_line[2:].strip()
                        html_parts.append(f'<li class="likely">✅ {clean_line}</li>')
                    elif clean_line.startswith('⚠️'):
                        clean_line = clean_line[2:].strip()
                        html_parts.append(f'<li class="possible">⚠️ {clean_line}</li>')
                    else:
                        html_parts.append(f'<li>{clean_line}</li>')

                elif current_section in ('option1', 'option2') and line.startswith(('1.', '2.', '3.', '4.')):
                    clean_line = line[3:].strip()
                    html_parts.append(f'<li>{clean_line}</li>')

                elif current_section == 'option3' and line.startswith('•'):
                    clean_line = line[2:].strip()
                    html_parts.append(f'<li>{clean_line}</li>')

            # Close any open tags
            if current_section == 'option3':
                html_parts.append('</ul></div>')
            elif current_section in ('option1', 'option2'):
                html_parts.append('</ol></div>')
            html_parts.append('</div>')  # Close error-section

        else:
            # Generic error formatting
            html_parts.append('<div class="error-details">')

            # Technical details
            if analysis.error_type != 'Unknown':
                html_parts.append(f'<p><strong>🔧 Tipe Error:</strong> <code>{analysis.error_type}</code></p>')

            # Affected rows
            if analysis.affected_rows:
                rows_str = ', '.join(map(str, analysis.affected_rows[:10]))
                if len(analysis.affected_rows) > 10:
                    rows_str += f", ... (+{len(analysis.affected_rows) - 10} lainnya)"
                html_parts.append(f'<p><strong>📍 Baris bermasalah:</strong> {rows_str}</p>')

            # Suggestions
            if analysis.suggestions:
                html_parts.append('<div class="suggestions">')
                html_parts.append('<h6>💡 Langkah Perbaikan:</h6>')
                html_parts.append('<ul>')
                for suggestion in analysis.suggestions:
                    clean_suggestion = suggestion.strip()
                    if clean_suggestion and not clean_suggestion.startswith(('📝', '🔧', '💡')):
                        html_parts.append(f'<li>{clean_suggestion}</li>')
                html_parts.append('</ul>')
                html_parts.append('</div>')

            html_parts.append('</div>')

    html_parts.append('</div>')  # Close error-message-container

    return '\n'.join(html_parts)


def format_error_for_user(analysis: ErrorAnalysis) -> List[str]:
    """
    Format error analysis as user-friendly messages.

    DEPRECATED: Use format_error_as_html() for better formatting.
    Kept for backward compatibility.

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
    'format_error_for_user',
    'format_error_as_html'
]
