"""WP-B5 inc-B5a — Centralized export error handling.

Exports must never leak raw exception text to the client or into a generated
document. Use these helpers to log full detail server-side under a short
correlation ID and surface only a safe, generic message that references that ID
(so users/support can correlate without exposing internals).
"""
from __future__ import annotations

import logging
import uuid

from django.http import JsonResponse

logger = logging.getLogger("detail_project.exports")

GENERIC_EXPORT_MESSAGE = "Gagal membuat file export. Silakan coba lagi atau hubungi admin."


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:12]


def log_export_error(exc, *, context: str = "", correlation_id: str | None = None) -> str:
    """Log an export failure with full detail under a correlation ID; return the ID."""
    cid = correlation_id or new_correlation_id()
    logger.error(
        "Export error [%s]%s: %s",
        cid,
        f" ({context})" if context else "",
        exc,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    return cid


def export_error_response(exc, *, context: str = "", status: int = 500, user_message: str | None = None):
    """JSON error response that references a correlation ID — never leaks ``str(exc)``."""
    cid = log_export_error(exc, context=context)
    return JsonResponse(
        {
            "ok": False,
            "error": user_message or GENERIC_EXPORT_MESSAGE,
            "correlation_id": cid,
        },
        status=status,
    )
