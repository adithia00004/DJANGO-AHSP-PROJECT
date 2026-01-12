from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('detail_project', '0022_projectchangestatus_unit_code_sequence'),
    ]

    operations = [
        migrations.AlterField(
          model_name='pekerjaanprogressweekly',
          name='proportion',
          field=models.DecimalField(
              decimal_places=2,
              help_text='Proportion of work (%) completed in this week. Range: 0 - 100.00',
              max_digits=5,
              validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100.0)],
          ),
        ),
    ]
