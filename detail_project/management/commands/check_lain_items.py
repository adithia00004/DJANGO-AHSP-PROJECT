# -*- coding: utf-8 -*-
"""
Django management command untuk mengecek project dengan LAIN items

Usage:
    python manage.py check_lain_items
"""

from django.core.management.base import BaseCommand
from dashboard.models import Project
from detail_project.services import compute_rekap_for_project


class Command(BaseCommand):
    help = 'Check all projects for LAIN items (bundle)'

    def handle(self, *args, **options):
        self.stdout.write("=" * 100)
        self.stdout.write("CHECKING ALL PROJECTS FOR LAIN ITEMS")
        self.stdout.write("=" * 100)

        all_projects = Project.objects.all().order_by('id')
        total_projects = all_projects.count()

        self.stdout.write(f"\nTotal projects: {total_projects}\n")
        self.stdout.write("-" * 100 + "\n")

        projects_with_lain = []
        projects_without_lain = []
        projects_error = []

        for project in all_projects:
            project_name = project.nama[:50] if len(project.nama) > 50 else project.nama

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
                    self.stdout.write(
                        f"Project #{project.id:3d}: {project_name:50s} "
                        + self.style.WARNING(f"[WARN] Has LAIN: Rp {total_lain:,.2f}")
                    )
                else:
                    projects_without_lain.append(project.id)
                    self.stdout.write(
                        f"Project #{project.id:3d}: {project_name:50s} "
                        + self.style.SUCCESS("[OK] No LAIN")
                    )

            except Exception as e:
                projects_error.append({'id': project.id, 'nama': project.nama, 'error': str(e)})
                self.stdout.write(
                    f"Project #{project.id:3d}: {project_name:50s} "
                    + self.style.ERROR(f"[ERROR] {str(e)[:30]}")
                )

        # Summary
        self.stdout.write("\n" + "=" * 100)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 100)

        self.stdout.write(f"\nTotal projects checked: {total_projects}")
        self.stdout.write(self.style.SUCCESS(f"Projects WITHOUT LAIN (safe): {len(projects_without_lain)}"))
        self.stdout.write(self.style.WARNING(f"Projects WITH LAIN (affected by fix): {len(projects_with_lain)}"))
        if projects_error:
            self.stdout.write(self.style.ERROR(f"Projects with ERRORS: {len(projects_error)}"))

        # Details for projects with LAIN
        if projects_with_lain:
            self.stdout.write("\n" + "-" * 100)
            self.stdout.write(self.style.WARNING("PROJECTS WITH LAIN ITEMS (AFFECTED BY FIX):"))
            self.stdout.write("-" * 100)

            for p in projects_with_lain:
                self.stdout.write(f"\nProject #{p['id']}: {p['nama']}")
                self.stdout.write(f"   Total LAIN: Rp {p['total_lain']:,.2f}")
                self.stdout.write(f"   Pekerjaan with LAIN:")

                for pkj in p['pekerjaan']:
                    self.stdout.write(f"      - {pkj['kode']}: {pkj['uraian']}")
                    self.stdout.write(f"        LAIN = Rp {pkj['lain']:,.2f}")

            self.stdout.write("\n" + "-" * 100)
            self.stdout.write("RECOMMENDATION:")
            self.stdout.write("-" * 100)
            self.stdout.write("\nThese projects have LAIN items (bundle).")
            self.stdout.write("The HSP fix will CORRECTLY include LAIN in calculations.")
            self.stdout.write("\nBefore fix: HSP = D (missing LAIN) - WRONG!")
            self.stdout.write("After fix:  HSP = D + LAIN - CORRECT!")
            self.stdout.write("\nAction: Verify these projects with:")
            for p in projects_with_lain:
                self.stdout.write(f"  python manage.py verify_hsp_fix --project={p['id']}")
        else:
            self.stdout.write("\n" + self.style.SUCCESS("=" * 100))
            self.stdout.write(self.style.SUCCESS("NO PROJECTS WITH LAIN ITEMS!"))
            self.stdout.write(self.style.SUCCESS("=" * 100))
            self.stdout.write("\nAll projects are safe. HSP fix has no impact on existing data.")
            self.stdout.write("The fix is purely preventive for future data with bundle items.")

        self.stdout.write("\n" + "=" * 100 + "\n")
