"""
Environment-aware settings loader.

Usage:
    DJANGO_ENV=production python manage.py runserver
"""

from __future__ import annotations

import os

ENVIRONMENT = os.getenv("DJANGO_ENV", "development").lower()

if ENVIRONMENT in {"prod", "production"}:
    from .production import *  # noqa: F401,F403
else:
    from .development import *  # noqa: F401,F403
