# detail_project/models.py
# ================================
from django.db import models
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import Sum, Q              # dipakai nanti oleh CheckConstraint (Fase 1)
from django.core.exceptions import ValidationError
from django.utils.timezone import now


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


class NameAliasManager(models.Manager):
    """Allow legacy 'nama' keyword arguments for models that now use 'name'."""

    @staticmethod
    def _normalize(kwargs):
        if kwargs is None:
            return None
        normalized = dict(kwargs)
        if "name" not in normalized and normalized.get("nama"):
            normalized["name"] = normalized.pop("nama")
        return normalized

    def create(self, **kwargs):
        return super().create(**self._normalize(kwargs))

    def get_or_create(self, defaults=None, **kwargs):
        return super().get_or_create(
            defaults=self._normalize(defaults),
            **self._normalize(kwargs)
        )

    def update_or_create(self, defaults=None, **kwargs):
        return super().update_or_create(
            defaults=self._normalize(defaults),
            **self._normalize(kwargs)
        )


class Klasifikasi(TimeStampedModel):
    project = models.ForeignKey('dashboard.Project', on_delete=models.CASCADE, related_name='klasifikasi_list')
    name = models.CharField(max_length=255)
    ordering_index = models.PositiveIntegerField(default=0, db_index=True)
    objects = NameAliasManager()

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
    objects = NameAliasManager()

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
        help_text="Override % Profit/Margin khusus pekerjaan ini; null=pakai default project"
    )
    detail_last_modified = models.DateTimeField(null=True, blank=True)

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
    
    def get_unassigned_proportion(self):
        '''
        Hitung proporsi yang belum di-assign ke tahapan.
        
        Returns:
            Decimal: Proporsi yang belum ter-assign (0-100)
        '''
        from decimal import Decimal
        assigned = self.tahapan_assignments.aggregate(
            total=Sum('proporsi_volume')
        )['total'] or Decimal('0')
        return Decimal('100') - assigned

    def is_fully_assigned(self):
        '''Check apakah pekerjaan sudah fully assigned ke tahapan'''
        return abs(float(self.get_unassigned_proportion())) < 0.01

    @property
    def tahapan_distribution(self):
        '''
        Return dict distribusi tahapan.
        
        Returns:
            dict: {nama_tahapan: proporsi_volume}
            
        Example:
            {"Tahap 1: Persiapan": 60.00, "Tahap 2: Struktur": 40.00}
        '''
        return {
            pt.tahapan.nama: float(pt.proporsi_volume)
            for pt in self.tahapan_assignments.select_related('tahapan')
        }

    def get_tahapan_assignments_detail(self):
        '''
        Return list detail assignments dengan info lengkap.
        
        Returns:
            list of dict: Detail assignments
        '''
        return [
            {
                'tahapan_id': pt.tahapan_id,
                'tahapan_nama': pt.tahapan.nama,
                'proporsi': float(pt.proporsi_volume),
                'volume_efektif': float(pt.volume_efektif),
                'catatan': pt.catatan
            }
            for pt in self.tahapan_assignments.select_related('tahapan').order_by('tahapan__urutan')
        ]    

    # Opsional: auto-generate kode untuk CUSTOM saat kosong. Tidak mengubah schema.
    def _gen_custom_code(self) -> str:
        # Sederhana: hitung jumlah custom saat ini + 1 → CUST-0001, CUST-0002, ...
        count = Pekerjaan.objects.filter(project=self.project, source_type=self.SOURCE_CUSTOM).count()
        return f"CUST-{count + 1:04d}"

    def save(self, *args, **kwargs):
        if self.is_custom and not self.snapshot_kode and not self.pk:
          try:
              from .services import generate_custom_code  # import lokal untuk hindari circular
              self.snapshot_kode = generate_custom_code(self.project)
          except Exception:
              self.snapshot_kode = self._gen_custom_code()
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
    # Support 2 jenis reference: AHSP Referensi OR Pekerjaan dalam project

    ref_ahsp = models.ForeignKey(
        'referensi.AHSPReferensi',
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='detail_bundles',
        help_text='Reference to AHSP master (bundle support for LAIN category)'
    )

    ref_pekerjaan = models.ForeignKey(
        Pekerjaan,
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name='bundle_references',
        help_text='Reference to another Pekerjaan in same project (bundle support for LAIN category)'
    )

    class Meta:
        indexes = [
            models.Index(fields=["project", "pekerjaan"]),                # sudah ada
            models.Index(fields=["project", "pekerjaan", "kategori"]),    # NEW: rekap cepat
            models.Index(fields=["project", "kategori", "harga_item"]),   # OPT: join & filter cepat per kategori
        ]
        unique_together = ("project", "pekerjaan", "kode")
        constraints = [
            # Hanya kategori 'LAIN' yang boleh punya bundle reference
            models.CheckConstraint(
                name="bundle_ref_only_for_lain",
                condition=Q(ref_ahsp__isnull=True, ref_pekerjaan__isnull=True) | Q(kategori='LAIN')
            ),
            # Hanya boleh salah satu: ref_ahsp OR ref_pekerjaan (tidak boleh keduanya)
            models.CheckConstraint(
                name="bundle_ref_exclusive",
                condition=~Q(ref_ahsp__isnull=False, ref_pekerjaan__isnull=False)
            ),
        ]

    def __str__(self):
        return f"{self.pekerjaan_id} / {self.kode} — {self.uraian}"


class DetailAHSPExpanded(TimeStampedModel):
    """
    STORAGE 2: Expanded components dari bundle pekerjaan.

    Purpose:
    - Auto-generated dari DetailAHSPProject bundle expansion
    - Digunakan untuk rekap computation
    - Menghindari override conflict saat multiple bundle dengan kode sama

    Relationship:
    - 1 DetailAHSPProject (LAIN bundle) → N DetailAHSPExpanded (expanded components)
    - 1 DetailAHSPProject (direct TK/BHN/ALT) → 1 DetailAHSPExpanded (pass-through)

    Example:
        DetailAHSPProject (RAW INPUT):
        Row 1: LAIN | Bundle_A | ref_pekerjaan=A | koef=2.0
        Row 2: LAIN | Bundle_B | ref_pekerjaan=B | koef=1.5
        Row 3: TK   | L.01     | direct         | koef=1.0

        DetailAHSPExpanded (COMPUTED):
        Row 1: TK.001 | source_detail=Row1 | source_bundle='Bundle_A' | koef=5.0
        Row 2: BHN.001| source_detail=Row1 | source_bundle='Bundle_A' | koef=20.0
        Row 3: TK.001 | source_detail=Row2 | source_bundle='Bundle_B' | koef=4.5  ← No conflict!
        Row 4: BHN.002| source_detail=Row2 | source_bundle='Bundle_B' | koef=12.0
        Row 5: TK.001 | source_detail=Row3 | source_bundle=NULL        | koef=1.0
    """
    project = models.ForeignKey(
        'dashboard.Project',
        on_delete=models.CASCADE,
        related_name='detail_ahsp_expanded'
    )
    pekerjaan = models.ForeignKey(
        Pekerjaan,
        on_delete=models.CASCADE,
        related_name='detail_expanded_list'
    )

    # Link back to source DetailAHSPProject (for audit trail)
    source_detail = models.ForeignKey(
        DetailAHSPProject,
        on_delete=models.CASCADE,
        related_name='expanded_components',
        help_text='Source raw input dari DetailAHSPProject'
    )

    # Expanded component data
    harga_item = models.ForeignKey(
        HargaItemProject,
        on_delete=models.PROTECT,
        related_name='expanded_refs'
    )
    kategori = models.CharField(max_length=10, choices=HargaItemProject.KATEGORI_CHOICES)
    kode = models.CharField(max_length=100)
    uraian = models.TextField()
    satuan = models.CharField(max_length=50, blank=True, null=True)
    koefisien = models.DecimalField(
        max_digits=18,
        decimal_places=6,
        validators=[MinValueValidator(0)],
        help_text='Koefisien final setelah expansion (sudah dikali multiplier)'
    )

    # Bundle metadata
    source_bundle_kode = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text='Kode bundle LAIN yang di-expand (NULL jika direct input)'
    )
    expansion_depth = models.PositiveSmallIntegerField(
        default=0,
        help_text='Kedalaman expansion (0=direct, 1=1-level bundle, 2=nested, dst)'
    )

    class Meta:
        indexes = [
            models.Index(fields=["project", "pekerjaan"]),
            models.Index(fields=["project", "pekerjaan", "kategori"]),
            models.Index(fields=["source_detail"]),
        ]
        # NO unique constraint on kode! Multiple bundles can have same kode

    def __str__(self):
        bundle_info = f" [from {self.source_bundle_kode}]" if self.source_bundle_kode else ""
        return f"{self.pekerjaan_id} / {self.kode} — {self.uraian}{bundle_info}"


class DetailAHSPAudit(TimeStampedModel):
    ACTION_CREATE = "CREATE"
    ACTION_UPDATE = "UPDATE"
    ACTION_DELETE = "DELETE"
    ACTION_CASCADE = "CASCADE"

    ACTION_CHOICES = [
        (ACTION_CREATE, "Create"),
        (ACTION_UPDATE, "Update"),
        (ACTION_DELETE, "Delete"),
        (ACTION_CASCADE, "Cascade Re-expansion"),
    ]

    TRIGGER_CHOICES = [
        ("user", "User"),
        ("cascade", "Cascade"),
        ("system", "System"),
    ]

    project = models.ForeignKey(
        'dashboard.Project',
        on_delete=models.CASCADE,
        related_name='detail_audit_entries'
    )
    pekerjaan = models.ForeignKey(
        Pekerjaan,
        on_delete=models.CASCADE,
        related_name='audit_entries'
    )
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    old_data = models.JSONField(null=True, blank=True)
    new_data = models.JSONField(null=True, blank=True)
    triggered_by = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default="user")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    change_summary = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "-created_at"]),
            models.Index(fields=["pekerjaan", "-created_at"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.project_id}/{self.pekerjaan_id} {self.action} @ {self.created_at:%Y-%m-%d %H:%M}"


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


# === Profit/Margin per Project ===
class ProjectPricing(TimeStampedModel):
    """
    Simpan Biaya Umum & Keuntungan (Profit/Margin) per project, dalam persen (0..100).
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
    # default Profit/Margin proyek
    markup_percent = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal('10.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['project'], name='uniq_project_pricing_one')
        ]

    def __str__(self):
        return f"Pricing for Project #{self.project_id}"


class TahapPelaksanaan(models.Model):
    """
    Tahapan pelaksanaan project konstruksi.
    User bisa mendefinisikan fase/tahap seperti: Persiapan, Struktur, Finishing, dll.
    """
    project = models.ForeignKey(
        'dashboard.Project', 
        on_delete=models.CASCADE, 
        related_name='tahapan'
    )
    nama = models.CharField(
        max_length=200,
        help_text="Nama tahapan (contoh: Tahap 1 - Persiapan)"
    )
    urutan = models.IntegerField(
        default=0,
        help_text="Urutan tahapan (untuk sorting)"
    )
    deskripsi = models.TextField(
        blank=True,
        help_text="Deskripsi detail tahapan (opsional)"
    )
    tanggal_mulai = models.DateField(
        null=True, 
        blank=True,
        help_text="Tanggal rencana mulai (opsional)"
    )
    tanggal_selesai = models.DateField(
        null=True,
        blank=True,
        help_text="Tanggal rencana selesai (opsional)"
    )

    # Auto-generation tracking (for time scale modes)
    is_auto_generated = models.BooleanField(
        default=False,
        help_text="True jika tahapan di-generate otomatis oleh sistem (daily/weekly/monthly mode)"
    )
    generation_mode = models.CharField(
        max_length=10,
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('custom', 'Custom'),
        ],
        null=True,
        blank=True,
        help_text="Mode yang digunakan untuk generate tahapan ini"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['urutan', 'id']
        unique_together = [('project', 'nama')]
        verbose_name = 'Tahap Pelaksanaan'
        verbose_name_plural = 'Tahap Pelaksanaan'
        indexes = [
            models.Index(fields=['project', 'urutan']),
        ]
    
    def __str__(self):
        return f"{self.nama} (Project: {self.project.nama})"
    
    def clean(self):
        """Validation untuk tanggal"""
        if self.tanggal_mulai and self.tanggal_selesai:
            if self.tanggal_selesai < self.tanggal_mulai:
                raise ValidationError({
                    'tanggal_selesai': 'Tanggal selesai harus >= tanggal mulai'
                })
    
    def get_total_pekerjaan(self):
        """Hitung jumlah pekerjaan (unique) di tahapan ini"""
        return self.pekerjaan_items.values('pekerjaan').distinct().count()
    
    def get_pekerjaan_list(self):
        """Return list pekerjaan di tahapan ini dengan proporsi"""
        return self.pekerjaan_items.select_related('pekerjaan').order_by('pekerjaan__ordering_index')


class PekerjaanProgressWeekly(models.Model):
    """
    CANONICAL STORAGE: Weekly progress for pekerjaan (single source of truth).

    This model stores progress in weekly units INDEPENDENT of TahapPelaksanaan.
    Weekly is the canonical unit - other views (daily/monthly) are calculated from this.

    Why weekly?
    - Most construction projects track progress per week
    - Avoids rounding errors when switching between time scale modes
    - Simple and maintainable

    IMPORTANT: This data is NEVER deleted when switching time scale modes!
    Only TahapPelaksanaan records are regenerated, not this canonical data.
    """
    pekerjaan = models.ForeignKey(
        'Pekerjaan',
        on_delete=models.CASCADE,
        related_name='weekly_progress'
    )
    project = models.ForeignKey(
        'dashboard.Project',
        on_delete=models.CASCADE,
        related_name='pekerjaan_weekly_progress',
        help_text="Denormalized for easier querying"
    )

    # Week identification (relative to project start date)
    week_number = models.IntegerField(
        help_text="Week number starting from 1 (relative to project start date)"
    )
    week_start_date = models.DateField(
        help_text="Start date of this week"
    )
    week_end_date = models.DateField(
        help_text="End date of this week"
    )

    # Progress data
    proportion = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(100.00)],
        help_text="Proportion of work (%) completed in this week. Range: 0.01 - 100.00"
    )

    # Metadata
    notes = models.TextField(
        blank=True,
        help_text="Optional notes for this week's progress"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [('pekerjaan', 'week_number')]
        ordering = ['pekerjaan', 'week_number']
        verbose_name = 'Weekly Progress Pekerjaan'
        verbose_name_plural = 'Weekly Progress Pekerjaan'
        indexes = [
            models.Index(fields=['pekerjaan', 'week_number']),
            models.Index(fields=['project', 'week_number']),
            models.Index(fields=['week_start_date', 'week_end_date']),
        ]

    def __str__(self):
        return f"{self.pekerjaan.snapshot_uraian} - Week {self.week_number} ({self.proportion}%)"

    def clean(self):
        """Validation"""
        if self.proportion < 0.01 or self.proportion > 100:
            raise ValidationError({
                'proportion': 'Proportion must be between 0.01% - 100%'
            })

        # Validate week dates
        if self.week_end_date < self.week_start_date:
            raise ValidationError({
                'week_end_date': 'Week end date must be >= start date'
            })

    def save(self, *args, **kwargs):
        """Auto-populate project field from pekerjaan"""
        if not self.project_id:
            # Get project from pekerjaan's volume_pekerjaan
            try:
                volume = self.pekerjaan.volume
                self.project = volume.project
            except:
                raise ValidationError('Cannot determine project from pekerjaan')

        self.full_clean()
        super().save(*args, **kwargs)


class PekerjaanTahapan(models.Model):
    """
    Junction table untuk many-to-many relationship dengan proporsi volume.
    Memungkinkan satu pekerjaan di-split ke multiple tahapan.

    IMPORTANT: Starting from the weekly canonical storage implementation,
    this model is DERIVED from PekerjaanProgressWeekly and should be
    considered a VIEW layer for backward compatibility.

    Data in this table can be regenerated from PekerjaanProgressWeekly
    when switching time scale modes.

    Contoh: Pekerjaan "Pasang Besi D13" bisa 60% di Tahap 1, 40% di Tahap 2
    """
    pekerjaan = models.ForeignKey(
        'Pekerjaan',
        on_delete=models.CASCADE,
        related_name='tahapan_assignments'
    )
    tahapan = models.ForeignKey(
        TahapPelaksanaan,
        on_delete=models.CASCADE,
        related_name='pekerjaan_items'
    )
    proporsi_volume = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(100.00)],
        help_text="Proporsi volume (%) untuk tahap ini. Range: 0.01 - 100.00"
    )
    catatan = models.TextField(
        blank=True,
        help_text="Catatan split volume (opsional)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = [('pekerjaan', 'tahapan')]
        ordering = ['tahapan__urutan', 'pekerjaan__ordering_index']
        verbose_name = 'Assignment Pekerjaan ke Tahapan'
        verbose_name_plural = 'Assignment Pekerjaan ke Tahapan'
        indexes = [
            models.Index(fields=['pekerjaan', 'tahapan']),
            models.Index(fields=['tahapan']),
        ]
    
    def __str__(self):
        return f"{self.pekerjaan.snapshot_uraian} → {self.tahapan.nama} ({self.proporsi_volume}%)"
    
    def clean(self):
        """Validation: proporsi harus 0.01-100"""
        if self.proporsi_volume < 0.01 or self.proporsi_volume > 100:
            raise ValidationError({
                'proporsi_volume': 'Proporsi volume harus antara 0.01% - 100%'
            })
    
    def save(self, *args, **kwargs):
        """Override save untuk validation"""
        self.full_clean()
        super().save(*args, **kwargs)
        
        # Validasi total proporsi setelah save
        # Note: Ini akan raise ValidationError jika total != 100%
        # Anda bisa comment jika mau allow partial assignment sementara
        # self.validate_total_proporsi()
    
    def validate_total_proporsi(self):
        """
        Pastikan total proporsi untuk pekerjaan ini = 100%
        
        Raises:
            ValidationError: Jika total proporsi != 100%
        """
        total = PekerjaanTahapan.objects.filter(
            pekerjaan=self.pekerjaan
        ).aggregate(total=Sum('proporsi_volume'))['total'] or 0
        
        # Tolerance untuk floating point comparison
        if abs(float(total) - 100.0) > 0.01:
            raise ValidationError(
                f"Total proporsi untuk pekerjaan '{self.pekerjaan.snapshot_uraian}' "
                f"harus 100%. Saat ini: {total}%"
            )
    
    @property
    def volume_efektif(self):
        """
        Hitung volume efektif untuk assignment ini.
        
        Returns:
            Decimal: Volume pekerjaan × proporsi
        """
        from decimal import Decimal
        try:
            vol_obj = self.pekerjaan.volume
            volume_total = vol_obj.quantity if vol_obj else Decimal('0')
            return volume_total * (self.proporsi_volume / Decimal('100'))
        except Exception:
            return Decimal('0')


class ProjectParameter(TimeStampedModel):
    """
    Store project-level parameters for volume formula calculations.

    Previously stored in browser localStorage, now persisted in database.
    These parameters are used in volume formulas (e.g., "panjang * lebar * tinggi").

    Examples:
        - name="panjang", value=10.000, label="Panjang (m)", unit="meter"
        - name="lebar", value=5.000, label="Lebar (m)", unit="meter"
        - name="koef_beton", value=1.2, label="Koefisien Beton", unit=""
    """
    project = models.ForeignKey(
        'dashboard.Project',
        on_delete=models.CASCADE,
        related_name='parameters',
        help_text="Project yang memiliki parameter ini"
    )
    name = models.CharField(
        max_length=100,
        help_text="Nama variabel parameter (lowercase, no spaces, e.g., 'panjang', 'lebar')"
    )
    value = models.DecimalField(
        max_digits=18,
        decimal_places=3,
        validators=[MinValueValidator(0)],
        help_text="Nilai parameter (numeric)"
    )
    label = models.CharField(
        max_length=200,
        blank=True,
        help_text="Label tampilan untuk UI (e.g., 'Panjang (m)')"
    )
    unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Satuan parameter (e.g., 'meter', 'm²', 'm³')"
    )
    description = models.TextField(
        blank=True,
        help_text="Deskripsi detail parameter (opsional)"
    )

    class Meta:
        unique_together = [('project', 'name')]
        ordering = ['name']
        verbose_name = 'Parameter Project'
        verbose_name_plural = 'Parameter Project'
        indexes = [
            models.Index(fields=['project', 'name']),
        ]

    def __str__(self):
        return f"{self.project.index_project} - {self.name} = {self.value} {self.unit}"

    def clean(self):
        """Validation"""
        # Ensure name is lowercase and no spaces
        if self.name:
            if ' ' in self.name:
                raise ValidationError({
                    'name': 'Parameter name cannot contain spaces. Use underscore instead (e.g., "koef_beton")'
                })
            # Auto-lowercase
            self.name = self.name.lower()

    def save(self, *args, **kwargs):
        """Override save for validation"""
        self.full_clean()
        super().save(*args, **kwargs)


class ProjectChangeStatus(TimeStampedModel):
    project = models.OneToOneField(
        'dashboard.Project',
        on_delete=models.CASCADE,
        related_name='change_status'
    )
    last_ahsp_change = models.DateTimeField(null=True, blank=True)
    last_harga_change = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"ChangeStatus[{self.project_id}]"
