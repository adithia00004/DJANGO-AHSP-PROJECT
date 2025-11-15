from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0009_remove_tanggal_mulai_default"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="tanggal_mulai",
            field=models.DateField(
                blank=True,
                help_text=(
                    "Tanggal mulai pelaksanaan project (wajib, tahun akan diambil dari field ini)"
                ),
                null=True,
                verbose_name="Tanggal Mulai Pelaksanaan",
            ),
        ),
    ]
