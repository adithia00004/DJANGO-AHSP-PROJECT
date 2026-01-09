"""
Locust Load Testing Configuration for DJANGO AHSP PROJECT
==========================================================

This file contains user behavior scenarios for load testing the detail_project app.

Usage:
------
1. Start Django server: python manage.py runserver
2. Run Locust: locust -f load_testing/locustfile.py --host=http://localhost:8000
3. Open browser: http://localhost:8089
4. Set users and spawn rate, then start test

User Classes:
-------------
- BrowsingUser: Simulates normal page browsing (60% of traffic)
- APIUser: Simulates frontend API calls (30% of traffic)  
- HeavyUser: Simulates export operations (10% of traffic)
"""

import random
import json
from locust import HttpUser, task, between, tag


class BrowsingUser(HttpUser):
    """
    Simulates a typical user browsing pages.
    Represents 60% of expected traffic.
    """
    weight = 6
    wait_time = between(2, 5)  # Wait 2-5 seconds between tasks
    
    def on_start(self):
        """Login at the start of the session"""
        # Try to get CSRF token first
        response = self.client.get("/accounts/login/")
        # For testing without auth, you can skip login
        # In production testing, implement proper login flow
        self.project_ids = [144, 145, 146, 147, 148]  # Valid project IDs from database
    
    @tag('page', 'dashboard')
    @task(10)
    def browse_dashboard(self):
        """View main dashboard - most common action"""
        self.client.get("/dashboard/", name="/dashboard/")
    
    @tag('page', 'list_pekerjaan')
    @task(5)
    def browse_list_pekerjaan(self):
        """View list pekerjaan page"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/{project_id}/list-pekerjaan/",
            name="/detail-project/[id]/list-pekerjaan/"
        )
    
    @tag('page', 'jadwal')
    @task(4)
    def browse_jadwal_pekerjaan(self):
        """View jadwal pekerjaan (Gantt/Kurva S) - HEAVY"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/{project_id}/jadwal-pekerjaan/",
            name="/detail-project/[id]/jadwal-pekerjaan/"
        )
    
    @tag('page', 'template_ahsp')
    @task(3)
    def browse_template_ahsp(self):
        """View template AHSP page"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/{project_id}/template-ahsp/",
            name="/detail-project/[id]/template-ahsp/"
        )
    
    @tag('page', 'rekap')
    @task(4)
    def browse_rekap_rab(self):
        """View rekap RAB page"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/{project_id}/rekap-rab/",
            name="/detail-project/[id]/rekap-rab/"
        )
    
    @tag('page', 'harga_items')
    @task(3)
    def browse_harga_items(self):
        """View harga items page"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/{project_id}/harga-items/",
            name="/detail-project/[id]/harga-items/"
        )
    
    @tag('page', 'volume')
    @task(2)
    def browse_volume_pekerjaan(self):
        """View volume pekerjaan page"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/{project_id}/volume-pekerjaan/",
            name="/detail-project/[id]/volume-pekerjaan/"
        )


class APIUser(HttpUser):
    """
    Simulates frontend JavaScript making API calls.
    Represents 30% of expected traffic.
    """
    weight = 3
    wait_time = between(1, 3)  # API calls are faster
    
    def on_start(self):
        """Initialize API user"""
        self.project_ids = [144, 145, 146, 147, 148]  # Valid project IDs from database
    
    @tag('api', 'critical')
    @task(10)
    def api_list_pekerjaan_tree(self):
        """Get pekerjaan tree structure - CRITICAL API"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/api/project/{project_id}/list-pekerjaan/tree/",
            name="/api/project/[id]/list-pekerjaan/tree/"
        )
    
    @tag('api', 'critical')
    @task(8)
    def api_rekap_rab(self):
        """Get rekap RAB data - CRITICAL API (heavy aggregation)"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/api/project/{project_id}/rekap/",
            name="/api/project/[id]/rekap/"
        )
    
    @tag('api', 'critical')
    @task(7)
    def api_chart_data(self):
        """Get chart data for Gantt/Kurva S - CRITICAL API"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/api/v2/project/{project_id}/chart-data/",
            name="/api/v2/project/[id]/chart-data/"
        )
    
    @tag('api', 'medium')
    @task(6)
    def api_harga_items_list(self):
        """Get harga items list"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/api/project/{project_id}/harga-items/list/",
            name="/api/project/[id]/harga-items/list/"
        )
    
    @tag('api', 'medium')
    @task(5)
    def api_rekap_kebutuhan(self):
        """Get rekap kebutuhan data"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/api/project/{project_id}/rekap-kebutuhan/",
            name="/api/project/[id]/rekap-kebutuhan/"
        )
    
    @tag('api', 'medium')
    @task(5)
    def api_volume_pekerjaan_list(self):
        """Get volume pekerjaan list"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/api/project/{project_id}/volume-pekerjaan/list/",
            name="/api/project/[id]/volume-pekerjaan/list/"
        )
    
    @tag('api', 'tahapan')
    @task(4)
    def api_tahapan_list(self):
        """Get tahapan list"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/api/project/{project_id}/tahapan/",
            name="/api/project/[id]/tahapan/"
        )
    
    @tag('api', 'assignments')
    @task(4)
    def api_v2_assignments(self):
        """Get project assignments (V2 API)"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/api/v2/project/{project_id}/assignments/",
            name="/api/v2/project/[id]/assignments/"
        )
    
    @tag('api', 'kurva_s')
    @task(3)
    def api_kurva_s_data(self):
        """Get Kurva S data"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/api/v2/project/{project_id}/kurva-s-data/",
            name="/api/v2/project/[id]/kurva-s-data/"
        )
    
    @tag('api', 'template')
    @task(3)
    def api_template_export(self):
        """Export project as template JSON - NEW v2.2"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            f"/detail_project/api/project/{project_id}/templates/export/",
            name="/api/project/[id]/templates/export/",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if 'export_version' in data and 'pekerjaan' in data:
                        response.success()
                    else:
                        response.failure("Missing expected fields in template")
                except:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @tag('api', 'volume')
    @task(4)
    def api_volume_formula_state(self):
        """Get volume formula state - reads formula engine data"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail_project/api/project/{project_id}/volume/formula-state/",
            name="/api/project/[id]/volume/formula-state/"
        )
    
    @tag('api', 'parameters')
    @task(2)
    def api_parameters_list(self):
        """Get project parameters list (NEW v2.2)"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail_project/api/project/{project_id}/parameters/",
            name="/api/project/[id]/parameters/"
        )
    
    @tag('api', 'detail_ahsp')
    @task(3)
    def api_detail_ahsp(self):
        """Get detail AHSP for a pekerjaan"""
        project_id = random.choice(self.project_ids)
        pekerjaan_id = random.randint(1, 100)
        with self.client.get(
            f"/detail_project/api/project/{project_id}/detail-ahsp/{pekerjaan_id}/",
            name="/api/project/[id]/detail-ahsp/[pekerjaan_id]/",
            catch_response=True
        ) as response:
            # Accept both 200 and 404 (pekerjaan might not exist)
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


class HeavyUser(HttpUser):
    """
    Simulates users performing heavy operations like exports.
    Represents 10% of expected traffic.
    These are CPU/memory intensive operations.
    """
    weight = 1
    wait_time = between(10, 30)  # Longer wait between heavy operations
    
    def on_start(self):
        """Initialize heavy user"""
        self.project_ids = [144]  # Use single project for export tests
    
    @tag('export', 'pdf')
    @task(3)
    def export_rekap_rab_pdf(self):
        """Export Rekap RAB as PDF - HEAVY OPERATION"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            f"/detail-project/api/project/{project_id}/export/rekap-rab/pdf/",
            name="/api/export/rekap-rab/pdf/",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 500:
                response.failure("Server error during PDF export")
    
    @tag('export', 'excel')
    @task(3)
    def export_rekap_rab_xlsx(self):
        """Export Rekap RAB as Excel - HEAVY OPERATION"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            f"/detail-project/api/project/{project_id}/export/rekap-rab/xlsx/",
            name="/api/export/rekap-rab/xlsx/",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 500:
                response.failure("Server error during Excel export")
    
    @tag('export', 'jadwal')
    @task(2)
    def export_jadwal_pdf(self):
        """Export Jadwal Pekerjaan as PDF - VERY HEAVY"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            f"/detail-project/api/project/{project_id}/export/jadwal-pekerjaan/pdf/",
            name="/api/export/jadwal-pekerjaan/pdf/",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 500:
                response.failure("Server error during Jadwal PDF export")
    
    @tag('export', 'csv')
    @task(2)
    def export_harga_items_csv(self):
        """Export Harga Items as CSV - Medium weight"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            f"/detail-project/api/project/{project_id}/export/harga-items/csv/",
            name="/api/export/harga-items/csv/"
        )
    
    @tag('copy', 'heavy')
    @task(1)
    def deep_copy_project(self):
        """Deep copy project - VERY HEAVY OPERATION"""
        project_id = random.choice(self.project_ids)
        # Note: This is a POST operation, use with caution in load tests
        # Uncomment only if you want to test this (will create many projects!)
        # self.client.post(
        #     f"/detail-project/api/project/{project_id}/deep-copy/",
        #     name="/api/project/[id]/deep-copy/",
        #     json={"name_suffix": "_loadtest"}
        # )
        pass  # Disabled by default


class MutationUser(HttpUser):
    """
    Simulates users making POST/PUT/DELETE mutations.
    Tests concurrent writes and optimistic locking.
    Represents 5% of expected traffic.
    
    WARNING: These tests WRITE data! Use dedicated test database.
    """
    weight = 1  # 5% of traffic (adjust based on HeavyUser weight)
    wait_time = between(5, 15)  # Slower, more deliberate mutations
    
    # Toggle to actually perform mutations (default: disabled for safety)
    MUTATIONS_ENABLED = False
    
    def on_start(self):
        """Initialize mutation user with auth"""
        self.project_ids = [144]  # Use single test project
        # Authentication required for mutations
        # TODO: Implement login flow
        # self.client.post("/accounts/login/", {"username": "...", "password": "..."})
    
    @tag('mutation', 'volume')
    @task(3)
    def save_volume_pekerjaan(self):
        """Save volume pekerjaan - tests optimistic locking"""
        if not self.MUTATIONS_ENABLED:
            return
        
        project_id = random.choice(self.project_ids)
        pekerjaan_id = random.randint(1, 20)
        volume = round(random.uniform(1, 100), 2)
        
        with self.client.post(
            f"/detail_project/api/project/{project_id}/volume-pekerjaan/save/",
            name="/api/project/[id]/volume-pekerjaan/save/",
            json={"items": [{"pekerjaan_id": pekerjaan_id, "kuantitas": volume}]},
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @tag('mutation', 'parameters')
    @task(2)
    def sync_parameters(self):
        """Sync project parameters - tests concurrent parameter updates"""
        if not self.MUTATIONS_ENABLED:
            return
        
        project_id = random.choice(self.project_ids)
        
        with self.client.post(
            f"/detail_project/api/project/{project_id}/parameters/sync/",
            name="/api/project/[id]/parameters/sync/",
            json={"params": [{"name": f"test_param_{random.randint(1,10)}", "value": "10.5"}]},
            catch_response=True
        ) as response:
            if response.status_code in [200, 400]:  # 400 might be validation error
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @tag('mutation', 'formula')
    @task(2)
    def save_volume_formula(self):
        """Save volume formula - tests formula persistence"""
        if not self.MUTATIONS_ENABLED:
            return
        
        project_id = random.choice(self.project_ids)
        
        with self.client.post(
            f"/detail_project/api/project/{project_id}/volume/formula/",
            name="/api/project/[id]/volume/formula/",
            json={"items": [{"pekerjaan_id": 1, "raw": "=10*5", "is_fx": True}]},
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")


# ============================================================================
# Custom Events and Hooks
# ============================================================================

from locust import events

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when the test starts"""
    print("=" * 60)
    print("LOAD TEST STARTED")
    print("=" * 60)
    print("\nTarget: Detail Project Application")
    print("User Classes:")
    print("  - BrowsingUser (55%): Page browsing")
    print("  - APIUser (27%): API calls")
    print("  - HeavyUser (9%): Export operations")
    print("  - MutationUser (9%): POST mutations (disabled by default)")
    print("\nEndpoints Being Tested:")
    print("  ⚡ Critical: /jadwal-pekerjaan/, /api/rekap/, /api/chart-data/")
    print("  📦 Templates: /api/templates/export/ (v2.2)")
    print("  📊 Volume: /api/volume/formula-state/, /api/parameters/")
    print("  📑 Export: PDF, Excel, CSV")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when the test stops"""
    print("\n" + "=" * 60)
    print("LOAD TEST COMPLETED")
    print("=" * 60)
    
    if environment.stats.total.num_failures > 0:
        failure_rate = (environment.stats.total.num_failures / 
                       environment.stats.total.num_requests) * 100
        print(f"\n⚠️  Failure Rate: {failure_rate:.2f}%")
        if failure_rate > 5:
            print("   WARNING: High failure rate detected!")
    
    print(f"\nTotal Requests: {environment.stats.total.num_requests}")
    print(f"Total Failures: {environment.stats.total.num_failures}")
    print(f"Average Response Time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"P95 Response Time: {environment.stats.total.get_response_time_percentile(0.95):.2f}ms")
    print("=" * 60)
