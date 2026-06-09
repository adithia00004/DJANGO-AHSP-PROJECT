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
)
from referensi.models import KodeItemReferensi


class Command(BaseCommand):
    help = "Align project item codes with KodeItemReferensi by category/description/unit"

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int, required=True)
        parser.add_argument("--apply", action="store_true")

    def handle(self, *args, **options):
        project_id = options["project_id"]
        apply_changes = bool(options["apply"])
        registry = {
            (row.kategori, row.uraian_item, row.satuan_item): row.kode_item
            for row in KodeItemReferensi.objects.all().iterator(chunk_size=1000)
        }
        items = list(
            HargaItemProject.objects
            .filter(project_id=project_id)
            .order_by("id")
        )
        updates = []
        collisions = []
        existing_by_code = {item.kode_item: item for item in items}
        for item in items:
            target = registry.get(
                (item.kategori, item.uraian, item.satuan or "")
            )
            if not target or target == item.kode_item:
                continue
            collision = existing_by_code.get(target)
            if collision and collision.id != item.id:
                collisions.append((item, target, collision))
                continue
            updates.append((item, target))

        self.stdout.write(
            f"project={project_id}: updates={len(updates)}, collisions={len(collisions)}"
        )
        if collisions:
            preview = ", ".join(
                f"{item.kode_item}->{target}"
                for item, target, _collision in collisions[:10]
            )
            raise CommandError(f"Code collisions must be resolved first: {preview}")
        if not updates:
            self.stdout.write(self.style.SUCCESS("No project item-code repairs needed."))
            return
        if not apply_changes:
            self.stdout.write("Dry-run only. Use --apply to persist repairs.")
            return

        backup_path = self._write_backup(project_id, updates)
        with transaction.atomic():
            for item, target in updates:
                DetailAHSPProject.objects.filter(
                    project_id=project_id,
                    harga_item=item,
                ).update(kode=target)
                DetailAHSPExpanded.objects.filter(
                    project_id=project_id,
                    harga_item=item,
                ).update(kode=target)
                item.kode_item = target
                item.save(update_fields=["kode_item", "updated_at"])

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {len(updates)} project items. Backup: {backup_path}"
            )
        )

    @staticmethod
    def _write_backup(project_id, updates):
        backup_dir = Path(settings.MEDIA_ROOT) / "backups" / "detail_project"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        path = backup_dir / f"repair_project_item_codes_{project_id}_{timestamp}.json"
        payload = {
            "project_id": project_id,
            "created_at": timezone.now().isoformat(),
            "items": [
                {
                    "id": item.id,
                    "old_code": item.kode_item,
                    "new_code": target,
                    "kategori": item.kategori,
                    "uraian": item.uraian,
                    "satuan": item.satuan,
                    "harga_satuan": (
                        str(item.harga_satuan)
                        if item.harga_satuan is not None
                        else None
                    ),
                }
                for item, target in updates
            ],
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
