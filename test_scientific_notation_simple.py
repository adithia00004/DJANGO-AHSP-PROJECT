#!/usr/bin/env python3
"""
Simple test for scientific notation support.
Tests normalize_num directly without Django dependencies.
"""

import re
from decimal import Decimal, InvalidOperation
import math

# Copy the normalize_num logic locally for testing
_NUM_CANON = re.compile(r"^-?\d+(?:\.\d+)?$")
_NUM_SCIENTIFIC = re.compile(r"^-?\d+(?:\.\d+)?[eE][+-]?\d+$")

def norm_text(val) -> str:
    if val is None:
        return ""
    if isinstance(val, float):
        if math.isnan(val):
            return ""
        return str(val).strip()
    s = str(val).strip()
    if s.lower() in ("nan", "none"):
        return ""
    return s

def normalize_num(val):
    """Test version of normalize_num with scientific notation support."""
    if isinstance(val, (int, float)):
        if isinstance(val, float):
            if math.isnan(val) or math.isinf(val):
                return None
        try:
            return Decimal(str(val))
        except (InvalidOperation, ValueError):
            return None

    s = norm_text(val).replace(" ", "")
    if s == "":
        return None

    if "e" not in s.lower():
        if "." in s and "," in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        elif "," in s and "." not in s:
            s = s.replace(",", ".")

    if not (_NUM_CANON.match(s) or _NUM_SCIENTIFIC.match(s)):
        return None

    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def test_case(description, input_val, expected):
    """Test a single case."""
    result = normalize_num(input_val)
    success = result == expected
    status = "✓" if success else "✗"
    print(f"{status} {description}")
    if not success:
        print(f"  Input: {input_val!r}")
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
        "8e-05 (YOUR EXACT ISSUE)", "8e-05", Decimal("0.00008")
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
    all_passed &= test_case(
        "-8e-05 (negative)", "-8e-05", Decimal("-0.00008")
    )

    # Standard decimals (should still work)
    print("\n2. Standard Decimal Numbers:")
    all_passed &= test_case(
        "0.000008 (user input)", "0.000008", Decimal("0.000008")
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
    all_passed &= test_case(
        "Invalid 'e-05' (no base)", "e-05", None
    )
    all_passed &= test_case(
        "Invalid '12e' (no exp)", "12e", None
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
        "0.000008 (user types)", "0.000008", Decimal("0.000008")
    )
    all_passed &= test_case(
        "8e-05 (Excel saves)", "8e-05", Decimal("0.00008")
    )

    print("\n" + "=" * 60)
    if all_passed:
        print("✓ ALL TESTS PASSED!\n")
        print("The fix successfully handles:")
        print("  ✓ Scientific notation from Excel (8e-05, 1.23E-10)")
        print("  ✓ Standard decimal numbers (0.000008)")
        print("  ✓ Comma separators (0,000008)")
        print("  ✓ Float/int inputs from pandas")
        print("  ✓ Invalid formats return None")
        print("\nYour error 'Baris 460: nilai koefisien 8e-05 tidak valid' ")
        print("should now be FIXED! ✓")
        return 0
    else:
        print("✗ SOME TESTS FAILED")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
