import json
import os
from unittest.mock import patch

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase

from detail_project.views_monitoring import api_report_client_metric


class ClientMetricsSecurityTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        cache.clear()

    def tearDown(self):
        cache.clear()

    def _post_metric(self, headers=None, payload=None):
        headers = headers or {}
        payload = payload or {"type": "pageLoad", "metric": {"duration": 100}}
        return self.factory.post(
            "/detail_project/api/monitoring/report-client-metric/",
            data=json.dumps(payload),
            content_type="application/json",
            **headers,
        )

    def test_metrics_endpoint_disabled_without_api_key(self):
        with patch.dict(os.environ, {"METRICS_API_KEY": ""}, clear=False):
            request = self._post_metric()
            response = api_report_client_metric(request)

        self.assertEqual(response.status_code, 503)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("error"), "Metrics endpoint is not configured")

    def test_metrics_endpoint_rejects_invalid_api_key(self):
        with patch.dict(os.environ, {"METRICS_API_KEY": "valid-key"}, clear=False):
            request = self._post_metric(headers={"HTTP_X_METRICS_KEY": "wrong-key"})
            response = api_report_client_metric(request)

        self.assertEqual(response.status_code, 403)
        payload = json.loads(response.content)
        self.assertEqual(payload.get("error"), "Unauthorized")

    def test_metrics_endpoint_accepts_valid_api_key(self):
        with patch.dict(
            os.environ,
            {"METRICS_API_KEY": "valid-key", "METRICS_RATE_LIMIT": "10", "METRICS_RATE_WINDOW": "60"},
            clear=False,
        ):
            request = self._post_metric(headers={"HTTP_X_METRICS_KEY": "valid-key"})
            response = api_report_client_metric(request)

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content)
        self.assertTrue(payload.get("ok"))

    def test_metrics_endpoint_applies_rate_limit(self):
        with patch.dict(
            os.environ,
            {"METRICS_API_KEY": "valid-key", "METRICS_RATE_LIMIT": "2", "METRICS_RATE_WINDOW": "60"},
            clear=False,
        ):
            request_1 = self._post_metric(headers={"HTTP_X_METRICS_KEY": "valid-key"})
            request_2 = self._post_metric(headers={"HTTP_X_METRICS_KEY": "valid-key"})
            request_3 = self._post_metric(headers={"HTTP_X_METRICS_KEY": "valid-key"})

            response_1 = api_report_client_metric(request_1)
            response_2 = api_report_client_metric(request_2)
            response_3 = api_report_client_metric(request_3)

        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(response_2.status_code, 200)
        self.assertEqual(response_3.status_code, 429)
        payload = json.loads(response_3.content)
        self.assertEqual(payload.get("error"), "Rate limit exceeded")
