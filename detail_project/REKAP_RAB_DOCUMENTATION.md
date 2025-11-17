# Rekap RAB – Technical Notes

_Last updated: 2025-11-17_

---

## 1. Purpose & UX Overview

Page **Rekap RAB** menampilkan struktur hierarki biaya proyek (Klasifikasi → Sub → Pekerjaan) dalam format tree-table yang bisa diekspor/print. Pengguna dapat:

- Mencari klasifikasi, sub, pekerjaan, atau kode AHSP.
- Expand/collapse seluruh tree atau hanya node tertentu.
- Mengaktifkan mode “Subtotal only” (hanya Klasifikasi/Sub) atau “Compact density”.
- Menyetel PPN (%) dan rounding base yang diaplikasikan di footer.
- Mengekspor ke CSV / PDF / Word atau langsung print.

Elemen utama:

| Komponen | Perilaku |
| --- | --- |
| Toolbar (`#rab-toolbar`) | Search, Expand/Collapse, Subtotal filter, Compact toggle, Refresh, Export, Print. |
| Table (`#rekap-table`) | Sticky header, row highlight per level, loading row, live totals. |
| Footer | Input PPN + rounding base, otomatis menyimpan preferensi ke `localStorage`. |
| Announcement live region | `#rab-announce` memberi feedback saat filter menghasilkan 0 hasil, dsb. |

---

## 2. File Responsibilities

| Path | Deskripsi |
| --- | --- |
| `detail_project/views.py::rekap_rab_view` | Render template dengan `project` dan `side_active`. |
| `detail_project/templates/detail_project/rekap_rab.html` | Struktur HTML, toolbar, table, PPN inputs, live region, modal print CSS. |
| `detail_project/static/detail_project/js/rekap_rab.js` | Controller utama: fetch data, render tree, filter, preferences, export, print. |
| `detail_project/static/detail_project/css/rekap_rab.css` | Styling (layout table, sticky header, density mode, tree indent). |
| `detail_project/views_api.py::api_get_rekap_rab` | REST endpoint untuk data tree + meta markup/PPN. |
| `detail_project/views_api.py::api_export_rekap_rab_csv` (dan rekan PDF/Word) | Export endpoints yang dipakai toolbar. |
| `detail_project/services.py::compute_rekap_for_project` | Sumber data RAB (A..G, total, markup). |

Belum ada dokumen eksternal sebelumnya untuk halaman ini; file ini mengisi kekosongan itu.

---

## 3. Data Flow

1. **Page load**: template menyuntik `data-project-*` (nama, kode, lokasi, tahun) pada `#rekap-app`. JS (`rekap_rab.js`) membaca atribut tersebut dan endpoints standar (`data-ep-rekap`, dll. didefinisikan di script).
2. **Fetch data**: `fetchRekap()` memanggil `api_get_rekap_rab`. Response struktur:
   ```json
   {
     "ok": true,
     "rows": [
       {
         "level": "K/S/P",
         "name/label": "...",
         "volume": "...",
         "harga": "...",
         "total": "...",
         "children": [...]
       }
     ],
     "meta": { "markup_percent": "10.00", "ppn_percent": "11.00", "rounding_base": 10000 }
   }
   ```
3. **Build rows**: `buildTreeRows()` flattens hierarki menjadi array `[{level, node, total}, …]`. Level 1 & 2 (Klasifikasi/Sub) menjadi summary rows; level 3 (Pekerjaan) menampilkan detail volume, harga, total.
4. **Persist expanded state**: Setiap node memiliki key `ex:<projectId>:<nodeId>`. `localStorage` menyimpan `'1'` (expanded) / `'0'` (collapsed). Toolbar “Expand/Collapse All” memrespect search filter (disabled saat filter aktif).
5. **Footer totals**: JS menghitung `totalD` (Σ Klasifikasi) dan menambahkan baris PPN + rounding base. Input PPN & rounding base disimpan dengan prefix `pref:<projectId>`.
6. **Exports / Print**: Toolbar men-trigger fetch ke `btn-export-*` endpoints. Print button hanyalah `window.print()` dengan CSS print khusus (`print/rekap-rab-print.css`).

---

## 4. JavaScript Highlights (`rekap_rab.js`)

### 4.1 State & Elements

- `expanded` (Map) – state expand/collapse per node.
- `prefKey/exKey` helpers – menentukan key `localStorage`.
- `btn*` references – toolbar, export buttons, density/subtotal toggles, PPN inputs, rounding select.
- `announce()` – menulis pesan ke `#rab-announce` (live region).

### 4.2 Rendering & Accessibility

- Table rows disusun via `buildRow(level, node, total, parentId, currentFilter)`.
- Level 1/2 row menampilkan tombol toggle `<span class="toggle" role="button" tabindex="0" aria-expanded="…">`.
- Search highlight dilakukan dengan `highlightMatch`.
- `applyVisibility()` menyembunyikan anak jika parent collapsed (kecuali saat filter aktif).
- Sorting: kolom Volume/Harga/Total memiliki `role="button"` + `aria-label` yang menginformasikan can sort.
- Live announcements saat hasil pencarian kosong / filter active.
- TODO (dalam perbaikan 2 di bawah): menambahkan `aria-level`/`aria-expanded` pada `<tr>` agar screen reader menangkap struktur tree secara penuh.

### 4.3 Preferences & LocalStorage

| Key | Isi | Catatan |
| --- | --- | --- |
| `ex:<projectId>:<nodeId>` | `'1'` / `'0'` | Expand state per node. |
| `pref:<projectId>:density_compact` | `'1'` if compact. | Toggle mempengaruhi class pada body/table. |
| `pref:<projectId>:subtotal_only` | `'1'` if hanya subtotal. |
| `pref:<projectId>:ppn_pct` | Last PPN input. |
| `pref:<projectId>:round_base` | Last rounding base select. |

### 4.4 Export Hooks

`initExportButtons()` mengikat `btn-export-csv/pdf/word` ke `ExportManager` (`static/detail_project/js/export/ExportManager.js`), serupa dengan halaman Rincian AHSP. Print button mengaktifkan CSS print (empat file di `css/print/`).

---

## 5. API & Services

### `api_get_rekap_rab`

- Mengambil `compute_rekap_for_project`.
- Menyuntik `markup_eff` jika kosong (menggunakan override per pekerjaan atau markup proyek).
- Menambahkan `biaya_langsung = D` dan memastikan `HSP = E_base`.
- Kalkulasi F/G/total jika belum ada di service output.
- Meta: `markup_percent`, `ppn_percent` (default 11%), `rounding_base` (default 10.000).

### `api_export_rekap_rab_csv` / `api_export_rekap_rab_pdf` / `api_export_rekap_rab_word`

- Controller tipis di `views_api.py` yang memanggil `ExportManager`.
- CSV generator sebelumnya simple; versi sekarang memanfaatkan `ExportManager` agar sinkron dengan UI.

### `compute_rekap_for_project` (services)

- Aggregates DetailAHSPExpanded (fallback ke raw detail) per pekerjaan.
- Menghitung `A..G`, `total`, `HSP`, `markup_eff`.
- Dibungkus cache `rekap:{projectId}:v2:{signatures}`; invalidated via signals setiap data relevan berubah.

---

## 6. Calculations & Business Rules

- Sama seperti AHSP:
  - `A` = Σ TK, `B` = Σ BHN, `C` = Σ ALT, `LAIN` = Σ LAIN.
  - `D = A+B+C`, `E_base = D+LAIN`, `F = E_base × markup_eff/100`, `G = E_base + F`.
  - `total = G × volume`.
- **biaya_langsung** ditampilkan terpisah agar user melihat angka tanpa LAIN.
- PPN (input) dihitung di front-end: `Grand = totalD + (totalD × PPN/100)` sebelum pembulatan.
- Rounding base digunakan saat men-format total akhir (default 10.000).

---

## 7. Testing

| Test | Fokus |
| --- | --- |
| `detail_project/tests/test_rekap_page.py` | Rendering minimal, API handshake. |
| `detail_project/tests/test_rekap_api.py` | API output, meta PPN, rounding. |
| `detail_project/tests/test_workflow_baseline.py` | Cascade updates mempengaruhi RAB totals. |

Manual QA:

1. Pastikan expand/collapse state bertahan setelah refresh.
2. Ganti PPN & rounding base, reload – nilai harus tetap.
3. Jalankan search + verify announcement “Tidak ada hasil” bekerja.
4. Export CSV/PDF/Word -> file memiliki header & totals benar.

---

## 8. Troubleshooting

| Gejala | Penyebab | Tindakan |
| --- | --- | --- |
| Tree tidak bisa expand (tombol disabled) | Toolbar guard aktif saat search. | Kosongkan search lalu coba lagi. |
| Nilai HSP/Subtotal mismatch | Cache `compute_rekap` stale. | Jalankan `invalidate_rekap_cache(project)` atau tunggu invalidation dari signal. |
| PPN tidak tersimpan | LocalStorage diblokir / situs dalam mode private. | Cek console untuk warning `localStorage`. |
| Export tombol tidak bereaksi | `ExportManager` tidak diload atau error server. | Cek console/log; ensure `static/detail_project/js/export/ExportManager.js` dimuat sebelum `rekap_rab.js`. |
| Sort header tidak fokus dengan keyboard | (Akan diperbaiki di langkah aksesibilitas) Pastikan `tabindex` masih ada; jika hilang, rebuild assets. |

---

## 9. TODO / Enhancements

1. **ARIA Treegrid**: Tambahkan `aria-level`, `aria-expanded` ke `<tr>` (sedang dikerjakan).
2. **Tooltip bundle**: Tandai pekerjaan yang berasal dari bundle.
3. **Analytics**: Logging event untuk export / print agar bisa mengukur penggunaan.

Dokumen ini harus diperbarui jika:
- Struktur API berubah (misal meta tambahan).
- Toolbar mendapatkan aksi baru.
- Sistem rounding/PPN dipindah ke backend.
