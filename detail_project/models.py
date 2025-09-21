# detail_project/models.py
# ================================
from django.db import models
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Q              # dipakai nanti oleh CheckConstraint (Fase 1)



# Referensi (read-only) — pastikan app `referensi` sudah ada.
try:
    from referensi.models import AHSPReferensi, RincianReferensi  # sesuaikan nama field di app referensi
except Exception:  # fallback bila belum tersedia saat makemigrations
    AHSPReferensi = None
    RincianReferensi = None


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Klasifikasi(TimeStampedModel):
    project = models.ForeignKey('dashboard.Project', on_delete=models.CASCADE, related_name='klasifikasi_list')
    name = models.CharField(max_length=255)
    ordering_index = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["ordering_index", "id"]
        unique_together = ("project", "ordering_index")

    def __str__(self):
        return f"{self.name}"


class SubKlasifikasi(TimeStampedModel):
    project = models.ForeignKey('dashboard.Project', on_delete=models.CASCADE, related_name='subklasifikasi_list')
    klasifikasi = models.ForeignKey(Klasifikasi, on_delete=models.CASCADE, related_name='sub_list')
    name = models.CharField(max_length=255)
    ordering_index = models.PositiveIntegerField(default=0, db_index=True)

    class Meta:
        ordering = ["ordering_index", "id"]
        unique_together = ("project", "klasifikasi", "ordering_index")

    def __str__(self):
        return f"{self.klasifikasi.name} › {self.name}"


class Pekerjaan(TimeStampedModel):
    SOURCE_REF = 'ref'
    SOURCE_CUSTOM = 'custom'
    SOURCE_REF_MOD = 'ref_modified'
    SOURCE_CHOICES = [
        (SOURCE_REF, 'Referensi'),
        (SOURCE_CUSTOM, 'Custom'),
        (SOURCE_REF_MOD, 'Ref Modified'),
    ]

    project = models.ForeignKey('dashboard.Project', on_delete=models.CASCADE, related_name='pekerjaan_list')
    sub_klasifikasi = models.ForeignKey(SubKlasifikasi, on_delete=models.CASCADE, related_name='pekerjaan_list')

    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    ref = models.ForeignKey('referensi.AHSPReferensi', on_delete=models.SET_NULL, null=True, blank=True)

    # Snapshot identitas dari referensi atau input manual (immutable setelah dibuat)
    snapshot_kode = models.CharField(max_length=100, blank=True, null=True)
    snapshot_uraian = models.TextField(blank=True, null=True)
    snapshot_satuan = models.CharField(max_length=50, blank=True, null=True)

    auto_load_rincian = models.BooleanField(default=True)
    detail_ready = models.BooleanField(default=False)  # khusus custom: true jika ≥1 baris valid

    notes = models.TextField(blank=True, null=True)
    ordering_index = models.PositiveIntegerField(default=0, db_index=True)
    markup_override_percent = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Override % BUK khusus pekerjaan ini; null=pakai default project"
    )

    class Meta:
        ordering = ["ordering_index", "id"]
        unique_together = ("project", "ordering_index")

    # ====== Helper properties/methods untuk tampilan ======

    @property
    def is_ref(self) -> bool:
        return self.source_type == self.SOURCE_REF

    @property
    def is_custom(self) -> bool:
        return self.source_type == self.SOURCE_CUSTOM

    @property
    def is_ref_modified(self) -> bool:
        return self.source_type == self.SOURCE_REF_MOD

    def ref_year(self):
        """
        Ambil tahun AHSP dari objek referensi dengan fallback beberapa nama field umum.
        Kembalikan string tahun (mis. '2025') atau None bila tidak tersedia.
        """
        r = self.ref
        if not r:
            return None
        for attr in ("tahun", "tahun_sni", "versi", "versi_tahun"):
            val = getattr(r, attr, None)
            if val:
                return str(val)
        return None

    def source_badge(self) -> str:
        """
        Label sumber untuk UI:
        - REF:          'AHSP {tahun}' (fallback 'AHSP' bila tahun tak ada)
        - REF_MODIFIED: 'AHSP {tahun} (modified)'
        - CUSTOM:       'Kustom'
        """
        if self.is_ref or self.is_ref_modified:
            base = "AHSP"
            yr = self.ref_year()
            if yr:
                base = f"{base} {yr}"
            if self.is_ref_modified:
                base = f"{base} (modified)"
            return base
        return "Kustom"

    def display_kode(self, mod_index: int | None = None) -> str | None:
        """
        Kode yang ditampilkan di UI:
        - REF:          snapshot_kode
        - REF_MODIFIED: 'mod.{X}-{snapshot_kode}' bila mod_index tersedia, jika tidak hanya snapshot_kode
        - CUSTOM:       snapshot_kode (bisa auto-generate saat save jika kosong)
        """
        if self.is_ref_modified and mod_index is not None:
            base = self.snapshot_kode or ""
            return f"mod.{mod_index}-{base}" if base else f"mod.{mod_index}"
        return self.snapshot_kode

    # Opsional: auto-generate kode untuk CUSTOM saat kosong. Tidak mengubah schema.
    def _gen_custom_code(self) -> str:
        # Sederhana: hitung jumlah custom saat ini + 1 → CUST-0001, CUST-0002, ...
        count = Pekerjaan.objects.filter(project=self.project, source_type=self.SOURCE_CUSTOM).count()
        return f"CUST-{count + 1:04d}"

    def save(self, *args, **kwargs):
        if self.is_custom and not self.snapshot_kode and not self.pk:
            # import lokal untuk hindari circular import
            from .services import generate_custom_code
            self.snapshot_kode = generate_custom_code(self.project)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.snapshot_kode or ''} - {self.snapshot_uraian or ''}"
    
    # QoL untuk API: volume aman (0 jika belum ada record VolumePekerjaan)
    @property
    def safe_volume(self):
        try:
            return self.volume.quantity  # OneToOne mungkin belum dibuat
        except VolumePekerjaan.DoesNotExist:
            return 0


class VolumePekerjaan(TimeStampedModel):
    project = models.ForeignKey('dashboard.Project', on_delete=models.CASCADE, related_name='volume_list')
    pekerjaan = models.OneToOneField(Pekerjaan, on_delete=models.CASCADE, related_name='volume')
    quantity = models.DecimalField(max_digits=18, decimal_places=3, validators=[MinValueValidator(0)])

    class Meta:
        unique_together = ("project", "pekerjaan")


class HargaItemProject(TimeStampedModel):
    KATEGORI_TK = 'TK'
    KATEGORI_BAHAN = 'BHN'
    KATEGORI_ALAT = 'ALT'
    KATEGORI_LAIN = 'LAIN'

    KATEGORI_CHOICES = [
        (KATEGORI_TK, 'Tenaga Kerja'),
        (KATEGORI_BAHAN, 'Bahan'),
        (KATEGORI_ALAT, 'Alat'),
        (KATEGORI_LAIN, 'Lain-lain'),
    ]

    project = models.ForeignKey('dashboard.Project', on_delete=models.CASCADE, related_name='harga_items')
    kode_item = models.CharField(max_length=100)
    satuan = models.CharField(max_length=50, blank=True, null=True)
    uraian = models.TextField()
    kategori = models.CharField(max_length=10, choices=KATEGORI_CHOICES)
    harga_satuan = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True, validators=[MinValueValidator(0)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "kode_item"], name="uniq_harga_kode_per_project"),
        ]
        indexes = [
            models.Index(fields=["project", "kategori"]),
        ]

    def __str__(self):
        return f"{self.kode_item} — {self.uraian}"


class DetailAHSPProject(TimeStampedModel):
    project = models.ForeignKey('dashboard.Project', on_delete=models.CASCADE, related_name='detail_ahsp')
    pekerjaan = models.ForeignKey(Pekerjaan, on_delete=models.CASCADE, related_name='detail_list')

    harga_item = models.ForeignKey(HargaItemProject, on_delete=models.PROTECT, related_name='detail_refs')
    kategori = models.CharField(max_length=10, choices=HargaItemProject.KATEGORI_CHOICES)
    kode = models.CharField(max_length=100)
    uraian = models.TextField()
    satuan = models.CharField(max_length=50, blank=True, null=True)
    koefisien = models.DecimalField(max_digits=18, decimal_places=6, validators=[MinValueValidator(0)])
    

    # bundle target (hanya dipakai saat kategori = 'LAIN')
    
    ref_ahsp = models.ForeignKey(
        'referensi.AHSPReferensi',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='detail_bundles'
    )

    class Meta:
        indexes = [
            models.Index(fields=["project", "pekerjaan"]),                # sudah ada
            models.Index(fields=["project", "pekerjaan", "kategori"]),    # NEW: rekap cepat
            models.Index(fields=["project", "kategori", "harga_item"]),   # OPT: join & filter cepat per kategori
        ]
        unique_together = ("project", "pekerjaan", "kode")
        constraints = [
            # NEW: hanya baris kategori 'LAIN' yang boleh punya ref_ahsp (atau kosong)
            models.CheckConstraint(
                name="ref_ahsp_only_for_lain",
                condition=Q(ref_ahsp__isnull=True) | Q(kategori='LAIN')
            ),
        ]

    def __str__(self):
        return f"{self.pekerjaan_id} / {self.kode} — {self.uraian}"


# === NEW: Volume Formula State (ringan; satu per project+pekerjaan) ===
class VolumeFormulaState(TimeStampedModel):
    """
    Menyimpan state formula input volume (ringan).
    - Nilai volume tetap sumber kebenaran di VolumePekerjaan.
    - Satu record per (project, pekerjaan).
    """
    project = models.ForeignKey('dashboard.Project', on_delete=models.CASCADE, related_name='volume_formula_states')
    pekerjaan = models.ForeignKey(Pekerjaan, on_delete=models.CASCADE, related_name='formula_state')
    raw = models.TextField(blank=True, default="")
    is_fx = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["project", "pekerjaan"], name="uniq_formula_per_project_pekerjaan"),
        ]
        indexes = [
            models.Index(fields=["project", "pekerjaan"]),
        ]

    def __str__(self):
        return f"F[{self.project_id}:{self.pekerjaan_id}] = {('fx' if self.is_fx else 'val')}«{(self.raw or '')[:30]}... »"


# === BUK per Project ===
class ProjectPricing(TimeStampedModel):
    """
    Simpan Biaya Umum & Keuntungan (BUK) per project, dalam persen (0..100).
    Minimal-change: OneToOne + default 10.00.
    """
    # NEW (Fase 4): preferensi tampilan/rekap proyek
    ppn_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=11,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="PPN (%) yang diterapkan pada Rekap RAB"
    )
    rounding_base = models.PositiveIntegerField(
        default=10000,
        help_text="Basis pembulatan grand total (Rp), mis. 10000"
    )
    project = models.OneToOneField(
        'dashboard.Project',
        on_delete=models.CASCADE,
        related_name='pricing'
    )
    # default BUK proyek
    markup_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('10.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['project'], name='uniq_project_pricing_one')
        ]

    def __str__(self):
        return f"Pricing for Project #{self.project_id}"
