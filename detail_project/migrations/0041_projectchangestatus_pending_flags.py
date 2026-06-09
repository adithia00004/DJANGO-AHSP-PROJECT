from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("detail_project", "0040_parametermigrationlog"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectchangestatus",
            name="pending_reload_job_ids",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Daftar pekerjaan yang wajib reload Template/Harga setelah perubahan sumber.",
            ),
        ),
        migrations.AddField(
            model_name="projectchangestatus",
            name="pending_volume_reset_job_ids",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="Daftar pekerjaan yang wajib cek ulang Volume/Jadwal setelah perubahan sumber.",
            ),
        ),
    ]

