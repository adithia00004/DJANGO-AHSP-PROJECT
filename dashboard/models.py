from django.db import models
from django.contrib.auth import get_user_model
from django.urls import reverse
from datetime import datetime

User = get_user_model()



class Project(models.Model):
    # === Kolom Sistem & Identitas ===
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="projects")
    index_project = models.CharField(max_length=20, unique=True, editable=False, null=True)

    # === 6 Kolom Wajib ===
    nama = models.CharField("Nama Project", max_length=200)  # wajib
    tahun_project = models.PositiveIntegerField(null=True, blank=True)
    sumber_dana = models.CharField(max_length=255, null=True, blank=True)
    lokasi_project = models.CharField(max_length=255, null=True, blank=True)
    nama_client = models.CharField(max_length=255, null=True, blank=True)
    anggaran_owner = models.DecimalField(max_digits=20, decimal_places=2, null=True, blank=True)

    # === 10 Kolom Tambahan ===
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
    deskripsi = models.TextField(blank=True)
    kategori = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.nama} ({self.index_project})"

    def save(self, *args, **kwargs):
        if not self.index_project:
            # Format tanggal sekarang
            today_str = datetime.now().strftime('%d%m%y')
            user_id = str(self.owner.id).zfill(2)  # Bisa juga pakai username jika lebih readable
            prefix = f"PRJ-{user_id}-{today_str}"

            # Hitung berapa banyak project yang sudah dibuat hari ini oleh user ini
            count_today = Project.objects.filter(
                owner=self.owner,
                created_at__date=datetime.today().date()
            ).count() + 1

            suffix = str(count_today).zfill(4)
            self.index_project = f"{prefix}-{suffix}"

            # Pastikan unik (extra safety)
            while Project.objects.filter(index_project=self.index_project).exists():
                count_today += 1
                suffix = str(count_today).zfill(4)
                self.index_project = f"{prefix}-{suffix}"

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('project_detail', kwargs={'pk': self.pk})
