# -*- coding: utf-8 -*-
"""
Django management command untuk debug HSP display issue

Usage:
    python manage.py debug_hsp_display --project=110 --kode="2.2.1.3.3"
"""

from django.core.management.base import BaseCommand
from dashboard.models import Project
from detail_project.models import Pekerjaan
from detail_project.services import compute_rekap_for_project
from detail_project.views_api import api_get_rekap_rab
from django.test import RequestFactory
from django.contrib.auth import get_user_model
import json


class Command(BaseCommand):
    help = 'Debug HSP display inconsistency for specific pekerjaan'

    def add_arguments(self, parser):
        parser.add_argument(
            '--project',
            type=int,
            required=True,
            help='Project ID',
        )
        parser.add_argument(
            '--kode',
            type=str,
            required=True,
            help='Pekerjaan kode (e.g., "2.2.1.3.3")',
        )

    def handle(self, *args, **options):
        project_id = options['project']
        kode = options['kode']

        self.stdout.write("=" * 100)
        self.stdout.write(f"DEBUG HSP DISPLAY FOR PEKERJAAN: {kode}")
        self.stdout.write("=" * 100)

        # Get project
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Project ID {project_id} not found!"))
            return

        self.stdout.write(f"\n[OK] Project: {project.nama} (ID: {project.id})")

        # Get pekerjaan
        try:
            pekerjaan = Pekerjaan.objects.get(project=project, snapshot_kode=kode)
        except Pekerjaan.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"\n[ERROR] Pekerjaan {kode} not found!"))
            return

        self.stdout.write(f"[OK] Pekerjaan: {pekerjaan.snapshot_uraian[:50]}")
        self.stdout.write(f"[OK] Pekerjaan ID: {pekerjaan.id}")
        self.stdout.write(f"[OK] Source Type: {pekerjaan.source_type}")

        # Get volume
        try:
            volume = pekerjaan.volume.quantity
        except Exception:
            volume = 0
        self.stdout.write(f"[OK] Volume: {volume}")

        self.stdout.write("\n" + "-" * 100)
        self.stdout.write("STEP 1: Backend Services Calculation (compute_rekap_for_project)")
        self.stdout.write("-" * 100)

        data = compute_rekap_for_project(project)
        pekerjaan_data = None
        for r in data:
            if r.get('kode') == kode:
                pekerjaan_data = r
                break

        if not pekerjaan_data:
            self.stdout.write(self.style.ERROR("\n[ERROR] Pekerjaan not found in rekap data!"))
            return

        self.print_rekap_data(pekerjaan_data, volume)

        self.stdout.write("\n" + "-" * 100)
        self.stdout.write("STEP 2: API Rekap RAB Response (for sidebar LEFT)")
        self.stdout.write("-" * 100)

        # Simulate API call
        User = get_user_model()
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR("\n[ERROR] No user found!"))
            return

        # Call compute directly (since we can't easily mock the request)
        # API just wraps this data
        self.stdout.write("\n[Note] API returns the same data from services")
        self.stdout.write("[Note] Sidebar LEFT should display:")
        self.stdout.write(f"   HSP: G = {pekerjaan_data.get('G')} (Harga Satuan dengan markup)")
        self.stdout.write(f"   Expected display: Rp {float(pekerjaan_data.get('G', 0)):,.2f}")

        self.stdout.write("\n" + "-" * 100)
        self.stdout.write("STEP 3: Detail AHSP Items (for sidebar RIGHT)")
        self.stdout.write("-" * 100)

        from detail_project.models import DetailAHSPProject
        items = DetailAHSPProject.objects.filter(
            pekerjaan=pekerjaan
        ).select_related('harga_item', 'ref_ahsp', 'ref_pekerjaan')

        if not items.exists():
            self.stdout.write(self.style.WARNING("\n[WARN] No detail AHSP items found!"))
            self.stdout.write("[WARN] Sidebar RIGHT will be empty")
        else:
            self.stdout.write(f"\n[OK] Found {items.count()} detail AHSP items")

            # Group by category
            group = {'TK': [], 'BHN': [], 'ALT': [], 'LAIN': []}
            for item in items:
                kat = item.kategori
                if kat in group:
                    koef = float(item.koefisien or 0)
                    # harga_satuan comes from harga_item FK
                    harga = float(item.harga_item.harga_satuan or 0) if item.harga_item else 0
                    jumlah = koef * harga

                    group[kat].append({
                        'uraian': item.uraian,
                        'koef': koef,
                        'harga': harga,
                        'jumlah': jumlah
                    })

            # Calculate totals
            A = sum(it['jumlah'] for it in group['TK'])
            B = sum(it['jumlah'] for it in group['BHN'])
            C = sum(it['jumlah'] for it in group['ALT'])
            LAIN = sum(it['jumlah'] for it in group['LAIN'])

            self.stdout.write(f"\n   Subtotal A (TK):   Rp {A:>20,.2f}")
            self.stdout.write(f"   Subtotal B (BHN):  Rp {B:>20,.2f}")
            self.stdout.write(f"   Subtotal C (ALT):  Rp {C:>20,.2f}")
            self.stdout.write(f"   Subtotal LAIN:     Rp {LAIN:>20,.2f}")

            E_base = A + B + C + LAIN
            markup_eff = float(pekerjaan_data.get('markup_eff', 10.0))
            F = E_base * (markup_eff / 100.0)
            G = E_base + F

            self.stdout.write(f"\n   E_base (A+B+C+LAIN): Rp {E_base:>18,.2f}")
            self.stdout.write(f"   Markup: {markup_eff:.2f}%")
            self.stdout.write(f"   F (Profit/Margin):   Rp {F:>18,.2f}")
            self.stdout.write(f"   G (Harga Satuan):    Rp {G:>18,.2f}")

            self.stdout.write("\n   Expected display in sidebar RIGHT (row G):")
            self.stdout.write(f"   Rp {G:,.2f}")

        self.stdout.write("\n" + "-" * 100)
        self.stdout.write("STEP 4: Verification & Diagnosis")
        self.stdout.write("-" * 100)

        # Check consistency
        services_G = float(pekerjaan_data.get('G', 0))
        services_HSP = float(pekerjaan_data.get('HSP', 0))
        services_E_base = float(pekerjaan_data.get('E_base', 0))
        services_F = float(pekerjaan_data.get('F', 0))
        services_total = float(pekerjaan_data.get('total', 0))

        self.stdout.write("\n   Services calculation:")
        self.stdout.write(f"   E_base = Rp {services_E_base:,.2f}")
        self.stdout.write(f"   F      = Rp {services_F:,.2f}")
        self.stdout.write(f"   G      = Rp {services_G:,.2f}")
        self.stdout.write(f"   HSP    = Rp {services_HSP:,.2f} (should equal E_base)")
        self.stdout.write(f"   total  = Rp {services_total:,.2f} (G × volume)")

        self.stdout.write("\n   EXPECTED DISPLAY:")
        self.stdout.write(f"   Sidebar LEFT (meta):  HSP: Rp {services_G:,.2f}")
        self.stdout.write(f"   Sidebar RIGHT (row G): Rp {services_G:,.2f}")
        self.stdout.write(f"   Sidebar RIGHT (total): Rp {services_total:,.2f} (if shown)")

        # Check for 10x error
        if items.exists():
            detail_G = G
            ratio = services_G / detail_G if detail_G > 0 else 0

            self.stdout.write(f"\n   RATIO CHECK:")
            self.stdout.write(f"   Services G / Detail G = {services_G:,.2f} / {detail_G:,.2f} = {ratio:.4f}")

            if abs(ratio - 1.0) > 0.01:
                self.stdout.write(self.style.ERROR(f"\n   [ERROR] INCONSISTENCY DETECTED!"))
                self.stdout.write(self.style.ERROR(f"   Services and Detail calculations differ by {abs(ratio-1.0)*100:.2f}%"))

                if abs(ratio - 10.0) < 0.1:
                    self.stdout.write(self.style.ERROR("\n   [CRITICAL] 10x ERROR DETECTED!"))
                    self.stdout.write("   Possible causes:")
                    self.stdout.write("   1. Markup applied twice (once in services, once in frontend)")
                    self.stdout.write("   2. Markup used as decimal (1.10) instead of percentage (10)")
                    self.stdout.write("   3. Wrong field used (total vs G)")
            else:
                self.stdout.write(self.style.SUCCESS("\n   [OK] Services and Detail calculations are consistent"))

        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("END OF DIAGNOSIS")
        self.stdout.write("=" * 100 + "\n")

    def print_rekap_data(self, r, volume):
        """Print rekap data in formatted way"""
        A = float(r.get('A', 0))
        B = float(r.get('B', 0))
        C = float(r.get('C', 0))
        LAIN = float(r.get('LAIN', 0))
        D = float(r.get('D', 0))
        E_base = float(r.get('E_base', 0))
        markup_eff = float(r.get('markup_eff', 0))
        F = float(r.get('F', 0))
        G = float(r.get('G', 0))
        HSP = float(r.get('HSP', 0))
        total = float(r.get('total', 0))

        self.stdout.write(f"\n   A (TK):              Rp {A:>20,.2f}")
        self.stdout.write(f"   B (BHN):             Rp {B:>20,.2f}")
        self.stdout.write(f"   C (ALT):             Rp {C:>20,.2f}")
        self.stdout.write(f"   LAIN:                Rp {LAIN:>20,.2f}")
        self.stdout.write(f"   D (A+B+C):           Rp {D:>20,.2f}")
        self.stdout.write(f"   E_base (A+B+C+LAIN): Rp {E_base:>20,.2f}")
        self.stdout.write(f"   Markup effective:    {markup_eff:>20.2f}%")
        self.stdout.write(f"   F (Profit/Margin):   Rp {F:>20,.2f}")
        self.stdout.write(f"   G (Harga Satuan):    Rp {G:>20,.2f}")
        self.stdout.write(f"   HSP (E_base):        Rp {HSP:>20,.2f}")
        self.stdout.write(f"   Volume:              {volume:>24.3f}")
        self.stdout.write(f"   Total (G × volume):  Rp {total:>20,.2f}")

        # Verify calculations
        self.stdout.write(f"\n   Verification:")
        if abs(D - (A+B+C)) < 0.01:
            self.stdout.write(self.style.SUCCESS(f"   [OK] D = A+B+C"))
        else:
            self.stdout.write(self.style.ERROR(f"   [ERROR] D != A+B+C"))

        if abs(E_base - (A+B+C+LAIN)) < 0.01:
            self.stdout.write(self.style.SUCCESS(f"   [OK] E_base = A+B+C+LAIN"))
        else:
            self.stdout.write(self.style.ERROR(f"   [ERROR] E_base != A+B+C+LAIN"))

        expected_F = E_base * (markup_eff / 100.0)
        if abs(F - expected_F) < 0.01:
            self.stdout.write(self.style.SUCCESS(f"   [OK] F = E_base × {markup_eff}%"))
        else:
            self.stdout.write(self.style.ERROR(f"   [ERROR] F != E_base × {markup_eff}%"))

        if abs(G - (E_base + F)) < 0.01:
            self.stdout.write(self.style.SUCCESS(f"   [OK] G = E_base + F"))
        else:
            self.stdout.write(self.style.ERROR(f"   [ERROR] G != E_base + F"))

        if abs(HSP - E_base) < 0.01:
            self.stdout.write(self.style.SUCCESS(f"   [OK] HSP = E_base"))
        else:
            self.stdout.write(self.style.ERROR(f"   [ERROR] HSP != E_base"))

        expected_total = G * float(volume)
        if abs(total - expected_total) < 0.01:
            self.stdout.write(self.style.SUCCESS(f"   [OK] total = G × volume"))
        else:
            self.stdout.write(self.style.ERROR(f"   [ERROR] total != G × volume"))
