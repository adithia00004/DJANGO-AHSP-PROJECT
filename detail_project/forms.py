# detail_project/forms.py
from django import forms
from .models import VolumePekerjaan, HargaItemProject, DetailAHSPProject

class VolumePekerjaanForm(forms.ModelForm):
    class Meta:
        model = VolumePekerjaan
        fields = ["quantity"]
        widgets = {
            "quantity": forms.NumberInput(attrs={"min": 0, "step": "0.001", "class": "form-control"})
        }

class HargaItemProjectForm(forms.ModelForm):
    class Meta:
        model = HargaItemProject
        fields = ["harga_satuan"]
        widgets = {
            "harga_satuan": forms.NumberInput(attrs={"min": 0, "step": "0.01", "class": "form-control"})
        }

class DetailAHSPRowForm(forms.ModelForm):
    class Meta:
        model = DetailAHSPProject
        fields = ["kategori", "kode", "uraian", "satuan", "koefisien"]
        widgets = {
            "kategori": forms.Select(attrs={"class": "form-select"}),
            "kode": forms.TextInput(attrs={"class": "form-control"}),
            "uraian": forms.TextInput(attrs={"class": "form-control"}),
            "satuan": forms.TextInput(attrs={"class": "form-control"}),
            "koefisien": forms.NumberInput(attrs={"min": 0, "step": "0.000001", "class": "form-control"}),
        }
