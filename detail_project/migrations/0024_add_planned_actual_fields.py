# Generated migration for Phase 2E.1 - Dual fields for Planned vs Actual progress
from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('detail_project', '0023_alter_pekerjaanprogressweekly_proportion'),
    ]

    operations = [
        # Step 1: Add new planned_proportion field (will hold existing data)
        migrations.AddField(
            model_name='pekerjaanprogressweekly',
            name='planned_proportion',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Planned proportion of work (%) for this week. Range: 0 - 100.00',
                max_digits=5,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100.0)
                ]
            ),
            preserve_default=False,  # Will use data migration to set values
        ),

        # Step 2: Add new actual_proportion field (default to 0 for existing records)
        migrations.AddField(
            model_name='pekerjaanprogressweekly',
            name='actual_proportion',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Actual proportion of work (%) completed in this week. Range: 0 - 100.00',
                max_digits=5,
                validators=[
                    django.core.validators.MinValueValidator(0),
                    django.core.validators.MaxValueValidator(100.0)
                ]
            ),
        ),

        # Step 3: Data migration - Copy existing 'proportion' to 'planned_proportion'
        migrations.RunPython(
            code=lambda apps, schema_editor: _copy_proportion_to_planned(apps, schema_editor),
            reverse_code=lambda apps, schema_editor: _copy_planned_to_proportion(apps, schema_editor),
        ),

        # Step 4: Add metadata field for tracking actual updates
        migrations.AddField(
            model_name='pekerjaanprogressweekly',
            name='actual_updated_at',
            field=models.DateTimeField(
                auto_now=True,
                help_text='Timestamp when actual_proportion was last updated'
            ),
        ),
    ]


def _copy_proportion_to_planned(apps, schema_editor):
    """
    Data migration: Copy existing 'proportion' values to 'planned_proportion'.
    This preserves all existing data as planned values.
    """
    PekerjaanProgressWeekly = apps.get_model('detail_project', 'PekerjaanProgressWeekly')

    # Bulk update all records
    records = PekerjaanProgressWeekly.objects.all()
    for record in records:
        record.planned_proportion = record.proportion

    # Use bulk_update for efficiency
    if records.exists():
        PekerjaanProgressWeekly.objects.bulk_update(records, ['planned_proportion'], batch_size=500)


def _copy_planned_to_proportion(apps, schema_editor):
    """
    Reverse migration: Copy 'planned_proportion' back to 'proportion'.
    """
    PekerjaanProgressWeekly = apps.get_model('detail_project', 'PekerjaanProgressWeekly')

    records = PekerjaanProgressWeekly.objects.all()
    for record in records:
        record.proportion = record.planned_proportion

    if records.exists():
        PekerjaanProgressWeekly.objects.bulk_update(records, ['proportion'], batch_size=500)
