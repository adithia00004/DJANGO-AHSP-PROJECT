# -*- coding: utf-8 -*-
"""
Django management command untuk test bundle koefisien fix

Usage:
    python manage.py test_bundle_koef_fix --project=110
"""

from django.core.management.base import BaseCommand
from dashboard.models import Project
from detail_project.models import Pekerjaan
from detail_project.services import compute_rekap_for_project
from decimal import Decimal


class Command(BaseCommand):
    help = 'Test bundle koefisien fix for project with bundle items'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project',
            type=int,
            required=True,
            help='Project ID',
        )

    def handle(self, *args, **options):
        project_id = options['project']

        self.stdout.write("=" * 100)
        self.stdout.write("TEST BUNDLE KOEFISIEN FIX")
        self.stdout.write("=" * 100)

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Project ID {project_id} not found!"))
            return

        self.stdout.write(f"\n[OK] Project: {project.nama} (ID: {project.id})")

        # Test scenarios
        test_cases = [
            {
                'kode': 'CUST-0001',
                'name': 'Bundle with koef=10',
                'expected_E_base': Decimal('2347200.00'),
                'expected_G': Decimal('2581920.00'),
            },
            {
                'kode': 'CUST-0002',
                'name': 'Bundle with koef=10 (copy)',
                'expected_E_base': Decimal('2347200.00'),
                'expected_G': Decimal('2581920.00'),
            },
            {
                'kode': '2.2.1.3.3',
                'name': 'Referenced pekerjaan (no bundle)',
                'expected_E_base': Decimal('234720.00'),
                'expected_G': Decimal('258192.00'),
            },
        ]

        data = compute_rekap_for_project(project)

        all_pass = True

        for tc in test_cases:
            self.stdout.write("\n" + "-" * 100)
            self.stdout.write(f"TEST: {tc['name']} ({tc['kode']})")
            self.stdout.write("-" * 100)

            # Find pekerjaan in rekap data
            pekerjaan_data = None
            for r in data:
                if r.get('kode') == tc['kode']:
                    pekerjaan_data = r
                    break

            if not pekerjaan_data:
                self.stdout.write(self.style.ERROR(f"[FAIL] Pekerjaan {tc['kode']} not found!"))
                all_pass = False
                continue

            E_base = Decimal(str(pekerjaan_data.get('E_base', 0)))
            G = Decimal(str(pekerjaan_data.get('G', 0)))

            # Display values
            self.stdout.write(f"\nActual values:")
            self.stdout.write(f"  E_base: Rp {E_base:,.2f}")
            self.stdout.write(f"  G:      Rp {G:,.2f}")

            self.stdout.write(f"\nExpected values:")
            self.stdout.write(f"  E_base: Rp {tc['expected_E_base']:,.2f}")
            self.stdout.write(f"  G:      Rp {tc['expected_G']:,.2f}")

            # Verify
            e_base_match = abs(E_base - tc['expected_E_base']) < Decimal('0.01')
            g_match = abs(G - tc['expected_G']) < Decimal('0.01')

            self.stdout.write(f"\nVerification:")
            if e_base_match:
                self.stdout.write(self.style.SUCCESS(f"  [PASS] E_base matches"))
            else:
                self.stdout.write(self.style.ERROR(f"  [FAIL] E_base mismatch! Expected {tc['expected_E_base']}, got {E_base}"))
                all_pass = False

            if g_match:
                self.stdout.write(self.style.SUCCESS(f"  [PASS] G matches"))
            else:
                self.stdout.write(self.style.ERROR(f"  [FAIL] G mismatch! Expected {tc['expected_G']}, got {G}"))
                all_pass = False

        # Final result
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("FINAL RESULT")
        self.stdout.write("=" * 100)

        if all_pass:
            self.stdout.write(self.style.SUCCESS("\n[PASS] ALL TESTS PASSED!\n"))
        else:
            self.stdout.write(self.style.ERROR("\n[FAIL] SOME TESTS FAILED!\n"))

        self.stdout.write("=" * 100 + "\n")
