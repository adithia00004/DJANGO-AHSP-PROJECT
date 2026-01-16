from decimal import Decimal

import pytest

from referensi.services.import_utils import normalize_num


SCIENTIFIC_CASES = [
    ("8e-05", Decimal("0.00008")),
    ("1.23e-10", Decimal("0.000000000123")),
    ("5E3", Decimal("5000")),
    ("2.5E+2", Decimal("250")),
    ("-8e-05", Decimal("-0.00008")),
]


STANDARD_CASES = [
    ("0.000008", Decimal("0.000008")),
    ("123.456", Decimal("123.456")),
    ("-123.456", Decimal("-123.456")),
    ("0,000008", Decimal("0.000008")),
    ("123,456", Decimal("123.456")),
    (0.000008, Decimal("0.000008")),
    (8e-05, Decimal("0.00008")),
    (123, Decimal("123")),
]


INVALID_CASES = [
    ("", None),
    (None, None),
    ("abc", None),
    ("e-05", None),
    ("12e", None),
]


@pytest.mark.parametrize(("value", "expected"), SCIENTIFIC_CASES + STANDARD_CASES + INVALID_CASES)
def test_normalize_num_handles_various_inputs(value, expected):
    assert normalize_num(value) == expected
