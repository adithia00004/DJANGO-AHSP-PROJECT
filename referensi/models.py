from django.db import models
from django.core.validators import MinValueValidator


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

    class Meta:
        verbose_name = "AHSP Referensi"
        verbose_name_plural = "AHSP Referensi"
        ordering = ["kode_ahsp"]
        indexes = [
            models.Index(fields=["klasifikasi", "sub_klasifikasi"]),
        ]

    def __str__(self):
        nama = (self.nama_ahsp or "")[:60]
        return f"{self.kode_ahsp} — {nama}"


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

    def __str__(self):
        uraian = (self.uraian_item or "")[:50]
        return f"{self.ahsp.kode_ahsp} | {self.get_kategori_display()} | {uraian}"
