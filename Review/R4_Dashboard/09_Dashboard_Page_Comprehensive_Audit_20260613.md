# R4.9 - Audit Komprehensif Dashboard Page

**Tanggal audit:** 13 Juni 2026  
**Objek:** kondisi working tree saat audit, termasuk implementasi mass edit terbaru  
**URL utama:** `/dashboard/`  
**Status:** **LULUS BERSYARAT - perlu remediasi temuan High sebelum production sign-off**

## 1. Ruang Lingkup

Audit mencakup alur:

`URL -> view/middleware -> form/service/model/query -> template -> JavaScript/CSS -> respons pengguna`

Mode yang diperiksa:

1. Dashboard analytics dan daftar project.
2. Filter, sorting, pagination, server search, dan quick search.
3. Tambah project mode Sederhana/Lengkap melalui formset modal.
4. Pilih project dan bulk soft delete.
5. Mass edit inline.
6. Tampilan archived.
7. Detail, edit tunggal, duplicate, dan delete.
8. Upload Excel.
9. Export dashboard Excel/CSV, bulk Excel, project PDF, serta import/export backup JSON dari UI.
10. Desktop/mobile, dark-mode styling statis, aksesibilitas dasar, subscription gate, owner isolation, performa, dan SSOT.

## 2. Ringkasan Eksekutif

Fondasi backend dashboard cukup kuat: seluruh endpoint utama memakai autentikasi, query project dibatasi berdasarkan owner, write access dikendalikan middleware subscription, delete menggunakan soft delete, upload dibatasi ukuran/baris, dan mass edit terbaru sudah atomik serta memakai `ProjectForm`.

Automated test dashboard sebanyak **36 test lulus**. Namun test yang ada belum menangkap dua risiko High:

- data `sumber_dana` dimasukkan ke JavaScript inline sebagai `safe`, sehingga payload `</script>` dapat memutus blok script dan menjadi stored XSS;
- perubahan `tanggal_mulai` melalui mass edit tidak menjalankan reset/regenerasi progress yang dijalankan oleh edit tunggal.

Tingkat SSOT dashboard dinilai **Sedang/Rendah** karena aturan filter, status timeline, dan perhitungan progress masih memiliki beberapa implementasi paralel.

## 3. Hasil Per Mode

| Mode | Status | Catatan utama |
|---|---|---|
| Analytics/list | Bersyarat | Owner-scoped dan paginated; status timeline kontradiktif dan chart memiliki risiko XSS |
| Filter/sort/server search | Baik | Backend lengkap; implementasi diduplikasi di export |
| Quick search | Gagal | JavaScript mengakses elemen clear yang tidak dirender |
| Tambah project | Baik bersyarat | Validasi form dipakai; label mode "Lengkap" tidak benar-benar menampilkan seluruh field |
| Bulk select/delete | Baik desktop | Soft delete dan owner isolation benar; pengalaman mobile tidak konsisten |
| Mass edit | Baik bersyarat | Atomic, row-lock, owner-scoped; efek samping perubahan timeline tidak konsisten |
| Archived | Tidak lengkap | Data bisa difilter, tetapi pengguna tidak memiliki alur restore dan action umum menghasilkan 404 |
| Edit tunggal | Baik | Memakai form, transaksi, dan reset progress saat tanggal mulai berubah |
| Duplicate | Baik | Deep copy dan owner isolation diuji |
| Upload Excel | Baik | Batas 10 MB/2.000 baris, validasi form, formula handling, dan duplikasi nama diuji |
| Export | Baik bersyarat | Gating dan file nyata diuji; filter/progress/status belum SSOT |
| Mobile | Bersyarat | Card tersedia, tetapi checkbox bulk tampil saat pemicu bulk dinonaktifkan |

## 4. Temuan

### F-01 - HIGH - Stored XSS pada data chart

**Bukti**

- `dashboard/views.py:537-539` memakai `mark_safe(json.dumps(...))`.
- `dashboard/templates/dashboard/dashboard.html:711-713` memasukkan hasil tersebut langsung ke blok `<script>`.
- `sumber_dana` merupakan input bebas. `json.dumps()` tidak mengubah `</script>` menjadi bentuk aman untuk konteks HTML.

**Dampak**

Project yang dibuat atau diimpor dengan nilai berbahaya dapat menutup blok script dan mengeksekusi JavaScript saat dashboard dibuka. Owner scoping membatasi blast radius antar-user, tetapi tetap memungkinkan pengambilalihan sesi pengguna melalui file/data yang tidak tepercaya.

**Rekomendasi**

Gunakan `json_script` dan baca dengan `JSON.parse(document.getElementById(...).textContent)`. Hapus `mark_safe` dari payload chart. Tambahkan regression test dengan nilai `</script><script>...`.

### F-02 - HIGH - Mass edit melewati efek samping perubahan tanggal mulai

**Bukti**

- Edit tunggal membandingkan tanggal lama/baru dan memanggil `reset_project_progress(..., regenerate_weekly=True)` pada `dashboard/views.py:582-594`.
- Mass edit hanya menjalankan `form.save()` pada `dashboard/views_mass_edit.py:139`.

**Dampak**

Project yang tanggal mulainya diubah lewat mass edit dapat memiliki timeline baru tetapi progress weekly lama. Hasil dashboard, jadwal, dan laporan dapat tidak konsisten tergantung mode edit yang digunakan.

**Rekomendasi**

Pusatkan operasi update project pada service/domain function yang menangani validasi, save, dan efek samping timeline. Gunakan service yang sama pada edit tunggal, mass edit, duplicate metadata update, dan jalur lain yang mengubah timeline. Tambahkan test bahwa mass edit tanggal mulai mereset dan meregenerasi weekly progress secara atomik.

### F-03 - MEDIUM - Quick search rusak dan memiliki dua makna pencarian

**Bukti**

- Template merender `quickSearchInput` dan `quickSearchBtn`, tetapi tidak merender `clearSearchBtn`: `_project_stats_and_table.html:150-154`.
- JavaScript memakai `clearBtn.style` tanpa null guard pada `ux-enhancements.js:272-279`.
- Tombol `quickSearchBtn` tidak memiliki handler.
- Quick search hanya mencari 20 record pada page aktif, sedangkan search di panel filter mencari seluruh queryset server.

**Dampak**

Mengetik pada quick search memicu error JavaScript. Selain itu, dua kontrol pencarian terlihat serupa tetapi memiliki cakupan berbeda, sehingga hasil dapat menyesatkan.

**Rekomendasi**

Pilih satu pola. Rekomendasi utama: jadikan toolbar search sebagai server search dan sinkronkan ke parameter `search`; hilangkan search duplikat dalam panel. Jika quick search tetap dipakai, labeli "Cari di halaman ini", render tombol clear, dan tambahkan test DOM.

### F-04 - MEDIUM - Status timeline tidak memiliki satu definisi

**Bukti**

- Tanggal selesai yang sudah lewat disebut `selesai` pada view/detail/filter dan chart: `dashboard/views.py:173-179`, `412-418`, `557-570`.
- Record yang sama ditampilkan sebagai `Terlambat` dalam analytics: `dashboard/views.py:503-508`.
- Bulk export juga menyebut tanggal lewat sebagai `Terlambat`, sedangkan CSV/PDF helper menyebutnya `Selesai`: `dashboard/views_bulk.py` dan `dashboard/views_export.py:439-452`.

**Dampak**

Satu project dapat tampil sebagai "Selesai" dan "Terlambat" pada page/file berbeda. Model tidak memiliki completion state aktual, sehingga tanggal target diperlakukan sebagai bukti project selesai.

**Rekomendasi**

Definisikan status domain tunggal. Minimal pisahkan `timeline_status` (`belum_mulai`, `berjalan`, `mendekati_deadline`, `terlambat`) dari `completion_status` aktual. Jangan menyimpulkan "selesai" hanya dari target date.

### F-05 - MEDIUM - Archived mode tidak memiliki alur pengguna yang lengkap

**Bukti**

- Filter `is_active=false` tersedia.
- Detail, edit, duplicate, dan delete mengambil project dengan `is_active=True`, misalnya `dashboard/views.py:552`, `581`, `613`, `628`.
- Tombol archive/unarchive sengaja dihapus dari UI, sementara endpoint masih ada.
- Mass edit tetap dapat mengambil project inactive karena endpoint tidak memfilter `is_active`.

**Dampak**

Pengguna dapat melihat project archived, tetapi tombol aksi umum berakhir 404 dan tidak ada restore. Di sisi lain, archived project masih dapat diedit melalui mass edit, menghasilkan aturan state yang tidak konsisten.

**Rekomendasi**

Tentukan kebijakan tunggal:

- jika archived adalah recycle bin, sediakan detail read-only, restore, dan permanent-delete sesuai retention policy;
- jika pemulihan hanya admin, jangan tampilkan archived kepada user biasa dan blok mass edit inactive.

### F-06 - MEDIUM - Filter dan progress calculation diduplikasi

**Bukti**

- Filter dashboard berada di `dashboard/views.py:89-218`.
- Salinannya berada di `dashboard/views_export.py:22-148`.
- Weighted progress dihitung di dashboard, dihitung ulang pada export XLSX, lalu memiliki helper kedua `_compute_weighted_progress_map()` pada `views_export.py:354`.

**Dampak**

Perubahan aturan dapat membuat layar, CSV, XLSX, dan PDF menghasilkan kumpulan/status/progress berbeda. Biaya maintenance dan test meningkat.

**Rekomendasi**

Ekstrak:

- `ProjectDashboardQueryService.apply_filters(queryset, cleaned_filters)`;
- `TimelineStatusService`;
- `ProjectProgressService.compute_map(projects)`.

View dan seluruh exporter harus memakai service yang sama.

### F-07 - MEDIUM - Error perhitungan progress disembunyikan

**Bukti**

`dashboard/views.py:380-384` menangkap seluruh exception, menetapkan progress `0.0`, lalu `pass`. Pola serupa ada pada export.

**Dampak**

Kerusakan data atau regresi kalkulasi terlihat sebagai progress nol yang valid. Tidak ada observability untuk membedakan "belum ada progress" dan "gagal menghitung".

**Rekomendasi**

Log exception dengan `project_id`, gunakan metric/error reporting, dan tampilkan state "tidak dapat dihitung" jika tepat. Tangkap exception yang memang diharapkan, bukan `Exception` secara umum.

### F-08 - MEDIUM - Mobile bulk UI tidak konsisten

**Bukti**

- Mobile card selalu merender checkbox: `_project_stats_and_table.html:372-374`.
- Tombol "Pilih Project" dinonaktifkan pada lebar `<=992px`: `mass-edit-toggle.js:139-146`.
- Handler bulk hanya membaca checkbox desktop: `_project_stats_and_table.html:630-632`.

**Dampak**

Checkbox mobile terlihat interaktif tetapi tidak terhubung ke bulk workflow. Pengguna tidak dapat memahami atau menyelesaikan aksi.

**Rekomendasi**

Sembunyikan checkbox mobile jika bulk memang desktop-only, atau implementasikan selection state tunggal yang menyinkronkan desktop/mobile dan izinkan bulk delete pada mobile. Mass edit dapat tetap desktop-only.

### F-09 - LOW - Pagination tidak membangun query string secara aman

**Bukti**

Pagination menyusun `&{{ key }}={{ value }}` secara manual pada `_project_stats_and_table.html:539`, `559`, `567`, dan `575`, sedangkan link export sudah memakai `request.GET.urlencode`.

**Dampak**

Nilai search yang mengandung `&`, `+`, atau karakter khusus dapat berubah makna saat pindah halaman.

**Rekomendasi**

Gunakan helper query-string template yang melakukan encoding dan mengganti hanya parameter `page`.

### F-10 - LOW - Implementasi mass edit lama masih hidup sebagai dead code

**Bukti**

- URL sudah memakai `dashboard/views_mass_edit.py`.
- Fungsi lama `mass_edit_bulk_update` masih ada pada `dashboard/views.py:821-979`.
- Implementasi lama menelan validasi, mencatat request body, dan mengembalikan detail exception.

**Dampak**

Ada dua implementasi bernama sama dengan tingkat keamanan berbeda. Risiko salah import/routing dan kebingungan maintenance tetap tinggi.

**Rekomendasi**

Hapus fungsi lama setelah memastikan tidak ada import tersisa. Pertahankan satu endpoint dan satu test suite.

### F-11 - LOW - Mode tambah "Lengkap" tidak benar-benar lengkap

**Bukti**

Modal formset menampilkan field wajib dan stakeholder, tetapi tidak menampilkan `deskripsi`, `kategori`, atau flag sistem. Tombol tetap diberi label "Lengkap".

**Dampak**

Ekspektasi pengguna tidak sesuai dengan isi mode. Data tersebut baru dapat diisi melalui edit tunggal.

**Rekomendasi**

Ubah label menjadi "Stakeholder lengkap" atau render seluruh field bisnis yang memang dapat diedit saat create. Flag sistem tidak perlu diekspos.

## 5. SSOT Assessment

| Area | Nilai | Penilaian |
|---|---|---|
| Owner isolation | Tinggi | Konsisten memakai owner-scoped queryset |
| Subscription write gate | Tinggi | Terpusat pada middleware/entitlement |
| Form validation | Cukup tinggi | Create/edit/upload/mass edit memakai `ProjectForm` |
| Timeline side effects | Rendah | Edit tunggal dan mass edit berbeda |
| Timeline status | Rendah | Definisi tersebar dan kontradiktif |
| Dashboard filters | Sedang/rendah | Disalin ke exporter |
| Progress calculation | Rendah | Sedikitnya tiga implementasi/alur |
| Archived lifecycle | Rendah | UI, endpoint, dan state action tidak selaras |

## 6. Rekomendasi Restrukturisasi

Urutan refactor yang disarankan:

1. Tambah `dashboard/services/project_update.py` untuk update metadata dan timeline side effects.
2. Tambah `dashboard/services/dashboard_query.py` untuk filter/sort.
3. Tambah `dashboard/services/project_progress.py` untuk batch weighted progress.
4. Tambah definisi status domain tunggal, idealnya pada service atau model enum/property yang teruji.
5. Pindahkan script inline besar dari template ke modul JS dan kirim data dengan `json_script`.
6. Hapus mass edit lama dan endpoint bulk yang tidak lagi menjadi bagian kebijakan produk.
7. Tetapkan lifecycle archived beserta permission dan retention policy.

## 7. Test yang Dijalankan

Perintah:

```text
python manage.py test dashboard --verbosity 2 --keepdb
```

Hasil:

```text
Ran 36 tests in 42.036s
OK
```

Test tambahan yang wajib:

1. Stored-XSS regression untuk seluruh chart payload.
2. Mass edit tanggal mulai mereset progress dan rollback jika reset gagal.
3. Konsistensi status antara list, detail, filter, analytics, CSV, XLSX, dan PDF.
4. Quick search tanpa console error.
5. Archived action matrix.
6. Pagination dengan search berisi karakter khusus.
7. Browser test desktop/mobile untuk bulk selection, modal, keyboard, focus, dan dark mode.

## 8. Prioritas Remediasi

| Urutan | Item | Gate |
|---|---|---|
| P0 | F-01 stored XSS chart | Wajib sebelum production |
| P0 | F-02 mass edit timeline side effect | Wajib sebelum mass edit dirilis |
| P1 | F-03 quick search | Wajib sebelum UI sign-off |
| P1 | F-04 status timeline SSOT | Wajib sebelum laporan dianggap konsisten |
| P1 | F-05 archived lifecycle | Keputusan produk + implementasi |
| P1 | F-06 progress/filter SSOT | Refactor sebelum fitur dashboard berkembang |
| P2 | F-07 sampai F-11 | Hardening dan penyempurnaan UX |

## 9. Kesimpulan

Dashboard berfungsi dan test backend yang tersedia lulus, tetapi belum layak diberi status final production-ready. Remediasi F-01 dan F-02 adalah syarat utama. Setelah itu, quick search, definisi status, dan lifecycle archived perlu dibereskan agar page konsisten secara fungsi, SSOT, dan UX.

Audit visual browser belum dieksekusi dalam sesi ini. Validasi responsive, dark mode, focus order, screen reader, chart rendering, dan console browser tetap harus dilakukan melalui UAT setelah remediasi kode.

---

## 10. Verifikasi Independen (Claude, 13 Juni 2026)

Setiap temuan diperiksa ulang terhadap kode kerja saat ini. Verdict, koreksi, dan temuan tambahan di bawah.

### 10.1 Verdict per temuan

| Temuan | Verdict | Catatan verifikasi |
|---|---|---|
| F-01 Stored XSS chart | **DIKONFIRMASI (naikkan ke kritikal)** | `views.py:537-539` `mark_safe(json.dumps(...))`; template `dashboard.html:711-713` inject via `\|safe`. Lihat koreksi 10.2 soal payload mana yang benar-benar rentan + absennya CSP. |
| F-02 Mass edit lewati side effect tanggal | **DIKONFIRMASI** | `views_mass_edit.py:138-139` hanya `form.save()`; tidak ada `reset_project_progress`. Edit tunggal `views.py:592-593` memanggilnya. Mass edit juga melewati `messages.warning`. |
| F-03 Quick search rusak | **DIKONFIRMASI (lebih parah dari tertulis)** | `clearSearchBtn` tidak dirender; `ux-enhancements.js:274` DAN `:278` keduanya akses `clearBtn.style` tanpa guard. Mengetik 1 karakter apa pun melempar `TypeError` (cabang kosong & non-kosong sama-sama crash). Handler ESC `:348` juga crash. Hanya handler click `:325` yang ter-guard. `quickSearchBtn` benar tanpa handler. |
| F-04 Status timeline tak ber-SSOT | **DIKONFIRMASI (bukti diperkuat)** | `status_selesai` (`views.py:412-418`) dan `overdue_projects` (`views.py:503-508`) memakai **kondisi identik** `tanggal_selesai < today`, tetapi diberi label "Selesai" vs "Terlambat" **dalam satu view yang sama**. Bukan sekadar tersebar antar file — kontradiktif di satu halaman. |
| F-05 Archived tak punya alur lengkap | **DIKONFIRMASI** | Detail/edit/duplicate/delete pakai `is_active=True` (`views.py:552,581,613,628`). Mass edit `views_mass_edit.py:70-76` query `filter(pk__in=..., owner=...)` **tanpa** filter `is_active` → project archived bisa diedit massal. |
| F-06 Filter/progress duplikat | **DIKONFIRMASI** | Logika filter di `views.py` disalin ke `views_export.py`; progress dihitung di dashboard dan ulang di exporter. |
| F-07 Error progress disembunyikan | **DIKONFIRMASI** | `views.py:380-384` `except Exception: project.progress_realisasi = 0.0; pass`. Pola sama di fallback rekap `views.py:334-335`. Catatan: loop progress utama justru sudah batched/N+1-aware (`views.py:311-321`) — engineering bagus, hanya error-handling-nya yang buram. |
| F-08 Mobile bulk UI tak konsisten | **DIKONFIRMASI** | Card mobile selalu render checkbox `_project_stats_and_table.html:372-374`; toggle dinonaktifkan `<=992px` di `mass-edit-toggle.js:140-142`. |
| F-09 Pagination query string tak aman | **DIKONFIRMASI** | `&{{ key }}={{ value }}` manual di `:539,559,567,575`. Framing audit tepat: ini bug integritas parameter (bukan XSS — Django tetap auto-escape HTML). Nilai search berisi `&`/`+`/`#` akan pecah/berubah saat ganti halaman. |
| F-10 Mass edit lama = dead code | **DIKONFIRMASI** | `views.py:821` masih ada `def mass_edit_bulk_update`; `urls.py:10` impor versi baru dari `views_mass_edit`. Versi lama benar-benar dead, tapi tetap berbahaya: ia mem-`logger.info` body request mentah (`views.py:842`) → kebocoran data bila ter-route ulang tak sengaja. |
| F-11 Mode "Lengkap" tak lengkap | **DIKONFIRMASI (label)** | Akurat sebagai isu UX/label. |

**Kesimpulan verifikasi:** seluruh 11 temuan valid. Tidak ada false positive. Beberapa undersold (lihat di atas).

### 10.2 Koreksi & penajaman

- **F-01 — presisi payload & severity.** Dari tiga payload chart, hanya `projects_by_sumber` yang membawa input bebas (`sumber_dana`); `projects_by_year` (integer tahun) dan `budget_by_year` (Decimal) tidak user-controllable, jadi keduanya tidak rentan. Rekomendasi audit ("hapus `mark_safe` dari semua payload chart") tetap benar dan aman, tapi vektor eksploitasi sesungguhnya hanya lewat `sumber_dana`. **Tidak ditemukan Content-Security-Policy** di `config/` (tidak ada `CONTENT_SECURITY_POLICY`/middleware CSP) — artinya tidak ada lapisan mitigasi kedua, sehingga severity F-01 layak dinaikkan ke **P0 kritikal**, bukan sekadar High. Pola perbaikan `json_script` sudah pernah dipakai tim untuk fix XSS template library (lihat commit `b5d2d83b`), jadi sudah ada preseden internal.

### 10.3 Temuan tambahan

- **F-12 - LOW/DEFENSE-IN-DEPTH - Tidak ada Content-Security-Policy.** Tidak ada header CSP di seluruh `config/`. CSP dengan `script-src` tanpa `'unsafe-inline'` akan menetralkan kelas kerentanan seperti F-01 walau ada inline injection. Saat ini dashboard sangat bergantung pada inline `<script>` + data inline, jadi CSP ketat perlu disertai migrasi data ke `json_script` (sejalan dengan rekomendasi restrukturisasi butir 5). Rekomendasi: tambahkan CSP report-only dulu, lalu enforce setelah inline script dibersihkan.

- **F-13 - LOW - Fallback rekap dalam loop masih bisa per-project.** `views.py:328-335` memanggil `compute_rekap_for_project(project)` di dalam loop untuk project yang `budgeted_cost`-nya kosong/<=0. Loop utama sudah dibatch dengan baik, tapi jalur fallback ini tetap berpotensi N×query untuk project lama yang belum punya `budgeted_cost`. Dampak performa hanya muncul pada akun dengan banyak project legacy di satu halaman; bukan blocker, tapi layak dipindah ke service progress batch (sejalan F-06).

### 10.4 Catatan untuk daftar test wajib (bagian 7)

Tambahan yang disarankan ke daftar test:
- Regression khusus `sumber_dana = '</script><script>alert(1)</script>'` yang dibuat lewat **create, upload Excel, dan import JSON** (ketiga jalur menulis `sumber_dana`), memverifikasi tidak ada break-out script pada dashboard.
- Test bahwa mass edit menolak / tidak menyentuh project `is_active=False` (mengunci F-05).

---

## 11. Audit UI/UX Dashboard

Bagian ini menilai implementasi UI/UX berdasarkan template, CSS, dan JavaScript. Temuan visual tetap perlu dikonfirmasi melalui browser UAT karena audit ini belum mencakup pengamatan langsung pada seluruh viewport dan perangkat input.

### 11.1 Implementasi yang Sudah Baik

1. **Dark mode memiliki cakupan luas.** Styling mendukung theme eksplisit melalui `data-bs-theme="dark"` dan preferensi sistem melalui `prefers-color-scheme: dark`. Cakupan mencakup toolbar, modal, analytics, stat pill, chart card, mass edit, dan beberapa state form.
2. **Reduced motion dihormati.** `dashboard/static/dashboard/css/ux-enhancements.css:941` menyediakan penyesuaian untuk `prefers-reduced-motion`.
3. **Aksi icon-only memiliki accessible name.** Tombol detail, edit, export, dan delete pada desktop/mobile menggunakan kombinasi `title` dan `aria-label` di `_project_stats_and_table.html:285-301` dan `:431-445`.
4. **Tabel mendukung pekerjaan dengan data lebar.** Header sticky, kolom sticky saat mass edit, resizable columns, dan horizontal scroll membantu penggunaan tabel kompleks.
5. **Tersedia mobile card view dan banyak responsive breakpoint.** Ini lebih baik daripada memaksa seluruh tabel desktop tetap tampil pada layar kecil, walaupun bulk workflow mobile masih tidak konsisten seperti F-08.
6. **Toolbar menyesuaikan ruang layar.** Label beberapa tombol disembunyikan pada viewport kecil, sementara `title` tetap memberi konteks bagi pointer user.
7. **Fondasi live announcement sudah tersedia.** `ux-enhancements.js:729-741` membuat region `role="status"` dan `aria-live="polite"` serta mengekspos `window.announce()`.

### UX-01 - HIGH - Warna dan label status saling bertentangan

**Bukti**

- `_project_stats_and_table.html:310` dan `:384` menampilkan badge `bg-danger` dengan label **Selesai** ketika tanggal selesai telah lewat.
- `dashboard.html:38-42` menghitung kondisi tanggal yang sama sebagai **Terlambat** pada stat pill.
- `dashboard.html:965` mempertahankan warna danger untuk kategori Selesai pada chart.

**Dampak**

Merah secara umum dibaca sebagai bahaya, gagal, atau terlambat, bukan keberhasilan. Project yang sama dapat terlihat sebagai badge merah “Selesai” di daftar dan masuk hitungan “Terlambat” pada analytics. Ini merupakan manifestasi visual langsung dari F-04.

**Rekomendasi**

Perbaiki bersama F-04 dengan status domain tunggal. Gunakan warna hijau atau netral untuk pekerjaan benar-benar selesai, merah untuk terlambat, kuning untuk mendekati deadline, dan abu-abu untuk belum mulai. Jangan menentukan status ulang di template.

### UX-02 - MEDIUM - Popover HTML bergantung pada sanitizer Bootstrap

**Bukti**

`dashboard.html:38-48` memakai `data-bs-html="true"` dan memasukkan nama project ke `data-bs-content`.

Django melakukan HTML escaping dan Bootstrap 5.3.3 memakai sanitizer default, sehingga tidak dikategorikan sebagai XSS aktif pada konfigurasi sekarang. Namun browser mendekode attribute value sebelum Bootstrap memprosesnya dan tag yang masuk allowlist dapat tetap ditafsirkan sebagai HTML. Keamanannya juga bergantung pada sanitizer tidak dimatikan atau dilemahkan pada masa depan.

**Dampak**

- markup yang diizinkan sanitizer dapat memengaruhi tampilan popover;
- perubahan konfigurasi `sanitize: false`, perubahan allowlist, atau downgrade dependency dapat mengubahnya menjadi stored XSS;
- data user dan markup presentasi bercampur dalam satu attribute.

**Rekomendasi**

Jangan gunakan HTML mode untuk data user. Bangun list popover dengan DOM API dan `textContent`, atau gunakan popover teks biasa. Tambahkan regression test untuk nama project yang mengandung tag dan attribute berbahaya.

### UX-03 - MEDIUM - Payload HTML per project terduplikasi

**Bukti**

- `_project_stats_and_table.html:247` membuat `data-search` dari sekitar 22 field.
- Field yang sama kembali disimpan sebagai banyak attribute `data-*` mulai `:248`.
- Mobile card mengulang gabungan `data-search` yang sama pada `:362`.
- Field panjang seperti deskripsi dan keterangan ikut disalin ke attribute HTML.

**Dampak**

Untuk setiap project, data yang sama dikirim beberapa kali. Pada page dengan 20 record, hal ini meningkatkan ukuran HTML, parsing DOM, penggunaan memori, dan biaya update tanpa menambah informasi baru.

**Rekomendasi**

Tentukan satu sumber data frontend. Pilihan yang lebih aman:

1. kirim hanya attribute yang benar-benar diperlukan oleh interaction;
2. bangun searchable text di JavaScript dari state canonical;
3. gunakan satu JSON bootstrap terstruktur jika mass edit memerlukan seluruh field;
4. ukur response size dan DOM node/attribute count sebelum dan sesudah refactor.

### UX-04 - MEDIUM - Empty state belum mengarahkan user ke tindakan berikutnya

**Bukti**

- Empty state desktop di `_project_stats_and_table.html:351-354` hanya berupa satu baris teks.
- Empty state mobile di `:455-457` sudah memiliki icon dan penjelasan, tetapi belum mempunyai CTA.

**Dampak**

User baru mengetahui bahwa project belum tersedia, tetapi tidak diarahkan secara eksplisit untuk membuat project atau mengunggah Excel. Empty state merupakan titik onboarding utama sehingga seharusnya langsung menjawab “apa yang harus dilakukan berikutnya”.

**Rekomendasi**

Gunakan satu komponen empty state responsive dengan:

- judul dan penjelasan singkat;
- CTA utama **Tambah Project**;
- CTA sekunder **Upload Excel**;
- link template/contoh bila relevan;
- state berbeda ketika hasil kosong disebabkan filter, dengan CTA **Reset Filter**.

### UX-05 - LOW - Live region tersedia tetapi belum terintegrasi menyeluruh

Klaim bahwa dashboard sama sekali tidak memiliki `aria-live` tidak tepat. `ux-enhancements.js:729-741` sudah membuat live region global.

Masalah yang terverifikasi adalah perubahan `selectedCount` di `_project_stats_and_table.html:691` dan `massEditChangeCount` di `mass-edit-toggle.js:303-307` hanya mengubah `textContent` elemen visual. Tidak ditemukan pemanggilan `window.announce()` pada kedua alur tersebut. Accessibility toast juga bergantung pada implementasi global `DP.toast`.

**Rekomendasi**

- panggil announcer saat jumlah pilihan atau perubahan mass edit berubah secara bermakna;
- hindari announcement pada setiap keystroke jika akan terlalu bising;
- pastikan toast global mempunyai semantics `status`/`alert` sesuai severity;
- tambahkan screen-reader UAT untuk search, bulk selection, mass edit, save, dan error.

### UX-06 - LOW - Teks progress mempunyai kontras yang tidak deterministik

**Bukti**

`_project_stats_and_table.html:332-334` menampilkan progress dengan ukuran `11px`, warna putih, dan `mix-blend-mode: difference`.

**Dampak**

Blend mode menghasilkan warna berdasarkan background akhir sehingga keterbacaan dapat berubah menurut warna progress bar, browser, dan theme. Ukuran 11px juga terlalu kecil untuk informasi numerik yang penting.

**Rekomendasi**

Gunakan ukuran minimum yang lebih nyaman, warna dengan rasio kontras terukur, dan background/outline teks eksplisit. Uji kombinasi progress 0%, rendah, 50%, dan 100% pada light/dark mode.

### UX-07 - LOW - Derivasi status diulang di beberapa lapisan

**Bukti**

Perbandingan tanggal dan penentuan badge dilakukan kembali pada tabel desktop, mobile card, chart mapping, dan backend. Ini mengikat presentation layer pada aturan domain dan memperkuat F-04/F-06.

**Dampak**

Perbaikan status pada satu lokasi mudah tidak diterapkan pada lokasi lain. Label, warna, filter, chart, dan export dapat kembali berbeda.

**Rekomendasi**

Backend mengirim satu nilai status canonical beserta presentation token yang terbatas, misalnya `status_code`. Template memetakan `status_code` melalui satu component/helper, bukan menghitung tanggal secara mandiri.

### 11.2 Hubungan dengan Temuan Sebelumnya

- F-03 tetap merupakan cacat UX utama karena quick search gagal segera setelah user mengetik.
- UX-01 adalah dampak visual dari F-04 dan harus diselesaikan dalam satu perubahan domain.
- UX-07 merupakan bagian presentation-layer dari masalah SSOT pada F-04 dan F-06.
- UX-04 memperluas F-11: masalah onboarding bukan hanya label mode form, tetapi juga keadaan awal sebelum user memiliki project.
- UX-05 memperjelas bahwa fondasi accessibility tersedia, tetapi integrasinya belum lengkap.

### 11.3 Prioritas UI/UX

| Urutan | Item | Alasan |
|---|---|---|
| P0 | F-03 quick search | Kontrol utama gagal saat digunakan |
| P0 | UX-01 + F-04 status canonical | Informasi status salah dan membingungkan |
| P1 | UX-04 empty state | Dampak langsung pada onboarding |
| P1 | UX-02 popover text-safe | Mengurangi ketergantungan security laten |
| P1 | UX-03 deduplikasi payload | Mengurangi bobot HTML dan kompleksitas state |
| P2 | UX-05 live announcement integration | Melengkapi accessibility workflow |
| P2 | UX-06 progress readability | Memperbaiki keterbacaan |
| P2 | UX-07 status presentation SSOT | Mencegah regresi lintas tampilan |

### 11.4 Batas Validasi

Temuan di atas telah diverifikasi dari kode, tetapi hal-hal berikut tetap memerlukan browser UAT:

1. kontras aktual seluruh badge dan progress pada light/dark mode;
2. behavior popover dengan nama project berisi markup;
3. keyboard focus order dan focus return setelah modal;
4. announcement pada NVDA/JAWS/VoiceOver;
5. layout toolbar, table, card, dan modal pada breakpoint utama;
6. touch target dan bulk interaction pada perangkat mobile;
7. dampak ukuran HTML melalui Network dan Performance panel.
