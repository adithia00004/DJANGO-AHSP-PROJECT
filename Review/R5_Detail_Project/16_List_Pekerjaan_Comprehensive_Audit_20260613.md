# Audit Komprehensif Page List Pekerjaan

**Tanggal audit:** 13 Juni 2026  
**Target:** `/detail_project/<project_id>/list-pekerjaan/`  
**Status:** **LULUS BERSYARAT - masih terdapat temuan High yang perlu ditutup**

## 1. Ringkasan Eksekutif

Page List Pekerjaan memiliki cakupan fitur yang besar dan secara umum telah mempunyai fondasi yang baik:

- akses project dibatasi berdasarkan owner;
- project nonaktif tidak dapat dibuka dari page utama;
- penyimpanan memakai endpoint upsert yang memvalidasi struktur dan referensi;
- tersedia drag-and-drop, pencarian, filter, ekspor/impor, dan Template Library;
- source pekerjaan dibedakan antara custom, referensi asli, dan referensi yang dimodifikasi;
- beberapa risiko XSS, permission template, cache, dan drag-and-drop sudah memiliki pengujian otomatis.

Namun, page ini belum dapat dinyatakan selesai sepenuhnya karena masih ada risiko utama:

1. Stored XSS masih dapat terjadi pada modal preview Template Library.
2. Endpoint upsert dapat melakukan commit parsial walaupun mengembalikan HTTP `207`.
3. Penyimpanan full-state belum mempunyai optimistic concurrency control sehingga tab lama dapat menimpa perubahan tab lain.
4. Penghapusan dan perubahan source dapat menghapus data turunan tanpa konfirmasi dampak yang memadai.
5. Terdapat dua jalur save yang memperlemah SSOT dan salah satunya merupakan endpoint lama yang kurang aman.

Kesimpulan audit: fitur inti berjalan dan test terarah lulus, tetapi temuan High harus diselesaikan sebelum page dinilai production-ready.

## 2. Ruang Lingkup Audit

### Frontend

- template Django dan struktur HTML;
- JavaScript editor tree;
- state dan dirty tracking;
- drag-and-drop;
- pencarian, filter, compact mode, dan navigasi;
- ekspor dan impor JSON;
- Template Library;
- feedback pengguna;
- accessibility dan responsive behavior.

### Backend

- page view dan authorization;
- tree API;
- upsert API;
- legacy save API;
- export/import API;
- Template Library API;
- transaction behavior;
- validasi source/reference;
- rate limiting dan batas payload.

### SSOT dan arsitektur

- sumber data authoritative;
- konsistensi jalur read/write;
- sinkronisasi antar-tab;
- hubungan data pekerjaan dengan Volume, Detail AHSP, dan Jadwal;
- duplikasi validasi frontend/backend.

### UI/UX

- kejelasan mode;
- feedback loading/error/success;
- keamanan tindakan destruktif;
- keyboard dan touch interaction;
- information hierarchy;
- kondisi empty, loading, dan failed state.

## 3. Mode yang Diaudit

### 3.1 Mode Custom

**Status:** Berfungsi, dengan catatan pada destructive save.

- User dapat membuat klasifikasi, subklasifikasi, dan pekerjaan custom.
- Editing nama dan kode dilakukan langsung pada editor.
- Data kemudian dikirim sebagai satu full-state tree.
- Penghapusan node di UI belum langsung menghapus database, tetapi omission saat save akan dianggap sebagai instruksi delete.

Risiko utamanya adalah user tidak memperoleh impact preview sebelum perubahan tersebut diterapkan ke data turunan.

### 3.2 Mode Referensi

**Status:** Validasi backend cukup baik.

- Pekerjaan referensi divalidasi terhadap sumber referensinya.
- Identitas source tidak hanya dipercaya dari data DOM.
- Referensi yang tidak konsisten dapat ditolak backend.

Masalah tersisa adalah perubahan source masih dapat menyebabkan reset data turunan tanpa dialog konfirmasi yang menjelaskan dampaknya.

### 3.3 Mode Referensi Dimodifikasi

**Status:** Berfungsi, tetapi transisi source berisiko destruktif.

- Mode ini membedakan pekerjaan referensi asli dan pekerjaan hasil modifikasi.
- Perubahan source dicatat agar page lain dapat bereaksi terhadap perubahan pekerjaan.
- Backend melakukan reset data terkait ketika source/type berubah.

Reset tersebut dapat mencakup Volume, Detail AHSP, tahapan pekerjaan, dan formula. UI perlu menunjukkan daftar pekerjaan serta jenis data yang akan terdampak sebelum save.

### 3.4 Drag-and-Drop

**Status:** Fungsional untuk desktop, accessibility belum memadai.

- Pemindahan pekerjaan, subklasifikasi, dan klasifikasi telah ditangani.
- State dirty diperbarui setelah perpindahan.
- Terdapat test backend untuk hasil struktur drag-and-drop.

Belum tersedia kontrol reorder berbasis keyboard dan fallback touch yang jelas. HTML5 drag-and-drop juga tidak cukup andal sebagai satu-satunya interaksi pada perangkat mobile.

### 3.5 Compact Mode, Filter, Search, dan Navigation Overlay

**Status:** Berfungsi, tetapi pola pencarian belum konsisten.

- Compact mode membantu mengurangi kepadatan tabel.
- Filter dan navigation overlay membantu mengakses tree besar.
- Toolbar search dan pencarian di navigation overlay mempunyai perilaku berbeda.
- Toolbar search hanya berorientasi pada hasil pertama dan tidak menampilkan jumlah hasil.

Sebaiknya terdapat satu model pencarian yang konsisten: query, jumlah hasil, previous/next result, clear state, dan empty result.

### 3.6 Export dan Import JSON

**Status:** Fungsional, batas keamanan payload belum spesifik.

- Export menggunakan response yang mencegah cache dan content sniffing.
- Nama file telah diperlakukan secara aman.
- Import browser membaca keseluruhan file sebelum dikirim.
- Tidak ditemukan batas ukuran file, jumlah node, atau kompleksitas tree yang spesifik untuk endpoint ini.

Global upload limit sebesar 50 MB terlalu longgar untuk payload tree. Endpoint perlu mempunyai batas yang lebih kecil dan terukur.

### 3.7 Template Library

**Status:** Permission cukup baik, preview masih memiliki celah XSS.

- Template private hanya dapat diakses owner.
- Template public dapat digunakan lintas user.
- Nama template pada daftar sudah di-escape.
- Isi preview klasifikasi dan subklasifikasi masih dimasukkan melalui `innerHTML` tanpa escaping yang konsisten.

Karena template public dapat dibuka user lain, data tersimpan yang berbahaya dapat dieksekusi ketika modal preview dibuka.

### 3.8 Multi-Tab Editing

**Status:** Peringatan tersedia, pencegahan konflik belum tersedia.

- `BroadcastChannel` digunakan untuk memberi tahu tab lain setelah save.
- Mekanisme ini membantu awareness, tetapi tidak mencegah stale write.
- Backend mengunci row project selama proses save, tetapi tidak memverifikasi versi data yang dibaca user.

Tab kedua yang memuat data lama masih dapat menyimpan full-state setelah tab pertama dan menghapus perubahan yang tidak terdapat pada snapshot lama.

## 4. Temuan Audit

### LP-01 - High - Stored XSS pada Preview Template Library

**Area:** Frontend security  
**Lokasi utama:** `detail_project/static/detail_project/js/list_pekerjaan.js`

Modal preview membangun HTML menggunakan nama klasifikasi dan subklasifikasi dari `template.content`. Nilai tersebut belum seluruhnya melewati `escapeHtml()` sebelum dimasukkan ke `innerHTML`.

**Dampak:**

- script atau event handler berbahaya dapat tersimpan di data template;
- payload dapat dieksekusi saat user lain membuka preview template public;
- permission backend tidak mencegah serangan karena user memang berhak membaca template public.

**Rekomendasi:**

1. Hindari penyusunan preview dengan raw HTML.
2. Gunakan `textContent` dan DOM API untuk nilai data.
3. Jika HTML generation tetap digunakan, escape seluruh nama, kode, dan unit tanpa pengecualian.
4. Tambahkan test frontend dengan payload pada nama klasifikasi dan subklasifikasi.
5. Pertimbangkan sanitasi defensif untuk konten template lama.

### LP-02 - High - Commit Parsial pada Upsert yang Mengembalikan HTTP 207

**Area:** Backend transaction dan data integrity  
**Lokasi utama:** `api_upsert_list_pekerjaan`

Endpoint dibungkus `transaction.atomic`, tetapi error selama pemrosesan dikumpulkan ke dalam array. Setelah itu backend tetap menjalankan penghapusan node yang tidak ada di payload dan mengembalikan response `207`.

Mengembalikan response dari blok atomic tidak menyebabkan rollback otomatis. Akibatnya, sebagian create/update/delete dapat tetap committed meskipun UI menyampaikan bahwa sebagian perubahan gagal.

**Dampak:**

- tree database dapat berada pada kondisi campuran;
- omission delete dapat tetap diterapkan;
- data turunan dapat terhapus walaupun save dianggap gagal;
- reload setelah response `207` tidak memulihkan data yang sudah committed.

**Rekomendasi:**

1. Lakukan validasi penuh sebelum mutasi database.
2. Terapkan all-or-nothing transaction untuk full-state upsert.
3. Jika ditemukan satu error, raise exception terkontrol atau tandai transaction rollback.
4. Gunakan `400`, `409`, atau `422` dengan error terstruktur.
5. Jangan gunakan `207` untuk destructive full-tree synchronization.

### LP-03 - High - Stale Write Dapat Menimpa Perubahan Tab Lain

**Area:** Concurrency dan SSOT

Row lock hanya menserialisasi proses save. Lock tersebut tidak membuktikan bahwa payload dibuat dari versi tree terbaru.

Karena payload bersifat full-state dan backend menghapus node yang tidak dikirim, tab dengan snapshot lama dapat menghapus perubahan yang baru disimpan tab lain.

**Rekomendasi:**

1. Sertakan `revision`, ETag, atau tree version pada response GET.
2. Client harus mengirim revision tersebut saat upsert.
3. Backend menolak revision lama dengan HTTP `409 Conflict`.
4. UI menyediakan opsi reload, bandingkan perubahan, atau merge.
5. `BroadcastChannel` tetap dipakai sebagai feedback tambahan, bukan mekanisme konsistensi utama.

### LP-04 - High - Operasi Destruktif Tidak Menampilkan Dampak Data Turunan

**Area:** Data safety dan UX

Delete pada klasifikasi, subklasifikasi, dan pekerjaan hanya menghapus elemen dari DOM serta menandai dirty. Dampak baru terjadi saat save, tetapi user tidak memperoleh rangkuman objek yang akan dihapus.

Perubahan source/type pekerjaan juga dapat mereset:

- Detail AHSP Project;
- Volume Pekerjaan;
- Pekerjaan Tahapan;
- Volume Formula State;
- Template AHSP coefficient formula state.

**Rekomendasi:**

1. Simpan daftar deletion/change intent secara eksplisit.
2. Sebelum save, tampilkan impact summary.
3. Minta konfirmasi tambahan untuk perubahan yang menghapus data turunan.
4. Tambahkan undo sebelum save.
5. Untuk data bernilai tinggi, pertimbangkan soft-delete atau audit log.

### LP-05 - Medium - Dua Endpoint Save Memperlemah SSOT

**Area:** Backend architecture

UI saat ini memakai endpoint upsert, tetapi legacy full-save endpoint masih terdaftar dan dapat dipanggil. Endpoint lama:

- mempunyai semantics berbeda;
- berpotensi menghasilkan duplikasi pada pemanggilan berulang;
- menggunakan error handling yang terlalu luas;
- dapat mengekspos detail exception;
- juga menggunakan partial success.

**Rekomendasi:**

1. Tetapkan upsert sebagai satu-satunya write SSOT.
2. Hapus route lama jika tidak memiliki consumer.
3. Jika masih dibutuhkan untuk compatibility, tandai deprecated dan batasi caller.
4. Tambahkan test yang memastikan UI dan integrasi hanya memakai endpoint canonical.

### LP-06 - Medium - Rate Limit dan Batas Payload Belum Spesifik

**Area:** Availability dan abuse protection

Legacy save memiliki rate limit, sedangkan upsert dan beberapa endpoint Template Library belum menunjukkan perlindungan setara. Import juga belum membatasi ukuran dan jumlah node secara domain-specific.

**Rekomendasi minimum:**

- rate limit untuk upsert, create template, dan import;
- batas request body khusus endpoint;
- batas jumlah klasifikasi, subklasifikasi, dan pekerjaan;
- batas panjang string;
- validasi depth dan bentuk JSON;
- penolakan file di browser sebelum `file.text()` jika melebihi batas.

### LP-07 - Medium - Import Template Dapat Berhasil Parsial

**Area:** Transaction dan UX

Import template dapat membuat sebagian record, mengembalikan warning/error, lalu tetap dinyatakan berhasil dan usage count diperbarui.

**Risiko:**

- user sulit memahami data mana yang masuk;
- retry dapat menghasilkan duplikasi;
- tree dapat berada pada kondisi setengah terimpor.

**Rekomendasi:**

1. Pisahkan proses menjadi preview/validate dan commit.
2. Tampilkan konflik sebelum import.
3. Gunakan idempotency key atau strategi deduplikasi.
4. Jika partial import dipertahankan, status dan daftar hasil harus eksplisit serta dapat diunduh.

### LP-08 - Medium - Reorder Belum Accessible untuk Keyboard dan Touch

**Area:** Accessibility dan responsive UX

Drag handle belum menyediakan mekanisme lengkap untuk:

- mengangkat dan memindahkan item dengan keyboard;
- mengumumkan posisi baru;
- memindahkan item pada perangkat touch tanpa drag HTML5.

**Rekomendasi:**

- sediakan tombol move up/down atau menu “Pindahkan ke”;
- tambahkan keyboard interaction dan live-region announcement;
- pastikan focus tetap berada pada item setelah dipindahkan;
- lakukan UAT pada mobile/touch device.

### LP-09 - Medium - Initial Load Bergantung pada Fetch dan Failed State Kurang Aman

**Area:** Loading UX dan reliability

Page template tidak membawa bootstrap tree. Editor baru terisi setelah JavaScript melakukan fetch. Ketika fetch gagal, kondisi UI dapat menyerupai tree kosong atau state awal sehingga penyebab kegagalan kurang tegas.

**Rekomendasi:**

1. Tampilkan skeleton/loading state yang eksplisit.
2. Disable edit dan save sampai initial load berhasil.
3. Sediakan retry action.
4. Bedakan empty data yang valid dengan network/server failure.
5. Pertimbangkan bootstrap JSON menggunakan `json_script` agar first render lebih stabil.

### LP-10 - Medium - Nama Template Unik Secara Global

**Area:** Data model dan multi-user UX

Nama template mempunyai uniqueness global. Akibatnya, user tidak dapat menggunakan nama private yang sama dengan template milik user lain dan dapat memperoleh sinyal bahwa nama tersebut sudah digunakan.

**Rekomendasi:**

- gunakan uniqueness per owner untuk template private;
- definisikan aturan terpisah untuk template public;
- hindari membocorkan keberadaan template private melalui pesan konflik.

### LP-11 - Low - Inline Event Handler Menghambat CSP Ketat

**Area:** Frontend security hardening

Masih terdapat event handler inline pada template untuk memicu input file. Pola ini menyulitkan penerapan Content Security Policy tanpa `unsafe-inline`.

**Rekomendasi:** pindahkan seluruh binding ke JavaScript module/event listener dan siapkan CSP bertahap.

### LP-12 - Low - Dua Pola Search Belum Konsisten

**Area:** UI/UX

Toolbar search mengarahkan user ke hasil pertama, sedangkan search pada navigation overlay menyaring daftar. Tidak ada indikator jumlah hasil atau navigasi previous/next yang konsisten.

**Rekomendasi:** satukan search state dan interaction model untuk mengurangi beban belajar user.

## 5. Penilaian SSOT

### Kondisi yang Sudah Baik

- Tree GET API menjadi sumber baca utama editor.
- Upsert API menjadi jalur write yang dipakai frontend.
- Ownership project diperiksa di backend.
- Referensi pekerjaan diverifikasi terhadap data sumber.
- Informasi perubahan source diteruskan agar page terkait dapat melakukan invalidation.

### Kelemahan SSOT

- Legacy save endpoint masih aktif.
- DOM frontend berfungsi sebagai full-state authoritative payload.
- Tidak ada revision token antara read dan write.
- Format template/import mendukung beberapa bentuk struktur sehingga normalisasi menjadi kompleks.
- Validasi bentuk data tersebar antara frontend dan backend.
- Partial success membuat status authoritative setelah save kurang dapat diprediksi.

### Target Arsitektur

1. Satu canonical tree schema.
2. Satu canonical write endpoint.
3. Validasi schema lengkap sebelum transaction mutasi.
4. All-or-nothing commit.
5. Revision-based concurrency control.
6. Explicit destructive command dan impact report.
7. Audit trail untuk perubahan source dan deletion penting.

## 6. Rekomendasi Restrukturisasi

### Tahap 1 - Security dan Integrity

1. Tutup XSS preview Template Library.
2. Ubah upsert menjadi all-or-nothing.
3. Tambahkan optimistic concurrency dan response `409`.
4. Tambahkan destructive impact confirmation.

### Tahap 2 - SSOT Backend

1. Deprecate dan hapus legacy save endpoint.
2. Buat schema validator terpusat untuk tree payload.
3. Pisahkan validation, planning, dan mutation:
   - `validate_tree_payload`;
   - `build_tree_change_plan`;
   - `apply_tree_change_plan`.
4. Tambahkan limit dan rate limiting per endpoint.

### Tahap 3 - Frontend State

1. Pisahkan canonical editor state dari DOM rendering.
2. Simpan dirty operations sebagai change set.
3. Gunakan renderer untuk menghasilkan DOM dari state.
4. Tampilkan save summary berdasarkan change set.
5. Tangani `409 Conflict` dengan reload/compare flow.

### Tahap 4 - UI/UX dan Accessibility

1. Perjelas loading, empty, error, dan conflict state.
2. Tambahkan keyboard/touch reorder.
3. Satukan search experience.
4. Tambahkan impact review modal.
5. Lakukan visual UAT pada desktop, tablet, dan mobile.

## 7. Pengujian yang Dijalankan

### Django

```text
python manage.py test \
  detail_project.tests_list_pekerjaan_upsert_validation \
  detail_project.tests_list_pekerjaan_upsert_drag_drop \
  detail_project.tests_list_pekerjaan_export \
  detail_project.tests_template_library_api \
  detail_project.tests_page_security_audit \
  detail_project.tests_page_cache_headers \
  --verbosity 2 --keepdb
```

**Hasil:** `40 tests`, seluruhnya lulus.

### Frontend

```text
npm run test:frontend -- --run \
  detail_project/static/detail_project/js/tests/feedback_governance_guard.test.js
```

**Hasil:** `1 test file`, `2 tests`, seluruhnya lulus.

### Gap Pengujian

Belum ditemukan coverage yang memadai untuk:

- XSS pada nama klasifikasi/subklasifikasi di modal preview;
- rollback saat satu node upsert gagal;
- stale revision dan HTTP `409`;
- impact confirmation untuk delete/source change;
- batas payload dan jumlah node;
- keyboard/touch reorder;
- visual dan responsive UAT melalui browser.

## 8. Prioritas Tindak Lanjut

| Prioritas | Item | Target |
|---|---|---|
| P0 | Escape/safe-render seluruh Template Preview | Menutup stored XSS |
| P0 | Atomic rollback pada seluruh error upsert | Menjamin integritas tree |
| P0 | Revision token dan stale-write rejection | Mencegah overwrite antar-tab |
| P0 | Konfirmasi dampak destructive save | Mencegah kehilangan data turunan |
| P1 | Hapus/deprecate legacy save endpoint | Memperkuat SSOT |
| P1 | Rate limit dan payload constraints | Menekan abuse/DoS |
| P1 | Transactional template import | Mencegah hasil parsial |
| P1 | Loading/error state yang eksplisit | Mencegah salah tafsir tree kosong |
| P2 | Keyboard/touch reorder | Meningkatkan accessibility |
| P2 | Konsolidasi search UX | Mengurangi inkonsistensi interaksi |
| P2 | Per-owner template uniqueness | Memperbaiki multi-user behavior |
| P3 | Hilangkan inline handlers dan siapkan CSP | Security hardening |

## 9. Keputusan Audit

Page List Pekerjaan **belum direkomendasikan sebagai final production-ready** sebelum LP-01 sampai LP-04 ditutup.

Fungsi inti dan permission dasar sudah cukup matang, dan seluruh test terarah yang dijalankan berhasil. Risiko terbesar bukan pada kemampuan CRUD dasar, tetapi pada keamanan preview, sifat destructive full-state synchronization, transaction parsial, dan konflik perubahan antar-tab.

Audit ini dilakukan terhadap current working tree pada 13 Juni 2026. Visual browser UAT lintas viewport belum dijalankan dalam audit ini dan tetap diperlukan setelah perbaikan P0 diterapkan.

---

## 10. Verifikasi Independen (Claude, 13 Juni 2026)

Setiap temuan diperiksa ulang terhadap kode kerja saat ini. Seluruh 12 temuan **valid, tidak ada false positive.** Verdict, penajaman bukti, dan temuan tambahan di bawah.

### 10.1 Verdict per temuan

| Temuan | Verdict | Bukti verifikasi |
|---|---|---|
| LP-01 XSS preview template | **DIKONFIRMASI** | `list_pekerjaan.js:2586` (`${s.name}`) dan `:2588` (`${k.name}`) di-inject ke `innerHTML` **tanpa** `escapeHtml()`. Bandingkan list template `:2536` yang sudah `escapeHtml(t.name)`. Gap terisolasi 2 baris. Lihat penajaman 10.2. |
| LP-02 Commit parsial 207 | **DIKONFIRMASI (dengan penajaman)** | `@transaction.atomic` ada (`:953`); status `207` di `:1670`; penghapusan node omitted (`:1662-1668`) **tetap dieksekusi** lalu response dikembalikan tanpa `set_rollback`/raise → commit. Lihat 10.2 soal cakupan praktis. |
| LP-03 Stale write antar-tab | **DIKONFIRMASI** | `select_for_update()` di `:976` hanya menserialkan, tidak ada token revisi. Payload full-state + delete omitted = tab lama menimpa. Cache GET tree (`:839`) memperlebar jendela stale. |
| LP-04 Destructive tanpa impact preview | **DIKONFIRMASI** | `_reset_pekerjaan_related_data` (`:1237-1280`) meng-cascade hapus DetailAHSPProject, VolumePekerjaan, PekerjaanTahapan, VolumeFormulaState, TemplateAhspKoefFormulaState. Tidak ada impact summary di FE sebelum save. |
| LP-05 Dua endpoint save | **DIKONFIRMASI** | Legacy `api_save_list_pekerjaan` (`:637`) masih terdaftar di `urls.py:37`; docstring sendiri memperingatkan "panggilan berulang bisa menduplikasi data". UI hanya memanggil `/upsert/` (`list_pekerjaan.js:2056`) → legacy dormant-but-callable. |
| LP-06 Rate limit & batas payload | **DIKONFIRMASI** | Legacy save punya `@rate_limit(category='write')` (`:635`), tetapi `api_upsert_list_pekerjaan` (`:951-953`), `api_create_template` (`:9119-9122`), `api_import_template` (`:9661-9664`), dan `api_import_template_from_file` (`:9724-9727`) **tidak punya** rate limit. |
| LP-07 Import template parsial | **DIKONFIRMASI** | `api_import_template:9704` ambil `(stats, errors)`; `:9707` `increment_usage()` jalan **tanpa syarat**; `:9712-9721` mengembalikan `'ok': True` walau ada error (hanya dimasukkan sebagai `warnings`). |
| LP-08 Reorder tak accessible | **PLAUSIBEL** | Konsisten dengan implementasi drag HTML5 saja; tidak ada handler keyboard reorder/aria-live yang ditemukan. Perlu UAT touch untuk konfirmasi penuh. |
| LP-09 Initial load bergantung fetch | **DIKONFIRMASI** | `list_pekerjaan_view` (`views.py:96-102`) hanya render konteks project, tanpa bootstrap tree — kontras dengan `volume_pekerjaan_view` (`:117-126`) yang sudah SSR-bootstrap. |
| LP-10 Nama template unik global | **DIKONFIRMASI** | `PekerjaanTemplate.name = models.CharField(..., unique=True)` (`models.py:1290-1292`) — uniqueness global, bukan per-owner. |
| LP-11 Inline event handler | **DIKONFIRMASI** | `list_pekerjaan.html:356` `onclick="document.getElementById('import-template-file').click()"`. |
| LP-12 Dua pola search | **PLAUSIBEL** | Konsisten dengan pola yang sama di dashboard; UI/UX, perlu konfirmasi visual. |

### 10.2 Penajaman bukti

- **LP-01 — benar-benar dapat dieksekusi, tanpa mitigasi.** `innerHTML` memang **tidak** menjalankan `<script>` yang di-insert, tetapi payload `<img src=x onerror=...>` pada `k.name`/`s.name` akan tereksekusi. Tidak ada Content-Security-Policy di `config/` (sama seperti temuan dashboard F-01), jadi tidak ada lapisan pertahanan kedua. `previewName.textContent = t.name` (`:2573`) sudah aman; navigasi TOC (`:1712-1735`) juga sudah `escapeHtml`. Jadi perbaikan cukup pada 2 baris (`:2586`, `:2588`) — **risiko tinggi, effort rendah**. Prioritas P0 tepat.

- **LP-02 — valid, tetapi cakupan praktis lebih sempit dari kesan dokumen, dan fix-nya satu baris.** Endpoint punya **fase PRE-FLIGHT VALIDATION** (`:1005-1168`) yang mengembalikan `400` **sebelum** mutasi apa pun untuk seluruh error struktur/referensi. Maka `207` partial-commit hanya terjadi untuk error yang muncul **saat fase proses** (mis. "Gagal clone referensi" `:1453/1504/1524`, error DB tak terduga). Itu tetap nyata, tetapi pengguna normal jarang memicunya. Perbaikan minimal: sebelum `return` di `:1670`, jalankan `if errors: transaction.set_rollback(True)` (atau raise terkontrol) sehingga delete omitted ikut ter-rollback. Ini lebih kecil dari kesan "refactor besar" — meski refactor validate/plan/apply di Tahap 2 tetap ideal.

### 10.3 Temuan tambahan

- **LP-13 - Medium (perf, memperburuk LP-03/LP-06) - Re-indexing per-node = O(N) write + lock lama.** `api_upsert_list_pekerjaan` menggeser `ordering_index` ke temp-offset dengan **satu `save()` per node** untuk klasifikasi (`:1190-1192`), sub (`:1195-1197`), dan pekerjaan (`:1213-1215`), lalu menulis ulang lagi saat assign final. Untuk tree besar ini menghasilkan ratusan UPDATE individual dalam satu transaksi sambil memegang row-lock project (`:976`). Efeknya: latensi save naik linear terhadap ukuran tree, dan **lock ditahan lebih lama** sehingga memperparah kontensi stale-write (LP-03) serta memperbesar dampak ketiadaan batas node (LP-06). Rekomendasi: batasi jumlah node (LP-06), dan pertimbangkan `bulk_update(..., ['ordering_index'])` alih-alih save per baris.

- **Catatan konsistensi lintas-page:** Ketiadaan CSP dan pola "endpoint lama dibiarkan hidup berdampingan dengan endpoint baru" muncul **berulang** (dashboard F-01/F-10, di sini LP-01/LP-05/LP-11). Layak diangkat sebagai keputusan arsitektur tingkat-aplikasi (CSP bertahap + kebijakan deprecation endpoint), bukan tambalan per-page.

### 10.4 Kalibrasi prioritas

Urutan P0 di tabel bagian 8 sudah tepat. Satu penyesuaian effort: **LP-01 dan LP-02 berdampak tinggi tetapi effort rendah** (masing-masing perubahan beberapa baris) — keduanya layak dikerjakan lebih dulu sebagai quick win sebelum LP-03/LP-04 yang menuntut perubahan kontrak API + alur UI yang lebih besar.
