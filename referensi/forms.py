from django import forms


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
