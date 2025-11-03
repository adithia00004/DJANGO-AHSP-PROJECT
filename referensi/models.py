from django.core.validators import MinValueValidator
from django.db import models
from simple_history.models import HistoricalRecords


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
