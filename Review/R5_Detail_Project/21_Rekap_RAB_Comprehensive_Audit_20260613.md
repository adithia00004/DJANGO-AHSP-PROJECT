# Audit Komprehensif Page Rekap RAB

**Tanggal audit:** 13 Juni 2026  
**Target:** `/detail_project/<project_id>/rekap-rab/`  
**Objek:** current working tree pada saat audit  
**Status:** **BELUM PRODUCTION-READY - terdapat risiko XSS, inkonsistensi markup, dan kesalahan dokumen print**

## 1. Ringkasan Eksekutif

Rekap RAB adalah consumer akhir dari alur:

```text
List Pekerjaan
  -> Volume Pekerjaan
  -> Template AHSP / expanded components
  -> Harga Items
  -> Markup project/override pekerjaan
  -> Rekap RAB
  -> PPN dan pembulatan
```

Page menyediakan:

- hierarki Klasifikasi -> Sub-klasifikasi -> Pekerjaan;
- mode expand/collapse;
- mode subtotal;
- mode compact;
- pencarian dan sorting;
- pengaturan PPN dan pembulatan;
- refresh;
- export XLSX, PDF, Word, dan JSON;
- print beserta lembar pengesahan.

Fondasi yang sudah baik:

- page dan API utama owner-scoped;
- perhitungan web dan adapter export sama-sama memakai `compute_rekap_for_project()`;
- harga satuan final memakai `G`, yaitu biaya komponen setelah markup;
- total pekerjaan memakai harga satuan final x volume;
- markup override pekerjaan didukung;
- PPN dan basis pembulatan disimpan per project;
- export entitlement telah dibatasi;
- tersedia sticky header, horizontal scroll, keyboard sorting, live region, dark mode, reduced motion, dan print layout;
- perubahan pekerjaan, volume, AHSP, dan harga dipantau oleh sync indicator.

Masalah utama:

1. Nama klasifikasi, sub-klasifikasi, pekerjaan, dan kode dimasukkan ke `innerHTML` tanpa escaping. Data tersimpan dapat menjalankan HTML/script pada browser.
2. Project tanpa row `ProjectPricing` dihitung dengan markup 0%, sedangkan API/UI menyatakan default 10%.
3. Modul print membaca angka pembulatan sebagai total dasar lalu menghitung PPN kembali, sehingga ringkasan print dapat salah.
4. Metadata print dapat memakai nilai contoh palsu seperti Jakarta, Dinas PUPR, dan APBD.
5. Pencarian mengubah Total, PPN, Grand Total, dan Pembulatan menjadi total hasil filter tanpa label yang menjelaskan perubahan scope.
6. Perubahan PPN/pembulatan autosave secara diam-diam tanpa validasi response, status simpan, rollback, atau perlindungan ketika user segera meninggalkan page.
7. Volume kosong, volume eksplisit nol, harga kosong, dan hasil perhitungan valid nol tidak dapat dibedakan.

## 2. Kontrak Produk dan SSOT

Kontrak perhitungan yang direkomendasikan:

| Nilai | Nama kanonik | Formula / sumber |
|---|---|---|
| Biaya komponen sebelum markup | `component_cost_before_markup` | Sum koefisien x harga item |
| Markup efektif | `effective_markup_percent` | Override pekerjaan atau default project |
| Nilai markup | `markup_amount` | Biaya komponen x markup |
| Harga satuan final | `unit_price_after_markup` | Biaya komponen + markup |
| Volume pekerjaan | `job_volume` | `VolumePekerjaan.quantity` |
| Total pekerjaan | `job_total_cost` | Harga satuan final x volume |
| Total sebelum pajak | `project_subtotal_before_tax` | Sum seluruh total pekerjaan |
| PPN | `tax_amount` | Subtotal x PPN project |
| Grand total | `grand_total_before_rounding` | Subtotal + PPN |
| Total dibulatkan | `rounded_grand_total` | Grand total dibulatkan sesuai basis project |

SSOT yang seharusnya berlaku:

- komponen dan koefisien: Template AHSP;
- komponen expanded: storage turunan yang mempunyai status readiness;
- harga dasar: Harga Items;
- volume: Volume Pekerjaan;
- markup default: `ProjectPricing.markup_percent`;
- markup khusus: `Pekerjaan.markup_override_percent`;
- PPN dan pembulatan: `ProjectPricing`;
- formula Rekap RAB: satu calculation service kanonik;
- web, print, dan seluruh format export: consumer calculation result yang sama.

## 3. Ruang Lingkup Implementasi

| Area | Implementasi |
|---|---|
| Page view | `detail_project.views.rekap_rab_view` |
| Template | `detail_project/templates/detail_project/rekap_rab.html` |
| JavaScript | `detail_project/static/detail_project/js/rekap_rab.js` |
| CSS | `detail_project/static/detail_project/css/rekap_rab.css` |
| Print JS | `detail_project/static/detail_project/js/print/RekapRABPrint.js` |
| Print CSS | `detail_project/static/detail_project/css/print/rekap-rab-print.css` |
| Calculation | `detail_project.services.compute_rekap_for_project` |
| Rekap API | `detail_project.views_api.api_get_rekap_rab` |
| Pricing API | `detail_project.views_api.api_project_pricing` |
| Export adapter | `detail_project.exports.rekap_rab_adapter.RekapRABAdapter` |
| Export orchestration | `detail_project.exports.export_manager.ExportManager` |

Data dimuat melalui tiga request paralel:

1. tree List Pekerjaan;
2. row perhitungan Rekap RAB;
3. project pricing.

## 4. Audit Per Mode dan Elemen Interaktif

### 4.1 Initial Load

**Status:** Fungsional bersyarat.

- loading state tersedia;
- tiga endpoint dipanggil paralel;
- pricing server diprioritaskan dibanding localStorage;
- error state mempunyai tombol reload;
- tidak ada bootstrap data dari server-side render;
- kegagalan satu endpoint utama menggagalkan seluruh page;
- refresh berulang tidak membatalkan request sebelumnya.

### 4.2 Mode Hierarki Default

**Status:** Fungsional, tetapi tidak aman.

- klasifikasi dan sub dapat dibuka/tutup;
- state expanded disimpan per project di localStorage;
- subtotal klasifikasi/sub dihitung dari child pekerjaan;
- label dinamis dirender melalui `innerHTML` tanpa escaping.

### 4.3 Expand dan Collapse

**Status:** Baik bersyarat.

- kontrol mouse dan keyboard tersedia;
- expand/collapse dinonaktifkan ketika search aktif;
- state disimpan;
- tombol print mencari ID `btn-expand-all`, sedangkan page memakai `btn-expand`;
- label tombol bercampur Indonesia dan Inggris.

### 4.4 Mode Subtotal

**Status:** Fungsional.

- row pekerjaan disembunyikan;
- subtotal dan grand total tetap memakai seluruh pekerjaan;
- state disimpan di localStorage;
- tombol aktif hanya dibedakan secara visual dan tidak memperbarui `aria-pressed`.

### 4.5 Mode Compact

**Status:** Fungsional.

- density table berubah;
- state disimpan;
- live region mengumumkan perubahan;
- tidak ada `aria-pressed`.

### 4.6 Search

**Status:** Tidak sesuai konteks total project.

- mencari klasifikasi, sub, uraian pekerjaan, dan kode;
- hasil diberi highlight;
- parent yang cocok membawa child terkait;
- expand/collapse dinonaktifkan saat search.

Namun footer dihitung ulang hanya dari pekerjaan yang cocok. Akibatnya angka yang sebelumnya berarti total project berubah menjadi total hasil pencarian tanpa perubahan label.

### 4.7 Sorting

**Status:** Fungsional bersyarat.

- Volume, Harga Satuan, dan Total dapat diurutkan;
- mendukung click, Enter, dan Space;
- `aria-sort` diperbarui;
- urutan hanya berubah di dalam sub-klasifikasi;
- sorting tidak dinyatakan sebagai mode sementara;
- tidak ada indikator bahwa urutan asli pekerjaan sedang disembunyikan.

### 4.8 PPN

**Status:** Berisiko kehilangan perubahan.

- input dibatasi 0-100 pada HTML dan backend;
- backend menyimpan dua desimal;
- perubahan langsung memengaruhi footer;
- POST dilakukan debounce 250 ms.

Kelemahan:

- browser dapat sementara menerima nilai invalid;
- response status/body tidak diperiksa;
- tidak ada saving/saved/failed indicator;
- tidak ada rollback;
- user dapat meninggalkan page sebelum request dikirim atau selesai;
- perubahan parameter finansial tidak mempunyai audit trail.

### 4.9 Pembulatan

**Status:** Fungsional bersyarat.

- pilihan Rp1, Rp1.000, Rp10.000, dan Rp100.000;
- disimpan pada `ProjectPricing`;
- frontend dan adapter export memakai pembulatan terdekat.

Kelemahannya sama dengan autosave PPN. Selain itu backend menerima integer positif apa pun, sementara UI hanya menawarkan empat kebijakan.

### 4.10 Refresh

**Status:** Fungsional bersyarat.

- data dimuat ulang tanpa reload page penuh;
- tidak ada `AbortController` atau request token;
- klik berulang dapat membuat response lama menimpa response baru;
- tombol tidak disabled selama loading;
- state loading awal mengacu pada node yang sudah dilepas.

### 4.11 Empty State

**Status:** Implementasi ganda dan tidak terhubung.

Template mempunyai empty state informatif dengan link ke List Pekerjaan dan Volume Pekerjaan. JavaScript tidak pernah menampilkannya dan hanya merender row `Tidak ada data`.

### 4.12 Export

**Status:** Calculation cukup selaras, orchestration terlalu kompleks.

- adapter menggunakan calculation service yang sama;
- footer export memakai PPN dan basis pembulatan project;
- XLSX/PDF/Word dibatasi entitlement;
- export mempunyai lock terhadap double click.

Kelemahan:

- listener export dibuat di JS utama lalu tombol di-clone dan di-bind ulang oleh inline script;
- SheetJS eksternal dan `ExcelExporter.js` tetap dimuat walaupun export final memakai server;
- fallback tombol XLSX dapat mengunduh CSV dengan nama/ekspektasi Excel;
- error endpoint mengembalikan detail exception;
- format angka export membulatkan harga dan total ke nol desimal, sementara nilai kanonik dua desimal;
- export belum membawa warning data tidak lengkap/readiness.

### 4.13 Print

**Status:** Tidak dapat dipercaya sebelum diperbaiki.

Print membuat:

- header RAB;
- informasi proyek;
- tabel hierarki;
- ringkasan total;
- lembar pengesahan;
- rekap per klasifikasi.

Tetapi metadata dan ringkasan total dapat salah. Detail dibahas pada temuan RR-03 dan RR-04.

### 4.14 Responsive

**Status:** Baik bersyarat.

- table mempunyai horizontal scroll;
- beberapa cell disembunyikan pada breakpoint kecil;
- total tetap terlihat;
- toolbar membungkus.

Risiko:

- class responsive berada pada cell body, sedangkan header tidak selalu memakai class hide yang sama;
- pada ukuran tertentu header dan body dapat tidak sejajar secara semantik;
- informasi Kode, Satuan, Volume, dan Harga dapat hilang sekaligus, menyisakan uraian dan total tanpa affordance detail.

### 4.15 Accessibility

**Status:** Fondasi baik, belum lengkap.

Yang sudah baik:

- search mempunyai accessible label;
- toolbar mempunyai role dan label;
- live region tersedia;
- sort keyboard-accessible;
- toggle keyboard-accessible;
- sticky table region dapat difokuskan;
- reduced motion didukung.

Kekurangan:

- table memakai `role=row` dan `aria-level` seperti tree tetapi table bukan `treegrid`;
- active state Subtotal/Compact tidak memakai `aria-pressed`;
- status save PPN/pembulatan tidak diumumkan;
- scope total hasil filter tidak diumumkan;
- hidden responsive cells dapat menghilangkan konteks penting;
- print dan export error masih mengandalkan console/alert.

## 5. Temuan Audit

### RR-01 - CRITICAL - Stored XSS pada Seluruh Label Hierarki

`highlightMatch()` mengembalikan HTML, lalu nama klasifikasi, sub, uraian pekerjaan, dan kode dimasukkan ke `innerHTML` pada `rekap_rab.js:82-87` dan `:323-343`.

Escaping hanya diterapkan sebagian pada atribut quote, bukan pada konten HTML.

**Dampak:**

- data seperti nama pekerjaan yang berisi markup dapat menjalankan HTML/script;
- payload tersimpan dapat aktif setiap kali Rekap RAB dibuka;
- search highlight tidak menjadi penyebab tunggal karena jalur tanpa search juga memakai `innerHTML`.

**Rekomendasi:** bangun node memakai `textContent`; untuk highlight, pecah text menjadi text node dan elemen `<mark>/<span>` tanpa menginterpretasikan input sebagai HTML.

### RR-02 - CRITICAL - Default Markup 0% dan 10% Tidak Konsisten

`compute_rekap_for_project()` memakai `Decimal("0")` jika `ProjectPricing` belum ada. API kemudian mengubah `markup_eff` menjadi 10%, tetapi tidak menghitung ulang `F`, `G`, dan `total` karena field tersebut sudah tersedia.

**Dampak:**

- label/meta dapat menyatakan 10%;
- harga satuan dan total tetap dihitung 0%;
- Rincian AHSP, Rekap RAB, dan export dapat sulit direkonsiliasi.

**Rekomendasi:** tetapkan default 10.00% pada satu helper/service dan jangan memperbaiki field calculation secara parsial di controller.

### RR-03 - CRITICAL - Ringkasan Print Dapat Menghitung PPN Dua Kali

`extractSummaryFromTfoot()` mencari cell pertama dengan class `text-end`. Cell tersebut dapat berupa label tanpa angka. Ketika hasil nol, fungsi mengambil cell terakhir pada footer, yaitu nilai yang sudah dibulatkan, lalu memperlakukannya sebagai `totalD` dan menghitung PPN kembali.

**Dampak:** total, PPN, grand total, dan pembulatan pada hasil print dapat salah walaupun tabel layar benar.

**Rekomendasi:** baca nilai dari ID eksplisit `ft-total-d`, `ft-ppn`, `ft-grand`, dan `ft-rounded`, atau lebih baik gunakan state calculation terstruktur.

### RR-04 - HIGH - Print Dapat Mencetak Identitas Proyek Palsu

Template memakai field yang tidak ada:

- `project.nama_project`;
- `project.kode_project`;
- `project.lokasi`;
- `project.tahun_anggaran`.

Model aktual memakai `nama`, `lokasi_project`, dan `tahun_project`. Print module juga tidak memakai dataset tersebut dan menyediakan fallback:

- `Pembangunan Gedung Serbaguna`;
- `Dinas PUPR (Pemprov DKI Jakarta)`;
- `Jakarta`;
- `APBD`.

**Dampak:** dokumen formal dapat membawa nama pemilik, lokasi, sumber dana, dan tahun yang tidak berasal dari project.

**Rekomendasi:** kirim metadata benar dari Django, baca dataset secara eksplisit, dan gunakan `-` untuk data kosong. Jangan pernah memakai data contoh dalam dokumen produksi.

### RR-05 - HIGH - Search Mengubah Arti Total Project

`render()` menghitung footer dari `computeTotalsFiltered()`. Saat search aktif, Total Sebelum Pajak, PPN, Grand Total, dan Pembulatan berubah menjadi subset hasil pencarian.

**Dampak:** user dapat mengira anggaran project berubah hanya karena mengetik kata pencarian.

**Rekomendasi:** footer utama selalu menampilkan total seluruh project. Jika diperlukan, tampilkan ringkasan kedua bernama `Total hasil filter`.

### RR-06 - HIGH - Autosave PPN dan Pembulatan Tidak Memastikan Data Tersimpan

POST pricing tidak memeriksa `res.ok`, tidak membaca error, dan tidak menampilkan status. Nilai juga disimpan ke localStorage sebelum server mengonfirmasi.

**Dampak:**

- UI menampilkan nilai baru yang mungkin tidak tersimpan;
- reload berikutnya dapat mengembalikan nilai lama;
- user tidak mengetahui kegagalan jaringan/validasi;
- perubahan terakhir dapat hilang saat navigasi cepat.

**Rekomendasi:** gunakan explicit save atau autosave state `Menyimpan / Tersimpan / Gagal`, flush saat blur/navigation, validasi response, dan rollback pada failure.

### RR-07 - HIGH - Missing Data dan Nilai Nol Tidak Dapat Dibedakan

Service memakai:

```text
harga kosong -> 0
volume kosong -> 0
volume eksplisit nol -> 0
```

Page hanya menampilkan angka nol tanpa status penyebab.

**Dampak:** RAB parsial dapat terlihat sebagai RAB lengkap bernilai nol.

**Rekomendasi:** sertakan diagnostic per pekerjaan:

- `volume_missing`;
- `price_missing_count`;
- `detail_missing`;
- `expanded_not_ready`;
- `explicit_zero`;
- `calculation_ready`.

### RR-08 - HIGH - Readiness Expanded Storage Tidak Menjadi Gate/Warning

Rekap memakai expanded rows jika tersedia dan fallback raw jika tidak. Page tidak menunjukkan apakah expansion:

- siap;
- stale;
- pending;
- gagal;
- parsial.

**Dampak:** nested bundle yang gagal dapat menghasilkan total yang tampak final.

**Rekomendasi:** perhitungan tetap dapat dibuka untuk diagnosis, tetapi label `Data belum lengkap` wajib tampil dan warning harus ikut export.

### RR-09 - HIGH - Harga Satuan Mempunyai Fallback Semantik yang Salah

Frontend memilih:

```text
G -> harga_satuan -> HSP -> unit_price
```

Dalam service saat ini `HSP` dan `unit_price` berarti biaya sebelum markup. Jika `G` hilang, frontend diam-diam menampilkan harga pra-markup sebagai harga final.

**Rekomendasi:** gunakan satu field wajib `unit_price_after_markup`; jika tidak tersedia, tampilkan error contract, bukan fallback ke field dengan arti berbeda.

### RR-10 - HIGH - Perubahan Parameter Finansial Tidak Mempunyai Audit Trail

PPN, pembulatan, dan markup project memengaruhi dokumen anggaran. Endpoint menyimpan perubahan tanpa event yang mencatat user, nilai lama, nilai baru, dan timestamp.

### RR-11 - MEDIUM - Cache Tidak Memasukkan Timestamp Harga Item

Signature cache rekap memasukkan raw detail, expanded detail, volume, pekerjaan, pricing, dan source. Timestamp `HargaItemProject` tidak dimasukkan.

Save normal dapat menginvalidasi cache secara eksplisit, tetapi perubahan melalui admin, import, bulk operation, atau jalur baru berisiko menyisakan cache lama.

**Rekomendasi:** masukkan aggregate timestamp harga ke signature sebagai pertahanan berlapis.

### RR-12 - MEDIUM - Refresh Mempunyai Race Condition

Tidak ada cancellation atau sequence token. Response request pertama yang lambat dapat menimpa request kedua yang lebih baru.

### RR-13 - MEDIUM - Empty State Informatif Tidak Pernah Dipakai

`#rab-empty` mempunyai CTA lintas-page yang benar, tetapi JS hanya membuat row kosong sederhana.

### RR-14 - MEDIUM - Export/Print Listener Ditumpuk lalu Dihapus dengan Cloning

JS utama mengikat export dan print. Inline script kemudian clone-replace tombol export, sedangkan print module clone-replace tombol print.

**Dampak:** ownership event tidak jelas, referensi tombol dapat stale, dan perubahan urutan script mudah menimbulkan aksi ganda atau mati.

**Rekomendasi:** satu initializer per aksi tanpa inline script dan tanpa clone untuk menghapus listener.

### RR-15 - MEDIUM - Dependency SheetJS Eksternal Tidak Diperlukan dan Tanpa SRI

Page memuat SheetJS CDN serta exporter client-side, tetapi export final menggunakan server `ExportManager`.

**Dampak:** menambah bobot, dependency jaringan, supply-chain surface, dan failure mode.

### RR-16 - MEDIUM - Fallback Excel Sebenarnya Menghasilkan CSV

Jika unified exporter tidak tersedia, click `Export Excel` menjalankan `exportCSV()`.

**Dampak:** label aksi dan tipe file tidak sesuai.

### RR-17 - MEDIUM - Export Error Mengekspos Exception Internal

Seluruh endpoint export mengirim `str(e)` ke client dan mencetak traceback langsung.

**Rekomendasi:** log terstruktur server-side dengan correlation ID dan kirim pesan generik.

### RR-18 - MEDIUM - Print Mereinjeksi Text sebagai HTML

Metadata dan nama klasifikasi diekstrak memakai `textContent`, kemudian dimasukkan kembali melalui template `innerHTML`.

Jika RR-01 diperbaiki dan data berisi literal `<...>`, print module dapat mengaktifkannya kembali.

### RR-19 - MEDIUM - Presisi Display/Export Tidak Sesuai Nilai Kanonik

Keputusan sebelumnya menetapkan harga item dua desimal. Table web menampilkan dua desimal, tetapi adapter export memformat harga dan jumlah dengan nol desimal.

**Rekomendasi:** nilai kanonik tetap dua desimal. Format rupiah penuh hanya sebagai presentation rule yang dinyatakan dan diterapkan konsisten.

### RR-20 - MEDIUM - Tidak Ada Concurrency Guard pada Pricing

Dua tab dapat mengubah PPN/pembulatan; last write wins tanpa version check atau warning.

### RR-21 - MEDIUM - Sorting Mengubah Urutan Child Secara In-place

Array pekerjaan diurutkan langsung. Reset sort menghilangkan indikator tetapi tidak menjamin kembali ke urutan awal tanpa reload.

### RR-22 - LOW - State Mode Tidak Lengkap untuk Screen Reader

Subtotal dan Compact memakai class `active`, tetapi tidak memperbarui `aria-pressed`.

### RR-23 - LOW - Terminologi Tidak Konsisten

Contoh:

- `Expand All`, `Collapse All`, `Compact`, dan `Toggle subtotal only`;
- `Total Proyek (D)` pada CSV/print;
- `Total Biaya Langsung` pada export, padahal harga sudah mencakup markup;
- `HSP`, `unit_price`, dan `G` membawa arti berbeda.

### RR-24 - LOW - Kode Legacy dan Duplikasi Print/Export Masih Aktif

Terdapat:

- exporter Rekap RAB lama;
- adapter/export manager baru;
- export client-side CSV;
- ExcelExporter;
- SheetJS;
- CSS print umum;
- CSS print khusus;
- style print yang diinjeksi JavaScript.

Ini memperbesar risiko drift dan membuat ownership sulit ditelusuri.

### RR-25 - LOW - Error UI Dibangun dengan `innerHTML`

Saat ini `e.message` berasal dari pesan internal yang tetap, sehingga eksploitasi langsung terbatas. Pola tersebut tetap tidak aman bila pesan server kelak diteruskan.

## 6. Penilaian UI/UX

### Yang Sudah Baik

1. Hierarki RAB mudah dipindai.
2. Expand/collapse dan subtotal membantu dataset panjang.
3. Search dan highlight tersedia.
4. Sorting memakai indikator accessible.
5. Footer memperlihatkan PPN, grand total, dan pembulatan dalam satu konteks.
6. Table responsive dan sticky header tersedia.
7. Live announcement tersedia.
8. Dark mode, reduced motion, dan print stylesheet didukung.
9. Empty state yang dirancang sudah mengarahkan ke page sumber.
10. Export dikelompokkan dalam satu dropdown dan mempunyai entitlement gate.

### Perbaikan UX Prioritas

1. Jangan biarkan search mengubah total project.
2. Tampilkan status kelengkapan data sebelum angka dianggap final.
3. Tampilkan status simpan PPN/pembulatan.
4. Bedakan `0 valid` dari `belum diisi`.
5. Perlihatkan markup efektif/override minimal melalui tooltip atau detail row.
6. Gunakan empty state yang sudah tersedia.
7. Hilangkan nilai contoh pada print.
8. Satukan bahasa dan label.

## 7. Konsistensi dengan Page Sebelumnya

### List Pekerjaan

- hierarki dan identitas pekerjaan berasal dari tree;
- perubahan source REF/MOD/CUS harus menginvalidasi calculation;
- pekerjaan tanpa detail/volume harus diberi diagnostic.

### Volume Pekerjaan

- volume merupakan SSOT;
- missing dan explicit zero harus dibedakan;
- perubahan source yang menghapus volume harus terlihat di Rekap RAB.

### Template AHSP

- nested bundle dan expansion readiness harus dibawa ke consumer;
- perubahan komponen harus menginvalidasi rekap;
- Rekap RAB tidak boleh mencoba menafsirkan ulang bundle.

### Harga Items

- harga dasar dua desimal merupakan SSOT;
- konversi hanya helper input;
- override manual menghapus profil konversi;
- missing price harus dilaporkan, bukan diam-diam nol.

### Rincian AHSP

- `G` adalah harga satuan final setelah markup;
- override per pekerjaan harus dipertahankan;
- default markup harus tunggal;
- Rekap RAB adalah tempat yang tepat untuk volume, PPN, dan pembulatan.

## 8. Prioritas Remediasi

| Urutan | Item | Gate |
|---|---|---|
| P0 | RR-01 tutup stored XSS | Wajib sebelum production |
| P0 | RR-02 satukan default markup | Wajib untuk integritas angka |
| P0 | RR-03 perbaiki calculation print | Wajib sebelum print dipakai |
| P0 | RR-04 hapus metadata print palsu | Wajib untuk dokumen resmi |
| P0 | RR-05 total project tidak berubah oleh search | Wajib untuk mencegah salah tafsir |
| P1 | RR-06 autosave pricing terkonfirmasi | Data integrity |
| P1 | RR-07/RR-08 completeness dan readiness | Reliability |
| P1 | RR-09 kontrak harga final tunggal | SSOT |
| P1 | RR-10 audit trail finansial | Governance |
| P1 | RR-11 sampai RR-20 | Cache, export, concurrency, security |
| P2 | RR-21 sampai RR-25 | Accessibility dan maintainability |

## 9. Keputusan Produk yang Perlu Dikonfirmasi

### D-RR-01 - Total Saat Search

**Rekomendasi:** footer utama selalu total seluruh project. Tambahkan `Total hasil filter` hanya jika user memang membutuhkan subtotal pencarian.

### D-RR-02 - Missing Data

**Rekomendasi:** Rekap tetap dapat dibuka untuk diagnosis, tetapi tampilkan banner:

```text
RAB belum lengkap:
- 3 pekerjaan belum mempunyai volume
- 5 item belum mempunyai harga
- 1 pekerjaan menunggu rebuild AHSP
```

Export tetap boleh dilakukan bila dibutuhkan, tetapi wajib membawa catatan warning.

### D-RR-03 - Penyimpanan PPN dan Pembulatan

**Rekomendasi:** tetap autosave, tetapi simpan saat `change/blur`, tampilkan status, dan sediakan retry. Tidak perlu tombol Save global.

### D-RR-04 - Presisi

**Rekomendasi:** harga satuan dan total kanonik dua desimal. Dokumen dapat menampilkan rupiah penuh bila presentation policy disepakati, tetapi hasil raw/JSON tetap dua desimal.

### D-RR-05 - Metadata Pengesahan

**Rekomendasi:** identitas penandatangan harus berasal dari konfigurasi project/export. Field yang kosong ditampilkan kosong atau `-`, bukan contoh fiktif.

### D-RR-06 - Visibilitas Markup

**Rekomendasi:** Rekap tidak perlu menambah kolom markup permanen. Tampilkan indikator/tooltip pada pekerjaan yang memakai override, beserta nilai efektifnya.

## 10. Browser UAT Matrix

| Area | Skenario |
|---|---|
| Initial | project kosong, data lengkap, satu API gagal, jaringan lambat |
| Hierarki | expand/collapse mouse dan keyboard, persistence |
| Mode | detail, subtotal, compact, kombinasi mode |
| Search | klasifikasi, sub, uraian, kode, no result, clear |
| Sorting | asc, desc, reset, search + sort, subtotal + sort |
| Calculation | markup default, override, volume/harga desimal, PPN, rounding |
| Missing | volume null, volume 0, harga null, harga 0, detail kosong |
| Bundle | direct, nested, stale, failed, partial expansion |
| Pricing | input valid/invalid, offline, server 400/500, navigasi cepat, dua tab |
| Refresh | click berulang, response out-of-order |
| Export | XLSX/PDF/Word/JSON, entitlement, rekonsiliasi layar |
| Print | metadata, subtotal, grand total, filter aktif, collapsed state, pengesahan |
| Security | payload HTML pada klasifikasi/sub/pekerjaan/kode |
| Accessibility | screen reader, keyboard, focus, aria state, zoom 200% |
| Responsive | 320, 360, 576, 768, 1024, desktop |
| Theme | light, dark, reduced motion, forced colors |

## 11. Verifikasi Teknis

Hasil pemeriksaan:

- `python manage.py check`: **lulus**;
- `node --check rekap_rab.js`: **lulus**;
- `node --check print/RekapRABPrint.js`: **lulus**;
- 33 test akses export, change-status sync, page security, dan pricing management: **lulus**.

Test database lama ditemukan lalu dihapus otomatis oleh Django sebelum suite berjalan.

Test yang belum tersedia:

- escaping/XSS label hierarki;
- default markup tanpa `ProjectPricing`;
- rekonsiliasi `markup_eff`, `F`, `G`, dan `total`;
- total footer saat search;
- autosave failure/rollback;
- navigation sebelum debounce selesai;
- cache setelah admin/import harga;
- missing versus explicit zero;
- expanded readiness;
- refresh race;
- metadata dan total print;
- parity web/XLSX/PDF/Word/JSON;
- responsive header/body alignment;
- screen-reader UAT.

Audit visual browser, hasil file export aktual, print preview, dan screen reader belum dijalankan.

## 12. Keputusan Audit

Rekap RAB sudah mempunyai struktur page yang kuat dan calculation service yang cukup dekat dengan kebutuhan SSOT. Pemisahan harga dasar, markup, volume, PPN, dan pembulatan secara konseptual sudah benar. Adapter export juga sudah mengambil calculation dari service yang sama, lebih baik dibanding menghitung ulang seluruh formula.

Namun page belum layak dianggap final karena:

1. data user dapat dieksekusi sebagai HTML;
2. markup default dapat menghasilkan label 10% dengan angka 0%;
3. hasil print dapat salah menghitung pajak dan memakai identitas proyek palsu;
4. search mengubah arti total tanpa penjelasan;
5. autosave parameter finansial tidak memberikan kepastian penyimpanan;
6. kelengkapan data dan readiness belum menjadi bagian kontrak output.

Perbaikan tidak memerlukan restrukturisasi database besar. Fokus utama adalah:

1. renderer aman berbasis `textContent`;
2. calculation contract tunggal dengan default markup kanonik;
3. print membaca state dan metadata terstruktur;
4. completeness/readiness diagnostic;
5. autosave pricing yang observable;
6. penyederhanaan ownership export/print;
7. rekonsiliasi otomatis web, print, dan semua export.

---

## 13. Verifikasi Independen (Claude, 13 Juni 2026)

Temuan diperiksa ulang terhadap kode kerja. Yang diverifikasi langsung: **RR-01, RR-02, RR-03, RR-04, RR-05 — semuanya valid, tidak ada false positive.** Sisanya (RR-06..RR-25) konsisten dengan kode/struktur (autosave, cache, export, a11y, dead code; perlu UAT browser untuk konfirmasi visual). Usulan D-RR-01..06 menunggu konfirmasi owner.

### 13.1 Verdict per temuan (yang diverifikasi langsung)

| Temuan | Verdict | Bukti verifikasi |
|---|---|---|
| RR-01 Stored XSS label hierarki | **DIKONFIRMASI** | `rekap_rab.js:86` `highlightMatch` menyisipkan teks mentah ke HTML; `:328` (`${displayName}`), `:342` (`<span>${displayLabel}</span>`), `:343` (`tdK.innerHTML = displayKode`) inject nama/kode mentah via `innerHTML`. Jalur tanpa search pun mentah (`displayName = node.name`). `escAttr:89` hanya escape `"`. Tanpa CSP → eksekutabel. |
| RR-02 Default markup 0% vs 10% | **DIKONFIRMASI (jalur kode sama dengan RA-01)** | `services.py:2293` default `Decimal("0")`; `api_get_rekap_rab:4594` suntik 10% tapi `:4614-4620` pertahankan F/G/total 0%. **Ini bug yang identik dengan RA-01 — satu jalur kode.** Lihat 13.2. |
| RR-03 Print hitung PPN dua kali | **DIKONFIRMASI** | `RekapRABPrint.js:191-205` `extractSummaryFromTfoot` memilih cell via heuristik (`'Rp'`/`.text-end`/right-align) — rapuh, bisa mengambil cell pembulatan sebagai `totalD` lalu menghitung PPN ulang. |
| RR-04 Print identitas palsu | **DIKONFIRMASI (lebih buruk: hardcoded)** | `RekapRABPrint.js:943-948`: `projectName` masih punya fallback (`titleEl.textContent`), tetapi `owner:'Dinas PUPR (Pemprov DKI Jakarta)'`, `location:'Jakarta'`, `sumberDana:'APBD'` adalah **literal tanpa syarat** — bukan fallback. Lihat 13.2. |
| RR-05 Search ubah arti total project | **DIKONFIRMASI** | Footer dihitung dari `computeTotalsFiltered` (`:262`) yang dipakai `render()`; saat search aktif, Total/PPN/Grand/Pembulatan berubah jadi subset hasil filter tanpa perubahan label. |

### 13.2 Penajaman bukti

- **RR-02 = RA-01: satu bug, satu fix.** Ini benar-benar jalur kode yang sama (`compute_rekap_for_project` + `api_get_rekap_rab`) yang sudah diverifikasi di audit Rincian AHSP. Memperbaiki default markup di **satu** service sekaligus menutup RA-01, RR-02, dan divergensi adapter (RA-03). Ini bukti terkuat untuk rekomendasi "satu calculation service kanonik" — jangan perbaiki di dua page terpisah.

- **RR-04 lebih parah dari "nilai contoh".** Tiga field (`owner`, `location`, `sumberDana`) di-hardcode **tanpa kondisi** (`:944-948`), jadi dokumen pengesahan **selalu** mencetak "Dinas PUPR (Pemprov DKI Jakarta) / Jakarta / APBD" — bahkan untuk project yang datanya benar. Untuk dokumen RAB formal yang ditandatangani, ini risiko kepercayaan/hukum, bukan sekadar polish. Harus kirim metadata asli dari Django dan tampilkan `-` bila kosong (sejalan D-RR-05).

- **RR-01 + RR-18 harus diperbaiki bersama.** Setelah renderer web diamankan dengan `textContent`, modul print (`RR-18`) mengekstrak `textContent` lalu menyuntik ulang via `innerHTML` — jadi data `<...>` bisa aktif kembali di jalur print. Perbaikan XSS tidak lengkap bila hanya menyentuh `rekap_rab.js`. Ini XSS kelas yang sama dengan dashboard F-01 dan List Pekerjaan LP-01; tanpa CSP, ketiganya nyata.

### 13.3 Catatan konsistensi lintas-page (page ke-7, penutup rantai detail_project)

Rekap RAB sebagai consumer akhir mengonfirmasi seluruh tema sistemik:
- **XSS via `innerHTML`** (RR-01) = F-01 (dashboard) = LP-01 (list pekerjaan); **tanpa CSP** di `config/` memperburuk semuanya.
- **Default markup divergen** (RR-02) = RA-01 (jalur kode identik) — argumen terkuat untuk satu calculation service.
- **`str(e)` bocor** pada export (RR-17) = TA-08/HI/RA — sistemik di seluruh exporter.
- **Tanpa concurrency guard** pricing (RR-20) = TA-02/HI-09/VP-06/RA-11.
- **Tanpa audit trail finansial** (RR-10) = TA-04/RA-07; keputusan owner D-02 (audit markup) belum menjangkau pricing PPN/pembulatan.
- **Readiness `expanded_ready` tak jadi gate** (RR-08) = RA-08 = keputusan owner D-06 belum diimplementasi ke consumer.
- **Missing vs explicit-zero** (RR-07) = keputusan owner D-04 (Template AHSP) belum diimplementasi ke Rekap.

Penegasan: banyak temuan RR (RR-07, RR-08, RR-10) bukan kebijakan baru — itu **consumer akhir yang belum mengikuti keputusan owner yang sudah final** (D-02/D-04/D-06). Fase perbaikan harus memperlakukan D-04/D-06 sebagai pekerjaan lintas-page (Volume → Template AHSP → Rincian AHSP → Rekap RAB), bukan per-page.

### 13.4 Kalibrasi prioritas

Urutan P0 (RR-01..RR-05) tepat. Catatan:
- **RR-04 quick win berdampak tinggi**: hapus literal hardcoded `:944-948`, kirim metadata project asli. Effort rendah, risiko dokumen tinggi.
- **RR-01 + RR-18 satu paket** (renderer `textContent` aman di web + print).
- **RR-02 jangan dikerjakan lokal**: perbaiki bersama RA-01 di service (default markup tunggal + satu calculation builder web/print/export).
- **RR-03** (print summary) sebaiknya baca ID eksplisit (`ft-total-d`/`ft-ppn`/`ft-grand`/`ft-rounded`) atau, lebih baik, state calculation terstruktur — sejalan dengan "satu calculation contract".
