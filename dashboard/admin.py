# dashboard/admin.py
"""
Django Admin configuration for dashboard app.

Features:
- Comprehensive Project model admin with filtering, search, and actions
- Custom bulk actions (activate, deactivate, export CSV)
- Read-only system fields
- Organized fieldsets
"""

from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
import csv
from datetime import date

from .models import Project


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin interface for Project model."""

    # List display
    list_display = [
        'index_project_display',
        'nama_display',
        'owner',
        'tahun_project',
        'timeline_display',
        'anggaran_display',
        'status_display',
        'created_at',
    ]

    # List filters
    list_filter = [
        'is_active',
        'tahun_project',
        'sumber_dana',
        'created_at',
        'tanggal_mulai',
        'tanggal_selesai',
    ]

    # Search fields
    search_fields = [
        'nama',
        'index_project',
        'lokasi_project',
        'nama_client',
        'owner__username',
        'owner__email',
    ]

    # Read-only fields
    readonly_fields = [
        'index_project',
        'created_at',
        'updated_at',
        'durasi_hari_display',
    ]

    # Date hierarchy
    date_hierarchy = 'created_at'

    # Ordering
    ordering = ['-updated_at']

    # Items per page
    list_per_page = 25

    def has_delete_permission(self, request, obj=None):
        """
        Enforce retention policy: project deletion is soft-delete only via `is_active`.
        Hard delete from admin is disabled to prevent accidental cascade data loss.
        """
        return False

    # Fieldsets for organized form
    fieldsets = (
        ('Identitas Project', {
            'fields': ('index_project', 'nama', 'owner', 'is_active')
        }),
        ('Data Wajib', {
            'fields': (
                'tahun_project',
                'sumber_dana',
                'lokasi_project',
                'nama_client',
                'anggaran_owner',
            )
        }),
        ('Timeline Pelaksanaan', {
            'fields': (
                'tanggal_mulai',
                'tanggal_selesai',
                'durasi_hari',
                'durasi_hari_display',
            ),
            'description': 'Timeline pelaksanaan project. Durasi akan dihitung otomatis dari tanggal mulai dan selesai.'
        }),
        ('Data Tambahan', {
            'fields': (
                'ket_project1',
                'ket_project2',
                'jabatan_client',
                'instansi_client',
                'nama_kontraktor',
                'instansi_kontraktor',
                'nama_konsultan_perencana',
                'instansi_konsultan_perencana',
                'nama_konsultan_pengawas',
                'instansi_konsultan_pengawas',
                'deskripsi',
                'kategori',
            ),
            'classes': ('collapse',),
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    # Custom display methods
    def index_project_display(self, obj):
        """Display index_project with link to detail page."""
        url = reverse('admin:dashboard_project_change', args=[obj.pk])
        return format_html('<a href="{}">{}</a>', url, obj.index_project or 'PRJ-NEW')
    index_project_display.short_description = 'Index Project'
    index_project_display.admin_order_field = 'index_project'

    def nama_display(self, obj):
        """Display nama with truncation."""
        if len(obj.nama) > 50:
            return format_html('<span title="{}">{}</span>', obj.nama, obj.nama[:50] + '...')
        return obj.nama
    nama_display.short_description = 'Nama Project'
    nama_display.admin_order_field = 'nama'

    def timeline_display(self, obj):
        """Display timeline information."""
        if obj.tanggal_mulai and obj.tanggal_selesai:
            return format_html(
                '{} s/d {}<br><small class="text-muted">{} hari</small>',
                obj.tanggal_mulai.strftime('%d/%m/%Y'),
                obj.tanggal_selesai.strftime('%d/%m/%Y'),
                obj.durasi_hari or '—'
            )
        return format_html('<span class="text-muted">—</span>')
    timeline_display.short_description = 'Timeline'

    def anggaran_display(self, obj):
        """Display anggaran with formatting."""
        if obj.anggaran_owner:
            # Format as Indonesian Rupiah
            anggaran_str = f"Rp {obj.anggaran_owner:,.0f}".replace(',', '.')
            if obj.anggaran_owner >= 1_000_000_000:  # 1 Miliar
                simplified = f"Rp {obj.anggaran_owner / 1_000_000_000:.1f} M"
            else:
                simplified = anggaran_str
            return format_html(
                '<span title="{}">{}</span>',
                anggaran_str,
                simplified
            )
        return format_html('<span class="text-muted">—</span>')
    anggaran_display.short_description = 'Anggaran'
    anggaran_display.admin_order_field = 'anggaran_owner'

    def status_display(self, obj):
        """Display project status with color badge."""
        if not obj.is_active:
            return format_html('<span style="color: #dc3545;">⚫ Archived</span>')

        if not obj.tanggal_mulai or not obj.tanggal_selesai:
            return format_html('<span style="color: #6c757d;">⚪ No Timeline</span>')

        today = date.today()

        if obj.tanggal_selesai < today:
            return format_html('<span style="color: #dc3545;">🔴 Terlambat</span>')
        elif obj.tanggal_mulai > today:
            return format_html('<span style="color: #6c757d;">⚪ Belum Mulai</span>')
        else:
            return format_html('<span style="color: #28a745;">🟢 Berjalan</span>')
    status_display.short_description = 'Status'

    def durasi_hari_display(self, obj):
        """Display calculated durasi_hari (read-only)."""
        if obj.tanggal_mulai and obj.tanggal_selesai:
            calculated = (obj.tanggal_selesai - obj.tanggal_mulai).days + 1
            return f"{calculated} hari"
        return "—"
    durasi_hari_display.short_description = 'Durasi (Kalkulasi)'

    # Custom actions
    actions = ['activate_projects', 'deactivate_projects', 'export_as_csv']

    @admin.action(description='Aktifkan project yang dipilih')
    def activate_projects(self, request, queryset):
        """Activate selected projects."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} project berhasil diaktifkan.'
        )

    @admin.action(description='Arsipkan project yang dipilih')
    def deactivate_projects(self, request, queryset):
        """Deactivate (archive) selected projects."""
        updated = queryset.update(is_active=False)
        self.message_user(
            request,
            f'{updated} project berhasil diarsipkan.'
        )

    @admin.action(description='Export project terpilih ke CSV')
    def export_as_csv(self, request, queryset):
        """Export selected projects to CSV."""
        meta = self.model._meta
        field_names = [
            'index_project', 'nama', 'tahun_project', 'sumber_dana',
            'lokasi_project', 'nama_client', 'anggaran_owner',
            'tanggal_mulai', 'tanggal_selesai', 'durasi_hari',
            'is_active', 'created_at', 'updated_at'
        ]

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename=projects_export.csv'
        response.write('\ufeff')  # UTF-8 BOM for Excel

        writer = csv.writer(response)
        writer.writerow(field_names)

        for obj in queryset:
            row = []
            for field in field_names:
                value = getattr(obj, field)
                if value is None:
                    row.append('')
                else:
                    row.append(str(value))
            writer.writerow(row)

        self.message_user(
            request,
            f'{queryset.count()} project berhasil diekspor ke CSV.'
        )

        return response

    # Override get_queryset to optimize queries
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('owner')

    # Custom save behavior
    def save_model(self, request, obj, form, change):
        """Custom save to set owner if creating new project."""
        if not change:  # Creating new object
            if not obj.owner:
                obj.owner = request.user
        super().save_model(request, obj, form, change)
