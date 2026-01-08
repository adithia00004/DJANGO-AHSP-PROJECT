from django import forms
from .models import Project
import re
from decimal import Decimal, InvalidOperation


# ====== Project Form ======
class ProjectForm(forms.ModelForm):
    REQUIRED_FIELDS = [
        "nama",
        "tanggal_mulai",  # Changed: tanggal_mulai is now required instead of tahun_project
        "sumber_dana",
        "lokasi_project",
        "nama_client",
        "anggaran_owner",
    ]

    # Override anggaran_owner to accept string input with custom parsing
    anggaran_owner = forms.CharField(
        label="Anggaran Owner",
        required=False,  # We handle required in clean()
        widget=forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'placeholder': 'Contoh: Rp 1.000.000.000 atau 1000000000'}),
        help_text="Format: angka biasa, Rp 1.000.000, atau 1,000,000.00"
    )

    class Meta:
        model = Project
        fields = "__all__"
        exclude = ["owner", "index_project", "is_active", "created_at", "updated_at", "tahun_project", "week_start_day", "week_end_day"]
        widgets = {
            "nama": forms.TextInput(attrs={"class": "form-control", "placeholder": "Masukkan nama project"}),
            "sumber_dana": forms.TextInput(attrs={"class": "form-control"}),
            "lokasi_project": forms.TextInput(attrs={"class": "form-control"}),
            "nama_client": forms.TextInput(attrs={"class": "form-control"}),
            "deskripsi": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "kategori": forms.TextInput(attrs={"class": "form-control"}),
            # Timeline fields
            "tanggal_mulai": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "tanggal_selesai": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "durasi_hari": forms.NumberInput(attrs={"class": "form-control", "min": 1, "placeholder": "Durasi dalam hari"}),
            # Other fields
            "ket_project1": forms.TextInput(attrs={"class": "form-control"}),
            "ket_project2": forms.TextInput(attrs={"class": "form-control"}),
            "jabatan_client": forms.TextInput(attrs={"class": "form-control"}),
            "instansi_client": forms.TextInput(attrs={"class": "form-control"}),
            "nama_kontraktor": forms.TextInput(attrs={"class": "form-control"}),
            "instansi_kontraktor": forms.TextInput(attrs={"class": "form-control"}),
            "nama_konsultan_perencana": forms.TextInput(attrs={"class": "form-control"}),
            "instansi_konsultan_perencana": forms.TextInput(attrs={"class": "form-control"}),
            "nama_konsultan_pengawas": forms.TextInput(attrs={"class": "form-control"}),
            "instansi_konsultan_pengawas": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Tandai field wajib di level form (aman walau model masih null=True sementara)
        for f in self.REQUIRED_FIELDS:
            if f in self.fields:
                self.fields[f].required = True

    # === Validations ===
    def clean_nama(self):
        nama = (self.cleaned_data.get("nama") or "").strip()
        if len(nama) < 3:
            raise forms.ValidationError("Nama project minimal 3 karakter.")
        return nama

    def clean_anggaran_owner(self):
        raw = self.cleaned_data.get("anggaran_owner")

        # Kosong -> 0
        if raw in (None, ""):
            return Decimal("0")

        s = str(raw)

        # Sisakan angka, koma, titik, minus (buang 'Rp', spasi, dll)
        s = re.sub(r"[^\d.,\-]", "", s)


        # Heuristik aman untuk ribuan/desimal
        if "." in s and "," in s:
            # titik=ribuan, koma=desimal (1.234,56)
            s = s.replace(".", "").replace(",", ".")
        elif "," in s and "." not in s:
            # hanya koma
            if s.count(",") == 1 and 1 <= len(s.split(",")[1]) <= 3:
                s = s.replace(",", ".")  # desimal
            else:
                s = s.replace(",", "")   # ribuan
        elif "." in s and "," not in s:
            # hanya titik
            if s.count(".") > 1:
                s = s.replace(".", "")   # ribuan
            else:
                lhs, rhs = s.split(".")
                if len(rhs) == 3 and sum(c.isdigit() for c in s) >= 4:
                    s = s.replace(".", "")  # ribuan
                # else: desimal sah

        # Setelah normalisasi, kalau kosong -> 0
        if s.strip() == "":
            return Decimal("0")

        try:
            val = Decimal(s)
        except InvalidOperation:
            raise forms.ValidationError(
                "Anggaran tidak valid. Contoh yang benar: 15000000 atau Rp 15.000.000"
            )

        if val < 0:
            raise forms.ValidationError("Anggaran harus bernilai positif.")
        return val

    def clean_kategori(self):
        kategori = self.cleaned_data.get("kategori")
        if kategori and not re.match(r"^[a-zA-Z0-9\s]+$", kategori):
            raise forms.ValidationError("Kategori hanya boleh berisi huruf dan angka.")
        return kategori

    def clean(self):
        cleaned = super().clean()
        for f in ["nama","sumber_dana","lokasi_project","nama_client","kategori"]:
            if f in cleaned and isinstance(cleaned[f], str):
                cleaned[f] = cleaned[f].strip()
        # Pastikan semua field wajib terisi (tanpa salah tafsir nilai 0)
        for f in self.REQUIRED_FIELDS:
            if f not in cleaned or cleaned.get(f) is None or cleaned.get(f) == "":
                self.add_error(f, "Wajib diisi.")

        # Validate timeline logic
        tanggal_mulai = cleaned.get('tanggal_mulai')
        tanggal_selesai = cleaned.get('tanggal_selesai')
        durasi_hari = cleaned.get('durasi_hari')

        # If both dates are provided, validate order
        if tanggal_mulai and tanggal_selesai:
            if tanggal_selesai < tanggal_mulai:
                self.add_error('tanggal_selesai', 'Tanggal selesai harus setelah tanggal mulai.')

            # Calculate and sync durasi_hari
            delta = (tanggal_selesai - tanggal_mulai).days + 1
            if durasi_hari and durasi_hari != delta:
                # If durasi provided but doesn't match, use calculated value
                cleaned['durasi_hari'] = delta
            elif not durasi_hari:
                cleaned['durasi_hari'] = delta

        # If only durasi provided with tanggal_mulai, calculate tanggal_selesai
        elif tanggal_mulai and durasi_hari and not tanggal_selesai:
            from datetime import timedelta
            cleaned['tanggal_selesai'] = tanggal_mulai + timedelta(days=durasi_hari - 1)

        # If only durasi provided with tanggal_selesai, calculate tanggal_mulai
        elif tanggal_selesai and durasi_hari and not tanggal_mulai:
            from datetime import timedelta
            cleaned['tanggal_mulai'] = tanggal_selesai - timedelta(days=durasi_hari - 1)

        return cleaned


# ====== Filter & Sort ======
class ProjectFilterForm(forms.Form):
    # Basic search
    search = forms.CharField(
        required=False,
        label="Cari Proyek",
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Cari nama/kategori/lokasi/sumber dana"
        }),
    )

    # Sort by
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ("-updated_at", "Update Terbaru"),
            ("updated_at", "Update Terlama"),
            ("nama", "Nama A–Z"),
            ("-nama", "Nama Z–A"),
            ("-tahun_project", "Tahun ↓"),
            ("tahun_project", "Tahun ↑"),
            ("-anggaran_owner", "Anggaran Terbesar"),
            ("anggaran_owner", "Anggaran Terkecil"),
        ],
        label="Urutkan",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    # FASE 2.2: Advanced Filters

    # Filter by year
    tahun_project = forms.ChoiceField(
        required=False,
        choices=[],  # Will be populated dynamically
        label="Tahun Project",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    # Filter by sumber dana
    sumber_dana = forms.ChoiceField(
        required=False,
        choices=[],  # Will be populated dynamically
        label="Sumber Dana",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    # Filter by timeline status
    status_timeline = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Semua Status'),
            ('belum_mulai', 'Belum Mulai'),
            ('berjalan', 'Sedang Berjalan'),
            ('terlambat', 'Terlambat'),
            ('selesai', 'Selesai'),
        ],
        label="Status Timeline",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    # Filter by budget range
    anggaran_min = forms.DecimalField(
        required=False,
        label="Anggaran Min (Rp)",
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "Min"
        }),
    )

    anggaran_max = forms.DecimalField(
        required=False,
        label="Anggaran Max (Rp)",
        widget=forms.NumberInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "Max"
        }),
    )

    # Filter by date range
    tanggal_mulai_from = forms.DateField(
        required=False,
        label="Tanggal Mulai Dari",
        widget=forms.DateInput(attrs={
            "class": "form-control form-control-sm",
            "type": "date"
        }),
    )

    tanggal_mulai_to = forms.DateField(
        required=False,
        label="Tanggal Mulai Sampai",
        widget=forms.DateInput(attrs={
            "class": "form-control form-control-sm",
            "type": "date"
        }),
    )

    # Filter by active status
    is_active = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'Semua'),
            ('true', 'Aktif'),
            ('false', 'Archived'),
        ],
        label="Status",
        widget=forms.Select(attrs={"class": "form-select form-select-sm"}),
    )

    def __init__(self, *args, **kwargs):
        # Extract user for dynamic choices
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if user:
            from .models import Project

            # Populate tahun_project choices
            years = Project.objects.filter(owner=user).values_list(
                'tahun_project', flat=True
            ).distinct().order_by('-tahun_project')

            year_choices = [('', 'Semua Tahun')]
            year_choices.extend([(year, str(year)) for year in years if year])
            self.fields['tahun_project'].choices = year_choices

            # Populate sumber_dana choices
            sumber_danas = Project.objects.filter(owner=user).values_list(
                'sumber_dana', flat=True
            ).distinct().order_by('sumber_dana')

            sumber_choices = [('', 'Semua Sumber Dana')]
            sumber_choices.extend([
                (sd, sd) for sd in sumber_danas if sd and sd.strip()
            ])
            self.fields['sumber_dana'].choices = sumber_choices


# ====== Upload Excel ======
class UploadProjectForm(forms.Form):
    file = forms.FileField(
        label="Pilih file Excel (.xlsx)",
        widget=forms.ClearableFileInput(attrs={"class": "form-control"}),
        help_text="Unggah file Excel dengan format kolom sesuai template.",
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        if not f.name.lower().endswith(".xlsx"):
            raise forms.ValidationError("Format file tidak didukung. Gunakan file .xlsx.")
        # (Opsional) batasi ukuran file, contoh 10 MB:
        # if f.size > 10 * 1024 * 1024:
        #     raise forms.ValidationError("Ukuran file maksimal 10 MB.")
        return f
