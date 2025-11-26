# Panduan Client-Side Halaman Jadwal Kegiatan

Dokumen ini menjelaskan arsitektur client-side halaman **Jadwal Kegiatan** yang saat ini menjalani transisi dari kode legacy ke bundler Vite. Gunakan panduan ini untuk memahami entry point, modul-modul utama, serta alur data di sisi browser.

---

## 1. Ruang Lingkup & Status Implementasi

- **Template aktif:** `kelola_tahapan_grid_modern.html` (Vite). Flag `ENABLE_AG_GRID=True` secara default, dan kontainer `#ag-grid-container` kini tampil ketika flag aktif sehingga legacy grid otomatis disembunyikan. Panel kiri terpin, status bar aktif, dan horizontal scrollbar tersedia di atas maupun bawah.
- **Bundler:** Vite 5.x dengan entry `static/detail_project/js/src/jadwal_kegiatan_app.js`. Build output berada di `static/detail_project/dist/`.
- **Dev server toggle:** gunakan setting `USE_VITE_DEV_SERVER=True` bila ingin memuat script dari `http://localhost:5173`. Default `False` memakai bundel `dist/`; manifest loader sedang dijadwalkan agar file fingerprint otomatis terdeteksi.
- **Endpoint data:** entry point membaca dataset `data-api-*` (tahapan, list-pekerjaan, save) dan kini mengirim payload `assignments` ke `/detail_project/api/v2/project/<id>/assign-weekly/`. Payload mendukung proporsi 0â€“100% per minggu, dan detail error dari API diteruskan ke UI (toast + row highlight).
- **Mode input:** toggle Persentase/Volume di toolbar default pada Persentase; saat pengguna beralih ke Volume, grid mengonversi nilai ke unit volume dan kembali ke persentase sebelum simpan (plus validasi otomatis 0â€“volume dan warning total >100%).
- **AG Grid:** modul `modules/grid/ag-grid-setup.js`, `column-definitions.js`, dan `grid-renderer.js` sudah tersedia. Event legacy dilepas ketika atribut `data-enable-ag-grid="true"`, jadi pastikan kontainer tidak disembunyikan sebelum QA regression selesai.
- **Theme sinkron:** kelas `ag-theme-alpine` â†” `ag-theme-alpine-dark` dipilih otomatis mengikuti `data-bs-theme`, sehingga mode terang/gelap konsisten dengan tampilan dashboard lain.
- **Phase 2 Assignments v2:** DataLoader kini membaca endpoint `/api/v2/project/<id>/assignments/` sebagai satu-satunya sumber data weekly (tidak ada fallback), sehingga grid, Rekap, dan modul lain selalu sinkron pada weekly canonical storage. WeekNumber kolom sudah konsisten, jadi penyimpanan minggu > 1 muncul kembali saat reload.
- **Week boundary preference:** Dropdown Week Start/End menyimpan nilai via API `week-boundary` dan mengisi ulang atribut `data-week-start-day` / `data-week-end-day`, sehingga grid, Gantt, dan Kurva S selalu memakai batas minggu yang sama.
- **Time scale switch:** Toggle Weekly/Monthly menampilkan agregasi 4 minggu (Monthly read-only, input tetap dilakukan pada mode weekly). Bila tahapan weekly hilang/kurang, frontend otomatis memanggil regenerate weekly berdasarkan tanggal mulai/akhir proyek (akhir default 31/12 YYYY bila kosong).
- **Auto reset saat timeline berubah:** Jika `tanggal_mulai` proyek diubah dari dashboard, backend otomatis menghapus PekerjaanProgressWeekly + assignments lalu menghitung ulang tahapan weekly sebelum halaman grid dibuka, sehingga user memulai dari nol pada timeline baru. Tombol toolbar “Reset Progress” memanggil endpoint yang sama bila dibutuhkan manual.

---

## 2. Struktur DOM

Elemen penting pada template (legacy maupun Vite) yang menjadi anchor bagi JavaScript:

| Elemen | Fungsi |
| --- | --- |
| `#tahapan-grid-app` | Root container, menyimpan atribut data (project id, API base, tanggal proyek). |
| `.grid-toolbar` | Toolbar utama (selector time scale, display mode, tombol reset/export/save). |
| `#viewTabs` + `#grid-view`/`#gantt-view`/`#scurve-view` | Tab navigasi antar tampilan. |
| `#left-tbody`, `#right-tbody` | Kontainer tabel grid dua kolom (legacy). |
| `#gantt-container`, `#scurve-container` | Target rendering Frappe Gantt & ECharts. |
| `#ag-grid-container` | Kontainer AG Grid (class `ag-theme-alpine`). Aktif bila `data-enable-ag-grid="true"`. |
| `data-api-save` (atribut root) | Endpoint canonical untuk menyimpan progress (`/detail_project/api/v2/project/<project_id>/assign-weekly/`). |
| `data-api-week-boundary` | Endpoint untuk menyimpan preferensi Week Start/End per proyek. UI memanggilnya saat dropdown berubah. |
| `data-api-regenerate-tahapan` | Endpoint regenerate tahapan v2 (dipakai saat Week Start/End disimpan). |
| Tombol `#btn-save-all`, `#refresh-button`, dsb. | Aksi toolbar (save, refresh, reset). |

---

## 3. Entry Point Vite

File: `static/detail_project/js/src/jadwal_kegiatan_app.js`

### Ringkasan
- Mendefinisikan kelas `JadwalKegiatanApp` (stateful controller).
- Mengikat event melalui helper `attachGridEvents` dan modul shared (`validation-utils`, `event-delegation`).
- Membaca atribut dataset (`data-api-base`, `data-enable-ag-grid`, dst.) dari root `#tahapan-grid-app`.
- Menyediakan hook `saveChanges()` yang memanfaatkan `_buildAssignmentsPayload()` agar `modifiedCells` dikonversi menjadi `assignments` dan dikirimkan ke endpoint canonical (`/detail_project/api/v2/project/<id>/assign-weekly/`).
- Expose state ke `window.kelolaTahapanPageState` agar kompatibel dengan kode lama atau debugging.

### Tahapan `initialize()`
1. **_setupState**: menggabungkan state global lama dengan state baru (pekerjaanTree, timeColumns, expandedNodes, modifiedCells, dsb).
2. **_setupDomRefs**: caching elemen DOM (tbody, toolbar, scroll container).
3. **_attachEvents**: memanggil `attachGridEvents` (delegasi event modern) serta binding tombol toolbar.
4. **_loadInitialData**: jika state belum memiliki data, fetch ke endpoint placeholder untuk memuat struktur grid.

---

## 4. Modul Shared

Semua berada di `static/detail_project/js/src/modules/shared/`:

| File | Fungsi Utama |
| --- | --- |
| `event-delegation.js` | `EventDelegationManager` dan utilitas pembersihan listener untuk mencegah memory leak. |
| `performance-utils.js` | `debounce`, `throttle`, `rafThrottle`, `batchDOMOperations`, monitor kinerja. |
| `validation-utils.js` | Validasi nilai cell (0â€“100%), progress total, feedback visual, dan summary toast. |

Modul-modul ini menggantikan logika inline pada `grid_module.js` lama.

---

## 5. Grid Event Manager (Vite)

File: `static/detail_project/js/src/modules/grid/grid-event-handlers.js`

- Menggunakan `EventDelegationManager` untuk mengikat event pada container tabel.
- Menangani klik, double click, input, blur, dan keydown untuk cell `.time-cell.editable`.
- Sinkronisasi scroll kiri/kanan menggunakan `rafThrottle` (mengurangi repaint).
- Mengelola toggling tree (expand/collapse) dan seleksi baris.
- Memanggil `handleCellValidation` dari modul shared untuk validasi real-time.

> Rencana Phase 2: modul ini akan digantikan/diadaptasi agar bekerja dengan AG Grid (`ag-grid-setup.js`). Saat ini tetap diperlukan karena grid HTML masih aktif.

---

## 5.1 AG Grid Manager (baru)

File: `static/detail_project/js/src/modules/grid/ag-grid-setup.js`

- `AGGridManager` membungkus inisialisasi AG Grid Community (`new Grid(container, gridOptions)`).
- Kolom dinamis dibangun via `modules/grid/column-definitions.js`, menambahkan kolom `Pekerjaan`, `Kode`, dan setiap tahapan (`fieldId = col_<id>`).
- `updateData()` menerima `tree` dan `timeColumns` dari state lalu menyusun row tree-data (auto expand, `getDataPath` berbasis array path).
- Kontainer `#ag-grid-container` akan muncul jika `data-enable-ag-grid="true"`; legacy table otomatis diberi `d-none` supaya tidak menggandakan tampilan.
- Grid baru sudah mendukung editing (`cellEditor` numeric + `onCellValueChanged` â†’ `_handleAgGridCellChange`) namun belum dijadikan default. Aktifkan dengan `ENABLE_AG_GRID=True` untuk QA; set kembali ke `False` bila ingin langsung kembali ke renderer legacy tanpa ubah kode.

### 5.2 Kolom Pinned & Mode Tampilan

- Panel kiri AG Grid kini terdiri dari kolom `Pekerjaan`, `Volume`, dan `Satuan` (kolom Kode disembunyikan). Kolom tersebut dipinned (`pinned: 'left'`) dan bersifat read-only. Data volume diambil dari `state.volumeMap`, sehingga angka yang tampil sama dengan modul Volume Pekerjaan. Label pekerjaan otomatis di-wrap maksimal 2 baris untuk menjaga tinggi baris tetap rapi.
- Theme AG Grid mengikuti atribut `data-bs-theme` secara otomatis: saat mode gelap aktif, kelas diganti ke `ag-theme-alpine-dark`; sebaliknya menggunakan `ag-theme-alpine`. Hal ini memastikan warna header/cell sinkron dengan dashboard.

---

## 6. State & Data Flow

### Objek State (`window.kelolaTahapanPageState`)
```javascript
{
  projectId,
  pekerjaanTree: [],
  timeColumns: [],
  expandedNodes: new Set(),
  modifiedCells: new Map(),
  progressTotals: new Map(),
  isDirty: false,
  domRefs: {...},
  ganttInstance,
  scurveChart,
  // atribut lain yang diisi saat runtime
}
```

### Alur Data
1. **Initial Rendering:** Template menampilkan struktur kosong + toolbar. JS mendeteksi state preloaded (jika template menyuntikkan data).
2. **Load Data:** Jika belum ada data, `_loadInitialData()` melakukan fetch ke API (placeholder). Data yang diharapkan: `pekerjaanTree`, `timeColumns`, `assignments` per cell.
3. **User Interaction:** Pengguna mengedit cell â†’ `eventManager` menandai cell sebagai modified (Map `modifiedCells`), menjalankan validasi, dan update indicator total per pekerjaan.
4. **Save:** `saveChanges()` konversi Map ke objek, kirim POST ke `/api/jadwal-kegiatan/save/` (perlu diganti ke endpoint actual). Sukses => bersihkan `modifiedCells` dan set `isDirty` ke false.
5. **Refresh/Reset:** Tombol toolbar memanggil `refresh()` atau `reset`. Saat ini stub (perlu implementasi lanjutan). 

---

## 7. Integrasi Gantt & Kurva S

(Masih menggunakan kode legacy)

- **Frappe Gantt** (`static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/gantt_module.js`) di-render ke `#gantt-container`. JS baru belum menulis ulang modul ini; existing code tetap dipakai.
- **ECharts Kurva S** (`static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/kurva_s_module.js`). Sama seperti Gantt, masih modul lama dengan fallback CDN. Template Vite memuat ECharts CDN + fallback lokal (`static/detail_project/js/vendor/echarts.min.js`).

> Setelah AG Grid siap, modul Gantt/Kurva S akan direstruktur agar membaca sumber data yang sama dengan grid baru.

---

## 8. Rencana Client-Side Phase 2

1. **Mode Persentase vs Volume**
   - Toggle sudah menyimpan preferensi pengguna; berikutnya konversi nilai volumeâ†”persentase sebelum payload dikirim.
   - Tambah validasi berbasis volume (misal: total volume minggu > volume pekerjaan).

2. **Validasi total & UX**
   - Terapkan agregasi per-pekerjaan di client: beri peringatan otomatis saat total > 100%.
   - Lanjutkan polishing keyboard navigation + dirty indicator lintas tab.

3. **Time Scale Switch (Weekly â†” Monthly)**
   - Aktifkan tombol switch untuk memanggil API regenerate dan reload DataLoader.
   - Pastikan assignments monthly masih membaca weekly canonical sebelum di-expand.

4. **Build & Manifest**
   - Implementasi pembacaan manifest.json sehingga bundel fingerprint otomatis dimuat di mode produksi (USE_VITE_DEV_SERVER=False).

5. **Testing & Automation**
   - Pertahankan pytest UI + canonical tests (round-trip/zero progress).
   - Tambahkan scenario volume mode + monthly switch sebelum flag production dinaikkan.


### 8.5 Canonical Save API

- Root container menyuplai `data-api-save` (default: `/detail_project/api/v2/project/<project_id>/assign-weekly/`).
- `jadwal_kegiatan_app.js` menggunakan helper `_buildAssignmentsPayload()` + `_getSaveMode()` untuk menghasilkan payload canonical sebelum melakukan POST.
  ```json
  {
    "assignments": [
      { "pekerjaan_id": 101, "week_number": 1, "proportion": 25.5 },
      { "pekerjaan_id": 101, "week_number": 2, "proportion": 50.0 }
    ],
    "mode": "weekly",
    "week_end_day": 6
  }
  ```
- Setiap kolom AG Grid menyimpan metadata (tahapan_id, order, weekNumber) sehingga payload tetap konsisten walau kolom dinamis.
- Endpoint `api_v2_assign_weekly` menyimpan progress ke `PekerjaanProgressWeekly` (canonical storage). Tambahkan `notes` atau atribut lain bila dibutuhkan oleh backend.

---

## 9. Troubleshooting Singkat

| Gejala | Penyebab Umum | Langkah Perbaikan |
| --- | --- | --- |
| Grid kosong / hanya latar putih | `ENABLE_AG_GRID` hidup tetapi AG Grid gagal mounting | Sementara set `ENABLE_AG_GRID=False` lalu reload; renderer legacy akan aktif kembali sambil Anda debug bundel baru. |
| Listener ganda / memory leak | Event legacy masih aktif bersamaan dengan Vite | Pastikan hanya satu controller yang diinisialisasi; gunakan `window.JadwalKegiatanApp` untuk cek status. |
| Fetch error `/api/jadwal-kegiatan/*` | Endpoint placeholder belum diganti | Manfaatkan `data-api-base` dari atribut HTML lalu panggil endpoint Django resmi. |
| Validasi tidak muncul | CSS `validation-enhancements.css` tidak dimuat atau modul `validation-utils.js` tidak dipanggil | Pastikan template menyertakan CSS baru dan `attachGridEvents` menggunakan helper `updateProgressIndicator`. |
| Toolbar Save tidak respon | `save_button` DOM ID mismatch | Pastikan template Vite memberikan id `save-button` (bukan `btn-save-all` saja). |

---

## 10. Referensi Terkait

- `DOCUMENTATION_OVERVIEW.md` â€“ indeks seluruh dokumentasi.
- `FINAL_IMPLEMENTATION_PLAN.md` â€“ detail per fase dan checklist AG Grid.
- `JADWAL_KEGIATAN_DOCUMENTATION.md` â€“ dokumentasi global halaman (backend + front-end).
- `PROJECT_ROADMAP.md` â€“ timeline resmi & status fase.

Keep this document updated setiap kali modul client-side berubah (misal: saat AG Grid dirilis atau endpoint API diganti).






