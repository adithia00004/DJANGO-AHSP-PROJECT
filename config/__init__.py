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

# Sentry diinisialisasi di sini, bukan di settings, supaya SEMUA entrypoint
# terlindungi seragam: gunicorn, worker celery, beat, dan management command.
#
# Sebelumnya `init_sentry()` ada tapi tidak pernah dipanggil dari mana pun,
# sehingga `sentry_sdk.capture_exception()` di ExceptionHandlerMiddleware adalah
# no-op -- produksi akan buta total terhadap error. Ditemukan pada sapuan
# pra-launching 2026-08-11.
#
# Aman dipanggil tanpa syarat: fungsinya keluar lebih awal bila SENTRY_DSN
# kosong, jadi dev dan test tidak terpengaruh.
try:
    from .sentry_config import init_sentry

    init_sentry()
except Exception:  # pragma: no cover - observabilitas tak boleh menjatuhkan app
    pass

__all__ = ('celery_app',)
