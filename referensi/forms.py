from django import forms

from .models import AHSPReferensi, RincianReferensi


class AHSPPreviewUploadForm(forms.Form):
    excel_file = forms.FileField(
        label="File Excel AHSP",
        help_text="Format .xlsx atau .xls (maks. 10 MB)",
    )

    MAX_SIZE_MB = 10

    def clean_excel_file(self):
        uploaded = self.cleaned_data["excel_file"]
        filename = (uploaded.name or "").lower()
        if not filename.endswith((".xlsx", ".xls")):
            raise forms.ValidationError("Hanya file Excel (.xlsx, .xls) yang diperbolehkan.")

        if uploaded.size and uploaded.size > self.MAX_SIZE_MB * 1024 * 1024:
            raise forms.ValidationError(
                f"Ukuran file melebihi {self.MAX_SIZE_MB} MB. Potong file atau bagi menjadi beberapa bagian."
            )

        return uploaded


class AHSPReferensiInlineForm(forms.ModelForm):
    class Meta:
        model = AHSPReferensi
        fields = [
            "kode_ahsp",
            "nama_ahsp",
            "klasifikasi",
            "sub_klasifikasi",
            "satuan",
            "sumber",
            "source_file",
        ]
        widgets = {
            "kode_ahsp": forms.TextInput(
                attrs={"class": "form-control form-control-sm ahsp-input text-break", "readonly": True}
            ),
            "nama_ahsp": forms.Textarea(
                attrs={
                    "class": "form-control form-control-sm ahsp-input ahsp-textarea",
                    "rows": 2,
                    "wrap": "soft",
                }
            ),
            "klasifikasi": forms.TextInput(attrs={"class": "form-control form-control-sm ahsp-input text-break"}),
            "sub_klasifikasi": forms.TextInput(attrs={"class": "form-control form-control-sm ahsp-input text-break"}),
            "satuan": forms.TextInput(attrs={"class": "form-control form-control-sm ahsp-input text-break"}),
            "sumber": forms.TextInput(
                attrs={"class": "form-control form-control-sm ahsp-input text-break", "readonly": True}
            ),
            "source_file": forms.TextInput(attrs={"class": "form-control form-control-sm ahsp-input text-break"}),
        }


class RincianReferensiInlineForm(forms.ModelForm):
    class Meta:
        model = RincianReferensi
        fields = [
            "kategori",
            "kode_item",
            "uraian_item",
            "satuan_item",
            "koefisien",
        ]
        widgets = {
            "kategori": forms.Select(attrs={"class": "form-select form-select-sm ahsp-input"}),
            "kode_item": forms.TextInput(attrs={"class": "form-control form-control-sm ahsp-input text-break"}),
            "uraian_item": forms.Textarea(
                attrs={
                    "class": "form-control form-control-sm ahsp-input ahsp-textarea",
                    "rows": 2,
                    "wrap": "soft",
                }
            ),
            "satuan_item": forms.TextInput(attrs={"class": "form-control form-control-sm ahsp-input text-break"}),
            "koefisien": forms.NumberInput(
                attrs={
                    "class": "form-control form-control-sm text-end ahsp-input",
                    "step": "0.000001",
                    "min": "0",
                }
            ),
        }
