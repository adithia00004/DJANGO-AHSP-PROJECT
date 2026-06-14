# Audit Komprehensif Page Rekap Kebutuhan

**Tanggal audit:** 13 Juni 2026  
**Target:** `/detail_project/<project_id>/rekap-kebutuhan/`  
**Objek:** current working tree pada saat audit  
**Status:** **BELUM PRODUCTION-READY - distribusi waktu belum memakai SSOT jadwal kanonik dan beberapa mode menghasilkan scope berbeda**

> **Catatan urutan dan dependensi:** laporan ini dibaca setelah
> `22_Jadwal_Pekerjaan_Comprehensive_Audit_20260613.md`. Kontrak final distribusi
> periode, batas minggu, dan definisi Periode 4 Minggu harus mengikuti keputusan pada
> audit Jadwal Pekerjaan.

## 0. Rekonsiliasi dengan Keputusan Jadwal Pekerjaan

**Ditetapkan 14 Juni 2026.**

Bagian ini menjadi koreksi otoritatif terhadap istilah atau rekomendasi lama
dalam laporan yang masih menyebut bulan kalender, `PekerjaanTahapan` sebagai
sumber distribusi, atau JSON sebagai format laporan.

Kontrak lintas-page:

1. `PekerjaanProgressWeekly.planned_proportion` adalah satu-satunya SSOT
   distribusi waktu kebutuhan.
   `actual_proportion` tidak digunakan karena Rekap Kebutuhan merupakan
   perencanaan kebutuhan/pengadaan, bukan laporan pemakaian aktual.
2. Kolom minggu, `week_number`, tanggal awal/akhir, dan minggu parsial berasal
   dari builder kanonik backend yang sama dengan Jadwal Pekerjaan.
3. Rekap Kebutuhan tidak menghitung ulang nomor minggu dan tidak mendeteksi
   timeline basi melalui heuristik client.
4. `PekerjaanTahapan` hanya projection legacy/pengelompokan. Proporsi dan overlap
   tanggalnya tidak boleh menjadi formula kebutuhan.
5. Agregasi lebih besar memakai `Periode 4 Minggu`, bukan bulan kalender.
   Periode terakhir boleh kurang dari empat minggu.
6. Snapshot, Mingguan, Periode 4 Minggu, analytics, validation, dan export
   berasal dari dataset weekly-expanded yang sama.
7. JSON bukan format laporan Rekap Kebutuhan. JSON adalah paket copy/duplikasi
   Project dengan schema version dan kontrak import atomik.
8. PDF/XLSX dibangun server-authoritative. Beban besar mengikuti adaptive
   background export berdasarkan jumlah pekerjaan, minggu, format, dan konten.
9. Identitas laporan berasal dari identitas Project pada Dashboard. Nilai kosong
   tidak memblokir export dan menggunakan `.` hanya jika renderer memerlukan
   karakter pengganti.
10. Timestamp export tidak menjadi metadata wajib isi laporan. Nama file memakai
    `NamaProject_TanggalExport.ext`.

Arsitektur target:

```text
expanded item requirement per pekerjaan
  x volume pekerjaan
  x planned_proportion per minggu
  = weekly canonical item requirement

weekly requirement
  -> snapshot keseluruhan
  -> Mingguan
  -> Periode 4 Minggu
  -> analytics
  -> validation
  -> PDF/XLSX
```

Endpoint `api_rekap_kebutuhan_weekly()` yang ada belum dapat langsung dijadikan
SSOT karena masih membaca komponen raw, memakai fallback volume `1.0`, dan
mengagregasi terutama berdasarkan kode. Formula weekly harus dipindahkan ke
service shared berbasis `DetailAHSPExpanded`; endpoint menjadi serializer dari
service tersebut.

## 1. Ringkasan Eksekutif

Rekap Kebutuhan merupakan consumer lintas-page untuk menghitung kebutuhan item:

```text
Volume Pekerjaan
  x Koefisien komponen expanded dari Template AHSP
  x Proporsi jadwal/periode
  x Harga dasar dari Harga Items
  = Kuantitas dan biaya kebutuhan
```

Page menyediakan:

- snapshot kebutuhan seluruh project;
- mode kebutuhan per periode;
- filter kategori;
- filter klasifikasi, sub-klasifikasi, pekerjaan, tahapan, dan waktu;
- pencarian item;
- satuan dasar dan satuan beli;
- analytics kategori dan biaya terbesar;
- pemisahan item terjadwal/belum terjadwal;
- pilihan kolom;
- export PDF, Word, dan XLSX;
- validasi snapshot versus timeline melalui shortcut debug.

Fondasi yang sudah baik:

- page dan endpoint utama owner-scoped;
- agregasi utama memakai `DetailAHSPExpanded`;
- multiplier bundle diterapkan;
- fallback raw tersedia untuk data legacy/fixture;
- key agregasi mencakup kategori, kode, uraian, dan satuan;
- harga dasar membaca `HargaItemProject`;
- filter backend dinormalisasi;
- cache mempunyai signature data;
- web dan export memakai service agregasi yang sama untuk snapshot;
- dark mode, responsive layout, reduced motion, keyboard search, tooltip, live announcement, dan export feedback tersedia;
- conversion profile server dapat dipakai untuk menampilkan satuan beli.

Masalah utama:

1. Mode Per Periode masih memakai `PekerjaanTahapan` dan membagi volume merata berdasarkan overlap hari. Sistem telah menetapkan `PekerjaanProgressWeekly.planned_proportion` sebagai SSOT jadwal.
2. Mode timeline per tahapan menerapkan proporsi tahapan dua kali.
3. Pekerjaan tanpa assignment dihitung penuh pada setiap filter periode snapshot.
4. Timeline cache tidak berubah ketika harga item berubah.
5. Mode Per Periode menggabungkan rentang menjadi satu tabel, menghilangkan item belum terjadwal, mengabaikan search, dan tidak menerapkan mode satuan beli.
6. Snapshot menentukan status terjadwal pada level item gabungan. Item yang dipakai pekerjaan terjadwal dan belum terjadwal tidak dapat dipisahkan secara benar.
7. Filter tahapan, sub-klasifikasi, pekerjaan, dan periode disembunyikan dari UI walaupun logic masih tersedia.
8. Kontrol pilihan kolom tidak mengubah tabel.

## 2. Kontrak Produk dan SSOT

### 2.1 Snapshot Keseluruhan

Untuk setiap komponen dasar:

```text
base_item_quantity = pekerjaan_volume x effective_component_coefficient
base_item_cost     = base_item_quantity x canonical_base_unit_price
```

`effective_component_coefficient` harus sudah membawa multiplier nested bundle.

### 2.2 Kebutuhan Mingguan

Karena `PekerjaanProgressWeekly` telah didefinisikan sebagai storage jadwal kanonik:

```text
weekly_item_quantity =
  pekerjaan_volume
  x effective_component_coefficient
  x planned_proportion_week / 100
```

Kebutuhan Periode 4 Minggu adalah agregasi empat bucket mingguan kanonik secara
berurutan. Jangan membuat distribusi kedua berdasarkan overlap tanggal tahapan
atau bulan kalender.

### 2.3 Tahapan

`PekerjaanTahapan` adalah view/derivasi kompatibilitas. Mode tahapan boleh mengelompokkan minggu atau pekerjaan yang berada dalam tahapan, tetapi proporsi tidak boleh diterapkan kembali setelah proporsi mingguan/tahapan sudah masuk.

### 2.4 Satuan Beli

Sesuai keputusan Harga Items:

- satuan dasar AHSP tidak berubah;
- harga dasar pada Harga Items tetap SSOT calculation;
- conversion profile hanya menerjemahkan presentasi pembelian;
- toggle satuan beli tidak boleh mengubah nilai total kanonik.

Formula display:

```text
market_quantity = base_quantity / factor_to_base
market_unit_price = base_total_cost / market_quantity
```

`market_price` dapat ditampilkan sebagai referensi input conversion, tetapi total kebutuhan harus tetap berasal dari harga dasar kanonik.

## 3. Ruang Lingkup Implementasi

| Area | Implementasi |
|---|---|
| Page view | `detail_project.views.rekap_kebutuhan_view` |
| Template | `detail_project/templates/detail_project/rekap_kebutuhan.html` |
| Main JS | `detail_project/static/detail_project/js/rekap_kebutuhan.js` |
| Toolbar JS | `detail_project/static/detail_project/js/rekap_kebutuhan_toolbar.js` |
| CSS | `rekap_kebutuhan.css`, `rekap_kebutuhan_enhancements.css` |
| Snapshot service | `compute_kebutuhan_items` |
| Timeline service | `compute_kebutuhan_timeline` |
| Weekly canonical endpoint | `api_rekap_kebutuhan_weekly` |
| Enhanced API | `api_get_rekap_kebutuhan_enhanced` |
| Timeline API | `api_get_rekap_kebutuhan_timeline` |
| Validation | `validate_kebutuhan_data` |
| Conversion profiles | `api_get_conversion_profiles` |
| Export | `RekapKebutuhanAdapter`, `ExportManager` |

Ukuran implementasi:

- main JavaScript sekitar 2.882 baris;
- template sekitar 654 baris;
- dua file CSS sekitar 2.649 baris;
- toolbar enhancement sekitar 383 baris.

Ukuran tersebut menunjukkan page telah mengakumulasi beberapa generasi UI dan mode kompatibilitas.

## 4. Audit Per Mode dan Elemen Interaktif

### 4.1 Initial Load

**Status:** Fungsional bersyarat.

Urutan initial:

1. parse URL filter;
2. fetch metadata filter;
3. fetch daftar tahapan;
4. pasang event;
5. inisialisasi export/range/UX;
6. fetch snapshot;
7. fetch timeline penuh sebagai auxiliary scheduled lookup.

Snapshot gagal seluruhnya jika request timeline auxiliary gagal karena keduanya berada dalam satu `Promise.all`.

### 4.2 Snapshot Keseluruhan

**Status:** Calculation dasar baik, grouping schedule tidak presisi.

- komponen expanded diagregasi;
- bundle multiplier diterapkan;
- volume dan harga item dibaca;
- kategori, quantity, harga satuan, dan total ditampilkan;
- analytics memakai row snapshot;
- search difilter backend.

Status terjadwal diperoleh dengan membandingkan key item terhadap seluruh item timeline. Ini tidak dapat memisahkan quantity item yang sama dari pekerjaan berbeda.

### 4.3 Mode Per Periode

**Status:** Tidak sesuai SSOT dan label UI.

Mode ini:

- memilih minggu/bulan kalender pada implementasi lama;
- memanggil timeline API dengan `aggregate=true`;
- server menggabungkan seluruh periode terpilih;
- client menampilkan satu tabel agregat.

Jadi label `Per Periode` sebenarnya berarti `Agregat rentang periode`, bukan
breakdown tiap periode. Implementasi card per minggu/bulan kalender masih ada
tetapi tidak menjadi jalur utama dan harus dimigrasikan menjadi Mingguan/Periode
4 Minggu.

### 4.4 Mode Tahapan

**Status:** Logic tersedia, UI utama disembunyikan, calculation timeline salah.

- endpoint menerima `mode=tahapan&tahapan_id=...`;
- menu tahapan berada dalam container `d-none`;
- mode dapat dipicu melalui URL/logic lama;
- snapshot memakai proporsi assignment satu kali;
- timeline memakai proporsi tersebut saat membuat `base_quantity`, lalu mengalikan kembali dengan proporsi assignment.

### 4.5 Filter Kategori

**Status:** Fungsional.

- TK, BHN, ALT, LAIN tersedia;
- backend whitelist kategori;
- chip aktif dapat dihapus;
- jika semua kategori dilepas, normalized filter kosong berarti semua kategori kembali ditampilkan.

State `tidak ada kategori` seharusnya menghasilkan nol hasil atau dicegah dengan validasi, bukan berarti semua.

### 4.6 Filter Klasifikasi

**Status:** Fungsional.

- multi-select tersedia;
- pekerjaan difilter melalui relasi sub-klasifikasi;
- count pekerjaan tersedia;
- penggunaan Shift/Ctrl untuk multi-select kurang discoverable pada mobile.

### 4.7 Filter Sub-klasifikasi dan Pekerjaan

**Status:** Logic tersedia tetapi tidak accessible dari UI normal.

Elemen dan renderer ada, tetapi seluruh kontrol ditempatkan dalam container `d-none`.

### 4.8 Filter Waktu

**Status:** Tersedia melalui timeline toolbar/export, tersembunyi pada filter modal.

- week/month kalender dan range didukung backend lama;
- snapshot memakai multiplier overlap tahapan;
- timeline memakai bucket overlap tahapan;
- timeline toolbar auto-fetch setiap perubahan select;
- start/end dapat dibalik backend;
- pekerjaan tanpa assignment diperlakukan tidak konsisten.

### 4.9 Search

**Status:** Snapshot fungsional, timeline tidak.

- snapshot mencari kode/uraian di backend;
- autocomplete memakai row terakhir;
- timeline query membawa parameter search tetapi service/API tidak menerapkannya;
- scope/filter indicator tetap menyatakan search aktif.

### 4.10 Satuan Dasar

**Status:** Fungsional.

Quantity, harga dasar, dan total berasal dari service kanonik.

### 4.11 Satuan Beli

**Status:** Snapshot bersyarat, timeline tidak berfungsi.

- snapshot memuat profile server;
- jika server gagal, client memindai localStorage;
- quantity dan harga dikonversi;
- timeline tidak dirender ulang dengan conversion;
- toggle tetap terlihat aktif pada timeline;
- analytics tidak ikut diperbarui ketika unit berubah;
- total snapshot dapat berubah karena dihitung ulang dari `market_price`.

### 4.12 Scheduled/Unscheduled

**Status:** Tidak presisi.

Snapshot:

- seluruh row item diberi boolean `is_scheduled`;
- satu item hanya dapat masuk salah satu group;
- quantity tidak dibagi berdasarkan asal pekerjaan.

Timeline:

- server membuat bucket `Di luar jadwal`;
- response aggregate memisahkan `unscheduled_total` tetapi tidak mengirim row unscheduled;
- renderer menerima `unscheduledTotal` tetapi tidak menampilkannya.

### 4.13 Analytics

**Status:** Snapshot baik bersyarat, timeline stale.

- chart komposisi kategori;
- top biaya;
- mode compact/full;
- summary list;
- ECharts dibundel lokal.

Saat timeline aggregate dimuat, stats toolbar diperbarui tetapi chart tidak. Chart tetap membawa data snapshot/filter sebelumnya.

### 4.14 Refresh

**Status:** Tidak berfungsi.

Toolbar mengirim event `rk:refresh`, tetapi main JS tidak mendengarkan event tersebut. Spinner berhenti setelah timeout dua detik tanpa memastikan data dimuat ulang.

Shortcut Ctrl+R juga mencegah browser refresh lalu memicu event yang tidak digunakan.

### 4.15 Column Visibility

**Status:** Dead control.

Checkbox Satuan Beli, Faktor Konversi, Qty Satuan Beli, dan Harga Satuan Beli hanya menyimpan state localStorage lalu merender ulang tabel yang tetap mempunyai tujuh kolom yang sama.

### 4.16 Empty dan Error State

**Status:** Dasar tersedia.

- loading dan empty state tersedia;
- empty state hanya mengatakan tidak ada data untuk filter;
- tidak membedakan project kosong, volume kosong, detail kosong, harga kosong, atau filter tanpa hasil;
- error snapshot diubah menjadi empty state setelah toast.

### 4.17 Export

**Status:** Snapshot cukup selaras, range berbeda dari layar.

- PDF, Word, XLSX tersedia;
- export modal mempunyai period dan unit mode;
- full export memakai snapshot service;
- range export memakai timeline service dan membuat page per periode;
- export melewati `Di luar jadwal`;
- layar timeline menggabungkan range menjadi satu tabel, sedangkan export memisah per periode;
- JSON tidak meneruskan `unit_mode`;
- error endpoint mengekspos `str(e)`;
- nilai harga dibulatkan ke rupiah penuh.

### 4.18 Validation Debug

**Status:** Berguna untuk developer, bukan kontrak user.

- Ctrl+Shift+D membuka validasi snapshot versus timeline;
- membandingkan total dan kategori;
- warning berbahasa Inggris;
- modal tidak terlihat dari UI;
- validation membandingkan dua algoritma yang memang berbeda;
- mismatch dapat berasal dari bug time scope/tahapan, bukan hanya data user.

### 4.19 Responsive dan Accessibility

**Status:** Baik bersyarat.

Yang sudah baik:

- toolbar responsive;
- sticky table header;
- horizontal scrolling;
- focus-visible;
- reduced motion;
- dark mode;
- aria-pressed pada view/unit toggle;
- modal mempunyai title;
- search mempunyai label;
- timeline tooltip dapat difokuskan.

Kekurangan:

- hidden advanced filters tidak dapat dipakai;
- multiple select bergantung keyboard modifier;
- range select tidak mempunyai visible/accessible label pada toolbar;
- icon-only week/month buttons hanya memakai `title`;
- table tidak mempunyai caption;
- loading container tidak memakai `aria-live`/`aria-busy`;
- perubahan data tidak selalu diumumkan;
- toolbar enhancement mengumumkan mode dalam bahasa Inggris;
- modal close memakai label `Close`;
- status warning tidak menyediakan link/tindakan.

## 5. Temuan Audit

### RK-01 - CRITICAL - Timeline Tidak Menggunakan Storage Jadwal Kanonik

Model dan API v2 menetapkan `PekerjaanProgressWeekly.planned_proportion` sebagai SSOT. `compute_kebutuhan_timeline()` masih memakai `PekerjaanTahapan` dan membagi quantity berdasarkan proporsi overlap hari dalam tanggal tahapan.

**Dampak:**

- kebutuhan mingguan tidak mengikuti distribusi yang diedit user;
- pekerjaan dengan planned progress tidak merata tetap tampil merata;
- Jadwal/Kurva S dan Rekap Kebutuhan dapat berbeda.

**Rekomendasi:** buat builder mingguan kanonik berbasis `PekerjaanProgressWeekly`, memakai komponen expanded. Snapshot, timeline, validation, dan export harus memakai builder tersebut.

### RK-02 - CRITICAL - Proporsi Tahapan Diterapkan Dua Kali pada Timeline

Dalam mode tahapan:

1. `pekerjaan_proporsi` sudah diisi `proporsi_volume / 100`;
2. `base_quantity` dikalikan proporsi tersebut;
3. loop assignment kembali menghitung `assignment_quantity = base_quantity x proporsi / 100`.

Contoh assignment 50% menghasilkan 25%, bukan 50%.

### RK-03 - CRITICAL - Pekerjaan Tanpa Jadwal Dihitung Penuh pada Setiap Filter Periode Snapshot

`_build_time_scope_multiplier()` mengembalikan `1.0` ketika pekerjaan tidak
mempunyai assignment. Akibatnya pekerjaan belum terjadwal masuk penuh pada
minggu/periode mana pun yang dipilih.

**Rekomendasi:** multiplier periode untuk pekerjaan tanpa jadwal adalah 0. Quantity tersebut masuk bucket `Belum terjadwal`, bukan periode terpilih.

### RK-04 - HIGH - Timeline Harga Dapat Stale Setelah Harga Items Berubah

Signature `_kebutuhan_signature()` tidak memasukkan timestamp `HargaItemProject`. Signal Harga Items hanya menghapus namespace `rekap_kebutuhan:<id>`, bukan `rekap_kebutuhan_timeline:<id>`.

**Dampak:** snapshot dapat baru sementara timeline tetap memakai harga cache lama sampai timeout.

### RK-05 - HIGH - Endpoint Weekly Baru Belum Layak Menjadi Pengganti Langsung

`api_rekap_kebutuhan_weekly()` sudah memakai planned proportion, tetapi membaca `pekerjaan.detail_list` raw, bukan `DetailAHSPExpanded`.

**Dampak:** nested bundle tidak dihitung sesuai expanded component.

**Rekomendasi:** pindahkan formula ke service shared berbasis expanded storage; endpoint hanya serialisasi.

### RK-06 - HIGH - Timeline Menghilangkan Item Belum Terjadwal

Aggregate API melewati period `unscheduled`, hanya mengirim totalnya. Renderer menerima `unscheduledTotal` tetapi tidak menampilkan angka atau row.

**Dampak:** user melihat timeline total yang lebih kecil dari kebutuhan project tanpa penjelasan memadai.

### RK-07 - HIGH - Search Tidak Berlaku pada Mode Per Periode

Parameter search dikirim, tetapi timeline service tidak memfilter kode/uraian. UI tetap menampilkan chip/search scope aktif.

### RK-08 - HIGH - Toggle Satuan Beli Tidak Berlaku pada Timeline

Handler hanya merender ulang snapshot. Timeline tetap menampilkan satuan dasar walaupun tombol `Satuan Beli` aktif.

### RK-09 - HIGH - Konversi Satuan Dapat Mengubah Grand Total

Client menghitung:

```text
market_total = base_qty / factor x market_price
```

Padahal total kanonik telah dihitung dari harga dasar. Jika profile stale/tidak identik dengan harga dasar, toggle presentasi mengubah total.

Export mempertahankan `harga_total` lama, sehingga web dan export dapat berbeda.

### RK-10 - HIGH - Fallback Conversion localStorage Tidak Project-Scoped

Fallback memindai key `hiConv:<kode>` tanpa project ID. Ketika endpoint server gagal, profile project lain dengan kode sama dapat dipakai.

**Rekomendasi:** hapus fallback dari consumer. Server/database adalah SSOT conversion profile.

### RK-11 - HIGH - Scheduled/Unscheduled Salah pada Item yang Dipakai Campuran

Status ditentukan dengan key:

```text
kategori|kode|uraian|satuan
```

Jika semen dipakai pada satu pekerjaan terjadwal dan satu belum terjadwal, seluruh semen ditandai terjadwal. Quantity/cost tidak dibagi.

### RK-12 - HIGH - Kegagalan Timeline Auxiliary Mematikan Snapshot

Snapshot dan timeline lookup dipanggil dengan `Promise.all`. Timeline hanya dipakai untuk status schedule, tetapi kegagalannya membuat tabel snapshot gagal.

### RK-13 - HIGH - Filter Penting Disembunyikan

Sub-klasifikasi, pekerjaan, tahapan, dan time scope berada di container `d-none`. Logic, URL parsing, chip, dan API tetap ada.

**Dampak:** kemampuan page tidak dapat ditemukan/digunakan secara normal dan kode maintenance jauh lebih besar daripada UI aktual.

### RK-14 - HIGH - Refresh Toolbar Tidak Memuat Ulang Data

Toolbar mengirim `rk:refresh`; tidak ada listener pada main JS. Ctrl+R browser juga dicegah.

### RK-15 - MEDIUM - Mode Per Periode Tidak Benar-Benar Menampilkan Per Periode

Jalur utama memakai `aggregate=true`, sehingga rentang minggu/periode menjadi
satu tabel. `periodTotals` diterima tetapi tidak ditampilkan.

### RK-16 - MEDIUM - Chart Timeline Membawa Data Lama

Aggregated timeline tidak memanggil update analytics. Chart dapat tetap menampilkan snapshot atau filter sebelumnya.

### RK-17 - MEDIUM - Pilihan Semua Kategori Dilepas Berarti Semua Kategori

Empty kategori list dinormalisasi sebagai tidak ada filter. Label sempat menyatakan `Tidak ada kategori`, tetapi backend mengembalikan semua.

### RK-18 - MEDIUM - Pilihan Kolom Tidak Mempunyai Efek

Empat checkbox column visibility tidak digunakan oleh renderer/header.

### RK-19 - MEDIUM - Missing Data dan Nol Valid Tidak Dibedakan

Harga, volume, dan koefisien kosong menjadi nol. Row dengan volume efektif nol dilewati.

Page tidak menjelaskan:

- pekerjaan belum mempunyai volume;
- item belum mempunyai harga;
- detail/expanded belum siap;
- koefisien memang nol;
- item tidak muncul karena filter waktu.

### RK-20 - MEDIUM - Total Proporsi Assignment Tidak Dijamin 100%

Model mempunyai `validate_total_proporsi()`, tetapi pemanggilannya dikomentari. API dapat menyimpan kombinasi assignment di bawah atau di atas 100%.

Timeline mode keseluruhan dapat undercount/overcount.

### RK-21 - MEDIUM - Timeline dan Snapshot Memakai Definisi Unscheduled Berbeda

Snapshot time filter memasukkan pekerjaan tanpa assignment penuh. Timeline memasukkannya ke `Di luar jadwal`. Validation mismatch menjadi konsekuensi formula, bukan diagnostic data saja.

### RK-22 - MEDIUM - Export Range Melewati Unscheduled Tanpa Catatan

`ExportManager` secara eksplisit skip period `unscheduled`. Tidak ada halaman/summary warning.

### RK-23 - MEDIUM - Error API Mengekspos Detail Exception

Enhanced/timeline/export endpoint dapat mengirim `str(e)` ke client.

### RK-24 - MEDIUM - Sidebar Active State Tidak Disetel

`rekap_kebutuhan_view()` tidak mengirim `side_active="rekap_kebutuhan"`, sehingga sidebar dapat tidak menandai page aktif.

### RK-25 - MEDIUM - State Scope Tidak Persisten dan Tidak Sinkron ke URL

URL awal dapat dibaca, tetapi perubahan filter/view/range tidak ditulis kembali ke URL. Refresh/share/back tidak merepresentasikan state terakhir.

### RK-26 - LOW - Empty State Tidak Menjelaskan Penyebab

Pesan yang sama dipakai untuk project kosong, no-result, missing volume, missing AHSP, dan scope jadwal kosong.

### RK-27 - LOW - Toolbar Enhancement Mempunyai Banyak Target Mati

Contoh:

- `rk-search-clear` tidak ada;
- `.rk-stats-toggle` tidak ada;
- `.rk-stat-card` tidak ada pada layout aktif;
- `rk-stats-collapse` hidden compatibility;
- event `rk:dataLoaded` tidak pernah dikirim.

### RK-28 - LOW - Debug dan Console Noise Masuk Production

Terdapat banyak `console.log`, data sample, period totals, scheduled keys, serta shortcut debug tersembunyi.

### RK-29 - LOW - Terminologi dan Bahasa Tidak Konsisten

Contoh:

- item/items;
- Stats;
- Close;
- Switched to timeline view;
- MISMATCH DETECTED;
- Satuan Beli `(dari Supplier)` walaupun sumbernya profile project.

### RK-30 - LOW - CSS dan UI Memuat Beberapa Generasi Implementasi

Dua stylesheet besar, print rule ganda, timeline cards, aggregate timeline, filter controls lama, toolbar compatibility, dan dead stat cards meningkatkan risiko regression.

## 6. Penilaian UI/UX

### Yang Sudah Baik

1. Snapshot kebutuhan mudah dipahami sebagai tabel item.
2. Kategori memiliki ikon dan warna konsisten.
3. Search dan autocomplete tersedia.
4. Analytics membantu melihat konsentrasi biaya.
5. Toggle snapshot/timeline jelas secara visual.
6. Toggle satuan dasar/beli sesuai kebutuhan lapangan.
7. Range waktu tersedia secara compact, walaupun implementasi lama masih memakai bulan kalender.
8. Export modal menjelaskan periode, format, dan satuan.
9. Active filter chip dapat dilepas langsung.
10. Table dan toolbar responsive.
11. Dark mode dan reduced motion tersedia.

### Perbaikan UX Prioritas

1. Ubah label timeline sesuai fungsi final: breakdown per periode, bukan satu tabel range.
2. Tampilkan unscheduled sebagai section permanen.
3. Berikan warning completeness dengan penyebab dan sumber pekerjaan/item.
4. Kembalikan filter tahapan, sub, dan pekerjaan hanya jika memang dibutuhkan; jika tidak, hapus logic dead.
5. Perbaiki refresh.
6. Hilangkan pilihan kolom sampai benar-benar didukung.
7. Pada satuan beli, tampilkan faktor dan tooltip sumber conversion tanpa mengubah total.
8. Tampilkan link langsung ke Jadwal untuk pekerjaan belum mempunyai planned distribution.

## 7. Konsistensi dengan Page Lain

### Template AHSP

- Rekap harus memakai expanded component;
- nested depth/readiness harus terbawa;
- raw fallback hanya kompatibilitas, bukan hasil final tanpa warning.

### Harga Items

- harga dasar adalah SSOT;
- conversion profile adalah helper presentasi/pembelian;
- override manual menghapus profile conversion;
- Rekap tidak boleh memakai localStorage sebagai sumber alternatif.

### Volume Pekerjaan

- volume null dan zero harus dibedakan;
- volume pekerjaan adalah input quantity utama.

### Jadwal Pekerjaan

- planned weekly proportion adalah SSOT;
- timeline Rekap Kebutuhan harus identik dengan distribusi planned;
- tahapan merupakan view pengelompokan, bukan formula jadwal kedua.

### Rekap RAB

- Rekap RAB menghitung nilai pekerjaan setelah markup;
- Rekap Kebutuhan menghitung kebutuhan item dengan harga dasar;
- total biaya kebutuhan tidak harus sama dengan Rekap RAB karena tidak membawa markup pekerjaan/PPN;
- perbedaan tersebut harus dijelaskan pada UI/help/export.

## 8. Prioritas Remediasi

| Urutan | Item | Gate |
|---|---|---|
| P0 | RK-01 builder timeline dari weekly canonical | Wajib sebelum timeline dipercaya |
| P0 | RK-02 hapus double proportion | Integritas quantity |
| P0 | RK-03 perbaiki unscheduled pada time filter | Integritas scope |
| P0 | RK-04 invalidasi/signature harga timeline | Integritas harga |
| P0 | RK-05 satukan weekly builder dengan expanded storage | SSOT nested bundle |
| P1 | RK-06 sampai RK-12 | Konsistensi mode dan availability |
| P1 | RK-13/RK-14 filter dan refresh | Workflow utama |
| P1 | RK-15 sampai RK-23 | Timeline/export/completeness |
| P2 | RK-24 sampai RK-30 | Navigation, accessibility, maintainability |

## 9. Keputusan Produk yang Perlu Dikonfirmasi

### D-RK-01 - Definisi Timeline

**Rekomendasi:** mode `Per Periode` menampilkan kebutuhan per Minggu atau
Periode 4 Minggu sesuai `planned_proportion`. Range hanya membatasi periode yang
terlihat, bukan menggabungkan semua menjadi satu tabel.

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

- User memilih salah satu mode: `Mingguan` atau `Periode 4 Minggu`.
- Kedua granularitas tidak ditampilkan atau dicampur bersamaan.
- Pada mode Mingguan, setiap minggu dalam rentang tampil sebagai tabel/section
  tersendiri.
- Pada mode Periode 4 Minggu, setiap blok empat minggu dalam rentang tampil
  sebagai tabel/section tersendiri.
- Rentang hanya membatasi bucket yang ditampilkan; backend tidak boleh
  menggabungkan seluruh rentang menjadi satu tabel agregat.
- Periode terakhir boleh kurang dari empat minggu dan tetap tampil sebagai
  bucket tersendiri.
- Pergantian mode memakai dataset weekly kanonik yang sama sehingga total
  gabungan bucket tetap konsisten.

### D-RK-02 - Unscheduled

**Rekomendasi:** selalu tampilkan section `Belum Terjadwal`, terpisah dari
Minggu/Periode 4 Minggu. Nilainya tetap masuk Total Kebutuhan Project, tetapi
tidak masuk total periode.

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

- Snapshot Total Kebutuhan Project dihitung dari volume pekerjaan dan komponen
  expanded, sehingga tidak bergantung pada mode Rencana atau Realisasi.
- Distribusi kebutuhan ke Minggu/Periode 4 Minggu hanya memakai
  `PekerjaanProgressWeekly.planned_proportion`.
- `actual_proportion` tidak digunakan pada Rekap Kebutuhan.
- Untuk setiap pekerjaan, persentase Rencana yang telah dialokasikan masuk ke
  bucket periode terkait.
- Sisa sampai 100% masuk section `Belum Terjadwal`; pekerjaan tanpa Rencana
  sama sekali mempunyai sisa 100%.
- Status dihitung pada level pekerjaan dan quantity, bukan boolean pada item
  yang sudah digabung.
- Section `Belum Terjadwal` tampil setelah seluruh periode dan disertakan pada
  PDF/XLSX.
- Nilai Belum Terjadwal masuk Total Kebutuhan Project, tetapi tidak masuk total
  periode tertentu.
- UI menampilkan pekerjaan sumber dan tautan menuju Jadwal Pekerjaan.
- Jika seluruh pekerjaan telah dialokasikan 100%, section disembunyikan.

Invariant:

```text
Total Kebutuhan Project
= jumlah kebutuhan seluruh periode
+ kebutuhan Belum Terjadwal
```

#### Keputusan Klasifikasi Ringkasan Kebutuhan

**Hasil diskusi 14 Juni 2026: DISETUJUI.**

Rekap Kebutuhan dibagi menjadi tiga klasifikasi utama:

1. **Total Kebutuhan**
   - seluruh kebutuhan Project berdasarkan volume pekerjaan dan komponen
     expanded;
   - tidak bergantung pada Rencana atau Realisasi;
   - menjadi nilai induk/acuan.
2. **Rencana Telah Dialokasikan**
   - bagian dari Total Kebutuhan yang sudah mempunyai distribusi
     `planned_proportion`;
   - merupakan jumlah seluruh bucket Mingguan atau Periode 4 Minggu yang
     ditampilkan;
   - bukan tambahan di luar Total Kebutuhan.
3. **Kebutuhan Belum Terjadwal**
   - sisa Total Kebutuhan yang belum dialokasikan oleh Rencana;
   - ditampilkan sebagai section terpisah setelah seluruh periode;
   - bukan item baru dan tidak boleh dihitung ganda.

Hubungan ketiganya:

```text
Total Kebutuhan
= Rencana Telah Dialokasikan
+ Kebutuhan Belum Terjadwal
```

Klasifikasi berlaku pada quantity dan biaya harga dasar. Ringkasan UI dan export
harus menampilkan ketiga nilai tersebut dengan label konsisten. Jika seluruh
Rencana telah mencapai 100%, nilai Belum Terjadwal adalah nol dan section
detailnya dapat disembunyikan.

### D-RK-03 - Satuan Beli

**Rekomendasi:** toggle hanya mengubah unit, quantity, dan harga display. Total biaya tetap identik dengan satuan dasar.

**Keputusan diskusi 14 Juni 2026: DISETUJUI DAN DISELARASKAN DENGAN HARGA ITEMS.**

Kontrak harga:

- `HargaItemProject.harga_satuan` adalah SSOT harga per satuan dasar untuk
  seluruh kalkulasi backend Rekap Kebutuhan;
- jika user memakai popup konversi pada Harga Items, server menghitung
  `harga_satuan = market_price / factor_to_base` dan menyimpan harga dasar serta
  conversion profile secara atomik;
- jika user mengubah harga dasar secara manual, conversion profile dihapus
  sesuai keputusan Page Harga Items;
- Rekap Kebutuhan tidak memilih sumber harga sendiri dan tidak menghitung ulang
  harga kanonik dari profile pada client.

Mode tampilan:

```text
Satuan Dasar:
base_quantity x HargaItemProject.harga_satuan

Satuan Beli:
market_quantity = base_quantity / factor_to_base
market_quantity x market_price
```

Dalam kondisi data valid, kedua representasi menghasilkan total identik.

Ketentuan:

- total resmi berasal dari hasil kalkulasi backend;
- mode Satuan Beli menampilkan `market_unit`, `market_quantity`, `market_price`,
  dan faktor konversi dari profile server yang tersinkron;
- snapshot, Mingguan, Periode 4 Minggu, analytics, PDF, dan XLSX memakai kontrak
  yang sama;
- fallback conversion dari `localStorage` dihapus;
- item tanpa conversion profile tetap ditampilkan dalam satuan dasar;
- jika `market_price / factor_to_base` berbeda dari `harga_satuan`, sistem
  menampilkan diagnostic integritas dan tidak memilih salah satu nilai secara
  diam-diam;
- nilai `null` dan harga eksplisit `0.00` tetap dibedakan sesuai keputusan Harga
  Items.

### D-RK-04 - Filter Lanjutan

**Rekomendasi:** tampilkan kategori, klasifikasi, sub-klasifikasi, pekerjaan, dan tahapan dalam modal bertingkat. Filter waktu cukup berada pada mode timeline agar tidak tumpang tindih.

**Keputusan diskusi 14 Juni 2026: DISETUJUI DENGAN PEMISAHAN FILTER DAN RENTANG WAKTU.**

Modal filter atribut memuat:

1. Kategori Item.
2. Klasifikasi.
3. Sub-klasifikasi yang mengikuti Klasifikasi.
4. Pekerjaan melalui pencarian multi-select.
5. Status Alokasi: Semua, Rencana Telah Dialokasikan, atau Belum Terjadwal.

Filter Tahapan legacy dihapus dari workflow utama. Tahapan tidak menjadi sumber
formula atau filter resmi karena distribusi kebutuhan memakai planned weekly
SSOT. Jika dibutuhkan kemudian, tahapan hanya boleh menjadi pengelompokan
presentasi.

Pemilihan waktu tetap tersedia di luar modal filter:

- mode `Mingguan` menyediakan pilihan minggu awal dan minggu akhir;
- mode `Periode 4 Minggu` menyediakan pilihan periode awal dan periode akhir;
- contoh Minggu 4 sampai Minggu 8 menampilkan kebutuhan yang harus disediakan
  dalam bucket Minggu 4, 5, 6, 7, dan 8;
- setiap bucket tetap tampil terpisah dan tidak digabung menjadi satu tabel;
- total rentang boleh ditampilkan sebagai ringkasan tambahan, tetapi tidak
  menggantikan rincian setiap bucket;
- rentang divalidasi terhadap weekly columns kanonik, termasuk minggu parsial;
- perpindahan granularitas Mingguan/Periode 4 Minggu tidak mencampur keduanya
  dalam satu tampilan.

Ketentuan UX:

- filter atribut dan rentang waktu dapat digunakan bersamaan;
- seluruh filter aktif dan rentang tampil sebagai chip/ringkasan;
- state ditulis ke URL agar refresh, back, dan share mempertahankan tampilan;
- tidak boleh ada filter tersembunyi aktif tanpa indikator;
- melepas seluruh kategori menghasilkan nol hasil atau dicegah melalui validasi,
  bukan diam-diam kembali menjadi semua kategori.

### D-RK-05 - Definisi Biaya

**Rekomendasi:** beri label `Total Harga Dasar Kebutuhan`. Tambahkan keterangan bahwa nilai belum mencakup markup pekerjaan dan PPN Rekap RAB.

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

Label biaya resmi:

| Konteks | Label |
|---|---|
| Harga per satuan item | `Harga Dasar Satuan` |
| Total per item | `Total Harga Dasar` |
| Total keseluruhan | `Total Harga Dasar Kebutuhan` |

Formula:

```text
Total Harga Dasar Item
= Quantity Kebutuhan
x HargaItemProject.harga_satuan
```

Rekap Kebutuhan tidak memasukkan markup pekerjaan, override markup Rincian AHSP,
PPN, atau komponen anggaran lain pada Rekap RAB. UI dan export menampilkan
catatan:

> Nilai menggunakan harga dasar dari Harga Items dan belum mencakup markup
> pekerjaan, PPN, maupun komponen anggaran Rekap RAB.

Ringkasan biaya mengikuti klasifikasi kebutuhan:

```text
Total Harga Dasar Kebutuhan
= Harga Dasar Rencana Telah Dialokasikan
+ Harga Dasar Kebutuhan Belum Terjadwal
```

Penanganan kelengkapan harga:

- `harga_satuan IS NULL` berarti harga belum diisi dan ditampilkan sebagai
  `Belum diisi`;
- harga eksplisit `0.00` ditampilkan sebagai `Rp0`;
- total dengan item berharga `null` diberi label `Total sementara`, bukan total
  final;
- UI menampilkan jumlah item tanpa harga dan tautan menuju Harga Items;
- analytics tidak boleh menyamarkan item tanpa harga sebagai item bernilai nol;
- PDF/XLSX mencantumkan jumlah item tanpa harga serta status total sementara.

### D-RK-06 - Export

**Rekomendasi:** export mengikuti mode layar:

- snapshot: satu tabel agregat;
- timeline: halaman/sheet per periode;
- unscheduled: halaman/sheet khusus;
- warning completeness: summary awal.

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

PDF dan XLSX memakai satu dataset server-authoritative yang sama. Perbedaan
format hanya pada presentasi, bukan sumber data, filter, quantity, harga, atau
status kelengkapan.

Struktur export:

1. **Total Kebutuhan**
   - ringkasan tiga klasifikasi;
   - status kelengkapan data;
   - satu tabel agregat Total Kebutuhan;
   - catatan definisi harga dasar;
   - pengesahan.
2. **Mingguan**
   - ringkasan cakupan;
   - satu tabel/section untuk setiap minggu terpilih;
   - section Kebutuhan Belum Terjadwal;
   - ringkasan total;
   - pengesahan.
3. **Periode 4 Minggu**
   - ringkasan cakupan;
   - satu tabel/section untuk setiap blok empat minggu terpilih;
   - periode terakhir boleh kurang dari empat minggu;
   - section Kebutuhan Belum Terjadwal;
   - ringkasan total;
   - pengesahan.

Ringkasan wajib memuat:

- Total Kebutuhan;
- Rencana Telah Dialokasikan;
- Kebutuhan Belum Terjadwal;
- jumlah item tanpa harga;
- jumlah pekerjaan tanpa volume;
- status/readiness expanded component;
- mode satuan;
- kategori, klasifikasi, sub-klasifikasi, pekerjaan, status alokasi, search, dan
  cakupan waktu yang diterapkan.

Aturan format:

- filter dan search file identik dengan pilihan user;
- rentang tidak digabung menjadi satu tabel agregat;
- JSON dikeluarkan dari format laporan Rekap Kebutuhan dan tetap menjadi paket
  copy/duplikasi Project;
- opsi Word disembunyikan sampai jalur tersebut didukung dan lulus pengujian;
- formula spreadsheet bukan SSOT; nilai resmi berasal dari dataset backend.

Aturan PDF:

- header tabel diulang pada halaman lanjutan;
- baris item tidak dipotong antarhalaman;
- judul bucket diulang jika satu bucket melewati lebih dari satu halaman;
- bagian akhir tabel, total, catatan, dan tanda tangan dijaga sebagai satu
  bundel;
- tanda tangan tidak boleh berdiri sendiri dan harus ikut dengan minimal tiga
  baris terakhir tabel, atau seluruh baris jika kurang dari tiga;
- pagination mereservasi ruang pengesahan sebelum membagi halaman.

Aturan XLSX:

- mempunyai sheet `Ringkasan`;
- snapshot mempunyai sheet `Total Kebutuhan`;
- Mingguan/Periode 4 Minggu memakai section atau sheet bucket terpisah tanpa
  mencampur granularitas;
- sheet `Belum Terjadwal` dibuat hanya jika mempunyai data;
- freeze panes, format angka, autofilter, dan lebar kolom diterapkan.

Export besar mengikuti adaptive background job dan timeout yang telah diputuskan
pada audit Jadwal Pekerjaan.

### D-RK-07 - Readiness dan Data Belum Lengkap

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

Backend dan UI wajib membedakan:

- nilai belum diisi;
- nilai eksplisit nol;
- data tidak valid;
- data belum siap;
- hasil kosong karena filter;
- kebutuhan belum terjadwal;
- kegagalan request.

Readiness response minimal memuat:

```text
missing_volume
missing_price
invalid_coefficient
expansion_not_ready
incomplete_planned_allocation
timeline_stale
```

Setiap kategori membawa jumlah dan sumber masalah sampai level pekerjaan, item,
atau tabel/data asal yang relevan.

Aturan:

- volume belum diisi tidak boleh diam-diam dianggap volume nol;
- harga `null` berarti belum diisi, sedangkan `0.00` adalah nilai eksplisit yang
  valid;
- koefisien kosong/negatif/invalid dipisahkan dari koefisien nol yang memang
  sah menurut kontrak Template AHSP;
- expanded component pending, stale, parsial, atau gagal harus terlihat;
- total Rencana di bawah 100% menjadi Kebutuhan Belum Terjadwal, bukan error
  kalkulasi;
- timeline kanonik yang invalid memblokir mode periode, tetapi snapshot Total
  Kebutuhan tetap dapat ditampilkan jika data dasarnya siap;
- hasil kosong karena filter menampilkan no-result state beserta tindakan reset;
- kegagalan API menampilkan error state dan `Coba Lagi`, bukan tabel kosong atau
  nilai nol.

Perilaku UI:

- tampilkan banner readiness ringkas dan panel rincian;
- data yang dapat dihitung tetap ditampilkan;
- sediakan tautan menuju Volume Pekerjaan, Harga Items, Template AHSP, atau
  Jadwal Pekerjaan sesuai sumber masalah;
- total yang dipengaruhi data belum lengkap diberi label `Total sementara`;
- status loading, empty, filtered-empty, warning, dan error dibedakan secara
  visual, semantik, dan melalui `aria-live`.

Export tetap diizinkan. Sheet/halaman Ringkasan wajib mencantumkan status
`Lengkap` atau `Sementara`, jumlah masalah, sumber masalah, dan catatan bahwa
total belum final jika terdapat data material yang belum lengkap.

### D-RK-08 - Peran Page dan Penghapusan Mode Tahapan

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

Rekap Kebutuhan adalah read-only reporting consumer. Page tetap melakukan
agregasi, proyeksi, pengelompokan, filter, pencarian, readiness diagnostics, dan
export, tetapi tidak menjadi tempat input serta tidak menciptakan aturan bisnis
atau SSOT baru.

Kontrak sumber:

```text
Volume Pekerjaan
x Komponen expanded Template AHSP
x planned_proportion mingguan dari Jadwal Pekerjaan
x harga dasar dari Harga Items
= Rekap Kebutuhan
```

Rekap Kebutuhan boleh:

- menghitung quantity dan Total Harga Dasar dari sumber resmi;
- mengelompokkan menurut kategori, klasifikasi, sub-klasifikasi, pekerjaan,
  Minggu, Periode 4 Minggu, dan status alokasi;
- menerapkan search serta filter;
- menampilkan kelengkapan dan sumber masalah;
- menghasilkan PDF/XLSX.

Rekap Kebutuhan tidak boleh:

- mengedit volume, koefisien, komponen expanded, harga, conversion profile, atau
  planned progress;
- membuat distribusi waktu dari `PekerjaanTahapan` atau overlap tanggal;
- menentukan ulang harga kanonik dari conversion profile pada client;
- mengisi atau memperbaiki data sumber secara otomatis;
- menyimpan hasil turunan sebagai SSOT baru.

Mode/filter Tahapan sebagai jalur kalkulasi dihapus:

- parameter publik `mode=tahapan` dan `tahapan_id` dipensiunkan;
- cabang service, frontend, URL state, chip, dan export terkait dihapus setelah
  compatibility audit;
- endpoint lama dapat diberi deprecation warning sementara;
- tahapan hanya boleh menjadi label informatif turunan dan tidak mengubah
  quantity atau total.

Jika readiness menemukan masalah, user diarahkan ke page pemilik data:

- Volume Pekerjaan untuk volume;
- Template AHSP untuk komponen/koefisien;
- Harga Items untuk harga dan konversi;
- Jadwal Pekerjaan untuk alokasi Rencana dan struktur minggu.

### D-RK-09 - Konsistensi Search, Analytics, Total, dan Scope

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

Setiap request menghasilkan satu payload terfilter yang menjadi sumber bersama:

```text
dataset
├── rows atau buckets
├── summary
├── analytics
├── readiness
└── active_scope
```

Tabel, chart, total, readiness, dan export tidak boleh membangun atau menyimpan
versi data terpisah.

Search:

- berlaku pada Total Kebutuhan, Mingguan, Periode 4 Minggu, dan Belum
  Terjadwal;
- mencari kode dan uraian item;
- hanya menyaring penyajian dan tidak mengubah data sumber;
- bucket tanpa hasil boleh disembunyikan dengan informasi jumlah bucket yang
  tidak mempunyai hasil.

Analytics:

- mengikuti mode, granularitas, rentang, filter, search, dan status alokasi yang
  aktif;
- memakai Total Harga Dasar kanonik;
- mode satuan hanya mengubah label/presentasi dan tidak mengubah nilai chart;
- selalu menampilkan label scope yang sedang dianalisis.

Total:

1. `Total Scope Aktif` mengikuti seluruh filter/search/rentang yang terlihat.
2. `Total Kebutuhan Project` tetap tersedia sebagai konteks keseluruhan.

Kebutuhan Belum Terjadwal tidak dimasukkan ke bucket minggu/periode tertentu,
tetapi tetap terlihat pada klasifikasi dan total yang memang mencakup keseluruhan
Project.

Ketentuan teknis:

- frontend tidak menghitung ulang analytics/total dari DOM;
- backend mengirim `active_scope` kanonik yang juga dipakai export;
- request lama dibatalkan atau diabaikan dengan sequence token jika request baru
  telah dimulai;
- loading dan error state terikat pada request aktif;
- chart tidak boleh mempertahankan data scope sebelumnya setelah mode/filter
  berubah.

### D-RK-10 - Refresh dan Persistensi State

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

URL menjadi SSOT state penyajian yang memengaruhi hasil:

- mode Total/Mingguan/Periode 4 Minggu;
- minggu/periode awal dan akhir;
- kategori, klasifikasi, sub-klasifikasi, dan pekerjaan;
- status alokasi;
- search;
- mode satuan.

State visual sementara seperti modal terbuka, panel collapse, dan posisi scroll
tidak perlu disimpan pada URL.

Kontrak refresh:

1. batalkan atau abaikan request aktif;
2. bersihkan cache frontend;
3. minta dataset baru dari backend;
4. pertahankan URL, filter, mode, rentang, dan satuan aktif;
5. render ulang tabel, analytics, readiness, dan total dari response yang sama.

Ketentuan browser:

- perubahan state menggunakan History API;
- `popstate` memulihkan state dari URL;
- `Ctrl+R`, `F5`, dan refresh browser tidak dicegah;
- URL yang dibagikan menghasilkan scope yang sama bagi user yang memiliki akses.

Perubahan sumber data tidak memicu reload mendadak. Page menampilkan indikator:

```text
Data sumber berubah
[Muat Ulang Rekap]
```

Trigger mencakup perubahan Volume Pekerjaan, Template/expanded AHSP, Harga
Items, planned progress Jadwal Pekerjaan, dan struktur minggu.

Cache:

- signature backend mencakup seluruh sumber tersebut;
- refresh eksplisit melewati cache frontend;
- cache backend hanya dipakai jika signature masih cocok;
- timeout tidak boleh menjadi satu-satunya mekanisme invalidasi.

### D-RK-11 - Performa dengan Minimal Effort dan Dampak Maksimal

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

Perbaikan performa dibatasi pada perubahan sederhana yang sekaligus menjaga
konsistensi data:

1. Gunakan satu shared builder untuk Total Kebutuhan, Mingguan, Periode 4
   Minggu, analytics, readiness, validation, dan export.
2. Gunakan satu signature/revision cache yang mencakup volume, expanded AHSP,
   harga dasar, planned weekly progress, struktur pekerjaan, dan boundary
   minggu.
3. Ambil volume, expanded component, harga, dan planned progress melalui batch
   query; hindari query per pekerjaan atau per minggu.
4. Request hanya mengirim scope yang dipilih. Contoh Minggu 4-8 tidak perlu
   memuat seluruh timeline ke browser.
5. Pertahankan cache sederhana per Project/revision/scope dengan timeout sebagai
   fallback, bukan membuat cache bertingkat.
6. Background job hanya digunakan untuk export berat sesuai keputusan adaptive
   export; tampilan web tetap sinkron.

Belum diperlukan tanpa bukti benchmark:

- cache tiga lapis;
- incremental recomputation;
- background calculation untuk tampilan web;
- virtualisasi atau pagination kompleks;
- adaptive rendering client;
- infrastruktur optimasi baru.

Benchmark project kecil, menengah, dan besar dilakukan pada tahap pengujian.
Optimasi lanjutan hanya ditambahkan jika target response time atau penggunaan
resource terbukti gagal. Pendekatan ini tidak mengubah workflow client.

### D-RK-12 - Polishing UI/UX dan Aksesibilitas

**Keputusan diskusi 14 Juni 2026: DISETUJUI.**

Polishing tidak mengubah formula, SSOT, atau workflow bisnis.

Hierarki page:

1. Judul dan status readiness.
2. Tiga ringkasan utama:
   - Total Kebutuhan;
   - Rencana Telah Dialokasikan;
   - Kebutuhan Belum Terjadwal.
3. Mode utama:
   - Total Kebutuhan;
   - Mingguan;
   - Periode 4 Minggu.
4. Toolbar dan tabel.
5. Analisis/chart sebagai informasi sekunder.

Toolbar memuat Search, Filter, Status Alokasi, Satuan, Rentang, Refresh, dan
Export. Rentang hanya muncul pada mode waktu.

Tabel:

- kolom utama: Kode, Uraian, Satuan, Quantity, Harga Dasar Satuan, dan Total
  Harga Dasar;
- sticky header serta sticky konteks Kode/Uraian pada desktop;
- responsive table/card pada mobile;
- detail pekerjaan sumber dibuka melalui modal/drawer;
- pilihan kolom dihapus sampai terdapat kebutuhan nyata dan implementasi aktif.

Readiness dan state:

- banner `Lengkap` atau `Total sementara` dapat dibuka untuk melihat sumber
  masalah;
- empty state dibedakan untuk project kosong, volume belum tersedia, no-result,
  Rencana belum dialokasikan, dan kegagalan API;
- setiap state mempunyai tindakan yang relevan;
- loading, warning, empty, filtered-empty, dan error tidak boleh memakai
  tampilan yang sama.

Aksesibilitas:

- seluruh tombol ikon mempunyai accessible name;
- status dinamis memakai `aria-live` dan area dataset memakai `aria-busy`;
- tabel mempunyai caption sesuai mode/scope;
- modal mempunyai focus trap dan mengembalikan fokus ke trigger;
- filter pekerjaan memakai searchable combobox;
- segmented control mode mendukung keyboard;
- warna bukan satu-satunya pembeda status;
- dark mode, reduced motion, forced colors, dan zoom 200% dipertahankan/diuji.

Cleanup:

- hapus filter Tahapan dan hidden compatibility controls yang tidak lagi dipakai;
- hapus column visibility mati dan target toolbar yang tidak ada;
- satukan renderer timeline menjadi satu jalur bucket terpisah;
- hapus debug shortcut dan console noise production;
- konsolidasikan CSS bertahap tanpa refactor visual besar sekaligus;
- gunakan istilah Indonesia secara konsisten.

## 10. Rekomendasi Arsitektur

Buat satu builder:

```text
build_canonical_item_requirements(project, filters)
  -> kebutuhan dasar per pekerjaan dan item expanded

distribute_requirements_by_week(requirements, planned_weekly_progress)
  -> minggu
  -> item
  -> quantity
  -> cost
  -> pekerjaan breakdown
  -> unscheduled
```

Consumer:

- snapshot menjumlahkan seluruh minggu + unscheduled;
- timeline menampilkan bucket minggu;
- Periode 4 Minggu mengagregasi empat bucket minggu berurutan;
- tahapan mengelompokkan bucket/pekerjaan;
- validation membandingkan agregasi timeline dengan snapshot builder;
- export memakai payload yang sama;
- API weekly lama diganti menjadi serializer builder ini.

Tidak dibutuhkan migrasi database besar karena storage weekly, expanded details, volume, harga, dan conversion profile sudah tersedia.

## 11. Browser UAT Matrix

| Area | Skenario |
|---|---|
| Snapshot | project kosong, data lengkap, nested bundle, raw fallback |
| Timeline | distribusi mingguan tidak merata, Periode 4 Minggu, range, no schedule |
| Tahapan | 25%, 50%, 100%, split beberapa tahapan |
| Assignment | total <100%, =100%, >100% |
| Search | snapshot/timeline, kode, uraian, no result |
| Filter | kategori none/one/all, klasifikasi, sub, pekerjaan, tahapan |
| Unit | base/market, profile ada/tidak, override profile dihapus |
| Missing | volume null/0, harga null/0, expanded stale/failed |
| Mixed schedule | item sama pada pekerjaan scheduled dan unscheduled |
| Cache | ubah harga lalu buka timeline, ubah jadwal, ubah volume |
| Refresh | button, Ctrl+R, request gagal/lambat/berulang |
| Analytics | snapshot/timeline/filter/unit toggle |
| Export | full/range, base/market, unscheduled, PDF/Word/XLSX |
| Accessibility | keyboard, screen reader, modal, range controls, zoom 200% |
| Responsive | 320, 360, 576, 768, 1024, desktop |
| Theme | light, dark, reduced motion, forced colors |

## 12. Verifikasi Teknis

Hasil pemeriksaan:

- `python manage.py check`: **lulus**;
- `node --check rekap_kebutuhan.js`: **lulus**;
- `node --check rekap_kebutuhan_toolbar.js`: **lulus**;
- 38 test terkait API access, sync, cache header, page security, dan export: seluruh assertion **lulus**.

Command test berakhir exit code 1 hanya saat teardown karena database test masih dipakai dua session PostgreSQL lain. Ini masalah environment teardown, bukan kegagalan assertion.

Test yang belum tersedia:

- nested bundle pada weekly canonical;
- snapshot versus weekly total;
- mode tahapan tidak double proportion;
- unscheduled pada filter waktu;
- mixed scheduled/unscheduled item;
- timeline cache setelah harga berubah;
- search timeline;
- conversion parity base/market;
- timeline unit toggle;
- refresh event;
- hidden/dead filter and column controls;
- export unscheduled;
- completeness/readiness warning;
- responsive dan screen reader.

Audit visual browser, output file export aktual, dan screen-reader UAT belum dijalankan.

## 13. Keputusan Audit

Snapshot Rekap Kebutuhan mempunyai fondasi agregasi item yang cukup baik: expanded storage digunakan, bundle multiplier diperhitungkan, harga dasar dibaca dari SSOT Harga Items, dan export snapshot memakai service yang sama.

Bagian yang belum dapat dipercaya adalah dimensi waktu. Sistem mempunyai dua formula:

1. planned proportion mingguan sebagai storage kanonik;
2. proporsi tahapan dan distribusi overlap hari sebagai formula page.

Selama keduanya hidup bersamaan, angka Rekap Kebutuhan per periode dapat berbeda dari Jadwal Pekerjaan. Perbaikan utama adalah menghapus formula waktu kedua dan menjadikan satu builder weekly-expanded sebagai SSOT seluruh consumer.

Sesudah itu, fokus berikutnya:

1. scheduled/unscheduled pada level quantity, bukan boolean item;
2. unit conversion sebagai presentasi yang menjaga total;
3. filter dan mode yang benar-benar tersedia bagi user;
4. parity layar, analytics, dan export;
5. completeness/readiness diagnostics;
6. penghapusan dead compatibility UI.

---

## 14. Verifikasi Independen (Claude, 13 Juni 2026)

Temuan diperiksa ulang terhadap kode kerja. Yang diverifikasi langsung: **RK-01, RK-02, RK-03, RK-04, RK-05, RK-20 — semuanya valid, tidak ada false positive.** Sisanya konsisten dengan kode/struktur. Dokumen ini sangat matang dari sisi keputusan owner (D-RK-01..12 lengkap dengan kontrak); verifikasi memastikan temuan teknis yang menjadi dasar keputusan itu nyata.

### 14.1 Verdict per temuan (yang diverifikasi langsung)

| Temuan | Verdict | Bukti verifikasi |
|---|---|---|
| RK-01 Timeline tak pakai weekly canonical | **DIKONFIRMASI** | `compute_kebutuhan_timeline` (`services.py:2907`) distribusi via `PekerjaanTahapan` + tanggal tahapan (`:3093-3115, 3172-3184`), bukan `PekerjaanProgressWeekly.planned_proportion`. (Catatan: komponennya sudah `DetailAHSPExpanded` `:3056` — yang salah hanya distribusi WAKTU, bukan agregasi.) |
| RK-02 Proporsi tahapan dobel | **DIKONFIRMASI (khusus mode tahapan)** | `:3144` `proporsi_multiplier = proporsi_volume/100` → `:3158` `base_quantity = koef × volume × proporsi_multiplier`, lalu `:3175-3176` `assignment_quantity = base_quantity × (proporsi/100)` lagi. 50% → 25%. Mode `all` pakai `1.0` (`:3008`) jadi tak terdampak. |
| RK-03 Unscheduled dihitung penuh (snapshot) | **DIKONFIRMASI** | `_build_time_scope_multiplier` (`:332`) `:380-381` `if totals[pk]==0: result[pk]=Decimal('1.0')` → pekerjaan tanpa assignment masuk penuh ke periode mana pun. |
| RK-04 Cache timeline stale setelah harga | **DIKONFIRMASI** | `_kebutuhan_signature` (`:101-118`) memuat raw/expanded/volume/pekerjaan/tahapan/assignment — **tanpa `HargaItemProject`**. Timeline pakai namespace `rekap_kebutuhan_timeline:` (`:2929`). |
| RK-05 Weekly endpoint baca raw | **DIKONFIRMASI** | `api_rekap_kebutuhan_weekly` (`views_api.py:6960`) `:7114` `pkj.detail_list.all()` = raw `DetailAHSPProject` (related_name `models.py:419`), bukan `DetailAHSPExpanded` → nested bundle tak terhitung. |
| RK-20 Total proporsi tak dijamin 100% | **DIKONFIRMASI** | `models.py:991` `# self.validate_total_proporsi()` di-comment; fungsi ada di `:993`. |

### 14.2 Penajaman bukti

- **RK-02 subsumed oleh keputusan D-RK-08.** Double-proportion hanya pada `mode=tahapan`. Karena D-RK-08 memutuskan menghapus mode tahapan sebagai jalur kalkulasi, fix RK-02 ikut selesai saat tahapan dihapus — tidak perlu menambal rumus lama. Pastikan saja penghapusan tahapan menyeluruh (service + URL + chip + export).

- **RK-01 lebih sempit dari kesan "rewrite".** Timeline sudah memakai `DetailAHSPExpanded` untuk komponen (`:3056`) dengan raw fallback — fondasi agregasi sudah benar. Yang perlu diganti hanya **sumber distribusi waktu**: dari `PekerjaanTahapan`/overlap-hari ke `PekerjaanProgressWeekly.planned_proportion`. Ini menguatkan rekomendasi arsitektur §10 (satu `distribute_requirements_by_week`).

- **RK-04/RK-03 = pola sistemik "signature lupa harga".** Omisi `HargaItemProject` di cache signature muncul berulang: RK-04 (`_kebutuhan_signature`), RR-11 (Rekap RAB), KS-03 (chart-data Kurva S). Rekomendasi: **satu helper signature bersama** yang selalu menyertakan harga + markup, dipakai semua consumer.

### 14.3 Catatan konsistensi lintas-page (page ke-8, consumer akhir)

Rekap Kebutuhan adalah consumer paling hilir — bergantung pada Volume, Template AHSP/expanded, Harga Items, dan Jadwal. Semua tema sistemik bermuara di sini:
- **Dua formula distribusi waktu** (tahapan vs weekly canonical) = manifestasi langsung dari isu SSOT Jadwal (JDW). RK-01 dan §0 dokumen sudah mengikat ke keputusan Jadwal.
- **Cache signature tanpa `HargaItemProject`** (RK-04 = RR-11 = KS-03).
- **`str(e)` bocor** (RK-23 = TA-08/HI/RA/RR).
- **localStorage conversion tidak project-scoped** (RK-10 = HI-08).
- **Unit conversion bisa ubah total** (RK-09 = HI-03 family) — diselesaikan oleh kontrak D-RK-03 (total dari backend, client tidak hitung ulang).
- **Missing-vs-zero** (RK-19 = D-04 Volume) — diselesaikan D-RK-07 readiness.

### 14.4 Kalibrasi prioritas

P0 (RK-01..RK-05) tepat. Catatan:
- **RK-03 quick win** (multiplier unscheduled = 0, bukan 1.0 — satu baris di `:380-381`).
- **RK-20 quick win** (aktifkan validasi atau tegaskan kebijakan partial → masuk Belum Terjadwal per D-RK-02).
- **RK-04 quick win** (tambah `HargaItemProject` ke signature; sejalan fix bersama lintas-page).
- **RK-01 + RK-05** = unit kerja utama: satu `build_canonical_item_requirements` + `distribute_requirements_by_week` dari `planned_proportion` berbasis expanded (§10). Ini menutup RK-01, RK-02 (via D-RK-08), dan RK-05 sekaligus.

Catatan proses: keputusan owner D-RK-01..12 sangat lengkap dan kontraknya koheren dengan akar masalah yang terverifikasi (dua formula waktu, signature harga, scheduled-by-quantity). Arsitektur target (satu builder weekly-expanded) tepat dan tidak butuh migrasi DB besar karena seluruh storage sudah ada.
