"""
Test fixture for verifying progress_bulan_ini and progress_bulan_lalu calculations.

Run with: python -m pytest detail_project/exports/tests/test_progress_calculation.py -v
Or standalone: python detail_project/exports/tests/test_progress_calculation.py
"""

from decimal import Decimal
from typing import Dict, Tuple
import unittest


def calculate_progress(
    actual_map: Dict[Tuple[int, int], Decimal],
    pek_id: int,
    total_harga: Decimal,
    harga_pekerjaan: Decimal,
    month: int
) -> Dict[str, float]:
    """
    Simulate the progress calculation logic from JadwalPekerjaanAdapter.
    
    Args:
        actual_map: Dict of (pekerjaan_id, week_number) -> actual_proportion
        pek_id: Pekerjaan ID
        total_harga: Total harga proyek
        harga_pekerjaan: Harga pekerjaan ini
        month: Target month (1-based)
        
    Returns:
        Dict with bobot, actual_ini, actual_lalu, progress_bulan_ini, progress_bulan_lalu
    """
    # Calculate week ranges
    start_week = (month - 1) * 4 + 1  # Month 1 → Week 1-4
    end_week = month * 4
    
    prev_month = month - 1
    prev_start_week = (prev_month - 1) * 4 + 1 if prev_month >= 1 else 0
    prev_end_week = prev_month * 4 if prev_month >= 1 else 0
    
    # Calculate bobot (weight percentage)
    bobot = float(harga_pekerjaan / total_harga * 100) if total_harga > 0 else 0.0
    
    # Calculate actual progress this month (sum of weeks)
    actual_ini = sum(
        float(actual_map.get((pek_id, w), Decimal("0")))
        for w in range(start_week, end_week + 1)
    )
    
    # Calculate actual progress previous month
    actual_lalu = 0.0
    if prev_month >= 1:
        actual_lalu = sum(
            float(actual_map.get((pek_id, w), Decimal("0")))
            for w in range(prev_start_week, prev_end_week + 1)
        )
    
    # Weighted progress (contribution to total project progress)
    progress_ini = actual_ini * bobot / 100 if bobot > 0 else 0.0
    progress_lalu = actual_lalu * bobot / 100 if bobot > 0 else 0.0
    
    return {
        "bobot": round(bobot, 2),
        "actual_ini": round(actual_ini, 2),
        "actual_lalu": round(actual_lalu, 2),
        "progress_bulan_ini": round(progress_ini, 2),
        "progress_bulan_lalu": round(progress_lalu, 2),
        "week_range_ini": f"W{start_week}-W{end_week}",
        "week_range_lalu": f"W{prev_start_week}-W{prev_end_week}" if prev_month >= 1 else "N/A",
    }


class TestProgressCalculation(unittest.TestCase):
    """Test cases for progress calculation."""
    
    def test_month_1_single_pekerjaan(self):
        """
        Test Month 1 dengan 1 pekerjaan.
        Week 1-4 memiliki progress: 5%, 10%, 8%, 7% = 30% actual_ini
        Bulan lalu tidak ada (Month 0).
        Bobot = 100% (satu-satunya pekerjaan)
        """
        actual_map = {
            (1, 1): Decimal("5"),
            (1, 2): Decimal("10"),
            (1, 3): Decimal("8"),
            (1, 4): Decimal("7"),
        }
        
        result = calculate_progress(
            actual_map=actual_map,
            pek_id=1,
            total_harga=Decimal("100000000"),  # Rp 100jt
            harga_pekerjaan=Decimal("100000000"),  # Rp 100jt (100%)
            month=1
        )
        
        print("\n=== Test: Month 1, Single Pekerjaan ===")
        print(f"Week Range Ini: {result['week_range_ini']}")
        print(f"Week Range Lalu: {result['week_range_lalu']}")
        print(f"Bobot: {result['bobot']}%")
        print(f"Actual Ini (raw): {result['actual_ini']}%")
        print(f"Actual Lalu (raw): {result['actual_lalu']}%")
        print(f"Progress Bulan Ini (weighted): {result['progress_bulan_ini']}%")
        print(f"Progress Bulan Lalu (weighted): {result['progress_bulan_lalu']}%")
        
        self.assertEqual(result['bobot'], 100.0)
        self.assertEqual(result['actual_ini'], 30.0)  # 5+10+8+7
        self.assertEqual(result['actual_lalu'], 0.0)  # Month 0 tidak ada
        self.assertEqual(result['progress_bulan_ini'], 30.0)  # 30% × 100% = 30%
        self.assertEqual(result['progress_bulan_lalu'], 0.0)
    
    def test_month_2_with_previous(self):
        """
        Test Month 2 dengan data bulan sebelumnya.
        Month 1 (W1-W4): 5%, 10%, 8%, 7% = 30%
        Month 2 (W5-W8): 12%, 15%, 10%, 13% = 50%
        """
        actual_map = {
            # Month 1 (Week 1-4)
            (1, 1): Decimal("5"),
            (1, 2): Decimal("10"),
            (1, 3): Decimal("8"),
            (1, 4): Decimal("7"),
            # Month 2 (Week 5-8)
            (1, 5): Decimal("12"),
            (1, 6): Decimal("15"),
            (1, 7): Decimal("10"),
            (1, 8): Decimal("13"),
        }
        
        result = calculate_progress(
            actual_map=actual_map,
            pek_id=1,
            total_harga=Decimal("100000000"),
            harga_pekerjaan=Decimal("100000000"),
            month=2
        )
        
        print("\n=== Test: Month 2, With Previous Month ===")
        print(f"Week Range Ini: {result['week_range_ini']}")
        print(f"Week Range Lalu: {result['week_range_lalu']}")
        print(f"Bobot: {result['bobot']}%")
        print(f"Actual Ini (raw): {result['actual_ini']}%")
        print(f"Actual Lalu (raw): {result['actual_lalu']}%")
        print(f"Progress Bulan Ini (weighted): {result['progress_bulan_ini']}%")
        print(f"Progress Bulan Lalu (weighted): {result['progress_bulan_lalu']}%")
        
        self.assertEqual(result['bobot'], 100.0)
        self.assertEqual(result['actual_ini'], 50.0)   # 12+15+10+13
        self.assertEqual(result['actual_lalu'], 30.0)  # 5+10+8+7
        self.assertEqual(result['progress_bulan_ini'], 50.0)
        self.assertEqual(result['progress_bulan_lalu'], 30.0)
    
    def test_weighted_by_bobot(self):
        """
        Test weighted calculation dengan multiple pekerjaan.
        Pekerjaan A: Rp 100jt (10% bobot), actual 30%
        Pekerjaan B: Rp 500jt (50% bobot), actual 20%
        Pekerjaan C: Rp 400jt (40% bobot), actual 0%
        """
        total_harga = Decimal("1000000000")  # Rp 1 Milyar
        
        actual_map = {
            # Pekerjaan A (pek_id=1): Week 1-4 = 30% total
            (1, 1): Decimal("10"),
            (1, 2): Decimal("10"),
            (1, 3): Decimal("5"),
            (1, 4): Decimal("5"),
            # Pekerjaan B (pek_id=2): Week 1-4 = 20% total
            (2, 1): Decimal("5"),
            (2, 2): Decimal("5"),
            (2, 3): Decimal("5"),
            (2, 4): Decimal("5"),
            # Pekerjaan C (pek_id=3): No progress
        }
        
        # Pekerjaan A
        result_a = calculate_progress(
            actual_map=actual_map,
            pek_id=1,
            total_harga=total_harga,
            harga_pekerjaan=Decimal("100000000"),  # 10%
            month=1
        )
        
        # Pekerjaan B
        result_b = calculate_progress(
            actual_map=actual_map,
            pek_id=2,
            total_harga=total_harga,
            harga_pekerjaan=Decimal("500000000"),  # 50%
            month=1
        )
        
        # Pekerjaan C
        result_c = calculate_progress(
            actual_map=actual_map,
            pek_id=3,
            total_harga=total_harga,
            harga_pekerjaan=Decimal("400000000"),  # 40%
            month=1
        )
        
        print("\n=== Test: Weighted by Bobot (Multiple Pekerjaan) ===")
        print(f"Pekerjaan A: Bobot={result_a['bobot']}%, Actual={result_a['actual_ini']}%, Progress={result_a['progress_bulan_ini']}%")
        print(f"Pekerjaan B: Bobot={result_b['bobot']}%, Actual={result_b['actual_ini']}%, Progress={result_b['progress_bulan_ini']}%")
        print(f"Pekerjaan C: Bobot={result_c['bobot']}%, Actual={result_c['actual_ini']}%, Progress={result_c['progress_bulan_ini']}%")
        
        total_progress = result_a['progress_bulan_ini'] + result_b['progress_bulan_ini'] + result_c['progress_bulan_ini']
        print(f"Total Project Progress: {total_progress}%")
        
        # Verify calculations
        self.assertEqual(result_a['bobot'], 10.0)
        self.assertEqual(result_a['actual_ini'], 30.0)
        self.assertEqual(result_a['progress_bulan_ini'], 3.0)  # 30% × 10% = 3%
        
        self.assertEqual(result_b['bobot'], 50.0)
        self.assertEqual(result_b['actual_ini'], 20.0)
        self.assertEqual(result_b['progress_bulan_ini'], 10.0)  # 20% × 50% = 10%
        
        self.assertEqual(result_c['bobot'], 40.0)
        self.assertEqual(result_c['actual_ini'], 0.0)
        self.assertEqual(result_c['progress_bulan_ini'], 0.0)  # 0% × 40% = 0%
        
        # Total project progress = 3% + 10% + 0% = 13%
        self.assertEqual(total_progress, 13.0)


if __name__ == "__main__":
    # Run tests with verbose output
    unittest.main(verbosity=2)
