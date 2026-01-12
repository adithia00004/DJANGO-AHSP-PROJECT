from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("detail_project", "0033_add_rekap_kebutuhan_indexes"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="pekerjaanprogressweekly",
            index=models.Index(
                fields=["project", "pekerjaan"],
                name="idx_ppw_project_pekerjaan",
            ),
        ),
    ]
