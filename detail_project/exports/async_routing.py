"""Routing helpers shared by legacy async export tasks and tests."""

from __future__ import annotations

import re


def filename_from_content_disposition(value):
    if not value:
        return None
    utf8_match = re.search(r"filename\*=UTF-8''([^;]+)", value, re.IGNORECASE)
    if utf8_match:
        from urllib.parse import unquote

        return unquote(utf8_match.group(1).strip().strip('"\''))
    match = re.search(r'filename[^;=\n]*=((["\']).*?\2|[^;\n]*)', value, re.IGNORECASE)
    if match and match.group(1):
        return match.group(1).strip().strip('"\'')
    return None


def call_export_method(manager, export_type, format_type, options):
    """Route async legacy exports with the same options used by sync UI flows."""
    options = options or {}

    if export_type == 'volume-pekerjaan':
        return manager.export_volume_pekerjaan(
            format_type,
            parameters=options.get('parameters'),
        )

    if export_type == 'rincian-ahsp':
        return manager.export_rincian_ahsp(
            format_type,
            orientation=options.get('orientation'),
        )

    if export_type == 'rekap-kebutuhan':
        return manager.export_rekap_kebutuhan(
            format_type,
            mode=options.get('mode', 'all'),
            tahapan_id=options.get('tahapan_id'),
            filters=options.get('filters'),
            search=options.get('search'),
            time_scope=options.get('time_scope'),
            unit_mode=options.get('unit_mode', 'base'),
        )

    if export_type == 'jadwal-pekerjaan':
        return manager.export_jadwal_pekerjaan(
            format_type,
            attachments=options.get('attachments'),
            parameters=options.get('parameters'),
        )

    export_type_normalized = export_type.replace('-', '_')
    method_name = f"export_{export_type_normalized}"
    if not hasattr(manager, method_name):
        raise ValueError(f"Export method '{method_name}' not found in ExportManager")
    return getattr(manager, method_name)(format_type)
