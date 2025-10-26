# detail_project/management/commands/cleanup_old_tahapan.py
"""
Management command to clean up old tahapan data from deleted kelola_tahapan page.
This removes custom tahapan that are not part of the new jadwal_pekerjaan workflow.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from detail_project.models import TahapPelaksanaan, PekerjaanTahapan


class Command(BaseCommand):
    help = 'Clean up old tahapan data from deleted kelola_tahapan page'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            help='Project ID to clean (if not specified, shows all old tahapan)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deleted without actually deleting',
        )
        parser.add_argument(
            '--delete-all-custom',
            action='store_true',
            help='Delete ALL custom (non-auto-generated) tahapan',
        )

    def handle(self, *args, **options):
        project_id = options.get('project_id')
        dry_run = options.get('dry_run', False)
        delete_all_custom = options.get('delete_all_custom', False)

        # Build query
        queryset = TahapPelaksanaan.objects.all()

        if project_id:
            queryset = queryset.filter(project_id=project_id)
            self.stdout.write(f"\n🔍 Filtering for Project ID: {project_id}")
        else:
            self.stdout.write(f"\n🔍 Checking ALL projects")

        # Find old custom tahapan
        if delete_all_custom:
            old_tahapan = queryset.filter(is_auto_generated=False)
            self.stdout.write(f"\n📋 Finding ALL custom (non-auto-generated) tahapan...")
        else:
            # Find tahapan with names matching old pattern
            old_tahapan = queryset.filter(
                nama__icontains='Tahap Persiapan'
            ) | queryset.filter(
                nama__icontains='Tahap Fondasi'
            ) | queryset.filter(
                nama__icontains='Tahap Struktur'
            )
            self.stdout.write(f"\n📋 Finding old tahapan (Persiapan, Fondasi, Struktur)...")

        # Count
        total_count = old_tahapan.count()

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ No old tahapan found. Database is clean!"))
            return

        self.stdout.write(f"\n⚠️  Found {total_count} old tahapan:\n")

        # Show details
        for tahap in old_tahapan.select_related('project'):
            # Count related assignments
            assignment_count = PekerjaanTahapan.objects.filter(tahapan=tahap).count()

            self.stdout.write(
                f"  - [{tahap.project.id}] {tahap.nama} "
                f"(ID: {tahap.id}, Assignments: {assignment_count}, "
                f"Auto-gen: {tahap.is_auto_generated}, Mode: {tahap.generation_mode or 'custom'})"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\n🔍 DRY RUN: Would delete {total_count} tahapan and their assignments."
            ))
            self.stdout.write("\nRun without --dry-run to actually delete.")
            return

        # Confirm deletion
        self.stdout.write(self.style.WARNING(
            f"\n⚠️  This will DELETE {total_count} tahapan and ALL their assignments!"
        ))
        confirm = input("\nType 'DELETE' to confirm: ")

        if confirm != 'DELETE':
            self.stdout.write(self.style.ERROR("\n❌ Cancelled. No changes made."))
            return

        # Delete with transaction
        with transaction.atomic():
            # First delete assignments
            assignment_ids = []
            for tahap in old_tahapan:
                assignment_ids.extend(
                    PekerjaanTahapan.objects.filter(tahapan=tahap).values_list('id', flat=True)
                )

            assignment_count = len(assignment_ids)
            if assignment_count > 0:
                PekerjaanTahapan.objects.filter(id__in=assignment_ids).delete()
                self.stdout.write(f"\n  ✓ Deleted {assignment_count} assignments")

            # Then delete tahapan
            tahapan_ids = list(old_tahapan.values_list('id', flat=True))
            TahapPelaksanaan.objects.filter(id__in=tahapan_ids).delete()
            self.stdout.write(f"  ✓ Deleted {len(tahapan_ids)} tahapan")

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Successfully cleaned up {total_count} old tahapan and {assignment_count} assignments!"
        ))
        self.stdout.write("\nNext steps:")
        self.stdout.write("  1. Refresh the jadwal_pekerjaan page")
        self.stdout.write("  2. Use mode switching to generate new tahapan (daily/weekly/monthly)")
