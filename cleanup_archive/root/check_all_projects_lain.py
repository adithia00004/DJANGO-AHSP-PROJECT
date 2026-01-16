#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script untuk mengecek semua project apakah ada yang punya LAIN > 0

Usage:
    python manage.py shell < check_all_projects_lain.py
"""

from dashboard.models import Project
from detail_project.services import compute_rekap_for_project

print("=" * 100)
print("CHECKING ALL PROJECTS FOR LAIN ITEMS")
print("=" * 100)

all_projects = Project.objects.all().order_by('id')
total_projects = all_projects.count()

print(f"\nTotal projects: {total_projects}")
print(f"\n{'-' * 100}\n")

projects_with_lain = []
projects_without_lain = []

for project in all_projects:
    print(f"Checking Project #{project.id}: {project.nama[:50]}")

    try:
        data = compute_rekap_for_project(project)

        has_lain = False
        total_lain = 0
        pekerjaan_with_lain = []

        for r in data:
            lain_value = float(r.get('LAIN', 0))
            if lain_value > 0:
                has_lain = True
                total_lain += lain_value
                pekerjaan_with_lain.append({
                    'kode': r.get('kode', 'N/A'),
                    'uraian': r.get('uraian', 'N/A')[:40],
                    'lain': lain_value
                })

        if has_lain:
            projects_with_lain.append({
                'id': project.id,
                'nama': project.nama,
                'total_lain': total_lain,
                'pekerjaan': pekerjaan_with_lain
            })
            print(f"   [WARN] Has LAIN items! Total: Rp {total_lain:,.2f}")
        else:
            projects_without_lain.append(project.id)
            print(f"   [OK] No LAIN items")

    except Exception as e:
        print(f"   [ERROR] Failed to compute: {str(e)}")

print(f"\n{'=' * 100}")
print("SUMMARY")
print(f"{'=' * 100}")

print(f"\nProjects WITHOUT LAIN (safe, no impact): {len(projects_without_lain)}")
print(f"Projects WITH LAIN (affected by fix): {len(projects_with_lain)}")

if projects_with_lain:
    print(f"\n{'-' * 100}")
    print("PROJECTS WITH LAIN ITEMS (AFFECTED BY FIX):")
    print(f"{'-' * 100}")

    for p in projects_with_lain:
        print(f"\nProject #{p['id']}: {p['nama']}")
        print(f"   Total LAIN: Rp {p['total_lain']:,.2f}")
        print(f"   Pekerjaan with LAIN:")

        for pkj in p['pekerjaan']:
            print(f"      - {pkj['kode']}: {pkj['uraian']}")
            print(f"        LAIN = Rp {pkj['lain']:,.2f}")

    print(f"\n{'-' * 100}")
    print("RECOMMENDATION:")
    print(f"{'-' * 100}")
    print("\nThese projects have LAIN items (bundle).")
    print("The HSP fix will CORRECTLY include LAIN in calculations.")
    print("\nBefore fix: HSP = D (missing LAIN) - WRONG!")
    print("After fix:  HSP = D + LAIN - CORRECT!")
    print("\nAction: Verify these projects with:")
    for p in projects_with_lain:
        print(f"  python manage.py verify_hsp_fix --project={p['id']}")
else:
    print(f"\n[OK] NO PROJECTS WITH LAIN!")
    print("All projects are safe. HSP fix has no impact on existing data.")
    print("The fix is purely preventive for future data.")

print(f"\n{'=' * 100}\n")
