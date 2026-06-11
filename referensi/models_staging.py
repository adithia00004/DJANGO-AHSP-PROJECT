from django.db import models
from django.conf import settings


class AHSPImportBatch(models.Model):
    """
    Lifecycle container for one AHSP import attempt.

    Staging rows are still the editable payload, but the batch is the audit and
    policy boundary: source, file, status, commit mode, and commit summary.
    """

    class Status(models.TextChoices):
        STAGED = "STAGED", "Staged"
        COMMITTED = "COMMITTED", "Committed"
        CLEARED = "CLEARED", "Cleared"
        FAILED = "FAILED", "Failed"

    class CommitMode(models.TextChoices):
        ABORT_DUPLICATE = "abort_duplicate", "Abort jika duplikat"
        MERGE = "merge", "Merge/update"
        REPLACE = "replace", "Replace kode dalam batch"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file_name = models.CharField(max_length=255)
    sumber = models.CharField(max_length=100, blank=True, default="")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STAGED)
    commit_mode = models.CharField(max_length=30, choices=CommitMode.choices, blank=True, default="")
    summary = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    committed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "status"], name="ix_importbatch_user_status"),
            models.Index(fields=["sumber", "status"], name="ix_importbatch_sumber_status"),
        ]
        verbose_name = "Batch Import AHSP"
        verbose_name_plural = "Batch Import AHSP"

    def __str__(self):
        return f"{self.file_name} ({self.sumber or '-'}) - {self.status}"


class AHSPImportStaging(models.Model):
    """
    Temporary table untuk menampung hasil ekstraksi PDF sebelum masuk ke Main Database.
    Data di sini bisa diedit/dihapus oleh user (Validation Layer).
    """

    SEGMENT_CHOICES = [
        ('A', 'A. Tenaga Kerja'),
        ('B', 'B. Bahan'),
        ('C', 'C. Peralatan'),
        ('LAIN', 'Lainnya'),
        ('HEADING', 'Heading / Judul Bab'),
    ]

    # Tracking & Ownership
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    batch = models.ForeignKey(
        AHSPImportBatch,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="rows",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255)

    # Source/version of the AHSP dataset (e.g. "AHSP 2024"). Declared by the
    # user at import time because the parsed Excel does not carry this metadata.
    sumber = models.CharField(
        max_length=100, blank=True, default="",
        help_text="Versi/tahun sumber AHSP, mis. 'AHSP 2024'",
    )

    # Hierarchy Context (Breadcrumb)
    # Ini menangkap kode AHSP induk tempat item ini berada (misal "A.2.2.1")
    parent_ahsp_code = models.CharField(max_length=50, blank=True, null=True, help_text="Kode AHSP Induk (misal A.2.2.1)")
    
    # Raw Data - Coefficient Extraction
    segment_type = models.CharField(max_length=20, choices=SEGMENT_CHOICES, blank=True, null=True)
    
    # Item Details (Regex Extracted)
    kode_item = models.CharField(max_length=50, help_text="Kode Item (misal L.01 atau batu_kali)")
    uraian_item = models.TextField(help_text="Nama Item (misal 'Pekerja' atau 'Semen')")
    satuan_item = models.CharField(max_length=50, blank=True, null=True)
    
    # Value (Koefisien is priority, Price is secondary/ignored generally)
    koefisien = models.DecimalField(max_digits=20, decimal_places=6, default=0)
    
    # Validation Status
    is_valid = models.BooleanField(default=True)
    error_message = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['created_at', 'id']
        indexes = [
            models.Index(fields=["user", "batch"], name="ix_staging_user_batch"),
            models.Index(fields=["user", "file_name"], name="ix_staging_user_file"),
        ]
        verbose_name = "Staging Import AHSP"
        verbose_name_plural = "Staging Import AHSP"

    def __str__(self):
        return f"{self.kode_item} - {self.uraian_item[:30]}"
