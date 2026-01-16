"""
Performance Benchmarks for DJANGO AHSP PROJECT
===============================================

Automated performance benchmarks for critical endpoints.
These can be run as pytest tests to track performance over time.

Usage:
------
pytest load_testing/benchmarks.py -v --durations=10

Requirements:
- pytest
- pytest-benchmark (optional, for detailed stats)
"""

import os
import sys
import time
import json
from typing import Dict, List, Tuple
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model


# ============================================================================
# CONFIGURATION
# ============================================================================

# Performance thresholds (in milliseconds)
THRESHOLDS = {
    # Page loads
    "page_dashboard": 500,
    "page_list_pekerjaan": 800,
    "page_jadwal_pekerjaan": 1500,
    "page_template_ahsp": 1000,
    "page_rekap_rab": 800,
    "page_volume_pekerjaan": 600,
    "page_harga_items": 600,
    
    # API endpoints - Critical
    "api_list_pekerjaan_tree": 300,
    "api_rekap": 500,
    "api_chart_data": 400,
    "api_harga_items_list": 300,
    "api_rekap_kebutuhan": 400,
    
    # API endpoints - v2.2 New
    "api_template_export": 1000,  # Template export can be heavy
    "api_parameters_list": 200,
    "api_volume_formula_state": 300,
    "api_detail_ahsp": 200,
    
    # API endpoints - Mutations
    "api_volume_save": 500,
    "api_parameters_sync": 400,
    "api_formula_save": 400,
    
    # Export operations (allow longer times)
    "export_rekap_rab_pdf": 5000,
    "export_rekap_rab_xlsx": 3000,
    "export_jadwal_pdf": 8000,
    "export_harga_items_csv": 1000,
}

# Test project ID (configure based on your test data)
TEST_PROJECT_ID = 144  # Valid project ID from database


# ============================================================================
# BENCHMARK FUNCTIONS
# ============================================================================

def measure_request(client: Client, path: str, method: str = "GET", 
                   data: dict = None) -> Tuple[float, int, str]:
    """
    Measure a single HTTP request.
    
    Returns:
        Tuple of (duration_ms, status_code, error_message)
    """
    start = time.perf_counter()
    
    try:
        if method.upper() == "GET":
            response = client.get(path)
        elif method.upper() == "POST":
            response = client.post(path, data=data, content_type="application/json")
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        duration_ms = (time.perf_counter() - start) * 1000
        return duration_ms, response.status_code, ""
        
    except Exception as e:
        duration_ms = (time.perf_counter() - start) * 1000
        return duration_ms, 0, str(e)


def run_benchmark(client: Client, name: str, path: str, 
                  iterations: int = 5) -> Dict:
    """
    Run multiple iterations of a request and collect statistics.
    """
    durations = []
    errors = []
    status_codes = []
    
    for i in range(iterations):
        duration, status, error = measure_request(client, path)
        durations.append(duration)
        status_codes.append(status)
        if error:
            errors.append(error)
    
    threshold = THRESHOLDS.get(name, 1000)
    avg_duration = sum(durations) / len(durations)
    
    return {
        "name": name,
        "path": path,
        "iterations": iterations,
        "avg_ms": round(avg_duration, 2),
        "min_ms": round(min(durations), 2),
        "max_ms": round(max(durations), 2),
        "threshold_ms": threshold,
        "passed": avg_duration <= threshold,
        "errors": len(errors),
        "status_codes": list(set(status_codes)),
    }


# ============================================================================
# BENCHMARK SUITE
# ============================================================================

class PerformanceBenchmarkSuite:
    """
    Collection of performance benchmarks for the detail_project app.
    """
    
    def __init__(self, project_id: int = TEST_PROJECT_ID):
        self.project_id = project_id
        self.client = Client()
        self.results = []
        
    def setup(self):
        """Setup test client with authentication if needed"""
        # For authenticated endpoints, login here
        # User = get_user_model()
        # self.client.force_login(User.objects.first())
        pass
    
    def benchmark_pages(self) -> List[Dict]:
        """Benchmark page load times"""
        benchmarks = [
            ("page_dashboard", "/dashboard/"),
            ("page_list_pekerjaan", f"/detail-project/{self.project_id}/list-pekerjaan/"),
            ("page_jadwal_pekerjaan", f"/detail-project/{self.project_id}/jadwal-pekerjaan/"),
            ("page_template_ahsp", f"/detail-project/{self.project_id}/template-ahsp/"),
            ("page_rekap_rab", f"/detail-project/{self.project_id}/rekap-rab/"),
        ]
        
        results = []
        for name, path in benchmarks:
            result = run_benchmark(self.client, name, path)
            results.append(result)
            self._print_result(result)
        
        return results
    
    def benchmark_apis(self) -> List[Dict]:
        """Benchmark API response times"""
        benchmarks = [
            ("api_list_pekerjaan_tree", 
             f"/detail-project/api/project/{self.project_id}/list-pekerjaan/tree/"),
            ("api_rekap", 
             f"/detail-project/api/project/{self.project_id}/rekap/"),
            ("api_chart_data", 
             f"/detail-project/api/v2/project/{self.project_id}/chart-data/"),
            ("api_harga_items_list", 
             f"/detail-project/api/project/{self.project_id}/harga-items/list/"),
            ("api_rekap_kebutuhan", 
             f"/detail-project/api/project/{self.project_id}/rekap-kebutuhan/"),
        ]
        
        results = []
        for name, path in benchmarks:
            result = run_benchmark(self.client, name, path)
            results.append(result)
            self._print_result(result)
        
        return results
    
    def benchmark_exports(self, iterations: int = 2) -> List[Dict]:
        """Benchmark export operations (fewer iterations due to heavy load)"""
        benchmarks = [
            ("export_rekap_rab_pdf", 
             f"/detail-project/api/project/{self.project_id}/export/rekap-rab/pdf/"),
            ("export_rekap_rab_xlsx", 
             f"/detail-project/api/project/{self.project_id}/export/rekap-rab/xlsx/"),
        ]
        
        results = []
        for name, path in benchmarks:
            result = run_benchmark(self.client, name, path, iterations=iterations)
            results.append(result)
            self._print_result(result)
        
        return results
    
    def _print_result(self, result: Dict):
        """Print a single benchmark result"""
        status = "✓ PASS" if result["passed"] else "✗ FAIL"
        print(f"  {status} {result['name']}: {result['avg_ms']:.2f}ms "
              f"(threshold: {result['threshold_ms']}ms)")
    
    def run_all(self, include_exports: bool = False) -> Dict:
        """Run all benchmarks and return summary"""
        print("=" * 60)
        print("PERFORMANCE BENCHMARK SUITE")
        print("=" * 60)
        print(f"\nProject ID: {self.project_id}")
        print(f"Timestamp: {datetime.now().isoformat()}")
        
        self.setup()
        
        print("\n--- Page Benchmarks ---")
        page_results = self.benchmark_pages()
        
        print("\n--- API Benchmarks ---")
        api_results = self.benchmark_apis()
        
        export_results = []
        if include_exports:
            print("\n--- Export Benchmarks (Heavy) ---")
            export_results = self.benchmark_exports()
        
        all_results = page_results + api_results + export_results
        
        passed = sum(1 for r in all_results if r["passed"])
        failed = sum(1 for r in all_results if not r["passed"])
        
        print("\n" + "=" * 60)
        print(f"SUMMARY: {passed} passed, {failed} failed")
        print("=" * 60)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "project_id": self.project_id,
            "summary": {"passed": passed, "failed": failed, "total": len(all_results)},
            "results": all_results,
        }
    
    def save_results(self, filepath: str = "load_testing/results/benchmark_results.json"):
        """Save results to JSON file"""
        results = self.run_all(include_exports=True)
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to: {filepath}")
        return results


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run performance benchmarks")
    parser.add_argument("--project-id", type=int, default=TEST_PROJECT_ID,
                       help="Project ID to test")
    parser.add_argument("--include-exports", action="store_true",
                       help="Include export benchmarks (slow)")
    parser.add_argument("--save", action="store_true",
                       help="Save results to JSON file")
    
    args = parser.parse_args()
    
    suite = PerformanceBenchmarkSuite(project_id=args.project_id)
    
    if args.save:
        suite.save_results()
    else:
        results = suite.run_all(include_exports=args.include_exports)
