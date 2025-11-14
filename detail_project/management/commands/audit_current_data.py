"""
Management command untuk audit data quality & integrity check.

Checks:
1. Orphaned HargaItemProject (not referenced in DetailAHSPExpanded)
2. Circular dependencies in bundle references
3. Stale expanded data (DetailAHSPExpanded vs DetailAHSPProject mismatch)
4. Empty bundles (should not exist after validation)
5. Max depth violations (>3 levels)
6. Cascade re-expansion integrity

Usage:
    python manage.py audit_current_data --project-id=1
    python manage.py audit_current_data --project-id=1 --detailed
    python manage.py audit_current_data --all-projects
    python manage.py audit_current_data --project-id=1 --output=report.md
"""
from django.core.management.base import BaseCommand
from django.db.models import Count, Q
from django.utils import timezone
from detail_project.models import (
    Pekerjaan, DetailAHSPProject, DetailAHSPExpanded, HargaItemProject
)
from detail_project.monitoring_helpers import log_orphan_detection
from dashboard.models import Project
from collections import defaultdict
from decimal import Decimal
import sys


class Command(BaseCommand):
    help = 'Audit data quality & integrity for AHSP workflow'

    def __init__(self):
        super().__init__()
        self.issues_found = []
        self.warnings_found = []
        self.output_lines = []

    def add_arguments(self, parser):
        parser.add_argument('--project-id', type=int, help='Project ID to audit')
        parser.add_argument('--all-projects', action='store_true', help='Audit all projects')
        parser.add_argument('--detailed', action='store_true', help='Show detailed item list')
        parser.add_argument('--output', type=str, help='Output report to file (markdown format)')

    def handle(self, *args, **options):
        project_id = options.get('project_id')
        all_projects = options.get('all_projects')
        self.detailed = options.get('detailed')
        output_file = options.get('output')

        if not project_id and not all_projects:
            self.print_error('❌ Either --project-id or --all-projects required!')
            self.print_line('Usage:')
            self.print_line('  python manage.py audit_current_data --project-id=1')
            self.print_line('  python manage.py audit_current_data --all-projects')
            return

        # Collect projects to audit
        if all_projects:
            projects = Project.objects.all().order_by('id')
            self.print_header(f"AUDITING ALL PROJECTS ({projects.count()} total)")
        else:
            try:
                projects = [Project.objects.get(id=project_id)]
                self.print_header(f"AUDITING PROJECT {project_id}")
            except Project.DoesNotExist:
                self.print_error(f'❌ Project {project_id} not found!')
                return

        # Run audit for each project
        total_issues = 0
        total_warnings = 0

        for project in projects:
            self.print_line("")
            self.audit_project(project)
            total_issues += len(self.issues_found)
            total_warnings += len(self.warnings_found)

            # Reset for next project
            if all_projects:
                self.issues_found = []
                self.warnings_found = []

        # Summary
        self.print_line("")
        self.print_header("AUDIT SUMMARY")
        if total_issues == 0 and total_warnings == 0:
            self.print_success("✅ No issues found! Data integrity is excellent.")
        else:
            if total_issues > 0:
                self.print_error(f"❌ Critical Issues: {total_issues}")
            if total_warnings > 0:
                self.print_warning(f"⚠️  Warnings: {total_warnings}")

        # Write to file if requested
        if output_file:
            self.write_report(output_file)
            self.print_success(f"\n📄 Report written to: {output_file}")

    def audit_project(self, project):
        """Run all audit checks for a project"""
        self.print_subheader(f"Project {project.id}: {project.nama}")
        self.print_line(f"Created: {project.created_at}")
        self.print_line("")

        # Reset counters
        self.issues_found = []
        self.warnings_found = []

        # Run checks
        self.check_orphaned_items(project)
        self.check_circular_dependencies(project)
        self.check_stale_expanded_data(project)
        self.check_empty_bundles(project)
        self.check_max_depth_violations(project)
        self.check_expansion_integrity(project)

        # Summary for this project
        if not self.issues_found and not self.warnings_found:
            self.print_success("✅ No issues found for this project")
        else:
            self.print_line("\nSummary for this project:")
            if self.issues_found:
                self.print_error(f"  Critical Issues: {len(self.issues_found)}")
            if self.warnings_found:
                self.print_warning(f"  Warnings: {len(self.warnings_found)}")

    def check_orphaned_items(self, project):
        """Check 1: Orphaned HargaItemProject"""
        self.print_line("\n[1] Checking for Orphaned HargaItemProject...")

        # Find items not referenced in DetailAHSPExpanded
        total_items = HargaItemProject.objects.filter(project=project).count()

        # Get all kode_item that are referenced in expanded
        referenced_kode = set(
            DetailAHSPExpanded.objects.filter(project=project)
            .values_list('kode', flat=True)
            .distinct()
        )

        # Find orphaned items
        all_items = HargaItemProject.objects.filter(project=project)
        orphaned = [item for item in all_items if item.kode_item not in referenced_kode]

        orphan_count = len(orphaned)
        orphan_percent = (orphan_count / total_items * 100) if total_items > 0 else 0

        self.print_line(f"  Total HargaItemProject: {total_items}")
        self.print_line(f"  Referenced in expanded: {len(referenced_kode)}")
        self.print_line(f"  Orphaned items: {orphan_count} ({orphan_percent:.1f}%)")

        # Monitoring hook: record orphan detection metrics for observability
        log_orphan_detection(
            project_id=project.id,
            orphan_count=orphan_count,
            total_items=total_items
        )

        if orphan_count > 0:
            self.warnings_found.append({
                'type': 'ORPHANED_ITEMS',
                'count': orphan_count,
                'percent': orphan_percent,
                'items': orphaned
            })
            self.print_warning(f"  ⚠️  Found {orphan_count} orphaned items")

            # Calculate total value
            total_value = sum(
                (item.harga_satuan or Decimal(0)) for item in orphaned
            )
            self.print_line(f"  Total value: Rp {total_value:,.2f}")

            if self.detailed:
                self.print_line("\n  Orphaned Items Detail:")
                for item in orphaned[:10]:  # Show first 10
                    harga = item.harga_satuan or Decimal(0)
                    self.print_line(
                        f"    - {item.kategori:4} | {item.kode_item:15} | "
                        f"Rp {harga:>12,.2f} | {item.uraian[:50]}"
                    )
                if len(orphaned) > 10:
                    self.print_line(f"    ... and {len(orphaned) - 10} more items")
        else:
            self.print_success("  ✅ No orphaned items found")

    def check_circular_dependencies(self, project):
        """Check 2: Circular dependencies in bundle references"""
        self.print_line("\n[2] Checking for Circular Dependencies...")

        # Build dependency graph
        bundles = DetailAHSPProject.objects.filter(
            project=project,
            kategori='LAIN',
            ref_pekerjaan__isnull=False
        ).select_related('pekerjaan', 'ref_pekerjaan')

        # Graph: pekerjaan_id -> list of referenced pekerjaan_id
        graph = defaultdict(list)
        for bundle in bundles:
            graph[bundle.pekerjaan_id].append(bundle.ref_pekerjaan_id)

        self.print_line(f"  Total bundle references: {bundles.count()}")
        self.print_line(f"  Unique source pekerjaan: {len(graph)}")

        # Detect cycles using DFS
        visited = set()
        rec_stack = set()
        cycles = []

        def has_cycle(node, path):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle(neighbor, path.copy()):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True

            rec_stack.remove(node)
            return False

        for node in graph.keys():
            if node not in visited:
                has_cycle(node, [])

        if cycles:
            self.issues_found.append({
                'type': 'CIRCULAR_DEPENDENCY',
                'count': len(cycles),
                'cycles': cycles
            })
            self.print_error(f"  ❌ Found {len(cycles)} circular dependencies!")

            for i, cycle in enumerate(cycles, 1):
                cycle_str = " → ".join(str(x) for x in cycle)
                self.print_line(f"    Cycle {i}: {cycle_str}")

                if self.detailed:
                    # Show pekerjaan details
                    pekerjaan_ids = cycle[:-1]  # Remove duplicate last item
                    pkjs = Pekerjaan.objects.filter(id__in=pekerjaan_ids)
                    for pkj in pkjs:
                        self.print_line(
                            f"      - ID {pkj.id}: {pkj.snapshot_kode} - {pkj.snapshot_uraian[:50]}"
                        )
        else:
            self.print_success("  ✅ No circular dependencies found")

    def check_stale_expanded_data(self, project):
        """Check 3: Stale expanded data (updated_at mismatch)"""
        self.print_line("\n[3] Checking for Stale Expanded Data...")

        pekerjaan_list = Pekerjaan.objects.filter(project=project)
        stale_count = 0
        stale_pekerjaan = []

        for pkj in pekerjaan_list:
            raw_updated = DetailAHSPProject.objects.filter(
                pekerjaan=pkj
            ).order_by('-updated_at').first()

            expanded_updated = DetailAHSPExpanded.objects.filter(
                pekerjaan=pkj
            ).order_by('-updated_at').first()

            if raw_updated and expanded_updated:
                # Check if raw is newer than expanded (allowing 1 second tolerance)
                time_diff = (raw_updated.updated_at - expanded_updated.updated_at).total_seconds()

                if time_diff > 1:  # Raw is significantly newer
                    stale_count += 1
                    stale_pekerjaan.append({
                        'pekerjaan': pkj,
                        'raw_updated': raw_updated.updated_at,
                        'expanded_updated': expanded_updated.updated_at,
                        'diff_seconds': time_diff
                    })

        self.print_line(f"  Total pekerjaan checked: {pekerjaan_list.count()}")
        self.print_line(f"  Stale expanded data: {stale_count}")

        if stale_count > 0:
            self.issues_found.append({
                'type': 'STALE_EXPANDED_DATA',
                'count': stale_count,
                'pekerjaan': stale_pekerjaan
            })
            self.print_error(f"  ❌ Found {stale_count} pekerjaan with stale expanded data!")

            if self.detailed:
                self.print_line("\n  Stale Pekerjaan Detail:")
                for item in stale_pekerjaan[:5]:
                    pkj = item['pekerjaan']
                    self.print_line(
                        f"    - ID {pkj.id}: {pkj.snapshot_kode} - {pkj.snapshot_uraian[:40]}"
                    )
                    self.print_line(f"      Raw updated:      {item['raw_updated']}")
                    self.print_line(f"      Expanded updated: {item['expanded_updated']}")
                    self.print_line(f"      Diff: {item['diff_seconds']:.0f} seconds")
                if len(stale_pekerjaan) > 5:
                    self.print_line(f"    ... and {len(stale_pekerjaan) - 5} more pekerjaan")
        else:
            self.print_success("  ✅ No stale expanded data found")

    def check_empty_bundles(self, project):
        """Check 4: Empty bundles (should not exist after validation)"""
        self.print_line("\n[4] Checking for Empty Bundles...")

        # Find LAIN items that reference pekerjaan with no details
        bundles = DetailAHSPProject.objects.filter(
            project=project,
            kategori='LAIN',
            ref_pekerjaan__isnull=False
        ).select_related('pekerjaan', 'ref_pekerjaan')

        empty_bundles = []
        for bundle in bundles:
            target_details = DetailAHSPExpanded.objects.filter(
                pekerjaan=bundle.ref_pekerjaan
            ).count()

            if target_details == 0:
                empty_bundles.append({
                    'bundle': bundle,
                    'source_pekerjaan': bundle.pekerjaan,
                    'target_pekerjaan': bundle.ref_pekerjaan
                })

        self.print_line(f"  Total bundles checked: {bundles.count()}")
        self.print_line(f"  Empty bundles: {len(empty_bundles)}")

        if empty_bundles:
            self.issues_found.append({
                'type': 'EMPTY_BUNDLES',
                'count': len(empty_bundles),
                'bundles': empty_bundles
            })
            self.print_error(f"  ❌ Found {len(empty_bundles)} empty bundles!")

            if self.detailed:
                self.print_line("\n  Empty Bundle Detail:")
                for item in empty_bundles[:5]:
                    bundle = item['bundle']
                    source = item['source_pekerjaan']
                    target = item['target_pekerjaan']
                    self.print_line(
                        f"    - Bundle: {bundle.kode} in Pekerjaan {source.id} ({source.snapshot_kode})"
                    )
                    self.print_line(
                        f"      → Target: Pekerjaan {target.id} ({target.snapshot_kode}) [EMPTY]"
                    )
                if len(empty_bundles) > 5:
                    self.print_line(f"    ... and {len(empty_bundles) - 5} more empty bundles")
        else:
            self.print_success("  ✅ No empty bundles found")

    def check_max_depth_violations(self, project):
        """Check 5: Max depth violations (>3 levels)"""
        self.print_line("\n[5] Checking for Max Depth Violations...")

        max_depth = 3
        violations = DetailAHSPExpanded.objects.filter(
            project=project,
            expansion_depth__gt=max_depth
        )

        violation_count = violations.count()
        self.print_line(f"  Max allowed depth: {max_depth}")
        self.print_line(f"  Violations found: {violation_count}")

        if violation_count > 0:
            self.issues_found.append({
                'type': 'MAX_DEPTH_VIOLATION',
                'count': violation_count,
                'max_depth': max_depth
            })
            self.print_error(f"  ❌ Found {violation_count} items exceeding max depth!")

            if self.detailed:
                self.print_line("\n  Violation Detail:")
                for item in violations[:5]:
                    self.print_line(
                        f"    - Pekerjaan {item.pekerjaan_id} | "
                        f"Depth {item.expansion_depth} | "
                        f"{item.kode} - {item.uraian[:40]}"
                    )
                    if item.source_bundle_kode:
                        self.print_line(f"      From bundle: {item.source_bundle_kode}")
                if violation_count > 5:
                    self.print_line(f"    ... and {violation_count - 5} more violations")
        else:
            self.print_success("  ✅ No max depth violations found")

    def check_expansion_integrity(self, project):
        """Check 6: Expansion integrity (DetailAHSPProject vs DetailAHSPExpanded count)"""
        self.print_line("\n[6] Checking Expansion Integrity...")

        pekerjaan_list = Pekerjaan.objects.filter(project=project)
        issues = []

        for pkj in pekerjaan_list:
            raw_count = DetailAHSPProject.objects.filter(pekerjaan=pkj).count()
            expanded_count = DetailAHSPExpanded.objects.filter(pekerjaan=pkj).count()

            # Problem: raw > 0 but expanded = 0
            if raw_count > 0 and expanded_count == 0:
                issues.append({
                    'pekerjaan': pkj,
                    'raw_count': raw_count,
                    'expanded_count': expanded_count,
                    'issue': 'NO_EXPANSION'
                })

        self.print_line(f"  Total pekerjaan checked: {pekerjaan_list.count()}")
        self.print_line(f"  Expansion issues: {len(issues)}")

        if issues:
            self.issues_found.append({
                'type': 'EXPANSION_INTEGRITY',
                'count': len(issues),
                'issues': issues
            })
            self.print_error(f"  ❌ Found {len(issues)} pekerjaan with expansion issues!")

            if self.detailed:
                self.print_line("\n  Issue Detail:")
                for item in issues[:5]:
                    pkj = item['pekerjaan']
                    self.print_line(
                        f"    - Pekerjaan {pkj.id}: {pkj.snapshot_kode} - {pkj.snapshot_uraian[:40]}"
                    )
                    self.print_line(f"      Raw count: {item['raw_count']}")
                    self.print_line(f"      Expanded count: {item['expanded_count']}")
                    self.print_line(f"      Issue: {item['issue']}")
                if len(issues) > 5:
                    self.print_line(f"    ... and {len(issues) - 5} more issues")
        else:
            self.print_success("  ✅ Expansion integrity is good")

    # Helper methods for styled output
    def print_header(self, text):
        """Print header with styling"""
        line = "=" * 80
        self.print_line(line, emit=False)
        self.print_line(text, emit=False)
        self.print_line(line, emit=False)
        self.stdout.write(self.style.HTTP_INFO(line))
        self.stdout.write(self.style.HTTP_INFO(text))
        self.stdout.write(self.style.HTTP_INFO(line))

    def print_subheader(self, text):
        """Print subheader with styling"""
        line = "-" * 80
        self.print_line(line, emit=False)
        self.print_line(text, emit=False)
        self.print_line(line, emit=False)
        self.stdout.write(self.style.HTTP_INFO(line))
        self.stdout.write(self.style.HTTP_INFO(text))
        self.stdout.write(self.style.HTTP_INFO(line))

    def print_success(self, text):
        """Print success message"""
        self.print_line(text, emit=False)
        self.stdout.write(self.style.SUCCESS(text))

    def print_warning(self, text):
        """Print warning message"""
        self.print_line(text, emit=False)
        self.stdout.write(self.style.WARNING(text))

    def print_error(self, text):
        """Print error message"""
        self.print_line(text, emit=False)
        self.stdout.write(self.style.ERROR(text))

    def print_line(self, text="", *, emit=True):
        """Print regular line and store for report"""
        self.output_lines.append(text)
        if emit:
            self.stdout.write(text)

    def write_report(self, filepath):
        """Write audit report to markdown file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# AHSP Data Audit Report\n\n")
            f.write(f"**Generated:** {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("---\n\n")

            for line in self.output_lines:
                # Convert terminal styling to markdown
                line = line.replace("❌", "🔴")
                line = line.replace("⚠️", "⚠️")
                line = line.replace("✅", "✅")
                f.write(line + "\n")
