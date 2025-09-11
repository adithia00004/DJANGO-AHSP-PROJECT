from django import forms
from .models import Project
import re
from decimal import Decimal, InvalidOperation


# ====== Project Form ======
class ProjectForm(forms.ModelForm):
    REQUIRED_FIELDS = [
        "nama",
        "tahun_project",
        "sumber_dana",
        "lokasi_project",
        "nama_client",
        "anggaran_owner",
    ]

    class Meta:
        model = Project
        fields = "__all__"
        exclude = ["owner", "index_project", "is_active", "created_at", "updated_at"]
        widgets = {
            "nama": forms.TextInput(attrs={"class": "form-control", "placeholder": "Masukkan nama project"}),
            "tahun_project": forms.NumberInput(attrs={"class": "form-control", "min": 1900, "max": 2100}),
            "sumber_dana": forms.TextInput(attrs={"class": "form-control"}),
            "lokasi_project": forms.TextInput(attrs={"class": "form-control"}),
            "nama_client": forms.TextInput(attrs={"class": "form-control"}),
            "anggaran_owner": forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric'}),
            "deskripsi": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "kategori": forms.TextInput(attrs={"class": "form-control"}),
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

    def clean_tahun_project(self):
        tahun = self.cleaned_data.get("tahun_project")
        if tahun is None or tahun < 1900 or tahun > 2100:
            raise forms.ValidationError("Tahun project harus antara 1900–2100.")
        return tahun

    def clean_anggaran_owner(self):
        raw = self.cleaned_data.get("anggaran_owner")

        # Kosong -> 0
        if raw in (None, ""):
            return Decimal("0")

        s = str(raw)

        # Sisakan angka, koma, titik, minus (buang 'Rp', spasi, dll)
        s = re.sub(r"[^\d.,\-]", "", s)

        # Hapus titik ribuan, koma -> titik (desimal)
        s = s.replace(".", "")
        s = s.replace(",", ".")

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
        # Pastikan semua field wajib terisi (guard rail kedua)
        for f in self.REQUIRED_FIELDS:
            if not cleaned.get(f):
                self.add_error(f, "Wajib diisi.")
        return cleaned


# ====== Filter & Sort ======
class ProjectFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        label="Cari Proyek",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Cari nama/kategori/lokasi/sumber dana"}),
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ("-updated_at", "Update Terbaru"),
            ("updated_at", "Update Terlama"),
            ("nama", "Nama A–Z"),
            ("-nama", "Nama Z–A"),
            ("-tahun_project", "Tahun ↓"),
            ("tahun_project", "Tahun ↑"),
        ],
        label="Urutkan",
        widget=forms.Select(attrs={"class": "form-select"}),
    )


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
