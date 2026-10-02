"""Renderer PDF standar dokumen perencanaan (ReportLab).

Komponen: kanvas header/footer bernomor ("Halaman x dari y"), kepala dokumen
(judul + garis aksen + panel identitas dua kolom), tabel standar (hierarki R-25,
arsir minimal), blok total, lembar pengesahan menempel (R-13/R-37), cover +
daftar isi (paket). Payload = keluaran adapter export yang sama dengan jalur lama.
"""
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, TableStyle,
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.platypus.tableofcontents import TableOfContents

from . import tokens as T
from .fonts import font
from .format import id_label

from .. import pdf_exporter as _legacy
from ..table_styles import ROW_MIN_HEIGHT_CM, ROW_MIN_HEIGHT_RINCIAN_CM


class Table(_legacy.Table):
    """Tabel dengan tinggi baris MINIMUM per tabel (keputusan owner 2026-09-22).

    Memakai mekanisme yang sama dengan jalur lama (`pdf_exporter.Table._calc`),
    tetapi ambangnya per tabel: tabel data 0,7 cm, tabel ringkas Rincian 0,4 cm.
    Panel identitas, blok total, dan pengesahan tidak ditegakkan.
    """

    floor_cm = ROW_MIN_HEIGHT_CM

    def _calc(self, availWidth, availHeight):
        previous = _legacy._ACTIVE_MIN_ROW_HEIGHT[0]
        _legacy._ACTIVE_MIN_ROW_HEIGHT[0] = self.floor_cm * cm
        try:
            super()._calc(availWidth, availHeight)
        finally:
            _legacy._ACTIVE_MIN_ROW_HEIGHT[0] = previous


def _layout_table(*args, **kwargs) -> Table:
    """Tabel tata letak (panel, blok total, pengesahan): tanpa tinggi minimum."""
    t = Table(*args, **kwargs)
    t.enforce_min_row_height = False
    return t


PAGE_W, PAGE_H = A4
M_LR = T.PAGE_MARGIN_LR * mm
M_TOP = T.PAGE_MARGIN_TOP * mm
M_BOTTOM = T.PAGE_MARGIN_BOTTOM * mm
CONTENT_W = PAGE_W - 2 * M_LR


def hexcolor(value: str):
    return colors.HexColor(value)


# ------------------------------------------------------------------ gaya ----
def _style(name, size=T.SIZE_BODY, weight='Std', color=T.TEXT, align=TA_LEFT, leading=None, **kw):
    return ParagraphStyle(name, fontName=font(weight), fontSize=size,
                          leading=leading or round(size * 1.28, 2),
                          textColor=hexcolor(color), alignment=align, **kw)


_STYLES: Dict[str, ParagraphStyle] = {}


def S(name: str) -> ParagraphStyle:
    if not _STYLES:
        _STYLES.update({
            'cell': _style('std_cell'),
            'cell_c': _style('std_cell_c', align=TA_CENTER),
            'cell_r': _style('std_cell_r', align=TA_RIGHT),
            'cell_b': _style('std_cell_b', weight='Std-Bold'),
            'cell_br': _style('std_cell_br', weight='Std-Bold', align=TA_RIGHT),
            'klas': _style('std_klas', T.SIZE_CATEGORY, 'Std-Bold'),
            'klas_r': _style('std_klas_r', T.SIZE_CATEGORY, 'Std-Bold', align=TA_RIGHT),
            'sub': _style('std_sub', T.SIZE_SUBCATEGORY, 'Std-BoldItalic'),
            'sub_r': _style('std_sub_r', T.SIZE_SUBCATEGORY, 'Std-BoldItalic', align=TA_RIGHT),
            'head': _style('std_head', T.SIZE_HEADER, 'Std-Bold', T.WHITE, TA_CENTER, 9.2),
            'title': _style('std_title', T.SIZE_DOC_TITLE, 'Std-Bold', T.NAVY_DARK, TA_CENTER, 19),
            'subtitle': _style('std_subtitle', T.SIZE_SUBTITLE, 'Std', T.TEXT2, TA_CENTER),
            'section': _style('std_section', T.SIZE_SECTION, 'Std-Bold', T.ACCENT,
                              spaceBefore=2 * mm, spaceAfter=1.5 * mm),
            'label': _style('std_label', T.SIZE_BODY, 'Std-Bold', T.TEXT2),
            'value': _style('std_value', T.SIZE_BODY),
            'sig_inst': _style('std_sig_inst', T.SIZE_SIGNATURE, 'Std-Bold', align=TA_CENTER),
            'sig_name': _style('std_sig_name', T.SIZE_SIGNATURE, 'Std-Bold', align=TA_CENTER),
            'sig_det': _style('std_sig_det', 7.5, 'Std', T.TEXT2, TA_CENTER),
            'sig_title': _style('std_sig_title', 9, 'Std-Bold', spaceBefore=4 * mm, spaceAfter=2 * mm),
            'note': _style('std_note', T.SIZE_NOTE, 'Std-Italic', T.MUTED),
            'toc': _style('std_toc', 9.5, 'Std', leading=16),
            'r_cell': _style('std_r_cell', T.RINCIAN_SIZE_BODY, leading=T.RINCIAN_LEADING),
            'r_cell_c': _style('std_r_cell_c', T.RINCIAN_SIZE_BODY, align=TA_CENTER, leading=T.RINCIAN_LEADING),
            'r_cell_r': _style('std_r_cell_r', T.RINCIAN_SIZE_BODY, align=TA_RIGHT, leading=T.RINCIAN_LEADING),
            'r_cell_br': _style('std_r_cell_br', T.RINCIAN_SIZE_BODY, 'Std-Bold', align=TA_RIGHT,
                                leading=T.RINCIAN_LEADING),
            'r_sub': _style('std_r_sub', T.RINCIAN_SIZE_GROUP, 'Std-BoldItalic', leading=8),
            'r_sub_r': _style('std_r_sub_r', T.RINCIAN_SIZE_GROUP, 'Std-BoldItalic', align=TA_RIGHT, leading=8),
            'r_klas': _style('std_r_klas', 7, 'Std-Bold', leading=8.4),
            'r_klas_r': _style('std_r_klas_r', 7, 'Std-Bold', align=TA_RIGHT, leading=8.4),
            'r_head': _style('std_r_head', T.RINCIAN_SIZE_BODY, 'Std-Bold', T.WHITE, TA_CENTER, 7.6),
            'r_heading': _style('std_r_heading', T.RINCIAN_SIZE_HEADING, 'Std-Bold', T.ACCENT,
                                spaceBefore=1 * mm, spaceAfter=1 * mm, leading=10),
        })
    return _STYLES[name]


def esc(text) -> str:
    return (str('' if text is None else text)
            .replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def P(text, style: str = 'cell') -> Paragraph:
    return Paragraph(esc(text).replace('\n', '<br/>'), S(style))


# --------------------------------------------------------------- kanvas ----
class StdCanvas(Canvas):
    """Header berjalan (proyek | dokumen) + footer 'Halaman x dari y' | brand.

    Halaman bertanda cover tidak diberi header/footer, hanya bingkai.
    """

    project = ''

    def __init__(self, *args, **kwargs):
        Canvas.__init__(self, *args, **kwargs)
        self._pages: List[dict] = []
        self.doc_name = ''
        self.cover = False

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self.cover = False
        self._startPage()

    def save(self):
        total = len(self._pages)
        for state in self._pages:
            self.__dict__.update(state)
            if self.cover:
                self._cover_frame()
            else:
                self._decorate(total)
            Canvas.showPage(self)
        Canvas.save(self)

    def _cover_frame(self):
        self.setStrokeColor(hexcolor(T.ACCENT))
        self.setLineWidth(1.5)
        self.rect(M_LR, M_BOTTOM, CONTENT_W, PAGE_H - M_TOP - M_BOTTOM + 4 * mm)

    def _decorate(self, total: int):
        top = PAGE_H - 11 * mm
        self.setFont(font('Std'), T.SIZE_RUNNING)
        self.setFillColor(hexcolor(T.TEXT2))
        name = self.project or ''
        if len(name) > 72:
            name = name[:69].rsplit(' ', 1)[0] + '…'
        self.drawString(M_LR, top, name)
        self.drawRightString(PAGE_W - M_LR, top, self.doc_name or '')
        self.setStrokeColor(hexcolor(T.GRID))
        self.setLineWidth(0.5)
        self.line(M_LR, top - 2 * mm, PAGE_W - M_LR, top - 2 * mm)
        bottom = 9 * mm
        self.line(M_LR, bottom + 4 * mm, PAGE_W - M_LR, bottom + 4 * mm)
        self.setFillColor(hexcolor(T.MUTED))
        self.drawCentredString(PAGE_W / 2, bottom, f"Halaman {self._pageNumber} dari {total}")
        self.drawRightString(PAGE_W - M_LR, bottom, T.BRAND)


class Mark(Flowable):
    """Penanda tak terlihat: nama dokumen di header, cover, entri daftar isi."""

    def __init__(self, doc_name: Optional[str] = None, cover: bool = False,
                 toc: Optional[str] = None, level: int = 0):
        super().__init__()
        self.doc_name, self.cover, self.toc, self.level = doc_name, cover, toc, level
        self.width = self.height = 0

    def wrap(self, *_):
        return 0, 0

    def draw(self):
        if self.doc_name is not None:
            self.canv.doc_name = self.doc_name
        if self.cover:
            self.canv.cover = True


class StdDoc(BaseDocTemplate):
    def __init__(self, buffer, project: str, title: str):
        super().__init__(buffer, pagesize=A4, leftMargin=M_LR, rightMargin=M_LR,
                         topMargin=M_TOP, bottomMargin=M_BOTTOM, title=title, author='Dashboard-RAB')
        frame = Frame(M_LR, M_BOTTOM, CONTENT_W, PAGE_H - M_TOP - M_BOTTOM, id='f',
                      leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate(id='p', frames=[frame])])
        self.project = project

    def afterFlowable(self, flowable):
        if isinstance(flowable, Mark) and flowable.toc:
            key = f"toc-{self.seq.nextf('toc')}"
            self.canv.bookmarkPage(key)
            self.notify('TOCEntry', (flowable.level, flowable.toc, self.page, key))


# ------------------------------------------------------------ komponen ----
class Context:
    """Data pendamping dari ExportConfig: proyek, identitas, penanda tangan."""

    def __init__(self, config):
        from ...export_config import build_identity_rows

        self.config = config
        self.project = getattr(config, 'project_name', '') or ''
        self.identity = [(row[0], row[2]) for row in build_identity_rows(config)]
        sig_cfg = getattr(config, 'signature_config', None)
        sigs = []
        if sig_cfg is not None and getattr(sig_cfg, 'enabled', False):
            sigs = sig_cfg.custom_signatures or sig_cfg.signatures or []
        self.signatures = list(sigs)


def identity_panel(identity: Sequence) -> Table:
    half = (len(identity) + 1) // 2
    left, right = list(identity[:half]), list(identity[half:])
    rows = []
    for i in range(half):
        lrow = left[i] if i < len(left) else ('', '')
        rrow = right[i] if i < len(right) else ('', '')
        rows.append([
            P(lrow[0], 'label'), P(':' if lrow[0] else '', 'label'), P(lrow[1], 'value') if lrow[0] else '',
            '',
            P(rrow[0], 'label'), P(':' if rrow[0] else '', 'label'), P(rrow[1], 'value') if rrow[0] else '',
        ])
    w = CONTENT_W
    t = _layout_table(rows, colWidths=[27 * mm, 3 * mm, w / 2 - 33 * mm, 6 * mm, 28 * mm, 3 * mm, w / 2 - 34 * mm])
    t.setStyle(TableStyle([
        # Tanpa latar (owner 2026-10-02): hanya bingkai tipis.
        ('BOX', (0, 0), (2, -1), 0.5, hexcolor(T.GRID)), ('BOX', (4, 0), (6, -1), 0.5, hexcolor(T.GRID)),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 1.1 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.1 * mm),
        ('LEFTPADDING', (0, 0), (-1, -1), 1.6 * mm), ('RIGHTPADDING', (0, 0), (-1, -1), 1.2 * mm),
        ('LEFTPADDING', (1, 0), (1, -1), 0), ('RIGHTPADDING', (1, 0), (1, -1), 0),
        ('LEFTPADDING', (5, 0), (5, -1), 0), ('RIGHTPADDING', (5, 0), (5, -1), 0),
    ]))
    return t


def doc_header(title: str, ctx: Context, subtitle: Optional[str] = None, toc: bool = True) -> list:
    name = title.title()
    out = [Mark(doc_name=name, toc=name if toc else None), Paragraph(esc(title), S('title'))]
    if subtitle:
        out.append(Paragraph(esc(subtitle), S('subtitle')))
    out += [Spacer(1, 2 * mm),
            HRFlowable(width=T.TITLE_RULE_WIDTH * mm, thickness=0.8, color=hexcolor(T.ACCENT), hAlign='CENTER'),
            Spacer(1, 4 * mm), identity_panel(ctx.identity), Spacer(1, 5 * mm)]
    return out


def data_table(headers, rows, widths, kinds=None, aligns=None, span_to=None,
               repeat=True, header=True, compact=False) -> Table:
    """Tabel standar.

    kinds per baris: 'klas' (diarsir tint muda) | 'sub' (tanpa latar, tebal-miring) |
    'item' | 'total' (tanpa latar, tebal, label digabung rata kanan) | 'grand' (krem).
    aligns per kolom: 'l' | 'c' | 'r'. span_to: kolom terakhir yang digabung pada
    baris klas/sub (sisanya untuk subtotal); None = gabung semua.
    compact: gaya Rincian AHSP (baris 0,4 cm, huruf 6,5 pt).
    """
    kinds = kinds or ['item'] * len(rows)
    aligns = aligns or ['l'] * len(headers)
    pre = 'r_' if compact else ''
    total_w = float(sum(widths))
    col_w = [w * CONTENT_W / total_w for w in widths]

    def PC(text, name):
        key = pre + name
        if compact and key not in ('r_cell', 'r_cell_c', 'r_cell_r', 'r_cell_br', 'r_sub', 'r_sub_r',
                                   'r_klas', 'r_klas_r', 'r_head'):
            key = name
        return Paragraph(esc(text).replace('\n', '<br/>'), S(key))

    pad_v = (T.RINCIAN_PAD_V_MM if compact else T.CELL_PAD_V) * mm
    pad_h = (T.RINCIAN_PAD_H_MM if compact else T.CELL_PAD_H) * mm
    data = [[PC(h, 'head') for h in headers]] if header else []
    off = 1 if header else 0
    cmds = [
        ('GRID', (0, 0), (-1, -1), 0.4, hexcolor(T.GRID)),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), pad_v), ('BOTTOMPADDING', (0, 0), (-1, -1), pad_v),
        ('LEFTPADDING', (0, 0), (-1, -1), pad_h), ('RIGHTPADDING', (0, 0), (-1, -1), pad_h),
        # Sel kosong (string) ikut ukuran huruf tabel, bukan bawaan 10 pt.
        ('FONTSIZE', (0, 0), (-1, -1), T.RINCIAN_SIZE_BODY if compact else T.SIZE_BODY),
        ('LEADING', (0, 0), (-1, -1), T.RINCIAN_LEADING if compact else 9.6),
    ]
    if header:
        cmds.append(('BACKGROUND', (0, 0), (-1, 0), hexcolor(T.NAVY_DARK)))
    amap = {'l': 'cell', 'c': 'cell_c', 'r': 'cell_r'}
    ncol = len(headers)
    for r_idx, (row, kind) in enumerate(zip(rows, kinds), start=off):
        row = list(row) + [''] * (ncol - len(row))
        if kind in ('klas', 'sub'):
            last = ncol - 1 if span_to is None else span_to
            label = next((c for c in row if c not in (None, '')), '')
            cells = [PC(label, kind)] + [''] * last
            if span_to is not None:
                for c in range(last + 1, ncol):
                    cells.append(PC(row[c], f'{kind}_r') if row[c] not in (None, '') else '')
            data.append(cells[:ncol])
            cmds.append(('SPAN', (0, r_idx), (last, r_idx)))
            if kind == 'klas':
                cmds.append(('BACKGROUND', (0, r_idx), (-1, r_idx), hexcolor(T.KLAS_BG)))
        elif kind in ('total', 'grand'):
            label = next((c for c in row[:-1] if c not in (None, '')), '')
            data.append([PC(label, 'cell_br')] + [''] * (ncol - 2) + [PC(row[-1], 'cell_br')])
            cmds.append(('SPAN', (0, r_idx), (ncol - 2, r_idx)))
            if kind == 'grand':
                cmds.append(('BACKGROUND', (0, r_idx), (-1, r_idx), hexcolor(T.GRAND_BG)))
        else:
            data.append([PC(v, amap[aligns[i]]) for i, v in enumerate(row[:ncol])])
    t = Table(data, colWidths=col_w, repeatRows=1 if (repeat and header) else 0)
    t.floor_cm = ROW_MIN_HEIGHT_RINCIAN_CM if compact else ROW_MIN_HEIGHT_CM
    t.setStyle(TableStyle(cmds))
    return t


def totals_block(pairs, emphasize_last: bool = True) -> Table:
    rows = [[P(id_label(lbl), 'cell_br'), P(val, 'cell_br')] for lbl, val in pairs]
    t = _layout_table(rows, colWidths=[T.TOTAL_BLOCK_WIDTH[0] * mm, T.TOTAL_BLOCK_WIDTH[1] * mm], hAlign='RIGHT')
    cmds = [('LINEABOVE', (0, 0), (-1, 0), 0.8, hexcolor(T.ACCENT)),
            ('TOPPADDING', (0, 0), (-1, -1), 1.2 * mm), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.2 * mm)]
    if emphasize_last and len(rows) > 1:
        cmds += [('LINEABOVE', (0, -1), (-1, -1), 1.2, hexcolor(T.NAVY_DARK)),
                 ('BACKGROUND', (0, -1), (-1, -1), hexcolor(T.GRAND_BG))]
    t.setStyle(TableStyle(cmds))
    return t


def signature_block(signatures) -> list:
    """Pengesahan R-37: INSTANSI / ruang 20 mm (R-23) / NAMA bergaris bawah / keterangan."""
    from ..signature_config import SIGNATURE_SPACE_MM

    if not signatures:
        return []
    n = len(signatures)
    col = CONTENT_W / n
    details = [list(s.get('details') or []) for s in signatures]
    max_det = max((len(d) for d in details), default=0)
    rows = [
        [P((s.get('instansi') or s.get('position') or ''), 'sig_inst') for s in signatures],
        [Spacer(1, SIGNATURE_SPACE_MM * mm) for _ in signatures],
        [Paragraph(f"<u>{esc(s.get('name') or '')}</u>", S('sig_name')) for s in signatures],
    ]
    for i in range(max_det):
        rows.append([P(d[i], 'sig_det') if i < len(d) and d[i] else '' for d in details])
    t = _layout_table(rows, colWidths=[col] * n)
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, 0), 'BOTTOM'), ('VALIGN', (0, 1), (-1, -1), 'TOP'),
                           ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0.6 * mm)]))
    return [Paragraph('LEMBAR PENGESAHAN', S('sig_title')), t]


def cover(kind: str, ctx: Context, contents: str) -> list:
    return [
        Mark(cover=True),
        Spacer(1, 55 * mm),
        Paragraph(esc(kind), _style('std_cv1', 22, 'Std-Bold', T.NAVY_DARK, TA_CENTER, 28)),
        Spacer(1, 5 * mm),
        HRFlowable(width=60 * mm, thickness=1, color=hexcolor(T.ACCENT), hAlign='CENTER'),
        Spacer(1, 7 * mm),
        Paragraph(esc(ctx.project), _style('std_cv2', 15, 'Std-Bold', T.NAVY_DARK, TA_CENTER, 19,
                                           leftIndent=12 * mm, rightIndent=12 * mm)),
        Spacer(1, 5 * mm),
        Paragraph(esc(contents), _style('std_cv3', 9, 'Std', T.TEXT2, TA_CENTER, 12,
                                        leftIndent=14 * mm, rightIndent=14 * mm)),
        Spacer(1, 14 * mm),
        _cover_identity(ctx),
    ]


def _cover_identity(ctx: Context) -> Table:
    rows = [[P(lbl, 'label'), P(':', 'label'), P(val, 'value')]
            for lbl, val in ctx.identity if lbl.lower() != 'proyek']
    t = _layout_table(rows, colWidths=[38 * mm, 4 * mm, 100 * mm], hAlign='CENTER')
    t.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'),
                           ('LEFTPADDING', (1, 0), (1, -1), 0), ('RIGHTPADDING', (1, 0), (1, -1), 0),
                           ('TOPPADDING', (0, 0), (-1, -1), 1.6 * mm),
                           ('BOTTOMPADDING', (0, 0), (-1, -1), 1.6 * mm)]))
    return t


def toc_page() -> list:
    toc = TableOfContents(dotsMinLevel=0, rightColumnWidth=14 * mm, levelStyles=[S('toc')])
    return [Mark(doc_name='Daftar Isi'), Paragraph('DAFTAR ISI', S('title')), Spacer(1, 2 * mm),
            HRFlowable(width=T.TITLE_RULE_WIDTH * mm, thickness=0.8, color=hexcolor(T.ACCENT), hAlign='CENTER'),
            Spacer(1, 6 * mm), toc]


# ------------------------------------------------------- blok -> flowable ----
def flowables(blocks: list, ctx: 'Context') -> list:
    """Terjemahkan blok netral (documents.py) menjadi flowable ReportLab."""
    out: list = []
    for block in blocks:
        kind = block[0]
        if kind == 'header':
            out += doc_header(block[1], ctx, subtitle=block[2])
        elif kind == 'section':
            out.append(Paragraph(esc(block[1]), S('section')))
        elif kind == 'heading':
            out.append(Paragraph(esc(block[1]), S('r_heading')))
        elif kind == 'table':
            spec = block[1]
            out.append(data_table(spec['headers'], spec['rows'], spec['widths'], spec['kinds'], spec['aligns'],
                                  spec['span_to'], header=spec['header'], compact=spec['compact']))
        elif kind == 'totals':
            out.append(totals_block(block[1], emphasize_last=block[2]))
        elif kind == 'note':
            out.append(Paragraph(esc(block[1]), S('note')))
        elif kind == 'spacer':
            out.append(Spacer(1, block[1] * mm))
        elif kind == 'signature':
            out += signature_block(ctx.signatures)
        elif kind == 'keep':
            inner = flowables(block[1], ctx)
            if inner:
                out.append(KeepTogether(inner))
        elif kind == 'pagebreak':
            out.append(PageBreak())
        else:  # pragma: no cover - jenis blok baru wajib ditangani di sini
            raise ValueError(f'blok tidak dikenal: {kind}')
    return out


# --------------------------------------------------------------- render ----
def build_pdf(story: list, ctx: Context, title: str, multipass: bool = False) -> bytes:
    buffer = BytesIO()
    doc = StdDoc(buffer, ctx.project, title)
    StdCanvas.project = ctx.project
    if multipass:
        doc.multiBuild(story, canvasmaker=StdCanvas)
    else:
        doc.build(story, canvasmaker=StdCanvas)
    return buffer.getvalue()
