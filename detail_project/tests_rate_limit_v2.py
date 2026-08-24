import threading
import json
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, override_settings

from detail_project import api_helpers


class _AtomicFakeCache:
    """Small cache double with the atomic operations used by limiter v2."""

    def __init__(self):
        self._lock = threading.Lock()
        self._data = {}

    def add(self, key, value, timeout=None):
        with self._lock:
            if key in self._data:
                return False
            self._data[key] = int(value)
            return True

    def incr(self, key, delta=1):
        with self._lock:
            if key not in self._data:
                raise ValueError(key)
            self._data[key] += delta
            return self._data[key]


class RateLimitV2Tests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = SimpleNamespace(id=91)
        self.request = self.factory.post('/test/')
        self.request.user = self.user

    @staticmethod
    def _view(request):
        return HttpResponse('ok')

    def test_fixed_window_does_not_accumulate_across_buckets(self):
        endpoint = api_helpers.rate_limit(max_requests=2, window=60)(self._view)
        cache = _AtomicFakeCache()
        statuses = []

        with patch.object(api_helpers, 'cache', cache), patch.object(api_helpers.time, 'time') as now:
            for timestamp in (0, 50, 100, 150, 200):
                now.return_value = timestamp
                statuses.append(endpoint(self.request).status_code)

        self.assertEqual(statuses, [200, 200, 200, 200, 200])

    def test_limit_and_retry_after_are_bucket_relative(self):
        endpoint = api_helpers.rate_limit(max_requests=1, window=60)(self._view)
        cache = _AtomicFakeCache()

        with patch.object(api_helpers, 'cache', cache), patch.object(api_helpers.time, 'time', return_value=100.25):
            self.assertEqual(endpoint(self.request).status_code, 200)
            response = endpoint(self.request)

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response['Retry-After'], '20')
        self.assertEqual(response['X-RateLimit-Remaining'], '0')
        payload = json.loads(response.content)
        self.assertEqual(payload['code'], 'RATE_LIMIT_EXCEEDED')
        self.assertEqual(payload['retry_after'], 20)
        self.assertEqual(payload['details']['reset_at'], 120)

    def test_methods_do_not_share_quota(self):
        endpoint = api_helpers.rate_limit(
            max_requests=1,
            window=60,
            methods=('POST',),
        )(self._view)
        cache = _AtomicFakeCache()
        get_request = self.factory.get('/test/')
        get_request.user = self.user

        with patch.object(api_helpers, 'cache', cache), patch.object(api_helpers.time, 'time', return_value=10):
            self.assertEqual(endpoint(get_request).status_code, 200)
            self.assertEqual(endpoint(get_request).status_code, 200)
            self.assertEqual(endpoint(self.request).status_code, 200)
            self.assertEqual(endpoint(self.request).status_code, 429)

    def test_cache_failure_is_fail_open(self):
        with self.assertLogs('detail_project.api_helpers', level='ERROR') as logs:
            with patch.object(api_helpers, '_rate_limit_increment', side_effect=RuntimeError('redis down')):
                response = api_helpers.rate_limit(max_requests=1, window=60)(self._view)(self.request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Rate limiter backend unavailable', '\n'.join(logs.output))

    def test_low_cardinality_metrics_are_recorded(self):
        endpoint = api_helpers.rate_limit(max_requests=2, window=60)(self._view)
        cache = _AtomicFakeCache()
        with patch.object(api_helpers, 'cache', cache), patch.object(api_helpers.time, 'time', return_value=10):
            endpoint(self.request)
            endpoint(self.request)
            endpoint(self.request)

        self.assertEqual(
            cache._data['metric:rate_limit_v2:allowed:global'],
            2,
        )
        self.assertEqual(
            cache._data['metric:rate_limit_v2:blocked:global'],
            1,
        )
        self.assertEqual(
            cache._data['metric:rate_limit_v2:near_limit:global'],
            1,
        )

    @override_settings(DETAIL_PROJECT_RATE_LIMIT_MODE='observe')
    def test_observe_mode_records_would_block_but_allows_request(self):
        endpoint = api_helpers.rate_limit(max_requests=1, window=60)(self._view)
        cache = _AtomicFakeCache()
        with patch.object(api_helpers, 'cache', cache), patch.object(api_helpers.time, 'time', return_value=10):
            self.assertEqual(endpoint(self.request).status_code, 200)
            second = endpoint(self.request)

        self.assertEqual(second.status_code, 200)
        self.assertEqual(cache._data['metric:rate_limit_v2:would_block:global'], 1)

    @override_settings(DETAIL_PROJECT_RATE_LIMIT_MODE='off')
    def test_off_mode_bypasses_counter_for_emergency_rollback(self):
        endpoint = api_helpers.rate_limit(max_requests=1, window=60)(self._view)
        cache = _AtomicFakeCache()
        with patch.object(api_helpers, 'cache', cache), patch.object(api_helpers.time, 'time', return_value=10):
            self.assertEqual(endpoint(self.request).status_code, 200)
            self.assertEqual(endpoint(self.request).status_code, 200)

        self.assertEqual(cache._data, {})

    def test_increment_is_not_lost_under_concurrency(self):
        cache = _AtomicFakeCache()
        with patch.object(api_helpers, 'cache', cache):
            with ThreadPoolExecutor(max_workers=8) as pool:
                values = list(pool.map(
                    lambda _: api_helpers._rate_limit_increment('concurrent-key', 60),
                    range(100),
                ))

        self.assertEqual(max(values), 100)
        self.assertEqual(len(set(values)), 100)
