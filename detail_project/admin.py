# detail_project/admin.py
from django.contrib import admin
from .models import (
    Klasifikasi, SubKlasifikasi, Pekerjaan, VolumePekerjaan,
    HargaItemProject, DetailAHSPProject, DetailAHSPExpanded,
    TahapPelaksanaan, PekerjaanTahapan, PekerjaanProgressWeekly
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
    list_display = ("id", "project", "pekerjaan", "kategori", "kode", "uraian", "satuan", "koefisien", "ref_pekerjaan")
    list_filter = ("project", "kategori", "pekerjaan")
    search_fields = ("kode", "uraian", "pekerjaan__snapshot_kode", "pekerjaan__snapshot_uraian", "project__nama")
    ordering = ("project", "pekerjaan__ordering_index", "kode")
    raw_id_fields = ("project", "pekerjaan", "harga_item", "ref_ahsp", "ref_pekerjaan")


@admin.register(DetailAHSPExpanded)
class DetailAHSPExpandedAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "pekerjaan", "kategori", "kode", "uraian", "koefisien", "source_bundle_kode", "expansion_depth")
    list_filter = ("project", "kategori", "expansion_depth")
    search_fields = ("kode", "uraian", "source_bundle_kode", "pekerjaan__snapshot_kode")
    ordering = ("project", "pekerjaan__ordering_index", "source_detail", "kode")
    raw_id_fields = ("project", "pekerjaan", "harga_item", "source_detail")
    readonly_fields = ("created_at", "updated_at")


# ===== Jadwal Pekerjaan (Work Schedule) =====

@admin.register(TahapPelaksanaan)
class TahapPelaksanaanAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "nama", "urutan", "tanggal_mulai", "tanggal_selesai",
                    "is_auto_generated", "generation_mode")
    list_filter = ("project", "is_auto_generated", "generation_mode")
    search_fields = ("nama", "deskripsi", "project__nama")
    ordering = ("project", "urutan", "id")
    raw_id_fields = ("project",)
    date_hierarchy = "tanggal_mulai"


@admin.register(PekerjaanTahapan)
class PekerjaanTahapanAdmin(admin.ModelAdmin):
    list_display = ("id", "pekerjaan", "tahapan", "proporsi_volume", "created_at", "updated_at")
    list_filter = ("tahapan__project", "tahapan")
    search_fields = ("pekerjaan__snapshot_kode", "pekerjaan__snapshot_uraian",
                     "tahapan__nama", "tahapan__project__nama")
    ordering = ("tahapan__project", "tahapan__urutan", "pekerjaan__ordering_index")
    raw_id_fields = ("pekerjaan", "tahapan")
    readonly_fields = ("created_at", "updated_at")


@admin.register(PekerjaanProgressWeekly)
class PekerjaanProgressWeeklyAdmin(admin.ModelAdmin):
    list_display = ("id", "pekerjaan", "project", "week_number", "week_start_date",
                    "week_end_date", "proportion", "created_at", "updated_at")
    list_filter = ("project", "week_number")
    search_fields = ("pekerjaan__snapshot_kode", "pekerjaan__snapshot_uraian",
                     "project__nama", "notes")
    ordering = ("project", "pekerjaan__ordering_index", "week_number")
    raw_id_fields = ("pekerjaan", "project")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "week_start_date"

    fieldsets = (
        ("Pekerjaan Info", {
            "fields": ("pekerjaan", "project")
        }),
        ("Week Info", {
            "fields": ("week_number", "week_start_date", "week_end_date")
        }),
        ("Progress Data", {
            "fields": ("proportion", "notes")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )
