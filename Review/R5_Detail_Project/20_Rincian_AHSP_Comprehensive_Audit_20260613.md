# Audit Komprehensif Page Rincian AHSP

**Tanggal audit:** 13 Juni 2026  
**Target:** `/detail_project/<project_id>/rincian-ahsp/`  
**Objek:** current working tree pada saat audit  
**Status:** **BELUM PRODUCTION-READY - terdapat temuan Critical pada default markup dan konsistensi web/export**

## 1. Ringkasan Eksekutif

Rincian AHSP adalah page inspeksi perhitungan harga satuan pekerjaan, bukan editor komponen AHSP. Tanggung jawab aktualnya:

- memilih pekerjaan REF, MOD, atau CUS;
- menampilkan komponen TK, BHN, ALT, dan LAIN;
- menghitung biaya komponen sebelum markup;
- menerapkan markup default project atau override per pekerjaan;
- menampilkan harga satuan setelah markup;
- membuka breakdown pekerjaan gabungan/bundle;
- memperlihatkan warning perubahan source/volume;
- mengekspor Rincian AHSP ke XLSX, PDF, dan Word.

Komponen dan koefisien tetap diedit pada Template AHSP. Harga dasar tetap diedit pada Harga Items. Rincian AHSP hanya boleh mengubah override markup per pekerjaan.

Fondasi yang sudah baik:

- page dan seluruh API owner-scoped;
- output dinamis utama di-escape;
- detail per pekerjaan dimuat lazy dan di-cache;
- stale request dibatalkan dengan `AbortController`;
- race selection dijaga token;
- source filter, search, keyboard navigation, resizer, dark mode, reduced motion, dan forced colors tersedia;
- override divalidasi 0-100 di frontend dan backend;
- bundle dapat dibuka untuk melihat komponen dasar;
- perhitungan utama membaca `HargaItemProject.harga_satuan`;
- project markup dan override pekerjaan dipisahkan.

Masalah utama:

1. Jika `ProjectPricing` belum ada, service menghitung markup 0%, tetapi API/UI menyatakan default 10%. Detail/list dapat tampil 10%, sementara Grand Total memakai total 0%.
2. Web dan export mempunyai kontrak total berbeda. Web Grand Total memakai `G x volume + PPN`, sedangkan export Rincian AHSP menjumlahkan harga satuan `G` tanpa volume/PPN.
3. Adapter export menghitung ulang data sendiri, tidak memakai calculation service yang sama, dan mempunyai beberapa drift field/default.
4. Template masih menampilkan kontrol Save, dirty, dan Reset yang tidak berfungsi.

## 2. Kontrak Produk dan SSOT

Kontrak yang direkomendasikan mengikuti keputusan audit Template AHSP:

| Nilai | Nama kanonik | Sumber |
|---|---|---|
| Biaya komponen sebelum markup | `component_cost_before_markup` | Koefisien x `HargaItemProject.harga_satuan` |
| Persentase markup | `effective_markup_percent` | Override pekerjaan atau default project |
| Nilai markup | `markup_amount` | Biaya komponen x markup |
| Harga satuan final pekerjaan | `unit_price_after_markup` | Biaya komponen + markup |
| Total pekerjaan | `job_total_cost` | Harga satuan final x volume |

Rincian AHSP seharusnya berfokus pada tiga nilai pertama dan harga satuan final. Total pekerjaan, PPN, serta pembulatan merupakan konteks Rekap RAB.

## 3. Ruang Lingkup dan Komponen

| Area | Implementasi |
|---|---|
| Page view | `detail_project.views.rincian_ahsp_view` |
| Rekap list | `api_get_rekap_rab`, `compute_rekap_for_project` |
| Detail pekerjaan | `api_get_detail_ahsp`, `build_detail_ahsp_payload` |
| Override markup | `api_pekerjaan_pricing` |
| Bundle breakdown | `api_get_bundle_expansion` |
| Template | `detail_project/templates/detail_project/rincian_ahsp.html` |
| JavaScript | `detail_project/static/detail_project/js/rincian_ahsp.js` |
| CSS | `detail_project/static/detail_project/css/rincian_ahsp.css` |
| Export | `RincianAHSPAdapter`, `ExportManager` |

Ukuran implementasi utama:

- `rincian_ahsp.js`: sekitar 1.600 baris;
- `rincian_ahsp.html`: sekitar 390 baris;
- `rincian_ahsp.css`: sekitar 760 baris.

Tidak ditemukan test khusus implementasi aktual `rincian_ahsp.js`. Komentar file yang menyatakan 22 test `test_rincian_ahsp.py` tidak sesuai dengan file test yang tersedia.

## 4. Audit Per Mode dan Elemen Interaktif

### 4.1 Initial Load

**Status:** Baik bersyarat.

- project pricing dan seluruh row rekap di-fetch lebih dahulu;
- pekerjaan terakhir dipulihkan dari localStorage;
- detail pekerjaan dipanggil terpisah;
- pricing pekerjaan dipanggil terpisah;
- initial job membutuhkan sampai tiga request setelah HTML.

Tidak ada SSR bootstrap untuk pekerjaan pertama seperti Template AHSP dan Harga Items.

### 4.2 Mode REF

**Status:** Fungsional jika detail referensi sudah di-clone.

- page menampilkan komponen read-only;
- override markup tetap dapat diterapkan, sesuai fungsi Rincian AHSP;
- jika raw detail REF tidak tersedia, endpoint melakukan fallback ke referensi tetapi tidak menyertakan harga item;
- calculation rekap tidak mempunyai fallback langsung ke `RincianReferensi`.

REF dengan `auto_load_rincian=False`, data legacy, atau clone gagal dapat tampil dengan harga nol dan total nol.

### 4.3 Mode MOD

**Status:** Fungsional.

- detail hasil modifikasi ditampilkan;
- harga berasal dari Harga Items;
- override markup tersedia;
- source badge membedakan MOD.

Perubahan komponen tetap harus dilakukan pada Template AHSP.

### 4.4 Mode CUS Direct

**Status:** Fungsional bersyarat.

- komponen direct ditampilkan dari raw detail;
- perhitungan row memakai koefisien x harga dasar;
- subtotal kategori dan harga satuan final dihitung di browser;
- readiness/error expansion belum terlihat.

### 4.5 Mode CUS Bundle/Nested

**Status:** Fungsional bersyarat.

- row bundle menampilkan harga per satu unit bundle;
- jumlah row memakai quantity bundle x harga per unit bundle;
- klik row membuka komponen expanded;
- komponen expansion ditampilkan per satu unit bundle.

Kelemahan:

- row hanya dapat dibuka dengan pointer;
- label tidak cukup menjelaskan bahwa breakdown adalah per unit, bukan setelah quantity bundle;
- endpoint dan komentar mempunyai kontrak koefisien yang bertentangan;
- diagnostic stale/partial/failed expansion belum ditampilkan.

### 4.6 Override Markup

**Status:** Fungsional bersyarat.

- override disimpan langsung dari modal;
- clear mengembalikan default project;
- cache rekap di-invalidasi;
- UI dan Grand Total di-refresh.

Kelemahan:

- input bertitik diparse salah oleh frontend;
- perubahan tidak masuk audit trail;
- tidak ada optimistic locking;
- error backend ditutupi pesan generik;
- save menggunakan `QuerySet.update`, sehingga timestamp pekerjaan tidak berubah.

### 4.7 Search dan Filter

**Status:** Baik bersyarat.

- search kode/uraian;
- filter REF/MOD/CUS;
- count visible;
- reset filter;
- selected job tetap dapat berada di luar hasil filter tanpa penjelasan;
- jika semua checkbox dilepas, implementasi justru menampilkan semua source.

### 4.8 Grand Total

**Status:** Tidak sesuai konteks.

Toolbar menghitung:

```text
sum(unit_price_after_markup x volume) + PPN
```

Nilai ini adalah ringkasan Rekap RAB, bukan total Rincian AHSP per unit. Label tidak menyebut PPN, tidak memakai pembulatan project, dan tidak sama dengan export Rincian AHSP.

### 4.9 Warning Volume/Source

**Status:** Tidak presisi.

State `volume` dan `reload/ahsp` digabung menjadi satu `pendingVolumeJobs`. Pesan selalu menyatakan Volume/Tahapan di-reset dan harus diperbarui sebelum export.

Padahal:

- perubahan template belum tentu mereset volume;
- export Rincian AHSP tidak memakai volume;
- masalah expansion seharusnya mengunci/menandai detail, bukan selalu mengarahkan ke Volume.

### 4.10 Export

**Status:** Tidak konsisten.

- adapter membangun ulang perhitungan dari `DetailAHSPProject`;
- web detail menggunakan payload API;
- sidebar/grand total menggunakan `compute_rekap_for_project`;
- adapter menggunakan satuan `pek.satuan`, padahal field model adalah `snapshot_satuan`;
- harga dan total export dibulatkan nol desimal;
- export tidak membawa status readiness atau warning;
- export tidak menyertakan PPN/volume tetapi web menampilkan Grand Total berbasis keduanya.

### 4.11 Responsive dan Accessibility

**Status:** Baik bersyarat.

Yang sudah baik:

- landmark, listbox, option, separator, table headers, modal title;
- keyboard search, pilihan pekerjaan, dan resizer;
- sticky header dan horizontal scroll;
- responsive layout menjadi vertikal di mobile;
- dark mode dan reduced motion.

Kekurangan:

- semua option memakai `tabindex=0`, bukan roving tabindex;
- arrow key mengubah selection secara global, bukan focus listbox;
- bundle row tidak keyboard-accessible;
- search tidak mempunyai accessible label;
- icon-only export/help bergantung pada `title`;
- source/satuan/override chips di list disembunyikan CSS;
- status loading memakai opacity/pointer-events tanpa `aria-busy`;
- fallback toast memakai inline style dan English `Close`;
- mobile mempertahankan `min-height: 1000px`.

## 5. Temuan Audit

### RA-01 - CRITICAL - Default Markup 0% dan 10% Dihitung Bersamaan

`compute_rekap_for_project()` memakai 0% jika row `ProjectPricing` belum ada. `api_get_rekap_rab()` lalu mengubah `markup_eff` menjadi 10%, tetapi tidak menghitung ulang `F`, `G`, dan `total` karena field tersebut sudah ada.

**Dampak:**

- sidebar/detail dapat menampilkan harga dengan 10%;
- Grand Total memakai total yang dihitung dengan 0%;
- API membawa kombinasi field yang saling bertentangan.

**Rekomendasi:** definisikan default di satu tempat dan selalu gunakan 10.00% atau default produk yang disepakati langsung dalam service.

### RA-02 - CRITICAL - Web dan Export Menggunakan Definisi Total Berbeda

Web Grand Total memakai volume dan PPN. Adapter export menjumlahkan `unit_price_after_markup` setiap pekerjaan tanpa volume dan PPN.

**Dampak:** dua output bernama total/grand total tidak dapat direkonsiliasi.

**Rekomendasi:** Rincian AHSP tidak menampilkan Grand Total RAB. Jika ringkasan tetap dibutuhkan, beri nama `Total Nilai Project (lihat Rekap RAB)` dan gunakan service yang sama dengan Rekap RAB.

### RA-03 - HIGH - Export Menduplikasi Calculation Logic

`RincianAHSPAdapter` menghitung kelompok, bundle, markup, dan total secara independen dari service/API web.

**Dampak:** perubahan formula dapat memperbaiki web tetapi meninggalkan export stale.

**Rekomendasi:** buat satu builder kanonik untuk rincian per pekerjaan dan gunakan pada web serta export.

### RA-04 - HIGH - Parsing Override dengan Titik Salah

`parsePctUI()` menghapus semua titik. Nilai:

- `12.5` menjadi `125`;
- `1.5` menjadi `15`.

**Dampak:** input valid dapat ditolak atau disimpan sepuluh kali lebih besar.

**Rekomendasi:** gunakan numeric parser shared yang sama dengan Harga Items/backend.

### RA-05 - HIGH - Kontrol Save, Dirty, dan Reset Tidak Berfungsi

Template menampilkan:

- tombol Simpan;
- spinner Save;
- indikator Belum disimpan;
- tombol Reset;
- endpoint reset.

JavaScript tidak mengikat kontrol tersebut.

**Dampak:** user dapat menunggu aksi yang tidak pernah tersedia dan salah memahami model penyimpanan override.

**Rekomendasi:** hapus seluruh kontrol dead. Override tetap memakai aksi eksplisit pada modal.

### RA-06 - HIGH - Export Satuan Pekerjaan Salah

Adapter membaca `pek.satuan`, sedangkan model menyimpan `snapshot_satuan`.

**Dampak:** satuan pekerjaan pada export dapat selalu `-`.

### RA-07 - HIGH - Override Tidak Tercatat pada Audit Trail

Keputusan produk sebelumnya mewajibkan perubahan markup mencatat nilai lama, baru, pekerjaan, user, dan timestamp. Endpoint hanya melakukan update field dan invalidasi cache.

**Rekomendasi:** tambah audit action pricing/markup atau audit event generik yang tidak mencampur snapshot komponen.

### RA-08 - HIGH - Readiness Expanded Storage Tidak Ditampilkan

Page belum menampilkan:

- `expanded_ready`;
- stale revision;
- rebuild pending/failed;
- expected versus actual components;
- sumber row/table yang gagal.

**Dampak:** perhitungan parsial dapat terlihat sebagai hasil valid.

### RA-09 - MEDIUM - REF Fallback Tidak Mempunyai Harga

Fallback `RincianReferensi` mengirim koefisien dan metadata, tetapi tidak menghubungkan `HargaItemProject`.

**Dampak:** REF tanpa cloned detail tampil nol dan tidak memengaruhi rekap.

### RA-10 - MEDIUM - Error Backend Override Tidak Disampaikan

`saveOverride()` selalu melempar `save override fail`, sehingga error field/range server tidak pernah diteruskan ke user.

### RA-11 - MEDIUM - Override Tidak Mempunyai Concurrency Guard

Dua tab dapat menyimpan override terakhir tanpa deteksi conflict.

### RA-12 - MEDIUM - Warning Source dan Volume Digabung

Reload template, source change, dan volume reset ditampilkan sebagai masalah Volume/Tahapan yang sama.

**Rekomendasi:** pisahkan state:

- detail stale/rebuild;
- volume missing/reset;
- schedule assignment reset.

### RA-13 - MEDIUM - Bundle Expansion Tidak Accessible

Row clickable tidak mempunyai button, tabindex, expanded state, atau keyboard handler.

**Rekomendasi:** sediakan tombol expand pada cell dengan `aria-expanded` dan `aria-controls`.

### RA-14 - MEDIUM - Override Indicator Disembunyikan CSS

JavaScript membuat chip override pada list, tetapi CSS menyembunyikan seluruh `.rk-chip` dalam metadata. Help modal menyatakan pekerjaan override ditandai chip kuning, tetapi indikator tidak terlihat.

### RA-15 - MEDIUM - Export Error Mengekspos Detail Exception

Endpoint export menangkap exception, mencetak traceback, dan mengembalikan `str(e)`.

**Rekomendasi:** log server-side dengan correlation ID dan kirim pesan generik.

### RA-16 - MEDIUM - Tidak Ada Rate/Payload Governance pada Pricing dan Bundle API

Endpoint ringan tetapi dapat dipanggil berulang. Bundle expansion besar juga tidak mempunyai component limit/pagination pada response.

### RA-17 - LOW - Empty State Detail Tidak Informatif

Empat section dan subtotal nol tetap dirender ketika pekerjaan tidak mempunyai item. Tidak ada CTA ke Template AHSP atau diagnostic readiness.

### RA-18 - LOW - Terminologi dan Bahasa Tidak Konsisten

Contoh:

- `Override Settings`;
- `Close`;
- `HSP` dipakai untuk harga setelah markup;
- `Grand Total` tanpa menyebut PPN;
- text literal `TABEL AHSP` muncul di layout.

### RA-19 - LOW - CSS/JS Mempunyai Drift dan Dead Code

Contoh:

- selector duplikat;
- referensi elemen inline override yang tidak ada;
- export loading modal yang tidak ada;
- pencarian ID tombol CSV lama;
- hardcoded bundle URL;
- manipulasi global semua modal backdrop;
- komentar test yang tidak sesuai repository.

### RA-20 - LOW - Mobile Layout Memaksakan Tinggi Minimum Besar

`min-height: 1000px` tetap aktif ketika layout berubah menjadi kolom. Sidebar dan editor dapat menghasilkan scroll page panjang dan ruang kosong.

## 6. Implementasi UI/UX yang Sudah Baik

1. Pekerjaan dikelompokkan dalam sidebar yang dapat dicari dan difilter.
2. REF, MOD, dan CUS dibedakan secara visual.
3. Pekerjaan terakhir dipulihkan.
4. Selection race dilindungi token.
5. Detail dikelompokkan per kategori dan mempunyai subtotal.
6. Effective markup dan override aktif terlihat pada header pekerjaan.
7. Modal override menjelaskan pekerjaan target.
8. Bundle dapat diperiksa tanpa berpindah page.
9. Resizer mendukung mouse dan keyboard.
10. Help modal menjelaskan shortcut dan workflow.
11. Dark mode, forced colors, dan reduced motion tersedia.
12. Source-change event dapat membersihkan detail cache.

## 7. Prioritas Remediasi

| Urutan | Item | Gate |
|---|---|---|
| P0 | RA-01 satukan default markup | Wajib sebelum production |
| P0 | RA-02 definisikan scope total Rincian AHSP | Wajib untuk konsistensi laporan |
| P0 | RA-03 shared calculation builder web/export | Wajib untuk SSOT |
| P0 | RA-04 perbaiki parser override | Wajib untuk data integrity |
| P1 | RA-05 hapus kontrol dead | Kejelasan workflow |
| P1 | RA-06 perbaiki satuan export | Keakuratan dokumen |
| P1 | RA-07 audit trail override | Governance |
| P1 | RA-08 readiness diagnostics | Reliability |
| P1 | RA-09 REF fallback pricing | Data completeness |
| P1 | RA-10 sampai RA-16 | UX, concurrency, security |
| P2 | RA-17 sampai RA-20 | Polish dan maintainability |

## 8. Keputusan Produk yang Perlu Dikonfirmasi

### D-RA-01 - Scope Grand Total

Rekomendasi: hapus Grand Total dari toolbar Rincian AHSP karena nilai tersebut merupakan domain Rekap RAB. Sidebar cukup menampilkan harga satuan final tiap pekerjaan.

Alternatif: pertahankan sebagai link/ringkasan `Total Nilai Project termasuk PPN`, tetapi harus identik dengan Rekap RAB termasuk pembulatan.

### D-RA-02 - Model Penyimpanan

Rekomendasi: tetapkan page sebagai viewer dengan satu aksi mutasi, yaitu override markup. Tombol Save, dirty indicator, reset detail, dan endpoint reset tidak ditampilkan pada page ini.

### D-RA-03 - Tampilan Bundle

Rekomendasi:

- breakdown menampilkan nilai per satu unit bundle;
- header menyebut quantity bundle pada pekerjaan induk;
- tampilkan total per unit dan total setelah quantity secara terpisah;
- nested depth/source chain ditampilkan untuk diagnosis.

### D-RA-04 - Warning Readiness

Rekomendasi: perhitungan tetap dapat dibuka untuk diagnosis, tetapi diberi label `Data belum lengkap` dan export membawa catatan warning. Jangan tampilkan angka parsial sebagai hasil final.

### D-RA-05 - Presisi

Harga dasar dan harga satuan final tetap dihitung dua desimal. Export dapat memformat rupiah penuh untuk presentasi hanya jika nilai kanonik dua desimal tetap tersedia dan kebijakan pembulatan dinyatakan.

## 9. Browser UAT Matrix

| Area | Skenario |
|---|---|
| Initial | project kosong, first selection, last selection, API gagal |
| Mode | REF, MOD, CUS direct, CUS bundle, nested bundle |
| Calculation | harga desimal, koefisien desimal, markup default, override 0/10/12.5/100 |
| Default | project tanpa `ProjectPricing` |
| Override | koma, titik, clear, failure, dua tab |
| Bundle | mouse, keyboard, empty, stale, nested depth |
| Readiness | pending, stale, partial, failed expansion |
| Sync | perubahan Template, Harga, source, volume |
| Export | XLSX/PDF/Word dan rekonsiliasi dengan layar |
| Accessibility | listbox, focus order, modal, bundle expand, screen reader |
| Responsive | 320, 360, 576, 768, 1024, desktop, zoom 200% |
| Theme | light, dark, reduced motion, forced colors |

## 10. Verifikasi Teknis

Hasil pemeriksaan:

- `python manage.py check`: **lulus**;
- `node --check rincian_ahsp.js`: **lulus**;
- Vitest: **235 lulus, 25 skipped**;
- 25 test backend gabungan: **22 lulus, 3 gagal**.

Tiga kegagalan berada pada `tests_export_button_visibility` karena fixture mendapatkan redirect HTTP 302 ketika mengharapkan page 200. Suite tersebut menguji page lain dan bukan calculation Rincian AHSP, tetapi tetap menjadi gap environment/test yang perlu diperiksa.

Test yang belum tersedia:

- default markup tanpa row pricing;
- parser override titik/koma;
- override audit/concurrency;
- bundle expansion UI aktual;
- rekonsiliasi web dan export;
- REF fallback tanpa cloned detail;
- readiness warning;
- accessibility keyboard bundle.

Audit visual browser dan screen reader belum dijalankan.

## 11. Keputusan Audit

Rincian AHSP memiliki struktur viewer yang baik dan pemisahan markup default/override sudah sesuai kebutuhan bisnis. Lazy loading, selection race protection, grouping kategori, dan bundle inspection merupakan fondasi yang berguna.

Page belum dapat dianggap final karena calculation dapat membawa markup 0% dan label 10% sekaligus, web/export mendefinisikan total secara berbeda, adapter export menduplikasi formula, dan parser override dapat menyimpan nilai yang salah.

Perbaikan tidak membutuhkan restrukturisasi database besar. Fokusnya adalah:

1. satu builder perhitungan kanonik;
2. penegasan scope viewer;
3. penghapusan kontrol dead;
4. auditability override;
5. readiness diagnostic;
6. rekonsiliasi penuh web, export, dan Rekap RAB.

---

## 12. Verifikasi Independen (Claude, 13 Juni 2026)

Temuan diperiksa ulang terhadap kode kerja. Yang diverifikasi langsung: **RA-01, RA-02, RA-03, RA-04, RA-06 — semuanya valid, tidak ada false positive.** Sisanya (RA-05/07..RA-20) konsisten dengan kode/struktur (dead control, audit, a11y, dead code; perlu UAT browser untuk konfirmasi visual). Keputusan produk D-RA-01..05 adalah usulan yang menunggu konfirmasi owner — tidak saya nilai ulang.

### 12.1 Verdict per temuan (yang diverifikasi langsung)

| Temuan | Verdict | Bukti verifikasi |
|---|---|---|
| RA-01 Default markup 0% vs 10% bersamaan | **DIKONFIRMASI (root + tiga arah)** | `services.py:2293` `proj_markup = Decimal("0")` (komentar "fallback 10.00" menyesatkan — kode tetap 0 bila tak ada `ProjectPricing`); `api_get_rekap_rab:4594` menyuntik `markup_eff=10` tetapi `:4614-4620` mempertahankan F/G/total lama (dihitung 0%). Lihat 12.2 soal divergensi tiga arah. |
| RA-02 Web vs export beda definisi total | **DIKONFIRMASI** | Adapter `rincian_ahsp_adapter.py:174` `G_hsp = E_total + F_margin` (per unit), `:210` `grand_total += G_hsp` — tanpa volume, tanpa PPN. Web Grand Total = `Σ(G×volume)+PPN`. |
| RA-03 Export duplikasi calculation | **DIKONFIRMASI** | Adapter menghitung sendiri `E_total/F_margin/G_hsp/eff_markup` (`:170-174`), tidak memakai `compute_rekap_for_project`. |
| RA-04 Parser override salah pada titik | **DIKONFIRMASI** | `rincian_ahsp.js:282` `s.replace(/\./g,'').replace(',','.')` → `"12.5"` menjadi `125`. Docstring sendiri (`:273-274`) menunjukkan asumsi format id-ID (titik = ribuan). |
| RA-06 Satuan pekerjaan export salah | **DIKONFIRMASI** | `rincian_ahsp_adapter.py:110` `getattr(pek, 'satuan', '-')` — model memakai `snapshot_satuan` (lih. `:109` yang benar pakai `snapshot_kode`), jadi satuan selalu jatuh ke default `'-'` tanpa error. |

### 12.2 Penajaman bukti

- **RA-01 sebenarnya divergensi TIGA arah, bukan dua.** Untuk project tanpa row `ProjectPricing`:
  1. `compute_rekap_for_project` memakai markup **0%** (`services.py:2293`) → F/G/total = 0% markup.
  2. `api_get_rekap_rab` menampilkan `markup_eff = 10%` (`:4594`) tetapi tidak menghitung ulang F/G/total → **label 10%, angka 0%**.
  3. `RincianAHSPAdapter` (export) memakai default **10%** sendiri (`:95-98`) dan menghitung G dengan 10% → **angka 10%**.
  Jadi web-detail, web-grand-total, dan export bisa menampilkan tiga hasil berbeda untuk project yang sama. Perbaikan paling kokoh: **satu sumber default markup** (di service), dan service ini yang dipakai web + export (sejalan RA-03).

- **RA-04 — fix harus pakai parser numeric shared.** Saat ini Rincian AHSP punya parser sendiri yang berbeda dari Harga Items/Volume; "12.5%" (cara umum user mengetik persen) tersimpan jadi 125 (>100 → ditolak) atau 10× lipat. Pakai parser kanonik yang sama dengan page lain.

- **RA-06 berbahaya karena senyap.** `getattr(..., '-')` tidak melempar error — satuan pekerjaan di seluruh dokumen export hanya menampilkan `-`, dan tidak ada sinyal bahwa ada bug. Ini lolos `node --check`/test karena tidak ada test rekonsiliasi export (lihat §10 dokumen).

### 12.3 Catatan konsistensi lintas-page (page ke-6)

Rincian AHSP mengonfirmasi ulang pola yang sama di lima page sebelumnya:
- **Export adapter menghitung ulang sendiri** alih-alih memakai service kanonik (RA-03) — persis HI-03 di Harga Items. Akar masalah yang sama: tidak ada satu calculation builder bersama web+export.
- **Bocoran `str(e)`** pada error export (RA-15) — sama TA-08, sistemik.
- **Mutasi tanpa audit trail** (RA-07 override) — sama TA-04 (reset Template AHSP). Bahkan keputusan owner D-02 (Template AHSP) sudah mewajibkan audit markup; di sini belum ada.
- **Tanpa concurrency guard** (RA-11) — sama TA-02/HI-09/VP-06.
- **Readiness `expanded_ready` tak ditampilkan** (RA-08) — implementasi dari keputusan owner D-06 (Template AHSP) belum menjangkau consumer ini.

Catatan: RA-07 (audit override) dan RA-08 (readiness) bukan temuan baru secara kebijakan — keduanya adalah **konsumen yang belum mengikuti keputusan owner yang sudah final** (D-02 audit markup, D-06 readiness contract). Saat fase perbaikan, pastikan implementasi D-02/D-06 mencakup page Rincian AHSP, bukan hanya Template AHSP.

### 12.4 Kalibrasi prioritas

Urutan P0 (RA-01..RA-04) sudah tepat. Catatan:
- **RA-04 dan RA-06 quick win** (RA-04: ganti ke parser shared; RA-06: `snapshot_satuan`) — effort sangat rendah, RA-06 cukup satu kata.
- **RA-01, RA-02, RA-03 sebaiknya satu paket**: buat satu calculation builder kanonik (default markup tunggal di service) yang dipakai `api_get_rekap_rab`, web, dan adapter export — menutup RA-01/02/03/06 sekaligus. Ini juga prasyarat keputusan D-RA-01 (scope Grand Total).
- **RA-05 (kontrol Save/Reset mati)** murah dan mengurangi kebingungan — bagus dikerjakan bareng D-RA-02.
