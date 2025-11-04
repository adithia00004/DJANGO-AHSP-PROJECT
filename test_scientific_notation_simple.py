from decimal import Decimal

import pytest

from referensi.services.import_utils import normalize_num


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0.5", Decimal("0.5")),
        ("1.05", Decimal("1.05")),
        ("0,000008", Decimal("0.000008")),
        ("8e-05", Decimal("0.00008")),
        ("invalid", None),
    ],
)
def test_normalize_num_simple_cases(value, expected):
    assert normalize_num(value) == expected
