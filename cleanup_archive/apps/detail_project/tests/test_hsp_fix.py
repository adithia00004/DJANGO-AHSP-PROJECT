#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test script untuk verifikasi fix HSP inconsistency

Usage:
    python manage.py shell < test_hsp_fix.py

Atau di Django shell:
    exec(open('test_hsp_fix.py').read())
"""
import pytest

pytestmark = pytest.mark.django_db


def _ensure_sample_project(project_id=None):
    """
    Buat dataset dummy agar test tidak otomatis skip ketika DB kosong.
    """
    from datetime import date
    from decimal import Decimal
    from django.contrib.auth import get_user_model
    from dashboard.models import Project
    from detail_project.models import (
        Klasifikasi,
        SubKlasifikasi,
        Pekerjaan,
        HargaItemProject,
        DetailAHSPProject,
        VolumePekerjaan,
    )

    if project_id:
        existing = Project.objects.filter(pk=project_id).first()
        if existing:
            return existing
    else:
        existing = Project.objects.first()
        if existing:
            return existing

    User = get_user_model()
    owner = User.objects.first()
    if not owner:
        owner = User.objects.create_user(
            username="hsp_dummy",
            email="hsp_dummy@example.com",
            password="secret",
        )

    project_kwargs = dict(
        owner=owner,
        nama="Dummy Project HSP",
        sumber_dana="APBD",
        lokasi_project="Jakarta",
        nama_client="Client HSP",
        anggaran_owner=Decimal("100000000.00"),
        allow_bundle_soft_errors=True,
        tanggal_mulai=date.today(),
    )

    if project_id:
        project = Project(**project_kwargs)
        project.id = project_id
        project.save(force_insert=True)
    else:
        project = Project.objects.create(**project_kwargs)

    klas = Klasifikasi.objects.create(project=project, name="Klasifikasi Dummy")
    sub = SubKlasifikasi.objects.create(project=project, klasifikasi=klas, name="Sub Dummy")

    pekerjaan = Pekerjaan.objects.create(
        project=project,
        sub_klasifikasi=sub,
        source_type=Pekerjaan.SOURCE_CUSTOM,
        snapshot_kode="CUST-HSP",
        snapshot_uraian="Pekerjaan Dummy",
        snapshot_satuan="OH",
        ordering_index=1,
        detail_ready=True,
    )

    harga_item = HargaItemProject.objects.create(
        project=project,
        kode_item="TK-HSP",
        satuan="OH",
        uraian="Tenaga Kerja Dummy",
        kategori=HargaItemProject.KATEGORI_TK,
        harga_satuan=Decimal("150000.00"),
    )

    DetailAHSPProject.objects.create(
        project=project,
        pekerjaan=pekerjaan,
        harga_item=harga_item,
        kategori=HargaItemProject.KATEGORI_TK,
        kode="TK-HSP",
        uraian="Tenaga Kerja Dummy",
        satuan="OH",
        koefisien=Decimal("1.000000"),
    )

    VolumePekerjaan.objects.get_or_create(
        project=project,
        pekerjaan=pekerjaan,
        defaults={"quantity": Decimal("1.000")},
    )

    return project


def test_hsp_consistency(project_id=None):
    """
    Test consistency antara backend services.py dan API views_api.py

    Args:
        project_id: ID project untuk test (default: project pertama)
    """
    from detail_project.models import Project
    from detail_project.services import compute_rekap_for_project
    from decimal import Decimal

    print("=" * 100)
    print("TEST: HSP CONSISTENCY FIX VERIFICATION")
    print("=" * 100)

    # Build sample dataset jika belum ada
    _ensure_sample_project(project_id=project_id)

    # Get project
    if project_id:
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            msg = f"\n❌ ERROR: Project ID {project_id} tidak ditemukan!"
            print(msg)
            pytest.skip(msg)
    else:
        project = Project.objects.first()
        if not project:
            msg = "\n❌ ERROR: Tidak ada project di database!"
            print(msg)
            pytest.skip(msg)

    print(f"\n✓ Testing Project: {project.nama} (ID: {project.id})")

    # Compute rekap
    print(f"\n{'─' * 100}")
    print("STEP 1: Compute Rekap dari Backend (services.py)")
    print(f"{'─' * 100}")

    data = compute_rekap_for_project(project)

    if not data:
        msg = "\n⚠️  WARNING: Tidak ada data rekap untuk project ini!"
        print(msg)
        pytest.skip(msg)

    print(f"\n✓ Found {len(data)} pekerjaan in rekap")

    # Test sample pekerjaan
    print(f"\n{'─' * 100}")
    print("STEP 2: Verify Calculation Consistency")
    print(f"{'─' * 100}")

    issues_found = 0
    test_count = 0

    for r in data[:5]:  # Test first 5 pekerjaan
        test_count += 1
        kode = r.get('kode', 'N/A')
        uraian = r.get('uraian', 'N/A')[:50]

        print(f"\n📦 Pekerjaan #{test_count}: {kode} - {uraian}")

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

        print(f"   A (TK):        Rp {A:>15,.2f}")
        print(f"   B (BHN):       Rp {B:>15,.2f}")
        print(f"   C (ALT):       Rp {C:>15,.2f}")
        print(f"   LAIN:          Rp {LAIN:>15,.2f}")
        print(f"   D (A+B+C):     Rp {D:>15,.2f}")
        print(f"   E_base:        Rp {E_base:>15,.2f}")
        print(f"   Markup:        {markup_eff:>15.2f}%")
        print(f"   F (Margin):    Rp {F:>15,.2f}")
        print(f"   G (E+F):       Rp {G:>15,.2f}")
        print(f"   HSP:           Rp {HSP:>15,.2f}")

        # Verify calculations
        print(f"\n   🔍 Verification:")

        # Test 1: D = A+B+C
        expected_D = A + B + C
        if abs(D - expected_D) < 0.01:
            print(f"   ✅ D = A+B+C: {D:,.2f} (OK)")
        else:
            print(f"   ❌ D = A+B+C: Expected {expected_D:,.2f}, got {D:,.2f}")
            issues_found += 1

        # Test 2: E_base = A+B+C+LAIN
        expected_E_base = A + B + C + LAIN
        if abs(E_base - expected_E_base) < 0.01:
            print(f"   ✅ E_base = A+B+C+LAIN: {E_base:,.2f} (OK)")
        else:
            print(f"   ❌ E_base: Expected {expected_E_base:,.2f}, got {E_base:,.2f}")
            issues_found += 1

        # Test 3: F = E_base × markup%
        expected_F = E_base * (markup_eff / 100.0)
        if abs(F - expected_F) < 0.01:
            print(f"   ✅ F = E_base × {markup_eff}%: {F:,.2f} (OK)")
        else:
            print(f"   ❌ F: Expected {expected_F:,.2f}, got {F:,.2f}")
            issues_found += 1

        # Test 4: G = E_base + F
        expected_G = E_base + F
        if abs(G - expected_G) < 0.01:
            print(f"   ✅ G = E_base + F: {G:,.2f} (OK)")
        else:
            print(f"   ❌ G: Expected {expected_G:,.2f}, got {G:,.2f}")
            issues_found += 1

        # Test 5: HSP = E_base (CRITICAL TEST!)
        if abs(HSP - E_base) < 0.01:
            print(f"   ✅ HSP = E_base: {HSP:,.2f} (OK)")
        else:
            print(f"   ❌ HSP: Expected {E_base:,.2f} (E_base), got {HSP:,.2f}")
            issues_found += 1

        # Test 6: Check if LAIN > 0 (data lama dengan bundle?)
        if LAIN > 0:
            print(f"\n   ⚠️  WARNING: Pekerjaan ini punya LAIN = Rp {LAIN:,.2f}")
            print(f"       Ini mungkin data lama dengan bundle yang belum di-expand!")
            print(f"       Pastikan HSP include LAIN!")

            # Verify HSP includes LAIN
            if abs(HSP - (D + LAIN)) < 0.01:
                print(f"   ✅ HSP include LAIN: {HSP:,.2f} = {D:,.2f} + {LAIN:,.2f} (OK)")
            else:
                print(f"   ❌ HSP tidak include LAIN! Expected {D + LAIN:,.2f}, got {HSP:,.2f}")
                issues_found += 1

    # Summary
    print(f"\n{'=' * 100}")
    print("TEST SUMMARY")
    print(f"{'=' * 100}")
    print(f"\n✓ Tested {test_count} pekerjaan")

    if issues_found == 0:
        print(f"✅ ALL TESTS PASSED! Tidak ada inconsistency ditemukan.")
    else:
        print(f"❌ FOUND {issues_found} ISSUES! Ada inconsistency dalam perhitungan.")

    print(f"\n{'=' * 100}\n")

    if issues_found != 0:
        raise AssertionError(f"Ditemukan {issues_found} inconsistency dalam perhitungan backend.")


def test_api_rekap_rab(project_id=None):
    """
    Test API Rekap RAB untuk memastikan HSP tidak di-overwrite

    Args:
        project_id: ID project untuk test
    """
    from detail_project.models import Project
    from detail_project.views_api import api_get_rekap_rab
    from django.test import RequestFactory
    from django.contrib.auth import get_user_model
    import json

    print("=" * 100)
    print("TEST: API REKAP RAB - HSP OVERWRITE CHECK")
    print("=" * 100)

    # Build sample dataset jika DB kosong
    _ensure_sample_project(project_id=project_id)

    # Get project
    if project_id:
        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            msg = f"\n❌ ERROR: Project ID {project_id} tidak ditemukan!"
            print(msg)
            pytest.skip(msg)
    else:
        project = Project.objects.first()
        if not project:
            msg = "\n❌ ERROR: Tidak ada project di database!"
            print(msg)
            pytest.skip(msg)

    print(f"\n✓ Testing Project: {project.nama} (ID: {project.id})")

    # Create request
    factory = RequestFactory()
    request = factory.get(f'/api/project/{project.id}/rekap/')

    # Get user (project owner)
    User = get_user_model()
    if hasattr(project, 'user'):
        request.user = project.user
    else:
        request.user = User.objects.first()

    if not request.user:
        msg = "\n❌ ERROR: Tidak ada user di database!"
        print(msg)
        pytest.skip(msg)

    print(f"✓ User: {request.user.username}")

    # Call API
    print(f"\n{'─' * 100}")
    print("STEP 1: Call API Rekap RAB")
    print(f"{'─' * 100}")

    try:
        response = api_get_rekap_rab(request, project.id)
        data = json.loads(response.content)
    except Exception as e:
        msg = f"\n❌ ERROR calling API: {str(e)}"
        print(msg)
        raise AssertionError(msg)

    if not data.get('ok'):
        msg = "\n❌ ERROR: API returned ok=False"
        print(msg)
        raise AssertionError(msg)

    rows = data.get('rows', [])
    print(f"\n✓ API returned {len(rows)} rows")

    # Test rows
    print(f"\n{'─' * 100}")
    print("STEP 2: Verify HSP Not Overwritten")
    print(f"{'─' * 100}")

    issues_found = 0
    test_count = 0

    for r in rows[:5]:  # Test first 5
        test_count += 1
        kode = r.get('kode', 'N/A')
        uraian = r.get('uraian', 'N/A')[:50]

        print(f"\n📦 Row #{test_count}: {kode} - {uraian}")

        D = float(r.get('D', 0))
        LAIN = float(r.get('LAIN', 0))
        E_base = float(r.get('E_base', 0))
        HSP = float(r.get('HSP', 0))
        biaya_langsung = float(r.get('biaya_langsung', 0))
        G = float(r.get('G', 0))

        print(f"   D (A+B+C):         Rp {D:>15,.2f}")
        print(f"   LAIN:              Rp {LAIN:>15,.2f}")
        print(f"   E_base (A+B+C+LAIN): Rp {E_base:>15,.2f}")
        print(f"   HSP (from API):    Rp {HSP:>15,.2f}")
        print(f"   biaya_langsung:    Rp {biaya_langsung:>15,.2f}")
        print(f"   G (E+F):           Rp {G:>15,.2f}")

        # Test 1: HSP should be E_base, NOT D!
        print(f"\n   🔍 Verification:")

        if abs(HSP - E_base) < 0.01:
            print(f"   ✅ HSP = E_base: {HSP:,.2f} (NOT overwritten with D)")
        else:
            print(f"   ❌ HSP overwritten! Expected {E_base:,.2f} (E_base), got {HSP:,.2f}")

            # Check if it was overwritten with D
            if abs(HSP - D) < 0.01:
                print(f"   ❌ CRITICAL: HSP = D! Missing LAIN = {LAIN:,.2f}")
                issues_found += 1
            else:
                print(f"   ❌ HSP has unexpected value")
                issues_found += 1

        # Test 2: biaya_langsung should be D
        if abs(biaya_langsung - D) < 0.01:
            print(f"   ✅ biaya_langsung = D: {biaya_langsung:,.2f}")
        else:
            print(f"   ❌ biaya_langsung: Expected {D:,.2f}, got {biaya_langsung:,.2f}")
            issues_found += 1

        # Test 3: If LAIN > 0, HSP must include it!
        if LAIN > 0:
            print(f"\n   ⚠️  Data dengan LAIN = Rp {LAIN:,.2f} detected!")

            if abs(HSP - (D + LAIN)) < 0.01:
                print(f"   ✅ HSP include LAIN: {HSP:,.2f} = {D:,.2f} + {LAIN:,.2f}")
            else:
                print(f"   ❌ HSP tidak include LAIN! Expected {D + LAIN:,.2f}, got {HSP:,.2f}")
                issues_found += 1

    # Summary
    print(f"\n{'=' * 100}")
    print("TEST SUMMARY")
    print(f"{'=' * 100}")
    print(f"\n✓ Tested {test_count} rows from API")

    if issues_found == 0:
        print(f"✅ ALL TESTS PASSED! HSP tidak di-overwrite dengan D.")
    else:
        print(f"❌ FOUND {issues_found} ISSUES! HSP masih di-overwrite atau ada error lain.")

    print(f"\n{'=' * 100}\n")

    if issues_found != 0:
        raise AssertionError(f"API Rekap RAB gagal: {issues_found} isu ditemukan.")


# Auto-run tests
if __name__ == '__main__':
    print("\n🚀 Running HSP Fix Verification Tests...\n")

    # Test 1: Backend consistency
    try:
        test_hsp_consistency()
        result1 = True
    except AssertionError as exc:
        result1 = False
        print(f"\n❌ Backend consistency test failed: {exc}")
    except pytest.skip.Exception as exc:
        result1 = False
        print(f"\n⚠️ Backend consistency test skipped: {exc}")

    print("\n" + "="*100 + "\n")

    # Test 2: API consistency
    try:
        test_api_rekap_rab()
        result2 = True
    except AssertionError as exc:
        result2 = False
        print(f"\n❌ API consistency test failed: {exc}")
    except pytest.skip.Exception as exc:
        result2 = False
        print(f"\n⚠️ API consistency test skipped: {exc}")

    print("\n" + "="*100)
    print("FINAL RESULT")
    print("="*100)

    if result1 and result2:
        print("\n🎉 ALL TESTS PASSED! HSP fix verified successfully!")
    else:
        print("\n⚠️  SOME TESTS FAILED! Please check the output above.")

    print("="*100 + "\n")

else:
    print("""
To run tests manually:

    # Test backend consistency
    test_hsp_consistency(project_id=YOUR_PROJECT_ID)

    # Test API consistency
    test_api_rekap_rab(project_id=YOUR_PROJECT_ID)

    # Or omit project_id to use first project:
    test_hsp_consistency()
    test_api_rekap_rab()
""")
