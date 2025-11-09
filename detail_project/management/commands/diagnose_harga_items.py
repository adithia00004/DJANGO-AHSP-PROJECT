"""
Management command untuk diagnose kenapa Harga Items kosong.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from detail_project.models import Pekerjaan, DetailAHSPProject, DetailAHSPExpanded, HargaItemProject


class Command(BaseCommand):
    help = 'Diagnose kenapa Harga Items page kosong untuk pekerjaan tertentu'

    def add_arguments(self, parser):
        parser.add_argument('--project-id', type=int, help='Project ID untuk di-check')
        parser.add_argument('--pekerjaan-id', type=int, help='Pekerjaan ID spesifik')
        parser.add_argument('--all', action='store_true', help='Check semua pekerjaan dalam project')

    def handle(self, *args, **options):
        project_id = options.get('project_id')
        pekerjaan_id = options.get('pekerjaan_id')
        check_all = options.get('all')

        if not project_id:
            self.stdout.write(self.style.ERROR('❌ --project-id required!'))
            self.stdout.write('Usage: python manage.py diagnose_harga_items --project-id=1')
            return

        if pekerjaan_id:
            # Check specific pekerjaan
            try:
                pkj = Pekerjaan.objects.get(id=pekerjaan_id, project_id=project_id)
                self.diagnose_pekerjaan(pkj)
            except Pekerjaan.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ Pekerjaan {pekerjaan_id} not found in project {project_id}'))
        else:
            # List all pekerjaan and their status
            pekerjaan_list = Pekerjaan.objects.filter(project_id=project_id).order_by('id')

            if not pekerjaan_list.exists():
                self.stdout.write(self.style.WARNING(f'⚠️  No pekerjaan found in project {project_id}'))
                return

            self.stdout.write(f"\n{'='*80}")
            self.stdout.write(f"PROJECT {project_id} - PEKERJAAN LIST")
            self.stdout.write(f"{'='*80}")
            self.stdout.write(f"{'ID':<6} {'Kode':<20} {'Source':<15} {'Storage1':<10} {'Storage2':<10} {'Status'}")
            self.stdout.write(f"{'-'*80}")

            for pkj in pekerjaan_list:
                raw_count = DetailAHSPProject.objects.filter(pekerjaan=pkj).count()
                expanded_count = DetailAHSPExpanded.objects.filter(pekerjaan=pkj).count()

                if raw_count > 0 and expanded_count == 0:
                    status = self.style.ERROR('❌ PROBLEM!')
                elif raw_count == 0:
                    status = self.style.WARNING('⚠️  No data')
                else:
                    status = self.style.SUCCESS('✅ OK')

                self.stdout.write(
                    f"{pkj.id:<6} {(pkj.snapshot_kode or 'N/A'):<20} "
                    f"{pkj.source_type:<15} {raw_count:<10} {expanded_count:<10} {status}"
                )

            self.stdout.write(f"{'-'*80}")
            self.stdout.write("\nTo diagnose specific pekerjaan:")
            self.stdout.write(f"  python manage.py diagnose_harga_items --project-id={project_id} --pekerjaan-id=<ID>")
            self.stdout.write("")

            if check_all:
                self.stdout.write(f"\n{'='*80}")
                self.stdout.write("DETAILED DIAGNOSIS FOR PROBLEM CASES")
                self.stdout.write(f"{'='*80}\n")

                for pkj in pekerjaan_list:
                    raw_count = DetailAHSPProject.objects.filter(pekerjaan=pkj).count()
                    expanded_count = DetailAHSPExpanded.objects.filter(pekerjaan=pkj).count()

                    if raw_count > 0 and expanded_count == 0:
                        self.diagnose_pekerjaan(pkj)
                        self.stdout.write("")

    def diagnose_pekerjaan(self, pkj):
        """Detailed diagnosis untuk satu pekerjaan"""
        project = pkj.project

        self.stdout.write(self.style.HTTP_INFO(f"\n{'='*80}"))
        self.stdout.write(self.style.HTTP_INFO(f"DIAGNOSIS: Pekerjaan {pkj.id} - {pkj.snapshot_kode}"))
        self.stdout.write(self.style.HTTP_INFO(f"{'='*80}"))
        self.stdout.write(f"Project ID:   {project.id}")
        self.stdout.write(f"Source Type:  {pkj.source_type}")
        self.stdout.write(f"Created:      {pkj.created_at}")
        self.stdout.write(f"Updated:      {pkj.updated_at}")
        self.stdout.write("")

        # Storage 1 check
        raw_items = DetailAHSPProject.objects.filter(pekerjaan=pkj)
        self.stdout.write(f"[1] Storage 1 (DetailAHSPProject): {raw_items.count()} rows")

        if raw_items.exists():
            for item in raw_items[:5]:  # Show first 5
                self.stdout.write(f"    - {item.kategori:4} | {item.kode:15} | koef={str(item.koefisien):10} | {item.uraian[:40]}")
                if item.kategori == 'LAIN':
                    self.stdout.write(f"      ref_ahsp_id: {item.ref_ahsp_id}")
                    self.stdout.write(f"      ref_pekerjaan_id: {item.ref_pekerjaan_id}")
            if raw_items.count() > 5:
                self.stdout.write(f"    ... and {raw_items.count() - 5} more rows")
        else:
            self.stdout.write(self.style.WARNING("    ⚠️  EMPTY! Pekerjaan has no details!"))

        # Storage 2 check
        expanded_items = DetailAHSPExpanded.objects.filter(pekerjaan=pkj)
        self.stdout.write(f"\n[2] Storage 2 (DetailAHSPExpanded): {expanded_items.count()} rows")

        if expanded_items.exists():
            for item in expanded_items[:5]:  # Show first 5
                bundle_info = f" [from: {item.source_bundle_kode}]" if item.source_bundle_kode else ""
                self.stdout.write(
                    f"    - {item.kategori:4} | {item.kode:15} | koef={str(item.koefisien):10} | "
                    f"depth={item.expansion_depth}{bundle_info}"
                )
            if expanded_items.count() > 5:
                self.stdout.write(f"    ... and {expanded_items.count() - 5} more rows")
        else:
            self.stdout.write(self.style.ERROR("    ❌ EMPTY! This is why Harga Items is empty!"))

        # HargaItemProject check
        hip_total = HargaItemProject.objects.filter(project=project).count()
        hip_linked = HargaItemProject.objects.filter(
            project=project,
            expanded_refs__project=project
        ).distinct().count()

        self.stdout.write(f"\n[3] HargaItemProject:")
        self.stdout.write(f"    Total in project:     {hip_total} items")
        self.stdout.write(f"    Linked to expanded:   {hip_linked} items")

        # Root cause analysis
        self.stdout.write(f"\n{self.style.HTTP_INFO('='*80)}")
        self.stdout.write(self.style.HTTP_INFO("ROOT CAUSE ANALYSIS:"))
        self.stdout.write(self.style.HTTP_INFO('='*80))

        if raw_items.count() == 0:
            self.stdout.write(self.style.ERROR("❌ CRITICAL: No raw data!"))
            self.stdout.write("   Pekerjaan has no details at all.")
            self.stdout.write("   → User never added any items to this pekerjaan.")

        elif expanded_items.count() == 0:
            self.stdout.write(self.style.ERROR("❌ ROOT CAUSE: Storage 2 (DetailAHSPExpanded) is EMPTY!"))
            self.stdout.write("")

            # Determine specific cause
            causes_found = []

            # Check 1: Old data
            # Commit 54d123c approximate date (adjust based on actual git log)
            import datetime
            from django.utils.timezone import make_aware

            # Get commit date from git (if available)
            try:
                import subprocess
                result = subprocess.run(
                    ['git', 'show', '-s', '--format=%ci', '54d123c'],
                    capture_output=True,
                    text=True,
                    cwd='/home/user/DJANGO-AHSP-PROJECT'
                )
                if result.returncode == 0:
                    commit_date_str = result.stdout.strip().split()[0]
                    commit_date = datetime.datetime.strptime(commit_date_str, '%Y-%m-%d')
                    commit_date = make_aware(commit_date)
                else:
                    # Fallback date
                    commit_date = make_aware(datetime.datetime(2025, 11, 8))
            except:
                commit_date = make_aware(datetime.datetime(2025, 11, 8))

            if pkj.created_at < commit_date:
                causes_found.append('OLD_DATA')
                self.stdout.write(self.style.WARNING("⚠️  CAUSE 1: Old Data"))
                self.stdout.write(f"   Pekerjaan created: {pkj.created_at}")
                self.stdout.write(f"   Dual storage fix:  {commit_date} (commit 54d123c)")
                self.stdout.write("   → Pekerjaan created BEFORE dual storage was implemented!")
                self.stdout.write("")
                self.stdout.write(self.style.SUCCESS("   SOLUTION:"))
                self.stdout.write("   1. Delete this pekerjaan from UI")
                self.stdout.write("   2. Re-add from AHSP Referensi (will use new code)")
                self.stdout.write("   OR")
                self.stdout.write(f"   Run: python manage.py migrate_dual_storage --project-id={project.id} --fix")
                self.stdout.write("")

            # Check 2: LAIN with AHSP reference
            lain_items = raw_items.filter(kategori='LAIN')
            for lain in lain_items:
                if lain.ref_ahsp_id and not lain.ref_pekerjaan_id:
                    causes_found.append('AHSP_BUNDLE')
                    self.stdout.write(self.style.WARNING("⚠️  CAUSE 2: AHSP Bundle (Not Supported)"))
                    self.stdout.write(f"   LAIN item: '{lain.kode}' - {lain.uraian}")
                    self.stdout.write(f"   ref_ahsp_id: {lain.ref_ahsp_id} (AHSP Referensi)")
                    self.stdout.write(f"   ref_pekerjaan_id: {lain.ref_pekerjaan_id} (NULL)")
                    self.stdout.write("   → User selected from 'Master AHSP' instead of 'Pekerjaan Proyek'!")
                    self.stdout.write("")
                    self.stdout.write(self.style.SUCCESS("   SOLUTION:"))
                    self.stdout.write("   1. Edit this pekerjaan")
                    self.stdout.write("   2. For LAIN items, select from 'Pekerjaan Proyek' dropdown")
                    self.stdout.write("   3. NOT from 'Master AHSP' autocomplete")
                    self.stdout.write("")
                    self.stdout.write("   CODE FIX (to prevent this):")
                    self.stdout.write("   → Add frontend validation in template_ahsp.js")
                    self.stdout.write("   → Reject AHSP selection for CUSTOM bundles")
                    self.stdout.write("")

            # Check 3: Code bug (if not old data and no AHSP issue)
            if not causes_found:
                self.stdout.write(self.style.ERROR("⚠️  CAUSE 3: Possible Code Bug"))
                self.stdout.write("   Storage 1 has data but Storage 2 is empty")
                self.stdout.write("   This shouldn't happen with current code!")
                self.stdout.write("")
                self.stdout.write(self.style.SUCCESS("   DEBUG STEPS:"))
                self.stdout.write("   1. Check Django logs for [POPULATE_EXPANDED] messages")
                self.stdout.write("   2. Verify _populate_expanded_from_raw() was called")
                self.stdout.write("   3. Check for errors during expansion")
                self.stdout.write("")

        else:
            self.stdout.write(self.style.SUCCESS("✅ Storage 2 has data!"))
            if hip_linked == 0:
                self.stdout.write(self.style.ERROR("❌ But HargaItemProject link is broken!"))
                self.stdout.write("   → Check FK relationships")
            else:
                self.stdout.write(self.style.SUCCESS("✅ Everything looks OK!"))
                self.stdout.write("   If Harga Items still empty, check:")
                self.stdout.write("   1. Browser console for JS errors")
                self.stdout.write("   2. API response: /api/project/{id}/harga-items/list/")

        self.stdout.write(f"{self.style.HTTP_INFO('='*80)}\n")
