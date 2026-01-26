from django.db import models
from django.conf import settings

class AHSPImportStaging(models.Model):
    """
    Temporary table untuk menampung hasil ekstraksi PDF sebelum masuk ke Main Database.
    Data di sini bisa diedit/dihapus oleh user (Validation Layer).
    """

    SEGMENT_CHOICES = [
        ('A', 'A. Tenaga Kerja'),
        ('B', 'B. Bahan'),
        ('C', 'C. Peralatan'),
        ('HEADING', 'Heading / Judul Bab'),
    ]

    # Tracking & Ownership
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    file_name = models.CharField(max_length=255)

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
        verbose_name = "Staging Import AHSP"
        verbose_name_plural = "Staging Import AHSP"

    def __str__(self):
        return f"{self.kode_item} - {self.uraian_item[:30]}"
