# detail_project/admin.py
from django.contrib import admin
from .models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan,
    HargaItemProject, DetailAHSPProject
)

@admin.register(Klasifikasi)
class KlasifikasiAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "name", "ordering_index")
    list_filter = ("project",)
    search_fields = ("name", "project__nama")
    ordering = ("project", "ordering_index", "id")
    raw_id_fields = ("project",)

@admin.register(SubKlasifikasi)
class SubKlasifikasiAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "klasifikasi", "name", "ordering_index")
    list_filter = ("project",)
    search_fields = ("name", "klasifikasi__name", "project__nama")
    ordering = ("project", "klasifikasi__ordering_index", "ordering_index", "id")
    raw_id_fields = ("project", "klasifikasi")

@admin.register(Pekerjaan)
class PekerjaanAdmin(admin.ModelAdmin):
    list_display = (
        "id", "project", "sub_klasifikasi", "source_type",
        "snapshot_kode", "snapshot_uraian", "snapshot_satuan",
        "auto_load_rincian", "detail_ready", "ordering_index",
    )
    list_filter = ("project", "source_type", "auto_load_rincian", "detail_ready")
    search_fields = ("snapshot_kode", "snapshot_uraian", "ref__kode_ahsp", "ref__nama_ahsp")
    ordering = ("project", "sub_klasifikasi__ordering_index", "ordering_index", "id")
    raw_id_fields = ("project", "sub_klasifikasi", "ref")

@admin.register(VolumePekerjaan)
class VolumePekerjaanAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "pekerjaan", "quantity")
    list_filter = ("project",)
    search_fields = ("pekerjaan__snapshot_kode", "pekerjaan__snapshot_uraian", "project__nama")
    ordering = ("project", "pekerjaan__ordering_index", "id")
    raw_id_fields = ("project", "pekerjaan")

@admin.register(HargaItemProject)
class HargaItemProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "kode_item", "kategori", "uraian", "satuan", "harga_satuan")
    list_filter = ("project", "kategori")
    search_fields = ("kode_item", "uraian", "project__nama")
    ordering = ("project", "kode_item")
    raw_id_fields = ("project",)

@admin.register(DetailAHSPProject)
class DetailAHSPProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "pekerjaan", "kategori", "kode", "uraian", "satuan", "koefisien")
    list_filter = ("project", "kategori", "pekerjaan")
    search_fields = ("kode", "uraian", "pekerjaan__snapshot_kode", "pekerjaan__snapshot_uraian", "project__nama")
    ordering = ("project", "pekerjaan__ordering_index", "kode")
    raw_id_fields = ("project", "pekerjaan", "harga_item")
