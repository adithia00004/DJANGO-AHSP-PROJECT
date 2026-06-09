"""Unit tests for the AHSP code single-source-of-truth helper."""

import pytest

from referensi.services.ahsp_code import (
    CLASSIFICATION,
    INVALID,
    PARENT,
    SUBCLASSIFICATION,
    classify_ahsp_code,
    extract_ahsp_code,
    is_ahsp_code,
    normalize_ahsp_code,
    numeric_segment_count,
    parse_ahsp_code,
    split_ahsp_title,
)


@pytest.mark.parametrize(
    "code",
    [
        "1.1",
        "1.1.1",
        "1.1.1.1",
        "1.1.1.1.5",
        "2.2.1.1.5.a",
        "2.2.1.1.5.b",
        "2.2.1.1.5.c",
        "1.1.1.a",  # suffix allowed at 3+ numeric segments (locked rule)
        "10.20.300",  # 3-digit segments allowed
    ],
)
def test_valid_codes(code):
    assert is_ahsp_code(code) is True


@pytest.mark.parametrize(
    "code",
    [
        "",
        None,
        "1",  # single numeric segment
        "1.a",  # suffix on a single numeric segment
        "1.1.a",  # suffix on only 2 numeric segments
        "2.2.a.1",  # letter in the middle
        "2.2.1.a.5",  # letter in the middle
        "2.2.1.1.5.aa",  # multi-letter suffix
        "2.2.1.1.5.a.1",  # numeric segment after suffix
        "2.2.1.1.5.a.b",  # double suffix
        "1.1.1.1.1.1",  # 6 numeric segments (over max)
        "0.1.1.1",  # first segment zero
        "1.01.1.1",  # leading-zero multi-digit segment
        "1.1.1.1234",  # 4-digit segment
        "U.3.4.1",  # alphabetic first segment
        "abc",
    ],
)
def test_invalid_codes(code):
    assert is_ahsp_code(code) is False
    assert classify_ahsp_code(code) == INVALID
    assert normalize_ahsp_code(code) == ""


def test_classification_by_numeric_count():
    assert classify_ahsp_code("1.1") == CLASSIFICATION
    assert classify_ahsp_code("1.1.1") == SUBCLASSIFICATION
    assert classify_ahsp_code("1.1.1.1") == PARENT
    assert classify_ahsp_code("1.1.1.1.5") == PARENT
    assert classify_ahsp_code("2.2.1.1.5.a") == PARENT
    # Suffix does not change the tier; classification uses numeric count only.
    assert classify_ahsp_code("1.1.1.a") == SUBCLASSIFICATION


def test_numeric_segment_count_excludes_suffix():
    assert numeric_segment_count("2.2.1.1.5.a") == 5
    assert numeric_segment_count("1.1.1.1") == 4
    assert numeric_segment_count("invalid") == 0


def test_parse_returns_segments_and_suffix():
    assert parse_ahsp_code("2.2.1.1.5.a") == (["2", "2", "1", "1", "5"], "a")
    assert parse_ahsp_code("1.1.1.1") == (["1", "1", "1", "1"], None)


def test_normalize_lowercases_suffix_and_trims():
    assert normalize_ahsp_code("  2.2.1.1.5.A  ") == "2.2.1.1.5.a"
    assert normalize_ahsp_code("1.1.1.1") == "1.1.1.1"


def test_extract_code_from_title_line():
    assert extract_ahsp_code("1.1.1.1 Nama Judul") == "1.1.1.1"
    assert extract_ahsp_code("2.2.1.1.5.a Nama Judul") == "2.2.1.1.5.a"
    assert extract_ahsp_code("2.2.1.1.5.A Nama Judul") == "2.2.1.1.5.a"
    assert extract_ahsp_code("Bukan kode apa pun") is None


def test_split_title_numeric_and_suffix():
    assert split_ahsp_title("1.1.1.1 Nama Judul") == ("1.1.1.1", "Nama Judul")
    assert split_ahsp_title("2.2.1.1.5.a Nama Judul") == ("2.2.1.1.5.a", "Nama Judul")
    # Separator between code and title is stripped.
    assert split_ahsp_title("1.1.1.1 - Nama Judul") == ("1.1.1.1", "Nama Judul")
    # Non-code lines fall back to (None, text).
    assert split_ahsp_title("Catatan kaki") == (None, "Catatan kaki")
