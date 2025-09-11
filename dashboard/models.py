from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

User = get_user_model()


class Project(models.Model):
    # === Kolom Sistem & Identitas ===
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects", db_index=True)
    index_project = models.CharField(max_length=30, unique=True, editable=False, null=True, blank=True)

    # === 6 Kolom Wajib ===
    nama = models.CharField("Nama Project", max_length=200)  # wajib
    tahun_project = models.PositiveIntegerField()            # wajib
    sumber_dana = models.CharField(max_length=255)           # wajib
    lokasi_project = models.CharField(max_length=255)        # wajib
    nama_client = models.CharField(max_length=255)           # wajib
    anggaran_owner = models.DecimalField(max_digits=20, decimal_places=2)  # wajib

    # === 10 Kolom Tambahan (opsional) ===
    ket_project1 = models.CharField(max_length=255, blank=True, null=True)
    ket_project2 = models.CharField(max_length=255, blank=True, null=True)
    jabatan_client = models.CharField(max_length=255, blank=True, null=True)
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

    def __str__(self):
        return f"{self.index_project or 'PRJ-NEW'} — {self.nama}"

    def save(self, *args, **kwargs):
        creating = self._state.adding and not self.index_project
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
