from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from django.db import transaction
from .models import DetailAHSPProject, HargaItemProject, VolumePekerjaan, Pekerjaan, ProjectPricing

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

@receiver(pre_save, sender=DetailAHSPProject)
def _sync_guard_detail_kategori(sender, instance, **kwargs):
    if instance.harga_item_id and instance.kategori and instance.harga_item.kategori:
        if instance.kategori != instance.harga_item.kategori:
            raise ValueError("Kategori detail tidak konsisten dengan kategori harga_item")
