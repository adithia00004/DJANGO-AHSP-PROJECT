# detail_project/management/commands/migrate_to_weekly_canonical.py
"""
Management command to migrate existing PekerjaanTahapan data to PekerjaanProgressWeekly.

This is a ONE-TIME migration command to be run after deploying the weekly canonical
storage feature.

What it does:
1. Reads all existing PekerjaanTahapan assignments
2. Converts them to weekly canonical format using daily distribution method
3. Creates PekerjaanProgressWeekly records
4. Preserves total proportions (100% rule)

IMPORTANT:
- Run this AFTER running: python manage.py migrate
- This does NOT delete existing PekerjaanTahapan data (backward compatibility)
- Safe to run multiple times (uses ignore_conflicts on bulk create)
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from detail_project.models import PekerjaanProgressWeekly, PekerjaanTahapan
from detail_project.progress_utils import migrate_existing_data_to_weekly_canonical
from dashboard.models import Project


class Command(BaseCommand):
    help = 'Migrate existing PekerjaanTahapan data to PekerjaanProgressWeekly (weekly canonical storage)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            help='Project ID to migrate (if not specified, migrates all projects)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually migrating',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force migration even if weekly data already exists',
        )

    def handle(self, *args, **options):
        project_id = options.get('project_id')
        dry_run = options.get('dry_run', False)
        force = options.get('force', False)

        self.stdout.write("\n" + "="*70)
        self.stdout.write(self.style.WARNING("MIGRATE TO WEEKLY CANONICAL STORAGE"))
        self.stdout.write("="*70 + "\n")

        # Get projects to migrate
        if project_id:
            try:
                projects = [Project.objects.get(id=project_id)]
                self.stdout.write(f"🎯 Target: Project ID {project_id}\n")
            except Project.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"❌ Project {project_id} not found!"))
                return
        else:
            projects = Project.objects.filter(
                tanggal_mulai__isnull=False
            ).order_by('id')
            self.stdout.write(f"🎯 Target: ALL projects with tanggal_mulai set ({projects.count()} projects)\n")

        if projects.count() == 0:
            self.stdout.write(self.style.ERROR("❌ No projects to migrate!"))
            return

        # Check each project
        migration_plan = []

        for project in projects:
            # Count existing data
            existing_assignments = PekerjaanTahapan.objects.filter(
                tahapan__project=project
            ).count()

            existing_weekly = PekerjaanProgressWeekly.objects.filter(
                project=project
            ).count()

            if existing_assignments == 0:
                self.stdout.write(f"  ⊘ Project {project.id} ({project.nama}): No assignments to migrate (skipping)")
                continue

            if existing_weekly > 0 and not force:
                self.stdout.write(
                    f"  ⚠️  Project {project.id} ({project.nama}): "
                    f"Already has {existing_weekly} weekly records (use --force to re-migrate)"
                )
                continue

            migration_plan.append({
                'project': project,
                'existing_assignments': existing_assignments,
                'existing_weekly': existing_weekly
            })

        if len(migration_plan) == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ No projects need migration!"))
            self.stdout.write("\nReasons:")
            self.stdout.write("  - All projects either have no assignments OR")
            self.stdout.write("  - Already migrated to weekly canonical storage")
            self.stdout.write("\nUse --force to re-migrate projects with existing weekly data.")
            return

        # Show migration plan
        self.stdout.write(f"\n📋 Migration Plan:\n")
        for item in migration_plan:
            project = item['project']
            self.stdout.write(
                f"  ✓ Project {project.id}: {project.nama}\n"
                f"      - {item['existing_assignments']} existing PekerjaanTahapan assignments\n"
                f"      - Will create weekly canonical records"
            )
            if item['existing_weekly'] > 0:
                self.stdout.write(
                    f"      - ⚠️  WARNING: {item['existing_weekly']} existing weekly records will be kept (duplicates ignored)"
                )

        self.stdout.write(f"\n📊 Total: {len(migration_plan)} project(s)")

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\n🔍 DRY RUN: Would migrate {len(migration_plan)} project(s)."
            ))
            self.stdout.write("\nRun without --dry-run to actually migrate.")
            return

        # Confirm
        self.stdout.write(self.style.WARNING(
            f"\n⚠️  This will migrate {len(migration_plan)} project(s) to weekly canonical storage."
        ))
        self.stdout.write("\nThis operation is safe:")
        self.stdout.write("  ✓ Preserves existing PekerjaanTahapan data")
        self.stdout.write("  ✓ Uses daily distribution for accurate conversion")
        self.stdout.write("  ✓ Safe to run multiple times (ignores conflicts)")

        confirm = input("\nType 'MIGRATE' to confirm: ")

        if confirm != 'MIGRATE':
            self.stdout.write(self.style.ERROR("\n❌ Cancelled. No changes made."))
            return

        # Perform migration
        self.stdout.write("\n" + "="*70)
        self.stdout.write("MIGRATION IN PROGRESS")
        self.stdout.write("="*70 + "\n")

        total_weekly_created = 0
        total_assignments_read = 0
        success_count = 0
        error_count = 0

        for item in migration_plan:
            project = item['project']

            try:
                self.stdout.write(f"\n🔄 Migrating Project {project.id}: {project.nama}")

                # Call migration function
                result = migrate_existing_data_to_weekly_canonical(project.id)

                weekly_created = result['weekly_created']
                old_assignments = result['old_assignments']

                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Created {weekly_created} weekly records from {old_assignments} assignments"
                ))

                total_weekly_created += weekly_created
                total_assignments_read += old_assignments
                success_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ ERROR: {str(e)}"))
                import traceback
                self.stdout.write(traceback.format_exc())
                error_count += 1

        # Summary
        self.stdout.write("\n" + "="*70)
        self.stdout.write("MIGRATION SUMMARY")
        self.stdout.write("="*70 + "\n")

        self.stdout.write(f"✓ Projects migrated successfully: {success_count}")
        self.stdout.write(f"✗ Projects with errors: {error_count}")
        self.stdout.write(f"📊 Total weekly records created: {total_weekly_created}")
        self.stdout.write(f"📖 Total assignments read: {total_assignments_read}")

        if success_count > 0:
            self.stdout.write(self.style.SUCCESS(
                f"\n✅ Migration completed successfully for {success_count} project(s)!"
            ))
            self.stdout.write("\nNext steps:")
            self.stdout.write("  1. Update frontend to use new API v2 endpoints")
            self.stdout.write("  2. Test mode switching - should be lossless now!")
            self.stdout.write("  3. Verify progress data consistency")
        else:
            self.stdout.write(self.style.ERROR("\n❌ Migration failed for all projects!"))
            self.stdout.write("\nCheck error messages above.")
