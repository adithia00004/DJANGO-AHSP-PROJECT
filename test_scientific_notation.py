#!/usr/bin/env python3
"""
Quick test script to verify scientific notation fix.
Run: python3 test_scientific_notation.py
"""

import sys
import os

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from decimal import Decimal
from referensi.services.import_utils import normalize_num


def test_case(description, input_val, expected):
    """Test a single case."""
    result = normalize_num(input_val)
    success = result == expected
    status = "✓" if success else "✗"
    print(f"{status} {description}")
    if not success:
        print(f"  Input: {input_val}")
        print(f"  Expected: {expected}")
        print(f"  Got: {result}")
    return success


def main():
    """Run all tests."""
    print("Testing normalize_num with scientific notation support\n")
    print("=" * 60)

    all_passed = True

    # Original issue - scientific notation from Excel
    print("\n1. Scientific Notation (Excel exports):")
    all_passed &= test_case(
        "8e-05 (your issue)", "8e-05", Decimal("0.00008")
    )
    all_passed &= test_case(
        "1.23e-10", "1.23e-10", Decimal("0.000000000123")
    )
    all_passed &= test_case(
        "5E3 (uppercase)", "5E3", Decimal("5000")
    )
    all_passed &= test_case(
        "2.5E+2", "2.5E+2", Decimal("250")
    )

    # Standard decimals (should still work)
    print("\n2. Standard Decimal Numbers:")
    all_passed &= test_case(
        "0.000008", "0.000008", Decimal("0.000008")
    )
    all_passed &= test_case(
        "123.456", "123.456", Decimal("123.456")
    )
    all_passed &= test_case(
        "-123.456", "-123.456", Decimal("-123.456")
    )

    # Comma as decimal separator
    print("\n3. Comma as Decimal Separator:")
    all_passed &= test_case(
        "0,000008", "0,000008", Decimal("0.000008")
    )
    all_passed &= test_case(
        "123,456", "123,456", Decimal("123.456")
    )

    # Float inputs (from pandas)
    print("\n4. Float Inputs (pandas/openpyxl):")
    all_passed &= test_case(
        "float 0.000008", 0.000008, Decimal("0.000008")
    )
    all_passed &= test_case(
        "float 8e-05", 8e-05, Decimal("0.00008")
    )
    all_passed &= test_case(
        "int 123", 123, Decimal("123")
    )

    # Edge cases
    print("\n5. Edge Cases:")
    all_passed &= test_case(
        "Empty string", "", None
    )
    all_passed &= test_case(
        "None", None, None
    )
    all_passed &= test_case(
        "Invalid 'abc'", "abc", None
    )
    all_passed &= test_case(
        "Zero", "0", Decimal("0")
    )

    # Real-world AHSP values
    print("\n6. Real-world AHSP Koefisien Values:")
    all_passed &= test_case(
        "0.5", "0.5", Decimal("0.5")
    )
    all_passed &= test_case(
        "1.05", "1.05", Decimal("1.05")
    )
    all_passed &= test_case(
        "0.000008 (user input)", "0.000008", Decimal("0.000008")
    )
    all_passed &= test_case(
        "8e-05 (Excel export)", "8e-05", Decimal("0.00008")
    )

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED!")
        print("\nThe fix successfully handles:")
        print("  - Scientific notation from Excel (8e-05, 1.23E-10)")
        print("  - Standard decimal numbers (0.000008)")
        print("  - Comma separators (0,000008)")
        print("  - Float/int inputs from pandas")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    sys.exit(main())
