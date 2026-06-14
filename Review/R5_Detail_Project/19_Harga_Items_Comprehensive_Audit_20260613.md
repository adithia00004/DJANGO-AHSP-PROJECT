# Audit Komprehensif Page Harga Items

**Tanggal audit:** 13 Juni 2026  
**Target:** `/detail_project/<project_id>/harga-items/`  
**Objek:** current working tree pada saat audit  
**Status:** **BELUM PRODUCTION-READY - terdapat temuan Critical pada status harga kosong dan konsistensi konversi**

## 1. Ringkasan Eksekutif

Page Harga Items menangani:

- harga satuan dasar item TK, BHN, ALT, dan LAIN;
- Profit/Margin default project;
- pencarian dan filter kategori/harga belum diisi;
- input angka lokal Indonesia;
- bulk paste;
- helper konversi satuan pembelian ke satuan dasar AHSP;
- sinkronisasi setelah perubahan Template AHSP;
- export XLSX, PDF, Word, dan JSON;
- propagasi harga ke Rincian AHSP, Rekap Kebutuhan, Rekap RAB, dan Jadwal.

Fondasi yang sudah baik:

- page dan API dibatasi ke owner project;
- initial list memakai SSR bootstrap sehingga tidak memerlukan fetch kedua;
- input user dirender dengan escaping;
- harga utama tersimpan pada `HargaItemProject.harga_satuan`;
- satuan dasar Template AHSP tidak diubah oleh fitur konversi;
- dirty state, before-unload, save spinner, partial-save handling, dan sync lock tersedia;
- dark mode, reduced motion, forced colors, sticky toolbar/header, filter, dan format angka lokal tersedia;
- export dan calculation menggunakan item yang benar-benar dipakai melalui `used_harga_items_queryset`.

Namun terdapat dua pelanggaran kontrak data utama:

1. Save mengubah seluruh harga `null` menjadi `0.00`, walaupun user hanya mengedit satu harga atau Profit/Margin. Status **belum diisi** hilang dan tidak lagi dapat dibedakan dari nol eksplisit.
2. Profil konversi dan harga dasar disimpan terpisah. Calculation memakai `harga_satuan`, sedangkan sebagian export dan mode market menghitung ulang dari `market_price / factor_to_base`. Satu item dapat menghasilkan harga berbeda antar-page.

## 2. Kontrak SSOT yang Direkomendasikan

Kontrak berikut konsisten dengan keputusan audit Template AHSP:

| Data | SSOT | Aturan |
|---|---|---|
| Kode, kategori, uraian, satuan dasar | `HargaItemProject` | Tidak boleh diubah oleh conversion profile |
| Harga dasar untuk perhitungan AHSP | `HargaItemProject.harga_satuan` | Satu-satunya harga yang dipakai Rincian AHSP dan Rekap RAB |
| Satuan/harga pembelian supplier | `ItemConversionProfile` | Metadata/helper pembelian |
| Faktor konversi | `ItemConversionProfile.factor_to_base` | `1 market unit = X base unit` |
| Hasil konversi | `market_price / factor_to_base` | Harus atomik tersinkron ke `harga_satuan` |
| Harga belum diisi | `harga_satuan IS NULL` | Berbeda dari harga eksplisit `0.00` |
| Profit/Margin project | `ProjectPricing.markup_percent` | Dipakai untuk harga setelah markup |

Prinsip penting:

- conversion profile tidak menjadi sumber harga kedua;
- export satuan dasar harus membaca `harga_satuan`;
- penyimpanan konversi harus memperbarui profile dan `harga_satuan` dalam satu transaksi;
- jika profile dan harga dasar tidak konsisten, tampilkan diagnostic dan jangan diam-diam memilih salah satunya.

## 3. Ruang Lingkup dan Komponen

| Area | Implementasi |
|---|---|
| Page view | `detail_project.views.harga_items_view` |
| List/bootstrap | `build_harga_items_payload`, `api_list_harga_items` |
| Save harga | `api_save_harga_items` |
| Conversion profile | `api_get_conversion_profiles`, `api_save_conversion_profile` |
| Model | `HargaItemProject`, `ItemConversionProfile`, `ProjectPricing` |
| Active/used contract | `active_harga_items_queryset`, `used_harga_items_queryset` |
| Template | `detail_project/templates/detail_project/harga_items.html` |
| JavaScript | `detail_project/static/detail_project/js/harga_items.js` |
| CSS | `detail_project/static/detail_project/css/harga_items.css` |
| Export | `HargaItemsAdapter`, JSON export, `ExportManager` |
| Consumer | Rincian AHSP, Rekap Kebutuhan, Rekap RAB, Jadwal |

Ukuran implementasi utama:

- `harga_items.js`: sekitar 1.241 baris;
- `harga_items.html`: sekitar 350 baris;
- `harga_items.css`: sekitar 808 baris.

## 4. Audit Per Mode dan Elemen Interaktif

### 4.1 Initial Load

**Status:** Baik bersyarat.

- daftar item dan markup di-bootstrap dalam HTML;
- fallback fetch tersedia;
- loading, error, dan empty row tersedia;
- item standalone saat ini ikut ditampilkan untuk mendukung import, tetapi perilaku ini tidak lagi sesuai keputusan produk;
- conversion profile server tidak disertakan dalam bootstrap dan tidak di-fetch page ini.

### 4.2 Harga Manual

**Status:** Fungsional bersyarat.

- menerima titik/koma dan grouping Indonesia;
- live preview Rupiah tersedia;
- negatif dan nilai di atas batas frontend ditandai invalid;
- blur menormalisasi input;
- save mengirim seluruh baris, bukan hanya baris berubah;
- backend belum menegakkan aturan negatif/range yang sama.

### 4.3 Harga Belum Diisi dan Nol

**Status:** Tidak aman.

UI awal membedakan `null` sebagai `hi-row-empty`, tetapi menampilkan nilai input `0.00`. Saat save, seluruh baris dikirim dan nilai kosong dinormalisasi menjadi `0.00`.

Akibatnya:

- null berubah menjadi nol tanpa tindakan eksplisit user;
- filter Belum Diisi menjadi kosong setelah save;
- completeness warning lintas-page kehilangan sumber datanya;
- perubahan markup saja dapat menandai seluruh harga sebagai sudah diisi.

### 4.4 Konversi Harga Supplier

**Status:** Tidak konsisten.

Formula UI benar:

```text
harga dasar = harga supplier / faktor ke satuan dasar
```

Contoh:

```text
Rp60.000 / zak
1 zak = 40 kg
harga dasar = Rp1.500 / kg
```

Masalahnya, tombol Terapkan:

1. mengubah input harga dasar hanya di browser;
2. menyimpan conversion profile melalui request terpisah;
3. membutuhkan tombol Simpan page untuk menyimpan harga dasar.

Jika user menutup page setelah Terapkan, profile dapat tersimpan sedangkan `harga_satuan` tetap lama.

### 4.5 Bulk Paste

**Status:** Berisiko.

- listener dipasang pada seluruh `document`;
- multiline paste di area mana pun dapat diproses sebagai tabel harga;
- format menganggap kolom Harga sebagai harga utama sekaligus `price_market`;
- jika factor tersedia, harga utama tidak dibagi factor;
- profile hanya masuk memory/localStorage dan tidak mengikuti satu transaksi save yang jelas.

### 4.6 Profit/Margin

**Status:** Fungsional.

- validasi backend 0-100 tersedia;
- perubahan menginvalidasi cache dan menandai change status;
- help text menyatakan dipakai Rekap AHSP;
- dampak ke Harga Satuan Setelah Markup dan Rekap RAB perlu dibuat lebih eksplisit.

### 4.7 Search dan Filter

**Status:** Baik bersyarat.

- search mencakup kode, uraian, dan kategori;
- filter Semua/TK/BHN/ALT/LAIN/Belum Diisi dapat digabung dengan search;
- count tersedia;
- state aktif hanya visual dan belum memakai `aria-pressed`;
- status jumlah hasil dinamis belum diumumkan melalui live region.

### 4.8 Sync Lock

**Status:** Baik untuk pointer, bersyarat untuk keyboard.

- banner dan overlay menjelaskan alasan lock;
- harga, markup, dan Save dinonaktifkan;
- link Buka Template tersedia;
- conversion button dan elemen lain di belakang overlay tidak dibuat `inert` atau dikeluarkan dari tab order;
- race pada `finally` save dapat mengaktifkan kembali tombol tanpa mempertimbangkan lock terbaru.

### 4.9 Export

**Status:** Tidak konsisten.

- export hanya memakai item yang benar-benar memengaruhi calculation;
- page saat ini dapat menampilkan item standalone yang tidak ikut export;
- XLSX/PDF/Word adapter menghitung ulang harga dasar dari conversion profile;
- JSON mengekspor `harga_satuan` dan profile secara terpisah;
- calculation utama tetap membaca `harga_satuan`.

### 4.10 Responsive, Theme, dan Accessibility

**Status:** Baik bersyarat.

Yang sudah baik:

- sticky toolbar/header;
- horizontal table scrolling;
- toolbar responsive;
- dark mode;
- reduced motion dan forced colors;
- input harga mempunyai accessible name;
- modal mempunyai title dan tombol tutup berlabel.

Kekurangan:

- mobile tetap berupa tabel lebar tanpa card/priority columns;
- label field modal tidak terhubung dengan `for`;
- conversion icon button mengandalkan `title`, tanpa `aria-label`;
- filter tidak mengumumkan pressed state;
- lock overlay bukan modal/focus trap;
- status edited/empty/invalid hanya dibedakan warna/border;
- belum ada instruksi keyboard atau feedback khusus untuk bulk paste.

## 5. Temuan Audit

### HI-01 - CRITICAL - Save Mengubah Semua Harga Null Menjadi Nol

`renderTable()` menampilkan null sebagai `0.00`. Save mengumpulkan seluruh `viewRows` dan mengirim `0.00`, termasuk baris yang tidak diedit.

**Dampak:** status belum diisi hilang, completeness report salah, dan perubahan markup saja memodifikasi semua item null.

**Rekomendasi:**

1. Simpan hanya baris dirty.
2. Pertahankan `null` sebagai null sampai user benar-benar mengisi.
3. Sediakan aksi eksplisit `Setel ke 0`.
4. Tambahkan test: edit satu item tidak mengubah null item lain.

### HI-02 - CRITICAL - Conversion Profile dan Harga Dasar Bukan Satu Transaksi

Profile disimpan segera dari modal, sedangkan harga dasar baru disimpan melalui tombol page.

**Dampak:** profile dan `harga_satuan` dapat berbeda setelah navigasi, kegagalan jaringan, atau user lupa menekan Simpan.

**Rekomendasi:** buat endpoint atomik `apply conversion` yang memvalidasi profile, menghitung harga dasar server-side, lalu menyimpan keduanya dalam satu transaction.

### HI-03 - CRITICAL - Export Dapat Memakai Harga Berbeda dari Calculation

`HargaItemsAdapter` memilih `market_price / factor_to_base` jika profile ada. Rincian AHSP dan Rekap RAB membaca `HargaItemProject.harga_satuan`.

**Dampak:** dokumen Harga Items dapat tidak cocok dengan RAB dan nilai pada database.

**Rekomendasi:** export satuan dasar selalu memakai `harga_satuan`; tampilkan hasil profile sebagai rekonsiliasi dan warning bila tidak sama.

### HI-04 - HIGH - Profile Database Tidak Dimuat Kembali di Editor

JavaScript mengharapkan `it.conv`, tetapi `build_harga_items_payload()` tidak mengirim field tersebut. Page juga tidak memanggil endpoint GET conversion profile.

**Dampak:** browser/perangkat baru membuka modal kosong walaupun profile ada di database.

**Rekomendasi:** sertakan profile dalam bootstrap dengan `select_related`, atau fetch endpoint profile sekali saat initial load.

### HI-05 - HIGH - Validation Conversion API Tidak Cukup

Endpoint:

- menerima market price negatif;
- menerima density/capacity negatif;
- menerima method di luar choices;
- mengubah decimal invalid menjadi default 0/1;
- tidak menjalankan `full_clean`;
- tidak menangani overflow DecimalField sebagai response 400;
- dapat error jika `market_unit` bukan string.

**Rekomendasi:** strict schema validation, whitelist method, range check, max length/digits, model/DB constraints, dan generic 400.

### HI-06 - HIGH - Backend Harga Tidak Menolak Nilai Negatif

`api_save_harga_items()` memparse dan quantize harga, tetapi tidak mengecek `dec < 0`. Validator model tidak otomatis berjalan saat `save()`.

**Dampak:** request API langsung dapat menyimpan harga negatif.

**Rekomendasi:** validasi backend `0 <= harga <= batas domain` dan tambahkan database `CheckConstraint`.

### HI-07 - HIGH - Bulk Paste Mencampur Harga Dasar dan Harga Market

Nilai Harga dipasang langsung ke input harga dasar dan sekaligus disimpan sebagai `price_market`. Factor tidak diterapkan ke harga utama.

**Dampak:** contoh Rp60.000/zak dengan factor 40 dapat tersimpan sebagai Rp60.000/kg, bukan Rp1.500/kg.

**Rekomendasi:** pisahkan format paste base-price dan market-conversion; tampilkan preview serta konfirmasi sebelum apply.

### HI-08 - MEDIUM - LocalStorage Tidak Project-Scoped

Key memakai `hiConv:<kode>`, tanpa project ID.

**Dampak:** kode item sama pada dua project dapat memakai profile browser dari project lain.

**Rekomendasi:** gunakan `hiConv:<project_id>:<kode>` dan prioritaskan server sebagai source profile.

### HI-09 - MEDIUM - Last-Save-Wins Tetap Berisiko pada Multi-Tab

Frontend sengaja tidak mengirim `client_updated_at`. Satu akun tetap dapat membuka dua tab/perangkat.

**Dampak:** save tab lama dapat menimpa harga tab baru tanpa warning.

**Rekomendasi:** aktifkan optimistic token; konflik hanya memerlukan reload/timpa eksplisit.

### HI-10 - MEDIUM - Save Seluruh Tabel Membebani Request dan Memperbesar Blast Radius

Setiap save mengirim semua item dan melakukan loop query/update. Tidak terlihat payload count limit atau rate limit pada endpoint ini.

**Rekomendasi:** kirim changed rows, batasi jumlah item/body, deduplicate ID, dan gunakan bulk update terkontrol.

### HI-11 - MEDIUM - Kegagalan Save Profile Tidak Terlihat User

Response profile gagal dan network error hanya ditulis ke console. Modal sudah tertutup dan harga browser sudah berubah.

**Rekomendasi:** tunggu response sebelum menutup modal; tampilkan error actionable dan pertahankan modal/input.

### HI-12 - MEDIUM - Active Page dan Export Memakai Scope Berbeda

Page menampilkan standalone/orphan-import item, sedangkan export hanya `used_harga_items_queryset`.

**Dampak:** jumlah dan isi export tidak sama dengan tabel tanpa penjelasan.

**Keputusan final:** Harga Items hanya boleh menampilkan item yang benar-benar dipakai oleh expanded detail atau raw fallback. Item standalone/orphan tidak mempunyai tempat dalam workflow user, tidak diberi badge, dan tidak dipindahkan ke page Orphan Cleanup.

**Rekomendasi implementasi:**

1. Gunakan `used_harga_items_queryset()` sebagai kontrak bersama page, save allow-list, calculation, dan export.
2. Hapus cabang standalone `Q(used_in_expanded=False, used_in_raw=False)` dari kontrak Harga Items.
3. Import tidak boleh membuat item harga bebas yang langsung tampil; item baru harus terhubung ke Template AHSP atau masuk proses staging/validation internal.
4. Bersihkan item tanpa referensi secara otomatis setelah transaction yang dapat membuat orphan berhasil commit.
5. Jika expansion pending/gagal, pertahankan diagnostic state terlebih dahulu agar item yang masih dibutuhkan tidak salah dibersihkan.

### HI-13 - MEDIUM - Lock Overlay Tidak Mengunci Interaksi Keyboard Secara Penuh

Overlay tidak memakai `inert`, dialog semantics, atau focus management. Conversion button di belakangnya tetap focusable.

**Rekomendasi:** set container `inert`, pindahkan focus ke lock card, dan pulihkan focus setelah unlock.

### HI-14 - LOW - Dirty State Tidak Dihitung Ulang Secara Menyeluruh

Setelah user mengubah lalu mengembalikan semua nilai ke baseline, global dirty dapat tetap aktif.

**Rekomendasi:** derive dirty dari seluruh row dirty + markup dirty, bukan latch satu arah.

### HI-15 - LOW - Aksesibilitas Modal dan Filter Belum Lengkap

Label modal tidak memakai `for`, icon conversion tidak mempunyai `aria-label`, filter tidak memakai `aria-pressed`, dan state row bergantung pada warna.

### HI-16 - LOW - Implementasi Memuat Dead/Drifted Code

Terdapat:

- `rememberServer` hidden yang tidak tersinkron;
- `payload.conversions` yang tidak diproses endpoint save;
- referensi tombol CSV yang tidak ada;
- URL save conversion hardcoded;
- hidden advanced fields dan wrapper JavaScript yang tidak lagi ada di template.

**Rekomendasi:** hapus jalur mati dan kirim semua endpoint melalui dataset hasil Django `url`.

## 6. Prioritas Remediasi

| Urutan | Item | Gate |
|---|---|---|
| P0 | HI-01 pertahankan null vs nol | Wajib sebelum production |
| P0 | HI-02 save conversion atomik | Wajib untuk SSOT |
| P0 | HI-03 samakan export dengan calculation | Wajib untuk keandalan laporan |
| P0 | HI-05 dan HI-06 backend validation | Wajib untuk data integrity |
| P1 | HI-04 load profile server | Konsistensi lintas perangkat |
| P1 | HI-07 redesign bulk paste | Mencegah salah harga besar |
| P1 | HI-08 project-scoped storage | Isolasi project |
| P1 | HI-09 optimistic locking | Multi-tab safety |
| P1 | HI-10 payload/rate limit | Reliability/performance |
| P1 | HI-11 visible profile failure | UX reliability |
| P1 | HI-12 samakan page/save/export ke used-item contract | SSOT dan penghapusan workflow orphan |
| P2 | HI-13 sampai HI-16 | UX, a11y, maintainability |

## 7. Rekomendasi Alur Konversi Final

1. User membuka Konversi.
2. Page memuat profile dari server.
3. User mengisi market unit, market price, dan factor.
4. Browser menampilkan preview harga dasar.
5. User menekan `Terapkan dan Simpan`.
6. Server memvalidasi profile dan base unit.
7. Server menghitung harga dasar dengan Decimal dan aturan rounding resmi.
8. Server menyimpan profile + `harga_satuan` secara atomik.
9. Server menjalankan `touch_project_change(harga=True)` dan cache invalidation.
10. Response mengembalikan profile serta harga dasar kanonik.
11. UI memperbarui row, dirty state, dan diagnostic.

Tidak diperlukan perubahan satuan atau koefisien Template AHSP.

## 8. Browser UAT Matrix

| Area | Skenario |
|---|---|
| Initial | SSR list, empty, error, retry, profile existing dari perangkat lain |
| Manual | titik, koma, grouping, negatif, max, kosong, nol eksplisit |
| Null safety | edit satu item, markup-only save, null item lain tetap null |
| Conversion | zak/kg, ton/kg, m3/kg, custom unit, rounding |
| Failure | profile save gagal, harga save gagal, offline, retry |
| Bulk paste | base-price, conversion, duplicate kode, invalid row, paste di search/modal |
| Sync | pending Template, keyboard lock, dirty refresh |
| Scope | hanya used item, raw fallback, nested expansion, dan kesamaan jumlah export |
| Cross-page | Harga Items ke Rincian AHSP, Kebutuhan base/market, Rekap RAB |
| Conflict | dua tab pada akun sama |
| Accessibility | keyboard-only, focus modal/lock, screen reader, zoom 200% |
| Responsive | 320, 360, 576, 768, 1024, desktop |
| Theme | light, dark, reduced motion, forced colors |

## 9. Verifikasi Teknis

Hasil pemeriksaan:

- `python manage.py check`: **lulus**;
- `node --check detail_project/static/detail_project/js/harga_items.js`: **lulus**;
- 14 test backend terarah: **lulus**;
- Vitest: **235 lulus, 25 skipped**.

Catatan:

- test yang ada belum mencakup null-to-zero, atomic conversion save, profile reload pada editor, negative API price, cross-project localStorage, dan mismatch export/calculation;
- audit visual browser dan screen reader belum dijalankan.

## 10. Keputusan Audit

Arsitektur dasar page sudah sesuai: Template AHSP mempertahankan satuan/koefisien dasar dan Harga Items menyediakan harga ekuivalen per satuan dasar. Fitur conversion helper juga relevan untuk kondisi pembelian lapangan.

Page belum dapat dianggap final karena implementasi saat ini memungkinkan:

- input belum diisi berubah menjadi nol tanpa persetujuan;
- conversion profile dan harga dasar berbeda;
- export berbeda dari calculation;
- profile database tidak tampil kembali pada editor;
- API menyimpan nilai yang tidak lolos aturan frontend.

Perbaikan yang direkomendasikan bersifat terarah dan tidak memerlukan restrukturisasi besar client-side. Perubahan utama adalah memperjelas kontrak SSOT, menyatukan transaksi konversi, menyimpan hanya perubahan, dan menambahkan validation/diagnostic.

## 11. Keputusan Produk Final

### D-HI-01 - Null dan Nol

- `null` berarti harga belum diisi.
- `0.00` berarti user sengaja menetapkan harga nol.
- Save tidak boleh mengubah null menjadi nol secara implisit.

### D-HI-02 - Penyimpanan Konversi

Tombol konversi menggunakan aksi `Terapkan dan Simpan`. Conversion profile dan harga dasar hasil konversi disimpan dalam satu transaksi server.

### D-HI-03 - Override Manual Menghapus Konversi

Jika user mengubah manual harga yang sebelumnya berasal dari popup konversi:

- conversion profile item dihapus saat harga manual disimpan;
- data localStorage terkait juga dihapus;
- UI menjelaskan bahwa perubahan manual akan menghapus pengaturan konversi.

Dengan aturan ini, perbedaan harga dasar dan hasil profile bukan workflow normal. Mismatch hanya diperlakukan sebagai diagnostic untuk data lama, import, admin/API eksternal, atau kegagalan integritas.

### D-HI-04 - Scope Harga Items

Harga Items hanya menampilkan item aktif yang memengaruhi perhitungan project:

- komponen `DetailAHSPExpanded`;
- item raw fallback untuk pekerjaan yang expanded storage-nya belum tersedia.

Item standalone tanpa referensi tidak ditampilkan. Page, save allow-list, calculation, dan export menggunakan kontrak `used_harga_items_queryset()` yang sama.

### D-HI-05 - Page Orphan Cleanup Dipensiunkan

Page Orphan Cleanup tidak lagi relevan dalam workflow project dan harus dipensiunkan:

1. hapus link dari sidebar dan navigasi user;
2. jangan mengarahkan item sisa ke page tersebut;
3. lakukan orphan cleanup otomatis sebagai housekeeping backend setelah commit;
4. pertahankan service/management command internal sementara untuk migrasi, diagnosis, dan recovery;
5. jangan menghapus item ketika expansion berstatus pending, stale, parsial, atau gagal;
6. setelah telemetry dan migration memastikan tidak ada consumer, endpoint dan template orphan dapat dihapus bertahap.

### D-HI-06 - Markup

- Harga Items adalah tempat utama menentukan markup default project.
- Rincian AHSP hanya mengatur override markup per pekerjaan.
- Override satu pekerjaan tidak mengubah default project atau pekerjaan lain.

### D-HI-07 - Bulk Paste

Listener paste global dipensiunkan. Fitur diganti dengan aksi terlihat `Import/Paste Massal`, dengan mode terpisah:

- Harga Dasar;
- Harga Supplier + Konversi.

Keduanya wajib mempunyai preview dan validation sebelum diterapkan.

### D-HI-08 - Presisi

Harga item disimpan sebagai nilai kanonik dua angka desimal.

---

## 12. Verifikasi Independen (Claude, 13 Juni 2026)

Temuan diperiksa ulang terhadap kode kerja. Yang diverifikasi langsung: **HI-01..HI-06, HI-09, HI-10, HI-12, HI-16 — semuanya valid, tidak ada false positive.** Sisanya (HI-07/08/11/13/14/15) konsisten dengan kode (UI/a11y/storage; perlu UAT browser untuk konfirmasi penuh). Keputusan produk D-HI-01..08 adalah keputusan owner final — tidak dinilai ulang.

### 12.1 Verdict per temuan (yang diverifikasi langsung)

| Temuan | Verdict | Bukti verifikasi |
|---|---|---|
| HI-01 Save null → 0 | **DIKONFIRMASI (end-to-end)** | Bootstrap menyimpan null sebagai `''` (`harga_items.js:352`), tetapi render menampilkan `0.00` (`:404`), dan save mengirim **semua** baris dengan `0.00` (`:613-625`, `if(!canon) canon='0.00'` `:619`). Backend `views_api.py:3018` menyimpan karena `None != 0.00`. |
| HI-02 Konversi & harga dasar bukan satu transaksi | **DIKONFIRMASI** | `api_save_conversion_profile` (`:3230`) hanya `update_or_create` profile; **tidak** menyentuh `harga_item.harga_satuan`. Harga dasar baru tersimpan via tombol Save page yang terpisah. |
| HI-03 Export ≠ calculation | **DIKONFIRMASI** | `harga_items_adapter.py:24` (docstring) + `:87-98`: bila profile ada → `market_price / factor_to_base`; consumer (Rincian AHSP/Rekap) membaca `harga_satuan`. Lihat 12.2 soal status setelah D-HI-03. |
| HI-04 Profile DB tak dimuat di editor | **DIKONFIRMASI** | `build_harga_items_payload:4094` hanya `values('id','kode_item','kategori','uraian','satuan','harga_satuan')` — tanpa `conv`; page tidak memanggil `api_get_conversion_profiles`. |
| HI-05 Validasi conversion API lemah | **DIKONFIRMASI** | `api_save_conversion_profile:3216-3222`: `market_price`/`density`/`capacity` tanpa cek negatif; `method` tanpa whitelist (`:3222`); decimal invalid → default 0/1 (`:3217-3218`); tanpa `full_clean`; `market_unit` non-string → `.strip()` bisa 500 (`:3216`). Hanya `factor_to_base <= 0` yang dijaga (`:3226`). |
| HI-06 Backend tak tolak harga negatif | **DIKONFIRMASI** | `api_save_harga_items:3005-3007` hanya cek `dec is None`; tidak ada `dec < 0`; pesan error berbunyi "Harus ≥ 0" tetapi tak menegakkannya (pola sama TA-01). |
| HI-09 Last-save-wins multi-tab | **DIKONFIRMASI** | Backend punya token+409 (`:2949-2978`), tetapi frontend `:649-652` sengaja tidak kirim `client_updated_at` (di-comment); retry juga `delete retryPayload.client_updated_at` (`:716`). |
| HI-10 Save seluruh tabel, tanpa limit | **DIKONFIRMASI** | `harga_items.js:613` `viewRows.forEach(...)` mengirim semua item; endpoint save tanpa `@rate_limit`/payload count limit. |
| HI-12 Scope page vs export beda | **DIKONFIRMASI** | `active_harga_items_queryset` punya cabang standalone `Q(used_in_expanded=False, used_in_raw=False)` (`services.py:552`); `used_harga_items_queryset` tidak (`:576`). Page/save pakai `active_`, export pakai `used_`. |
| HI-16 Dead/drift code | **DIKONFIRMASI** | `payload.conversions` dibangun & dikirim (`harga_items.js:641`) tetapi `api_save_harga_items` **tidak pernah membacanya** — hanya `items` + `markup_percent`. Lihat 12.2. |

### 12.2 Penajaman bukti

- **HI-16 + HI-02 saling memperburuk — array `conversions` di tombol Save menuju ke mana-mana.** Frontend membangun `payload.conversions` (`:641`) dan mengirimnya bersama Save, tetapi endpoint save mengabaikannya total. Jadi satu-satunya cara konversi tersimpan adalah lewat endpoint profile terpisah (HI-02) — yang tidak menulis `harga_satuan`. Hasilnya: tidak ada satu pun jalur yang menyimpan profile **dan** harga dasar secara atomik. Ini menguatkan rekomendasi HI-02/D-HI-02 (`Terapkan dan Simpan` atomik) dan sekaligus menutup dead path HI-16.

- **HI-03 statusnya bergantung pada D-HI-03.** Setelah D-HI-03 (override manual menghapus profile) diimplementasikan, mismatch export/calculation memang turun jadi "diagnostic untuk data lama". Tetapi **saat ini** adapter masih aktif menghitung ulang dari profile (`:87-98`), jadi dokumen Harga Items yang diekspor ke klien/supplier bisa menampilkan harga berbeda dari RAB — bug hidup sampai HI-03+D-HI-03 dikerjakan. Prioritas P0-nya tepat.

- **HI-06 — pesan "≥ 0" tanpa penegakan** identik dengan Template AHSP TA-01. Fix konsisten: guard `dec < 0` (atau `<= 0` jika nol bukan harga sah — perlu keputusan, mirip aturan koefisien nol) + DB `CheckConstraint`.

### 12.3 Catatan konsistensi lintas-page (page ke-5)

Harga Items mengonfirmasi ulang pola sistemik yang sama di Dashboard, List Pekerjaan, Volume, dan Template AHSP:
- **Last-write-wins sengaja dimatikan di frontend** walau backend 409 tersedia (HI-09 = persis TA-02). Conflict backend memakai `project.updated_at` (`:2958`) yang juga di-bump oleh save harga (`:3052`) → rentan blind-spot/false-positive seperti VP-06.
- **Tanpa rate limit / payload limit** pada endpoint write (HI-10).
- **Pesan validasi "≥ 0" tanpa penegakan** (HI-06 = TA-01).
- **Bocoran `str(e)`** pada exporter (sama seperti TA-08, sistemik).
- **Sukses parsial diam-diam** — di sini varian "null→0 tanpa persetujuan" (HI-01) dan "conversions diabaikan" (HI-16).

Empat keputusan tingkat-aplikasi yang sama tetap berlaku: CSP bertahap; konvensi concurrency (revisi monotonik); wrapper error export bersama; dan konvensi "jangan ubah/buang data secara diam-diam — pakai status/diagnostic eksplisit".

### 12.4 Kalibrasi prioritas

Urutan P0 (HI-01, HI-02, HI-03, HI-05/06) sudah tepat. Catatan:
- **HI-01 dan HI-06 quick win** (HI-01: simpan hanya baris dirty + pertahankan null; HI-06: satu guard + DB constraint) — dampak integritas tinggi, effort rendah.
- **HI-02 + HI-16 sebaiknya dikerjakan bersama**: buat endpoint `Terapkan dan Simpan` atomik (D-HI-02) sekaligus hapus `payload.conversions` yang mati.
- **HI-12 + D-HI-04/D-HI-05** (unifikasi ke `used_` + pensiun Orphan Cleanup) adalah unit kerja tersendiri yang menyentuh beberapa consumer — jadwalkan terpisah.
