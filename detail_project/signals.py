from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from django.db import transaction
from .models import (
    DetailAHSPProject,
    HargaItemProject,
    VolumePekerjaan,
    Pekerjaan,
    ProjectPricing,
    DetailAHSPExpanded,
    TahapPelaksanaan,
    PekerjaanTahapan,
)
import logging

logger = logging.getLogger(__name__)

def _clear_rekap_cache(project_id):
    def _clear():
        cache.delete(f"rekap:{project_id}:v1")
        cache.delete(f"rekap:{project_id}:v2")
    transaction.on_commit(_clear)

@receiver([post_save, post_delete], sender=DetailAHSPProject)
def _i1(sender, instance, **kw): _clear_rekap_cache(instance.project_id)

@receiver([post_save, post_delete], sender=HargaItemProject)
def _i2(sender, instance, **kw): _clear_rekap_cache(instance.project_id)

@receiver([post_save, post_delete], sender=VolumePekerjaan)
def _i3(sender, instance, **kw): _clear_rekap_cache(instance.project_id)

@receiver(post_save, sender=Pekerjaan)
def _i4(sender, instance, **kw): _clear_rekap_cache(instance.project_id)

@receiver(post_delete, sender=Pekerjaan)
def _i4_del(sender, instance, **kw): _clear_rekap_cache(instance.project_id)

@receiver([post_save, post_delete], sender=ProjectPricing)
def _i5(sender, instance, **kw): _clear_rekap_cache(instance.project_id)

# ============================================================================
# PHASE 5 TRACK 2.2: SMART CACHE INVALIDATION
# ============================================================================

def _clear_rekap_kebutuhan_cache(project_id):
    """
    Clear Rekap Kebutuhan cache for a specific project.

    The cache uses namespace pattern: rekap_kebutuhan:<project_id>
    Instead of deleting by pattern, we rely on signature-based invalidation
    which is already implemented in compute_kebutuhan_items().

    This function clears the entire cache namespace to force recomputation.
    """
    def _clear():
        cache_namespace = f"rekap_kebutuhan:{project_id}"
        cache.delete(cache_namespace)
        logger.debug(f"Invalidated rekap_kebutuhan cache for project {project_id}")

    # Execute on transaction commit to avoid premature cache clearing
    transaction.on_commit(_clear)


# Invalidate Rekap Kebutuhan cache when DetailAHSPExpanded changes
@receiver([post_save, post_delete], sender=DetailAHSPExpanded)
def _invalidate_on_detail_ahsp_expanded(sender, instance, **kwargs):
    """Invalidate when detail AHSP items are modified."""
    _clear_rekap_kebutuhan_cache(instance.project_id)


# Invalidate Rekap Kebutuhan cache when VolumePekerjaan changes
@receiver([post_save, post_delete], sender=VolumePekerjaan)
def _invalidate_on_volume_pekerjaan(sender, instance, **kwargs):
    """Invalidate when volume changes affect quantities."""
    _clear_rekap_kebutuhan_cache(instance.project_id)


# Invalidate Rekap Kebutuhan cache when HargaItemProject changes
@receiver([post_save, post_delete], sender=HargaItemProject)
def _invalidate_on_harga_item(sender, instance, **kwargs):
    """Invalidate when pricing changes."""
    _clear_rekap_kebutuhan_cache(instance.project_id)


# Invalidate Rekap Kebutuhan cache when Pekerjaan changes
@receiver([post_save, post_delete], sender=Pekerjaan)
def _invalidate_on_pekerjaan(sender, instance, **kwargs):
    """Invalidate when pekerjaan structure changes."""
    _clear_rekap_kebutuhan_cache(instance.project_id)


# Invalidate Rekap Kebutuhan cache when TahapPelaksanaan changes
@receiver([post_save, post_delete], sender=TahapPelaksanaan)
def _invalidate_on_tahapan(sender, instance, **kwargs):
    """Invalidate when tahapan definition changes."""
    _clear_rekap_kebutuhan_cache(instance.project_id)


# Invalidate Rekap Kebutuhan cache when PekerjaanTahapan assignment changes
@receiver([post_save, post_delete], sender=PekerjaanTahapan)
def _invalidate_on_pekerjaan_tahapan(sender, instance, **kwargs):
    """Invalidate when pekerjaan-tahapan assignments change."""
    # PekerjaanTahapan has FK to both tahapan and pekerjaan
    # Get project_id from either relation
    if hasattr(instance, 'tahapan') and instance.tahapan:
        project_id = instance.tahapan.project_id
    elif hasattr(instance, 'pekerjaan') and instance.pekerjaan:
        project_id = instance.pekerjaan.project_id
    else:
        logger.warning("PekerjaanTahapan signal: Could not determine project_id")
        return

    _clear_rekap_kebutuhan_cache(project_id)


@receiver(pre_save, sender=DetailAHSPProject)
def _sync_guard_detail_kategori(sender, instance, **kwargs):
    if instance.harga_item_id and instance.kategori and instance.harga_item.kategori:
        if instance.kategori != instance.harga_item.kategori:
            raise ValueError("Kategori detail tidak konsisten dengan kategori harga_item")
