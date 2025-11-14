from django.core.management.base import BaseCommand
from django.utils import timezone
from dashboard.models import Project

from detail_project.services import validate_project_data


class Command(BaseCommand):
    help = "Validate AHSP data integrity per project"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            help="Project ID to validate",
        )
        parser.add_argument(
            "--all-projects",
            action="store_true",
            help="Validate all active projects",
        )
        parser.add_argument(
            "--orphan-threshold",
            type=int,
            default=0,
            help="Maximum allowed orphan count before marking issue",
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Optional path to write JSON report",
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        all_projects = options.get("all_projects")
        orphan_threshold = options.get("orphan_threshold") or 0
        output_path = options.get("output")

        if not project_id and not all_projects:
            self.stderr.write(
                self.style.ERROR("Gunakan --project-id atau --all-projects")
            )
            return
        if project_id and all_projects:
            self.stderr.write(
                self.style.ERROR("Gunakan salah satu: --project-id atau --all-projects")
            )
            return

        if all_projects:
            projects = Project.objects.filter(is_active=True).order_by("id")
        else:
            try:
                projects = [Project.objects.get(id=project_id)]
            except Project.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f"Project {project_id} tidak ditemukan")
                )
                return

        results = []
        for project in projects:
            self.stdout.write(
                self.style.HTTP_INFO(f"Validating project #{project.id} {project.nama}")
            )
            report = validate_project_data(
                project, orphan_threshold=orphan_threshold
            )
            results.append(report)

            if report["passed"]:
                self.stdout.write(self.style.SUCCESS("  ✓ Passed"))
            else:
                self.stdout.write(self.style.WARNING("  ⚠ Issues detected"))
                if report["invalid_bundles"]:
                    self.stdout.write(
                        f"    - Invalid bundles: {len(report['invalid_bundles'])}"
                    )
                if report["circular_dependencies"]:
                    self.stdout.write(
                        f"    - Circular dependencies: {len(report['circular_dependencies'])}"
                    )
                if report["expansion_issues"]:
                    self.stdout.write(
                        f"    - Expansion issues: {len(report['expansion_issues'])}"
                    )
                if report["orphan_threshold_exceeded"]:
                    self.stdout.write(
                        f"    - Orphan count {report['orphan_count']} exceeds threshold {orphan_threshold}"
                    )

        if output_path:
            import json

            data = {
                "generated_at": timezone.now().isoformat(),
                "projects": results,
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            self.stdout.write(
                self.style.SUCCESS(f"Report written to {output_path}")
            )
