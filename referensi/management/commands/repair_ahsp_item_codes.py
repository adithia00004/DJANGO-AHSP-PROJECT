import json
from pathlib import Path
from types import SimpleNamespace

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from referensi.models import KodeItemReferensi, RincianReferensi
from referensi.services.item_code_registry import assign_item_codes, persist_item_codes


PLACEHOLDER_CODES = {"", "-", "–", "—"}


class Command(BaseCommand):
    help = "Replace placeholder item codes in one AHSP source using the item-code registry"

    def add_arguments(self, parser):
        parser.add_argument("--source", default="AHSP 2026")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist changes. Without this flag the command is dry-run only.",
        )

    def handle(self, *args, **options):
        source = options["source"]
        apply_changes = bool(options["apply"])
        source_rows = list(
            RincianReferensi.objects
            .filter(ahsp__sumber=source)
            .select_related("ahsp")
            .order_by("id")
        )
        placeholder_rows = [
            row for row in source_rows if row.kode_item in PLACEHOLDER_CODES
        ]

        registry_map = {
            (obj.kategori, obj.uraian_item, obj.satuan_item): obj.kode_item
            for obj in KodeItemReferensi.objects.all().iterator(chunk_size=1000)
        }
        unique_details = {}
        for row in placeholder_rows:
            key = (row.kategori, row.uraian_item, row.satuan_item)
            unique_details.setdefault(
                key,
                SimpleNamespace(
                    kategori=row.kategori,
                    kategori_source=row.kategori,
                    uraian_item=row.uraian_item,
                    satuan_item=row.satuan_item,
                    kode_item="",
                    kode_item_source="",
                ),
            )

        parse_result = SimpleNamespace(jobs=[SimpleNamespace(rincian=[])])
        stats = SimpleNamespace(generated=0)
        assignment_map = dict(registry_map)
        if unique_details:
            parse_result.jobs[0].rincian = list(unique_details.values())
            stats = assign_item_codes(parse_result)
            assignment_map.update({
                (detail.kategori, detail.uraian_item, detail.satuan_item): detail.kode_item
                for detail in parse_result.jobs[0].rincian
            })

        rows = []
        for row in source_rows:
            target_code = assignment_map.get(
                (row.kategori, row.uraian_item, row.satuan_item)
            )
            if target_code and target_code != row.kode_item:
                rows.append(row)

        reused_rows = sum(
            1
            for row in placeholder_rows
            if (row.kategori, row.uraian_item, row.satuan_item) in registry_map
        )
        generated_rows = len(placeholder_rows) - reused_rows
        alignment_rows = len(rows) - len(placeholder_rows)
        self.stdout.write(
            f"{source}: placeholders={len(placeholder_rows)}, "
            f"unique_placeholder_combinations={len(unique_details)}, "
            f"reused_rows={reused_rows}, generated_rows={generated_rows}, "
            f"generated_combinations={stats.generated}, "
            f"registry_alignment_rows={alignment_rows}, total_updates={len(rows)}"
        )
        if not rows:
            self.stdout.write(self.style.SUCCESS(f"No item-code repairs needed for {source}."))
            return
        if not apply_changes:
            self.stdout.write("Dry-run only. Use --apply to persist repairs.")
            return

        backup_path = self._write_backup(source, rows, assignment_map)
        with transaction.atomic():
            if parse_result.jobs[0].rincian:
                persist_item_codes(parse_result)
            for row in rows:
                row.kode_item = assignment_map[
                    (row.kategori, row.uraian_item, row.satuan_item)
                ]
            RincianReferensi.objects.bulk_update(
                rows,
                ["kode_item"],
                batch_size=500,
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Updated {len(rows)} rows for {source}. Backup: {backup_path}"
            )
        )

    @staticmethod
    def _write_backup(source, rows, assignment_map):
        backup_dir = Path(settings.MEDIA_ROOT) / "backups" / "referensi"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
        safe_source = "".join(ch if ch.isalnum() else "_" for ch in source)
        path = backup_dir / f"repair_item_codes_{safe_source}_{timestamp}.json"
        payload = {
            "source": source,
            "created_at": timezone.now().isoformat(),
            "rows": [
                {
                    "id": row.id,
                    "ahsp_id": row.ahsp_id,
                    "ahsp_kode": row.ahsp.kode_ahsp,
                    "kategori": row.kategori,
                    "old_code": row.kode_item,
                    "new_code": assignment_map[
                        (row.kategori, row.uraian_item, row.satuan_item)
                    ],
                    "uraian": row.uraian_item,
                    "satuan": row.satuan_item,
                    "koefisien": str(row.koefisien),
                }
                for row in rows
            ],
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path
