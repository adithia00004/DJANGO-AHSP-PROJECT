"""
Management command to warm referensi cache.

PHASE 3: Pre-populate cache with frequently accessed data.
Useful after deployment or cache clear.

Usage:
    python manage.py warm_cache
"""

from django.core.management.base import BaseCommand

from referensi.services.cache_helpers import ReferensiCache


class Command(BaseCommand):
    help = "Warm referensi cache with frequently accessed data"

    def handle(self, *args, **options):
        self.stdout.write("Warming referensi cache...")

        # Warm cache
        ReferensiCache.warm_cache()

        # Get stats
        stats = ReferensiCache.get_cache_stats()

        self.stdout.write(self.style.SUCCESS("Cache warmed successfully!"))
        self.stdout.write(f"  Sources cached: {stats['sources_cached']}")
        self.stdout.write(
            f"  Klasifikasi cached: {stats['klasifikasi_cached']}"
        )
        self.stdout.write(
            f"  Job choices cached: {stats['job_choices_cached']}"
        )

        # Get counts
        sources = ReferensiCache.get_available_sources()
        klasifikasi = ReferensiCache.get_available_klasifikasi()
        job_choices = ReferensiCache.get_job_choices()

        self.stdout.write(f"\n  Total sources: {len(sources)}")
        self.stdout.write(f"  Total klasifikasi: {len(klasifikasi)}")
        self.stdout.write(f"  Total job choices: {len(job_choices)}")
