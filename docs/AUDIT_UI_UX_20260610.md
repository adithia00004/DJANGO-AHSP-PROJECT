# Audit UI/UX — Elemen Antarmuka & Peta Z-Index

**Tanggal:** 2026-06-10 06:50 WITA
**Basis:** HEAD `4d1f4353` + working tree
**Metode:** inventaris statis seluruh CSS (35 file app), template (semua app), dan JS; ekstraksi & klasifikasi 216 deklarasi `z-index` CSS + 38 `zIndex` JS + 7 template inline; pemeriksaan sistem theme, responsive, aksesibilitas, loading/feedback, dan dependensi vendor UI.
**Pelengkap:** `AUDIT_KESIAPAN_LAUNCH_20260609.md` (addendum per-app/per-page 2026-06-10) — dokumen ini fokus lapisan presentasi.

---

## 1. Ringkasan Eksekutif

- **Fondasi UI solid**: satu `templates/base.html` global yang diwarisi semua app, theme system light/dark/auto + density dengan anti-FOUC boot, 344 atribut `aria-*`, 28 rule `:focus-visible`, 121 media query + `toolbar-responsive.css`, folder print CSS khusus, design layer global (`core.css` + `corporate-theme.css` + `components-library.css`).
- **Masalah utama: "perang z-index"** — terdapat **5 generasi skala z-index yang hidup berdampingan** (Bootstrap 1000-an, legacy 2100-2501, generasi 9999, token resmi `--dp-z-*` 12005-13100, dan generasi "nuklir" 99998-100000). `core.css` sebenarnya sudah punya **skala token yang dirancang baik dan terdokumentasi**, tapi banyak komponen tidak mematuhinya.
- **2 bug layering hampir pasti** (toast tertutup modal) + beberapa risiko: dirinci di §4.
- Tidak ada blocker launch dari sisi UI/UX; perbaikan prioritas (§6) murah dan disarankan masuk sebelum/bersamaan UAT L7.

Severity: 🔴 Tinggi (bug nyata bagi user) · 🟡 Sedang (rapuh/inkonsisten) · 🟢 Rendah (kebersihan).

---

## 2. Inventaris Elemen UI per Lapisan

### 2.1 Shell global (`templates/base.html`)
| Elemen | Implementasi | Catatan |
|---|---|---|
| Theme boot | inline script set `data-bs-theme` + `data-theme` sebelum render; `html:not([data-theme-ready]){visibility:hidden}` | Anti-FOUC ✓; **tanpa fallback `<noscript>`** — halaman blank bila JS gagal (U8) |
| Vendor CSS | Bootstrap 5.3.3, Font Awesome 6.5.2, Bootstrap Icons 1.11.3 via CDN | **Tanpa SRI** + dependensi eksternal (U7) |
| App CSS global | `core.css`, `corporate-theme.css`, `error-recovery-modal.css`, `toast-global.css` | Urutan benar (vendor → app) |
| Messages modal | `#messagesModal` + `messages_modal.js` | Django messages → modal |
| Meta | `lang="id"`, viewport, `color-scheme: light dark` | ✓ |

### 2.2 Sistem komponen lintas halaman (detail_project)
| Komponen | File | Z-layer |
|---|---|---|
| Sidebar global | `_sidebar_global.html` + `sidebar_global.css` | token `--dp-z-sidebar` 12045 |
| Topbar/toolbar/searchbar | `_searchbar.html`, `toolbar-responsive.css` | token 12041-12044 |
| Toast terpusat | `js/core/toast.js` + `toast-global.css` | 13100 (= token `--dp-z-toast`) ✓ |
| Modal manager | `js/core/modal.js` | runtime bump +5/+4 utk modal bertumpuk (U4) |
| Sync LED | `_sync_led.html` + `sync_led.css` | rendah ✓ |
| Loading overlay + skeleton | `loading.css`, `loading-skeleton.css` | **9999 hardcode** (U6) |
| Export dropdown/loading modal | `_export_dropdown.html`, `_export_loading_modal.html` | Bootstrap default |
| Error recovery modal | `error-recovery-modal.css` | global |
| Param sidebar + formula editor | `param_sidebar_shared.css` | 13050/13054 hack (U4) |
| Fullscreen mode | `fullscreen-mode.css` | 12050 hardcode (U5) |

### 2.3 Per app lain
- **referensi**: base sendiri (`referensi/base.html` extends global) untuk halaman admin; halaman import extends `base.html` langsung. **3 implementasi toast duplikat** per-file JS (`ahsp_database.js`, `ahsp_database_v2.js`, `preview_import_v2.js`) masing-masing inline `zIndex 99999` (U2/U9). Dark-mode hanya 16 selector di 3 file CSS (U10).
- **dashboard**: 2 CSS (`dashboard.css`, `ux-enhancements.css`), Bootstrap-scale murni — bersih.
- **pages/subscriptions/account**: template Bootstrap standar; halaman auth allauth di `templates/account/`.

---

## 3. Peta Z-Index Lengkap

### 3.1 Skala token RESMI (`core.css:31-53`) — kanonik, terdokumentasi
```
--dp-z-search            12005   (search dropdown dalam halaman)
--dp-z-thead             12030   (header tabel sticky)
--dp-z-sticky            12031   (elemen sticky umum)
--dp-z-dropdown          12040
--dp-z-toolbar           12041
--dp-z-topbar            12044
--dp-z-sidebar           12045
--dp-z-backdrop          12990
--dp-z-modal             13000
--dp-z-overlay-backdrop  13042
--dp-z-overlay           13043
--dp-z-toast             13100   (teratas — by design)
```
Alias halaman: `--vp-z-search: var(--dp-z-search)` ✓ (pola benar).

### 3.2 Lima generasi skala yang ditemukan hidup bersama
| Generasi | Rentang | Lokasi | Status |
|---|---|---|---|
| Bootstrap vendor | 1000-1090 (1020×4, 1030×2, 1050×4, 1055) | dashboard, komponen BS | sah (vendor) |
| Legacy ribuan-rendah | 2100, 2500, 2501 | `list_pekerjaan.css` (sticky toolbar, overlay) | pra-token, belum dimigrasi |
| Generasi 9999 | 9998-9999 (×9), 10005-10011 | `loading.css`, `kelola_tahapan_grid.css`, `validation-enhancements.css`, select2 hack, toast referensi | off-scale |
| Token dp | 12005-13100 (+ 12032 fab, 12050 fullscreen, 13050-13060 formula/confirm hardcode) | core + halaman dp | kanonik (sebagian hardcode) |
| "Nuklir" | 99998, 99999 (×4 CSS + 4 JS), **100000** | `ahsp_database.css` (modal/backdrop `!important`), 3 toast JS referensi, `#templateLibraryModal` | eskalasi perang |

### 3.3 Deklarasi tinggi yang signifikan (bukti)
| Selektor | Nilai | File:Baris |
|---|---|---|
| `#templateLibraryModal` | **100000 !important** | `list_pekerjaan.css:1924` |
| `.modal.fade.show` (referensi) | 99999 !important | `ahsp_database.css:201` |
| `.modal-backdrop.show` (referensi) | 99998 !important | `ahsp_database.css:206` |
| toast referensi (JS inline) | 99999 | `ahsp_database.js:31`, `ahsp_database_v2.js:31`, `preview_import_v2.js:30`, `import_progress.js:367` |
| toast referensi (CSS) | 9999 | `ahsp_database.css:273` |
| select2 list-pekerjaan (3 lapis) | 10005/10010/10011 !important | `detail_project.css:78-80` |
| `#vpFormulaEditorModal` / `#dp-core-modal` / backdrop | 13050 / 13055 !important / 13054 !important | `volume_pekerjaan.css:2250-2261`, `param_sidebar_shared.css:1286-1287` |
| `#vpFormulaHelpModal` | 13060 | `volume_pekerjaan.css:1760` |
| Loading overlay global / grid / validation | 9999 | `loading.css:15`, `kelola_tahapan_grid.css:1240`, `validation-enhancements.css:286` |
| Fullscreen mode | 12050 (hardcode, komentar merujuk token) | `fullscreen-mode.css:67` |
| Sticky toolbar / overlay list_pekerjaan | 2500 / 2100 / 2501 | `list_pekerjaan.css:16,188,1942` |

---

## 4. Temuan (U1-U10)

| ID | Severity | Temuan | Dampak | Rekomendasi |
|---|---|---|---|---|
| U1 | 🔴 Tinggi | `#templateLibraryModal` **100000** > toast global **13100** | Saat modal Template Library terbuka (List Pekerjaan), SEMUA toast (sukses/gagal import template) render **di belakang modal** — feedback tak terlihat user | Turunkan ke rentang modal token (≤13041) atau naikkan area toast saat modal ini aktif; idealnya pakai `var(--dp-z-modal)` |
| U2 | 🔴 Tinggi | Referensi: modal 99999 vs toast JS 99999 (seri — urutan DOM yang menentukan) dan toast CSS 9999 < modal 99999 | Toast feedback CRUD database AHSP berisiko tertutup modal yang sedang terbuka | Samakan ke satu skala; toast harus > modal (tiru pola dp: toast = modal+100) |
| U3 | 🟡 Sedang | Select2 (CDN, **versi RC sejak 2020**) butuh hack 3 lapis `!important` 10005-10011 dan nilainya < topbar 12044/sidebar 12045 | Dropdown autocomplete bisa terpotong elemen sticky; hack menandakan stacking-context conflict dengan `.dp-scope` | Render dropdown ke `body` via opsi `dropdownParent`, hapus hack; pertimbangkan ganti select2-RC dengan komponen yang dipakai di volume (custom dropdown sudah ada) |
| U4 | 🟡 Sedang | Modal bertumpuk diatur via JS runtime bump (+5/+4) + selector rapuh `~.modal-backdrop:last-of-type` 13054 `!important` | Bergantung detail DOM Bootstrap; upgrade BS minor bisa merusak urutan backdrop | Konsolidasi ke `js/core/modal.js` satu-satunya pengatur, tambah token `--dp-z-modal-2` (13050) & `--dp-z-confirm` (13055) agar CSS tak perlu `!important` |
| U5 | 🟢 Rendah | Hardcode yang sebetulnya merujuk token: fullscreen 12050, fab 12032, formula 13050-13060 | Token scale tak bisa digeser tanpa grep manual | Ganti angka → `calc(var(--dp-z-...) + n)` atau token baru |
| U6 | 🟢 Rendah | Generasi 9999 (loading overlay global, grid overlay, validation tooltip) & legacy 2100-2501 (`list_pekerjaan`) di luar skala | Kebetulan masih benar urutannya (9999 < 12005) — loading overlay global justru DI BAWAH topbar/sidebar dp; tapi rapuh | Migrasi bertahap ke token saat menyentuh file terkait |
| U7 | 🟡 Sedang | Vendor UI via CDN **tanpa SRI**: Bootstrap, FA, BI, select2 (+`select2` versi `4.1.0-rc.0`) | Supply-chain risk + gagal total bila CDN tak terjangkau (klien proyek sering di jaringan terbatas); menyulitkan CSP ketat di L5 | Self-host via pipeline Vite/static yang sudah ada, atau minimal tambah atribut `integrity` |
| U8 | 🟢 Rendah | `html:not([data-theme-ready]){visibility:hidden}` tanpa `<noscript>` fallback | JS error/diblokir → halaman blank permanen | Tambah `<noscript><style>html{visibility:visible}</style></noscript>` |
| U9 | 🟡 Sedang | **3 implementasi toast duplikat** di referensi (per-file, inline style, zIndex 99999) vs sistem toast terpusat dp (`core/toast.js`) | UX feedback tidak konsisten antar app (posisi/durasi/gaya beda); triple maintenance | Pakai `dp-toast` global (sudah dimuat di base.html) — hapus 3 duplikat |
| U10 | 🟡 Sedang | Dark-mode coverage timpang: detail_project penuh (token + data-theme), referensi hanya 16 selector di 3 CSS, dashboard minim | Berpindah halaman dp (dark rapi) → referensi/dashboard berpotensi kontras rusak/elemen putih menyilaukan | Sapu visual dark-mode per halaman saat UAT; tambah variant `[data-theme="dark"]` di CSS referensi/dashboard |

---

## 5. Aspek UI/UX yang DINILAI BAIK (jangan diubah)

- **Skala token `--dp-z-*` itu sendiri** — desain berlapis dengan gap antar layer, terdokumentasi inline; masalahnya kepatuhan, bukan desain.
- **Theme system**: light/dark/auto + density, sinkron `data-bs-theme` (Bootstrap) + `data-theme` (custom), event `theme:changed` untuk komponen, anti-FOUC, `color-scheme` meta.
- **Pola feedback data-entry**: dirty-guard → save eksplisit → sync LED → toast — konsisten di seluruh halaman dp.
- **Aksesibilitas**: 344 `aria-*` (terbanyak di volume 61, template_ahsp 49, rincian_ahsp 32), 28 `:focus-visible`, `lang="id"`; pernah dijalankan WCAG check lokal (`_wcag_check*`).
- **Responsif**: 121 media query + file khusus `toolbar-responsive.css`; grid jadwal punya fullscreen mode.
- **Print stylesheet** terpisah (4 file `css/print/`) untuk output laporan.
- **Loading states berlapis**: skeleton + overlay + export progress modal.

---

## 6. Rekomendasi Prioritas

**Sebelum/bersamaan UAT L7 (murah, mencegah bug terlihat user):**
1. U1 — turunkan `#templateLibraryModal` ke skala token (1 baris).
2. U2 + U9 — referensi pindah ke `dp-toast` global + samakan z modal (hapus 99999-an).
3. U3 — `dropdownParent: $(document.body)` pada inisialisasi select2 (2 callsite), hapus hack `detail_project.css:78-80`.

**Pasca-launch (bertahap, saat menyentuh file terkait):**
4. U4/U5 — token-isasi nilai 12032-13060 + jadikan `core/modal.js` satu-satunya pengatur stacking.
5. U6 — migrasi generasi 9999/legacy 2xxx ke token.
6. U7 — self-host vendor UI lewat Vite (selaras roadmap restrukturisasi frontend #4 di catatan arsitektur).
7. U10 — sapu dark-mode referensi/dashboard.
8. U8 — `<noscript>` fallback (1 baris).

**Aturan tunggal ke depan** (usul untuk ditegakkan via review/guard): *semua `z-index` baru WAJIB memakai `var(--dp-z-*)` atau `calc()` darinya; angka literal >100 di luar `core.css` ditolak.* Guard otomatis bisa meniru pola `xss_governance_guard.test.js` — test vitest yang nge-grep nilai literal.

---

## 7. Checklist Visual untuk UAT L7 (turunan temuan)

- [ ] Buka Template Library di List Pekerjaan → trigger import sukses & gagal → toast HARUS terlihat (U1).
- [ ] CRUD di Database AHSP referensi dengan modal terbuka → toast terlihat (U2).
- [ ] Select2 di List Pekerjaan & Template AHSP dekat tepi atas/bawah viewport → dropdown tidak terpotong (U3).
- [ ] Volume: buka Formula Editor → buka confirm dialog di atasnya → urutan benar, backdrop tidak menelan modal (U4).
- [ ] Jadwal: fullscreen mode → toolbar/topbar tidak menembus (U5).
- [ ] Dark mode: lintasi SEMUA halaman referensi & dashboard (U10).
- [ ] Matikan jaringan ke CDN (DevTools block) → halaman masih dapat dipakai? (U7 — saat ini TIDAK; verifikasi setelah self-host).
- [ ] Print preview Rekap RAB/laporan — stylesheet print bekerja.

---

## 8. Addendum Inventaris Elemen Per-Halaman — 2026-06-10 07:05 WITA

Melengkapi §2 (yang per-sistem) dengan enumerasi elemen interaktif **per halaman untuk SEMUA app**: modal/popup (dengan ID), dropdown, sidebar, sticky, tooltip, tab, dan elemen yang dibuat JS secara dinamis.

### 8.0 Elemen GLOBAL (hadir di semua halaman via `base.html` / `base_detail.html`)
| Elemen | Sumber | Z-layer |
|---|---|---|
| `#messagesModal` (Django messages → popup) | `base.html` | Bootstrap modal |
| Toast area terpusat `dp-toast-area` (top-right, max 3) | `core/toast.js` (dimuat global) | 13100 ✓ |
| Error recovery modal | `error-recovery-modal.css` + handler | global |
| Theme toggle + early-boot anti-FOUC | `base.html` + `theme.js` | — |
| **Khusus detail_project** (via `base_detail.html`): sidebar global (`_sidebar_global.html`), project identity bar (`_project_identity.html`) | include otomatis 12 halaman | sidebar 12045, topbar 12044 |

### 8.1 detail_project — elemen per halaman (12/12 halaman tercakup)

| Halaman | Modal/Popup (ID) | Dropdown | Sticky | Tooltip/title | Elemen JS dinamis |
|---|---|---|---|---|---|
| List Pekerjaan | `templateLibraryModal` (**z=100000, U1**), `saveTemplateModal`, `templatePreviewModal`, + `_modal_referensi` (picker AHSP) | 14 (export, aksi baris) | 3 (toolbar z=2500 legacy) | 13 | **select2** picker AHSP (z-hack 10005-10011, U3); drag-drop tree |
| Volume Pekerjaan | `vpFormulaEditorModal` (13050), `vpParamPaletteModal`, `vpFormulaHelpModal` (13060) | 24 (terbanyak) | 3 | 21 | search dropdown (`--vp-z-search`), suggest list autocomplete param, action toast, param sidebar editor, FAB (12032) |
| Template AHSP | `taFormulaEditorModal` (13050), `taParamPaletteModal`, `taHelpModal` | 18 | 7 (terbanyak — header kolom) | 12 | **select2** (z-hack, U3), param sidebar shared, suggest list |
| Harga Items | `hiConvModal` (profil konversi) | 9 | 4 | 0 | inline edit numerik |
| Rincian AHSP | `raOverrideModal`, `raHelpModal`, popover override `ovr-modal-kode`/`ovr-modal-uraian` | 9 | 2 | 6 | render tabel bertingkat + subtotal |
| Rekap RAB | — (pakai export dropdown partial + `_export_loading_modal`) | 8 | 1 | 14 | ExcelExporter client-side |
| Rekap Kebutuhan | `rk-export-modal`, `rk-filter-modal` | 3 | 1 | 12 | **echarts** canvas, autocomplete `rk-autocomplete` (esc ✓), toolbar dinamis |
| Rincian RAB | — | 4 | 0 | 1 | JS inline (±120 baris) |
| Jadwal Pekerjaan | `exportModal`, `exportProgressModal`, `confirmModal`, `successModal` | 9 | 1 | 8 | TanStack grid overlay (z 2/4), Gantt canvas overlay, **Kurva-S canvas tooltip (z 50) + legend (z 40)**, fullscreen mode (12050), 1 nav-tabs (grid/gantt/kurva) |
| Orphan Cleanup | — (halaman polos: tabel + tombol) | 0 | 0 | 0 | — |
| Audit Trail | — (halaman polos) | 0 | 0 | 0 | — |
| Export Test | — (halaman dev, F14) | 0 | 0 | 0 | — |

### 8.2 dashboard

| Halaman | Modal/Popup (ID) | Elemen lain |
|---|---|---|
| Dashboard utama | `addProjectModal`, `importProjectModal`, `dpConfirmModal` (konfirmasi bulk, di partial `_project_stats_and_table` — 25 ref modal utk aksi per-baris) | sticky header tabel; mass-edit toggle; resizable columns (JS); formset dinamis |
| Project Detail | `copyProjectModal` (duplicate) | kartu statistik |
| Edit/Delete/Duplicate confirm | halaman terpisah (`project_confirm_delete/duplicate.html`) — bukan popup | form crispy |
| Upload Excel | — | formset multi-baris |

### 8.3 referensi

| Halaman | Modal/Popup (ID) | Elemen lain |
|---|---|---|
| Admin Portal | — (kartu navigasi polos) | — |
| AHSP Database v2 | `edit-modal` (CRUD), `modalBulkDelete` (z **99999**, U2) | 5 dropdown filter; toast JS sendiri 99999 (U9); pagination |
| Pricing Management | — (form inline) | tabel plan/promo |
| Import: options/pdf-convert/upload | — | progress bar (`import_progress.js`, warning z 99999) |
| Import: validate report | `assistedRepairModal` (WYSIWYG repair) | 2 sticky; editor embedded besar |
| Import: staging | — | tabel staging + aksi commit/clear |
| Audit dashboard/logs/statistics | — | tabel + filter |

### 8.4 pages, subscriptions, accounts

| Halaman | Elemen | Catatan |
|---|---|---|
| Landing | navbar fixed-top, hero, kartu fitur | tanpa modal |
| Pricing | navbar fixed-top, kartu plan | tanpa modal |
| Checkout | ringkasan plan + tombol bayar → **Snap.js popup Midtrans** (iframe pihak ketiga, z-index dikelola Snap) | perlu dicek vs navbar saat UAT |
| Login/Signup/Reset/Verifikasi (8 template allauth) | form crispy polos | tanpa modal; rate-limit feedback via halaman |
| 404/500 | statis + tombol kembali | error 500 menampilkan debug info hanya saat DEBUG |

### 8.5 Temuan tambahan dari inventaris per-halaman

| ID | Severity | Temuan | Rekomendasi |
|---|---|---|---|
| U11 | 🟡 Sedang | **27 callsite `confirm()`/`alert()` native** masih dipakai (terbanyak `template_ahsp.js` 9, `detail_ahsp_gabungan.js` 4, `volume_pekerjaan.js` 3, referensi 4) padahal sistem `dp-core-modal` + toast sudah ada | Konsistenkan ke `core/modal.js` confirm — native dialog tidak ter-theme (dark mode), memblokir thread, dan tampil berbeda per browser |
| U12 | 🟢 Info | 3 halaman dp polos (orphan-cleanup, audit-trail, export-test) tanpa elemen berlapis — risiko UI nol | — |
| U13 | 🟢 Info | Checkout bergantung popup Snap.js Midtrans (z-index eksternal) | Masukkan ke checklist UAT: popup Snap muncul di atas semua elemen |

### 8.6 Pernyataan cakupan

Dengan addendum ini, audit UI/UX telah meng-cover **semua 6 app dan seluruh halaman ber-UI**: 12 halaman detail_project, 4 kelompok dashboard, 7 kelompok referensi (termasuk seluruh alur import 3-tier), 2 pages, checkout subscriptions, 8 template allauth, 2 halaman error, plus elemen global (sidebar, topbar, toast, messages modal, error-recovery, theme). Elemen yang dibuat dinamis oleh JS (select2, autocomplete, canvas tooltip, grid overlay, FAB, toast, Snap popup) ikut terinventaris. Verifikasi **visual** (bukan statis) tetap menjadi bagian UAT browser L7 — gunakan checklist §7.

---

## 9. Rekomendasi Perbaikan + Checklist Pemeriksaan Manual — 2026-06-10 07:43 WITA

### 9.0 Koreksi konteks dari pemilik produk (2026-06-10)

1. **Rincian RAB adalah halaman legacy** — fungsinya sudah digantikan Rincian AHSP dan Rekap RAB. Rekomendasi sidebar di percakapan audit (menambahkan Rincian RAB ke menu) **DIBATALKAN**; rekomendasi yang benar = pensiunkan halamannya (U15).
2. **Orphan Cleanup & Audit Trail dimaksudkan admin-only.** Verifikasi kode menunjukkan intent ini **belum terimplementasi** (U14).

### 9.1 Temuan baru hasil verifikasi konteks

| ID | Severity | Temuan | Bukti | Rekomendasi |
|---|---|---|---|---|
| U14 | 🟡 Sedang | **Intent ≠ implementasi: Orphan Cleanup & Audit Trail terlihat & dapat diakses SEMUA pemilik proyek**, bukan admin-only. Sidebar me-render kedua link tanpa kondisi role; view hanya `@login_required` + owner; tidak ada penyembunyian via JS/CSS | `_sidebar_global.html:117-124` (orphan) & `:136-143` (audit) tanpa `{% if %}` role; `views.py:178,188` tanpa cek staff; `sidebar_global.js` tanpa logika role | Bungkus kedua `<li>` dengan `{% if request.user.is_staff %}` DAN tambah `@user_passes_test(lambda u: u.is_staff)` di kedua view (defense-in-depth). Catatan: ini bukan kebocoran data (tetap owner-scoped), tapi fitur "usang" terekspos ke semua user |
| U15 | 🟢 Rendah | **Halaman Rincian RAB yatim total**: tidak ada satu pun link masuk dari template/JS lain (hanya disebut `sync_led.js` & template-nya sendiri); route + API + export CSV masih hidup | grep inbound-link = 0; `urls.py:34,134-135` | Ikuti pola deprecation yang sudah ada (seperti tahapan v1): beri deprecation header + telemetry, atau langsung redirect 301 → `rincian-ahsp`. Hapus route+template+JS inline+2 API endpoint setelah window deprecation |

### 9.2 Checklist Pemeriksaan MANUAL (urut prioritas — buka, klik, bandingkan)

Setiap butir: **cara memeriksa → hasil yang BENAR → lokasi fix bila rusak.**

**M1 — Toast tertutup modal Template Library (U1) — 🔴 periksa pertama**
- *Cara:* List Pekerjaan → tombol Template Library → modal terbuka → lakukan import template (atau aksi yang memunculkan notifikasi).
- *Benar:* toast hijau/merah muncul **di atas** modal, pojok kanan-atas.
- *Rusak (prediksi kode):* toast tidak terlihat (tertutup modal z=100000 vs toast 13100).
- *Fix:* `list_pekerjaan.css:1924` — ganti `100000 !important` → `var(--dp-z-modal)`.

**M2 — Toast referensi vs modal bulk delete (U2/U9)**
- *Cara:* Database AHSP v2 → pilih beberapa item → buka modal Bulk Delete → eksekusi → amati notifikasi.
- *Benar:* notifikasi hasil terlihat penuh.
- *Rusak:* toast di belakang modal/backdrop (toast CSS 9999 < modal 99999; toast JS 99999 seri dengan modal — tergantung urutan DOM).
- *Fix:* `ahsp_database.css:201-206` turunkan ke skala Bootstrap; 3 toast JS referensi diganti panggilan `dp-toast` global (sudah dimuat di base.html).

**M3 — Select2 terpotong elemen sticky (U3)**
- *Cara:* List Pekerjaan → buka picker AHSP (select2) saat baris berada dekat topbar; ulangi di Template AHSP; scroll saat dropdown terbuka.
- *Benar:* dropdown utuh, mengikuti input.
- *Rusak:* terpotong topbar/sidebar (z 10005-10011 < topbar 12044).
- *Fix:* tambahkan `dropdownParent: $(document.body)` di init select2 (2 callsite JS), lalu hapus hack `detail_project.css:78-80`.

**M4 — Modal bertumpuk Formula Editor (U4)**
- *Cara:* Volume → buka Formula Editor → dari dalamnya picu confirm (mis. tutup dengan perubahan belum disimpan) → tutup keduanya berurutan.
- *Benar:* confirm di atas editor; setelah semua ditutup TIDAK ada backdrop abu-abu tersisa; halaman bisa di-scroll.
- *Rusak:* backdrop nyangkut / urutan terbalik (selector `~.modal-backdrop:last-of-type` rapuh).
- *Fix:* token-isasi 13050/13054/13055 di `volume_pekerjaan.css:2250-2261` + `param_sidebar_shared.css:1286-1287`; jadikan `core/modal.js` satu-satunya pengatur.

**M5 — Dark mode referensi & dashboard (U10)**
- *Cara:* toggle tema gelap → telusuri: Database AHSP v2, Import Validate Report, Staging, Audit Dashboard, Dashboard utama.
- *Benar:* semua permukaan/teks/tabel mengikuti tema.
- *Rusak (prediksi):* panel putih menyilaukan / teks gelap di atas gelap (referensi hanya punya 16 selector dark di 3 CSS).
- *Fix:* tambah variant `[data-theme="dark"]` di `ahsp_database.css`, `preview_import.css`, `import_progress.css`, `dashboard.css`.

**M6 — Dialog native vs custom (U11)**
- *Cara:* Template AHSP → hapus komponen/reset; Rincian AHSP → override; Database AHSP → hapus.
- *Benar (target):* semua konfirmasi memakai modal ber-tema (`dp-core-modal`).
- *Saat ini:* 27 callsite `confirm()`/`alert()` native (kotak abu-abu OS, tidak dark-mode).
- *Fix:* ganti bertahap ke `core/modal.js` confirm; mulai dari `template_ahsp.js` (9 callsite).

**M7 — Visibilitas gating Pro pada tombol Export (rekomendasi penyajian)**
- *Cara:* login akun TRIAL → Rekap RAB / Harga Items → buka dropdown Export → klik Export PDF.
- *Saat ini:* tombol tampak normal, gagal SETELAH diklik (403 → pesan).
- *Target yang disarankan:* item PDF/Word/Excel ter-disable + ikon gembok + tooltip "Fitur Pro — upgrade" (link pricing). Diskon kejutan = nol, sekaligus titik konversi.
- *Fix:* view kirim flag entitlement ke context → `_export_dropdown.html` render kondisi disabled; data sudah tersedia via `get_feature_access`.

**M8 — Admin-only Orphan/Audit (U14)**
- *Cara:* login akun user biasa (non-staff) → buka project → lihat sidebar.
- *Saat ini (terverifikasi kode):* kedua menu TERLIHAT dan halamannya bisa dibuka.
- *Target sesuai intent:* hanya staff/superuser.
- *Fix:* lihat U14 (template `{% if %}` + decorator view).

**M9 — Halaman Rincian RAB legacy (U15)**
- *Cara:* akses langsung `/detail_project/<id>/rincian-rab/`.
- *Saat ini:* halaman hidup penuh (route+API+export) tapi tanpa pintu masuk.
- *Fix:* redirect → `rincian-ahsp` atau deprecation window; bersihkan `urls.py:34,134-135`.

**M10 — Snap.js checkout (U13)**
- *Cara:* checkout sandbox Midtrans → popup pembayaran muncul.
- *Benar:* popup di atas seluruh elemen, bisa ditutup, halaman pulih.

**M11 — Ketahanan tanpa CDN (U7)**
- *Cara:* DevTools → Network request blocking: `cdn.jsdelivr.net`, `cdnjs.cloudflare.com` → reload halaman mana pun.
- *Saat ini:* layout hancur total (Bootstrap CSS dari CDN) — dicatat sebagai keputusan sadar; self-host direkomendasikan saat L5 (selaras CSP).

**M12 — Fallback tanpa JS (U8)**
- *Cara:* disable JavaScript → buka halaman login.
- *Saat ini:* blank permanen (`visibility:hidden` menunggu theme-boot).
- *Fix:* 1 baris `<noscript>` di `base.html`.

### 9.3 Urutan eksekusi yang disarankan

| Kapan | Item | Effort |
|---|---|---|
| Sebelum UAT L7 | M1 (1 baris), M8/U14 (intent admin-only), M2 | ~1 jam |
| Bersamaan UAT L7 | M3, M4, M5, M10 (verifikasi visual checklist §7) | per temuan |
| Sebelum public launch | M7 (gating terlihat — nilai konversi), M9/U15 (tutup pintu legacy), M12 | ~½ hari |
| Pasca-launch bertahap | M6 (27 callsite), M11 (self-host vendor), token-isasi §6 | roadmap frontend #4 |

---

## 10. STANDAR: Kontrak Feedback UI Seragam — 2026-06-10 09:40 WITA

**Usulan pemilik produk (2026-06-10):** semua elemen feedback yang muncul berulang dengan konteks/konten berbeda — toast, popup, pesan — harus seragam di seluruh web. **Disetujui sebagai standar.** Section ini menjadi acuan resmi; menyatukan akar temuan U1, U2, U9, U11.

### 10.1 Fakta kunci (verifikasi 2026-06-10)

Sistem seragamnya **sudah ada dan sudah dimuat global** untuk SEMUA app via `templates/base.html`:
- `base.html:347` → `core/toast.js` — expose **`window.DP.toast`** + preset (`DP.toast.export.started()` dst.) + shim kompat `window.showToast` (komentar kode: *"for easy migration"* — konsolidasi ini memang by-design, tinggal diselesaikan adopsinya).
- `base.html:349` → `core/modal.js` — expose **`DP.modal`** (`dp-core-modal`, confirm/alert ber-tema).
- `base.html:345` → `messages_modal.js` — Django messages → `#messagesModal`.

Kesimpulan: pekerjaan = **adopsi/penertiban**, bukan membangun komponen baru.

### 10.2 Kontrak (acuan untuk semua kode baru & migrasi kode lama)

| Kategori | Kapan dipakai | Satu-satunya implementasi yang SAH | Status adopsi saat ini |
|---|---|---|---|
| **Toast** — notifikasi non-blocking (sukses/gagal/info/progress singkat) | hasil save, export, sync, CRUD | `DP.toast` (z=13100 token, top-right, max 3, durasi 3 dtk, dark-mode ✓) | dp ✓; **referensi: 3 duplikat lokal** (`ahsp_database.js`, `ahsp_database_v2.js`, `preview_import_v2.js` — U9) |
| **Confirm/Alert** — keputusan blocking | hapus, reset, keluar tanpa save | `DP.modal.confirm` / `DP.modal.alert` | **27 callsite `confirm()`/`alert()` native** (U11) |
| **Pesan server** — feedback pasca-redirect | Django messages | `#messagesModal` | global ✓ |
| **Loading/progress** — operasi panjang | export, proses batch | loading overlay + `_export_loading_modal` | dp ✓ |
| **Validasi inline** — error per-field | input form | `validation-enhancements.css` | dp ✓ |

**Dikecualikan dari kontrak (sengaja TIDAK diseragamkan):**
- Popup pembayaran **Snap.js Midtrans** — dikelola pihak ketiga, jangan disentuh.
- Halaman **allauth** — form server-rendered murni; `messagesModal` sudah memadai.
- **Progress bar import referensi** — long-running batch dengan UI khusus, bukan notifikasi.

### 10.3 Aturan untuk kode baru

1. DILARANG membuat elemen toast/notifikasi ad-hoc (`createElement` + inline style) — panggil `DP.toast`.
2. DILARANG `confirm()` / `alert()` native — panggil `DP.modal` (async; gunakan `await`/callback).
3. DILARANG set `z-index` literal pada elemen feedback — layer sudah diatur token (`--dp-z-toast` 13100 > `--dp-z-modal` 13000).
4. Pesan sukses singkat = toast; keputusan destruktif = confirm modal; jangan dibalik.

### 10.4 Rencana migrasi (kode lama)

| Langkah | Scope | Menutup | Effort | Kapan |
|---|---|---|---|---|
| 1 | Referensi → `DP.toast`: ganti 3 implementasi toast lokal + inline z 99999 (4 file JS) | U2 + U9 (+sebagian U1-class) | ~1 jam | **Sebelum UAT L7** |
| 2 | Guard test anti-regresi (pola `xss_governance_guard`): vitest gagal bila ada `confirm(`/`alert(`/toast `createElement` baru di luar `js/core/` | mencegah kambuh | ~1 jam | Bersamaan langkah 1 |
| 3 | 27 callsite `confirm()`/`alert()` → `DP.modal`, bertahap per file mulai `template_ahsp.js` (9) → `detail_ahsp_gabungan.js` (4) → `volume_pekerjaan.js` (3) → referensi (4) → sisanya | U11 | ±5 mnt/callsite + smoke test per aksi | Pasca-launch bertahap |
| 4 | (Opsional) seragamkan loading overlay ke satu komponen | konsistensi lanjutan | — | roadmap frontend #4 |

**Catatan teknis langkah 3 (satu-satunya bagian non-mekanis):** `confirm()` native bersifat sinkron-blocking; `DP.modal.confirm` asinkron — setiap callsite `if (confirm(...)) {...}` perlu direstrukturisasi menjadi `await`/callback. Karena menyentuh aksi destruktif, wajib smoke test per aksi; jangan mass-replace satu commit.

### 10.5 Record eksekusi — 2026-06-10 10:55 WITA

Langkah 1+2 §10.4 plus item pra-UAT §9.3 **DIEKSEKUSI**:

| Item | Perubahan | Hasil |
|---|---|---|
| **M1/U1** | `list_pekerjaan.css` — `#templateLibraryModal` 100000 → `var(--dp-z-modal)` | toast (13100) kini selalu di atas modal |
| **M8/U14** | Decorator baru `staff_only_page` (`views.py`) pada `orphan_cleanup_view` + `audit_trail_view` (redirect ke List Pekerjaan + pesan); sidebar: kedua `<li>` dibungkus `{% if request.user.is_staff or is_superuser %}` | + file test baru `tests_admin_only_pages.py` (4 test: non-staff redirect, staff 200, sidebar hide/show); `tests_page_cache_headers` owner → staff |
| **M2/U2/U9 (langkah 1)** | 3 fallback toast referensi → z token `var(--dp-z-toast)`; `ahsp_database_api.js` (duplikat ke-4, baru terdeteksi guard!) kini delegasi `DP.toast`; warning memori `import_progress.js` → `DP.toast.show`; `ahsp_database.css` modal/backdrop 99999/99998 → token 13000/12990, toast util → 13100 | Semua notifikasi referensi seragam via `DP.toast`; tidak ada z literal 9xxxx tersisa |
| **Langkah 2 (guard)** | File test baru `feedback_governance_guard.test.js`: (a) larang `style.zIndex` literal ≥1000 di luar `js/core/`; (b) budget `confirm()`/`alert()` per file — baseline **18 file, total budget 37 callsite** (guard menemukan 7 file tambahan yang luput dari grep manual, termasuk modul `src/`), hanya boleh turun | 2 test hijau |
| Bonus | `volume_pekerjaan.js` boost 13055/13054 literal → `var(--dp-z-confirm, 13055)` / `var(--dp-z-confirm-backdrop, 13054)` | sebagian U5 tertutup |

Catatan koreksi data: jumlah callsite native sebenarnya **±37 di 18 file** (bukan 27 — grep awal melewatkan folder `src/` dan beberapa modul). Tabel `NATIVE_DIALOG_BUDGET` di guard test adalah angka otoritatif; angka 27 pada U11/M6 di atas dibaca sebagai perkiraan awal.

### 10.6 Definisi selesai

- `grep -rn "confirm(\|alert(" --include="*.js"` (non-test, non-vendor, di luar `js/core/`) = 0 hasil.
- Tidak ada `zIndex`/`z-index` literal pada elemen feedback di luar `core.css`/`toast-global.css`.
- Guard test langkah 2 hijau di CI.
- Satu perilaku feedback yang identik di seluruh halaman saat UAT (posisi, durasi, gaya, dark-mode).
