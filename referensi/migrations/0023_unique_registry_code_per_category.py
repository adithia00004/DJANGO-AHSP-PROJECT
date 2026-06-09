from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("referensi", "0022_import_batch_lifecycle"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="kodeitemreferensi",
            constraint=models.UniqueConstraint(
                fields=("kategori", "kode_item"),
                name="uniq_kode_item_per_kategori",
            ),
        ),
    ]
