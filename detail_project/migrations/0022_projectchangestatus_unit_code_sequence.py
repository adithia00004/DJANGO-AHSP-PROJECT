from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("detail_project", "0021_pekerjaan_detail_last_modified_projectchangestatus"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectchangestatus",
            name="unit_code_sequence",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Pencacah kode otomatis 'Unit-XXXX' terakhir per proyek.",
            ),
        ),
    ]
