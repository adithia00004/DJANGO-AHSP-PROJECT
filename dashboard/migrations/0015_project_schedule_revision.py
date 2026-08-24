from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0014_alter_project_owner'),
    ]

    operations = [
        migrations.AddField(
            model_name='project',
            name='schedule_revision',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Versi struktur jadwal untuk mencegah penyimpanan dari halaman yang sudah kedaluwarsa',
            ),
        ),
    ]
