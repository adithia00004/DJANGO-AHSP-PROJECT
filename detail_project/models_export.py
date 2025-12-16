# detail_project/models_export.py
"""
Export Session Models
Tracks multi-page export sessions for PDF and Word generation
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import uuid
import json


class ExportSession(models.Model):
    """
    Export session untuk batch upload (large datasets)
    Stores metadata dan tracks progress untuk multi-page exports
    """

    # Status choices
    STATUS_INIT = 'init'
    STATUS_UPLOADING = 'uploading'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_EXPIRED = 'expired'

    STATUS_CHOICES = [
        (STATUS_INIT, 'Initialized'),
        (STATUS_UPLOADING, 'Uploading Pages'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_EXPIRED, 'Expired'),
    ]

    # Format choices
    FORMAT_PDF = 'pdf'
    FORMAT_WORD = 'word'

    FORMAT_CHOICES = [
        (FORMAT_PDF, 'PDF'),
        (FORMAT_WORD, 'Word Document'),
    ]

    # Report type choices
    REPORT_REKAP = 'rekap'
    REPORT_MONTHLY = 'monthly'
    REPORT_WEEKLY = 'weekly'

    REPORT_CHOICES = [
        (REPORT_REKAP, 'Laporan Rekap'),
        (REPORT_MONTHLY, 'Laporan Bulanan'),
        (REPORT_WEEKLY, 'Laporan Mingguan'),
    ]

    # Primary fields
    export_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text="Unique export session ID"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='export_sessions',
        help_text="User who initiated the export"
    )

    # Export configuration
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_CHOICES,
        help_text="Type of report to generate"
    )

    format_type = models.CharField(
        max_length=10,
        choices=FORMAT_CHOICES,
        help_text="Output format (PDF or Word)"
    )

    # Progress tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_INIT,
        db_index=True,
        help_text="Current status of export"
    )

    estimated_pages = models.PositiveIntegerField(
        default=0,
        help_text="Estimated total pages"
    )

    pages_received = models.PositiveIntegerField(
        default=0,
        help_text="Number of pages uploaded"
    )

    batches_received = models.PositiveIntegerField(
        default=0,
        help_text="Number of batches uploaded"
    )

    # Metadata
    project_name = models.CharField(
        max_length=255,
        blank=True,
        help_text="Project name for the export"
    )

    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional metadata (month, week, options, etc.)"
    )

    # File storage
    output_file = models.FileField(
        upload_to='exports/%Y/%m/%d/',
        null=True,
        blank=True,
        help_text="Generated output file (PDF or Word)"
    )

    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="File size in bytes"
    )

    # Error tracking
    error_message = models.TextField(
        blank=True,
        help_text="Error message if export failed"
    )

    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text="When the export was initiated"
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        help_text="Last update timestamp"
    )

    expires_at = models.DateTimeField(
        db_index=True,
        help_text="When the session expires (auto-cleanup)"
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the export was completed"
    )

    class Meta:
        db_table = 'detail_project_export_session'
        verbose_name = 'Export Session'
        verbose_name_plural = 'Export Sessions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', 'expires_at']),
        ]

    def __str__(self):
        return f"{self.report_type.upper()} {self.format_type.upper()} - {self.export_id}"

    def save(self, *args, **kwargs):
        # Set expiration time on creation (1 hour from now)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        """Check if session has expired"""
        return timezone.now() > self.expires_at

    @property
    def progress_percent(self):
        """Calculate upload progress percentage"""
        if self.estimated_pages == 0:
            return 0
        return min(100, int((self.pages_received / self.estimated_pages) * 100))

    @property
    def download_url(self):
        """Get download URL for completed export"""
        if self.status == self.STATUS_COMPLETED and self.output_file:
            return self.output_file.url
        return None

    def mark_uploading(self):
        """Mark session as uploading"""
        self.status = self.STATUS_UPLOADING
        self.save(update_fields=['status', 'updated_at'])

    def mark_processing(self):
        """Mark session as processing"""
        self.status = self.STATUS_PROCESSING
        self.save(update_fields=['status', 'updated_at'])

    def mark_completed(self, output_file, file_size):
        """Mark session as completed"""
        self.status = self.STATUS_COMPLETED
        self.output_file = output_file
        self.file_size = file_size
        self.completed_at = timezone.now()
        self.save(update_fields=['status', 'output_file', 'file_size', 'completed_at', 'updated_at'])

    def mark_failed(self, error_message):
        """Mark session as failed"""
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.save(update_fields=['status', 'error_message', 'updated_at'])

    def increment_pages(self, count=1):
        """Increment pages received counter"""
        self.pages_received += count
        self.save(update_fields=['pages_received', 'updated_at'])

    def increment_batches(self):
        """Increment batches received counter"""
        self.batches_received += 1
        self.save(update_fields=['batches_received', 'updated_at'])


class ExportPage(models.Model):
    """
    Individual page data for an export session
    Stores base64-encoded PNG images
    """

    id = models.BigAutoField(primary_key=True)

    session = models.ForeignKey(
        ExportSession,
        on_delete=models.CASCADE,
        related_name='pages',
        help_text="Parent export session"
    )

    page_number = models.PositiveIntegerField(
        help_text="Page number (1-indexed)"
    )

    batch_index = models.PositiveIntegerField(
        default=0,
        help_text="Batch index (for tracking upload order)"
    )

    title = models.CharField(
        max_length=255,
        help_text="Page title (e.g., 'Gantt W1-W12', 'Kurva S Weekly')"
    )

    # Image data (base64-encoded PNG)
    image_data = models.TextField(
        help_text="Base64-encoded PNG image (data:image/png;base64,...)"
    )

    format = models.CharField(
        max_length=10,
        default='png',
        help_text="Image format (usually 'png')"
    )

    # Metadata
    width = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Image width in pixels"
    )

    height = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Image height in pixels"
    )

    file_size = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Image size in bytes (base64)"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="When the page was uploaded"
    )

    class Meta:
        db_table = 'detail_project_export_page'
        verbose_name = 'Export Page'
        verbose_name_plural = 'Export Pages'
        ordering = ['session', 'page_number']
        unique_together = [('session', 'page_number')]
        indexes = [
            models.Index(fields=['session', 'page_number']),
            models.Index(fields=['session', 'batch_index']),
        ]

    def __str__(self):
        return f"{self.session.export_id} - Page {self.page_number}: {self.title}"

    @property
    def image_size_kb(self):
        """Get image size in KB"""
        if self.file_size:
            return self.file_size / 1024
        return len(self.image_data) / 1024 if self.image_data else 0
