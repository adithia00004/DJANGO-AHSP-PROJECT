# 📖 Panduan Pengguna - Sistem Manajemen Project AHSP

**Aplikasi:** Dashboard Project & Deep Copy
**Versi:** 4.0
**Tanggal:** 6 November 2025
**Bahasa:** Indonesia

---

## 📑 Daftar Isi

1. [Pengenalan](#pengenalan)
2. [Memulai](#memulai)
3. [Dashboard Project](#dashboard-project)
4. [Manajemen Project](#manajemen-project)
5. [Fitur Analytics](#fitur-analytics)
6. [Filter & Pencarian](#filter--pencarian)
7. [Operasi Bulk](#operasi-bulk)
8. [Export Data](#export-data)
9. [Deep Copy Project](#deep-copy-project)
10. [Admin Panel](#admin-panel)
11. [Tips & Trik](#tips--trik)
12. [FAQ](#faq)

---

## 🎯 Pengenalan

### Apa itu Sistem Manajemen Project AHSP?

Sistem ini adalah aplikasi web untuk mengelola project-project konstruksi dengan fitur:
- ✅ **Dashboard Analytics** - Statistik dan grafik real-time
- ✅ **Manajemen Project** - CRUD lengkap untuk project
- ✅ **Timeline Tracking** - Monitor tanggal mulai, selesai, dan durasi
- ✅ **Deep Copy** - Duplikasi project lengkap dengan semua detail
- ✅ **Filtering Canggih** - 8 filter untuk pencarian data
- ✅ **Bulk Operations** - Operasi massal untuk efisiensi
- ✅ **Export Multi-Format** - Excel, CSV, dan PDF

### Siapa yang Menggunakan?

- **Project Manager** - Mengelola multiple projects
- **Estimator** - Membuat dan mengelola AHSP
- **Admin** - Mengelola users dan sistem
- **Supervisor** - Monitoring progress project

---

## 🚀 Memulai

### 1. Login ke Sistem

1. Buka browser dan akses: `https://yourdomain.com/`
2. Klik tombol **"Login"** di pojok kanan atas
3. Masukkan **username** dan **password** Anda
4. Klik **"Masuk"**

**Catatan:** Jika Anda lupa password, hubungi administrator sistem.

### 2. Navigasi Utama

Setelah login, Anda akan melihat menu navigasi:

```
┌─────────────────────────────────────────────────┐
│  LOGO    [Dashboard]  [Admin]  [Profile]  [Logout] │
└─────────────────────────────────────────────────┘
```

- **Dashboard** - Halaman utama dengan daftar project
- **Admin** - Panel admin (hanya untuk admin)
- **Profile** - Profil dan pengaturan akun Anda
- **Logout** - Keluar dari sistem

---

## 📊 Dashboard Project

### Tampilan Utama

Dashboard menampilkan 3 bagian utama:

1. **Analytics Section** (dapat disembunyikan/ditampilkan)
2. **Filter & Search Bar**
3. **Tabel Project**

### 1. Analytics Section

Klik tombol **"Tampilkan Analytics"** untuk melihat:

#### Summary Cards (4 Kartu Statistik)

```
┌─────────────┬─────────────┬─────────────┬─────────────┐
│ Total       │ Total       │ Project     │ Project     │
│ Project     │ Anggaran    │ Tahun Ini   │ Berjalan    │
│             │             │             │             │
│   150       │ Rp 50 M     │    45       │    12       │
└─────────────┴─────────────┴─────────────┴─────────────┘
```

- **Total Project** - Jumlah semua project aktif Anda
- **Total Anggaran** - Total anggaran semua project
- **Project Tahun Ini** - Project yang dimulai tahun ini
- **Project Berjalan** - Project yang sedang berlangsung

#### Grafik Interaktif (2 Charts)

**Projects per Tahun** (Bar Chart)
```
|     📊
| ██  ██
| ██  ██  ██
| ██  ██  ██
└─────────────
 2023 2024 2025
```
Menampilkan distribusi project per tahun.

**Projects per Sumber Dana** (Pie Chart)
```
     🥧
   ╱───╲
  ╱ 40% ╲
 │ APBN  │
 │  30%  │
  ╲ DAU ╱
   ╲───╱
```
Menampilkan proporsi sumber dana project.

#### Upcoming Deadlines & Overdue

**Upcoming Deadlines** (7 hari ke depan)
- Menampilkan 5 project yang akan jatuh tempo
- Status badge: 🟡 **Segera Jatuh Tempo**

**Overdue Projects**
- Menampilkan 5 project yang terlambat
- Status badge: 🔴 **Terlambat**

---

## 📝 Manajemen Project

### Membuat Project Baru

#### Metode 1: Form Inline (Dashboard)

1. Di halaman Dashboard, scroll ke bagian **"Tambah Project Baru"**
2. Isi form dengan data project:

**Field Wajib** (harus diisi):
- **Nama Project** - Minimal 3 karakter
- **Tanggal Mulai** - Format: DD/MM/YYYY
- **Sumber Dana** - Contoh: APBN, DAU, APBD
- **Lokasi Project** - Lokasi pelaksanaan
- **Nama Client** - Nama pemberi kerja
- **Anggaran Owner** - Format: Rp 1.000.000.000 atau 1000000000

**Field Opsional**:
- **Tanggal Selesai** - Target penyelesaian
- **Durasi (hari)** - Akan otomatis terisi jika tanggal selesai diisi
- **Kategori** - Kategori project
- **Deskripsi** - Deskripsi singkat
- **Keterangan Project 1 & 2** - Info tambahan
- **Data Client** - Jabatan, Instansi
- **Data Kontraktor** - Nama, Instansi
- **Data Konsultan** - Perencana & Pengawas

3. Klik tombol **"Simpan Project"**
4. Project baru akan muncul di tabel

#### Metode 2: Upload Excel

1. Klik tombol **"Upload Excel"** di dashboard
2. Download template Excel dengan klik **"Download Template"**
3. Isi template dengan data project Anda
4. Upload file Excel yang sudah diisi
5. Sistem akan validasi dan import data

**Format Template Excel:**
```
| nama | tanggal_mulai | sumber_dana | lokasi_project | nama_client | anggaran_owner | ... |
|------|---------------|-------------|----------------|-------------|----------------|-----|
```

**Tips Upload Excel:**
- Maksimal 2000 baris data
- Format tanggal: YYYY-MM-DD atau DD/MM/YYYY
- Format anggaran: angka tanpa simbol (1000000000)
- Jika ada error, sistem akan menampilkan baris yang error

### Melihat Detail Project

1. Di tabel project, klik **nama project** atau tombol **"Detail"**
2. Anda akan melihat halaman detail dengan 3 section:

**Info Project**
- Index Project, Nama, Tahun
- Sumber Dana, Lokasi, Client
- Anggaran, Status

**Timeline Pelaksanaan**
```
┌────────────────────────────────────────┐
│ 📅 Timeline Pelaksanaan                │
├────────────────────────────────────────┤
│ Tanggal Mulai:    01/01/2025          │
│ Tanggal Selesai:  31/12/2025          │
│ Durasi:           365 hari             │
│                                        │
│ Progress Bar:                          │
│ ████████░░░░░░░░░░░ 45%               │
│                                        │
│ Status: 🟢 Berjalan                    │
└────────────────────────────────────────┘
```

**Aksi yang Tersedia**
- **Edit** - Ubah data project
- **Duplikasi** - Copy project sederhana
- **Deep Copy** - Copy project lengkap dengan AHSP
- **Export PDF** - Download laporan project
- **Hapus** - Soft delete project (arsip)

### Mengedit Project

1. Di halaman detail project, klik tombol **"Edit Project"**
2. Ubah data yang ingin diubah
3. Klik **"Simpan Perubahan"**

**Yang Tidak Bisa Diubah:**
- Index Project (auto-generated)
- Created At / Updated At (timestamps)
- Owner (pemilik project)

### Menghapus Project

**⚠️ Soft Delete:** Project tidak benar-benar dihapus, hanya diarsipkan.

1. Di halaman detail project, klik tombol **"Hapus Project"**
2. Konfirmasi penghapusan
3. Project akan dipindahkan ke arsip (is_active = False)

**Mengembalikan Project dari Arsip:**
- Gunakan filter "Status: Archived" di dashboard
- Pilih project yang ingin dikembalikan
- Gunakan bulk action **"Unarchive"**

---

## 📈 Fitur Analytics

### Menggunakan Analytics

1. Di dashboard, klik tombol **"Tampilkan Analytics"**
2. Analytics section akan terbuka dengan animasi
3. Scroll untuk melihat semua data:
   - 4 Summary Cards di atas
   - 2 Charts di tengah
   - Upcoming Deadlines & Overdue di bawah

### Interpretasi Data

#### Total Anggaran

Format: **Rp XX.X M** (Milyar) atau **Rp XX.X T** (Triliun)

Contoh:
- Rp 1.5 M = Rp 1.500.000.000
- Rp 2.3 T = Rp 2.300.000.000.000

#### Status Project

- 🟢 **Berjalan** - Tanggal sekarang antara mulai dan selesai
- 🔴 **Terlambat** - Tanggal selesai sudah terlewat
- ⚪ **Belum Mulai** - Tanggal mulai belum tiba
- ⚫ **Archived** - Project diarsipkan

#### Progress Bar

Perhitungan: `(Hari Berlalu / Total Durasi) × 100%`

Contoh:
- Mulai: 01/01/2025
- Selesai: 31/12/2025
- Hari ini: 18/06/2025
- Progress: 168/365 × 100% = **46%**

---

## 🔍 Filter & Pencarian

### 8 Filter yang Tersedia

#### 1. Search (Pencarian Teks)

Ketik di kolom pencarian untuk mencari di 6 field:
- Nama project
- Deskripsi
- Sumber dana
- Lokasi project
- Nama client
- Kategori

**Contoh:** Ketik "APBN" akan menampilkan semua project dengan sumber dana APBN.

#### 2. Filter Tahun Project

Dropdown untuk filter berdasarkan tahun:
```
┌─────────────────┐
│ Tahun Project   │
├─────────────────┤
│ Semua Tahun     │
│ 2025            │
│ 2024            │
│ 2023            │
└─────────────────┘
```

#### 3. Filter Sumber Dana

Dropdown untuk filter berdasarkan sumber dana:
```
┌─────────────────┐
│ Sumber Dana     │
├─────────────────┤
│ Semua           │
│ APBN            │
│ DAU             │
│ APBD            │
│ Swasta          │
└─────────────────┘
```

#### 4. Filter Status Timeline

Filter berdasarkan status pelaksanaan:
```
┌─────────────────┐
│ Status Timeline │
├─────────────────┤
│ Semua Status    │
│ Belum Mulai     │
│ Sedang Berjalan │
│ Terlambat       │
│ Selesai         │
└─────────────────┘
```

#### 5. Filter Anggaran (Range)

Filter berdasarkan rentang anggaran:
```
Anggaran Min: [ 1000000000     ] Rp
Anggaran Max: [ 5000000000     ] Rp
```

**Contoh:**
- Min: 1.000.000.000 (1 Miliar)
- Max: 5.000.000.000 (5 Miliar)
- Hasil: Project dengan anggaran 1-5 Miliar

#### 6. Filter Tanggal Mulai (Range)

Filter berdasarkan rentang tanggal mulai:
```
Dari Tanggal: [ 01/01/2025 ]
Sampai:       [ 31/12/2025 ]
```

#### 7. Filter Status Aktif

Filter project aktif atau arsip:
```
┌─────────────────┐
│ Status          │
├─────────────────┤
│ Semua           │
│ Aktif           │
│ Archived        │
└─────────────────┘
```

**Default:** Hanya menampilkan project aktif.

#### 8. Sorting (Urutan)

Urutkan hasil dengan 8 pilihan:
```
┌──────────────────────┐
│ Urutkan              │
├──────────────────────┤
│ Update Terbaru       │
│ Update Terlama       │
│ Nama A–Z             │
│ Nama Z–A             │
│ Tahun ↓ (terbaru)   │
│ Tahun ↑ (terlama)   │
│ Anggaran Terbesar    │
│ Anggaran Terkecil    │
└──────────────────────┘
```

### Kombinasi Filter

Anda bisa menggunakan multiple filter sekaligus!

**Contoh:**
```
Search: "Jalan"
Tahun: 2025
Sumber Dana: APBN
Status: Berjalan
Anggaran Min: 1000000000
Sort: Anggaran Terbesar
```

Hasil: Project jalan tahun 2025, sumber APBN, sedang berjalan, anggaran > 1M, diurutkan dari terbesar.

### Reset Filter

Klik tombol **"Reset"** atau **"Clear Filter"** untuk menghapus semua filter.

---

## ⚡ Operasi Bulk

Operasi bulk memungkinkan Anda melakukan aksi pada multiple project sekaligus.

### 4 Operasi yang Tersedia

#### 1. Bulk Delete (Arsip Massal)

**Langkah:**
1. Centang checkbox di sebelah kiri nama project
2. Klik tombol **"Delete Selected"** di atas tabel
3. Konfirmasi penghapusan
4. Semua project terpilih akan diarsipkan

**Catatan:** Ini adalah soft delete, data tidak hilang permanen.

#### 2. Bulk Archive

**Langkah:**
1. Centang checkbox project yang ingin diarsipkan
2. Klik tombol **"Archive Selected"**
3. Konfirmasi
4. Project akan dipindahkan ke status archived

**Perbedaan dengan Delete:**
- Delete: Bisa digunakan kapan saja
- Archive: Hanya untuk project aktif

#### 3. Bulk Unarchive

**Langkah:**
1. Filter project dengan "Status: Archived"
2. Centang checkbox project yang ingin dikembalikan
3. Klik tombol **"Unarchive Selected"**
4. Konfirmasi
5. Project akan dikembalikan ke status aktif

#### 4. Bulk Export to Excel

**Langkah:**
1. Centang checkbox project yang ingin diekspor
2. Klik tombol **"Export Selected"**
3. File Excel akan otomatis terdownload

**Format Export:**
- 14 kolom data
- Header dengan styling biru
- Currency formatting untuk anggaran
- Auto-adjusted column widths

### Tips Bulk Operations

✅ **DO:**
- Centang hanya project yang benar-benar ingin diproses
- Gunakan filter untuk mempersempit selection
- Verifikasi jumlah project terpilih sebelum eksekusi

❌ **DON'T:**
- Jangan centang "Select All" tanpa filter jika punya ribuan project
- Jangan bulk delete tanpa backup
- Jangan bulk archive project yang sedang berjalan tanpa konfirmasi tim

---

## 📥 Export Data

Sistem menyediakan 3 format export dengan styling profesional.

### 1. Excel Export (.xlsx)

**Cara Menggunakan:**
1. Terapkan filter sesuai kebutuhan (opsional)
2. Klik tombol **"Export to Excel"** di atas tabel
3. File `.xlsx` akan terdownload otomatis

**Fitur Excel Export:**
- ✅ Header dengan background biru dan teks putih bold
- ✅ Border pada semua cell
- ✅ Currency formatting untuk kolom anggaran
- ✅ Auto-adjusted column widths
- ✅ 14 kolom data lengkap:
  - No, Index Project, Nama Project
  - Tahun, Sumber Dana, Lokasi
  - Client, Anggaran (Rp)
  - Tanggal Mulai, Tanggal Selesai, Durasi (hari)
  - Status, Kategori, Created

**Best Practice:**
- Gunakan untuk laporan formal atau presentasi
- Filter data sebelum export untuk hasil yang lebih relevan
- File hasil dapat langsung dibuka di Microsoft Excel atau LibreOffice

### 2. CSV Export (.csv)

**Cara Menggunakan:**
1. Terapkan filter sesuai kebutuhan
2. Klik tombol **"Export to CSV"**
3. File `.csv` akan terdownload

**Fitur CSV Export:**
- ✅ UTF-8 BOM untuk kompatibilitas dengan Excel
- ✅ Comma-separated format standar
- ✅ Import-friendly untuk database lain
- ✅ Semua field project included

**Kapan Menggunakan CSV:**
- Import ke aplikasi lain (database, spreadsheet)
- Processing dengan script/code
- Backup data sederhana
- File size lebih kecil dari Excel

### 3. PDF Export (Single Project)

**Cara Menggunakan:**
1. Buka halaman detail project
2. Klik tombol **"Export to PDF"**
3. File PDF akan terdownload

**Fitur PDF Export:**
- ✅ Landscape A4 page size
- ✅ Professional table formatting
- ✅ Sections:
  - Header dengan nama project
  - Info Project (lengkap)
  - Timeline Pelaksanaan
  - Data Anggaran
  - Data Client & Kontraktor
  - Data Konsultan
- ✅ Color styling untuk header sections
- ✅ Ready to print

**Kapan Menggunakan PDF:**
- Laporan untuk client atau stakeholder
- Dokumentasi project untuk arsip
- Lampiran proposal atau kontrak
- Print untuk meeting

### Export dengan Filter

**Skenario:**
Anda ingin export semua project APBN tahun 2025 yang berjalan.

**Langkah:**
1. Set filter:
   - Tahun Project: 2025
   - Sumber Dana: APBN
   - Status Timeline: Sedang Berjalan
2. Klik **"Terapkan Filter"**
3. Verifikasi hasil di tabel (misal: 25 project)
4. Klik **"Export to Excel"**
5. File akan berisi 25 project sesuai filter

**Catatan:** CSV dan Excel export akan mengikuti filter yang aktif. PDF export hanya untuk single project.

---

## 🔄 Deep Copy Project

Deep Copy adalah fitur advanced untuk menduplikasi project **lengkap** dengan semua data detail termasuk:
- Klasifikasi
- Sub-Klasifikasi
- Pekerjaan
- Volume Pekerjaan
- AHSP Template
- Harga Item
- Tahapan Pelaksanaan

### Kapan Menggunakan Deep Copy?

✅ **Gunakan untuk:**
- Project serupa dengan lokasi berbeda
- Project tahun baru dengan template sama
- Backup project sebelum perubahan besar
- Testing dengan data real

❌ **Jangan gunakan untuk:**
- Duplikasi sederhana (gunakan "Duplikasi" biasa)
- Project dengan struktur sangat berbeda

### Cara Menggunakan Deep Copy

#### Langkah 1: Akses Fitur

1. Buka halaman detail project yang ingin dicopy
2. Klik tombol **"Deep Copy Project"** (ikon 📋)
3. Halaman Deep Copy akan terbuka

#### Langkah 2: Konfigurasi Copy

Form Deep Copy:
```
┌──────────────────────────────────────────┐
│ Nama Project Baru                        │
│ [Project Jalan Raya 2025 - Copy      ]  │
│                                          │
│ ☑ Copy Klasifikasi & Sub-Klasifikasi   │
│ ☑ Copy Pekerjaan & Volume              │
│ ☑ Copy AHSP Template                   │
│ ☑ Copy Harga Item Project              │
│ ☑ Copy Tahapan Pelaksanaan             │
│                                          │
│ [ Cancel ]  [ Start Deep Copy ]         │
└──────────────────────────────────────────┘
```

**Field Wajib:**
- **Nama Project Baru** - Harus unik, tidak boleh sama dengan project lain

**Opsi Copy:**
- Centang/uncheck sesuai kebutuhan
- Default: semua tercentang (copy lengkap)

#### Langkah 3: Eksekusi

1. Isi nama project baru
2. Pilih opsi yang ingin dicopy
3. Klik **"Start Deep Copy"**
4. Progress indicator akan muncul
5. Tunggu hingga selesai (bisa 30 detik - 2 menit tergantung ukuran)

#### Langkah 4: Verifikasi

Setelah selesai, sistem akan menampilkan:

**Success Message:**
```
✅ Deep Copy Berhasil!

Project baru: "Project Jalan Raya 2025 - Copy"
Index: PRJ-12-061125-0234

Statistik Copy:
- Klasifikasi: 5 copied
- Sub-Klasifikasi: 15 copied
- Pekerjaan: 120 copied
- Volume: 120 copied
- AHSP Template: 80 copied
- Harga Item: 250 copied
- Tahapan: 6 copied

Warnings: 0
Skipped Items: 0

[ Lihat Project Baru ] [ Tutup ]
```

Klik **"Lihat Project Baru"** untuk verifikasi hasilnya.

### Error Handling

Jika terjadi error, sistem akan menampilkan:

**Error Types:**

1. **Validation Error** (🟡)
   - Nama project kosong
   - Nama project duplikat
   - Project source tidak valid
   - **Solusi:** Perbaiki input dan coba lagi

2. **Permission Error** (🔴)
   - Anda bukan owner project source
   - **Solusi:** Hubungi owner atau admin

3. **Database Error** (🔴)
   - Integrity constraint violation
   - Deadlock
   - **Solusi:** Coba lagi atau hubungi admin

4. **System Error** (🔴🔴)
   - Memory limit exceeded
   - Timeout
   - **Solusi:** Hubungi admin dengan Error ID

**Error Display:**
```
❌ Deep Copy Gagal

Error: DUPLICATE_PROJECT_NAME
Kode Error: 3001
Tipe: ValidationError

Pesan: Project dengan nama "Project Jalan Raya 2025 - Copy"
sudah ada. Silakan gunakan nama yang berbeda.

Error ID: ERR-1730884523

[ Copy Error ID ] [ Tutup ]
```

### Skip Tracking

Jika ada data yang tidak bisa dicopy (orphaned data), sistem akan skip dan laporkan:

**Skipped Items Display:**
```
⚠️ Ada Item yang Di-skip

Beberapa item tidak dapat dicopy karena missing dependencies:

- Sub-Klasifikasi: 2 items skipped
- Pekerjaan: 5 items skipped

Detail skipped items tersedia di log sistem.
Hubungi admin jika perlu investigasi lebih lanjut.

[ Lanjutkan ] [ Lihat Detail ]
```

### Performance Tips

**Project Kecil (< 100 pekerjaan):**
- Waktu: 10-30 detik
- Queries: ~60
- Memory: Low

**Project Medium (100-500 pekerjaan):**
- Waktu: 30-60 detik
- Queries: ~100
- Memory: Medium

**Project Besar (> 500 pekerjaan):**
- Waktu: 1-2 menit
- Queries: ~150
- Memory: High
- **Saran:** Lakukan saat traffic rendah (malam/weekend)

**Project Sangat Besar (> 2000 pekerjaan):**
- Waktu: 2-5 menit
- **Saran:** Hubungi admin untuk bulk copy script

---

## 👨‍💼 Admin Panel

### Mengakses Admin Panel

1. Klik menu **"Admin"** di navigation bar
2. Atau akses langsung: `https://yourdomain.com/admin/`
3. Login dengan akun admin (superuser)

**Catatan:** Hanya user dengan status admin/superuser yang bisa akses.

### Project Admin Features

#### List View

Tampilan list dengan 7 kolom custom:

```
┌────────┬──────────┬───────┬──────┬──────────┬──────────┬────────┐
│ Index  │ Nama     │ Owner │ Tahun│ Timeline │ Anggaran │ Status │
├────────┼──────────┼───────┼──────┼──────────┼──────────┼────────┤
│ PRJ... │ Proj A   │ User1 │ 2025 │ 01/01... │ Rp 1.5 M │ 🟢     │
│ PRJ... │ Proj B   │ User2 │ 2024 │ 15/03... │ Rp 2.3 M │ 🔴     │
└────────┴──────────┴───────┴──────┴──────────┴──────────┴────────┘
```

**Status Icons:**
- 🟢 Berjalan
- 🔴 Terlambat
- ⚪ Belum Mulai
- ⚫ Archived

#### Filters (6 Dimensions)

**Sidebar Filters:**
1. **By Status** - Active / Inactive
2. **By Year** - 2025, 2024, 2023, ...
3. **By Sumber Dana** - APBN, DAU, APBD, ...
4. **By Created Date** - Today, Past 7 days, This month, ...
5. **By Tanggal Mulai** - Date range picker
6. **By Tanggal Selesai** - Date range picker

#### Search (6 Fields)

Search box di atas mencari di:
- Nama project
- Index project
- Lokasi project
- Nama client
- Owner username
- Owner email

**Contoh:** Ketik "Jakarta" untuk cari semua project di Jakarta.

#### Date Hierarchy

Navigasi breadcrumb di atas untuk filter by created date:
```
2025 > November > 6
```

Klik tahun, bulan, atau tanggal untuk filter.

#### Custom Actions (3 Actions)

Pilih project (centang checkbox) lalu pilih action:

1. **Aktifkan project yang dipilih**
   - Set is_active = True
   - Mengembalikan dari arsip

2. **Arsipkan project yang dipilih**
   - Set is_active = False
   - Soft delete massal

3. **Export project terpilih ke CSV**
   - Download CSV dengan 13 fields
   - UTF-8 BOM encoding

### Project Detail/Edit View

#### Organized Fieldsets

**1. Identitas Project**
- Index Project (read-only)
- Nama
- Owner
- Status (is_active)

**2. Data Wajib**
- Tahun Project
- Sumber Dana
- Lokasi Project
- Nama Client
- Anggaran Owner

**3. Timeline Pelaksanaan**
- Tanggal Mulai
- Tanggal Selesai
- Durasi (hari)
- Durasi (Kalkulasi) - read-only, auto-calculated

**4. Data Tambahan** (collapsible)
- 10 field opsional
- Keterangan, Jabatan, Instansi, dll.

**5. Metadata** (collapsible)
- Created At (read-only)
- Updated At (read-only)

### Tips Admin Panel

✅ **Best Practices:**
- Gunakan filters untuk mempersempit hasil
- Gunakan search untuk find specific project
- Gunakan bulk actions untuk efisiensi
- Check "Date Hierarchy" untuk temporal analysis

❌ **Avoid:**
- Edit field read-only (akan error)
- Bulk delete tanpa backup
- Change owner tanpa consent

---

## 💡 Tips & Trik

### 1. Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + F` | Focus pada search box |
| `Ctrl + S` | Simpan form (jika ada form) |
| `Esc` | Tutup modal/dialog |

### 2. Workflow Efisien

**Membuat Multiple Projects:**
1. Gunakan Excel upload untuk batch creation
2. Template sudah include semua field
3. Validasi di Excel sebelum upload

**Monitoring Progress:**
1. Set filter "Status: Berjalan"
2. Sort by "Tanggal Selesai"
3. Focus pada yang paling dekat deadline

**Reporting:**
1. Set filter sesuai kebutuhan laporan
2. Export to Excel
3. Open di Excel untuk pivot table atau chart tambahan

### 3. Mobile Usage

**Responsive Design:**
- Dashboard fully responsive
- Filter collapse di mobile
- Table scrollable horizontal
- Touch-friendly buttons

**Recommended Actions on Mobile:**
- View project details
- Check analytics
- Basic filtering
- Export data

**Not Recommended on Mobile:**
- Bulk operations
- Excel upload
- Deep copy (gunakan desktop untuk ini)

### 4. Performance Tips

**Jika Dashboard Lambat:**
- Gunakan filter untuk reduce data
- Collapse analytics section
- Disable charts jika tidak perlu
- Clear browser cache

**Jika Deep Copy Lambat:**
- Lakukan saat traffic rendah
- Uncheck opsi yang tidak perlu
- Hubungi admin untuk optimization

### 5. Data Integrity

**Best Practices:**
- Backup sebelum bulk operations
- Verifikasi data setelah import
- Test deep copy dengan project kecil dulu
- Regular export untuk backup

---

## ❓ FAQ (Frequently Asked Questions)

### Umum

**Q: Berapa banyak project yang bisa saya buat?**
A: Tidak ada limit. Namun untuk performa optimal, recommended < 10,000 projects per user.

**Q: Apakah data saya aman?**
A: Ya, sistem menggunakan enkripsi HTTPS, database backup harian, dan user isolation.

**Q: Bisakah saya mengakses dari mobile?**
A: Ya, dashboard fully responsive. Namun beberapa fitur advanced lebih baik di desktop.

### Project Management

**Q: Bagaimana cara menghapus project permanen?**
A: Sistem menggunakan soft delete. Untuk permanent delete, hubungi admin.

**Q: Bisakah saya transfer ownership project?**
A: Ya, hubungi admin untuk change owner.

**Q: Format tanggal yang diterima?**
A: YYYY-MM-DD (recommended) atau DD/MM/YYYY.

### Deep Copy

**Q: Berapa lama proses deep copy?**
A: 10 detik - 5 menit tergantung ukuran project. Average: 30-60 detik.

**Q: Apakah deep copy mempengaruhi project original?**
A: Tidak, deep copy hanya read project original, tidak modify.

**Q: Bagaimana jika deep copy error?**
A: Sistem akan rollback otomatis. Tidak ada partial copy. Copy ulang setelah perbaiki issue.

**Q: Bisakah saya copy dari project user lain?**
A: Tidak, hanya owner yang bisa deep copy. Minta owner atau admin untuk copy.

### Export

**Q: Berapa limit export?**
A: Tidak ada hard limit. Namun untuk > 10,000 records, recommended gunakan CSV.

**Q: Format anggaran di Excel?**
A: Formatted sebagai number dengan currency format (#,##0).

**Q: Bisakah export dengan custom columns?**
A: Saat ini fixed 14 columns. Untuk custom, hubungi admin.

### Filter & Search

**Q: Bisakah save filter untuk next visit?**
A: Filter tersimpan di URL. Bookmark URL untuk quick access.

**Q: Search case-sensitive?**
A: Tidak, search case-insensitive.

**Q: Bisakah filter multiple sumber dana?**
A: Saat ini single select. Untuk multiple, gunakan search.

### Performance

**Q: Dashboard lambat loading?**
A: Try: 1) Collapse analytics, 2) Use filters, 3) Clear cache, 4) Hubungi admin jika persistent.

**Q: Export timeout?**
A: Untuk large dataset (>5000), hubungi admin untuk async export.

### Troubleshooting

**Q: Forgot password?**
A: Hubungi admin atau gunakan "Forgot Password" link (jika available).

**Q: Error 500?**
A: Server error. Copy Error ID dan hubungi admin.

**Q: Data tidak muncul setelah save?**
A: Refresh page (F5) atau clear cache.

---

## 📞 Bantuan & Support

### Kontak Support

**Email:** support@yourdomain.com
**Phone:** +62-XXX-XXXX-XXXX
**Jam Kerja:** Senin-Jumat, 08:00-17:00 WIB

### Reporting Issues

Jika menemukan bug atau error:

1. Screenshot error message
2. Copy Error ID (jika ada)
3. Catat langkah-langkah reproduce
4. Email ke support dengan detail di atas

### Feedback & Feature Request

Kami sangat menghargai feedback Anda!

**Cara Submit:**
- Email ke: feedback@yourdomain.com
- GitHub Issues: https://github.com/adithia00004/DJANGO-AHSP-PROJECT/issues

---

## 📚 Panduan Lainnya

- **[Deployment Guide](./DEPLOYMENT_GUIDE.md)** - Untuk IT/DevOps
- **[Troubleshooting Guide](./TROUBLESHOOTING_GUIDE.md)** - Mengatasi masalah umum
- **[Performance Tuning Guide](./PERFORMANCE_TUNING_GUIDE.md)** - Optimasi sistem
- **[Roadmap](./DASHBOARD_IMPROVEMENT_ROADMAP.md)** - Fitur mendatang

---

**Terima kasih telah menggunakan Sistem Manajemen Project AHSP!** 🎉

_Panduan ini akan terus diupdate seiring dengan perkembangan fitur baru._

**Versi Panduan:** 4.0
**Terakhir Diupdate:** 6 November 2025
