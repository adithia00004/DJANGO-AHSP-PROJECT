from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0010_alter_project_tanggal_mulai"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="allow_bundle_soft_errors",
            field=models.BooleanField(
                default=False,
                help_text="Izinkan endpoint detail AHSP mengembalikan status 207 (peringatan) untuk bundle kosong.",
            ),
        ),
    ]
