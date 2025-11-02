"""
Management command to refresh materialized view for AHSP statistics.

PHASE 3 DAY 3: Materialized View Refresh

Usage:
    python manage.py refresh_stats
    python manage.py refresh_stats --concurrently  # Non-blocking refresh
"""

import time

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Refresh the AHSP statistics materialized view"

    def add_arguments(self, parser):
        parser.add_argument(
            "--concurrently",
            action="store_true",
            help="Refresh concurrently (non-blocking, requires unique index)",
        )

    def handle(self, *args, **options):
        concurrently = options.get("concurrently", False)

        self.stdout.write("=" * 60)
        self.stdout.write("AHSP Statistics Materialized View Refresh")
        self.stdout.write("=" * 60)

        if concurrently:
            self.stdout.write(
                "Mode: CONCURRENT (non-blocking, queries can continue)"
            )
        else:
            self.stdout.write(
                "Mode: STANDARD (blocking, faster but locks view)"
            )

        self.stdout.write("\nRefreshing materialized view...")

        start_time = time.time()

        with connection.cursor() as cursor:
            if concurrently:
                # CONCURRENTLY: Allows queries to continue during refresh
                # Requires UNIQUE index on the view
                cursor.execute(
                    "REFRESH MATERIALIZED VIEW CONCURRENTLY referensi_ahsp_stats"
                )
            else:
                # Standard: Faster but locks the view during refresh
                cursor.execute(
                    "REFRESH MATERIALIZED VIEW referensi_ahsp_stats"
                )

        elapsed_ms = (time.time() - start_time) * 1000

        self.stdout.write(
            self.style.SUCCESS(
                f"\nMaterialized view refreshed successfully in {elapsed_ms:.2f}ms"
            )
        )

        # Get statistics about the refreshed view
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total_ahsp,
                    SUM(rincian_total) AS total_rincian,
                    SUM(tk_count) AS total_tk,
                    SUM(bhn_count) AS total_bhn,
                    SUM(alt_count) AS total_alt,
                    SUM(lain_count) AS total_lain,
                    SUM(zero_coef_count) AS total_zero_coef,
                    SUM(missing_unit_count) AS total_missing_unit
                FROM referensi_ahsp_stats
            """
            )
            stats = cursor.fetchone()

        self.stdout.write("\nMaterialized View Statistics:")
        self.stdout.write("-" * 60)
        self.stdout.write(f"  Total AHSP records: {stats[0]:,}")
        self.stdout.write(f"  Total rincian items: {stats[1]:,}")
        self.stdout.write(f"  TK items: {stats[2]:,}")
        self.stdout.write(f"  BHN items: {stats[3]:,}")
        self.stdout.write(f"  ALT items: {stats[4]:,}")
        self.stdout.write(f"  LAIN items: {stats[5]:,}")
        self.stdout.write(f"  Zero coefficient: {stats[6]:,}")
        self.stdout.write(f"  Missing unit: {stats[7]:,}")
        self.stdout.write("=" * 60)

        self.stdout.write(
            self.style.SUCCESS(
                "\nTip: Run this command after importing new AHSP data."
            )
        )
