# Audit Komprehensif Page Audit Trail

**Tanggal audit:** 14 Juni 2026  
**Target:** `/detail_project/<project_id>/audit-trail/`  
**Objek:** current working tree pada saat audit  
**Status:** **DIPENSIUNKAN DARI WORKFLOW - UI dan API pembacaan akan dihapus; histori serta logging backend dipertahankan sementara**

## 1. Ringkasan Eksekutif

Page ini bukan audit trail seluruh Project. Storage dan pencatatan yang tersedia
berfokus pada perubahan komponen AHSP melalui `DetailAHSPAudit`, yaitu:

- perubahan isi Detail/Template AHSP per pekerjaan;
- perubahan sumber pekerjaan REF/MOD/CUSTOM;
- cascade re-expansion bundle;
- actor user/system/cascade;
- snapshot data lama dan data baru.

Page belum mencatat perubahan Volume Pekerjaan, Harga Items, conversion profile,
markup, identitas Project, Jadwal Pekerjaan, Rekap Kebutuhan, maupun aktivitas
export. Nama `Audit Trail` terlalu luas untuk cakupan aktual. Label yang lebih
jujur adalah `Riwayat Perubahan AHSP`.

Fondasi backend sudah cukup baik:

- data dipisahkan per Project;
- pekerjaan yang dihapus tidak menghapus baris audit;
- ordering terbaru lebih dahulu;
- tersedia filter, pagination, lazy detail, dan index dasar;
- halaman HTML tidak disimpan dalam browser cache.

Namun ada empat masalah utama:

1. data audit dirender dengan `innerHTML` tanpa escaping sehingga stored XSS
   dapat dieksekusi;
2. halaman hanya untuk staff/superuser, tetapi API dapat diakses pemilik Project
   biasa;
3. identitas pekerjaan dan actor tidak disimpan sebagai snapshot sehingga
   konteks histori hilang setelah object sumber dihapus;
4. ringkasan perubahan mengabaikan uraian, satuan, dan referensi.

## 2. Kontrak Produk dan SSOT

### 2.1 Peran Page

Page bersifat read-only untuk inspeksi perubahan AHSP. Page tidak menjadi sumber
data bisnis dan tidak boleh mengubah Template AHSP, Harga Items, atau page lain.

SSOT histori saat ini:

```text
DetailAHSPAudit
  -> project
  -> pekerjaan nullable
  -> action
  -> triggered_by
  -> user nullable
  -> old_data/new_data
  -> change_summary
  -> created_at
```

### 2.2 Cakupan yang Direkomendasikan

Untuk menjaga effort tetap proporsional, jangan langsung mengubah page ini
menjadi event log seluruh aplikasi. Tetapkan dua batas:

1. nama page menjadi `Riwayat Perubahan AHSP`; atau
2. jika nama `Audit Trail` dipertahankan, tampilkan badge/filter domain `AHSP`
   dan informasi bahwa domain lain belum dicatat.

Perluasan ke seluruh aktivitas Project hanya dilakukan setelah terdapat kebutuhan
audit operasional yang nyata dan schema event lintas-domain sudah disepakati.

## 3. Ruang Lingkup Implementasi

| Area | Implementasi |
|---|---|
| Web view | `detail_project.views.audit_trail_view` |
| API | `detail_project.views_api.api_get_audit_trail` |
| Model | `DetailAHSPAudit` |
| Audit writer | `detail_project.services.log_audit` |
| Template | `detail_project/audit_trail.html` |
| JavaScript | `detail_project/js/audit_trail.js` |
| CSS | `detail_project/css/audit_trail.css` |
| Akses page | login + staff/superuser + owner Project |
| Akses API | login + owner Project, tanpa pemeriksaan staff |
| Page size | fixed 20 pada client; API menerima 1-100 |

## 4. Audit Mode dan Interaksi User

### 4.1 Initial Load

Page me-render pilihan pekerjaan dari server, kemudian JavaScript meminta daftar
audit dengan `include_diff=0`. Ini menghindari pengiriman JSON diff besar pada
initial load dan merupakan keputusan yang baik.

Kekurangan:

- loading hanya berupa satu baris teks;
- tidak ada `aria-busy`;
- refresh dan perubahan filter tidak membatalkan request lama;
- respons request lama dapat menimpa hasil filter yang lebih baru.

### 4.2 Filter Action

Pilihan `CREATE`, `UPDATE`, `DELETE`, dan `CASCADE` sesuai model. API tidak
memvalidasi pilihan terhadap enum; nilai tidak dikenal hanya menghasilkan hasil
kosong. Dampaknya kecil, tetapi contract API tidak tegas.

### 4.3 Filter Trigger

Pilihan user/cascade/system sesuai model. Label masih campur Inggris dan
Indonesia. Gunakan `Pengguna`, `Cascade`, dan `Sistem`, dengan tooltip singkat
untuk menjelaskan cascade.

### 4.4 Filter Pekerjaan

Filter hanya memuat pekerjaan yang masih aktif. Audit pekerjaan yang telah
dihapus tetap ada, tetapi tidak dapat dipilih dari filter dan tampil sebagai
pekerjaan `-`.

Untuk data besar, native select tanpa search juga tidak efisien.

### 4.5 Rentang Tanggal

API menerima tanggal ISO, tetapi membuat `datetime` naive pada project dengan
`USE_TZ=True`. Batas hari dapat bergeser terhadap timezone aplikasi.

Belum ada validasi bahwa tanggal awal tidak melewati tanggal akhir. UI juga tidak
memberi tombol reset rentang.

### 4.6 Pagination

Pagination previous/next sederhana dan cukup untuk initial scope. API memakai
`int()` langsung untuk `page` dan `page_size`; input nonangka menghasilkan 500.

Page yang melebihi total halaman menghasilkan tabel kosong tanpa koreksi menuju
halaman terakhir. Offset pagination dan `COUNT(*)` masih memadai untuk data kecil,
tetapi perlu benchmark jika histori tumbuh besar.

### 4.7 Detail Old/New Data

Lazy loading detail merupakan pola yang baik. Masalahnya:

- JSON mentah sulit dibaca user nonteknis;
- tidak ada highlight field yang berubah;
- tidak ada accessible expanded state;
- payload tidak dibatasi ukurannya;
- rendering menggunakan HTML mentah dan rentan stored XSS.

Rekomendasi: tampilkan summary field-level terlebih dahulu, sedangkan raw JSON
menjadi detail teknis sekunder.

### 4.8 Refresh

Refresh mempertahankan page dan filter aktif. Ini sesuai ekspektasi. Tombol belum
memiliki loading state, disabled state, atau pencegahan double request.

### 4.9 Empty dan Error State

Empty state tidak membedakan:

- belum pernah ada perubahan;
- filter tidak menemukan hasil;
- pekerjaan terhapus;
- data audit gagal dicatat.

Pesan error generik dan detail endpoint hanya dicetak ke console. Untuk tool
admin, tampilkan pesan yang dapat ditindaklanjuti tanpa mengekspos exception.

### 4.10 Responsive, Theme, dan Accessibility

Halaman memakai Bootstrap responsive table dan token warna Bootstrap sehingga
fondasi light/dark cukup baik. Kekurangannya:

- mobile hanya mendapat horizontal scroll;
- tombol `Lihat` tidak memiliki `aria-expanded` dan `aria-controls`;
- perubahan tabel/pagination tidak diumumkan melalui `aria-live`;
- tabel tidak memiliki caption;
- filter date group tidak memiliki fieldset/legend;
- badge action hanya satu warna sehingga scanning lemah;
- fokus tidak dipindahkan atau dipertahankan dengan jelas setelah refresh;
- raw JSON panjang dapat membuat layout dan navigasi keyboard berat.

## 5. Temuan Audit

### AT-01 - CRITICAL - Stored XSS pada Tabel dan Detail Audit

`audit_trail.js` memasukkan kode, uraian, username, action, trigger,
`change_summary`, dan hasil `JSON.stringify(old_data/new_data)` melalui
`innerHTML`.

Nilai seperti `</pre><img src=x onerror=...>` pada data audit dapat keluar dari
elemen `<pre>` dan dieksekusi. Data pekerjaan dan komponen berasal dari input
tersimpan sehingga risiko ini nyata.

**Rekomendasi:** bangun seluruh cell dengan `textContent`/DOM API. Untuk JSON,
buat elemen `<pre>` lalu set `textContent`. Jangan mengandalkan sanitizer browser.

### AT-02 - HIGH - Otorisasi Page dan API Tidak Konsisten

Web view memakai `staff_only_page`, tetapi API hanya memakai `login_required`
dan `_owner_or_404`. Pemilik Project non-staff yang mengetahui endpoint tetap
dapat membaca audit termasuk old/new data.

**Rekomendasi:** gunakan satu permission helper pada page dan API. Jika kontrak
tetap admin-only, API wajib memeriksa staff/superuser dan ownership.

### AT-03 - HIGH - Identitas Pekerjaan Hilang Setelah Pekerjaan Dihapus

Foreign key `pekerjaan` memakai `SET_NULL`, tetapi kode dan uraian pekerjaan tidak
disimpan dalam record audit. Setelah pekerjaan dihapus, histori tetap ada namun
UI hanya menampilkan `-` dan filter pekerjaan tidak dapat menemukannya.

**Rekomendasi:** simpan `pekerjaan_id_snapshot`, `pekerjaan_kode_snapshot`, dan
`pekerjaan_uraian_snapshot` pada saat log dibuat. FK hanya menjadi link opsional
ke object aktif.

### AT-04 - HIGH - Ringkasan Perubahan Tidak Mencakup Seluruh Field

`_build_change_summary()` hanya menandai perubahan `koefisien` dan `kategori`
pada kode yang sama. Perubahan uraian, satuan, `ref_kind`, dan `ref_id` dapat
ditulis sebagai `Update - no material changes`.

**Rekomendasi:** diff seluruh field bisnis yang disimpan dalam snapshot dan
hasilkan daftar field berubah per kode.

### AT-05 - HIGH - Audit Bukan Bagian Andal dari Transaksi Bisnis

`log_audit()` bersifat fail-safe dan menelan seluruh exception. Perubahan bisnis
dapat berhasil tanpa histori dan user/admin tidak mendapat indikator bahwa audit
gagal. Pada cascade, operasi juga sengaja dilanjutkan ketika pencatatan gagal.

**Rekomendasi:** untuk perubahan user utama, buat audit dalam transaksi yang
sama atau gunakan outbox/on-commit yang terpantau. Untuk cascade asynchronous,
simpan status event dan retry. Minimal tambahkan metric/alert, bukan hanya log.

### AT-06 - HIGH - Audit Coverage Tidak Lengkap terhadap Nama Page

Page tidak mencatat perubahan Harga Items, Volume, conversion, markup, Jadwal,
identitas Project, dan export. Judul generik dapat membuat admin menganggap
riwayat tersebut lengkap.

**Rekomendasi:** rename menjadi `Riwayat Perubahan AHSP` sebagai solusi minimal.
Jangan memperluas schema sebelum kebutuhan produk disepakati.

### AT-07 - MEDIUM - Snapshot Actor Hilang Setelah User Dihapus

FK user memakai `SET_NULL` dan username dibaca dari record user aktif. Setelah
user dihapus, actor menjadi `-`.

**Rekomendasi:** simpan `actor_id_snapshot` dan `actor_label_snapshot` pada event.

### AT-08 - MEDIUM - Filter Tanggal Tidak Timezone-Aware

`datetime.fromisoformat("YYYY-MM-DD")` menghasilkan datetime naive sementara
aplikasi memakai `USE_TZ=True`. Batas hari tidak eksplisit mengikuti timezone
Project/aplikasi.

**Rekomendasi:** parse sebagai `date`, bentuk awal/akhir hari dengan
`timezone.make_aware`, dan gunakan half-open range `[start, next_day)`.

### AT-09 - MEDIUM - Input Pagination Dapat Menghasilkan HTTP 500

`page` dan `page_size` dikonversi dengan `int()` tanpa penanganan `ValueError`.

**Rekomendasi:** gunakan parser integer terkontrol dan respons 400 dengan error
field yang konsisten.

### AT-10 - MEDIUM - Race Condition saat Filter/Refresh Cepat

Tidak ada `AbortController` atau request sequence. Respons lama dapat dirender
setelah respons terbaru dan membuat tabel tidak sesuai filter yang terlihat.

**Rekomendasi:** abort request aktif atau abaikan response dengan request ID lama.

### AT-11 - MEDIUM - API Audit Tidak Menetapkan Cache Policy Sensitif

Middleware `no-store` hanya diterapkan pada HTML detail project, bukan response
API. Response audit berisi data sebelum/sesudah dan username.

**Rekomendasi:** tambahkan `Cache-Control: private, no-store` pada API audit.

### AT-12 - MEDIUM - Detail Diff Belum Human-Readable

Old/new raw JSON memaksa admin membandingkan dua payload secara manual.

**Rekomendasi:** tampilkan `ditambah`, `dihapus`, dan `diubah` per kode/field,
dengan raw JSON sebagai expandable technical detail.

### AT-13 - LOW - Filter dan State Tidak Persisten di URL

Refresh browser atau share URL menghapus filter, tanggal, dan page.

**Rekomendasi:** sinkronkan query parameter filter dan page ke URL menggunakan
`history.replaceState`.

### AT-14 - LOW - Empty State dan Terminologi Belum Kontekstual

`Tidak ada data audit` tidak membedakan initial-empty dan filtered-empty. Label
Action, Triggered By, Old Data, New Data, dan Refresh bercampur bahasa.

**Rekomendasi:** gunakan bahasa Indonesia konsisten dan CTA `Reset Filter` untuk
filtered-empty.

### AT-15 - LOW - Aksesibilitas Detail dan Tabel Belum Lengkap

Tidak ada caption, live region hasil, expanded state, hubungan tombol dengan
detail row, dan busy state.

**Rekomendasi:** tambahkan semantic state tanpa mengubah workflow.

## 6. Penilaian UI/UX

### Yang Sudah Baik

- layout ringkas dan fokus pada inspeksi;
- filter utama tersedia tanpa modal tambahan;
- lazy detail mengurangi initial payload;
- pagination sederhana mudah dipahami;
- tabel responsive dan token Bootstrap mendukung theme;
- alert menggunakan `role="status"`;
- page bersifat read-only sehingga risiko aksi destruktif rendah.

### Perbaikan UX Prioritas

1. Ganti raw HTML rendering dengan DOM aman.
2. Ubah judul menjadi `Riwayat Perubahan AHSP`.
3. Buat detail diff field-level yang dapat dipindai.
4. Pertahankan identitas pekerjaan terhapus.
5. Tambahkan reset filter, filtered-empty state, dan loading state.
6. Untuk mobile, tampilkan entry sebagai card atau drawer detail.
7. Gunakan badge action semantik:
   - create: hijau;
   - update: biru;
   - delete: merah;
   - cascade: ungu/abu dengan label sistem.

## 7. Konsistensi dengan Page Lain

### Template AHSP dan List Pekerjaan

Perubahan sumber REF/MOD/CUSTOM dicatat, tetapi audit tidak menyimpan old/new
payload struktural untuk event tersebut. Keputusan reset volume ketika source
berubah juga belum terlihat sebagai event terkait.

### Harga Items

Harga adalah SSOT biaya, tetapi perubahan harga dan conversion profile tidak
tercatat pada page ini. Jangan menyebut page sebagai audit seluruh Project.

### Volume Pekerjaan

Perubahan volume dan formula volume tidak dicatat. Bila kelak diperlukan, domain
event harus menyimpan formula/value before-after tanpa mencampurkannya ke schema
snapshot AHSP.

### Jadwal Pekerjaan

Last-save-wins, planned/actual weekly, regenerate timeline, dan export tidak
tercatat. Audit Jadwal sebaiknya terpisah bila kebutuhan operasional muncul.

### Rekap RAB dan Rekap Kebutuhan

Keduanya merupakan consumer/read-only. Tidak perlu mencatat setiap kalkulasi
ulang sebagai audit event. Yang perlu dicatat adalah perubahan sumber datanya,
bukan page dibuka atau dihitung.

## 8. Rekomendasi Arsitektur Minimal

Pertahankan model khusus AHSP, tetapi perkuat contract:

```text
DetailAHSPAudit
  domain = "AHSP"
  project_id
  pekerjaan FK nullable
  pekerjaan_id_snapshot
  pekerjaan_kode_snapshot
  pekerjaan_uraian_snapshot
  actor FK nullable
  actor_id_snapshot
  actor_label_snapshot
  action
  trigger
  old_data
  new_data
  changed_fields
  summary
  created_at
```

Gunakan satu serializer server dan renderer DOM aman. Jangan membuat event bus
umum atau audit framework lintas aplikasi hanya untuk menyelesaikan page ini.

## 9. Prioritas Remediasi

| Prioritas | Item | Tujuan |
|---|---|---|
| P0 | AT-01 hapus seluruh unsafe `innerHTML` | Menutup stored XSS |
| P0 | AT-02 samakan permission page/API | Menutup bypass akses |
| P1 | AT-03/AT-07 snapshot pekerjaan dan actor | Menjaga konteks histori |
| P1 | AT-04 perbaiki field-level diff | Integritas ringkasan |
| P1 | AT-05 observability/reliability audit writer | Mendeteksi audit gap |
| P1 | AT-08/AT-09 validasi tanggal dan pagination | Ketahanan API |
| P1 | AT-10/AT-11 request race dan no-store API | Konsistensi dan privasi |
| P2 | AT-06 rename/cakupan page | Ekspektasi produk |
| P2 | AT-12 sampai AT-15 | UI/UX dan aksesibilitas |

## 10. UAT Matrix

| Area | Skenario |
|---|---|
| Akses | anonymous, owner biasa, staff owner, superuser, project milik user lain |
| XSS | kode/uraian/summary/JSON mengandung tag, quote, dan closing `pre` |
| Action | create, update, delete, cascade |
| Trigger | user, system, cascade |
| Diff | koefisien, kategori, uraian, satuan, ref kind, ref id |
| Retention | pekerjaan dihapus, user dihapus, project dihapus |
| Filter | action, trigger, pekerjaan, tanggal, kombinasi |
| Date | timezone boundary, DST-independent zone, from > to |
| Pagination | page pertama/akhir/kosong/nonangka/terlalu besar |
| Race | filter cepat, refresh berulang, response out-of-order |
| Data besar | banyak entry, snapshot besar, pekerjaan banyak |
| Empty | belum ada audit, filtered-empty, pekerjaan terhapus |
| Error | 400, 403/404, 500, offline, timeout |
| Accessibility | keyboard, screen reader, focus, zoom 200% |
| Responsive | 320, 360, 576, 768, desktop |
| Theme | light, dark, reduced motion, forced colors |

## 11. Verifikasi Teknis

Hasil pemeriksaan:

- `python manage.py check`: **lulus**;
- `node --check detail_project/static/detail_project/js/audit_trail.js`: **lulus**;
- test retention audit: tersedia;
- test no-store HTML: tersedia;
- test admin-only page/sidebar: tersedia tetapi **gagal pada run audit** karena
  test client diarahkan ke login meskipun menggunakan `force_login`.

Run gabungan menemukan lima failure pada module admin-only. Kegagalan tersebut
perlu diinvestigasi terpisah karena membuat kontrak akses halaman belum dapat
dinyatakan tervalidasi oleh automated test.

Test yang belum tersedia:

- permission API audit untuk regular owner/staff/non-owner;
- sanitasi/XSS seluruh field;
- filter dan pagination invalid input;
- timezone date boundary;
- field-level diff;
- snapshot identity setelah pekerjaan/user dihapus;
- cache header API;
- out-of-order request;
- responsive dan screen-reader UAT.

Audit visual browser belum dijalankan.

## 12. Keputusan Audit

**Keputusan owner 14 Juni 2026: page Audit Trail dipensiunkan.**

Page ini tidak mempunyai dampak yang cukup signifikan terhadap workflow utama
Project dan hanya berfungsi sebagai utility debugging admin untuk perubahan AHSP.
Tidak diperlukan investasi untuk memoles UI, filter, pagination, atau responsive
page yang akan dihapus.

Yang dihapus:

1. link dan active state sidebar;
2. route `audit-trail/`;
3. `audit_trail_view`;
4. template `audit_trail.html`;
5. `audit_trail.js` dan `audit_trail.css`;
6. API pembacaan `api_get_audit_trail`;
7. test page, sidebar, cache-header, dan API yang khusus menjaga UI tersebut.

Yang dipertahankan sementara:

1. model dan tabel `DetailAHSPAudit`;
2. `log_audit()` dan pencatatan perubahan/cascade;
3. histori audit yang sudah tersimpan;
4. test retensi dasar;
5. akses diagnosis melalui Django admin, shell, atau tooling internal bila
   diperlukan.

AT-01 stored XSS dan AT-02 mismatch permission ditutup dengan menghapus permukaan
web/API, bukan memperbaiki page. AT-03 sampai AT-15 tidak menjadi pekerjaan
implementasi UI. Keandalan writer backend dapat dievaluasi terpisah ketika ada
kebutuhan operasional nyata.
