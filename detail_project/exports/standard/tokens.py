"""Token desain standar dokumen (satu sumber untuk PDF & Word).

Palet owner 2026-10-02: #213448 #547792 #94B4C1 #EAE0CF. Krem dan tint dipakai
seminimal mungkin: warna menandai baris penting, bukan menjadi latar.
"""

# Warna (hex tanpa '#'' dipakai Word; dengan '#' dipakai PDF via hexcolor()).
NAVY_DARK = '#213448'   # judul dokumen, header tabel, garis grand total
ACCENT = '#547792'      # garis aksen judul, bingkai cover, judul seksi/pekerjaan, garis atas blok total
GRID = '#94B4C1'        # garis tabel, garis header/footer halaman
KLAS_BG = '#ECF2F4'     # SATU-SATUNYA arsir hierarki: baris klasifikasi (tint 18% dari GRID)
GRAND_BG = '#EAE0CF'    # krem: hanya baris akhir (Harga Satuan Pekerjaan G, Pembulatan/Grand Total)
EXTENSION = '#4A0E0E'   # masa Penambahan Waktu Kerja (R-42), tidak berubah
TEXT = '#1A202C'
TEXT2 = '#4A5568'
MUTED = '#718096'
WHITE = '#FFFFFF'

# Ukuran huruf (pt)
SIZE_DOC_TITLE = 15
SIZE_SUBTITLE = 8.5
SIZE_SECTION = 9
SIZE_HEADER = 7.5
SIZE_BODY = 7.5
SIZE_CATEGORY = 8.5
SIZE_SUBCATEGORY = 8
SIZE_NOTE = 7
SIZE_RUNNING = 7          # header/footer halaman
SIZE_SIGNATURE = 8

# Rincian AHSP ringkas (owner 2026-10-02): baris 0,4 cm, huruf 6,5 pt.
RINCIAN_SIZE_BODY = 6.5
RINCIAN_SIZE_GROUP = 6.8
RINCIAN_LEADING = 7.8
RINCIAN_PAD_V_MM = 0.63   # -> tinggi baris 4,0 mm
RINCIAN_PAD_H_MM = 1.2
RINCIAN_SIZE_HEADING = 8

# Tata letak (mm)
PAGE_MARGIN_LR = 15
PAGE_MARGIN_TOP = 22      # termasuk ruang header berjalan
PAGE_MARGIN_BOTTOM = 18   # termasuk ruang footer berjalan
CELL_PAD_V = 1.3
CELL_PAD_H = 1.4
TITLE_RULE_WIDTH = 40
TOTAL_BLOCK_WIDTH = (55, 40)

BRAND = 'Dashboard-RAB.com'


def word_hex(color: str) -> str:
    return color.lstrip('#').upper()
