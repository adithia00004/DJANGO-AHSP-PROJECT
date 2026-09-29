from django.db import models
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


class Project(models.Model):
    # === Kolom Sistem & Identitas ===
    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="projects", db_index=True)
    index_project = models.CharField(max_length=30, unique=True, editable=False, null=True, blank=True)

    # === 6 Kolom Wajib ===
    nama = models.CharField("Nama Project", max_length=200)  # wajib
    tahun_project = models.PositiveIntegerField(editable=False, null=True, blank=True)  # auto-calculated from tanggal_mulai
    sumber_dana = models.CharField(max_length=255)           # wajib
    lokasi_project = models.CharField(max_length=255)        # wajib
    nama_client = models.CharField(max_length=255)           # wajib
    anggaran_owner = models.DecimalField(max_digits=20, decimal_places=2)  # wajib

    # === 10 Kolom Tambahan (opsional) ===
    ket_project1 = models.CharField(max_length=255, blank=True, null=True)
    ket_project2 = models.CharField(max_length=255, blank=True, null=True)
    # Keterangan 1 pada lembar pengesahan (jabatan/peran, mis. "PPK Konstruksi").
    # Nama field dipertahankan karena sudah terisi di sebagian besar project.
    jabatan_client = models.CharField(max_length=255, blank=True, null=True)
    # Keterangan 2 pada lembar pengesahan (NIP atau identitas sejenis).
    ket_client2 = models.CharField(max_length=255, blank=True, null=True)
    # Sebutan peran pemilik di lembar pengesahan. Sebagian instansi mewajibkan
    # sebutan tertentu ("Pejabat Pembuat Komitmen Dinas X", "Penanggung Jawab
    # Perusahaan Y"). Kosong berarti pakai default "Pemilik Proyek".
    sebutan_client = models.CharField(max_length=255, blank=True, null=True)
    instansi_client = models.CharField(max_length=255, blank=True, null=True)
    nama_kontraktor = models.CharField(max_length=255, blank=True, null=True)
    instansi_kontraktor = models.CharField(max_length=255, blank=True, null=True)
    nama_konsultan_perencana = models.CharField(max_length=255, blank=True, null=True)
    instansi_konsultan_perencana = models.CharField(max_length=255, blank=True, null=True)
    nama_konsultan_pengawas = models.CharField(max_length=255, blank=True, null=True)
    instansi_konsultan_pengawas = models.CharField(max_length=255, blank=True, null=True)

    # === Kolom tambahan dari sistem lama ===
    deskripsi = models.TextField(blank=True, null=True)
    kategori = models.CharField(max_length=100, blank=True, null=True)
    allow_bundle_soft_errors = models.BooleanField(
        default=False,
        help_text="Izinkan endpoint detail AHSP mengembalikan status 207 (peringatan) untuk bundle kosong."
    )

    # === Timeline Pelaksanaan Project ===
    tanggal_mulai = models.DateField(
        'Tanggal Mulai Pelaksanaan',
        help_text='Tanggal mulai pelaksanaan project (wajib, tahun akan diambil dari field ini)',
        null=True,
        blank=True,
    )
    tanggal_selesai = models.DateField(
        'Tanggal Target Selesai',
        null=True,
        blank=True,
        help_text='Tanggal target penyelesaian project'
    )
    tanggal_akhir_tambahan = models.DateField(
        'Akhir Tambahan Waktu Kerja',
        null=True,
        blank=True,
        help_text='Tanggal akhir pencatatan realisasi setelah akhir waktu kerja kontrak',
    )
    durasi_hari = models.PositiveIntegerField(
        'Durasi Pelaksanaan (hari)',
        null=True,
        blank=True,
        help_text='Durasi pelaksanaan dalam hari kalender'
    )

    week_start_day = models.PositiveSmallIntegerField(
        default=0,
        blank=True,
        null=True,
        help_text='Angka hari awal minggu (0=Senin, 1=Selasa ... 6=Minggu) untuk siklus progress mingguan'
    )
    week_end_day = models.PositiveSmallIntegerField(
        default=6,
        blank=True,
        null=True,
        help_text='Angka hari akhir minggu (0=Senin, 1=Selasa ... 6=Minggu) untuk siklus progress mingguan'
    )
    schedule_revision = models.PositiveIntegerField(
        default=1,
        help_text='Versi struktur jadwal untuk mencegah penyimpanan dari halaman yang sudah kedaluwarsa'
    )

    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['owner', '-updated_at']),
            models.Index(fields=['nama']),
            models.Index(fields=['tahun_project']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(tanggal_akhir_tambahan__isnull=True)
                    | models.Q(
                        tanggal_selesai__isnull=False,
                        tanggal_akhir_tambahan__gt=models.F('tanggal_selesai'),
                    )
                ),
                name='project_additional_end_after_contract_end',
            ),
        ]

    def __str__(self):
        return f"{self.index_project or 'PRJ-NEW'} — {self.nama}"

    def save(self, *args, **kwargs):
        from datetime import date

        creating = self._state.adding and not self.index_project

        previous = None
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).values(
                'tanggal_mulai', 'tanggal_selesai', 'tanggal_akhir_tambahan', 'week_start_day',
                'week_end_day', 'schedule_revision'
            ).first()

        # Provide safe defaults when callers omit mandatory business fields (e.g., in unit tests)
        if not getattr(self, "sumber_dana", None):
            self.sumber_dana = "N/A"
        if not getattr(self, "lokasi_project", None):
            self.lokasi_project = "Tidak Ditentukan"
        if not getattr(self, "nama_client", None):
            self.nama_client = "Client"
        if getattr(self, "anggaran_owner", None) is None:
            self.anggaran_owner = Decimal("0.00")
        if not getattr(self, "tanggal_mulai", None):
            self.tanggal_mulai = date.today()

        try:
            self.week_start_day = int(self.week_start_day) % 7
        except (TypeError, ValueError):
            self.week_start_day = 0

        try:
            normalized_end = int(self.week_end_day) % 7
        except (TypeError, ValueError):
            normalized_end = None

        if normalized_end is None or (normalized_end - self.week_start_day) % 7 != 6:
            normalized_end = (self.week_start_day + 6) % 7
        self.week_end_day = normalized_end

        # Auto-calculate tahun_project from tanggal_mulai
        if self.tanggal_mulai:
            self.tahun_project = self.tanggal_mulai.year

            if not self.durasi_hari and self.tanggal_selesai:
                # Calculate duration from dates (ensure it's positive)
                delta = (self.tanggal_selesai - self.tanggal_mulai).days + 1
                self.durasi_hari = max(1, delta)  # Ensure minimum 1 day

        structure_changed = bool(previous and any(
            previous.get(field) != getattr(self, field)
            for field in (
                'tanggal_mulai', 'tanggal_selesai', 'tanggal_akhir_tambahan',
                'week_start_day', 'week_end_day',
            )
        ))
        if previous:
            current_revision = previous.get('schedule_revision') or 1
            if structure_changed:
                self.schedule_revision = current_revision + 1
            elif not self.schedule_revision:
                self.schedule_revision = current_revision
        elif not self.schedule_revision:
            self.schedule_revision = 1

        update_fields = kwargs.get('update_fields')
        if structure_changed and update_fields is not None:
            kwargs['update_fields'] = set(update_fields) | {'schedule_revision'}

        super().save(*args, **kwargs)

        if creating and not self.index_project:
            # Gunakan timezone-aware now
            now = timezone.localtime()
            today_str = now.strftime('%d%m%y')
            user_id = str(self.owner_id).zfill(2)

            prefix = f"PRJ-{user_id}-{today_str}"

            # Hitung urutan per user per hari
            count_today = Project.objects.filter(
                owner=self.owner,
                created_at__date=now.date()
            ).count()

            # loop sampai unik (safety terhadap race)
            while True:
                count_today += 1
                suffix = str(count_today).zfill(4)
                candidate = f"{prefix}-{suffix}"
                if not Project.objects.filter(index_project=candidate).exists():
                    self.index_project = candidate
                    break

            super().save(update_fields=["index_project"])

    def get_absolute_url(self):
        return reverse('dashboard:project_detail', kwargs={'pk': self.pk})
