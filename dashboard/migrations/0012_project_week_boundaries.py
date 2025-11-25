from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0011_project_allow_bundle_soft_errors'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='week_end_day',
            field=models.PositiveSmallIntegerField(default=6, help_text='Angka hari akhir minggu (0=Senin ... 6=Minggu) untuk siklus progress mingguan'),
        ),
        migrations.AddField(
            model_name='project',
            name='week_start_day',
            field=models.PositiveSmallIntegerField(default=0, help_text='Angka hari awal minggu (0=Senin ... 6=Minggu) untuk siklus progress mingguan'),
        ),
    ]
