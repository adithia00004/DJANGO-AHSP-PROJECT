"""Fase 4b (SYN-05): bersihkan flag "detail perlu dimuat ulang" warisan.

Sebelum perbaikan SYN-01, `api_upsert_list_pekerjaan` menandai SETIAP pekerjaan
yang hadir di payload sebagai `pending_reload_job_ids`. Karena halaman List
Pekerjaan selalu mengirim pohon penuh, satu save biasa menandai seluruh proyek.

Perbaikan SYN-01 hanya menghentikan flag BARU. Flag yang telanjur tersimpan di
`ProjectChangeStatus` tidak ikut bersih -- ia hanya susut satu per satu saat user
membuka tiap pekerjaan di Template AHSP. Selama belum bersih:

  * Template AHSP terus menampilkan banner "N pekerjaan memiliki perubahan
    sumber ..." meski tidak ada yang berubah;
  * Harga Items terus mengunci input harga (`harga_items.js` -> updateSyncLockState);
  * response save yang bersih pun tetap membawa set kumulatif itu (SYN-07).

Command ini menutup celah tersebut satu kali, per-proyek atau seluruhnya.

Contoh:
    python manage.py clear_stale_reload_flags --all --dry-run
    python manage.py clear_stale_reload_flags --project-id 198 --yes
    python manage.py clear_stale_reload_flags --all --yes

Dokumen: `Review/R5_Detail_Project/36_Cross_Page_Sync_Over_Notification_Audit_Plan_20260824.md`
"""

from django.core.management.base import BaseCommand, CommandError

from dashboard.models import Project
from detail_project.models import Pekerjaan, ProjectChangeStatus


class Command(BaseCommand):
    help = (
        "Kosongkan pending_reload_job_ids (dan opsional pending_volume_reset_job_ids) "
        "warisan over-flag SYN-01. Jalankan --dry-run lebih dulu."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--project-id",
            type=int,
            help="Bersihkan satu project saja. Tanpa ini wajib pakai --all.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Bersihkan seluruh project yang punya flag menggantung.",
        )
        parser.add_argument(
            "--include-volume",
            action="store_true",
            help=(
                "Ikut kosongkan pending_volume_reset_job_ids. TIDAK default: flag "
                "volume menandai volume yang benar-benar di-reset dan masih perlu "
                "diisi ulang user, jadi menghapusnya bisa menyembunyikan pekerjaan "
                "yang volumenya kosong."
            ),
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Tampilkan dampaknya tanpa menulis ke database.",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Jalankan tanpa konfirmasi interaktif.",
        )

    def handle(self, *args, **options):
        project_id = options.get("project_id")
        do_all = bool(options.get("all"))
        include_volume = bool(options.get("include_volume"))
        dry_run = bool(options.get("dry_run"))
        skip_confirm = bool(options.get("yes"))

        if not project_id and not do_all:
            raise CommandError("Tentukan --project-id <id> atau --all.")
        if project_id and do_all:
            raise CommandError("--project-id dan --all tidak bisa dipakai bersamaan.")

        queryset = ProjectChangeStatus.objects.exclude(pending_reload_job_ids=[])
        if project_id:
            if not Project.objects.filter(id=project_id).exists():
                raise CommandError(f"Project {project_id} tidak ditemukan.")
            queryset = queryset.filter(project_id=project_id)

        trackers = list(queryset.select_related("project").order_by("project_id"))
        if not trackers:
            scope = f"project {project_id}" if project_id else "seluruh project"
            self.stdout.write(
                self.style.WARNING(f"Tidak ada flag reload menggantung pada {scope}.")
            )
            return

        self.stdout.write(
            f"Target: {len(trackers)} project, include_volume={include_volume}, "
            f"dry_run={dry_run}"
        )

        total_reload = 0
        total_volume = 0
        for tracker in trackers:
            reload_ids = tracker.pending_reload_job_ids or []
            volume_ids = tracker.pending_volume_reset_job_ids or []
            jumlah_pekerjaan = Pekerjaan.objects.filter(project_id=tracker.project_id).count()
            porsi = (
                f"{round(100 * len(reload_ids) / jumlah_pekerjaan)}%"
                if jumlah_pekerjaan else "n/a"
            )
            nama = getattr(tracker.project, "nama", "") or "-"
            self.stdout.write(
                f" - project {tracker.project_id} ({nama}): "
                f"{len(reload_ids)} dari {jumlah_pekerjaan} pekerjaan ditandai ({porsi})"
                + (f", volume={len(volume_ids)}" if include_volume else "")
            )
            total_reload += len(reload_ids)
            if include_volume:
                total_volume += len(volume_ids)

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"DRY-RUN selesai. Akan mengosongkan {total_reload} flag reload"
                    + (f" dan {total_volume} flag volume." if include_volume else ".")
                )
            )
            return

        if not skip_confirm:
            confirm = input("Type 'CLEAR' to continue: ").strip()
            if confirm != "CLEAR":
                raise CommandError("Dibatalkan oleh user.")

        # `updated_at` sengaja TIDAK ikut: ia auto_now, dan bulk_update hanya akan
        # menulis nilai in-memory yang basi.
        fields = ["pending_reload_job_ids"]
        if include_volume:
            fields.append("pending_volume_reset_job_ids")

        for tracker in trackers:
            tracker.pending_reload_job_ids = []
            if include_volume:
                tracker.pending_volume_reset_job_ids = []

        ProjectChangeStatus.objects.bulk_update(trackers, fields)

        self.stdout.write(
            self.style.SUCCESS(
                f"Selesai. {len(trackers)} project dibersihkan; "
                f"{total_reload} flag reload dikosongkan"
                + (f", {total_volume} flag volume dikosongkan." if include_volume else ".")
            )
        )
        self.stdout.write(
            "Catatan: mirror di localStorage browser akan ikut menyusut sendiri saat "
            "halaman dimuat (sync LED memanggil syncFlags terhadap state server)."
        )
