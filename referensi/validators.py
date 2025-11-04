"""
Security validators for AHSP referensi app.

This module provides comprehensive validation for file uploads including:
- File size limits
- Extension whitelist
- Content security (malicious formulas, zip bombs)
- Row limits for Excel files
"""

from __future__ import annotations

import mimetypes
import zipfile
from typing import Any

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.utils.translation import gettext_lazy as _

try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False


class AHSPFileValidator:
    """
    Comprehensive file validator for AHSP Excel uploads.

    Features:
    - File size validation (default: 50MB max)
    - Extension whitelist (xlsx, xls)
    - Content type validation
    - Malicious formula detection
    - Zip bomb detection
    - Row limit enforcement (default: 50,000 rows)

    Usage:
        validator = AHSPFileValidator()
        try:
            validator.validate(uploaded_file)
        except ValidationError as e:
            # Handle validation error
            print(e.messages)
    """

    # Configuration constants
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = ['xlsx', 'xls']
    ALLOWED_MIME_TYPES = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',  # .xlsx
        'application/vnd.ms-excel',  # .xls
    ]
    MAX_ROWS = 50000
    MAX_COLUMNS = 100

    # Zip bomb detection thresholds
    MAX_COMPRESSION_RATIO = 100  # Maximum compression ratio (uncompressed/compressed)
    MAX_UNCOMPRESSED_SIZE = 500 * 1024 * 1024  # 500MB uncompressed

    # Dangerous formula patterns
    DANGEROUS_FORMULA_PATTERNS = [
        'WEBSERVICE',
        'IMPORTXML',
        'IMPORTDATA',
        'IMPORTFEED',
        'IMPORTHTML',
        'IMPORTRANGE',
        'HYPERLINK',
        'EXEC',
        'SYSTEM',
        'CALL',
        'REGISTER',
    ]

    def __init__(
        self,
        max_file_size: int | None = None,
        allowed_extensions: list[str] | None = None,
        max_rows: int | None = None,
        max_columns: int | None = None,
    ):
        """
        Initialize validator with optional custom limits.

        Args:
            max_file_size: Maximum file size in bytes
            allowed_extensions: List of allowed file extensions
            max_rows: Maximum number of rows allowed
            max_columns: Maximum number of columns allowed
        """
        self.max_file_size = max_file_size or self.MAX_FILE_SIZE
        self.allowed_extensions = allowed_extensions or self.ALLOWED_EXTENSIONS
        self.max_rows = max_rows or self.MAX_ROWS
        self.max_columns = max_columns or self.MAX_COLUMNS

    def validate(self, file: UploadedFile) -> None:
        """
        Run all validation checks on the uploaded file.

        Args:
            file: Django UploadedFile instance

        Raises:
            ValidationError: If any validation check fails
        """
        self.validate_file_exists(file)
        self.validate_file_size(file)
        self.validate_extension(file)
        self.validate_mime_type(file)
        self.validate_zip_bomb(file)
        self.validate_content_security(file)
        self.validate_row_limit(file)

    def validate_file_exists(self, file: UploadedFile) -> None:
        """
        Ensure file was actually uploaded.

        Args:
            file: Django UploadedFile instance

        Raises:
            ValidationError: If file is None or empty
        """
        if not file:
            raise ValidationError(
                _("Tidak ada file yang diunggah."),
                code='no_file'
            )

        if file.size == 0:
            raise ValidationError(
                _("File kosong atau rusak."),
                code='empty_file'
            )

    def validate_file_size(self, file: UploadedFile) -> None:
        """
        Validate file size is within limits.

        Args:
            file: Django UploadedFile instance

        Raises:
            ValidationError: If file exceeds size limit
        """
        if file.size > self.max_file_size:
            max_size_mb = self.max_file_size / (1024 * 1024)
            actual_size_mb = file.size / (1024 * 1024)
            raise ValidationError(
                _(f"File terlalu besar ({actual_size_mb:.2f} MB). "
                  f"Ukuran maksimum: {max_size_mb:.0f} MB."),
                code='file_too_large'
            )

    def validate_extension(self, file: UploadedFile) -> None:
        """
        Validate file extension is in whitelist.

        Args:
            file: Django UploadedFile instance

        Raises:
            ValidationError: If extension is not allowed
        """
        filename = file.name.lower()
        extension = filename.split('.')[-1] if '.' in filename else ''

        if extension not in self.allowed_extensions:
            allowed_str = ', '.join(self.allowed_extensions)
            raise ValidationError(
                _(f"Ekstensi file tidak didukung. "
                  f"Hanya file {allowed_str} yang diperbolehkan."),
                code='invalid_extension'
            )

    def validate_mime_type(self, file: UploadedFile) -> None:
        """
        Validate MIME type matches expected Excel types.

        Args:
            file: Django UploadedFile instance

        Raises:
            ValidationError: If MIME type is invalid
        """
        # Get MIME type from file
        mime_type = file.content_type

        # Also check using mimetypes library
        guessed_type, _ = mimetypes.guess_type(file.name)

        # Accept if either matches
        if mime_type not in self.ALLOWED_MIME_TYPES and guessed_type not in self.ALLOWED_MIME_TYPES:
            raise ValidationError(
                "Tipe file tidak valid. File harus berupa Excel (.xlsx atau .xls).",
                code='invalid_mime_type'
            )

    def validate_zip_bomb(self, file: UploadedFile) -> None:
        """
        Detect potential zip bomb attacks.

        .xlsx files are actually ZIP archives. This checks for:
        - Excessive compression ratios
        - Extremely large uncompressed sizes

        Args:
            file: Django UploadedFile instance

        Raises:
            ValidationError: If file appears to be a zip bomb
        """
        # Only check .xlsx files (which are ZIP archives)
        if not file.name.lower().endswith('.xlsx'):
            return

        try:
            # Seek to beginning
            file.seek(0)

            # Try to open as ZIP
            with zipfile.ZipFile(file, 'r') as zip_ref:
                compressed_size = file.size
                uncompressed_size = sum(info.file_size for info in zip_ref.infolist())

                # Check uncompressed size
                if uncompressed_size > self.MAX_UNCOMPRESSED_SIZE:
                    raise ValidationError(
                        _(f"File terlalu besar setelah diekstrak. "
                          f"Kemungkinan file berbahaya (zip bomb)."),
                        code='zip_bomb_size'
                    )

                # Check compression ratio
                if compressed_size > 0:
                    ratio = uncompressed_size / compressed_size
                    if ratio > self.MAX_COMPRESSION_RATIO:
                        raise ValidationError(
                            _(f"Rasio kompresi file mencurigakan ({ratio:.0f}x). "
                              f"Kemungkinan file berbahaya (zip bomb)."),
                            code='zip_bomb_ratio'
                        )

        except zipfile.BadZipFile:
            raise ValidationError(
                _("File Excel rusak atau tidak valid."),
                code='corrupted_file'
            )

        finally:
            # Always seek back to beginning
            file.seek(0)

    def validate_content_security(self, file: UploadedFile) -> None:
        """
        Scan for malicious formulas and content.

        Detects dangerous Excel formulas that could:
        - Fetch external data
        - Execute system commands
        - Access sensitive information

        Args:
            file: Django UploadedFile instance

        Raises:
            ValidationError: If dangerous content is detected
        """
        if not OPENPYXL_AVAILABLE:
            # Skip if openpyxl not installed
            return

        # Only check .xlsx files
        if not file.name.lower().endswith('.xlsx'):
            return

        try:
            file.seek(0)
            workbook = openpyxl.load_workbook(file, data_only=False)

            for sheet in workbook.worksheets:
                for row in sheet.iter_rows():
                    for cell in row:
                        if cell.value and isinstance(cell.value, str):
                            # Check if cell contains formula
                            if cell.value.startswith('='):
                                formula_upper = cell.value.upper()

                                # Check for dangerous patterns
                                for pattern in self.DANGEROUS_FORMULA_PATTERNS:
                                    if pattern in formula_upper:
                                        raise ValidationError(
                                            _(f"File mengandung formula berbahaya: {pattern}. "
                                              f"File tidak dapat diproses untuk keamanan."),
                                            code='dangerous_formula'
                                        )

        except ValidationError:
            raise

        except Exception as e:
            raise ValidationError(
                _(f"Gagal memvalidasi konten file: {str(e)}"),
                code='content_validation_error'
            )

        finally:
            file.seek(0)

    def validate_row_limit(self, file: UploadedFile) -> None:
        """
        Ensure file doesn't exceed maximum row limit.

        Args:
            file: Django UploadedFile instance

        Raises:
            ValidationError: If file has too many rows
        """
        if not OPENPYXL_AVAILABLE:
            # Skip if openpyxl not installed
            return

        # Only check .xlsx files
        if not file.name.lower().endswith('.xlsx'):
            return

        try:
            file.seek(0)
            workbook = openpyxl.load_workbook(file, read_only=True)

            for sheet in workbook.worksheets:
                # Get max row
                max_row = sheet.max_row
                max_col = sheet.max_column

                if max_row > self.max_rows:
                    raise ValidationError(
                        _(f"File memiliki terlalu banyak baris ({max_row:,}). "
                          f"Maksimum: {self.max_rows:,} baris."),
                        code='too_many_rows'
                    )

                if max_col > self.max_columns:
                    raise ValidationError(
                        _(f"File memiliki terlalu banyak kolom ({max_col}). "
                          f"Maksimum: {self.max_columns} kolom."),
                        code='too_many_columns'
                    )

        except ValidationError:
            raise

        except Exception as e:
            # Don't fail validation if we can't read the file
            # (it will fail in parsing stage anyway)
            pass

        finally:
            file.seek(0)


def validate_ahsp_file(file: UploadedFile) -> None:
    """
    Convenience function for validating AHSP files.

    Usage:
        from referensi.validators import validate_ahsp_file

        try:
            validate_ahsp_file(request.FILES['excel_file'])
        except ValidationError as e:
            # Handle error

    Args:
        file: Django UploadedFile instance

    Raises:
        ValidationError: If validation fails
    """
    validator = AHSPFileValidator()
    validator.validate(file)
