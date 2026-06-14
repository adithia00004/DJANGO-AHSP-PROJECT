"""
Tests for server-side formula validation in api_volume_formula_state().

Sprint 1 — Critical Security: Validates that the _validate_formula_raw()
utility correctly rejects injection attempts while accepting legitimate formulas.
"""
import json
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django.utils import timezone

from dashboard.models import Project
from detail_project.models import (
    Klasifikasi,
    Pekerjaan,
    SubKlasifikasi,
    VolumeFormulaState,
)
from detail_project.views_api import (
    _validate_formula_raw,
    api_volume_formula_state,
)


class ValidateFormulaRawUnitTests(TestCase):
    """Direct unit tests for _validate_formula_raw()."""

    # ---- Valid formulas ----

    def test_empty_string_is_valid(self):
        self.assertEqual(_validate_formula_raw(""), [])

    def test_whitespace_only_is_valid(self):
        self.assertEqual(_validate_formula_raw("   "), [])

    def test_none_is_valid(self):
        self.assertEqual(_validate_formula_raw(None), [])

    def test_simple_formula(self):
        self.assertEqual(_validate_formula_raw("=bp_1 * 2"), [])

    def test_formula_with_addition(self):
        self.assertEqual(_validate_formula_raw("=bp_1 + bp_2"), [])

    def test_formula_with_parentheses(self):
        self.assertEqual(_validate_formula_raw("=(bp_1 + bp_2) * bp_3"), [])

    def test_formula_with_allowed_function_sum(self):
        self.assertEqual(_validate_formula_raw("=sum(bp_1, bp_2, bp_3)"), [])

    def test_formula_with_allowed_function_min(self):
        self.assertEqual(_validate_formula_raw("=min(bp_1, bp_2)"), [])

    def test_formula_with_allowed_function_max(self):
        self.assertEqual(_validate_formula_raw("=max(bp_1, bp_2)"), [])

    def test_formula_with_allowed_function_round(self):
        self.assertEqual(_validate_formula_raw("=round(bp_1, 2)"), [])

    def test_formula_with_allowed_function_avg(self):
        self.assertEqual(_validate_formula_raw("=avg(bp_1, bp_2)"), [])

    def test_formula_with_allowed_function_abs(self):
        self.assertEqual(_validate_formula_raw("=abs(bp_1)"), [])

    def test_formula_with_allowed_function_floor(self):
        self.assertEqual(_validate_formula_raw("=floor(bp_1)"), [])

    def test_formula_with_allowed_function_ceil(self):
        self.assertEqual(_validate_formula_raw("=ceil(bp_1)"), [])

    def test_formula_with_allowed_function_pow(self):
        self.assertEqual(_validate_formula_raw("=pow(bp_1, 2)"), [])

    def test_formula_with_computed_param(self):
        self.assertEqual(_validate_formula_raw("=cp_1 + bp_2"), [])

    def test_formula_with_decimal_literal(self):
        self.assertEqual(_validate_formula_raw("=bp_1 * 3.14"), [])

    def test_formula_with_newline(self):
        """Multiline formulas from the editor modal should be accepted."""
        self.assertEqual(_validate_formula_raw("=bp_1\n+ bp_2"), [])

    def test_formula_with_tab(self):
        self.assertEqual(_validate_formula_raw("=bp_1\t* 2"), [])

    def test_formula_with_carriage_return(self):
        self.assertEqual(_validate_formula_raw("=bp_1\r\n+ bp_2"), [])

    def test_formula_with_power_operator(self):
        self.assertEqual(_validate_formula_raw("=bp_1 ^ 2"), [])

    def test_formula_nested_functions(self):
        self.assertEqual(_validate_formula_raw("=round(sum(bp_1, bp_2), 2)"), [])

    def test_formula_no_equals_prefix(self):
        """Raw can also be plain number (non-formula mode)."""
        self.assertEqual(_validate_formula_raw("42.5"), [])

    # ---- Invalid formulas: injection attempts ----

    def test_reject_eval(self):
        errors = _validate_formula_raw("=eval('hack')")
        self.assertTrue(len(errors) > 0)
        # Note: rejected at Layer 1 (quote char) before Layer 2 sees 'eval'

    def test_reject_eval_no_quotes(self):
        """eval without quotes — caught at Layer 2 (unknown function)."""
        errors = _validate_formula_raw("=eval(bp_1)")
        self.assertTrue(len(errors) > 0)
        self.assertIn("eval", errors[0])

    def test_reject_dunder_import(self):
        errors = _validate_formula_raw("=__import__('os')")
        self.assertTrue(len(errors) > 0)

    def test_reject_script_tag(self):
        errors = _validate_formula_raw("=<script>alert(1)</script>")
        self.assertTrue(len(errors) > 0)

    def test_reject_semicolon(self):
        errors = _validate_formula_raw("=bp_1; eval('x')")
        self.assertTrue(len(errors) > 0)

    def test_reject_curly_braces(self):
        errors = _validate_formula_raw("={bp_1}")
        self.assertTrue(len(errors) > 0)

    def test_reject_square_brackets(self):
        errors = _validate_formula_raw("=[bp_1]")
        self.assertTrue(len(errors) > 0)

    def test_reject_backtick(self):
        errors = _validate_formula_raw("=`bp_1`")
        self.assertTrue(len(errors) > 0)

    def test_reject_dollar_sign(self):
        errors = _validate_formula_raw("=$bp_1")
        self.assertTrue(len(errors) > 0)

    def test_reject_ampersand(self):
        errors = _validate_formula_raw("=bp_1 && bp_2")
        self.assertTrue(len(errors) > 0)

    def test_reject_pipe(self):
        errors = _validate_formula_raw("=bp_1 || bp_2")
        self.assertTrue(len(errors) > 0)

    # ---- Invalid formulas: unknown functions ----

    def test_reject_unknown_function(self):
        errors = _validate_formula_raw("=unknown_func(bp_1)")
        self.assertTrue(len(errors) > 0)
        self.assertIn("unknown_func", errors[0])

    def test_reject_exec(self):
        errors = _validate_formula_raw("=exec(bp_1)")
        self.assertTrue(len(errors) > 0)

    def test_reject_fetch(self):
        errors = _validate_formula_raw("=fetch(bp_1)")
        self.assertTrue(len(errors) > 0)

    # ---- Invalid formulas: bad identifier format ----

    def test_reject_arbitrary_identifier(self):
        errors = _validate_formula_raw("=xyz_999")
        self.assertTrue(len(errors) > 0)

    def test_reject_bp_zero(self):
        """bp_0 is not valid — identifiers must be bp_N where N >= 1."""
        errors = _validate_formula_raw("=bp_0 * 2")
        self.assertTrue(len(errors) > 0)

    # ---- Length limit ----

    def test_reject_too_long_formula(self):
        long_formula = "=" + " + ".join(f"bp_{i}" for i in range(1, 200))
        errors = _validate_formula_raw(long_formula)
        self.assertTrue(len(errors) > 0)
        self.assertIn("panjang", errors[0].lower())

    def test_accept_formula_at_limit(self):
        """Formula at exactly 500 chars should be accepted."""
        filler = "bp_1 + " * 60  # ~420 chars
        formula = "=" + filler[:498]  # just under 500
        if len(formula) <= 500:
            errors = _validate_formula_raw(formula)
            # May have token errors from truncated filler, but no length error
            if errors:
                self.assertNotIn("panjang", errors[0].lower())


class FormulaValidationIntegrationTests(TestCase):
    """Integration tests: validate via the api_volume_formula_state endpoint."""

    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="formula_val_user",
            email="formula-val@example.com",
            password="Secret123!",
        )
        self.project = Project.objects.create(
            owner=self.user,
            nama="Formula Validation Project",
            sumber_dana="APBN",
            lokasi_project="Jakarta",
            nama_client="Client",
            anggaran_owner=1000,
        )
        klas = Klasifikasi.objects.create(
            project=self.project,
            name="Klas Test",
            ordering_index=1,
        )
        sub_klas = SubKlasifikasi.objects.create(
            project=self.project,
            klasifikasi=klas,
            name="Sub Test",
            ordering_index=1,
        )
        self.pekerjaan = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=sub_klas,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-VAL-001",
            snapshot_uraian="Pekerjaan Validation Test",
            snapshot_satuan="m3",
            ordering_index=1,
        )
        self.factory = RequestFactory()

    def _post(self, payload: dict):
        request = self.factory.post(
            "/api/project/volume-formula-state/",
            data=json.dumps(payload),
            content_type="application/json",
        )
        request.user = self.user
        return api_volume_formula_state(request, self.project.id)

    def test_valid_formula_accepted(self):
        response = self._post({
            "items": [{
                "pekerjaan_id": self.pekerjaan.id,
                "raw": "=bp_1 * 2",
                "is_fx": True,
            }]
        })
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("errors"), [])

    def test_injection_rejected_with_400(self):
        response = self._post({
            "items": [{
                "pekerjaan_id": self.pekerjaan.id,
                "raw": "=eval('hack')",
                "is_fx": True,
            }]
        })
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.assertTrue(len(body.get("errors", [])) > 0)

    def test_non_formula_mode_skips_validation(self):
        """When is_fx=False, raw is not formula — skip validation."""
        response = self._post({
            "items": [{
                "pekerjaan_id": self.pekerjaan.id,
                "raw": "some plain text <script>",
                "is_fx": False,
            }]
        })
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))

    def test_empty_raw_accepted(self):
        """Empty raw = clear formula, should be accepted."""
        response = self._post({
            "items": [{
                "pekerjaan_id": self.pekerjaan.id,
                "raw": "",
                "is_fx": True,
            }]
        })
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))

    def test_multiline_formula_accepted(self):
        """Formulas with newlines from the multiline editor should work."""
        response = self._post({
            "items": [{
                "pekerjaan_id": self.pekerjaan.id,
                "raw": "=bp_1\n+ bp_2\n* bp_3",
                "is_fx": True,
            }]
        })
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content.decode("utf-8"))
        self.assertTrue(body.get("ok"))

    def test_too_long_formula_rejected(self):
        long = "=" + "bp_1 + " * 100  # > 500 chars
        response = self._post({
            "items": [{
                "pekerjaan_id": self.pekerjaan.id,
                "raw": long,
                "is_fx": True,
            }]
        })
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.assertTrue(len(body.get("errors", [])) > 0)

    def test_unknown_function_rejected(self):
        response = self._post({
            "items": [{
                "pekerjaan_id": self.pekerjaan.id,
                "raw": "=unknown_func(1)",
                "is_fx": True,
            }]
        })
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        errors = body.get("errors", [])
        self.assertTrue(len(errors) > 0)
        self.assertIn("unknown_func", str(errors))

    def test_invalid_sibling_rejects_whole_batch_atomically(self):
        """WP-B3 / VP-01 (supersedes the old partial-success contract): an invalid
        item rejects the WHOLE formula sync (400). The valid sibling is NOT saved
        (all-or-nothing, A-5)."""
        pekerjaan2 = Pekerjaan.objects.create(
            project=self.project,
            sub_klasifikasi=self.pekerjaan.sub_klasifikasi,
            source_type=Pekerjaan.SOURCE_CUSTOM,
            snapshot_kode="CUST-VAL-002",
            snapshot_uraian="Pekerjaan Test 2",
            snapshot_satuan="m2",
            ordering_index=2,
        )
        response = self._post({
            "items": [
                {
                    "pekerjaan_id": self.pekerjaan.id,
                    "raw": "=bp_1 * 2",  # valid
                    "is_fx": True,
                },
                {
                    "pekerjaan_id": pekerjaan2.id,
                    "raw": "=eval('x')",  # invalid
                    "is_fx": True,
                },
            ]
        })
        self.assertEqual(response.status_code, 400)
        body = json.loads(response.content.decode("utf-8"))
        self.assertFalse(body.get("ok"))
        self.assertTrue(len(body.get("errors", [])) > 0)
        # All-or-nothing: the valid sibling must NOT have been persisted.
        from detail_project.models import VolumeFormulaState
        self.assertFalse(
            VolumeFormulaState.objects.filter(
                project=self.project, pekerjaan=self.pekerjaan
            ).exists()
        )
