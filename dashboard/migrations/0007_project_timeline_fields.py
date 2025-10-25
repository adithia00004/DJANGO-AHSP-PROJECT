# Generated manually for project timeline feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0006_alter_project_anggaran_owner_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='tanggal_mulai',
            field=models.DateField(blank=True, help_text='Tanggal mulai pelaksanaan project', null=True, verbose_name='Tanggal Mulai Pelaksanaan'),
        ),
        migrations.AddField(
            model_name='project',
            name='tanggal_selesai',
            field=models.DateField(blank=True, help_text='Tanggal target penyelesaian project', null=True, verbose_name='Tanggal Target Selesai'),
        ),
        migrations.AddField(
            model_name='project',
            name='durasi_hari',
            field=models.PositiveIntegerField(blank=True, help_text='Durasi pelaksanaan dalam hari kalender', null=True, verbose_name='Durasi Pelaksanaan (hari)'),
        ),
    ]
