# Generated manually for time scale feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('detail_project', '0011_tahappelaksanaan_pekerjaantahapan_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='tahappelaksanaan',
            name='is_auto_generated',
            field=models.BooleanField(default=False, help_text='True jika tahapan di-generate otomatis oleh sistem (daily/weekly/monthly mode)'),
        ),
        migrations.AddField(
            model_name='tahappelaksanaan',
            name='generation_mode',
            field=models.CharField(blank=True, choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('custom', 'Custom')], help_text='Mode yang digunakan untuk generate tahapan ini', max_length=10, null=True),
        ),
    ]
