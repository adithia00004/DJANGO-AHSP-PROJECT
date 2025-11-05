"""
Django configuration package initialization.

PHASE 5: Auto-load Celery app
"""

from __future__ import annotations

# This will make sure the app is always imported when
# Django starts so that shared_task will use this app.
try:
    from .celery import app as celery_app
except ModuleNotFoundError as exc:
    if exc.name != "celery":
        raise
    celery_app = None  # Celery not installed; allow Django startup without it.

__all__ = ('celery_app',)
