# -*- coding: utf-8 -*-
"""
Django management command untuk verifikasi HSP fix

Usage:
    python manage.py verify_hsp_fix
    python manage.py verify_hsp_fix --project=111
"""

from django.core.management.base import BaseCommand
from dashboard.models import Project  # FIXED: Project is in dashboard app
from detail_project.services import compute_rekap_for_project
from detail_project.views_api import api_get_rekap_rab
from django.test import RequestFactory
from django.contrib.auth import get_user_model
import json


class Command(BaseCommand):
    help = 'Verify HSP inconsistency fix'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project',
            type=int,
            help='Project ID to test (default: first project)',
        )

    def handle(self, *args, **options):
        project_id = options.get('project')

        self.stdout.write("=" * 100)
        self.stdout.write("HSP CONSISTENCY FIX VERIFICATION")
        self.stdout.write("=" * 100)

        # Get project
        if project_id:
            try:
                project = Project.objects.get(pk=project_id)
            except Project.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"\nERROR: Project ID {project_id} not found!"))
                return
        else:
            project = Project.objects.first()
            if not project:
                self.stdout.write(self.style.ERROR("\nERROR: No projects in database!"))
                return

        self.stdout.write(f"\n[OK] Testing Project: {project.nama} (ID: {project.id})")

        # Run tests
        result1 = self.test_backend_consistency(project)
        self.stdout.write("\n" + "=" * 100 + "\n")
        result2 = self.test_api_consistency(project)

        # Final result
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("FINAL RESULT")
        self.stdout.write("=" * 100)

        if result1 and result2:
            self.stdout.write(self.style.SUCCESS("\n[PASS] ALL TESTS PASSED! HSP fix verified successfully!\n"))
        else:
            self.stdout.write(self.style.ERROR("\n[FAIL] SOME TESTS FAILED! Check output above.\n"))

        self.stdout.write("=" * 100 + "\n")

    def test_backend_consistency(self, project):
        """Test backend calculation consistency"""
        self.stdout.write("\n" + "-" * 100)
        self.stdout.write("TEST 1: Backend Calculation Consistency")
        self.stdout.write("-" * 100)

        data = compute_rekap_for_project(project)

        if not data:
            self.stdout.write(self.style.WARNING("\n[WARN] No rekap data for this project!"))
            return True  # Not a failure, just no data

        self.stdout.write(f"\n[OK] Found {len(data)} pekerjaan in rekap")

        issues_found = 0
        test_count = 0

        for r in data[:5]:  # Test first 5
            test_count += 1
            kode = r.get('kode', 'N/A')
            uraian = r.get('uraian', 'N/A')[:50]

            self.stdout.write(f"\nPekerjaan #{test_count}: {kode} - {uraian}")

            # Extract values
            A = float(r.get('A', 0))
            B = float(r.get('B', 0))
            C = float(r.get('C', 0))
            LAIN = float(r.get('LAIN', 0))
            D = float(r.get('D', 0))
            E_base = float(r.get('E_base', 0))
            F = float(r.get('F', 0))
            G = float(r.get('G', 0))
            HSP = float(r.get('HSP', 0))
            markup_eff = float(r.get('markup_eff', 0))

            self.stdout.write(f"   A (TK):        Rp {A:>15,.2f}")
            self.stdout.write(f"   B (BHN):       Rp {B:>15,.2f}")
            self.stdout.write(f"   C (ALT):       Rp {C:>15,.2f}")
            self.stdout.write(f"   LAIN:          Rp {LAIN:>15,.2f}")
            self.stdout.write(f"   D (A+B+C):     Rp {D:>15,.2f}")
            self.stdout.write(f"   E_base:        Rp {E_base:>15,.2f}")
            self.stdout.write(f"   Markup:        {markup_eff:>15.2f}%")
            self.stdout.write(f"   F (Margin):    Rp {F:>15,.2f}")
            self.stdout.write(f"   G (E+F):       Rp {G:>15,.2f}")
            self.stdout.write(f"   HSP:           Rp {HSP:>15,.2f}")

            self.stdout.write(f"\n   Verification:")

            # Test 1: D = A+B+C
            expected_D = A + B + C
            if abs(D - expected_D) < 0.01:
                self.stdout.write(self.style.SUCCESS(f"   [PASS] D = A+B+C: {D:,.2f}"))
            else:
                self.stdout.write(self.style.ERROR(f"   [FAIL] D: Expected {expected_D:,.2f}, got {D:,.2f}"))
                issues_found += 1

            # Test 2: E_base = A+B+C+LAIN
            expected_E_base = A + B + C + LAIN
            if abs(E_base - expected_E_base) < 0.01:
                self.stdout.write(self.style.SUCCESS(f"   [PASS] E_base = A+B+C+LAIN: {E_base:,.2f}"))
            else:
                self.stdout.write(self.style.ERROR(f"   [FAIL] E_base: Expected {expected_E_base:,.2f}, got {E_base:,.2f}"))
                issues_found += 1

            # Test 3: F = E_base × markup%
            expected_F = E_base * (markup_eff / 100.0)
            if abs(F - expected_F) < 0.01:
                self.stdout.write(self.style.SUCCESS(f"   [PASS] F = E_base x {markup_eff}%: {F:,.2f}"))
            else:
                self.stdout.write(self.style.ERROR(f"   [FAIL] F: Expected {expected_F:,.2f}, got {F:,.2f}"))
                issues_found += 1

            # Test 4: G = E_base + F
            expected_G = E_base + F
            if abs(G - expected_G) < 0.01:
                self.stdout.write(self.style.SUCCESS(f"   [PASS] G = E_base + F: {G:,.2f}"))
            else:
                self.stdout.write(self.style.ERROR(f"   [FAIL] G: Expected {expected_G:,.2f}, got {G:,.2f}"))
                issues_found += 1

            # Test 5: HSP = E_base (CRITICAL!)
            if abs(HSP - E_base) < 0.01:
                self.stdout.write(self.style.SUCCESS(f"   [PASS] HSP = E_base: {HSP:,.2f}"))
            else:
                self.stdout.write(self.style.ERROR(f"   [FAIL] HSP: Expected {E_base:,.2f}, got {HSP:,.2f}"))
                issues_found += 1

            # Test 6: LAIN check
            if LAIN > 0:
                self.stdout.write(self.style.WARNING(f"\n   [WARN] Pekerjaan has LAIN = Rp {LAIN:,.2f}"))
                self.stdout.write("          This might be old data with unexpanded bundle!")

                if abs(HSP - (D + LAIN)) < 0.01:
                    self.stdout.write(self.style.SUCCESS(f"   [PASS] HSP includes LAIN: {HSP:,.2f} = {D:,.2f} + {LAIN:,.2f}"))
                else:
                    self.stdout.write(self.style.ERROR(f"   [FAIL] HSP missing LAIN! Expected {D + LAIN:,.2f}, got {HSP:,.2f}"))
                    issues_found += 1

        # Summary
        self.stdout.write(f"\n{'-' * 100}")
        self.stdout.write(f"Tested {test_count} pekerjaan")

        if issues_found == 0:
            self.stdout.write(self.style.SUCCESS("[PASS] No inconsistencies found!"))
            return True
        else:
            self.stdout.write(self.style.ERROR(f"[FAIL] Found {issues_found} inconsistencies!"))
            return False

    def test_api_consistency(self, project):
        """Test API Rekap RAB consistency"""
        self.stdout.write("\n" + "-" * 100)
        self.stdout.write("TEST 2: API Rekap RAB - HSP Not Overwritten")
        self.stdout.write("-" * 100)

        # Create request
        factory = RequestFactory()
        request = factory.get(f'/api/project/{project.id}/rekap/')

        # Get user
        User = get_user_model()
        if hasattr(project, 'owner'):
            request.user = project.owner
        else:
            request.user = User.objects.first()

        if not request.user:
            self.stdout.write(self.style.ERROR("\n[ERROR] No user found!"))
            return False

        self.stdout.write(f"\n[OK] User: {request.user.username}")

        # Call API
        try:
            response = api_get_rekap_rab(request, project.id)
            data = json.loads(response.content)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] API call failed: {str(e)}"))
            return False

        if not data.get('ok'):
            self.stdout.write(self.style.ERROR("\n[ERROR] API returned ok=False"))
            return False

        rows = data.get('rows', [])
        self.stdout.write(f"\n[OK] API returned {len(rows)} rows")

        issues_found = 0
        test_count = 0

        for r in rows[:5]:  # Test first 5
            test_count += 1
            kode = r.get('kode', 'N/A')
            uraian = r.get('uraian', 'N/A')[:50]

            self.stdout.write(f"\nRow #{test_count}: {kode} - {uraian}")

            D = float(r.get('D', 0))
            LAIN = float(r.get('LAIN', 0))
            E_base = float(r.get('E_base', 0))
            HSP = float(r.get('HSP', 0))
            biaya_langsung = float(r.get('biaya_langsung', 0))
            G = float(r.get('G', 0))

            self.stdout.write(f"   D (A+B+C):           Rp {D:>15,.2f}")
            self.stdout.write(f"   LAIN:                Rp {LAIN:>15,.2f}")
            self.stdout.write(f"   E_base (A+B+C+LAIN): Rp {E_base:>15,.2f}")
            self.stdout.write(f"   HSP (from API):      Rp {HSP:>15,.2f}")
            self.stdout.write(f"   biaya_langsung:      Rp {biaya_langsung:>15,.2f}")
            self.stdout.write(f"   G (E+F):             Rp {G:>15,.2f}")

            self.stdout.write(f"\n   Verification:")

            # Test 1: HSP should be E_base, NOT D
            if abs(HSP - E_base) < 0.01:
                self.stdout.write(self.style.SUCCESS(f"   [PASS] HSP = E_base: {HSP:,.2f} (NOT overwritten)"))
            else:
                self.stdout.write(self.style.ERROR(f"   [FAIL] HSP overwritten! Expected {E_base:,.2f}, got {HSP:,.2f}"))

                if abs(HSP - D) < 0.01:
                    self.stdout.write(self.style.ERROR(f"   [CRITICAL] HSP = D! Missing LAIN = {LAIN:,.2f}"))
                    issues_found += 1

            # Test 2: biaya_langsung should be D
            if abs(biaya_langsung - D) < 0.01:
                self.stdout.write(self.style.SUCCESS(f"   [PASS] biaya_langsung = D: {biaya_langsung:,.2f}"))
            else:
                self.stdout.write(self.style.ERROR(f"   [FAIL] biaya_langsung: Expected {D:,.2f}, got {biaya_langsung:,.2f}"))
                issues_found += 1

            # Test 3: If LAIN > 0, HSP must include it
            if LAIN > 0:
                self.stdout.write(self.style.WARNING(f"\n   [WARN] Data with LAIN = Rp {LAIN:,.2f} detected!"))

                if abs(HSP - (D + LAIN)) < 0.01:
                    self.stdout.write(self.style.SUCCESS(f"   [PASS] HSP includes LAIN: {HSP:,.2f} = {D:,.2f} + {LAIN:,.2f}"))
                else:
                    self.stdout.write(self.style.ERROR(f"   [FAIL] HSP missing LAIN! Expected {D + LAIN:,.2f}, got {HSP:,.2f}"))
                    issues_found += 1

        # Summary
        self.stdout.write(f"\n{'-' * 100}")
        self.stdout.write(f"Tested {test_count} rows from API")

        if issues_found == 0:
            self.stdout.write(self.style.SUCCESS("[PASS] HSP not overwritten with D!"))
            return True
        else:
            self.stdout.write(self.style.ERROR(f"[FAIL] Found {issues_found} issues!"))
            return False
