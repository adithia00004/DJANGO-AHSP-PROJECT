from django.core.management.base import BaseCommand
from django.db import transaction

from detail_project.models import DetailAHSPExpanded, DetailAHSPProject


class Command(BaseCommand):
    help = "Align Detail AHSP item metadata with canonical HargaItemProject values"

    def add_arguments(self, parser):
        parser.add_argument("--project-id", type=int)
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist repairs. Without this flag the command is dry-run only.",
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        apply_changes = bool(options.get("apply"))

        raw_qs = DetailAHSPProject.objects.select_related("harga_item").order_by("id")
        expanded_qs = DetailAHSPExpanded.objects.select_related("harga_item").order_by("id")
        if project_id:
            raw_qs = raw_qs.filter(project_id=project_id)
            expanded_qs = expanded_qs.filter(project_id=project_id)

        raw_updates = self._collect_updates(raw_qs)
        expanded_updates = self._collect_updates(expanded_qs)

        self.stdout.write(
            f"Detected metadata drift: raw={len(raw_updates)}, "
            f"expanded={len(expanded_updates)}"
        )
        if not apply_changes:
            self.stdout.write("Dry-run only. Use --apply to persist repairs.")
            return

        with transaction.atomic():
            if raw_updates:
                DetailAHSPProject.objects.bulk_update(
                    raw_updates,
                    ["kategori", "kode", "uraian", "satuan"],
                    batch_size=500,
                )
            if expanded_updates:
                DetailAHSPExpanded.objects.bulk_update(
                    expanded_updates,
                    ["kategori", "kode", "uraian", "satuan"],
                    batch_size=500,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Repaired metadata: raw={len(raw_updates)}, "
                f"expanded={len(expanded_updates)}"
            )
        )

    @staticmethod
    def _collect_updates(queryset):
        updates = []
        for detail in queryset.iterator(chunk_size=500):
            item = detail.harga_item
            canonical = (item.kategori, item.kode_item, item.uraian, item.satuan)
            current = (detail.kategori, detail.kode, detail.uraian, detail.satuan)
            if current == canonical:
                continue
            detail.kategori = item.kategori
            detail.kode = item.kode_item
            detail.uraian = item.uraian
            detail.satuan = item.satuan
            updates.append(detail)
        return updates
