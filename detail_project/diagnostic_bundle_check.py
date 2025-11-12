"""
Diagnostic script untuk mengecek bundle items di Rincian AHSP

Usage:
    python manage.py shell < detail_project/diagnostic_bundle_check.py

Atau di Django shell:
    exec(open('detail_project/diagnostic_bundle_check.py').read())
"""

def diagnose_bundle_issue(project_id, pekerjaan_id=None):
    """
    Diagnose bundle items issue untuk project tertentu

    Args:
        project_id: ID project yang akan di-check
        pekerjaan_id: (Optional) ID pekerjaan spesifik untuk di-check
    """
    from detail_project.models import (
        Project, Pekerjaan, DetailAHSPProject, DetailAHSPExpanded,
        HargaItemProject
    )
    from decimal import Decimal

    print("=" * 80)
    print("BUNDLE ITEMS DIAGNOSTIC")
    print("=" * 80)

    try:
        project = Project.objects.get(id=project_id)
        print(f"\n✓ Project: {project.nama} (ID: {project.id})")
    except Project.DoesNotExist:
        print(f"\n✗ ERROR: Project dengan ID {project_id} tidak ditemukan!")
        return

    # Filter pekerjaan
    if pekerjaan_id:
        pekerjaan_qs = Pekerjaan.objects.filter(project=project, id=pekerjaan_id)
    else:
        pekerjaan_qs = Pekerjaan.objects.filter(project=project)

    print(f"\n{'─' * 80}")
    print(f"CHECKING {pekerjaan_qs.count()} PEKERJAAN...")
    print(f"{'─' * 80}")

    for pkj in pekerjaan_qs:
        print(f"\n📦 Pekerjaan: {pkj.snapshot_kode} - {pkj.snapshot_uraian}")
        print(f"   ID: {pkj.id}")
        print(f"   Source Type: {pkj.source_type}")

        # Check DetailAHSPProject (raw storage)
        raw_details = DetailAHSPProject.objects.filter(
            project=project, pekerjaan=pkj
        )
        print(f"\n   🗂️  DetailAHSPProject (raw): {raw_details.count()} rows")

        bundle_count = 0
        for detail in raw_details:
            if detail.kategori == 'LAIN' and detail.ref_pekerjaan_id:
                bundle_count += 1
                print(f"      ├─ Bundle: {detail.kode} → ref_pekerjaan_id={detail.ref_pekerjaan_id}")

        if bundle_count > 0:
            print(f"      └─ Found {bundle_count} bundle item(s)")

        # Check DetailAHSPExpanded (expanded storage)
        expanded_details = DetailAHSPExpanded.objects.filter(
            project=project, pekerjaan=pkj
        ).select_related('harga_item')

        print(f"\n   📊 DetailAHSPExpanded (expanded): {expanded_details.count()} rows")

        if expanded_details.exists():
            # Aggregate by kategori
            from django.db.models import Sum, F, DecimalField, ExpressionWrapper

            agg = expanded_details.values('kategori').annotate(
                count=Sum(1),
                total_nilai=Sum(
                    ExpressionWrapper(
                        F('koefisien') * F('harga_item__harga_satuan'),
                        output_field=DecimalField(max_digits=20, decimal_places=2)
                    )
                )
            )

            total_E = Decimal('0')
            for row in agg:
                kat = row['kategori']
                count = row['count'] or 0
                nilai = row['total_nilai'] or Decimal('0')

                icon = {'TK': '👷', 'BHN': '🧱', 'ALT': '🔧', 'LAIN': '📦'}.get(kat, '❓')
                print(f"      ├─ {icon} {kat}: {count} items → Rp {nilai:,.2f}")

                if kat in ['TK', 'BHN', 'ALT']:
                    total_E += nilai

            print(f"      └─ TOTAL (A+B+C): Rp {total_E:,.2f}")

            # Check for items with zero harga
            zero_harga = expanded_details.filter(harga_item__harga_satuan=0)
            if zero_harga.exists():
                print(f"\n   ⚠️  WARNING: {zero_harga.count()} item(s) dengan harga 0!")
                for item in zero_harga[:5]:  # Show max 5
                    print(f"      ├─ {item.kategori}: {item.kode} - {item.uraian} (koef={item.koefisien})")

                if zero_harga.count() > 5:
                    print(f"      └─ ... dan {zero_harga.count() - 5} items lagi")

            # Check for items with null harga_item
            null_harga = expanded_details.filter(harga_item__isnull=True)
            if null_harga.exists():
                print(f"\n   ⚠️  WARNING: {null_harga.exists()} item(s) tanpa harga_item reference!")

        else:
            print(f"      └─ ⚠️  No expanded items found!")
            if bundle_count > 0:
                print(f"         → Bundle items exist in raw storage but NOT expanded!")
                print(f"         → This is likely the bug - bundle not expanded to DetailAHSPExpanded")

    print(f"\n{'=' * 80}")
    print("DIAGNOSTIC COMPLETE")
    print(f"{'=' * 80}\n")


# Example usage:
# diagnose_bundle_issue(project_id=1)
# diagnose_bundle_issue(project_id=1, pekerjaan_id=123)

print("""
To use this diagnostic:

    from detail_project.diagnostic_bundle_check import diagnose_bundle_issue

    # Check all pekerjaan in project
    diagnose_bundle_issue(project_id=YOUR_PROJECT_ID)

    # Check specific pekerjaan
    diagnose_bundle_issue(project_id=YOUR_PROJECT_ID, pekerjaan_id=YOUR_PEKERJAAN_ID)
""")
