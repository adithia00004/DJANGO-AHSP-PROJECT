# detail_project/tests/test_numeric.py
from decimal import Decimal
from django.test import SimpleTestCase

from detail_project.numeric import (
    parse_any,
    to_dp_str,
    quantize_half_up,
    DECIMAL_SPEC,
)

class NumericUtilTests(SimpleTestCase):
    def test_parse_any_accepts_common_locales(self):
        cases = {
            "2,7275": Decimal("2.7275"),
            "1.234,56": Decimal("1234.56"),
            "1,234.56": Decimal("1234.56"),
            "2_000,5": Decimal("2000.5"),
            "2.000,000001": Decimal("2000.000001"),
            "0": Decimal("0"),
            "  12,0  ": Decimal("12.0"),
            "": None,
            None: None,
            "-1": None,                # < 0 ditolak
            "abc": None,               # bukan angka
        }
        for raw, expected in cases.items():
            got = parse_any(raw)
            self.assertEqual(got, expected, msg=f"parse_any({raw!r}) => {got} != {expected}")

    def test_quantize_half_up_specs(self):
        # KOEF: 6 dp
        x = Decimal("2.72750049")
        q = quantize_half_up(x, DECIMAL_SPEC["KOEF"].dp)
        self.assertEqual(q, Decimal("2.727500"))
        x2 = Decimal("2.7275005")
        q2 = quantize_half_up(x2, DECIMAL_SPEC["KOEF"].dp)
        self.assertEqual(q2, Decimal("2.727501"))

        # VOL: 3 dp
        v = Decimal("123.4564")
        self.assertEqual(quantize_half_up(v, DECIMAL_SPEC["VOL"].dp), Decimal("123.456"))
        v2 = Decimal("123.4565")
        self.assertEqual(quantize_half_up(v2, DECIMAL_SPEC["VOL"].dp), Decimal("123.457"))

        # HARGA: 2 dp
        h = Decimal("9999.994")
        self.assertEqual(quantize_half_up(h, DECIMAL_SPEC["HARGA"].dp), Decimal("9999.99"))
        h2 = Decimal("9999.995")
        self.assertEqual(quantize_half_up(h2, DECIMAL_SPEC["HARGA"].dp), Decimal("10000.00"))

    def test_to_dp_str_canonical(self):
        self.assertEqual(to_dp_str(Decimal("12"), 2), "12.00")
        self.assertEqual(to_dp_str("1.2", 3), "1.200")
        self.assertEqual(to_dp_str(None, 2), None)
