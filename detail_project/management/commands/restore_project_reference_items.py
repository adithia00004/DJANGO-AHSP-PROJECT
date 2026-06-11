import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from detail_project.models import (
    DetailAHSPExpanded,
    DetailAHSPProject,
    HargaItemProject,
    Pekerjaan,
)
from detail_project.services import (
    _populate_expanded_from_raw,
    _resolve_ahsp_by_code_in_source,
    _upsert_harga_item,
    cleanup_orphaned_items,
)


class Command(BaseCommand):
    help = (
        "Restore non-custom project details from their AHSP parents and "
        "re-expand custom bundles using system-owned canonical item codes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        project_id = options["project_id"]
        apply_changes = bool(options["apply"])
        jobs = list(
            Pekerjaan.objects.filter(project_id=project_id)
            .select_related("project", "ref")
            .order_by("ordering_index", "id")
        )
        reference_jobs = [
            job
            for job in jobs
            if job.source_type != Pekerjaan.SOURCE_CUSTOM and job.ref_id
        ]
        custom_jobs = [
            job for job in jobs if job.source_type == Pekerjaan.SOURCE_CUSTOM
        ]
        missing_parent = [
            job.id
            for job in jobs
            if job.source_type != Pekerjaan.SOURCE_CUSTOM and not job.ref_id
        ]
        if missing_parent:
            raise CommandError(
                "Non-custom jobs without parent reference: "
                + ", ".join(map(str, missing_parent))
            )

        target_rows = sum(job.ref.rincian.count() for job in reference_jobs)
        current_rows = DetailAHSPProject.objects.filter(
            project_id=project_id,
            pekerjaan__in=reference_jobs,
        ).count()
        self.stdout.write(
            f"project={project_id}: reference_jobs={len(reference_jobs)}, "
            f"custom_jobs={len(custom_jobs)}, current_reference_rows={current_rows}, "
            f"target_reference_rows={target_rows}"
        )
        if not apply_changes:
            self.stdout.write("Dry-run only. Use --apply to persist repairs.")
            return

        backup_path = self._write_backup(project_id)
        with transaction.atomic():
            for job in reference_jobs:
                DetailAHSPExpanded.objects.filter(
                    project_id=project_id,
                    pekerjaan=job,
                ).delete()
                DetailAHSPProject.objects.filter(
                    project_id=project_id,
                    pekerjaan=job,
                ).delete()

                rows = []
                for source in job.ref.rincian.order_by("id"):
                    ref_ahsp = None
                    if source.kategori == "LAIN":
                        ref_ahsp = _resolve_ahsp_by_code_in_source(
                            source.kode_item,
                            job.ref.sumber,
                        )
                    item = _upsert_harga_item(
                        job.project,
                        source.kategori,
                        source.kode_item,
                        source.uraian_item,
                        source.satuan_item,
                    )
                    rows.append(
                        DetailAHSPProject(
                            project=job.project,
                            pekerjaan=job,
                            harga_item=item,
                            kategori=item.kategori,
                            kode=item.kode_item,
                            uraian=item.uraian,
                            satuan=item.satuan,
                            koefisien=source.koefisien,
                            ref_ahsp=ref_ahsp,
                        )
                    )
                DetailAHSPProject.objects.bulk_create(rows)
                _populate_expanded_from_raw(job.project, job)

            for job in custom_jobs:
                _populate_expanded_from_raw(job.project, job)

            cleanup_orphaned_items(jobs[0].project if jobs else project_id)

        self.stdout.write(
            self.style.SUCCESS(
                f"Restored project {project_id}. Backup: {backup_path}"
            )
        )

    @staticmethod
    def _write_backup(project_id):
        backup_dir = Path(settings.MEDIA_ROOT) / "backups" / "detail_project"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        path = backup_dir / (
            f"restore_project_reference_items_{project_id}_{timestamp}.json"
        )
        payload = {
            "project_id": project_id,
            "created_at": timezone.now().isoformat(),
            "harga_items": list(
                HargaItemProject.objects.filter(project_id=project_id)
                .order_by("id")
                .values(
                    "id",
                    "kode_item",
                    "kategori",
                    "uraian",
                    "satuan",
                    "harga_satuan",
                )
            ),
            "raw_details": list(
                DetailAHSPProject.objects.filter(project_id=project_id)
                .order_by("id")
                .values(
                    "id",
                    "pekerjaan_id",
                    "harga_item_id",
                    "kategori",
                    "kode",
                    "uraian",
                    "satuan",
                    "koefisien",
                    "ref_ahsp_id",
                    "ref_pekerjaan_id",
                )
            ),
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
        return path
