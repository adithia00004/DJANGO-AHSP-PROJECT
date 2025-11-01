from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import DEFAULT_DB_ALIAS, connections, transaction

from referensi.models import AHSPReferensi, RincianReferensi

try:
    from detail_project.models import DetailAHSPProject
except Exception as exc:  # pragma: no cover - import guarded for migrations
    DetailAHSPProject = None


class Command(BaseCommand):
    help = (
        "Detach project detail links and delete all AHSP referensi data. "
        "Useful when you want to replace the reference dataset entirely."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--noinput",
            action="store_true",
            dest="noinput",
            help="Do not prompt for confirmation.",
        )
        parser.add_argument(
            "--database",
            default=DEFAULT_DB_ALIAS,
            help="Nominates a database onto which to run the command.",
        )

    def handle(self, *args, **options):
        database = options["database"]
        noinput = options["noinput"]

        if DetailAHSPProject is None:
            raise CommandError("detail_project.models.DetailAHSPProject could not be imported.")

        connection = connections[database]

        if connection.vendor != "sqlite" and connection.in_atomic_block:
            raise CommandError("Cannot run purge inside an existing transaction.")

        if not noinput:
            confirmed = input(
                "This will detach project detail rows and delete ALL AHSP referensi data.\n"
                "Type 'yes' to continue: "
            )
            if confirmed.lower() != "yes":
                self.stdout.write(self.style.WARNING("Aborted."))
                return

        detail_qs = DetailAHSPProject.objects.using(database).filter(ref_ahsp__isnull=False)
        detail_count = detail_qs.count()

        job_qs = AHSPReferensi.objects.using(database).all()
        job_count = job_qs.count()
        item_qs = RincianReferensi.objects.using(database).all()
        item_count = item_qs.count()

        if not job_count and not item_count:
            self.stdout.write(self.style.WARNING("No AHSP referensi data found. Nothing to purge."))
            return

        with transaction.atomic(using=database):
            if detail_count:
                detached = detail_qs.update(ref_ahsp=None)
            else:
                detached = 0

            items_deleted, _ = item_qs.delete()
            jobs_deleted, _ = job_qs.delete()

        self.stdout.write(self.style.SUCCESS(
            "Detached %d project detail rows." % detached
        ))
        self.stdout.write(self.style.SUCCESS(
            "Deleted %d AHSP detail rows and %d AHSP jobs." % (items_deleted, jobs_deleted)
        ))
