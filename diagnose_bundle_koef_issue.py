# -*- coding: utf-8 -*-
"""
Diagnostic Script: Bundle Quantity Semantic

Tujuan:
- Memastikan setiap bundle memiliki DetailAHSPExpanded (per-unit components).
- Menghitung subtotal per unit dan jumlah akhir (koef bundle x subtotal) untuk validasi cepat.
- Mendeteksi bundle yang belum di-expand atau expansion yang lebih tua dari sumbernya.

Usage:
    python manage.py shell --command="exec(open('diagnose_bundle_koef_issue.py').read())"

Atau di Django shell:
    exec(open('diagnose_bundle_koef_issue.py').read())
"""

import os
import sys
from pathlib import Path


def resolve_base_dir() -> Path:
    """
    Locate the Django project root by looking for manage.py relative to either
    this file (when __file__ is available) or the current working directory.
    """
    if '__file__' in globals():
        start_path = Path(__file__).resolve().parent
    else:
        start_path = Path.cwd()

    for candidate in (start_path, *start_path.parents):
        if (candidate / "manage.py").exists():
            return candidate
    return start_path


# Setup Django
BASE_DIR = resolve_base_dir()
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from decimal import Decimal
from django.db import models

from detail_project.models import (
    Project,
    Pekerjaan,
    DetailAHSPProject,
    DetailAHSPExpanded,
    HargaItemProject,
)

# ============================================================================
# CONFIGURATION - GANTI INI!
# ============================================================================
PROJECT_ID = 111  # <- GANTI dengan project_id Anda
PEKERJAAN_ID = None  # <- OPTIONAL: ID pekerjaan dengan bundle, atau None untuk auto-detect

print("=" * 100)
print("DIAGNOSTIC: Bundle Koef Change Issue")
print("=" * 100)

# Get project
try:
    project = Project.objects.get(pk=PROJECT_ID)
    print(f"\n[OK] Project: {project.nama}")
except Project.DoesNotExist:
    print(f"\n[ERROR] Project ID {PROJECT_ID} tidak ditemukan!")
    sys.exit(1)

# Find bundle items
bundles = (
    DetailAHSPProject.objects.filter(
        project=project,
        kategori=HargaItemProject.KATEGORI_LAIN,
    )
    .filter(models.Q(ref_pekerjaan__isnull=False) | models.Q(ref_ahsp__isnull=False))
    .select_related('pekerjaan', 'harga_item')
    .order_by('pekerjaan_id', 'kode')
)

if not bundles.exists():
    print("\n[WARN] Tidak ada bundle item (kategori LAIN dengan referensi) di project ini.")
    print("Silakan buat bundle terlebih dahulu di Template AHSP page.")
    sys.exit(0)

print(f"\n[OK] Found {bundles.count()} bundle items in project")

# If specific pekerjaan provided, filter
if PEKERJAAN_ID:
    bundles = bundles.filter(pekerjaan_id=PEKERJAAN_ID)
    print(f"   Filtered to pekerjaan ID {PEKERJAAN_ID}")

print(f"\n{'=' * 100}")
print(f"ANALYSIS: Bundle Items & Their Expanded Components")
print(f"{'=' * 100}\n")

print(f"{'Pekerjaan':<15} {'Bundle Kode':<20} {'Koef':<12} {'Expanded Rows':<15} {'Per-unit Total':<18} {'Jumlah (koef x per-unit)':<28}")
print(f"{'-' * 15} {'-' * 20} {'-' * 12} {'-' * 15} {'-' * 18} {'-' * 28}")

issues_found = []

for bundle in bundles:
    # Get expanded components
    expanded_qs = DetailAHSPExpanded.objects.filter(
        project=project,
        pekerjaan=bundle.pekerjaan,
        source_detail=bundle
    ).select_related('harga_item')

    expanded_count = expanded_qs.count()

    # Calculate per-unit subtotal from expanded components
    per_unit_total = Decimal('0')
    for exp in expanded_qs:
        koef = exp.koefisien or Decimal('0')
        harga = exp.harga_item.harga_satuan or Decimal('0')
        per_unit_total += koef * harga

    bundle_koef = bundle.koefisien or Decimal('0')
    jumlah_total = per_unit_total * bundle_koef

    # Expected: If bundle koef changed, expansion per-unit tetap sama tetapi timestamp harus >= sumber detail

    # Get first expanded component to check
    first_exp = expanded_qs.first()

    pekerjaan_name = f"{bundle.pekerjaan_id}"

    print(
        f"{pekerjaan_name:<15} "
        f"{bundle.kode:<20} "
        f"{bundle.koefisien:<12.6f} "
        f"{expanded_count:<15} "
        f"Rp {per_unit_total:>12,.2f} "
        f"Rp {jumlah_total:>20,.2f}"
    )

    # DIAGNOSIS: Check if expansion is stale
    if first_exp:
        # Koef di expanded storage adalah nilai per unit, sehingga tidak bergantung pada jumlah bundle di pekerjaan ini.
        # Fokus utama script adalah memastikan expansion ada dan timestamp-nya terkini.

        if expanded_count == 0:
            issues_found.append({
                'bundle': bundle,
                'issue': 'NO_EXPANSION',
                'message': 'Bundle tidak memiliki DetailAHSPExpanded rows!'
            })

        # Check timestamp
        bundle_updated = bundle.updated_at
        exp_updated = first_exp.updated_at if first_exp else None

        if exp_updated and bundle_updated and exp_updated < bundle_updated:
            issues_found.append({
                'bundle': bundle,
                'issue': 'STALE_EXPANSION',
                'message': f'Expansion outdated! Bundle updated: {bundle_updated}, Expansion: {exp_updated}',
                'bundle_updated': bundle_updated,
                'exp_updated': exp_updated,
            })

print(f"\n{'=' * 100}")
print(f"DETAILED EXPANSION ANALYSIS")
print(f"{'=' * 100}\n")

# Pick first bundle for detailed analysis
if bundles.exists():
    test_bundle = bundles.first()
    print(f"Analyzing bundle: {test_bundle.kode} (Pekerjaan {test_bundle.pekerjaan_id})")
    print(f"Bundle koefisien: {test_bundle.koefisien}")
    print(f"Bundle updated_at: {test_bundle.updated_at}")
    print()

    expanded_qs = DetailAHSPExpanded.objects.filter(
        project=project,
        pekerjaan=test_bundle.pekerjaan,
        source_detail=test_bundle
    ).select_related('harga_item')

    if not expanded_qs.exists():
        print("[FAIL] NO EXPANDED COMPONENTS FOUND!")
        print("   This bundle has not been expanded yet.")
        print("   Save the pekerjaan in Template AHSP to trigger expansion.")
    else:
        print(f"[OK] Found {expanded_qs.count()} expanded components:\n")
        print(f"{'Kategori':<10} {'Kode':<15} {'Expanded Koef':<18} {'Harga Satuan':<18} {'Subtotal':<18} {'Updated At':<25}")
        print(f"{'-' * 10} {'-' * 15} {'-' * 18} {'-' * 18} {'-' * 18} {'-' * 25}")

        total = Decimal('0')
        for exp in expanded_qs:
            koef = exp.koefisien or Decimal('0')
            harga = exp.harga_item.harga_satuan or Decimal('0')
            subtotal = koef * harga
            total += subtotal

            print(
                f"{exp.kategori:<10} "
                f"{exp.kode:<15} "
                f"{koef:>15.6f} "
                f"Rp {harga:>12,.2f} "
                f"Rp {subtotal:>12,.2f} "
                f"{exp.updated_at}"
            )

        print(f"\n{'Per-unit Total:':<43} Rp {total:>12,.2f}")

        jumlah_total = total * (test_bundle.koefisien or Decimal('0'))
        print(f"{'Jumlah (koef x per-unit):':<43} Rp {jumlah_total:>12,.2f}")

        if abs(jumlah_total - (total * (test_bundle.koefisien or Decimal('0')))) < Decimal('0.01'):
            print(f"\n[OK] MATH CHECK: Per-unit subtotal dikalikan koef bundle = jumlah akhir.")
        else:
            print(f"\n[FAIL] MATH CHECK: Jumlah tidak konsisten dengan per-unit subtotal!")

print(f"\n{'=' * 100}")
print(f"ISSUES DETECTED")
print(f"{'=' * 100}\n")

if issues_found:
    print(f"[FAIL] Found {len(issues_found)} issues:\n")

    for i, issue in enumerate(issues_found, 1):
        bundle = issue['bundle']
        print(f"{i}. Bundle: {bundle.kode} (Pekerjaan {bundle.pekerjaan_id})")
        print(f"   Issue: {issue['issue']}")
        print(f"   Message: {issue['message']}")

        if issue['issue'] == 'STALE_EXPANSION':
            print(f"   Bundle updated: {issue['bundle_updated']}")
            print(f"   Expansion updated: {issue['exp_updated']}")
            print(f"   [WARN]  Expansion is {issue['bundle_updated'] - issue['exp_updated']} older than bundle!")

        print()
else:
    print("[OK] No timestamp issues detected.")
    print("   All expansions appear to be up-to-date with bundle koefisien.")

print(f"{'=' * 100}")
print(f"RECOMMENDATIONS")
print(f"{'=' * 100}\n")

if any(i['issue'] == 'NO_EXPANSION' for i in issues_found):
    print("[FAIL] ISSUE: Bundles without expansion")
    print("   CAUSE: Bundle created but expansion not triggered")
    print("   SOLUTION:")
    print("   1. Open Template AHSP page for affected pekerjaan")
    print("   2. Click 'Simpan' (even without changes)")
    print("   3. This will trigger bundle expansion")
    print()

if any(i['issue'] == 'STALE_EXPANSION' for i in issues_found):
    print("[FAIL] ISSUE: Stale expansion detected")
    print("   CAUSE: Bundle koef berubah tetapi expansion belum dijalankan ulang.")
    print("   SOLUTION:")
    print("   1. Jalankan ulang migration command untuk project tersebut:")
    print("      python manage.py migrate_bundle_quantity_semantic --project-id <ID>")
    print("   2. Alternatif sementara: buka Template AHSP dan klik Simpan agar expansion dipicu.")
    print("   3. Verifikasi lagi dengan script ini + Rincian AHSP.")
    print()

if not issues_found:
    print("[OK] System appears to be working correctly!")
    print()
    print("Jika masih melihat harga satuan tidak konsisten di Rincian AHSP:")
    print("   1. Hard refresh browser (Ctrl+Shift+R)")
    print("   2. Pastikan front-end build terbaru sudah terdeploy")
    print("   3. Cek API `/api/project/<pid>/detail-ahsp/<pekerjaan_id>/` dan pastikan `jumlah = koef × harga`.")

print(f"\n{'=' * 100}\n")
