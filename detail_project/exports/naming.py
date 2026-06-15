"""WP-B5 inc-B5c — canonical export filename builder.

Convention (B-5): the locked owner decision is project name plus export date:
``NamaProject_YYYY-MM-DD.ext``. Report type remains represented by the selected
export option and document contents.
"""
from __future__ import annotations

import re
from datetime import date as _date, datetime


def sanitize_for_filename(text, fallback: str = "Project") -> str:
    """Filesystem-safe slug: word chars + hyphen kept, runs collapsed to '_'."""
    s = re.sub(r"[^\w\-]+", "_", str(text or "").strip(), flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or fallback


def build_export_filename(project_name, doc_label, ext, when=None) -> str:
    """Return the locked ``NamaProject_YYYY-MM-DD.ext`` convention.

    ``doc_label`` remains accepted for compatibility with existing callers but
    is intentionally omitted from the downloaded filename.
    """
    if when is None:
        when = _date.today()
    elif isinstance(when, datetime):
        when = when.date()
    name = sanitize_for_filename(project_name)
    return f"{name}_{when.strftime('%Y-%m-%d')}.{str(ext).lstrip('.')}"
