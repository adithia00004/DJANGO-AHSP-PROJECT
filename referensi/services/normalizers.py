"""
Normalizers for referensi data.

Provides single source of truth for data normalization logic,
eliminating code duplication across the codebase.

PHASE 2 REFACTORING:
- Centralized category normalization
- Replaces duplicate logic in import_utils.py and normalize_referensi.py
"""

from __future__ import annotations


class KategoriNormalizer:
    """
    Normalize kategori values to standard codes (TK/BHN/ALT/LAIN).

    Single source of truth for category normalization, used by:
    - import_utils.canonicalize_kategori()
    - normalize_referensi management command
    - PreviewDetailForm.clean_kategori()
    """

    # Standard kategori codes
    TK = "TK"  # Tenaga Kerja (Labor)
    BHN = "BHN"  # Bahan (Material)
    ALT = "ALT"  # Alat (Equipment)
    LAIN = "LAIN"  # Lain-lain (Other)

    # Mapping patterns: (code, tuple_of_patterns)
    PATTERNS = (
        (
            TK,
            (
                "tk",
                "tenaga",
                "tenaga kerja",
                "upah",
                "labor",
                "pekerja",
            ),
        ),
        (
            BHN,
            (
                "bhn",
                "bahan",
                "material",
                "mat",
            ),
        ),
        (
            ALT,
            (
                "alt",
                "alat",
                "peralatan",
                "equipment",
                "equip",
                "mesin",
                "tools",
            ),
        ),
    )

    @classmethod
    def normalize(cls, value: str | None) -> str:
        """
        Normalize kategori value to standard code.

        Args:
            value: Raw category value (can be None or any case)

        Returns:
            str: Normalized kategori code (TK/BHN/ALT/LAIN)

        Examples:
            >>> KategoriNormalizer.normalize("upah")
            'TK'
            >>> KategoriNormalizer.normalize("BAHAN")
            'BHN'
            >>> KategoriNormalizer.normalize("peralatan")
            'ALT'
            >>> KategoriNormalizer.normalize("xyz")
            'LAIN'
            >>> KategoriNormalizer.normalize(None)
            'LAIN'
            >>> KategoriNormalizer.normalize("")
            'LAIN'
        """
        # Handle None or empty
        if not value:
            return cls.LAIN

        # Normalize to lowercase and strip whitespace
        normalized = str(value).strip().lower()

        if not normalized:
            return cls.LAIN

        # Check each pattern
        for code, patterns in cls.PATTERNS:
            # Exact match with code (case-insensitive)
            if normalized == code.lower():
                return code

            # Match against patterns
            for pattern in patterns:
                # Exact match
                if normalized == pattern:
                    return code
                # Starts with pattern
                if normalized.startswith(pattern):
                    return code
                # Contains pattern (for flexibility)
                if pattern in normalized:
                    return code

        # Default to LAIN if no match
        return cls.LAIN

    @classmethod
    def is_valid(cls, value: str) -> bool:
        """
        Check if value is a valid standard kategori code.

        Args:
            value: Value to check

        Returns:
            bool: True if value is TK/BHN/ALT/LAIN (case-sensitive)

        Examples:
            >>> KategoriNormalizer.is_valid("TK")
            True
            >>> KategoriNormalizer.is_valid("tk")
            False
            >>> KategoriNormalizer.is_valid("LAIN")
            True
            >>> KategoriNormalizer.is_valid("xyz")
            False
        """
        return value in {cls.TK, cls.BHN, cls.ALT, cls.LAIN}

    @classmethod
    def get_all_codes(cls) -> list[str]:
        """
        Get all valid kategori codes.

        Returns:
            list[str]: List of valid codes [TK, BHN, ALT, LAIN]
        """
        return [cls.TK, cls.BHN, cls.ALT, cls.LAIN]

    @classmethod
    def get_choices(cls) -> list[tuple[str, str]]:
        """
        Get choices for Django form field.

        Returns:
            list[tuple]: List of (code, display_name) tuples
        """
        return [
            (cls.TK, "Tenaga Kerja"),
            (cls.BHN, "Bahan"),
            (cls.ALT, "Alat"),
            (cls.LAIN, "Lain-lain"),
        ]


__all__ = ["KategoriNormalizer"]
