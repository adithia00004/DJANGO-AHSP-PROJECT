# Generated migration for ProjectParameter model

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
from django.core.validators import MinValueValidator


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0009_remove_tanggal_mulai_default'),
        ('detail_project', '0014_rename_detail_proj_pekerjaan_week_idx_detail_proj_pekerja_27e8a7_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ProjectParameter',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(help_text="Nama variabel parameter (lowercase, no spaces, e.g., 'panjang', 'lebar')", max_length=100)),
                ('value', models.DecimalField(decimal_places=3, help_text='Nilai parameter (numeric)', max_digits=18, validators=[MinValueValidator(0)])),
                ('label', models.CharField(blank=True, help_text="Label tampilan untuk UI (e.g., 'Panjang (m)')", max_length=200)),
                ('unit', models.CharField(blank=True, help_text="Satuan parameter (e.g., 'meter', 'm²', 'm³')", max_length=50)),
                ('description', models.TextField(blank=True, help_text='Deskripsi detail parameter (opsional)')),
                ('project', models.ForeignKey(help_text='Project yang memiliki parameter ini', on_delete=django.db.models.deletion.CASCADE, related_name='parameters', to='dashboard.project')),
            ],
            options={
                'verbose_name': 'Parameter Project',
                'verbose_name_plural': 'Parameter Project',
                'ordering': ['name'],
                'unique_together': {('project', 'name')},
            },
        ),
        migrations.AddIndex(
            model_name='projectparameter',
            index=models.Index(fields=['project', 'name'], name='detail_proj_project_6c8b4e_idx'),
        ),
    ]
