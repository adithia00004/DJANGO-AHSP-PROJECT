"""
Unit tests for import_utils module.

Tests the normalize_num function, especially scientific notation support.
"""

from decimal import Decimal
import pytest

from referensi.services.import_utils import normalize_num


class TestNormalizeNum:
    """Test normalize_num function for various number formats."""

    def test_standard_decimal(self):
        """Test standard decimal numbers."""
        assert normalize_num("123.456") == Decimal("123.456")
        assert normalize_num("0.000008") == Decimal("0.000008")
        assert normalize_num("999") == Decimal("999")

    def test_negative_numbers(self):
        """Test negative numbers."""
        assert normalize_num("-123.456") == Decimal("-123.456")
        assert normalize_num("-0.000008") == Decimal("-0.000008")

    def test_comma_as_decimal_separator(self):
        """Test comma as decimal separator (European format)."""
        assert normalize_num("123,456") == Decimal("123.456")
        assert normalize_num("0,000008") == Decimal("0.000008")

    def test_thousand_separators(self):
        """Test numbers with thousand separators."""
        # European format: 1.234,56
        assert normalize_num("1.234,56") == Decimal("1234.56")
        # US format: 1,234.56
        assert normalize_num("1,234.56") == Decimal("1234.56")

    def test_scientific_notation_lowercase(self):
        """Test scientific notation with lowercase 'e'."""
        assert normalize_num("8e-05") == Decimal("0.00008")
        assert normalize_num("1.23e-10") == Decimal("0.000000000123")
        assert normalize_num("5e3") == Decimal("5000")
        assert normalize_num("2.5e+2") == Decimal("250")

    def test_scientific_notation_uppercase(self):
        """Test scientific notation with uppercase 'E'."""
        assert normalize_num("8E-05") == Decimal("0.00008")
        assert normalize_num("1.23E-10") == Decimal("0.000000000123")
        assert normalize_num("5E3") == Decimal("5000")
        assert normalize_num("2.5E+2") == Decimal("250")

    def test_scientific_notation_negative(self):
        """Test negative numbers in scientific notation."""
        assert normalize_num("-8e-05") == Decimal("-0.00008")
        assert normalize_num("-1.23E+10") == Decimal("-12300000000")

    def test_float_input(self):
        """Test direct float input (from pandas)."""
        assert normalize_num(123.456) == Decimal("123.456")
        assert normalize_num(0.000008) == Decimal("0.000008")
        assert normalize_num(8e-05) == Decimal("0.00008")

    def test_int_input(self):
        """Test direct int input."""
        assert normalize_num(123) == Decimal("123")
        assert normalize_num(0) == Decimal("0")

    def test_empty_and_none(self):
        """Test empty strings and None values."""
        assert normalize_num("") is None
        assert normalize_num(None) is None
        assert normalize_num("   ") is None

    def test_nan_values(self):
        """Test NaN values."""
        assert normalize_num("nan") is None
        assert normalize_num("NaN") is None
        assert normalize_num("none") is None
        assert normalize_num("None") is None

    def test_invalid_formats(self):
        """Test invalid number formats."""
        assert normalize_num("abc") is None
        assert normalize_num("12.34.56") is None
        assert normalize_num("12,34,56") is None
        assert normalize_num("1e") is None  # Incomplete scientific notation
        assert normalize_num("e-05") is None  # Missing base
        assert normalize_num("12e3e4") is None  # Multiple exponents

    def test_whitespace_handling(self):
        """Test handling of whitespace."""
        assert normalize_num("  123.456  ") == Decimal("123.456")
        assert normalize_num("1 234.56") == Decimal("1234.56")
        assert normalize_num("8 e-05") == Decimal("0.00008")

    def test_very_small_numbers(self):
        """Test very small numbers that Excel exports as scientific notation."""
        # These are typical Excel exports for small koefisien values
        assert normalize_num("8e-05") == Decimal("0.00008")
        assert normalize_num("1.5e-06") == Decimal("0.0000015")
        assert normalize_num("3.2e-08") == Decimal("0.000000032")

    def test_very_large_numbers(self):
        """Test very large numbers in scientific notation."""
        assert normalize_num("1.23e10") == Decimal("12300000000")
        assert normalize_num("5.6E+12") == Decimal("5600000000000")

    def test_infinity_and_special_floats(self):
        """Test special float values."""
        import math
        assert normalize_num(math.inf) is None
        assert normalize_num(-math.inf) is None
        assert normalize_num(math.nan) is None

    def test_pandas_na_values(self):
        """Test pandas NA values (if pandas available)."""
        try:
            import pandas as pd
            assert normalize_num(pd.NA) is None
        except (ImportError, AttributeError):
            # pandas not available or no NA type
            pytest.skip("pandas not available")

    def test_real_world_excel_values(self):
        """Test real-world values from Excel AHSP files."""
        # Common koefisien values from AHSP
        assert normalize_num("0.5") == Decimal("0.5")
        assert normalize_num("1.05") == Decimal("1.05")
        assert normalize_num("0,000008") == Decimal("0.000008")  # User's input
        assert normalize_num("8e-05") == Decimal("0.00008")  # Excel's export

        # Decimal places precision
        result = normalize_num("0.123456")
        assert result == Decimal("0.123456")
        assert str(result) == "0.123456"


class TestNormalizeNumEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_handling(self):
        """Test various representations of zero."""
        assert normalize_num("0") == Decimal("0")
        assert normalize_num("0.0") == Decimal("0")
        assert normalize_num("0,0") == Decimal("0")
        assert normalize_num("0e0") == Decimal("0")
        assert normalize_num(0) == Decimal("0")

    def test_precision_preservation(self):
        """Test that precision is preserved."""
        # Decimal should preserve exact representation
        result = normalize_num("0.000008")
        assert result == Decimal("0.000008")

        # Scientific notation should convert correctly
        result = normalize_num("8e-06")
        assert result == Decimal("0.000008")

    def test_leading_trailing_zeros(self):
        """Test numbers with leading/trailing zeros."""
        assert normalize_num("000123.456") == Decimal("123.456")
        assert normalize_num("123.456000") == Decimal("123.456")
        assert normalize_num("0.00008") == Decimal("0.00008")
