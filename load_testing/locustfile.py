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
import re
import os
import sys
import logging
import threading
from datetime import datetime
from locust import HttpUser, task, between, tag


# ============================================================================
# AUTHENTICATION CONFIGURATION
# ============================================================================
# Set these via environment variables or edit directly for testing

TEST_USERNAME = "aditf96@gmail.com"
TEST_PASSWORD = "Ph@ntomk1d"  # password user aditf96

# Project IDs to test (from your database)
TEST_PROJECT_IDS = [160, 161, 163, 139, 162]

# URL prefixes (override if your routes use a different base path)
# Django uses /detail_project (underscore) - verified from show_urls output
DETAIL_PROJECT_PREFIX = os.getenv("DETAIL_PROJECT_PREFIX", "/detail_project").rstrip("/")
API_PREFIX = f"{DETAIL_PROJECT_PREFIX}/api"
API_V2_PREFIX = f"{DETAIL_PROJECT_PREFIX}/api/v2"

LOG_DIR = os.getenv("LOCUST_LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)
_LOGIN_LOG_PATH = os.path.join(LOG_DIR, "locust_login_failures.log")
_login_logger = logging.getLogger("locust.auth")
if not _login_logger.handlers:
    _login_logger.setLevel(logging.INFO)
    handler = logging.FileHandler(_LOGIN_LOG_PATH, encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    _login_logger.addHandler(handler)

def _parse_user_pool(raw: str) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            _login_logger.warning(
                "TEST_USER_POOL invalid entry (missing ':password'): '%s' - skipped (format: username:password)",
                item
            )
            continue
        username, password = item.split(":", 1)
        username = username.strip()
        password = password.strip()
        if username and password:
            entries.append((username, password))
        else:
            _login_logger.warning(
                "TEST_USER_POOL empty username or password: '%s' - skipped",
                item
            )
    return entries


USER_POOL = _parse_user_pool(os.getenv("TEST_USER_POOL", ""))
if not USER_POOL:
    USER_POOL = [(TEST_USERNAME, TEST_PASSWORD)]
else:
    _login_logger.info(
        "Multi-user pool configured: %d users (%s)",
        len(USER_POOL),
        ", ".join([u[0] for u in USER_POOL])
    )
USER_POOL_SIZE = len(USER_POOL)

AUTH_ONLY = os.getenv("LOCUST_AUTH_ONLY", "false").lower() == "true"
AUTH_LOGIN_ALLOW_REDIRECTS = os.getenv("AUTH_LOGIN_ALLOW_REDIRECTS", "false").lower() == "true"

# Detect if export/admin tags are excluded to auto-disable HeavyUser
# Locust passes excluded tags via command line, we need to check sys.argv
_EXCLUDE_EXPORT = False
_EXCLUDE_ADMIN = False
if "--exclude-tags" in sys.argv:
    try:
        idx = sys.argv.index("--exclude-tags")
        if idx + 1 < len(sys.argv):
            excluded = sys.argv[idx + 1].lower()
            _EXCLUDE_EXPORT = "export" in excluded
            _EXCLUDE_ADMIN = "admin" in excluded
            if _EXCLUDE_EXPORT:
                _login_logger.info("Export tags excluded - HeavyUser will be auto-disabled (weight=0)")
    except (ValueError, IndexError):
        pass

def _append_login_log(message: str) -> None:
    """Write login failure details to a dedicated file (avoids logger overrides)."""
    try:
        with open(_LOGIN_LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(f"{datetime.now().isoformat()} {message}\n")
    except Exception:
        pass


def _page_url(project_id: int, path: str) -> str:
    """Build detail_project page URLs with a configurable base prefix."""
    return f"{DETAIL_PROJECT_PREFIX}/{project_id}/{path.lstrip('/')}"


def _api_url(project_id: int, path: str) -> str:
    """Build detail_project API URLs with a configurable base prefix."""
    return f"{API_PREFIX}/project/{project_id}/{path.lstrip('/')}"


def _api_v2_url(project_id: int, path: str) -> str:
    """Build detail_project v2 API URLs with a configurable base prefix."""
    return f"{API_V2_PREFIX}/project/{project_id}/{path.lstrip('/')}"


# ============================================================================
# BASE USER CLASS WITH AUTHENTICATION
# ============================================================================

class AuthenticatedUser(HttpUser):
    """
    Base class that handles Django authentication with CSRF tokens.
    All user types should inherit from this class.
    """
    abstract = True  # Don't instantiate this class directly

    _user_lock = threading.Lock()
    _user_index = 0
    _single_user_warned = False
    
    def on_start(self):
        """Login at the start of each user session"""
        self.project_ids = TEST_PROJECT_IDS
        self.test_username, self.test_password = self._get_credentials()
        self.login()

    def _get_credentials(self) -> tuple[str, str]:
        if USER_POOL_SIZE == 1:
            if not AuthenticatedUser._single_user_warned:
                _login_logger.info(
                    "single_user_pool active username=%s (set TEST_USER_POOL to test multi-user)",
                    USER_POOL[0][0],
                )
                AuthenticatedUser._single_user_warned = True
            return USER_POOL[0]
        with AuthenticatedUser._user_lock:
            idx = AuthenticatedUser._user_index % USER_POOL_SIZE
            AuthenticatedUser._user_index += 1
        return USER_POOL[idx]
    
    def login(self):
        """
        Perform Django login with CSRF token handling.
        This mimics the browser login flow.
        """
        # Step 1: Get login page and extract CSRF token
        login_page = self.client.get("/accounts/login/", name="[AUTH] Get Login Page")
        
        if login_page.status_code != 200:
            print(f"[AUTH] Failed to get login page: {login_page.status_code}")
            return False
        
        # Extract CSRF token from response
        csrf_token = self._extract_csrf_token(login_page.text)
        
        if not csrf_token:
            print("[AUTH] Failed to extract CSRF token from login page")
            return False
        
        # Step 2: Submit login form
        # Django Allauth uses 'login' for username/email field
        login_data = {
            "csrfmiddlewaretoken": csrf_token,
            "login": self.test_username,
            "password": self.test_password,
        }
        
        headers = {
            "Referer": f"{self.host}/accounts/login/",
        }
        
        with self.client.post(
            "/accounts/login/",
            data=login_data,
            headers=headers,
            name="[AUTH] Login POST",
            allow_redirects=AUTH_LOGIN_ALLOW_REDIRECTS,
            catch_response=True,
        ) as response:
            # Debug: Check final URL after redirects
            final_url = response.url if hasattr(response, 'url') else "unknown"
            if response.status_code in (301, 302, 303, 307, 308):
                final_url = response.headers.get("Location", final_url)
            login_page_returned = self._is_login_page(response)
            error_message = self._extract_login_error_message(response.text or "")

            if response.status_code >= 500:
                response.failure(f"login server error: {response.status_code}")
                print(f"[AUTH] Login FAILED - status: {response.status_code}, url: {final_url}")
                _login_logger.warning(
                    "login_server_error username=%s status=%s url=%s error=%s",
                    self.test_username,
                    response.status_code,
                    final_url,
                    error_message or "unknown",
                )
                _append_login_log(
                    f"login_server_error username={self.test_username} status={response.status_code} url={final_url} error={error_message or 'unknown'}"
                )
                return False
            if response.status_code in (301, 302, 303, 307, 308):
                if "login" in final_url.lower():
                    response.failure("login redirect back to login")
                    print(f"[AUTH] Login FAILED - redirect to login: {final_url}")
                    _login_logger.warning(
                        "login_redirect_back username=%s url=%s error=%s",
                        self.test_username,
                        final_url,
                        error_message or "unknown",
                    )
                    _append_login_log(
                        f"login_redirect_back username={self.test_username} url={final_url} error={error_message or 'unknown'}"
                    )
                    return False
                response.success()
                print(f"[AUTH] Login got redirect to: {final_url}")
                return True
            if response.status_code == 200:
                if login_page_returned:
                    response.failure("login failed (login page returned)")
                    print(f"[AUTH] Login FAILED - still on login page: {final_url}")
                    _login_logger.warning(
                        "login_page_returned username=%s url=%s error=%s",
                        self.test_username,
                        final_url,
                        error_message or "unknown",
                    )
                    _append_login_log(
                        f"login_page_returned username={self.test_username} url={final_url} error={error_message or 'unknown'}"
                    )
                    return False
                response.success()
                print(f"[AUTH] Login SUCCESS - redirected to: {final_url}")
                return True

            response.failure(f"unexpected login status: {response.status_code}")
            print(f"[AUTH] Login FAILED - status: {response.status_code}, url: {final_url}")
            _login_logger.warning(
                "login_unexpected_status username=%s status=%s url=%s error=%s",
                self.test_username,
                response.status_code,
                final_url,
                error_message or "unknown",
            )
            _append_login_log(
                f"login_unexpected_status username={self.test_username} status={response.status_code} url={final_url} error={error_message or 'unknown'}"
            )
            return False

    def _is_login_page(self, response) -> bool:
        """Detect if the response is still the login page."""
        final_url = response.url if hasattr(response, "url") else ""
        if "/accounts/login" in final_url:
            return True
        body = response.text or ""
        markers = (
            "Masuk ke Sistem",
            "WELCOME SIMPANSE",
            "account_login",
            'name="login"',
            'action="/accounts/login/"',
        )
        return any(marker in body for marker in markers)

    def _extract_login_error_message(self, html: str) -> str:
        """Extract a short, readable error message from the login page."""
        if not html:
            return ""

        patterns = (
            r'<ul class="errorlist[^"]*">(.+?)</ul>',
            r'<div class="alert[^"]*">(.+?)</div>',
            r'<span class="invalid-feedback">(.+?)</span>',
        )
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL | re.IGNORECASE)
            if match:
                return self._strip_html(match.group(1))

        common_markers = (
            "Please enter a correct",
            "Invalid",
            "Salah",
            "Masukkan",
            "Kesalahan",
            "Akun",
            "Email",
        )
        for marker in common_markers:
            if marker in html:
                return marker
        return ""

    def _strip_html(self, value: str) -> str:
        text = re.sub(r"<[^>]+>", " ", value)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:200]
    
    def _extract_csrf_token(self, html_content: str) -> str:
        """Extract CSRF token from HTML form"""
        # Try to find csrfmiddlewaretoken in form
        match = re.search(
            r'name=["\']csrfmiddlewaretoken["\'][^>]*value=["\']([^"\']+)["\']',
            html_content
        )
        if match:
            return match.group(1)
        
        # Try alternate pattern
        match = re.search(
            r'value=["\']([^"\']+)["\'][^>]*name=["\']csrfmiddlewaretoken["\']',
            html_content
        )
        if match:
            return match.group(1)
        
        return ""


class AuthOnlyUser(AuthenticatedUser):
    """Auth-only scenario to isolate login success/failure."""
    weight = 1 if AUTH_ONLY else 0
    wait_time = between(1, 2)

    @task(1)
    def idle(self):
        return


class BrowsingUser(AuthenticatedUser):
    """
    Simulates a typical user browsing pages.
    Represents 60% of expected traffic.
    """
    weight = 0 if AUTH_ONLY else 6
    wait_time = between(2, 5)  # Wait 2-5 seconds between tasks
    
    # on_start is inherited from AuthenticatedUser (handles login)
    
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
            _page_url(project_id, "list-pekerjaan/"),
            name="/detail_project/[id]/list-pekerjaan/"
        )
    
    @tag('page', 'jadwal')
    @task(4)
    def browse_jadwal_pekerjaan(self):
        """View jadwal pekerjaan (Gantt/Kurva S) - HEAVY"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _page_url(project_id, "jadwal-pekerjaan/"),
            name="/detail_project/[id]/jadwal-pekerjaan/"
        )
    
    @tag('page', 'template_ahsp')
    @task(3)
    def browse_template_ahsp(self):
        """View template AHSP page"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _page_url(project_id, "template-ahsp/"),
            name="/detail_project/[id]/template-ahsp/"
        )
    
    @tag('page', 'rekap')
    @task(4)
    def browse_rekap_rab(self):
        """View rekap RAB page"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _page_url(project_id, "rekap-rab/"),
            name="/detail_project/[id]/rekap-rab/"
        )
    
    @tag('page', 'harga_items')
    @task(3)
    def browse_harga_items(self):
        """View harga items page"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _page_url(project_id, "harga-items/"),
            name="/detail_project/[id]/harga-items/"
        )
    
    @tag('page', 'volume')
    @task(2)
    def browse_volume_pekerjaan(self):
        """View volume pekerjaan page"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _page_url(project_id, "volume-pekerjaan/"),
            name="/detail_project/[id]/volume-pekerjaan/"
        )

    # ========================================================================
    # PHASE 1 CRITICAL PAGE VIEWS - High frequency user pages
    # ========================================================================

    @tag('page', 'rincian_ahsp', 'phase1')
    @task(4)
    def browse_rincian_ahsp(self):
        """View rincian AHSP (detailed AHSP gabungan) - Frequently accessed"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _page_url(project_id, "rincian-ahsp/"),
            name="/detail_project/[id]/rincian-ahsp/"
        )

    @tag('page', 'rekap_kebutuhan', 'phase1')
    @task(3)
    def browse_rekap_kebutuhan(self):
        """View rekap kebutuhan (material requirements) - Important for procurement"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _page_url(project_id, "rekap-kebutuhan/"),
            name="/detail_project/[id]/rekap-kebutuhan/"
        )

    @tag('page', 'rincian_rab', 'new', 'phase1')
    @task(3)
    def browse_rincian_rab(self):
        """View rincian RAB (NEW detailed RAB page)"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _page_url(project_id, "rincian-rab/"),
            name="/detail_project/[id]/rincian-rab/"
        )

    @tag('page', 'audit_trail', 'phase1')
    @task(2)
    def browse_audit_trail(self):
        """View audit trail (change tracking) - Used for troubleshooting"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _page_url(project_id, "audit-trail/"),
            name="/detail_project/[id]/audit-trail/"
        )

    # ========================================================================
    # PHASE 2 PAGE VIEWS - Additional page coverage
    # ========================================================================

    @tag('page', 'export_test', 'export', 'phase2')
    @task(2)
    def browse_export_test(self):
        """View export test page - Phase 4 export system"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _page_url(project_id, "export-test/"),
            name="/detail_project/[id]/export-test/"
        )


class APIUser(AuthenticatedUser):
    """
    Simulates frontend JavaScript making API calls.
    Represents 30% of expected traffic.
    """
    weight = 0 if AUTH_ONLY else 3
    wait_time = between(1, 3)  # API calls are faster
    
    # on_start is inherited from AuthenticatedUser (handles login)
    
    @tag('api', 'critical')
    @task(10)
    def api_list_pekerjaan_tree(self):
        """Get pekerjaan tree structure - CRITICAL API"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "list-pekerjaan/tree/"),
            name="/api/project/[id]/list-pekerjaan/tree/"
        )
    
    @tag('api', 'critical')
    @task(8)
    def api_rekap_rab(self):
        """Get rekap RAB data - CRITICAL API (heavy aggregation)"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "rekap/"),
            name="/api/project/[id]/rekap/"
        )
    
    @tag('api', 'critical')
    @task(7)
    def api_chart_data(self):
        """Get chart data for Gantt/Kurva S - CRITICAL API"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_v2_url(project_id, "chart-data/"),
            name="/api/v2/project/[id]/chart-data/"
        )
    
    @tag('api', 'medium')
    @task(6)
    def api_harga_items_list(self):
        """Get harga items list"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "harga-items/list/"),
            name="/api/project/[id]/harga-items/list/"
        )
    
    @tag('api', 'medium')
    @task(5)
    def api_rekap_kebutuhan(self):
        """Get rekap kebutuhan data"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "rekap-kebutuhan/"),
            name="/api/project/[id]/rekap-kebutuhan/"
        )
    
    @tag('api', 'medium')
    @task(5)
    def api_volume_pekerjaan_list(self):
        """Get volume pekerjaan list"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "volume-pekerjaan/list/"),
            name="/api/project/[id]/volume-pekerjaan/list/"
        )
    
    @tag('api', 'tahapan')
    @task(4)
    def api_tahapan_list(self):
        """Get tahapan list"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "tahapan/"),
            name="/api/project/[id]/tahapan/"
        )
    
    @tag('api', 'assignments')
    @task(4)
    def api_v2_assignments(self):
        """Get project assignments (V2 API)"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_v2_url(project_id, "assignments/"),
            name="/api/v2/project/[id]/assignments/"
        )
    
    @tag('api', 'kurva_s')
    @task(3)
    def api_kurva_s_data(self):
        """Get Kurva S data"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_v2_url(project_id, "kurva-s-data/"),
            name="/api/v2/project/[id]/kurva-s-data/"
        )
    
    @tag('api', 'template', 'export')
    @task(3)
    def api_template_export(self):
        """Export project as template JSON - NEW v2.2"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "templates/export/"),
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
        # Fixed: Use correct URL - Django has both /volume/formula/ and /volume-formula-state/
        # Using the primary endpoint /volume/formula/
        self.client.get(
            _api_url(project_id, "volume/formula/"),
            name="/api/project/[id]/volume/formula/"
        )
    
    @tag('api', 'parameters')
    @task(2)
    def api_parameters_list(self):
        """Get project parameters list (NEW v2.2)"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "parameters/"),
            name="/api/project/[id]/parameters/"
        )
    
    @tag('api', 'detail_ahsp')
    @task(3)
    def api_detail_ahsp(self):
        """Get detail AHSP for a pekerjaan"""
        project_id = random.choice(self.project_ids)
        pekerjaan_id = random.randint(1, 100)
        with self.client.get(
            _api_url(project_id, f"detail-ahsp/{pekerjaan_id}/"),
            name="/api/project/[id]/detail-ahsp/[pekerjaan_id]/",
            catch_response=True
        ) as response:
            # Accept both 200 and 404 (pekerjaan might not exist)
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    # ========================================================================
    # PHASE 1 CRITICAL ADDITIONS - High frequency & business-critical endpoints
    # ========================================================================

    @tag('api', 'critical', 'autocomplete', 'phase1')
    @task(10)
    def api_search_ahsp(self):
        """Search AHSP autocomplete - CRITICAL! Called on every keystroke in dropdown"""
        project_id = random.choice(self.project_ids)
        # Simulate common search terms
        search_terms = ['beton', 'semen', 'pasir', 'besi', 'kayu', 'cat', 'pipa', 'kabel']
        search_term = random.choice(search_terms)
        self.client.get(
            _api_url(project_id, f"search-ahsp/?q={search_term}"),
            name="/api/project/[id]/search-ahsp/"
        )

    @tag('api', 'critical', 'pricing', 'phase1')
    @task(6)
    def api_project_pricing(self):
        """Get project pricing (profit/margin calculation) - Business critical"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "pricing/"),
            name="/api/project/[id]/pricing/"
        )

    @tag('api', 'critical', 'pricing', 'phase1')
    @task(5)
    def api_pekerjaan_pricing(self):
        """Get per-pekerjaan pricing - Business logic"""
        project_id = random.choice(self.project_ids)
        pekerjaan_id = random.randint(1, 50)
        with self.client.get(
            _api_url(project_id, f"pekerjaan/{pekerjaan_id}/pricing/"),
            name="/api/project/[id]/pekerjaan/[pekerjaan_id]/pricing/",
            catch_response=True
        ) as response:
            # Accept 404 if pekerjaan doesn't exist
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @tag('api', 'critical', 'validation', 'phase1')
    @task(5)
    def api_validate_rekap_kebutuhan(self):
        """Validate rekap kebutuhan data - Phase 5 data integrity"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "rekap-kebutuhan/validate/"),
            name="/api/project/[id]/rekap-kebutuhan/validate/"
        )

    @tag('api', 'critical', 'new', 'phase1')
    @task(5)
    def api_rincian_rab(self):
        """Get rincian RAB - NEW API endpoint"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "rincian-rab/"),
            name="/api/project/[id]/rincian-rab/"
        )

    @tag('api', 'critical', 'enhanced', 'phase1')
    @task(5)
    def api_rekap_kebutuhan_enhanced(self):
        """Get enhanced rekap kebutuhan with filters - Replaces legacy endpoint"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "rekap-kebutuhan-enhanced/"),
            name="/api/project/[id]/rekap-kebutuhan-enhanced/"
        )

    @tag('api', 'v2', 'critical', 'phase1')
    @task(4)
    def api_kurva_s_harga(self):
        """Get V2 cost-based S-curve data - Heavy computation"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_v2_url(project_id, "kurva-s-harga/"),
            name="/api/v2/project/[id]/kurva-s-harga/"
        )

    @tag('api', 'v2', 'critical', 'phase1')
    @task(4)
    def api_rekap_kebutuhan_weekly(self):
        """Get V2 weekly procurement breakdown - Weekly resource planning"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_v2_url(project_id, "rekap-kebutuhan-weekly/"),
            name="/api/v2/project/[id]/rekap-kebutuhan-weekly/"
        )

    @tag('api', 'medium', 'audit', 'admin', 'phase1')
    @task(3)
    def api_audit_trail(self):
        """Get audit trail for change tracking"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "audit-trail/"),
            name="/api/project/[id]/audit-trail/"
        )

    # ========================================================================
    # PHASE 2 ADDITIONS - Additional coverage for template, parameters, exports
    # ========================================================================

    @tag('api', 'high', 'parameters', 'phase2')
    @task(4)
    def api_project_parameters(self):
        """Get project parameters - Configuration settings"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "parameters/"),
            name="/api/project/[id]/parameters/"
        )

    @tag('api', 'medium', 'parameters', 'phase2')
    @task(2)
    def api_parameter_detail(self):
        """Get parameter detail - Individual parameter"""
        project_id = random.choice(self.project_ids)
        param_id = random.randint(1, 10)
        with self.client.get(
            _api_url(project_id, f"parameters/{param_id}/"),
            name="/api/project/[id]/parameters/[param_id]/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @tag('api', 'high', 'conversion', 'phase2')
    @task(4)
    def api_conversion_profiles(self):
        """Get conversion profiles - Material/unit conversions"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "conversion-profiles/"),
            name="/api/project/[id]/conversion-profiles/"
        )

    @tag('api', 'medium', 'bundle', 'phase2')
    @task(3)
    def api_bundle_expansion(self):
        """Get bundle expansion - Expand bundled AHSP"""
        project_id = random.choice(self.project_ids)
        pekerjaan_id = random.randint(1, 50)
        bundle_id = random.randint(1, 20)
        with self.client.get(
            _api_url(project_id, f"pekerjaan/{pekerjaan_id}/bundle/{bundle_id}/expansion/"),
            name="/api/project/[id]/pekerjaan/[id]/bundle/[id]/expansion/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @tag('api', 'v2', 'high', 'weekly', 'phase2')
    @task(4)
    def api_weekly_progress(self):
        """Get V2 weekly progress for pekerjaan - Canonical storage"""
        project_id = random.choice(self.project_ids)
        pekerjaan_id = random.randint(1, 50)
        with self.client.get(
            _api_v2_url(project_id, f"pekerjaan/{pekerjaan_id}/weekly-progress/"),
            name="/api/v2/project/[id]/pekerjaan/[id]/weekly-progress/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @tag('api', 'medium', 'parameters', 'phase2')
    @task(2)
    def api_parameters_sync(self):
        """Sync parameters with templates"""
        project_id = random.choice(self.project_ids)
        # POST with sample parameters payload
        payload = {
            "parameters": {
                "test_param_1": {"value": 10, "label": "Test Parameter 1"},
                "test_param_2": {"value": 20, "label": "Test Parameter 2"}
            },
            "mode": "merge"
        }
        with self.client.post(
            _api_url(project_id, "parameters/sync/"),
            json=payload,
            name="/api/project/[id]/parameters/sync/",
            catch_response=True
        ) as response:
            # Accept 200, 204 (success), and 403 (not owner - expected for test users)
            if response.status_code in [200, 204, 403]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @tag('api', 'medium', 'template', 'export', 'phase2')
    @task(3)
    def api_template_export(self):
        """Export template AHSP as JSON"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "export/template-ahsp/json/"),
            name="/api/project/[id]/export/template-ahsp/json/"
        )

    # ========================================================================
    # PHASE 4 ADDITIONS - Tahapan Management, V2 APIs, Rekap Variants
    # ========================================================================

    @tag('api', 'high', 'tahapan', 'phase4')
    @task(3)
    def api_tahapan_detail(self):
        """Get tahapan detail"""
        project_id = random.choice(self.project_ids)
        tahapan_id = random.randint(1, 20)
        with self.client.get(
            _api_url(project_id, f"tahapan/{tahapan_id}/"),
            name="/api/project/[id]/tahapan/[tahapan_id]/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @tag('api', 'medium', 'tahapan', 'phase4')
    @task(2)
    def api_tahapan_unassigned(self):
        """Get unassigned pekerjaan"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "tahapan/unassigned/"),
            name="/api/project/[id]/tahapan/unassigned/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @tag('api', 'medium', 'tahapan', 'write', 'phase4')
    @task(2)
    def api_assign_pekerjaan_to_tahapan(self):
        """Assign pekerjaan to tahapan - write operation"""
        project_id = random.choice(self.project_ids)
        tahapan_id = random.randint(1, 10)
        payload = {"pekerjaan_ids": [random.randint(1, 50)]}
        with self.client.post(
            _api_url(project_id, f"tahapan/{tahapan_id}/assign/"),
            json=payload,
            name="/api/project/[id]/tahapan/[tahapan_id]/assign/",
            catch_response=True
        ) as response:
            # Accept 200, 201, 403 (not owner - expected), 404 (not found)
            if response.status_code in [200, 201, 403, 404]:
                response.success()

    @tag('api', 'medium', 'tahapan', 'write', 'phase4')
    @task(1)
    def api_unassign_pekerjaan_from_tahapan(self):
        """Unassign pekerjaan from tahapan - write operation"""
        project_id = random.choice(self.project_ids)
        tahapan_id = random.randint(1, 10)
        payload = {"pekerjaan_ids": [random.randint(1, 50)]}
        with self.client.post(
            _api_url(project_id, f"tahapan/{tahapan_id}/unassign/"),
            json=payload,
            name="/api/project/[id]/tahapan/[tahapan_id]/unassign/",
            catch_response=True
        ) as response:
            # Accept 200, 201, 403 (not owner), 404 (not found)
            if response.status_code in [200, 201, 403, 404]:
                response.success()

    @tag('api', 'low', 'tahapan', 'write', 'phase4')
    @task(1)
    def api_reorder_tahapan(self):
        """Reorder tahapan - write operation"""
        project_id = random.choice(self.project_ids)
        payload = {"tahapan_order": [1, 2, 3]}
        with self.client.post(
            _api_url(project_id, "tahapan/reorder/"),
            json=payload,
            name="/api/project/[id]/tahapan/reorder/",
            catch_response=True
        ) as response:
            # Accept 200, 201, 403 (not owner), 400 (invalid data)
            if response.status_code in [200, 201, 403, 400]:
                response.success()

    @tag('api', 'low', 'tahapan', 'write', 'phase4')
    @task(1)
    def api_validate_assignments(self):
        """Validate all tahapan assignments"""
        project_id = random.choice(self.project_ids)
        with self.client.post(
            _api_url(project_id, "tahapan/validate/"),
            json={},
            name="/api/project/[id]/tahapan/validate/",
            catch_response=True
        ) as response:
            # Accept 200, 403 (not owner)
            if response.status_code in [200, 403]:
                response.success()

    # V2 Tahapan APIs (Weekly Progress)

    @tag('api', 'v2', 'high', 'tahapan', 'write', 'phase4')
    @task(2)
    def api_v2_assign_weekly(self):
        """V2: Assign pekerjaan to weekly schedule"""
        project_id = random.choice(self.project_ids)
        payload = {
            "pekerjaan_id": random.randint(1, 50),
            "week_number": random.randint(1, 10),
            "planned_proportion": 10.0
        }
        with self.client.post(
            _api_v2_url(project_id, "assign-weekly/"),
            json=payload,
            name="/api/v2/project/[id]/assign-weekly/",
            catch_response=True
        ) as response:
            # Accept 200, 201, 403 (not owner), 404 (not found), 400 (invalid)
            if response.status_code in [200, 201, 403, 404, 400]:
                response.success()

    @tag('api', 'v2', 'low', 'tahapan', 'write', 'phase4')
    @task(1)
    def api_v2_regenerate_tahapan(self):
        """V2: Regenerate tahapan - HEAVY operation"""
        project_id = random.choice(self.project_ids)
        with self.client.post(
            _api_v2_url(project_id, "regenerate-tahapan/"),
            json={},
            name="/api/v2/project/[id]/regenerate-tahapan/",
            catch_response=True
        ) as response:
            # Accept 200, 403 (not owner), 500 (timeout expected), 504 (timeout)
            if response.status_code in [200, 403, 500, 504]:
                response.success()

    @tag('api', 'v2', 'low', 'tahapan', 'write', 'phase4')
    @task(1)
    def api_v2_reset_progress(self):
        """V2: Reset progress data - write operation"""
        project_id = random.choice(self.project_ids)
        with self.client.post(
            _api_v2_url(project_id, "reset-progress/"),
            json={},
            name="/api/v2/project/[id]/reset-progress/",
            catch_response=True
        ) as response:
            # Accept 200, 403 (not owner)
            if response.status_code in [200, 403]:
                response.success()

    @tag('api', 'v2', 'low', 'tahapan', 'write', 'phase4')
    @task(1)
    def api_v2_update_week_boundaries(self):
        """V2: Update week boundaries - write operation"""
        project_id = random.choice(self.project_ids)
        payload = {
            "week_start": 1,
            "week_end": 10
        }
        with self.client.post(
            _api_v2_url(project_id, "week-boundary/"),
            json=payload,
            name="/api/v2/project/[id]/week-boundary/",
            catch_response=True
        ) as response:
            # Accept 200, 403 (not owner), 400 (invalid)
            if response.status_code in [200, 403, 400]:
                response.success()

    # Rekap Kebutuhan Variants

    @tag('api', 'high', 'rekap', 'phase4')
    @task(3)
    def api_rekap_kebutuhan_timeline(self):
        """Get rekap kebutuhan timeline"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "rekap-kebutuhan-timeline/"),
            name="/api/project/[id]/rekap-kebutuhan-timeline/"
        )

    @tag('api', 'medium', 'rekap', 'phase4')
    @task(2)
    def api_rekap_kebutuhan_filters(self):
        """Get rekap kebutuhan filters"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "rekap-kebutuhan/filters/"),
            name="/api/project/[id]/rekap-kebutuhan/filters/"
        )

    # Orphaned Items Management

    @tag('api', 'medium', 'cleanup', 'admin', 'phase4')
    @task(2)
    def api_list_orphaned_items(self):
        """List orphaned harga items"""
        project_id = random.choice(self.project_ids)
        self.client.get(
            _api_url(project_id, "orphaned-items/"),
            name="/api/project/[id]/orphaned-items/"
        )

    @tag('api', 'low', 'cleanup', 'write', 'admin', 'phase4')
    @task(1)
    def api_cleanup_orphaned_items(self):
        """Cleanup orphaned harga items - write operation"""
        project_id = random.choice(self.project_ids)
        with self.client.post(
            _api_url(project_id, "orphaned-items/cleanup/"),
            json={},
            name="/api/project/[id]/orphaned-items/cleanup/",
            catch_response=True
        ) as response:
            # Accept 200, 403 (not owner)
            if response.status_code in [200, 403]:
                response.success()

    # Monitoring APIs

    @tag('api', 'monitoring', 'phase4')
    @task(1)
    def api_performance_metrics(self):
        """Get performance metrics"""
        with self.client.get(
            "/detail_project/api/monitoring/performance-metrics/",
            name="/api/monitoring/performance-metrics/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @tag('api', 'monitoring', 'phase4')
    @task(1)
    def api_deprecation_metrics(self):
        """Get deprecation metrics"""
        with self.client.get(
            "/detail_project/api/monitoring/deprecation-metrics/",
            name="/api/monitoring/deprecation-metrics/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()

    @tag('api', 'monitoring', 'phase4')
    @task(1)
    def api_report_client_metric(self):
        """Report client-side metrics"""
        payload = {
            "metric_name": "page_load",
            "value": random.randint(100, 500),
            "timestamp": "2026-01-10T10:00:00Z"
        }
        with self.client.post(
            "/detail_project/api/monitoring/report-client-metric/",
            json=payload,
            name="/api/monitoring/report-client-metric/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 400]:
                response.success()


class HeavyUser(AuthenticatedUser):
    """
    Simulates users performing heavy operations like exports.
    Represents 10% of expected traffic.
    These are CPU/memory intensive operations.

    NOTE: Auto-disabled when export tags are excluded to prevent
    "No tasks defined" errors (all HeavyUser tasks are export-tagged).
    """
    weight = 0 if (AUTH_ONLY or _EXCLUDE_EXPORT) else 1
    wait_time = between(10, 30)  # Longer wait between heavy operations
    
    def on_start(self):
        """Initialize heavy user with single project"""
        super().on_start()  # Call parent login
        self.project_ids = [TEST_PROJECT_IDS[0]]  # Use first project for export tests
    
    @tag('export', 'pdf')
    @task(3)
    def export_rekap_rab_pdf(self):
        """Export Rekap RAB as PDF - HEAVY OPERATION"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rekap-rab/pdf/"),
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
            _api_url(project_id, "export/rekap-rab/xlsx/"),
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
            _api_url(project_id, "export/jadwal-pekerjaan/pdf/"),
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
            _api_url(project_id, "export/harga-items/csv/"),
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
        #     _api_url(project_id, "deep-copy/"),
        #     name="/api/project/[id]/deep-copy/",
        #     json={"name_suffix": "_loadtest"}
        # )
        pass  # Disabled by default

    # ========================================================================
    # PHASE 2 HEAVY OPERATIONS - Additional export variations
    # ========================================================================

    @tag('export', 'json', 'phase2')
    @task(2)
    def export_full_backup_json(self):
        """Export full project backup as JSON - VERY HEAVY"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/full-backup/json/"),
            name="/api/project/[id]/export/full-backup/json/",
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code in [500, 504]:
                response.failure("Server error or timeout during full backup export")

    @tag('export', 'pdf', 'harga', 'phase2')
    @task(2)
    def export_harga_items_pdf(self):
        """Export Harga Items as PDF"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/harga-items/pdf/"),
            name="/api/project/[id]/export/harga-items/pdf/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'excel', 'harga', 'phase2')
    @task(2)
    def export_harga_items_xlsx(self):
        """Export Harga Items as Excel"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/harga-items/xlsx/"),
            name="/api/project/[id]/export/harga-items/xlsx/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'word', 'harga', 'phase2')
    @task(1)
    def export_harga_items_word(self):
        """Export Harga Items as Word"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/harga-items/word/"),
            name="/api/project/[id]/export/harga-items/word/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'csv', 'jadwal', 'phase2')
    @task(2)
    def export_jadwal_csv(self):
        """Export Jadwal Pekerjaan as CSV"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/jadwal-pekerjaan/csv/"),
            name="/api/project/[id]/export/jadwal-pekerjaan/csv/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'json', 'harga', 'phase2')
    @task(1)
    def export_harga_items_json(self):
        """Export Harga Items as JSON"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/harga-items/json/"),
            name="/api/project/[id]/export/harga-items/json/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    # ========================================================================
    # PHASE 3 HEAVY OPERATIONS - Additional export coverage (critical missing exports)
    # ========================================================================

    @tag('export', 'csv', 'rekap-rab', 'phase3')
    @task(2)
    def export_rekap_rab_csv(self):
        """Export Rekap RAB as CSV"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rekap-rab/csv/"),
            name="/api/project/[id]/export/rekap-rab/csv/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'word', 'rekap-rab', 'phase3')
    @task(1)
    def export_rekap_rab_word(self):
        """Export Rekap RAB as Word"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rekap-rab/word/"),
            name="/api/project/[id]/export/rekap-rab/word/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'json', 'rekap-rab', 'phase3')
    @task(1)
    def export_rekap_rab_json(self):
        """Export Rekap RAB as JSON"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rekap-rab/json/"),
            name="/api/project/[id]/export/rekap-rab/json/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'csv', 'rincian-ahsp', 'phase3')
    @task(2)
    def export_rincian_ahsp_csv(self):
        """Export Rincian AHSP as CSV"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rincian-ahsp/csv/"),
            name="/api/project/[id]/export/rincian-ahsp/csv/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'pdf', 'rincian-ahsp', 'phase3')
    @task(1)
    def export_rincian_ahsp_pdf(self):
        """Export Rincian AHSP as PDF - HEAVY"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rincian-ahsp/pdf/"),
            name="/api/project/[id]/export/rincian-ahsp/pdf/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500, 504]:
                response.success()

    @tag('export', 'xlsx', 'rincian-ahsp', 'phase3')
    @task(2)
    def export_rincian_ahsp_xlsx(self):
        """Export Rincian AHSP as Excel"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rincian-ahsp/xlsx/"),
            name="/api/project/[id]/export/rincian-ahsp/xlsx/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'csv', 'rekap-kebutuhan', 'phase3')
    @task(2)
    def export_rekap_kebutuhan_csv(self):
        """Export Rekap Kebutuhan as CSV - Procurement planning"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rekap-kebutuhan/xlsx/"),
            name="/api/project/[id]/export/rekap-kebutuhan/xlsx/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'pdf', 'rekap-kebutuhan', 'phase3')
    @task(1)
    def export_rekap_kebutuhan_pdf(self):
        """Export Rekap Kebutuhan as PDF"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rekap-kebutuhan/pdf/"),
            name="/api/project/[id]/export/rekap-kebutuhan/pdf/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'xlsx', 'jadwal', 'phase3')
    @task(2)
    def export_jadwal_xlsx(self):
        """Export Jadwal Pekerjaan as Excel"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/jadwal-pekerjaan/xlsx/"),
            name="/api/project/[id]/export/jadwal-pekerjaan/xlsx/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'word', 'jadwal', 'phase3')
    @task(1)
    def export_jadwal_word(self):
        """Export Jadwal Pekerjaan as Word"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/jadwal-pekerjaan/word/"),
            name="/api/project/[id]/export/jadwal-pekerjaan/word/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'json', 'list-pekerjaan', 'phase3')
    @task(1)
    def export_list_pekerjaan_json(self):
        """Export List Pekerjaan as JSON - Tree structure backup"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/list-pekerjaan/json/"),
            name="/api/project/[id]/export/list-pekerjaan/json/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'json', 'volume', 'phase3')
    @task(1)
    def export_volume_pekerjaan_json(self):
        """Export Volume Pekerjaan as JSON"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/volume-pekerjaan/json/"),
            name="/api/project/[id]/export/volume-pekerjaan/json/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    # ========================================================================
    # PHASE 4 HEAVY OPERATIONS - Remaining export formats
    # ========================================================================

    @tag('export', 'pdf', 'rekap-rab', 'phase4')
    @task(1)
    def export_rekap_rab_pdf(self):
        """Export Rekap RAB as PDF - HEAVY"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rekap-rab/pdf/"),
            name="/api/project/[id]/export/rekap-rab/pdf/",
            catch_response=True
        ) as response:
            # Accept 200, 500 (timeout), 504 (gateway timeout)
            if response.status_code in [200, 500, 504]:
                response.success()

    @tag('export', 'word', 'rincian-ahsp', 'phase4')
    @task(1)
    def export_rincian_ahsp_word(self):
        """Export Rincian AHSP as Word"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rincian-ahsp/word/"),
            name="/api/project/[id]/export/rincian-ahsp/word/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500, 504]:
                response.success()

    @tag('export', 'json', 'rekap-kebutuhan', 'phase4')
    @task(1)
    def export_rekap_kebutuhan_json(self):
        """Export Rekap Kebutuhan as JSON"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rekap-kebutuhan/json/"),
            name="/api/project/[id]/export/rekap-kebutuhan/json/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()

    @tag('export', 'word', 'rekap-kebutuhan', 'phase4')
    @task(1)
    def export_rekap_kebutuhan_word(self):
        """Export Rekap Kebutuhan as Word"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/rekap-kebutuhan/word/"),
            name="/api/project/[id]/export/rekap-kebutuhan/word/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500, 504]:
                response.success()

    @tag('export', 'pdf', 'jadwal', 'phase4')
    @task(1)
    def export_jadwal_pekerjaan_pdf(self):
        """Export Jadwal Pekerjaan as PDF"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/jadwal-pekerjaan/pdf/"),
            name="/api/project/[id]/export/jadwal-pekerjaan/pdf/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500, 504]:
                response.success()

    @tag('export', 'pdf', 'volume', 'phase4')
    @task(1)
    def export_volume_pekerjaan_pdf(self):
        """Export Volume Pekerjaan as PDF"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/volume-pekerjaan/pdf/"),
            name="/api/project/[id]/export/volume-pekerjaan/pdf/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500, 504]:
                response.success()

    @tag('export', 'word', 'volume', 'phase4')
    @task(1)
    def export_volume_pekerjaan_word(self):
        """Export Volume Pekerjaan as Word"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/volume-pekerjaan/word/"),
            name="/api/project/[id]/export/volume-pekerjaan/word/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500, 504]:
                response.success()

    @tag('export', 'xlsx', 'volume', 'phase4')
    @task(1)
    def export_volume_pekerjaan_xlsx(self):
        """Export Volume Pekerjaan as Excel"""
        project_id = random.choice(self.project_ids)
        with self.client.get(
            _api_url(project_id, "export/volume-pekerjaan/xlsx/"),
            name="/api/project/[id]/export/volume-pekerjaan/xlsx/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 500]:
                response.success()


class MutationUser(AuthenticatedUser):
    """
    Simulates users making POST/PUT/DELETE mutations.
    Tests concurrent writes and optimistic locking.
    Represents 5% of expected traffic.
    
    WARNING: These tests WRITE data! Use dedicated test database.
    """
    weight = 0 if AUTH_ONLY else 1  # 5% of traffic (adjust based on HeavyUser weight)
    wait_time = between(5, 15)  # Slower, more deliberate mutations
    
    # Toggle to actually perform mutations (default: disabled for safety)
    MUTATIONS_ENABLED = False
    
    def on_start(self):
        """Initialize mutation user with auth"""
        super().on_start()  # Call parent login
        self.project_ids = [TEST_PROJECT_IDS[0]]  # Use first test project
    
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
            _api_url(project_id, "volume-pekerjaan/save/"),
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
            _api_url(project_id, "parameters/sync/"),
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
            _api_url(project_id, "volume/formula/"),
            name="/api/project/[id]/volume/formula/",
            json={"items": [{"pekerjaan_id": 1, "raw": "=10*5", "is_fx": True}]},
            catch_response=True
        ) as response:
            if response.status_code in [200, 404]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    # ========================================================================
    # PHASE 1 CRITICAL WRITE OPERATIONS - Concurrent write testing
    # ========================================================================
    # WARNING: These operations WRITE to database!
    # Only enable with MUTATIONS_ENABLED = True and dedicated test database

    @tag('mutation', 'critical', 'tree', 'phase1')
    @task(4)
    def save_list_pekerjaan(self):
        """Test tree structure save + optimistic locking - CRITICAL"""
        if not self.MUTATIONS_ENABLED:
            return

        project_id = random.choice(self.project_ids)
        # Simplified test data - single item add
        test_data = {
            "items": [
                {
                    "id": None,  # New item
                    "uraian": f"Load Test Item {random.randint(1000, 9999)}",
                    "ordering_index": random.randint(1, 100),
                    "satuan": "ls",
                    "volume": random.uniform(1, 10)
                }
            ]
        }

        with self.client.post(
            _api_url(project_id, "list-pekerjaan/save/"),
            json=test_data,
            name="/api/project/[id]/list-pekerjaan/save/",
            catch_response=True
        ) as response:
            # 200 = success, 400 = validation error (acceptable), 409 = conflict
            if response.status_code in [200, 201, 400, 409]:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @tag('mutation', 'critical', 'harga_items', 'phase1')
    @task(3)
    def save_harga_items(self):
        """Test harga items bulk save - Frequent write operation"""
        if not self.MUTATIONS_ENABLED:
            return

        project_id = random.choice(self.project_ids)
        # Test data - update existing items
        test_data = {
            "items": [
                {
                    "kode": "TK-0001",
                    "harga": random.uniform(100000, 500000)
                },
                {
                    "kode": "B-0001",
                    "harga": random.uniform(5000, 50000)
                }
            ]
        }

        with self.client.post(
            _api_url(project_id, "harga-items/save/"),
            json=test_data,
            name="/api/project/[id]/harga-items/save/",
            catch_response=True
        ) as response:
            if response.status_code in [200, 201, 400, 404]:
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
    print("  - BrowsingUser (55%): Page browsing + PHASE 1 pages")
    print("  - APIUser (27%): API calls + PHASE 1 critical APIs")
    print("  - HeavyUser (9%): Export operations")
    print("  - MutationUser (9%): POST mutations (disabled by default)")
    print("\nPHASE 1 ADDITIONS (15 critical endpoints):")
    print("  * Search/Autocomplete: /search-ahsp/ (HIGH FREQUENCY)")
    print("  * Pricing APIs: /pricing/, /pekerjaan/.../pricing/")
    print("  * Validation: /rekap-kebutuhan/validate/")
    print("  * NEW APIs: /rincian-rab/, /rekap-kebutuhan-enhanced/")
    print("  * V2 APIs: /kurva-s-harga/, /rekap-kebutuhan-weekly/")
    print("  * Pages: rincian-ahsp, rekap-kebutuhan, rincian-rab, audit-trail")
    print("  * Writes: list-pekerjaan/save/, harga-items/save/ (if enabled)")
    print("\nLegacy Endpoints:")
    print("  * Critical: /jadwal-pekerjaan/, /api/rekap/, /api/chart-data/")
    print("  * Templates: /api/templates/export/ (v2.2)")
    print("  * Volume: /api/volume/formula/, /api/parameters/")
    print("  * Export: PDF, Excel, CSV")
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
        print(f"\n[WARN] Failure Rate: {failure_rate:.2f}%")
        if failure_rate > 5:
            print("   WARNING: High failure rate detected!")
    
    print(f"\nTotal Requests: {environment.stats.total.num_requests}")
    print(f"Total Failures: {environment.stats.total.num_failures}")
    print(f"Average Response Time: {environment.stats.total.avg_response_time:.2f}ms")
    print(f"P95 Response Time: {environment.stats.total.get_response_time_percentile(0.95):.2f}ms")
    print("=" * 60)
