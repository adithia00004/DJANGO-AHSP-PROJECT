# Phase 0.1: Remove legacy 'proportion' field after dual-state migration
# This migration completes the cleanup started in 0024_add_planned_actual_fields
# by removing the redundant 'proportion' field and its circular sync logic.

from django.db import migrations, models


def ensure_data_migrated(apps, schema_editor):
    """
    Safety check: Ensure all 'proportion' data is copied to 'planned_proportion'.

    This handles edge cases where:
    1. Migration 0024 ran but some records were added afterward
    2. Manual data entry created records with proportion but null planned_proportion
    3. Rollback/re-apply scenarios

    Strategy:
    - If planned_proportion is NULL but proportion is NOT NULL → copy proportion to planned_proportion
    - If both are set → keep planned_proportion (it's the source of truth)
    - If both are NULL → leave as is (edge case, should not happen due to validators)
    """
    PekerjaanProgressWeekly = apps.get_model('detail_project', 'PekerjaanProgressWeekly')

    # Find records that need migration
    records_to_migrate = PekerjaanProgressWeekly.objects.filter(
        planned_proportion__isnull=True,
        proportion__isnull=False
    )

    count = records_to_migrate.count()

    if count > 0:
        print(f"\n[Migration 0025] Found {count} records with NULL planned_proportion")
        print("[Migration 0025] Copying proportion → planned_proportion...")

        # Copy proportion to planned_proportion
        for record in records_to_migrate:
            record.planned_proportion = record.proportion

        # Bulk update for efficiency
        PekerjaanProgressWeekly.objects.bulk_update(
            records_to_migrate,
            ['planned_proportion'],
            batch_size=500
        )

        print(f"[Migration 0025] SUCCESS: Migrated {count} records successfully")
    else:
        print("[Migration 0025] SUCCESS: No records need migration (all data already in planned_proportion)")

    # Validation: Check for any NULL planned_proportion after migration
    null_count = PekerjaanProgressWeekly.objects.filter(
        planned_proportion__isnull=True
    ).count()

    if null_count > 0:
        print(f"[Migration 0025] WARNING: {null_count} records still have NULL planned_proportion")
        print("[Migration 0025] This may indicate data integrity issues")
    else:
        print("[Migration 0025] SUCCESS: All records have valid planned_proportion")


def restore_proportion_from_planned(apps, schema_editor):
    """
    Reverse migration: Restore 'proportion' field from 'planned_proportion'.

    This is the rollback path if we need to undo this migration.
    Note: This function will be called BEFORE the RemoveField operation is reversed,
    so at this point the 'proportion' field already exists again.
    """
    PekerjaanProgressWeekly = apps.get_model('detail_project', 'PekerjaanProgressWeekly')

    # Copy all planned_proportion back to proportion
    records = PekerjaanProgressWeekly.objects.all()
    count = records.count()

    if count > 0:
        print(f"\n[Migration 0025 ROLLBACK] Restoring {count} records...")
        print("[Migration 0025 ROLLBACK] Copying planned_proportion → proportion...")

        for record in records:
            # Copy planned_proportion back to proportion
            if record.planned_proportion is not None:
                record.proportion = record.planned_proportion
            else:
                # Fallback: if planned_proportion is NULL, set proportion to 0
                record.proportion = 0

        # Bulk update
        PekerjaanProgressWeekly.objects.bulk_update(
            records,
            ['proportion'],
            batch_size=500
        )

        print(f"[Migration 0025 ROLLBACK] SUCCESS: Restored {count} records successfully")
    else:
        print("[Migration 0025 ROLLBACK] No records to restore")


class Migration(migrations.Migration):

    dependencies = [
        ('detail_project', '0024_add_planned_actual_fields'),
    ]

    operations = [
        # Step 1: Ensure all data is migrated from proportion to planned_proportion
        # This is a safety check in case migration 0024 didn't run fully
        migrations.RunPython(
            code=ensure_data_migrated,
            reverse_code=restore_proportion_from_planned,
        ),

        # Step 2: Remove the legacy 'proportion' field
        migrations.RemoveField(
            model_name='pekerjaanprogressweekly',
            name='proportion',
        ),
    ]
