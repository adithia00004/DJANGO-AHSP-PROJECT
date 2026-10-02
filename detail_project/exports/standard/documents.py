"""Penyusun isi dokumen perencanaan dengan standar template.

Setiap fungsi menerima payload export yang SAMA dengan jalur lama (keluaran
adapter / ``ExportManager._build_rekap_rab_data``) dan mengembalikan daftar
BLOK netral. Blok diterjemahkan oleh ``pdf_render`` (ReportLab) dan
``word_render`` (python-docx) sehingga isi PDF dan Word selalu sama (S-8).

Jenis blok (tuple, elemen pertama = jenis):
  ('header', title, subtitle|None)        kepala dokumen (judul + panel identitas)
  ('section', text)                       judul seksi (mis. periode Rekap Kebutuhan)
  ('heading', text)                       judul pekerjaan Rincian (ringkas)
  ('table', spec)                         spec: dict headers/rows/widths/kinds/aligns/span_to/compact/header
  ('totals', pairs, emphasize_last)       blok total rata kanan
  ('note', text)                          catatan kecil miring
  ('spacer', mm)
  ('signature',)                          lembar pengesahan (R-37)
  ('keep', [blok...])                     dijaga satu halaman (R-13)
  ('pagebreak',)
"""
from __future__ import annotations

from decimal import Decimal
from typing import Callable, Dict, List

from .format import dec, drop_empty_columns, id_label, kinds_from, kinds_from_levels, num


def table(headers, rows, widths, kinds=None, aligns=None, span_to=None, compact=False, header=True):
    return ('table', {
        'headers': list(headers), 'rows': [list(r) for r in rows], 'widths': list(widths),
        'kinds': list(kinds or ['item'] * len(rows)), 'aligns': list(aligns or ['l'] * len(headers)),
        'span_to': span_to, 'compact': compact, 'header': header,
    })


def closing(parts: list) -> list:
    """Bagian akhir + pengesahan dijaga satu halaman (R-13/R-38)."""
    return [('keep', parts + [('spacer', 3), ('signature',)])]


def split_tail(headers, rows, widths, kinds, aligns, span_to=None, tail=3, compact=False):
    """Pisahkan N baris terakhir agar bisa menempel pada blok total/pengesahan."""
    if len(rows) <= tail + 2:
        return [], table(headers, rows, widths, kinds, aligns, span_to, compact)
    head = table(headers, rows[:-tail], widths, kinds[:-tail], aligns, span_to, compact)
    tail_t = table(headers, rows[-tail:], widths, kinds[-tail:], aligns, span_to, compact, header=False)
    return [head], tail_t


def _footer_pairs(footer_rows) -> List[tuple]:
    pairs = []
    for row in footer_rows or []:
        if isinstance(row, (list, tuple)) and len(row) >= 2:
            label, value = str(row[0]), row[1]
            pairs.append((id_label(label), num(value) if dec(value) is not None else str(value)))
    return pairs


# ------------------------------------------------------- Rekap RAB (2 hal.) --
def rab_blocks(data: Dict) -> list:
    pages = data.get('pages') or []
    out: list = []
    if pages:
        page = pages[0]
        td = page.get('table_data', {})
        rows = td.get('rows', [])
        kinds = kinds_from(page.get('row_types') or [])
        kinds += ['item'] * (len(rows) - len(kinds))
        fmt = []
        for row, kind in zip(rows, kinds):
            row = list(row) + [''] * (6 - len(row))
            if kind == 'item':
                fmt.append([row[0], row[1] or '-', row[2] or '-', num(row[3], 3), num(row[4]), num(row[5])])
            else:
                fmt.append([row[0], '', '', '', '', num(row[5], empty='')])
        out.append(('header', page.get('title') or 'RENCANA ANGGARAN BIAYA', None))
        out.append(table(td.get('headers', []), fmt, [71, 27, 16, 16, 26, 28], kinds,
                         ['l', 'c', 'c', 'r', 'r', 'r'], span_to=4))
        if page.get('footer_rows'):
            out += [('spacer', 3), ('totals', _footer_pairs(page['footer_rows']), True)]
    if len(pages) > 1:
        rekap = pages[1]
        td = rekap.get('table_data', {})
        out += [('pagebreak',), ('header', rekap.get('title') or 'REKAPITULASI RENCANA ANGGARAN BIAYA', None)]
        rows = [[r[0], r[1], num(r[2])] for r in td.get('rows', [])]
        parts = [table(td.get('headers', ['No', 'Uraian Klasifikasi', 'Jumlah Harga (Rp)']), rows,
                       [10, 90, 40], aligns=['c', 'l', 'r'])]
        if rekap.get('footer_rows'):
            parts += [('spacer', 3), ('totals', _footer_pairs(rekap['footer_rows']), True)]
        out += closing(parts)
    return out


# ------------------------------------------ Rekap & Rincian Analisa (AHSP) --
def rincian_blocks(data: Dict) -> list:
    sections = data.get('sections') or []
    out: list = [('header', 'REKAP ANALISA HARGA SATUAN PEKERJAAN', None)]
    rows = []
    for i, sec in enumerate(sections, 1):
        pek, tot = sec.get('pekerjaan', {}), sec.get('totals', {})
        rows.append([str(i), pek.get('kode', ''), pek.get('uraian', ''),
                     num(tot.get('E')), num(tot.get('F')), num(tot.get('G'))])
    out.append(table(['No', 'Kode', 'Uraian Pekerjaan', 'Jumlah (E)', 'Profit/Margin (F)', 'Harga Satuan (G)'],
                     rows, [8, 18, 74, 24, 24, 26], aligns=['c', 'c', 'l', 'r', 'r', 'r']))

    out += [('pagebreak',), ('header', 'RINCIAN ANALISA HARGA SATUAN PEKERJAAN', None)]
    headers = ['No', 'Uraian', 'Kode', 'Satuan', 'Koefisien', 'Harga Satuan (Rp)', 'Jumlah Harga (Rp)']
    for idx, sec in enumerate(sections):
        pek, tot = sec.get('pekerjaan', {}), sec.get('totals', {})
        kode = pek.get('kode', '')
        heading = f"{kode} — {pek.get('uraian', '')}" if kode else pek.get('uraian', '')
        rows, kinds = [], []
        for grp in sec.get('groups', []):
            if not grp.get('rows'):
                continue
            rows.append([grp.get('title', '')] + [''] * 6)
            kinds.append('sub')
            for g in grp['rows']:
                g = list(g) + [''] * (7 - len(g))
                rows.append([g[0], g[1], g[2], g[3] or '-', num(g[4], 6), num(g[5]), num(g[6])])
                kinds.append('item')
            rows.append(['', f"Subtotal {grp.get('short_title', '')}", '', '', '', '', num(grp.get('subtotal'))])
            kinds.append('total')
        rows.append(['', 'Jumlah (E)', '', '', '', '', num(tot.get('E'))]); kinds.append('total')
        markup = num(tot.get('markup_eff')) if tot.get('markup_eff') is not None else ''
        rows.append(['', f"Profit/Margin {markup}% (F)", '', '', '', '', num(tot.get('F'))]); kinds.append('total')
        rows.append(['', 'Harga Satuan Pekerjaan (G = E + F)', '', '', '', '', num(tot.get('G'))]); kinds.append('grand')
        block = [('heading', heading),
                 table(headers, rows, [8, 52, 18, 12, 18, 24, 26], kinds, ['c', 'l', 'c', 'c', 'r', 'r', 'r'],
                       compact=True),
                 ('spacer', 3)]
        # R-11: tanpa page break paksa; satu blok pekerjaan tidak terbelah.
        out.append(('keep', block + ([('signature',)] if idx == len(sections) - 1 else [])))
    if not sections:
        out.append(('signature',))
    return out


# ---------------------------------------------- Volume + Daftar Parameter --
def volume_blocks(data: Dict) -> list:
    pages = data.get('pages') or []
    out: list = []
    for p_idx, page in enumerate(pages):
        td = page.get('table_data', {})
        headers, rows = td.get('headers', []), td.get('rows', [])
        if p_idx:
            out.append(('pagebreak',))
        out.append(('header', page.get('title') or 'VOLUME PEKERJAAN', None))
        if page.get('hierarchy_levels'):
            kinds = kinds_from_levels(page['hierarchy_levels'], len(rows))
            fmt = [r if k != 'item' else [r[0], r[1], r[2], r[3] or '-', num(r[4], 3)] for r, k in zip(rows, kinds)]
            parts = [table(headers, fmt, [8, 70, 62, 14, 20], kinds, ['c', 'l', 'l', 'c', 'r'])]
            count = next((r[1] for r in page.get('footer_rows') or [] if str(r[0]).lower().startswith('total')), None)
            if count is not None:
                parts += [('spacer', 2), ('note', f"Jumlah item pekerjaan: {count}. Formula ditampilkan sebagai "
                                                   "teks audit; nilai Volume adalah nilai resmi.")]
        else:
            fmt = [[r[0], r[1], r[2], num(r[3], 2), r[4] if len(r) > 4 else ''] for r in rows]
            h, fmt, w, a = drop_empty_columns(headers, fmt, [10, 70, 50, 25, 20], ['c', 'l', 'l', 'r', 'c'],
                                              keep=(0, 1, 3))
            parts = [table(h, fmt, w, aligns=a)]
        out += closing(parts) if p_idx == len(pages) - 1 else parts
    return out


# --------------------------------------- Harga Satuan Dasar + Konversi ----
def harga_blocks(data: Dict) -> list:
    pages = data.get('pages') or ([data] if data.get('table_data') else [])
    out: list = []
    price: Dict[str, object] = {}
    for p_idx, page in enumerate(pages):
        td = page.get('table_data', {})
        headers, rows = td.get('headers', []), td.get('rows', [])
        kinds = kinds_from(page.get('row_types') or [])
        kinds += ['item'] * (len(rows) - len(kinds))
        if p_idx:
            out.append(('pagebreak',))
        out.append(('header', page.get('title') or 'DAFTAR HARGA SATUAN DASAR', None))
        is_konversi = any('konversi' in str(h).lower() for h in headers)
        fmt = []
        for row, kind in zip(rows, kinds):
            row = list(row) + [''] * (5 - len(row))
            if kind != 'item':
                fmt.append(row)
            elif is_konversi:
                value = row[4]
                unit = str(value).split('/')[-1] if '/' in str(value) else ''
                if row[1] in price and unit:
                    value = f"Rp {num(price[row[1]])}/{unit}"  # 2 desimal, sama dengan daftar harga
                fmt.append([row[0], row[1], row[2], row[3], value])
            else:
                price[row[1]] = row[4]
                fmt.append([row[0], row[1], row[2], row[3] or '-', num(row[4])])
        widths = [8, 15, 38, 66, 26] if is_konversi else [8, 16, 80, 16, 30]
        aligns = ['c', 'c', 'l', 'l', 'r'] if is_konversi else ['c', 'c', 'l', 'c', 'r']
        parts = [table(headers, fmt, widths, kinds, aligns)]
        pairs = [(('Jumlah item' + lbl[len('Total Items'):]) if lbl.startswith('Total Items') else lbl, val)
                 for lbl, val in _footer_pairs(page.get('footer_rows'))]
        if pairs:
            parts += [('spacer', 3), ('totals', pairs, False)]
        out += closing(parts) if p_idx == len(pages) - 1 else parts
    return out


# ------------------------------------------------ Rekap Kebutuhan Material --
_GROUPS = (('TK', 'TENAGA KERJA'), ('BHN', 'BAHAN'), ('ALT', 'ALAT'), ('LAIN', 'LAINNYA'))


def _group_of(kode: str, kategori: str) -> str:
    kat = (kategori or '').upper()
    if kat in ('TK', 'BHN', 'ALT'):
        return kat
    k = (kode or '').upper()
    if k.startswith('TK'):
        return 'TK'
    if k.startswith(('B-', 'BHN')):
        return 'BHN'
    if k.startswith(('PR', 'ALT', 'A-')):
        return 'ALT'
    return 'LAIN'


def kebutuhan_blocks(data: Dict) -> list:
    headers = ['No', 'Kode', 'Uraian', 'Satuan', 'Kuantitas', 'Harga Satuan (Rp)', 'Total Harga (Rp)']
    widths, aligns = [8, 15, 58, 13, 18, 22, 26], ['c', 'c', 'l', 'c', 'r', 'r', 'r']
    mode_label = 'Satuan Beli' if data.get('unit_mode') == 'market' else 'Satuan Dasar'
    out: list = [('header', 'REKAP KEBUTUHAN MATERIAL', f"Mode satuan: {mode_label}")]

    if data.get('pages'):  # mode per periode (minggu/bulan): satu tabel per periode
        pages = data['pages']
        for p_idx, page in enumerate(pages):
            rows = page.get('table_data', {}).get('rows', [])
            section = [('section', page.get('title') or 'Periode')]
            section.append(table(headers, rows, widths, aligns=aligns) if rows
                           else ('note', 'Tidak ada kebutuhan pada periode ini.'))
            section.append(('spacer', 4))
            out += closing(section) if p_idx == len(pages) - 1 else section
        return out

    src_rows = data.get('table_data', {}).get('rows', [])
    kategori = data.get('row_kategori') or [''] * len(src_rows)
    rows, kinds, grand, no = [], [], Decimal('0'), 0
    for key, title in _GROUPS:
        items = [r for r, k in zip(src_rows, kategori) if _group_of(r[1], k) == key]
        if not items:
            continue
        rows.append([title] + [''] * 6); kinds.append('klas')
        sub = Decimal('0')
        for r in items:
            no += 1
            rows.append([str(no), r[1], r[2], r[3], num(r[4], 3), num(r[5]), num(r[6])]); kinds.append('item')
            sub += dec(r[6]) or Decimal('0')
        rows.append(['', f"Subtotal {title.title()}", '', '', '', '', num(sub)]); kinds.append('total')
        grand += sub
    head, tail = split_tail(headers, rows, widths, kinds, aligns)
    out += head

    pairs, notes = [], []
    for row in data.get('footer_rows') or []:
        label, value = str(row[0]), row[1]
        if label.startswith('Total Items'):
            pairs.append(('Jumlah item', str(value)))
        elif label.startswith(('Tenaga Kerja', 'Bahan', 'Alat')):
            notes.append(f"{label.split(' (')[0]} {value}")
        elif label == 'Filters':
            notes.append(f"Filter: {value}")
        elif label == 'Grand Total Harga':
            grand = dec(value) or grand
    pairs.append(('GRAND TOTAL HARGA', num(grand)))
    parts = [tail, ('spacer', 3), ('totals', pairs, True)]
    if notes:
        parts.append(('note', 'Rincian item: ' + ' · '.join(notes) + '.'))
    out += closing(parts)
    return out


BLOCKS: Dict[str, Callable[[Dict], list]] = {
    'rekap_rab': rab_blocks,
    'rincian_ahsp': rincian_blocks,
    'volume_pekerjaan': volume_blocks,
    'harga_items': harga_blocks,
    'rekap_kebutuhan': kebutuhan_blocks,
}

TITLES = {
    'rekap_rab': 'Rencana Anggaran Biaya',
    'rincian_ahsp': 'Analisa Harga Satuan Pekerjaan',
    'volume_pekerjaan': 'Volume Pekerjaan',
    'harga_items': 'Daftar Harga Satuan Dasar',
    'rekap_kebutuhan': 'Rekap Kebutuhan Material',
}
