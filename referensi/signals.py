"""
Django signals for referensi app.

PHASE 3: Automatic cache invalidation when data changes.
"""

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from referensi.models import AHSPReferensi, RincianReferensi
from referensi.services.cache_helpers import ReferensiCache


@receiver([post_save, post_delete], sender=AHSPReferensi)
def invalidate_ahsp_cache(sender, instance, **kwargs):
    """
    Invalidate cache when AHSP data changes.

    Called automatically after:
    - Creating new AHSP record
    - Updating existing AHSP record
    - Deleting AHSP record

    PHASE 3: Ensures cache is always fresh.
    """
    # Invalidate all caches related to AHSP data
    ReferensiCache.invalidate_all()


@receiver([post_save, post_delete], sender=RincianReferensi)
def invalidate_rincian_cache(sender, instance, **kwargs):
    """
    Invalidate cache when Rincian data changes.

    Called automatically after:
    - Creating new Rincian record
    - Updating existing Rincian record
    - Deleting Rincian record

    PHASE 3: Ensures cache is always fresh.

    Note: We invalidate AHSP-related caches because rincian changes
    might affect category counts and anomaly detection.
    """
    # Invalidate relevant caches
    # (rincian changes might affect dropdown data indirectly)
    ReferensiCache.invalidate_all()
