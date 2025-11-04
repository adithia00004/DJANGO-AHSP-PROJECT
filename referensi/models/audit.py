"""
Audit logging models for tracking security events.

This module provides comprehensive audit trail functionality for:
- File upload attempts and validations
- Rate limiting events
- XSS attempts
- Import operations
- User actions
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


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
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
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
