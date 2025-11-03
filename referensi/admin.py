from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from .models import AHSPReferensi, KodeItemReferensi, RincianReferensi

@admin.register(AHSPReferensi)
class AHSPReferensiAdmin(SimpleHistoryAdmin):
    list_display = ("id", "kode_ahsp", "nama_ahsp", "klasifikasi", "sub_klasifikasi", "satuan", "sumber")
    search_fields = ("kode_ahsp", "nama_ahsp", "klasifikasi", "sub_klasifikasi")
    list_filter = ("sumber",)
    ordering = ("kode_ahsp",)
    history_list_display = ("kode_ahsp", "nama_ahsp", "sumber")

@admin.register(RincianReferensi)
class RincianReferensiAdmin(SimpleHistoryAdmin):
    list_display = ("id", "ahsp", "kategori", "kode_item", "uraian_item", "satuan_item", "koefisien")
    list_filter = ("kategori", "ahsp")
    search_fields = ("kode_item", "uraian_item", "satuan_item", "ahsp__kode_ahsp", "ahsp__nama_ahsp")
    raw_id_fields = ("ahsp",)
    ordering = ("ahsp", "kategori", "id")
    history_list_display = ("ahsp", "kategori", "kode_item", "koefisien")


@admin.register(KodeItemReferensi)
class KodeItemReferensiAdmin(SimpleHistoryAdmin):
    list_display = ("id", "kategori", "kode_item", "uraian_item", "satuan_item")
    list_filter = ("kategori",)
    search_fields = ("kode_item", "uraian_item", "satuan_item")
    ordering = ("kode_item",)
    history_list_display = ("kategori", "kode_item", "satuan_item")
