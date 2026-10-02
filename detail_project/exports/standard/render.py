"""Titik masuk standar template: dokumen tunggal dan Paket Perencanaan."""
from __future__ import annotations

from typing import Dict, Iterable, Tuple

from django.http import HttpResponse

from .documents import BLOCKS, TITLES


def _response(content: bytes, config, ext: str, content_type: str) -> HttpResponse:
    from ..naming import build_export_filename

    filename = build_export_filename(config.project_name, config.title, ext, config.export_date)
    resp = HttpResponse(content, content_type=content_type)
    resp['Content-Disposition'] = f'attachment; filename="{filename}"'
    return resp


def export_pdf(kind: str, data: Dict, config) -> HttpResponse:
    """Dokumen tunggal PDF (S-1: tanpa cover)."""
    from .pdf import Context, build_pdf, flowables

    ctx = Context(config)
    return _response(build_pdf(flowables(BLOCKS[kind](data), ctx), ctx, TITLES[kind]),
                     config, 'pdf', 'application/pdf')


def export_package_pdf(documents: Iterable[Tuple[str, Dict]], config) -> HttpResponse:
    """Paket Perencanaan utuh (T3): cover + daftar isi + nomor halaman berkelanjutan."""
    from reportlab.platypus import PageBreak

    from .pdf import Context, build_pdf, cover, flowables, toc_page

    ctx = Context(config)
    documents = list(documents)
    contents = ' · '.join(TITLES[kind] for kind, _ in documents)
    story = cover('DOKUMEN PERENCANAAN', ctx, contents) + [PageBreak()] + toc_page()
    for kind, data in documents:
        story.append(PageBreak())
        story += flowables(BLOCKS[kind](data), ctx)
    return _response(build_pdf(story, ctx, 'Dokumen Perencanaan', multipass=True),
                     config, 'pdf', 'application/pdf')
