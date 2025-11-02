"""
Tests for normalizers module.

PHASE 2: Testing KategoriNormalizer for single source of truth.
"""

import pytest

from referensi.services.normalizers import KategoriNormalizer


class TestKategoriNormalizer:
    """Test KategoriNormalizer class."""

    def test_normalize_tk_exact_match(self):
        """Test exact match for TK."""
        assert KategoriNormalizer.normalize("TK") == "TK"
        assert KategoriNormalizer.normalize("tk") == "TK"
        assert KategoriNormalizer.normalize("Tk") == "TK"

    def test_normalize_tk_patterns(self):
        """Test various patterns that should normalize to TK."""
        assert KategoriNormalizer.normalize("upah") == "TK"
        assert KategoriNormalizer.normalize("UPAH") == "TK"
        assert KategoriNormalizer.normalize("Upah") == "TK"
        assert KategoriNormalizer.normalize("tenaga") == "TK"
        assert KategoriNormalizer.normalize("tenaga kerja") == "TK"
        assert KategoriNormalizer.normalize("pekerja") == "TK"
        assert KategoriNormalizer.normalize("labor") == "TK"
        assert KategoriNormalizer.normalize("TENAGA KERJA") == "TK"

    def test_normalize_bhn_exact_match(self):
        """Test exact match for BHN."""
        assert KategoriNormalizer.normalize("BHN") == "BHN"
        assert KategoriNormalizer.normalize("bhn") == "BHN"
        assert KategoriNormalizer.normalize("Bhn") == "BHN"

    def test_normalize_bhn_patterns(self):
        """Test various patterns that should normalize to BHN."""
        assert KategoriNormalizer.normalize("bahan") == "BHN"
        assert KategoriNormalizer.normalize("BAHAN") == "BHN"
        assert KategoriNormalizer.normalize("material") == "BHN"
        assert KategoriNormalizer.normalize("Material") == "BHN"
        assert KategoriNormalizer.normalize("mat") == "BHN"

    def test_normalize_alt_exact_match(self):
        """Test exact match for ALT."""
        assert KategoriNormalizer.normalize("ALT") == "ALT"
        assert KategoriNormalizer.normalize("alt") == "ALT"
        assert KategoriNormalizer.normalize("Alt") == "ALT"

    def test_normalize_alt_patterns(self):
        """Test various patterns that should normalize to ALT."""
        assert KategoriNormalizer.normalize("alat") == "ALT"
        assert KategoriNormalizer.normalize("ALAT") == "ALT"
        assert KategoriNormalizer.normalize("peralatan") == "ALT"
        assert KategoriNormalizer.normalize("equipment") == "ALT"
        assert KategoriNormalizer.normalize("Equipment") == "ALT"
        assert KategoriNormalizer.normalize("equip") == "ALT"
        assert KategoriNormalizer.normalize("mesin") == "ALT"
        assert KategoriNormalizer.normalize("tools") == "ALT"

    def test_normalize_lain_exact_match(self):
        """Test exact match for LAIN."""
        assert KategoriNormalizer.normalize("LAIN") == "LAIN"
        assert KategoriNormalizer.normalize("lain") == "LAIN"
        assert KategoriNormalizer.normalize("Lain") == "LAIN"

    def test_normalize_lain_unknown(self):
        """Test unknown values normalize to LAIN."""
        assert KategoriNormalizer.normalize("xyz") == "LAIN"
        assert KategoriNormalizer.normalize("unknown") == "LAIN"
        assert KategoriNormalizer.normalize("???") == "LAIN"
        assert KategoriNormalizer.normalize("12345") == "LAIN"

    def test_normalize_empty_values(self):
        """Test empty and None values normalize to LAIN."""
        assert KategoriNormalizer.normalize(None) == "LAIN"
        assert KategoriNormalizer.normalize("") == "LAIN"
        assert KategoriNormalizer.normalize("   ") == "LAIN"
        assert KategoriNormalizer.normalize("\t") == "LAIN"

    def test_normalize_with_whitespace(self):
        """Test normalization strips whitespace."""
        assert KategoriNormalizer.normalize("  tk  ") == "TK"
        assert KategoriNormalizer.normalize("\tupah\n") == "TK"
        assert KategoriNormalizer.normalize("  bahan  ") == "BHN"
        assert KategoriNormalizer.normalize("  alat  ") == "ALT"

    def test_normalize_case_insensitive(self):
        """Test normalization is case-insensitive."""
        assert KategoriNormalizer.normalize("UPAH") == "TK"
        assert KategoriNormalizer.normalize("upah") == "TK"
        assert KategoriNormalizer.normalize("Upah") == "TK"
        assert KategoriNormalizer.normalize("uPaH") == "TK"

    def test_normalize_contains_pattern(self):
        """Test normalization when value contains pattern."""
        assert KategoriNormalizer.normalize("upah pekerja") == "TK"
        assert KategoriNormalizer.normalize("bahan material") == "BHN"
        assert KategoriNormalizer.normalize("alat equipment") == "ALT"

    def test_is_valid_true(self):
        """Test is_valid returns True for valid codes."""
        assert KategoriNormalizer.is_valid("TK") is True
        assert KategoriNormalizer.is_valid("BHN") is True
        assert KategoriNormalizer.is_valid("ALT") is True
        assert KategoriNormalizer.is_valid("LAIN") is True

    def test_is_valid_false_case_sensitive(self):
        """Test is_valid is case-sensitive."""
        assert KategoriNormalizer.is_valid("tk") is False
        assert KategoriNormalizer.is_valid("bhn") is False
        assert KategoriNormalizer.is_valid("alt") is False
        assert KategoriNormalizer.is_valid("lain") is False
        assert KategoriNormalizer.is_valid("Tk") is False

    def test_is_valid_false_invalid_values(self):
        """Test is_valid returns False for invalid values."""
        assert KategoriNormalizer.is_valid("xyz") is False
        assert KategoriNormalizer.is_valid("upah") is False
        assert KategoriNormalizer.is_valid("") is False
        assert KategoriNormalizer.is_valid(None) is False

    def test_get_all_codes(self):
        """Test get_all_codes returns all valid codes."""
        codes = KategoriNormalizer.get_all_codes()
        assert codes == ["TK", "BHN", "ALT", "LAIN"]
        assert len(codes) == 4

    def test_get_choices(self):
        """Test get_choices returns Django form choices."""
        choices = KategoriNormalizer.get_choices()
        assert len(choices) == 4
        assert choices[0] == ("TK", "Tenaga Kerja")
        assert choices[1] == ("BHN", "Bahan")
        assert choices[2] == ("ALT", "Alat")
        assert choices[3] == ("LAIN", "Lain-lain")

    def test_normalize_backwards_compatibility(self):
        """Test normalization matches old canonicalize_kategori behavior."""
        # These should match the old _KATEGORI_PATTERNS behavior
        old_patterns = [
            ("tk", "TK"),
            ("tenaga", "TK"),
            ("tenaga kerja", "TK"),
            ("upah", "TK"),
            ("labor", "TK"),
            ("pekerja", "TK"),
            ("bhn", "BHN"),
            ("bahan", "BHN"),
            ("material", "BHN"),
            ("mat", "BHN"),
            ("alt", "ALT"),
            ("alat", "ALT"),
            ("peralatan", "ALT"),
            ("equipment", "ALT"),
            ("mesin", "ALT"),
            ("tools", "ALT"),
        ]

        for input_val, expected in old_patterns:
            assert KategoriNormalizer.normalize(input_val) == expected

    def test_normalize_startswith_pattern(self):
        """Test normalization when value starts with pattern."""
        assert KategoriNormalizer.normalize("tk123") == "TK"
        assert KategoriNormalizer.normalize("bahan-extra") == "BHN"
        assert KategoriNormalizer.normalize("alat-123") == "ALT"
