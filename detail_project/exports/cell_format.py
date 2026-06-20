"""WP Export — shared cell formatting at the text-exporter boundary.

Owner decision (2026-06-20, all Option A): the adapter hands the exporter the
canonical ``Decimal`` and each exporter formats at its own boundary. The Excel
exporter writes a real number + ``number_format`` (see ExcelExporter); the
text-based exporters (PDF / Word / CSV) cannot show a live number, so they
render the Decimal to an Indonesian-locale display string at the precision
declared by the table's ``column_formats`` — consistent 2-dp money everywhere.

``materialize_display_rows`` is a single pre-processing pass: it only touches
tables that declare ``column_formats`` (the migrated reports), so reports not
yet migrated pass through untouched.
"""
from __future__ import annotations

from decimal import Decimal


def _decimals_from_format(fmt) -> int:
    """Number of fractional digits implied by an Excel number_format token."""
    s = str(fmt)
    if '.' in s:
        frac = s.split('.', 1)[1]
        return sum(1 for c in frac if c in '0#')
    return 0


def _is_numeric_format(fmt) -> bool:
    return bool(fmt) and str(fmt).strip() not in ('@', 'text', '')


def format_cell_display(val, fmt=None) -> str:
    """Render one cell for PDF/Word/CSV.

    A Decimal/number in a numeric column becomes an id-ID string at the format's
    precision (thousands ``.``, decimal ``,``). Text columns / non-numbers (incl.
    the NULL ``-`` marker) pass through as ``str``.
    """
    if (
        _is_numeric_format(fmt)
        and isinstance(val, (Decimal, int, float))
        and not isinstance(val, bool)
    ):
        decimals = _decimals_from_format(fmt)
        formatted = f"{float(val):,.{decimals}f}"  # en-US grouping
        return formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
    return '' if val is None else str(val)


def _format_footer(section: dict) -> None:
    if not isinstance(section, dict):
        return
    fmt = section.get('footer_value_format')
    if not fmt:
        return
    new_footer = []
    for footer in section.get('footer_rows') or []:
        if isinstance(footer, (list, tuple)) and len(footer) > 1:
            new_footer.append([footer[0], format_cell_display(footer[1], fmt)])
        else:
            new_footer.append(footer)
    section['footer_rows'] = new_footer


def _format_table(table: dict) -> None:
    if not isinstance(table, dict):
        return
    fmts = table.get('column_formats') or []
    if not fmts:
        return  # not a migrated table — leave untouched
    new_rows = []
    for row in table.get('rows') or []:
        new_rows.append([
            format_cell_display(val, fmts[i] if i < len(fmts) else None)
            for i, val in enumerate(row)
        ])
    table['rows'] = new_rows


def materialize_display_rows(data: dict) -> dict:
    """In-place: format Decimal cells of column_formats-tagged tables to display
    strings, for text-based exporters. Returns ``data`` for convenience."""
    if not isinstance(data, dict):
        return data
    _format_table(data.get('table_data'))
    _format_footer(data)
    for page in data.get('pages') or []:
        if isinstance(page, dict):
            _format_table(page.get('table_data'))
            _format_footer(page)
    return data
