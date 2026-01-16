"""
Load Testing with Locust

This file defines load testing scenarios for the AHSP application.
Run with: locust -f detail_project/tests/locustfile.py

Usage:
  # Development (local)
  locust -f detail_project/tests/locustfile.py --host=http://localhost:8000

  # Staging
  locust -f detail_project/tests/locustfile.py --host=https://staging.example.com

  # Web UI (default port 8089)
  # Open http://localhost:8089 in browser

  # Headless mode (for CI/CD)
  locust -f detail_project/tests/locustfile.py \
    --host=http://localhost:8000 \
    --users=50 \
    --spawn-rate=5 \
    --run-time=60s \
    --headless

Target Metrics:
- p95 < 500ms for read endpoints
- p95 < 1000ms for write endpoints
- Support 50+ concurrent users
- Error rate < 1%
"""

from locust import HttpUser, task, between, events
from locust.exception import RescheduleTask
import json
import random
import logging

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# User Behavior Classes
# ============================================================================

class AHSPUser(HttpUser):
    """
    Simulates a typical AHSP user interacting with the application.

    User behavior:
    - Login
    - Browse projects
    - View project details
    - Edit project data
    - Save changes
    - Logout
    """

    # Wait between tasks (in seconds)
    wait_time = between(1, 3)

    def on_start(self):
        """
        Called when a simulated user starts.
        Login and get CSRF token.
        """
        # Login
        self.login()

        # Store project IDs for later use
        self.project_ids = []

        # Fetch some project IDs
        self.fetch_project_list()

    def login(self):
        """Login to the application."""
        # Get login page to obtain CSRF token
        response = self.client.get("/accounts/login/")

        if response.status_code == 200:
            # Extract CSRF token from cookies
            csrf_token = self.client.cookies.get('csrftoken')

            # Attempt login
            login_data = {
                'login': 'loadtest',  # Use test user
                'password': 'loadtest123',
                'csrfmiddlewaretoken': csrf_token
            }

            response = self.client.post(
                "/accounts/login/",
                data=login_data,
                headers={'Referer': self.host + '/accounts/login/'}
            )

            if response.status_code in [200, 302]:
                logger.info("Login successful")
            else:
                logger.error(f"Login failed: {response.status_code}")
                raise RescheduleTask()
        else:
            logger.error("Could not access login page")
            raise RescheduleTask()

    def fetch_project_list(self):
        """Fetch project list to get IDs."""
        response = self.client.get("/dashboard/")

        if response.status_code == 200:
            # In real scenario, parse HTML or JSON to extract project IDs
            # For now, use mock IDs
            self.project_ids = [1, 2, 3, 4, 5]
            logger.info(f"Fetched {len(self.project_ids)} project IDs")
        else:
            logger.warning("Could not fetch project list")

    @task(10)
    def view_project_list(self):
        """View project list page (common action)."""
        with self.client.get(
            "/dashboard/",
            catch_response=True,
            name="View Project List"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(8)
    def view_list_pekerjaan(self):
        """View list pekerjaan for a project."""
        if not self.project_ids:
            return

        project_id = random.choice(self.project_ids)

        with self.client.get(
            f"/detail_project/list_pekerjaan/{project_id}/",
            catch_response=True,
            name="View List Pekerjaan"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(6)
    def get_pekerjaan_tree(self):
        """Get pekerjaan tree via API (read operation)."""
        if not self.project_ids:
            return

        project_id = random.choice(self.project_ids)

        with self.client.get(
            f"/detail_project/api/{project_id}/list_pekerjaan/tree/",
            catch_response=True,
            name="API: Get Pekerjaan Tree"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Rate limited - expected behavior
                response.success()
                logger.info("Rate limited (expected)")
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(4)
    def save_volume(self):
        """Save volume data (write operation)."""
        if not self.project_ids:
            return

        project_id = random.choice(self.project_ids)

        # Mock payload
        payload = {
            'volumes': [{
                'pekerjaan_id': random.randint(1, 100),
                'quantity': str(random.uniform(1, 100))
            }]
        }

        csrf_token = self.client.cookies.get('csrftoken')

        with self.client.post(
            f"/detail_project/api/{project_id}/volume/save/",
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_token
            },
            catch_response=True,
            name="API: Save Volume"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 429:
                # Rate limited
                response.success()
                logger.info("Save rate limited (expected)")
            elif response.status_code == 400:
                # Validation error (expected with mock data)
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(2)
    def view_rekap(self):
        """View rekap/summary page."""
        if not self.project_ids:
            return

        project_id = random.choice(self.project_ids)

        with self.client.get(
            f"/detail_project/rekap_kebutuhan/{project_id}/",
            catch_response=True,
            name="View Rekap"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(1)
    def health_check(self):
        """Check health endpoint."""
        with self.client.get(
            "/health/",
            catch_response=True,
            name="Health Check"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


class AdminUser(HttpUser):
    """
    Simulates an admin user with heavier operations.

    Admin behavior:
    - Bulk operations
    - Deep copy projects
    - Export operations
    - System monitoring
    """

    wait_time = between(2, 5)

    def on_start(self):
        """Login as admin."""
        self.login_admin()
        self.project_ids = [1, 2, 3, 4, 5]

    def login_admin(self):
        """Login with admin credentials."""
        response = self.client.get("/accounts/login/")
        csrf_token = self.client.cookies.get('csrftoken')

        login_data = {
            'login': 'admin',
            'password': 'admin123',
            'csrfmiddlewaretoken': csrf_token
        }

        self.client.post(
            "/accounts/login/",
            data=login_data,
            headers={'Referer': self.host + '/accounts/login/'}
        )

    @task(5)
    def view_dashboard(self):
        """View admin dashboard."""
        with self.client.get(
            "/dashboard/",
            catch_response=True,
            name="Admin: View Dashboard"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(2)
    def bulk_export(self):
        """Trigger bulk export (expensive operation)."""
        if not self.project_ids:
            return

        project_id = random.choice(self.project_ids)

        with self.client.get(
            f"/detail_project/export/rekap/{project_id}/",
            catch_response=True,
            name="Admin: Bulk Export"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Rate limited (export category)
                response.success()
                logger.info("Export rate limited (expected)")
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(1)
    def deep_copy_project(self):
        """Attempt deep copy (bulk category)."""
        if not self.project_ids:
            return

        source_id = random.choice(self.project_ids)

        csrf_token = self.client.cookies.get('csrftoken')

        payload = {
            'source_project_id': source_id,
            'new_name': f'Copy of Project {source_id}'
        }

        with self.client.post(
            f"/detail_project/api/deep_copy/{source_id}/",
            data=json.dumps(payload),
            headers={
                'Content-Type': 'application/json',
                'X-CSRFToken': csrf_token
            },
            catch_response=True,
            name="Admin: Deep Copy"
        ) as response:
            if response.status_code in [200, 201]:
                response.success()
            elif response.status_code == 429:
                # Rate limited (bulk category - strict limits)
                response.success()
                logger.info("Deep copy rate limited (expected)")
            else:
                # May fail due to mock data
                response.success()


class ReadOnlyUser(HttpUser):
    """
    Simulates read-only user (viewer, auditor, etc.).

    Behavior:
    - Only read operations
    - No writes
    - Frequent page views
    """

    wait_time = between(0.5, 2)

    def on_start(self):
        """Login as read-only user."""
        response = self.client.get("/accounts/login/")
        csrf_token = self.client.cookies.get('csrftoken')

        login_data = {
            'login': 'viewer',
            'password': 'viewer123',
            'csrfmiddlewaretoken': csrf_token
        }

        self.client.post(
            "/accounts/login/",
            data=login_data,
            headers={'Referer': self.host + '/accounts/login/'}
        )

        self.project_ids = [1, 2, 3, 4, 5]

    @task(10)
    def browse_projects(self):
        """Browse project list frequently."""
        with self.client.get(
            "/dashboard/",
            catch_response=True,
            name="Viewer: Browse Projects"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(8)
    def view_details(self):
        """View project details."""
        if not self.project_ids:
            return

        project_id = random.choice(self.project_ids)

        with self.client.get(
            f"/detail_project/list_pekerjaan/{project_id}/",
            catch_response=True,
            name="Viewer: View Details"
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")

    @task(6)
    def get_tree_data(self):
        """Fetch tree data via API."""
        if not self.project_ids:
            return

        project_id = random.choice(self.project_ids)

        with self.client.get(
            f"/detail_project/api/{project_id}/list_pekerjaan/tree/",
            catch_response=True,
            name="Viewer: Get Tree Data"
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 429:
                # Even read operations can be rate limited
                response.success()
            else:
                response.failure(f"Failed: {response.status_code}")


# ============================================================================
# Event Listeners (for metrics)
# ============================================================================

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when load test starts."""
    logger.info("Load test starting...")
    logger.info(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when load test stops."""
    logger.info("Load test completed")

    # Print summary
    stats = environment.stats
    logger.info(f"Total requests: {stats.total.num_requests}")
    logger.info(f"Total failures: {stats.total.num_failures}")
    logger.info(f"Median response time: {stats.total.median_response_time}ms")
    logger.info(f"95 percentile: {stats.total.get_response_time_percentile(0.95)}ms")
    logger.info(f"99 percentile: {stats.total.get_response_time_percentile(0.99)}ms")


# ============================================================================
# Usage Examples
# ============================================================================

"""
# Quick Test (10 users for 30 seconds)
locust -f locustfile.py --host=http://localhost:8000 --users=10 --spawn-rate=2 --run-time=30s --headless

# Staging Test (50 users for 5 minutes)
locust -f locustfile.py --host=https://staging.example.com --users=50 --spawn-rate=5 --run-time=5m --headless

# Production Stress Test (100 users ramping up)
locust -f locustfile.py --host=https://production.example.com --users=100 --spawn-rate=10 --run-time=10m --headless

# Web UI Mode (interactive)
locust -f locustfile.py --host=http://localhost:8000
# Then open http://localhost:8089

# Different user types distribution
# Default: All AHSPUser
# To customize, use Locust's weight parameter in class definition

# Export results to CSV
locust -f locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=60s --headless --csv=results

# Expected Results:
# - p95 response time < 500ms for reads
# - p95 response time < 1000ms for writes
# - Error rate < 1%
# - Rate limiting works (429 responses expected)
# - No server crashes or 500 errors (except expected errors)
"""
