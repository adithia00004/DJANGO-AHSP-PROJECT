from django.contrib import admin
from .models import AHSPReferensi, RincianReferensi

@admin.register(AHSPReferensi)
class AHSPReferensiAdmin(admin.ModelAdmin):
    list_display = ("id", "kode_ahsp", "nama_ahsp", "klasifikasi", "sub_klasifikasi", "satuan", "sumber")
    search_fields = ("kode_ahsp", "nama_ahsp", "klasifikasi", "sub_klasifikasi")
    list_filter = ("sumber",)
    ordering = ("kode_ahsp",)

@admin.register(RincianReferensi)
class RincianReferensiAdmin(admin.ModelAdmin):
    list_display = ("id", "ahsp", "kategori", "kode_item", "uraian_item", "satuan_item", "koefisien")
    list_filter = ("kategori", "ahsp")
    search_fields = ("kode_item", "uraian_item", "satuan_item", "ahsp__kode_ahsp", "ahsp__nama_ahsp")
    raw_id_fields = ("ahsp",)
    ordering = ("ahsp", "kategori", "id")
