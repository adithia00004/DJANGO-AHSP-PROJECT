"""
Custom exceptions for detail_project app.

This module defines custom exception classes for better error handling
and user-friendly error messages in the Deep Copy feature.

Usage:
    from detail_project.exceptions import ValidationError, USER_MESSAGES

    if not valid:
        raise ValidationError(
            code=1001,
            message="Technical message for logs",
            user_message=USER_MESSAGES[1001],
            details={'field': 'new_name'}
        )
"""

# ==============================================================================
# ERROR CODE DEFINITIONS
# ==============================================================================

ERROR_CODES = {
    # 1000-1999: Input Validation Errors (User fault - 400 status)
    1001: "EMPTY_PROJECT_NAME",
    1002: "INVALID_DATE_FORMAT",
    1003: "INVALID_DATE_RANGE",
    1004: "PROJECT_NAME_TOO_LONG",
    1005: "INVALID_BOOLEAN_VALUE",
    1006: "INVALID_PROJECT_ID",
    1007: "XSS_DETECTED_IN_INPUT",
    1008: "INVALID_JSON_PAYLOAD",
    1009: "MISSING_REQUIRED_FIELD",
    1010: "INVALID_NUMERIC_VALUE",

    # 2000-2999: Permission/Access Errors (User fault - 403/404 status)
    2001: "PROJECT_NOT_FOUND",
    2002: "NOT_PROJECT_OWNER",
    2003: "AUTHENTICATION_REQUIRED",
    2004: "INSUFFICIENT_PERMISSIONS",
    2005: "PROJECT_ACCESS_DENIED",

    # 3000-3999: Business Logic Errors (Business rule violation - 400 status)
    3001: "DUPLICATE_PROJECT_NAME",
    3002: "SOURCE_PROJECT_INVALID",
    3003: "PROJECT_TOO_LARGE",
    3004: "EMPTY_PROJECT_WARNING",
    3005: "ORPHANED_DATA_DETECTED",
    3006: "INVALID_PRICING_VALUES",
    3007: "MISSING_REQUIRED_DATA",
    3008: "INVALID_PROJECT_STATE",
    3009: "CIRCULAR_REFERENCE_DETECTED",
    3010: "DATA_INTEGRITY_VIOLATION",

    # 4000-4999: Database Errors (System issue - 500 status)
    4001: "DATABASE_CONNECTION_ERROR",
    4002: "INTEGRITY_CONSTRAINT_VIOLATION",
    4003: "TRANSACTION_DEADLOCK",
    4004: "DATABASE_TIMEOUT",
    4005: "FOREIGN_KEY_VIOLATION",
    4006: "UNIQUE_CONSTRAINT_VIOLATION",
    4007: "DATABASE_OPERATIONAL_ERROR",
    4008: "DATABASE_PROGRAMMING_ERROR",

    # 5000-5999: System/Resource Errors (System issue - 500 status)
    5001: "OPERATION_TIMEOUT",
    5002: "OUT_OF_MEMORY",
    5003: "DISK_FULL",
    5004: "CONNECTION_POOL_EXHAUSTED",
    5005: "RATE_LIMIT_EXCEEDED",
    5006: "SYSTEM_OVERLOAD",
    5007: "SERVICE_UNAVAILABLE",

    # 9000-9999: Unknown/Unexpected Errors (500 status)
    9999: "UNKNOWN_ERROR",
}

# ==============================================================================
# USER-FRIENDLY ERROR MESSAGES (Indonesian)
# ==============================================================================

USER_MESSAGES = {
    # Input Validation Errors
    1001: "Nama project tidak boleh kosong. Silakan masukkan nama project.",
    1002: "Format tanggal tidak valid. Gunakan format YYYY-MM-DD (contoh: 2025-06-15).",
    1003: "Tanggal tidak valid. Pastikan tanggal dalam rentang yang wajar (1900-2100).",
    1004: "Nama project terlalu panjang. Maksimal 200 karakter.",
    1005: "Nilai copy_jadwal harus berupa true atau false.",
    1006: "ID project tidak valid.",
    1007: "Nama project mengandung karakter tidak diperbolehkan (< atau >).",
    1008: "Format data tidak valid. Pastikan data dikirim dalam format JSON yang benar.",
    1009: "Field yang diperlukan tidak diisi. Silakan lengkapi semua field yang wajib.",
    1010: "Nilai numerik tidak valid. Pastikan menggunakan angka yang benar.",

    # Permission/Access Errors
    2001: "Project tidak ditemukan atau Anda tidak memiliki akses.",
    2002: "Anda bukan pemilik project ini dan tidak dapat melakukan copy.",
    2003: "Silakan login terlebih dahulu untuk menggunakan fitur ini.",
    2004: "Anda tidak memiliki izin untuk melakukan operasi ini.",
    2005: "Akses ke project ini ditolak.",

    # Business Logic Errors
    3001: "Nama project sudah digunakan. Silakan gunakan nama yang berbeda.",
    3002: "Project sumber tidak valid atau tidak dapat di-copy.",
    3003: "Project sangat besar (lebih dari 1000 pekerjaan). Proses copy akan memakan waktu lama. Harap bersabar.",
    3004: "Project ini kosong (tidak ada pekerjaan). Copy akan membuat project kosong.",
    3005: "Beberapa data tidak lengkap dan tidak dapat di-copy. Silakan periksa hasil setelah proses selesai.",
    3006: "Nilai pricing tidak valid. PPN dan Markup harus antara 0-100%.",
    3007: "Data project tidak lengkap. Beberapa komponen mungkin tidak ter-copy dengan sempurna.",
    3008: "Status project tidak memungkinkan untuk di-copy saat ini.",
    3009: "Terdeteksi referensi melingkar pada data. Hubungi administrator.",
    3010: "Integritas data tidak terpenuhi. Beberapa data mungkin corrupt.",

    # Database Errors
    4001: "Koneksi ke database bermasalah. Silakan coba lagi dalam beberapa saat.",
    4002: "Terjadi konflik data pada database. Silakan coba dengan nama project yang berbeda.",
    4003: "Database sedang sibuk memproses request lain. Silakan tunggu dan coba lagi.",
    4004: "Operasi database memakan waktu terlalu lama dan dibatalkan. Project mungkin terlalu besar.",
    4005: "Terjadi kesalahan integritas referensi data. Hubungi administrator.",
    4006: "Data yang sama sudah ada di database. Gunakan nilai yang berbeda.",
    4007: "Terjadi kesalahan operasional database. Silakan coba lagi atau hubungi administrator.",
    4008: "Terjadi kesalahan program database. Hubungi administrator segera.",

    # System/Resource Errors
    5001: "Operasi memakan waktu terlalu lama dan dibatalkan. Coba copy project yang lebih kecil atau hubungi administrator.",
    5002: "Server kehabisan memori. Silakan hubungi administrator untuk meningkatkan kapasitas.",
    5003: "Ruang penyimpanan server penuh. Hubungi administrator untuk pembersihan.",
    5004: "Server sedang sangat sibuk. Silakan tunggu beberapa menit dan coba lagi.",
    5005: "Terlalu banyak request dalam waktu singkat. Tunggu sebentar sebelum mencoba lagi.",
    5006: "Sistem sedang overload. Silakan coba lagi nanti.",
    5007: "Layanan sedang tidak tersedia. Hubungi administrator.",

    # Unknown Errors
    9999: "Terjadi kesalahan tidak terduga. Silakan hubungi administrator dengan kode error dan waktu kejadian.",
}

# ==============================================================================
# SUPPORT MESSAGES (Additional context for critical errors)
# ==============================================================================

SUPPORT_MESSAGES = {
    4001: "Jika masalah berlanjut, hubungi support dengan kode error dan waktu kejadian.",
    4002: "Jika masalah berlanjut, hubungi support dengan detail data yang ingin dicopy.",
    4003: "Jika masalah terus terjadi, mungkin ada proses berat di server. Hubungi administrator.",
    4004: "Pertimbangkan untuk membagi project menjadi lebih kecil atau hubungi administrator.",
    4005: "Hubungi administrator segera dengan kode error ini.",
    4006: "Jika masalah berlanjut setelah mengubah nama, hubungi support.",
    4007: "Jika masalah berlanjut, hubungi support dengan kode error ini.",
    4008: "Hubungi administrator segera. Ini adalah bug sistem.",

    5001: "Jika project tidak terlalu besar, hubungi administrator untuk cek timeout setting.",
    5002: "Hubungi administrator segera untuk upgrade server.",
    5003: "Hubungi administrator segera untuk pembersihan disk.",
    5004: "Jika server terus sibuk, hubungi administrator untuk scaling.",
    5005: "Jika Anda perlu copy banyak project sekaligus, hubungi administrator.",
    5006: "Coba lagi di luar jam sibuk atau hubungi administrator.",
    5007: "Hubungi administrator untuk cek status layanan.",

    9999: "Hubungi support dengan informasi: error_id, user_id, project_id, dan waktu kejadian.",
}

# ==============================================================================
# CUSTOM EXCEPTION CLASSES
# ==============================================================================

class DeepCopyError(Exception):
    """
    Base exception for all deep copy operations.

    All custom exceptions inherit from this class.

    Attributes:
        code (int): Error code from ERROR_CODES
        message (str): Technical message for logging
        user_message (str): User-friendly message from USER_MESSAGES
        details (dict): Additional context for debugging
        support_message (str): Support/action message for critical errors
    """

    def __init__(self, code, message, user_message=None, details=None, support_message=None):
        """
        Initialize DeepCopyError.

        Args:
            code: Error code from ERROR_CODES dictionary
            message: Technical message for logs and developers
            user_message: User-friendly message (defaults to USER_MESSAGES[code])
            details: Additional context dict (optional)
            support_message: Support message (defaults to SUPPORT_MESSAGES[code] if exists)
        """
        self.code = code
        self.message = message
        self.user_message = user_message or USER_MESSAGES.get(code, USER_MESSAGES[9999])
        self.details = details or {}
        self.support_message = support_message or SUPPORT_MESSAGES.get(code, None)

        super().__init__(message)

    def to_dict(self):
        """
        Convert exception to dictionary for JSON response.

        Returns:
            dict: Dictionary with error information
        """
        result = {
            'error_code': self.code,
            'error': self.user_message,
            'error_type': ERROR_CODES.get(self.code, 'UNKNOWN'),
        }

        if self.details:
            result['details'] = self.details

        if self.support_message:
            result['support_message'] = self.support_message

        return result

    def get_http_status(self):
        """
        Get appropriate HTTP status code based on error code.

        Returns:
            int: HTTP status code (400, 403, 404, or 500)
        """
        if 1000 <= self.code < 2000:
            return 400  # Bad Request - Input validation
        elif 2000 <= self.code < 3000:
            if self.code == 2001:
                return 404  # Not Found
            return 403  # Forbidden - Permission errors
        elif 3000 <= self.code < 4000:
            return 400  # Bad Request - Business logic
        else:
            return 500  # Internal Server Error - System/DB errors


class DeepCopyValidationError(DeepCopyError):
    """
    Exception for input validation errors.

    Use for: empty fields, invalid format, wrong data type, etc.
    HTTP Status: 400 Bad Request
    Error Codes: 1000-1999
    """
    pass


class DeepCopyPermissionError(DeepCopyError):
    """
    Exception for permission and access errors.

    Use for: not owner, not authenticated, insufficient permissions, etc.
    HTTP Status: 403 Forbidden or 404 Not Found
    Error Codes: 2000-2999
    """
    pass


class DeepCopyBusinessError(DeepCopyError):
    """
    Exception for business logic violations.

    Use for: duplicate name, invalid state, data integrity issues, etc.
    HTTP Status: 400 Bad Request
    Error Codes: 3000-3999
    """
    pass


class DeepCopyDatabaseError(DeepCopyError):
    """
    Exception for database-related errors.

    Use for: connection errors, deadlocks, constraint violations, etc.
    HTTP Status: 500 Internal Server Error
    Error Codes: 4000-4999
    """
    pass


class DeepCopySystemError(DeepCopyError):
    """
    Exception for system and resource errors.

    Use for: timeout, out of memory, disk full, etc.
    HTTP Status: 500 Internal Server Error
    Error Codes: 5000-5999
    """
    pass


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_error_response(exception, error_id=None):
    """
    Convert exception to JSON response dictionary.

    Args:
        exception: DeepCopyError instance
        error_id: Optional unique error ID for support tracking

    Returns:
        tuple: (response_dict, http_status_code)
    """
    response = {
        'ok': False,
        **exception.to_dict()
    }

    if error_id:
        response['error_id'] = error_id

    return response, exception.get_http_status()


def classify_database_error(db_error):
    """
    Classify Django database exception to appropriate custom exception.

    Args:
        db_error: Django database exception

    Returns:
        DeepCopyDatabaseError: Classified custom exception
    """
    from django.db import IntegrityError, OperationalError, ProgrammingError, DataError

    error_str = str(db_error).lower()

    if isinstance(db_error, IntegrityError):
        if 'unique' in error_str:
            return DeepCopyDatabaseError(
                code=4006,
                message=f"Unique constraint violation: {str(db_error)}",
                user_message=USER_MESSAGES[4006],
                details={'db_error': str(db_error)}
            )
        elif 'foreign key' in error_str:
            return DeepCopyDatabaseError(
                code=4005,
                message=f"Foreign key violation: {str(db_error)}",
                user_message=USER_MESSAGES[4005],
                details={'db_error': str(db_error)}
            )
        else:
            return DeepCopyDatabaseError(
                code=4002,
                message=f"Integrity constraint violation: {str(db_error)}",
                user_message=USER_MESSAGES[4002],
                details={'db_error': str(db_error)}
            )

    elif isinstance(db_error, OperationalError):
        if 'deadlock' in error_str:
            return DeepCopyDatabaseError(
                code=4003,
                message=f"Database deadlock: {str(db_error)}",
                user_message=USER_MESSAGES[4003],
                details={'db_error': str(db_error)}
            )
        elif 'timeout' in error_str or 'timed out' in error_str:
            return DeepCopyDatabaseError(
                code=4004,
                message=f"Database timeout: {str(db_error)}",
                user_message=USER_MESSAGES[4004],
                details={'db_error': str(db_error)}
            )
        else:
            return DeepCopyDatabaseError(
                code=4007,
                message=f"Database operational error: {str(db_error)}",
                user_message=USER_MESSAGES[4007],
                details={'db_error': str(db_error)}
            )

    elif isinstance(db_error, ProgrammingError):
        return DeepCopyDatabaseError(
            code=4008,
            message=f"Database programming error: {str(db_error)}",
            user_message=USER_MESSAGES[4008],
            details={'db_error': str(db_error)}
        )

    else:
        # Generic database error
        return DeepCopyDatabaseError(
            code=4001,
            message=f"Database connection error: {str(db_error)}",
            user_message=USER_MESSAGES[4001],
            details={'db_error': str(db_error)}
        )


def classify_system_error(system_error):
    """
    Classify system exception to appropriate custom exception.

    Args:
        system_error: System exception (MemoryError, OSError, etc.)

    Returns:
        DeepCopySystemError: Classified custom exception
    """
    error_str = str(system_error).lower()

    if isinstance(system_error, MemoryError):
        return DeepCopySystemError(
            code=5002,
            message=f"Out of memory: {str(system_error)}",
            user_message=USER_MESSAGES[5002],
            details={'error': str(system_error)}
        )

    elif isinstance(system_error, TimeoutError):
        return DeepCopySystemError(
            code=5001,
            message=f"Operation timeout: {str(system_error)}",
            user_message=USER_MESSAGES[5001],
            details={'error': str(system_error)}
        )

    elif isinstance(system_error, OSError):
        if 'disk full' in error_str or 'no space' in error_str:
            return DeepCopySystemError(
                code=5003,
                message=f"Disk full: {str(system_error)}",
                user_message=USER_MESSAGES[5003],
                details={'error': str(system_error)}
            )
        else:
            return DeepCopySystemError(
                code=5007,
                message=f"Service unavailable: {str(system_error)}",
                user_message=USER_MESSAGES[5007],
                details={'error': str(system_error)}
            )

    else:
        # Generic system error
        return DeepCopySystemError(
            code=5006,
            message=f"System overload: {str(system_error)}",
            user_message=USER_MESSAGES[5006],
            details={'error': str(system_error)}
        )
