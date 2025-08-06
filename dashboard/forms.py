from django import forms
from .models import Project


from django import forms
from .models import Project
import re

class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = '__all__'
        widgets = {
            'nama': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan nama project'}),
            'tahun_project': forms.NumberInput(attrs={'class': 'form-control'}),
            'sumber_dana': forms.TextInput(attrs={'class': 'form-control'}),
            'lokasi_project': forms.TextInput(attrs={'class': 'form-control'}),
            'nama_client': forms.TextInput(attrs={'class': 'form-control'}),
            'anggaran_owner': forms.NumberInput(attrs={'class': 'form-control'}),
            'deskripsi': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'kategori': forms.TextInput(attrs={'class': 'form-control'}),
            'ket_project1': forms.TextInput(attrs={'class': 'form-control'}),
            'ket_project2': forms.TextInput(attrs={'class': 'form-control'}),
            'jabatan_client': forms.TextInput(attrs={'class': 'form-control'}),
            'instansi_client': forms.TextInput(attrs={'class': 'form-control'}),
            'nama_kontraktor': forms.TextInput(attrs={'class': 'form-control'}),
            'instansi_kontraktor': forms.TextInput(attrs={'class': 'form-control'}),
            'nama_konsultan_perencana': forms.TextInput(attrs={'class': 'form-control'}),
            'instansi_konsultan_perencana': forms.TextInput(attrs={'class': 'form-control'}),
            'nama_konsultan_pengawas': forms.TextInput(attrs={'class': 'form-control'}),
            'instansi_konsultan_pengawas': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_tahun_project(self):
        tahun = self.cleaned_data.get('tahun_project')
        if tahun and (tahun < 1900 or tahun > 2100):
            raise forms.ValidationError("Tahun project harus antara 1900 - 2100.")
        return tahun

    def clean_anggaran_owner(self):
        anggaran = self.cleaned_data.get('anggaran_owner')
        if anggaran is None or anggaran < 0:
            raise forms.ValidationError("Anggaran harus berupa angka positif.")
        return anggaran

    def clean_sumber_dana(self):
        sumber = self.cleaned_data.get('sumber_dana')
        if not sumber:
            raise forms.ValidationError("Sumber dana wajib diisi.")
        return sumber

    def clean_lokasi_project(self):
        lokasi = self.cleaned_data.get('lokasi_project')
        if not lokasi:
            raise forms.ValidationError("Lokasi project wajib diisi.")  
        return lokasi

    def clean_nama_client(self):
        nama = self.cleaned_data.get('nama_client')
        if not nama:
            raise forms.ValidationError("Nama client wajib diisi.")
        return nama


    def clean_nama(self):
        nama = self.cleaned_data.get('nama')
        if nama and len(nama.strip()) < 3:
            raise forms.ValidationError("Nama project minimal 3 karakter.")
        return nama

    def clean_kategori(self):
        kategori = self.cleaned_data.get('kategori')
        if kategori and not re.match(r'^[a-zA-Z0-9\s]+$', kategori):
            raise forms.ValidationError("Kategori hanya boleh berisi huruf dan angka.")
        return kategori

class ProjectFilterForm(forms.Form):
    search = forms.CharField(
        required=False,
        label='Cari Proyek',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cari berdasarkan nama proyek'
        })
    )
    sort_by = forms.ChoiceField(
        required=False,
        choices=[
            ('nama', 'Nama A-Z'),
            ('-nama', 'Nama Z-A'),
            ('updated_at', 'Update Terlama'),
            ('-updated_at', 'Update Terbaru'),
        ],
        label='Urutkan',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

class UploadProjectForm(forms.Form):
    file = forms.FileField(
        label='Pilih file Excel (.xlsx)',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
        help_text='Unggah file Excel dengan format kolom sesuai template.',
    )

    def clean_file(self):
        file = self.cleaned_data['file']
        if not file.name.endswith('.xlsx'):
            raise forms.ValidationError("Format file tidak didukung. Gunakan file .xlsx.")
        return file