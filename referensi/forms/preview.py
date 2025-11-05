from django import forms
from django.conf import settings

from referensi.models import RincianReferensi
# PHASE 2: Import normalizer for kategori validation
from referensi.services.normalizers import KategoriNormalizer


class AHSPPreviewUploadForm(forms.Form):
    # PHASE 1: Use centralized config from settings
    REFERENSI_CONFIG = getattr(settings, 'REFERENSI_CONFIG', {})
    MAX_SIZE_MB = REFERENSI_CONFIG.get('file_upload', {}).get('max_size_mb', 10)
    ALLOWED_EXTENSIONS = REFERENSI_CONFIG.get('file_upload', {}).get('allowed_extensions', ['.xlsx', '.xls'])

    excel_file = forms.FileField(
        label="File Excel AHSP",
        help_text=f"Format {', '.join(ALLOWED_EXTENSIONS)} (maks. {MAX_SIZE_MB} MB)",
        widget=forms.ClearableFileInput(
            attrs={
                "class": "form-control form-control-sm",
                "accept": ",".join(ALLOWED_EXTENSIONS),
            }
        ),
    )

    def clean_excel_file(self):
        uploaded = self.cleaned_data["excel_file"]
        filename = (uploaded.name or "").lower()

        if not any(filename.endswith(ext) for ext in self.ALLOWED_EXTENSIONS):
            raise forms.ValidationError(
                f"❌ Format file tidak sesuai\n\n"
                f"File yang Anda pilih bukan file Excel. Hanya file {', '.join(self.ALLOWED_EXTENSIONS)} yang dapat diproses."
            )

        if uploaded.size and uploaded.size > self.MAX_SIZE_MB * 1024 * 1024:
            actual_mb = uploaded.size / (1024 * 1024)
            raise forms.ValidationError(
                f"📦 File terlalu besar ({actual_mb:.1f} MB)\n\n"
                f"Ukuran maksimum: {self.MAX_SIZE_MB} MB. Silakan bagi data menjadi beberapa file yang lebih kecil "
                f"atau hapus data yang tidak diperlukan."
            )

        return uploaded


class PreviewJobForm(forms.Form):
    job_index = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    sumber = forms.CharField(
        label="Sumber AHSP",
        max_length=100,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-sm ahsp-input text-break"}
        ),
    )
    kode_ahsp = forms.CharField(
        label="Kode AHSP",
        max_length=50,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-sm ahsp-input text-break"}
        ),
    )
    nama_ahsp = forms.CharField(
        label="Nama Pekerjaan",
        widget=forms.Textarea(
            attrs={
                "class": "form-control form-control-sm ahsp-input ahsp-textarea",
                "rows": 2,
                "wrap": "soft",
            }
        ),
    )
    klasifikasi = forms.CharField(
        label="Klasifikasi",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-sm ahsp-input text-break"}
        ),
    )
    sub_klasifikasi = forms.CharField(
        label="Sub-klasifikasi",
        max_length=100,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-sm ahsp-input text-break"}
        ),
    )
    satuan = forms.CharField(
        label="Satuan",
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-sm ahsp-input text-break"}
        ),
    )

    # PHASE 2: Form validators for data quality
    def clean_sumber(self):
        """Validate and clean sumber field."""
        sumber = self.cleaned_data.get('sumber', '')
        if not sumber:
            raise forms.ValidationError(
                "📝 Sumber AHSP kosong\n\n"
                "Field 'Sumber AHSP' wajib diisi. Contoh: AHSP 2022, SNI 2024, dll."
            )
        return sumber.strip()

    def clean_kode_ahsp(self):
        """Validate and clean kode AHSP field."""
        kode = self.cleaned_data.get('kode_ahsp', '')
        if not kode:
            raise forms.ValidationError(
                "📝 Kode AHSP kosong\n\n"
                "Field 'Kode AHSP' wajib diisi. Contoh: 6.1.1, A.1.2.3, dll."
            )
        return kode.strip()

    def clean_nama_ahsp(self):
        """Validate and clean nama AHSP field."""
        nama = self.cleaned_data.get('nama_ahsp', '')
        if not nama:
            raise forms.ValidationError(
                "📝 Nama pekerjaan kosong\n\n"
                "Field 'Nama Pekerjaan' wajib diisi dengan deskripsi pekerjaan."
            )
        return nama.strip()


class PreviewDetailForm(forms.Form):
    job_index = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    detail_index = forms.IntegerField(widget=forms.HiddenInput, min_value=0)
    kategori = forms.ChoiceField(
        choices=RincianReferensi.Kategori.choices,
        widget=forms.Select(attrs={"class": "form-select form-select-sm ahsp-input"}),
    )
    kode_item = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-sm ahsp-input text-break"}
        ),
    )
    uraian_item = forms.CharField(
        widget=forms.Textarea(
            attrs={
                "class": "form-control form-control-sm ahsp-input ahsp-textarea",
                "rows": 2,
                "wrap": "soft",
            }
        ),
    )
    satuan_item = forms.CharField(
        max_length=20,
        widget=forms.TextInput(
            attrs={"class": "form-control form-control-sm ahsp-input text-break"}
        ),
    )
    koefisien = forms.DecimalField(
        max_digits=20,
        decimal_places=6,
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control form-control-sm text-end ahsp-input",
                "step": "0.000001",
                "min": "0",
            }
        ),
    )

    # PHASE 2: Form validators for data quality
    def clean_kategori(self):
        """Validate and normalize kategori using KategoriNormalizer."""
        kategori = self.cleaned_data.get('kategori', '')
        if not kategori:
            raise forms.ValidationError(
                "📝 Kategori kosong\n\n"
                "Field 'Kategori' wajib diisi."
            )

        # Normalize the kategori value
        normalized = KategoriNormalizer.normalize(kategori)

        # Validate against allowed values
        if not KategoriNormalizer.is_valid(normalized):
            valid_codes = ', '.join(KategoriNormalizer.get_all_codes())
            raise forms.ValidationError(
                f"❌ Kategori tidak valid: '{kategori}'\n\n"
                f"Kategori harus salah satu dari: {valid_codes}"
            )

        return normalized

    def clean_uraian_item(self):
        """Validate and clean uraian item field."""
        uraian = self.cleaned_data.get('uraian_item', '')
        if not uraian:
            raise forms.ValidationError(
                "📝 Uraian item kosong\n\n"
                "Field 'Uraian Item' wajib diisi dengan deskripsi material/upah/alat."
            )
        return uraian.strip()

    def clean_satuan_item(self):
        """Validate and clean satuan item field."""
        satuan = self.cleaned_data.get('satuan_item', '')
        if not satuan:
            raise forms.ValidationError(
                "📝 Satuan item kosong\n\n"
                "Field 'Satuan' wajib diisi. Contoh: m3, kg, unit, OH, dll."
            )
        return satuan.strip()

    def clean_koefisien(self):
        """Validate koefisien is non-negative."""
        koef = self.cleaned_data.get('koefisien')
        if koef is None:
            raise forms.ValidationError(
                "📝 Koefisien kosong\n\n"
                "Field 'Koefisien' wajib diisi dengan angka. Contoh: 1.5, 0.25, dll."
            )
        if koef < 0:
            raise forms.ValidationError(
                "❌ Koefisien tidak boleh negatif\n\n"
                "Koefisien harus berupa angka positif. Contoh: 1.5, 0.25, 2, dll."
            )
        return koef
