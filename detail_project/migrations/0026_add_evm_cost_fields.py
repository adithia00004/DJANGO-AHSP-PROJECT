from decimal import Decimal
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('detail_project', '0025_remove_legacy_proportion_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='pekerjaan',
            name='budgeted_cost',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0.00'),
                help_text='Budgeted cost (BAC) untuk pekerjaan ini',
                max_digits=15,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name='pekerjaanprogressweekly',
            name='actual_cost',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Actual cost incurred for this pekerjaan during this week',
                max_digits=15,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
    ]
