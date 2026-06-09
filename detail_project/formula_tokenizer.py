"""
Lightweight formula tokenizer utilities for parameter migration.

This module mirrors the identifier token behavior used by frontend formula
parsing, but keeps implementation simple for migration and remap tasks.
"""

from __future__ import annotations

from typing import Dict, List, Tuple


Token = Tuple[str, str, int, int]


def tokenize_formula(expr: str) -> List[Token]:
    """
    Tokenize formula expression.

    Returns:
        List of tokens in format: (token_type, raw_value, start_pos, end_pos)
    """
    text = str(expr or "")
    tokens: List[Token] = []
    i = 0

    while i < len(text):
        ch = text[i]

        if ch in " \t\n\r":
            i += 1
            continue

        if ch == "=" and i == 0:
            i += 1
            continue

        if ch.isalpha() or ch == "_":
            j = i + 1
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            tokens.append(("id", text[i:j], i, j))
            i = j
            continue

        if ch.isdigit() or (ch == "." and i + 1 < len(text) and text[i + 1].isdigit()):
            j = i + 1
            while j < len(text) and (text[j].isdigit() or text[j] in ".,_"):
                j += 1
            tokens.append(("num", text[i:j], i, j))
            i = j
            continue

        tokens.append(("op", ch, i, i + 1))
        i += 1

    return tokens


def remap_expression(expr: str, name_map: Dict[str, str]) -> str:
    """
    Replace identifier tokens in expression with new names.

    The replacement is span-based on original string positions so spacing and
    formatting stay unchanged.
    """
    if not expr:
        return expr

    if not name_map:
        return expr

    lowered_map = {str(k).lower(): str(v) for k, v in name_map.items()}
    result = str(expr)
    tokens = tokenize_formula(result)

    for token_type, token_value, start, end in reversed(tokens):
        if token_type != "id":
            continue
        repl = lowered_map.get(token_value.lower())
        if repl is None:
            continue
        result = result[:start] + repl + result[end:]

    return result

