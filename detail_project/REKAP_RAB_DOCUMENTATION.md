# Rekap RAB - Technical Notes

_Last updated: 2025-11-18_

---

## 1. Purpose & UX Overview

Halaman **Rekap RAB** merangkum biaya proyek dalam tree-table tiga level (Klasifikasi -> Sub-klasifikasi -> Pekerjaan). Target pengguna: estimator yang ingin melihat total biaya, margin, serta melakukan export atau print.

Fitur utama:

| Komponen | Perilaku |
| --- | --- |
| Toolbar `#rab-toolbar` | Search client-side, Expand/Collapse All, toggle mode Subtotal only, toggle Compact density, Refresh baru dari API, dropdown Export (CSV/PDF/Word), tombol Excel legacy, Print. |
| Tabel `#rekap-table` | Sticky header, highlight level (warna untuk klas/sub), loading row `#rab-loading`, data live dari JS. |
| Footer | Input `#ppn-pct` dan select `#round-base` menyimpan preferensi, menghitung Grand Total + pembulatan. |
| Live region `#rab-announce` | `aria-live="polite"` untuk feedback search/filter/export. |
| Print system | `print/*.css` + module `RekapRABPrint.js` memakai `window.RABModule`. |

---

## 2. File Responsibilities

| Path | Peran |
| --- | --- |
| `detail_project/views.py::rekap_rab_view` | Render template dengan objek `project` dan `side_active`. |
| `detail_project/templates/detail_project/rekap_rab.html` | Markup, toolbar, tabel, footer, script tags (`ExportManager.js`, `rekap_rab.js`, modul print). |
| `detail_project/static/detail_project/js/rekap_rab.js` | Controller utama: fetch tree + rekap + pricing, normalisasi data, render tabel, search, toggle, export hooks. |
| `detail_project/static/detail_project/css/rekap_rab.css` | Styling tree-table, density toggle, toolbar, print overrides untuk layar. |
| `detail_project/static/detail_project/js/export/ExportManager.js` | Helper front-end untuk export via API (CSV/PDF/Word) yang dipakai beberapa halaman termasuk Rekap RAB. |
| `detail_project/static/detail_project/js/print/RekapRABPrint.js` | ES module yang mengambil `window.RABModule` untuk print-ready layout. |
| `detail_project/views_api.py::{api_get_list_pekerjaan_tree, api_get_rekap_rab, api_project_pricing}` | API data tree dan meta pricing yang dikonsumsi JS. |
| `detail_project/views_api.py::{export_rekap_rab_csv, export_rekap_rab_pdf, export_rekap_rab_word}` | Endpoint export yang memanggil `ExportManager`. |
| `detail_project/exports/export_manager.py` + `detail_project/exports/rekap_rab_adapter.py` | Adaptasi data `compute_rekap_for_project` ke output CSV/PDF/Word. |
| `detail_project/services.py::compute_rekap_for_project` | Hitung komponen A..G, `biaya_langsung`, `total`, cache `rekap:{project_id}:v2`. |

---

## 3. Data Flow & API Contracts

1. **Template bootstrap**  
   `#rekap-app` menyimpan `data-project-id/name/code/location/year` untuk print/export metadata.

2. **Fetch awal (`loadData`)**  
   Dilakukan via `Promise.all`:
   - `GET /detail_project/api/project/<id>/list-pekerjaan/tree/` -> `{"ok": true, "klasifikasi": [{id, name, sub:[{id, name, pekerjaan:[{id, snapshot_*}]}]}]}`.
   - `GET /detail_project/api/project/<id>/rekap/` -> `{"ok": true, "rows": [...], "meta": {"markup_percent": "10.00", "ppn_percent": "11.00", "rounding_base": 10000}}`. Tiap row memuat `A..G`, `LAIN`, `E_base`, `markup_eff`, `volume`, `total`, `biaya_langsung`, `HSP`.
   - `GET /detail_project/api/project/<id>/pricing/` -> `{"ok": true, "markup_percent": "...", "ppn_percent": "...", "rounding_base": ...}`. Dipakai memprefill footer dan toggle rounding.

3. **Normalisasi**  
   `normalize(tree, rekapRows)` memetakan `pekerjaan_id` <-> data numeric lalu mengisi fallback snapshot ketika row belum tersedia (mis. data baru). Tiap pekerjaan menyimpan `harga` (G) dan `total = volume * harga`. Hasilnya disimpan di `fullModel` dan dipakai untuk tabel, export, serta footer.

4. **Cache & invalidation**  
   `compute_rekap_for_project` disimpan di cache `rekap:{project.id}:v2` dengan signature gabungan timestamp `DetailAHSPProject`, `DetailAHSPExpanded`, `VolumePekerjaan`, `Pekerjaan`, dan `ProjectPricing`. Semua update harga, volume, atau pricing memanggil `invalidate_rekap_cache(project)` setelah commit (lihat `transaction.on_commit` di services & pricing API).

5. **Post preferensi footer**  
   Perubahan PPN / rounding dikirim ke `POST /detail_project/api/project/<id>/pricing/` dengan payload `{ppn_percent?, rounding_base?}` melalui `postPricingDebounced`.

---

## 4. Front-End Controller (`rekap_rab.js`)

### 4.1 State & Normalization
- `tree`, `rekapRows`, `fullModel` menyimpan struktur gabungan.
- `subtotalOnly`, `dense` (Compact) dihidupkan via tombol toolbar.
- `expanded` state tersimpan di `localStorage` memakai key `rekap_rab:<projectId>:expanded:<nodeId>` dan default `true`.

### 4.2 Rendering & Interaction
- `computeTotalsFiltered(model, predicate)` menghitung total per K/S beserta flattened rows sesuai filter / mode subtotal.
- `buildRow` mengisi `<tr>` dengan atribut `data-node-id`, `data-level`, `aria-level`, toggle icon, highlight search dengan `highlightMatch`.
- `applyVisibility` menyembunyikan anak saat parent collapsed (kecuali saat search aktif). Toolbar expand/collapse otomatis disable ketika search terisi.
- `announce(message)` menulis ke `#rab-announce` untuk memberi tahu success/error/search result.
- `recalcFooter(totalD)` menghitung PPN, Grand Total, dan pembulatan berbasis input dengan `totalD` = akumulasi `volume * G` (total biaya sebelum pajak).
- Sortable headers (`th.th-sortable`) sekarang siklik (`none` → `asc` → `desc` → `none`). Saat aktif, job di setiap sub disortir berdasarkan kolom yang dipilih dan indikator `aria-sort` diperbarui untuk aksesibilitas.
- `recalcTableHeight` memastikan table wrapper memenuhi tinggi viewport dengan topbar offset.

### 4.3 Preferences & Persistence

| Key `localStorage` | Nilai | Keterangan |
| --- | --- | --- |
| `rekap_rab:<pid>:expanded:<nodeId>` | `'1'` / `'0'` | State expand per node. |
| `rekap_rab:<pid>:subtotal_only` | `'1'` jika hanya subtotal. | Dipakai untuk tombol Subtotal. |
| `rekap_rab:<pid>:dense` | `'1'` jika compact mode aktif. | Menambah class `rab-dense` di root. |
| `rekap_rab:<pid>:ppn_pct` | String nilai PPN terakhir. | Dipakai ketika meta dari server tidak tersedia. |
| `rekap_rab:<pid>:round_base` | String rounding base terakhir. | Juga dipakai sebagai fallback. |

Server sync (`postPricingDebounced`) mengirim perubahan PPN/rounding ke `api_project_pricing` dengan delay 250 ms serta menyertakan CSRF header.

### 4.4 Export & Print Hooks
- `exportCSV()` membangun file semicolon-separated (header + seluruh pekerjaan + ringkasan) dan dipanggil oleh tombol `#btn-export-excel` untuk mendukung format legacy.
- `initUnifiedExport()` mencari `btn-export-csv/pdf/word`, membuat instance `ExportManager`, lalu memanggil `exporter.exportAs(format)` ketika tombol ditekan. Jika `ExportManager` tidak tersedia, tombol-tombol tetap tapi log warning ke console.
- `window.RABModule` mengekspos referensi DOM, `expandAll/collapseAll`, state tree, serta `unifiedExporter` agar modul print dan util lain dapat mengakses data yang sama.

---

## 5. Calculations & Services

### `compute_rekap_for_project(project)`
- Baca `DetailAHSPExpanded` (fallback `DetailAHSPProject`) untuk agregasi kategori `TK/BHN/ALT/LAIN`.
- Mengalikan koef bundle dengan `DetailAHSPProject.koefisien` supaya komponen TK/BHN/ALT sudah merefleksikan jumlah bundle aktual.
- Mengambil `VolumePekerjaan` per pekerjaan, menerapkan markup override (`Pekerjaan.markup_override_percent`) atau default proyek dari `ProjectPricing`.
- Mengembalikan dict per pekerjaan: `A,B,C,D,LAIN,E_base,F,G,total,markup_eff,HSP=E_base,unit_price,biaya langsung (D)`, plus metadata `kode/uraian/satuan/volume`.
- Cache hasil beserta signature timestamp; TTL default 5 menit.

### `api_get_rekap_rab`
- Validasi kepemilikan, memanggil service di atas.
- Pastikan `markup_eff`, `F`, `G`, `total` tersedia untuk data lama; menyuntik `biaya_langsung = D` agar UI bisa menampilkan biaya langsung terpisah.
- Meta response mengambil `ProjectPricing` jika ada (`markup_percent`, `ppn_percent`, `rounding_base`), fallback ke default 10% markup dan 11% PPN.

### `api_project_pricing`
- `GET` -> nilai markup, ppn, rounding (membuat row default jika tidak ada).
- `POST` -> menerima subset field (0..100 untuk persen, rounding_base integer > 0). Setelah simpan memanggil `invalidate_rekap_cache(project)` via `transaction.on_commit`.

---

## 6. Export & Print Stack

- `views_api.export_rekap_rab_{csv,pdf,word}` autentikasi user, instantiate `ExportManager(project, request.user)` lalu memanggil `export_rekap_rab(format)`.
- `ExportManager` melimpahkan konversi ke `RekapRABAdapter`, memastikan data yang dipakai sama dengan UI (via `compute_rekap_for_project`) sehingga CSV/PDF/Word konsisten.
- File CSS print (`print-base.css`, `print-theme.css`, `print-components.css`, `rekap-rab-print.css`) disertakan di `<head>`. Module `RekapRABPrint.js` memanggil `initRekapRABPrint(window.RABModule)` untuk menyuntik layout print (header proyek, metadata, dsb.) sebelum `window.print()`.

---

## 7. Testing & Verification

| Test | Fokus |
| --- | --- |
| `detail_project/tests/test_rekap_page.py` | Memastikan view dapat dirender, toolbar elemen tersedia. |
| `detail_project/tests/test_rekap_api.py` | Validasi struktur API `api_get_rekap_rab` & meta PPN. |
| `detail_project/tests/test_rekap_rab_with_buk_and_lain.py` | Regression untuk perhitungan A..G saat ada pekerjaan bundel + kategori LAIN. |
| `detail_project/tests/test_rekap_consistency.py` | Membandingkan hasil `compute_rekap_for_project` dengan volume/detil real. |
| `detail_project/tests/test_page_interactions_comprehensive.py` | Flow end-to-end (list pekerjaan -> rekap -> export endpoints). |
| `detail_project/tests/test_workflow_baseline.py` | Scenario update harga/volume memastikan invalidasi cache memantul ke rekap. |

Manual QA checklist:
1. Expand/collapse state bertahan setelah reload halaman.
2. Mengubah PPN dan rounding base, lalu refresh: nilai harus tetap (localStorage + API).
3. Search kata unik: hasil highlight dan live-region (`#rab-announce`) muncul dengan pesan benar.
4. Export CSV/PDF/Word menghasilkan file dengan header + total sama dengan UI.
5. Tombol Print memanggil preview dengan layout `rekap-rab-print.css`.

---

## 8. Troubleshooting

| Gejala | Penyebab | Tindakan |
| --- | --- | --- |
| Expand/Collapse all tidak bisa diklik | Toolbar guard mengunci saat search aktif. | Kosongkan input search atau klik tombol Clear filter (X). |
| Total/markup tidak berubah setelah edit harga | Cache `rekap:{id}:v2` belum terinvalidasi. | Jalankan aksi yang memanggil `invalidate_rekap_cache` (mis. simpan harga) atau gunakan management command `invalidate_rekap_cache`. |
| Nilai PPN / rounding tidak tersimpan | `localStorage` diblok atau `api_project_pricing` gagal (lihat console). | Periksa console network, atau copy error JSON lalu lapor backend. |
| Tombol export tidak bekerja | `ExportManager.js` gagal dimuat atau API export error. | Pastikan script load order benar (`ExportManager.js` sebelum `rekap_rab.js`) dan periksa response `export_rekap_rab_*`. |
| Print kosong | `window.RABModule` belum terdefinisi (script gagal). | Pastikan `rekap_rab.js` sukses dieksekusi sebelum modul print. |

---

## 9. Known Gaps / TODO

1. **ARIA treegrid** - Tambah `aria-treegrid`, `aria-expanded`, dan `aria-level` yang konsisten pada `<tr>` untuk aksesibilitas screen reader (partial sudah ada tapi belum lengkap).
2. **Bundle marker** - Masih belum ada indikator pekerjaan hasil ekspansi bundle (tooltip/tag) agar estimator tahu dari mana angka berasal.
3. **Analytics** - Belum ada logging penggunaan export/print untuk mengukur fitur paling sering dipakai.

Perbarui dokumen ini bila:
- Struktur response `api_get_rekap_rab` berubah (field baru/rename).
- Toolbar/print/export mendapatkan aksi baru.
- Logika PPN/pembulatan dialihkan sepenuhnya ke backend.
