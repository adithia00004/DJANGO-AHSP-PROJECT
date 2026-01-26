from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from simple_history.models import HistoricalRecords
from .models_staging import AHSPImportStaging  # Import Staging Model


class AHSPReferensiManager(models.Manager):
    def create(self, **kwargs):
        obj = super().create(**kwargs)
        from referensi.search_cache import invalidate_search_cache
        invalidate_search_cache()
        return obj

    def bulk_create(self, objs, **kwargs):
        result = super().bulk_create(objs, **kwargs)
        from referensi.search_cache import rebuild_search_cache
        rebuild_search_cache()
        return result


class AHSPReferensi(models.Model):
    # Unik & terindeks agar cepat saat lookup dari List Pekerjaan
    kode_ahsp = models.CharField(max_length=50, db_index=True)
    nama_ahsp = models.TextField()

    # Untuk autofill di List Pekerjaan (boleh kosong jika datamu belum lengkap; bisa diisi via data migration)
    klasifikasi = models.CharField(max_length=100, blank=True, null=True)
    sub_klasifikasi = models.CharField(max_length=100, blank=True, null=True)

    # Satuan snapshot di level pekerjaan
    satuan = models.CharField(max_length=50, blank=True, null=True)

    # Provenance
    sumber = models.CharField(max_length=100, default='AHSP SNI 2025')
    source_file = models.CharField(max_length=100, blank=True, null=True)

    # PHASE 3: Full-text search vector (PostgreSQL generated column, managed by migration)
    # This field is auto-updated by PostgreSQL trigger on INSERT/UPDATE
    # Do not set this field manually - it's computed from kode_ahsp, nama_ahsp, klasifikasi, sub_klasifikasi

    history = HistoricalRecords()
    objects = AHSPReferensiManager()

    class Meta:
        verbose_name = "AHSP Referensi"
        verbose_name_plural = "AHSP Referensi"
        ordering = ["kode_ahsp"]
        indexes = [
            models.Index(fields=["klasifikasi", "sub_klasifikasi"]),
            models.Index(fields=["sumber", "kode_ahsp"], name="ix_ahsp_sumber_kode"),

            # PHASE 1: Strategic indexes for performance
            models.Index(fields=["sumber"], name="ix_ahsp_sumber"),  # For source filtering
            models.Index(fields=["klasifikasi"], name="ix_ahsp_klasifikasi"),  # For classification dropdown
            models.Index(fields=["sumber", "klasifikasi"], name="ix_ahsp_sumber_klas"),  # Common filter combo

            # PHASE 3: Full-text search GIN index (managed by migration)
            # See migration 0012_add_fulltext_search.py for ix_ahsp_search_vector
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["sumber", "kode_ahsp"], name="uniq_ahsp_per_sumber"
            ),
        ]
        permissions = [
            ("view_ahsp_stats", "Can view AHSP statistics"),
            ("import_ahsp_data", "Can import AHSP data"),
            ("export_ahsp_data", "Can export AHSP data"),
        ]

    def __str__(self):
        nama = (self.nama_ahsp or "")[:60]
        return f"{self.kode_ahsp} - {nama}"


class RincianReferensi(models.Model):
    class Kategori(models.TextChoices):
        TK = "TK", "Tenaga Kerja"
        BHN = "BHN", "Bahan"
        ALT = "ALT", "Peralatan"
        LAIN = "LAIN", "Lainnya"

    ahsp = models.ForeignKey(
        AHSPReferensi,
        on_delete=models.CASCADE,
        related_name="rincian",
    )

    # Standarkan kategori → cocok dengan UI (TK/BHN/ALT/LAIN)
    kategori = models.CharField(max_length=50, choices=Kategori.choices, db_index=True)

    # RENAME: kode_item_lookup → kode_item (lebih konsisten dengan app detail_project)
    kode_item = models.CharField(max_length=50)

    # RENAME: item → uraian_item (konsisten penamaan)
    uraian_item = models.TextField()

    # RENAME: satuan → satuan_item (jelas konteksnya item)
    satuan_item = models.CharField(max_length=20)

    # Koefisien non-negatif
    koefisien = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        validators=[MinValueValidator(0)]
    )

    history = HistoricalRecords()

    class Meta:
        verbose_name = "Rincian Item AHSP"
        verbose_name_plural = "Rincian Item AHSP"
        # Hindari duplikasi baris identik pada satu AHSP
        constraints = [
            models.UniqueConstraint(
                fields=["ahsp", "kategori", "kode_item", "uraian_item", "satuan_item"],
                name="uniq_rincian_ref_per_ahsp",
            )
        ]
        ordering = ["ahsp_id", "kategori", "kode_item"]
        indexes = [
            models.Index(fields=["ahsp"]),
            models.Index(fields=["ahsp", "kategori"]),

            # PHASE 1: Strategic indexes for performance
            models.Index(fields=["kategori", "kode_item"], name="ix_rincian_kat_kode"),  # For category filtering
            models.Index(fields=["koefisien"], name="ix_rincian_koef"),  # For anomaly detection (zero coef)
            models.Index(fields=["satuan_item"], name="ix_rincian_satuan"),  # For anomaly detection (missing unit)

            # Covering index for common SELECT queries (reduces disk I/O)
            models.Index(
                fields=["ahsp", "kategori", "kode_item"],
                name="ix_rincian_covering"
            ),
        ]

    def __str__(self):
        uraian = (self.uraian_item or "")[:50]
        return f"{self.ahsp.kode_ahsp} | {self.get_kategori_display()} | {uraian}"


class KodeItemReferensi(models.Model):
    class Meta:
        db_table = "referensi_kode_item"
        verbose_name = "Kode Item Referensi"
        verbose_name_plural = "Kode Item Referensi"
        constraints = [
            models.UniqueConstraint(
                fields=["kategori", "uraian_item", "satuan_item"],
                name="uniq_kode_item_kombinasi",
            )
        ]
        indexes = [
            models.Index(fields=["kategori"]),
            models.Index(fields=["kode_item"]),

            # PHASE 1: Covering index for item code lookups (reduces disk I/O)
            models.Index(
                fields=["kategori", "uraian_item", "satuan_item", "kode_item"],
                name="ix_kodeitem_covering"
            ),
        ]

    kategori = models.CharField(
        max_length=50,
        choices=RincianReferensi.Kategori.choices,
    )
    uraian_item = models.TextField()
    satuan_item = models.CharField(max_length=20)
    kode_item = models.CharField(max_length=50)

    history = HistoricalRecords()

    def __str__(self):
        uraian = (self.uraian_item or "")[:50]
        return f"{self.kode_item} | {self.get_kategori_display()} | {uraian}"

    def get_kategori_display(self) -> str:  # pragma: no cover - passthrough helper
        return RincianReferensi.Kategori(self.kategori).label


class AHSPStats(models.Model):
    """
    PHASE 3 DAY 3: Materialized view for pre-computed AHSP statistics.

    This is a read-only model that maps to a PostgreSQL materialized view.
    DO NOT insert/update/delete directly - use `python manage.py refresh_stats` instead.

    Performance: 90-99% faster than computing aggregations on-the-fly.

    Usage:
        # Query pre-computed stats (fast!)
        stats = AHSPStats.objects.filter(sumber="SNI 2025")
        for stat in stats:
            print(f"{stat.kode_ahsp}: {stat.rincian_total} items")

        # Refresh after data changes
        python manage.py refresh_stats
    """

    class Meta:
        db_table = "referensi_ahsp_stats"
        managed = False  # Don't let Django manage this table
        verbose_name = "AHSP Statistics (Materialized View)"
        verbose_name_plural = "AHSP Statistics (Materialized View)"

    # Link to AHSP (not a ForeignKey because it's a view)
    ahsp_id = models.IntegerField(primary_key=True)

    # AHSP fields (denormalized from AHSPReferensi)
    kode_ahsp = models.CharField(max_length=50)
    nama_ahsp = models.TextField()
    klasifikasi = models.CharField(max_length=100, blank=True, null=True)
    sub_klasifikasi = models.CharField(max_length=100, blank=True, null=True)
    satuan = models.CharField(max_length=50, blank=True, null=True)
    sumber = models.CharField(max_length=100)
    source_file = models.CharField(max_length=100, blank=True, null=True)

    # Pre-computed statistics
    rincian_total = models.IntegerField()
    tk_count = models.IntegerField()
    bhn_count = models.IntegerField()
    alt_count = models.IntegerField()
    lain_count = models.IntegerField()
    zero_coef_count = models.IntegerField()
    missing_unit_count = models.IntegerField()

    def __str__(self):
        return f"{self.kode_ahsp} (Stats)"


# =============================================================================
# Phase 2: Security Audit & Logging Models
# =============================================================================

class SecurityAuditLog(models.Model):
    """
    Comprehensive security audit log for tracking all security-related events.

    This model stores detailed information about:
    - File validation attempts (success/failure)
    - Rate limiting events
    - XSS attempts and sanitization
    - User authentication events
    - Import operations

    Features:
    - Automatic timestamping
    - User and IP tracking
    - Severity levels
    - Categorization
    - Detailed metadata (JSON field)
    """

    # Severity levels
    SEVERITY_INFO = 'info'
    SEVERITY_WARNING = 'warning'
    SEVERITY_ERROR = 'error'
    SEVERITY_CRITICAL = 'critical'

    SEVERITY_CHOICES = [
        (SEVERITY_INFO, 'Info'),
        (SEVERITY_WARNING, 'Warning'),
        (SEVERITY_ERROR, 'Error'),
        (SEVERITY_CRITICAL, 'Critical'),
    ]

    # Event categories
    CATEGORY_FILE_UPLOAD = 'file_upload'
    CATEGORY_RATE_LIMIT = 'rate_limit'
    CATEGORY_XSS = 'xss'
    CATEGORY_AUTHENTICATION = 'authentication'
    CATEGORY_IMPORT = 'import'
    CATEGORY_EXPORT = 'export'
    CATEGORY_DATA_CHANGE = 'data_change'
    CATEGORY_PERMISSION = 'permission'
    CATEGORY_SYSTEM = 'system'

    CATEGORY_CHOICES = [
        (CATEGORY_FILE_UPLOAD, 'File Upload'),
        (CATEGORY_RATE_LIMIT, 'Rate Limit'),
        (CATEGORY_XSS, 'XSS Protection'),
        (CATEGORY_AUTHENTICATION, 'Authentication'),
        (CATEGORY_IMPORT, 'Import Operation'),
        (CATEGORY_EXPORT, 'Export Operation'),
        (CATEGORY_DATA_CHANGE, 'Data Change'),
        (CATEGORY_PERMISSION, 'Permission'),
        (CATEGORY_SYSTEM, 'System'),
    ]

    # Core fields
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="When the event occurred"
    )

    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default=SEVERITY_INFO,
        db_index=True,
        help_text="Severity level of the event"
    )

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        db_index=True,
        help_text="Category of the security event"
    )

    # User tracking
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_audit_logs',
        help_text="User who triggered the event (if authenticated)"
    )

    username = models.CharField(
        max_length=150,
        blank=True,
        db_index=True,
        help_text="Username snapshot (preserved even if user deleted)"
    )

    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        db_index=True,
        help_text="IP address of the request"
    )

    user_agent = models.TextField(
        blank=True,
        help_text="User agent string from the request"
    )

    # Event details
    event_type = models.CharField(
        max_length=100,
        db_index=True,
        help_text="Specific event type (e.g., 'file_too_large', 'rate_limit_exceeded')"
    )

    message = models.TextField(
        help_text="Human-readable description of the event"
    )

    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional event-specific data (JSON)"
    )

    # Request details
    path = models.CharField(
        max_length=500,
        blank=True,
        db_index=True,
        help_text="Request path that triggered the event"
    )

    method = models.CharField(
        max_length=10,
        blank=True,
        help_text="HTTP method (GET, POST, etc.)"
    )

    # Resolution tracking
    resolved = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether this event has been reviewed/resolved"
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the event was marked as resolved"
    )

    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_audit_logs',
        help_text="User who resolved the event"
    )

    notes = models.TextField(
        blank=True,
        help_text="Admin notes about this event"
    )

    class Meta:
        db_table = 'referensi_security_audit_log'
        verbose_name = 'Security Audit Log'
        verbose_name_plural = 'Security Audit Logs'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['-timestamp', 'severity']),
            models.Index(fields=['-timestamp', 'category']),
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['ip_address', '-timestamp']),
            models.Index(fields=['event_type', '-timestamp']),
            models.Index(fields=['resolved', '-timestamp']),
        ]

    def __str__(self):
        return f"[{self.severity.upper()}] {self.event_type} - {self.username or 'Anonymous'} at {self.timestamp}"

    def save(self, *args, **kwargs):
        """Auto-populate username from user if available."""
        if self.user and not self.username:
            self.username = self.user.username
        super().save(*args, **kwargs)

    def mark_resolved(self, user=None, notes=''):
        """Mark this event as resolved."""
        self.resolved = True
        self.resolved_at = timezone.now()
        self.resolved_by = user
        if notes:
            self.notes = notes
        self.save(update_fields=['resolved', 'resolved_at', 'resolved_by', 'notes'])

    @classmethod
    def log_file_validation_success(cls, user, ip_address, filename, file_size, **metadata):
        """Log successful file validation."""
        return cls.objects.create(
            severity=cls.SEVERITY_INFO,
            category=cls.CATEGORY_FILE_UPLOAD,
            event_type='file_validation_success',
            user=user,
            ip_address=ip_address,
            message=f"File validation passed: {filename} ({file_size} bytes)",
            metadata={
                'filename': filename,
                'file_size': file_size,
                **metadata
            }
        )

    @classmethod
    def log_file_validation_failure(cls, user, ip_address, filename, reason, **metadata):
        """Log failed file validation."""
        return cls.objects.create(
            severity=cls.SEVERITY_WARNING,
            category=cls.CATEGORY_FILE_UPLOAD,
            event_type='file_validation_failure',
            user=user,
            ip_address=ip_address,
            message=f"File validation failed: {filename} - {reason}",
            metadata={
                'filename': filename,
                'reason': reason,
                **metadata
            }
        )

    @classmethod
    def log_malicious_file(cls, user, ip_address, filename, threat_type, **metadata):
        """Log detection of malicious file."""
        return cls.objects.create(
            severity=cls.SEVERITY_CRITICAL,
            category=cls.CATEGORY_FILE_UPLOAD,
            event_type='malicious_file_detected',
            user=user,
            ip_address=ip_address,
            message=f"SECURITY ALERT: Malicious file detected - {filename} ({threat_type})",
            metadata={
                'filename': filename,
                'threat_type': threat_type,
                **metadata
            }
        )

    @classmethod
    def log_rate_limit_exceeded(cls, user, ip_address, path, limit, window, **metadata):
        """Log rate limit exceeded event."""
        return cls.objects.create(
            severity=cls.SEVERITY_WARNING,
            category=cls.CATEGORY_RATE_LIMIT,
            event_type='rate_limit_exceeded',
            user=user,
            ip_address=ip_address,
            path=path,
            message=f"Rate limit exceeded: {limit} requests per {window}s",
            metadata={
                'limit': limit,
                'window': window,
                **metadata
            }
        )

    @classmethod
    def log_xss_attempt(cls, user, ip_address, path, input_field, dangerous_content, **metadata):
        """Log XSS attempt."""
        return cls.objects.create(
            severity=cls.SEVERITY_ERROR,
            category=cls.CATEGORY_XSS,
            event_type='xss_attempt',
            user=user,
            ip_address=ip_address,
            path=path,
            message=f"XSS attempt blocked in field: {input_field}",
            metadata={
                'input_field': input_field,
                'dangerous_content': dangerous_content[:200],  # Limit stored content
                **metadata
            }
        )

    @classmethod
    def log_import_operation(cls, user, ip_address, filename, jobs_count, details_count, **metadata):
        """Log successful import operation."""
        return cls.objects.create(
            severity=cls.SEVERITY_INFO,
            category=cls.CATEGORY_IMPORT,
            event_type='import_success',
            user=user,
            ip_address=ip_address,
            message=f"Import completed: {filename} ({jobs_count} jobs, {details_count} details)",
            metadata={
                'filename': filename,
                'jobs_count': jobs_count,
                'details_count': details_count,
                **metadata
            }
        )

    @classmethod
    def cleanup_old_logs(cls, days=90):
        """Delete audit logs older than specified days."""
        from django.utils import timezone as tz
        cutoff_date = tz.now() - tz.timedelta(days=days)
        deleted_count, _ = cls.objects.filter(timestamp__lt=cutoff_date).delete()
        return deleted_count


class AuditLogSummary(models.Model):
    """
    Daily/hourly summary statistics for audit logs.

    This model provides pre-aggregated statistics for dashboard performance.
    Updated periodically via management command or celery task.
    """

    PERIOD_HOURLY = 'hourly'
    PERIOD_DAILY = 'daily'
    PERIOD_WEEKLY = 'weekly'
    PERIOD_MONTHLY = 'monthly'

    PERIOD_CHOICES = [
        (PERIOD_HOURLY, 'Hourly'),
        (PERIOD_DAILY, 'Daily'),
        (PERIOD_WEEKLY, 'Weekly'),
        (PERIOD_MONTHLY, 'Monthly'),
    ]

    period_type = models.CharField(
        max_length=20,
        choices=PERIOD_CHOICES,
        db_index=True
    )

    period_start = models.DateTimeField(
        db_index=True,
        help_text="Start of the aggregation period"
    )

    period_end = models.DateTimeField(
        help_text="End of the aggregation period"
    )

    category = models.CharField(
        max_length=50,
        choices=SecurityAuditLog.CATEGORY_CHOICES,
        db_index=True
    )

    severity = models.CharField(
        max_length=20,
        choices=SecurityAuditLog.SEVERITY_CHOICES,
        db_index=True
    )

    # Counts
    event_count = models.IntegerField(
        default=0,
        help_text="Total events in this period"
    )

    unique_users = models.IntegerField(
        default=0,
        help_text="Number of unique users"
    )

    unique_ips = models.IntegerField(
        default=0,
        help_text="Number of unique IP addresses"
    )

    # Metadata
    top_events = models.JSONField(
        default=list,
        blank=True,
        help_text="List of most common event types with counts"
    )

    top_users = models.JSONField(
        default=list,
        blank=True,
        help_text="List of most active users with counts"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'referensi_audit_log_summary'
        verbose_name = 'Audit Log Summary'
        verbose_name_plural = 'Audit Log Summaries'
        ordering = ['-period_start']
        unique_together = [['period_type', 'period_start', 'category', 'severity']]
        indexes = [
            models.Index(fields=['period_type', '-period_start']),
            models.Index(fields=['category', '-period_start']),
        ]

    def __str__(self):
        return f"{self.period_type} summary: {self.category}/{self.severity} - {self.period_start.date()}"
