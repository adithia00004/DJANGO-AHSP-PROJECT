"""
Management command for Redis cache administration.

PHASE 4: Redis Cache Layer

Provides commands to:
- View cache statistics
- Clear/invalidate caches
- Test cache connectivity
- Warm up cache with common queries
"""

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from referensi.services.cache_service import CacheService
from referensi.services.ahsp_repository import ahsp_repository
from referensi.models import AHSPReferensi, RincianReferensi


class Command(BaseCommand):
    help = "Redis cache administration and management"

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            type=str,
            choices=['stats', 'clear', 'test', 'warmup', 'invalidate'],
            help='Action to perform'
        )

        parser.add_argument(
            '--pattern',
            type=str,
            default='ahsp:*',
            help='Cache key pattern for invalidate action (default: ahsp:*)'
        )

        parser.add_argument(
            '--queries',
            type=str,
            nargs='+',
            help='Queries to warm up cache (for warmup action)'
        )

        parser.add_argument(
            '--force',
            action='store_true',
            help='Force action without confirmation'
        )

    def handle(self, *args, **options):
        action = options['action']

        if action == 'stats':
            self.show_stats()
        elif action == 'clear':
            self.clear_cache(options['force'])
        elif action == 'test':
            self.test_cache()
        elif action == 'warmup':
            self.warmup_cache(options.get('queries', []))
        elif action == 'invalidate':
            self.invalidate_cache(options['pattern'], options['force'])
        else:
            raise CommandError(f"Unknown action: {action}")

    def show_stats(self):
        """Display cache statistics."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("📊 REDIS CACHE STATISTICS"))
        self.stdout.write("="*60 + "\n")

        cache = CacheService()
        stats = cache.get_stats()

        if not stats.get('connected'):
            self.stdout.write(self.style.ERROR(
                f"❌ Failed to connect to cache: {stats.get('error', 'Unknown error')}"
            ))
            return

        # Display statistics
        self.stdout.write(f"✅ Connection Status: {self.style.SUCCESS('Connected')}")
        self.stdout.write(f"📦 Total Keys: {self.style.WARNING(str(stats.get('total_keys', 0)))}")
        self.stdout.write(f"💾 Memory Used: {self.style.WARNING(stats.get('used_memory', 'N/A'))}")
        self.stdout.write(f"🎯 Hit Rate: {self.style.WARNING(f\"{stats.get('hit_rate', 0):.2f}%\")}")
        self.stdout.write(f"⏱️  Uptime: {self.style.WARNING(f\"{stats.get('uptime_seconds', 0):,}s\")}\n")

        # Cache configuration
        self.stdout.write(self.style.SUCCESS("⚙️  CACHE CONFIGURATION:"))
        self.stdout.write(f"Backend: {settings.CACHES['default']['BACKEND']}")
        self.stdout.write(f"Location: {settings.CACHES['default']['LOCATION']}")
        self.stdout.write(f"Default Timeout: {settings.CACHES['default'].get('TIMEOUT', 'N/A')}s")
        self.stdout.write(f"Key Prefix: {settings.CACHES['default'].get('KEY_PREFIX', 'N/A')}\n")

        # Search settings
        self.stdout.write(self.style.SUCCESS("🔍 SEARCH CACHE SETTINGS:"))
        self.stdout.write(f"Cache Enabled: {settings.FTS_CACHE_RESULTS}")
        self.stdout.write(f"Cache TTL: {settings.FTS_CACHE_TTL}s\n")

    def clear_cache(self, force=False):
        """Clear all application caches."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.WARNING("🗑️  CLEAR ALL CACHES"))
        self.stdout.write("="*60 + "\n")

        if not force:
            confirm = input("Are you sure you want to clear ALL caches? This cannot be undone. (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR("Aborted."))
                return

        cache = CacheService()
        deleted = cache.invalidate_all()

        self.stdout.write(self.style.SUCCESS(
            f"✅ Successfully cleared {deleted} cache keys\n"
        ))

    def test_cache(self):
        """Test cache connectivity and basic operations."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("🧪 CACHE CONNECTIVITY TEST"))
        self.stdout.write("="*60 + "\n")

        cache = CacheService()

        # Test 1: Connection
        self.stdout.write("Test 1: Connection...", ending=" ")
        stats = cache.get_stats()
        if stats.get('connected'):
            self.stdout.write(self.style.SUCCESS("✅ PASSED"))
        else:
            self.stdout.write(self.style.ERROR(f"❌ FAILED: {stats.get('error')}"))
            return

        # Test 2: Set/Get
        self.stdout.write("Test 2: Set/Get...", ending=" ")
        test_key = "test:cache_admin:connectivity"
        test_value = {"test": "value", "timestamp": "2025-11-04"}

        cache.set(test_key, test_value, timeout=60)
        retrieved = cache.get(test_key)

        if retrieved == test_value:
            self.stdout.write(self.style.SUCCESS("✅ PASSED"))
        else:
            self.stdout.write(self.style.ERROR("❌ FAILED"))
            return

        # Test 3: Delete
        self.stdout.write("Test 3: Delete...", ending=" ")
        cache.delete(test_key)
        retrieved = cache.get(test_key)

        if retrieved is None:
            self.stdout.write(self.style.SUCCESS("✅ PASSED"))
        else:
            self.stdout.write(self.style.ERROR("❌ FAILED"))
            return

        # Test 4: Repository search with cache
        self.stdout.write("Test 4: Search Cache...", ending=" ")

        # First search (cache miss)
        results1 = ahsp_repository.search_ahsp("test_query_12345", limit=5)

        # Second search (should be cached)
        results2 = ahsp_repository.search_ahsp("test_query_12345", limit=5)

        # Both should return same (empty) results
        if list(results1) == list(results2):
            self.stdout.write(self.style.SUCCESS("✅ PASSED"))
        else:
            self.stdout.write(self.style.ERROR("❌ FAILED"))
            return

        self.stdout.write(self.style.SUCCESS("\n✅ All tests passed!"))
        self.stdout.write("Cache is working correctly.\n")

    def warmup_cache(self, queries):
        """Warm up cache with common search queries."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.SUCCESS("🔥 CACHE WARMUP"))
        self.stdout.write("="*60 + "\n")

        # Default queries if none provided
        if not queries:
            queries = [
                "pekerjaan",
                "beton",
                "tanah",
                "galian",
                "pondasi",
                "baja",
                "atap",
                "dinding",
                "pengecatan",
                "plester",
            ]
            self.stdout.write("Using default warmup queries...\n")

        self.stdout.write(f"Warming up cache with {len(queries)} queries:\n")

        total_cached = 0
        for query in queries:
            self.stdout.write(f"  - {query:20}", ending=" ")

            try:
                # Perform search (will cache results)
                results = ahsp_repository.search_ahsp(query, limit=50)
                count = len(list(results))

                self.stdout.write(self.style.SUCCESS(f"✅ ({count} results)"))
                total_cached += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error: {e}"))

        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Successfully warmed up {total_cached}/{len(queries)} queries\n"
        ))

    def invalidate_cache(self, pattern, force=False):
        """Invalidate caches matching pattern."""
        self.stdout.write("\n" + "="*60)
        self.stdout.write(self.style.WARNING(f"🗑️  INVALIDATE CACHE: {pattern}"))
        self.stdout.write("="*60 + "\n")

        if not force and pattern == 'ahsp:*':
            confirm = input(f"This will invalidate ALL application caches. Continue? (yes/no): ")
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR("Aborted."))
                return

        cache = CacheService()

        if pattern == 'ahsp:search:*':
            deleted = cache.invalidate_search_cache()
            cache_type = "search"
        elif pattern == 'ahsp:audit:*':
            deleted = cache.invalidate_audit_cache()
            cache_type = "audit"
        elif pattern == 'ahsp:*':
            deleted = cache.invalidate_all()
            cache_type = "all"
        else:
            deleted = cache.delete_pattern(pattern)
            cache_type = "custom"

        self.stdout.write(self.style.SUCCESS(
            f"✅ Successfully invalidated {deleted} {cache_type} cache keys\n"
        ))


# Example usage:
# python manage.py cache_admin stats
# python manage.py cache_admin test
# python manage.py cache_admin warmup
# python manage.py cache_admin warmup --queries "beton" "pekerjaan" "tanah"
# python manage.py cache_admin invalidate --pattern "ahsp:search:*"
# python manage.py cache_admin clear --force
