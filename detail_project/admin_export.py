# detail_project/admin_export.py
"""
Django Admin configuration for Export System models
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models_export import ExportSession, ExportPage


@admin.register(ExportSession)
class ExportSessionAdmin(admin.ModelAdmin):
    """Admin interface for ExportSession"""

    list_display = [
        'export_id_short',
        'user',
        'report_type',
        'format_type',
        'status',
        'progress_display',
        'created_at',
        'expires_at',
        'download_link',
    ]

    list_filter = [
        'status',
        'report_type',
        'format_type',
        'created_at',
        'expires_at',
    ]

    search_fields = [
        'export_id',
        'user__username',
        'project_name',
    ]

    readonly_fields = [
        'export_id',
        'user',
        'created_at',
        'updated_at',
        'completed_at',
        'progress_percent',
        'download_url',
    ]

    fieldsets = (
        ('Session Info', {
            'fields': ('export_id', 'user', 'status')
        }),
        ('Configuration', {
            'fields': ('report_type', 'format_type', 'project_name', 'metadata')
        }),
        ('Progress', {
            'fields': ('estimated_pages', 'pages_received', 'batches_received', 'progress_percent')
        }),
        ('Output', {
            'fields': ('output_file', 'file_size', 'download_url')
        }),
        ('Error Info', {
            'fields': ('error_message',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'expires_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )

    def export_id_short(self, obj):
        """Show first 8 characters of UUID"""
        return str(obj.export_id)[:8]
    export_id_short.short_description = 'Export ID'

    def progress_display(self, obj):
        """Show progress bar"""
        percent = obj.progress_percent
        if obj.status == ExportSession.STATUS_COMPLETED:
            color = '#28a745'  # Green
        elif obj.status == ExportSession.STATUS_FAILED:
            color = '#dc3545'  # Red
        elif percent > 0:
            color = '#007bff'  # Blue
        else:
            color = '#6c757d'  # Gray

        return format_html(
            '<div style="width: 100px; background-color: #e9ecef; border-radius: 3px;">'
            '<div style="width: {}%; background-color: {}; height: 20px; border-radius: 3px; text-align: center; line-height: 20px; color: white; font-size: 12px;">'
            '{}%'
            '</div>'
            '</div>',
            percent, color, percent
        )
    progress_display.short_description = 'Progress'

    def download_link(self, obj):
        """Show download link if completed"""
        if obj.status == ExportSession.STATUS_COMPLETED and obj.output_file:
            url = reverse('detail_project:export_download', kwargs={'export_id': obj.export_id})
            return format_html(
                '<a href="{}" target="_blank" style="color: #28a745; font-weight: bold;">📥 Download</a>',
                url
            )
        return '-'
    download_link.short_description = 'Download'

    actions = ['mark_as_expired']

    def mark_as_expired(self, request, queryset):
        """Mark selected sessions as expired"""
        updated = queryset.update(status=ExportSession.STATUS_EXPIRED)
        self.message_user(request, f'{updated} session(s) marked as expired.')
    mark_as_expired.short_description = 'Mark as expired'


@admin.register(ExportPage)
class ExportPageAdmin(admin.ModelAdmin):
    """Admin interface for ExportPage"""

    list_display = [
        'id',
        'session_id_short',
        'page_number',
        'title',
        'batch_index',
        'image_size_display',
        'created_at',
    ]

    list_filter = [
        'format',
        'created_at',
    ]

    search_fields = [
        'session__export_id',
        'title',
    ]

    readonly_fields = [
        'session',
        'page_number',
        'batch_index',
        'title',
        'format',
        'created_at',
        'image_size_kb',
        'image_preview',
    ]

    fieldsets = (
        ('Page Info', {
            'fields': ('session', 'page_number', 'batch_index', 'title', 'format')
        }),
        ('Image Data', {
            'fields': ('image_preview', 'width', 'height', 'file_size', 'image_size_kb'),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
        }),
    )

    def session_id_short(self, obj):
        """Show first 8 characters of session UUID"""
        return str(obj.session.export_id)[:8]
    session_id_short.short_description = 'Session ID'

    def image_size_display(self, obj):
        """Show image size in KB"""
        return f'{obj.image_size_kb:.2f} KB'
    image_size_display.short_description = 'Image Size'

    def image_preview(self, obj):
        """Show image preview"""
        if obj.image_data:
            # Limit preview size
            return format_html(
                '<img src="{}" style="max-width: 600px; max-height: 400px; border: 1px solid #ddd;" />',
                obj.image_data
            )
        return 'No image data'
    image_preview.short_description = 'Image Preview'

    def has_add_permission(self, request):
        """Disable manual page addition"""
        return False
