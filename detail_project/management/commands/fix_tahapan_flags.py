# detail_project/management/commands/fix_tahapan_flags.py
"""
Management command to fix existing tahapan flags.

Updates tahapan that were generated via mode switching but don't have
proper is_auto_generated and generation_mode flags set.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from detail_project.models import TahapPelaksanaan
import re


class Command(BaseCommand):
    help = 'Fix tahapan flags for auto-generated tahapan'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project-id',
            type=int,
            help='Project ID to fix (if not specified, fixes all projects)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually fixing',
        )

    def handle(self, *args, **options):
        project_id = options.get('project_id')
        dry_run = options.get('dry_run', False)

        # Build query
        queryset = TahapPelaksanaan.objects.all()

        if project_id:
            queryset = queryset.filter(project_id=project_id)
            self.stdout.write(f"\n🔍 Checking Project ID: {project_id}")
        else:
            self.stdout.write(f"\n🔍 Checking ALL projects")

        # Find tahapan that need fixing based on name patterns
        patterns = {
            'daily': [
                (r'^Day \d+$', 'daily'),
            ],
            'weekly': [
                (r'^W\d+$', 'weekly'),
                (r'^Week \d+:', 'weekly'),
                (r'^Week \d+ \(\d+-\d+\)$', 'weekly'),
            ],
            'monthly': [
                (r'^(Januari|Februari|Maret|April|Mei|Juni|Juli|Agustus|September|Oktober|November|Desember) \d{4}$', 'monthly'),
                (r'^(January|February|March|April|May|June|July|August|September|October|November|December) \d{4}$', 'monthly'),
            ]
        }

        to_fix = []

        for tahap in queryset:
            # Check if already properly flagged
            if tahap.is_auto_generated and tahap.generation_mode:
                continue

            # Try to detect mode from name
            detected_mode = None
            for mode_type, pattern_list in patterns.items():
                for pattern, mode in pattern_list:
                    if re.match(pattern, tahap.nama):
                        detected_mode = mode
                        break
                if detected_mode:
                    break

            if detected_mode:
                to_fix.append({
                    'tahap': tahap,
                    'detected_mode': detected_mode,
                    'current_auto': tahap.is_auto_generated,
                    'current_mode': tahap.generation_mode
                })

        if len(to_fix) == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ No tahapan need fixing!"))
            return

        self.stdout.write(f"\n⚠️  Found {len(to_fix)} tahapan that need fixing:\n")

        for item in to_fix:
            tahap = item['tahap']
            self.stdout.write(
                f"  - [{tahap.project.id}] {tahap.nama} (ID: {tahap.id})\n"
                f"      Current: is_auto_generated={item['current_auto']}, generation_mode={item['current_mode']}\n"
                f"      Will set: is_auto_generated=True, generation_mode='{item['detected_mode']}'"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING(
                f"\n🔍 DRY RUN: Would fix {len(to_fix)} tahapan."
            ))
            self.stdout.write("\nRun without --dry-run to actually fix.")
            return

        # Confirm
        self.stdout.write(self.style.WARNING(
            f"\n⚠️  This will update {len(to_fix)} tahapan flags."
        ))
        confirm = input("\nType 'FIX' to confirm: ")

        if confirm != 'FIX':
            self.stdout.write(self.style.ERROR("\n❌ Cancelled. No changes made."))
            return

        # Fix with transaction
        with transaction.atomic():
            fixed_count = 0
            for item in to_fix:
                tahap = item['tahap']
                tahap.is_auto_generated = True
                tahap.generation_mode = item['detected_mode']
                tahap.save()
                fixed_count += 1

            self.stdout.write(f"\n  ✓ Fixed {fixed_count} tahapan")

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Successfully fixed {fixed_count} tahapan!"
        ))
        self.stdout.write("\nNext steps:")
        self.stdout.write("  1. Refresh the jadwal_pekerjaan page")
        self.stdout.write("  2. Hard refresh browser (Ctrl+Shift+R)")
        self.stdout.write("  3. Check console - warning should be gone")
