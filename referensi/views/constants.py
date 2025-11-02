"""Shared constants for referensi views."""

from django.conf import settings

TAB_JOBS = "jobs"
TAB_ITEMS = "items"

# PHASE 1: Use centralized config from settings
# Reduced from 150 to 50/100 for better memory usage (30-40% reduction)
REFERENSI_CONFIG = getattr(settings, 'REFERENSI_CONFIG', {})

JOB_DISPLAY_LIMIT = REFERENSI_CONFIG.get('display_limits', {}).get('jobs', 50)
ITEM_DISPLAY_LIMIT = REFERENSI_CONFIG.get('display_limits', {}).get('items', 100)

PENDING_IMPORT_SESSION_KEY = "referensi_pending_import"
