"""
Management command to migrate old pekerjaan data to Storage 2.

This fixes pekerjaan that were created before the dual storage architecture
was fully implemented. It populates Storage 2 (DetailAHSPExpanded) from
Storage 1 (DetailAHSPProject) for pekerjaan where Storage 2 is empty.

Usage:
    python manage.py migrate_storage2 --project-id=<ID>
    python manage.py migrate_storage2 --project-id=<ID> --dry-run
    python manage.py migrate_storage2 --project-id=<ID> --pekerjaan-id=<ID>
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from dashboard.models import Project
from detail_project.models import Pekerjaan, DetailAHSPProject, DetailAHSPExpanded
from detail_project.services import _populate_expanded_from_raw


class Command(BaseCommand):
    help = 'Migrate old pekerjaan data to populate Storage 2 (DetailAHSPExpanded)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            required=True,
            help='Project ID to migrate'
        )
        parser.add_argument(
            '--pekerjaan-id',
            type=int,
            help='Specific pekerjaan ID to migrate (optional)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it'
        )

    def handle(self, *args, **options):
        project_id = options['project_id']
        pekerjaan_id = options.get('pekerjaan_id')
        dry_run = options.get('dry_run', False)

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Project {project_id} not found'))
            return

        self.stdout.write('=' * 80)
        self.stdout.write(f'STORAGE 2 MIGRATION - Project {project_id}')
        if dry_run:
            self.stdout.write(self.style.WARNING('🔍 DRY RUN MODE - No changes will be made'))
        self.stdout.write('=' * 80)

        # Find pekerjaan that need migration
        if pekerjaan_id:
            pekerjaan_qs = Pekerjaan.objects.filter(project=project, id=pekerjaan_id)
        else:
            pekerjaan_qs = Pekerjaan.objects.filter(project=project)

        # Identify pekerjaan with empty Storage 2
        to_migrate = []
        for pekerjaan in pekerjaan_qs:
            storage1_count = DetailAHSPProject.objects.filter(
                project=project,
                pekerjaan=pekerjaan
            ).count()

            storage2_count = DetailAHSPExpanded.objects.filter(
                project=project,
                pekerjaan=pekerjaan
            ).count()

            if storage1_count > 0 and storage2_count == 0:
                # Check for AHSP bundles (which can't be migrated)
                has_ahsp_bundle = DetailAHSPProject.objects.filter(
                    project=project,
                    pekerjaan=pekerjaan,
                    kategori='LAIN',
                    ref_ahsp_id__isnull=False,
                    ref_pekerjaan_id__isnull=True
                ).exists()

                to_migrate.append({
                    'pekerjaan': pekerjaan,
                    'storage1_count': storage1_count,
                    'has_ahsp_bundle': has_ahsp_bundle
                })

        if not to_migrate:
            self.stdout.write(self.style.SUCCESS('✅ No pekerjaan need migration!'))
            self.stdout.write('All pekerjaan already have Storage 2 populated.')
            return

        # Show what will be migrated
        self.stdout.write(f'\nFound {len(to_migrate)} pekerjaan to migrate:\n')
        self.stdout.write(f"{'ID':<6} {'Kode':<20} {'Source':<15} {'Storage1':<10} {'Status':<30}")
        self.stdout.write('-' * 80)

        for item in to_migrate:
            p = item['pekerjaan']
            status = '⚠️  AHSP Bundle (Skip)' if item['has_ahsp_bundle'] else '✅ Can migrate'
            self.stdout.write(
                f"{p.id:<6} {p.snapshot_kode[:20]:<20} {p.source_type:<15} "
                f"{item['storage1_count']:<10} {status:<30}"
            )

        # Count migratable pekerjaan
        migratable = [item for item in to_migrate if not item['has_ahsp_bundle']]
        skipped = [item for item in to_migrate if item['has_ahsp_bundle']]

        self.stdout.write('-' * 80)
        self.stdout.write(f'Total: {len(to_migrate)} pekerjaan')
        self.stdout.write(f'  ✅ Can migrate: {len(migratable)}')
        self.stdout.write(f'  ⚠️  Will skip (AHSP bundles): {len(skipped)}')

        if dry_run:
            self.stdout.write('\n' + self.style.WARNING('🔍 DRY RUN - No changes made'))
            return

        # Perform migration
        if migratable:
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write('STARTING MIGRATION...')
            self.stdout.write('=' * 80 + '\n')

            success_count = 0
            error_count = 0

            for item in migratable:
                pekerjaan = item['pekerjaan']

                try:
                    with transaction.atomic():
                        # Populate Storage 2 from Storage 1
                        # The function internally queries DetailAHSPProject
                        _populate_expanded_from_raw(
                            project=project,
                            pekerjaan=pekerjaan
                        )

                        # Verify
                        storage2_count = DetailAHSPExpanded.objects.filter(
                            project=project,
                            pekerjaan=pekerjaan
                        ).count()

                        self.stdout.write(
                            self.style.SUCCESS(
                                f'✅ {pekerjaan.id} - {pekerjaan.snapshot_kode}: '
                                f'{item["storage1_count"]} → {storage2_count} rows'
                            )
                        )
                        success_count += 1

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(
                            f'❌ {pekerjaan.id} - {pekerjaan.snapshot_kode}: ERROR - {str(e)}'
                        )
                    )
                    error_count += 1

            # Summary
            self.stdout.write('\n' + '=' * 80)
            self.stdout.write('MIGRATION COMPLETE')
            self.stdout.write('=' * 80)
            self.stdout.write(f'✅ Success: {success_count}')
            self.stdout.write(f'❌ Errors: {error_count}')
            self.stdout.write(f'⚠️  Skipped (AHSP bundles): {len(skipped)}')

            if skipped:
                self.stdout.write('\n' + self.style.WARNING('AHSP Bundles (Manual Fix Required):'))
                for item in skipped:
                    p = item['pekerjaan']
                    self.stdout.write(f'  - {p.id} - {p.snapshot_kode}')
                    self.stdout.write('    Solution: Edit pekerjaan, select from "Pekerjaan Proyek" dropdown')

        else:
            self.stdout.write('\n' + self.style.WARNING('⚠️  No pekerjaan can be auto-migrated'))
            self.stdout.write('All remaining pekerjaan have AHSP bundles and require manual editing.')
