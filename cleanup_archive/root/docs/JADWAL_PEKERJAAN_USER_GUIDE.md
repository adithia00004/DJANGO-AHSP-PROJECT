# Jadwal Pekerjaan - Panduan Pengguna

## Daftar Isi
1. [Pendahuluan](#pendahuluan)
2. [Memulai](#memulai)
3. [Mode Skala Waktu](#mode-skala-waktu)
4. [Mengedit Progress Pekerjaan](#mengedit-progress-pekerjaan)
5. [Menyimpan Perubahan](#menyimpan-perubahan)
6. [Mode Tampilan](#mode-tampilan)
7. [Visualisasi Data](#visualisasi-data)
8. [Tips dan Best Practices](#tips-dan-best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Pendahuluan

**Jadwal Pekerjaan** adalah fitur untuk mengelola dan memantau progress pekerjaan konstruksi dalam skala waktu tertentu. Fitur ini memungkinkan Anda untuk:

- Mendistribusikan volume pekerjaan ke berbagai tahapan waktu (harian, mingguan, bulanan, atau custom)
- Memantau progress pekerjaan secara real-time
- Mengkonversi antara skala waktu yang berbeda secara otomatis
- Visualisasi progress dengan Gantt Chart dan S-Curve

---

## Memulai

### Mengakses Jadwal Pekerjaan

1. Buka halaman detail project Anda
2. Klik tab **"Jadwal Pekerjaan"** di navigation bar
3. Sistem akan otomatis memuat data pekerjaan dan tahapan

### Tampilan Awal

Saat pertama kali membuka halaman, Anda akan melihat:

- **Panel Kiri**: Daftar pekerjaan dalam struktur tree (parent-child)
- **Panel Kanan**: Grid tahapan waktu (kolom-kolom waktu)
- **Toolbar Atas**: Kontrol untuk mode skala waktu dan mode tampilan
- **Status Bar**: Informasi jumlah perubahan yang belum disimpan

---

## Mode Skala Waktu

Jadwal Pekerjaan mendukung 4 mode skala waktu:

### 1. Daily (Harian)
- Setiap kolom mewakili 1 hari
- Format: "Day 1, 26 Oct", "Day 2, 27 Oct", dst.
- Cocok untuk: Project pendek atau tracking detail harian

### 2. Weekly (Mingguan)
- Setiap kolom mewakili 1 minggu
- Format: "Week 1: 26 Oct - 27 Oct", "Week 2: 28 Oct - 03 Nov", dst.
- Cocok untuk: Project menengah (1-6 bulan)

### 3. Monthly (Bulanan)
- Setiap kolom mewakili 1 bulan
- Format: "Oktober 2025", "November 2025", dst.
- Cocok untuk: Project panjang (lebih dari 6 bulan)

### 4. Custom (Kustom)
- Kolom dibuat manual oleh user
- Fleksibel untuk kebutuhan khusus
- Menampilkan semua tahapan (auto-generated + custom)

### Cara Mengganti Mode

1. Pilih radio button mode yang diinginkan (Daily/Weekly/Monthly/Custom)
2. Sistem akan menampilkan **dialog konfirmasi**:
   - Jika **ADA perubahan yang belum disimpan**: Warning dengan jumlah perubahan
   - Jika **TIDAK ADA perubahan**: Konfirmasi standar
3. Klik **OK** untuk melanjutkan atau **Cancel** untuk membatalkan
4. Sistem akan otomatis:
   - Regenerate tahapan sesuai mode baru
   - Konversi assignments yang sudah ada ke mode baru
   - Mempertahankan proporsi total volume

**PENTING**:
- Perubahan yang belum disimpan akan **HILANG** saat mengganti mode
- Selalu **Save All Changes** sebelum mengganti mode jika ingin mempertahankan data

---

## Mengedit Progress Pekerjaan

### Cara Mengedit Cell

1. **Double-click** pada cell yang ingin diedit
2. Masukkan nilai progress (dalam persen, 0-100)
3. Tekan **Enter** untuk konfirmasi atau **Escape** untuk membatalkan
4. Cell akan berubah warna:
   - **Hijau muda** (modified): Ada perubahan yang belum disimpan
   - **Biru muda** (saved): Data sudah tersimpan di database

### Navigasi Keyboard

Saat mengedit cell, Anda bisa menggunakan:

- **Enter**: Konfirmasi input dan pindah ke cell di bawah
- **Tab**: Konfirmasi input dan pindah ke cell di kanan
- **Shift+Tab**: Konfirmasi input dan pindah ke cell di kiri
- **Escape**: Batalkan input dan kembalikan nilai original
- **Arrow Keys**: Navigasi setelah selesai mengedit

### Validasi Input

- Nilai harus antara **0 - 100** (persen)
- Sistem akan menolak input yang tidak valid
- Total proporsi boleh melebihi 100% (untuk handling overlap atau buffer)

---

## Menyimpan Perubahan

### Cara Menyimpan

1. Setelah mengedit cell, klik tombol **"Save All Changes"**
2. Loading overlay akan muncul dengan progress message:
   - "Preparing changes..." - Memproses data
   - "Saving changes... Pekerjaan N of M" - Menyimpan per pekerjaan
   - "Updating UI..." - Memperbarui tampilan
3. Setelah berhasil, Anda akan melihat:
   - Toast notification: "All changes saved successfully (N pekerjaan)"
   - Cell berubah dari hijau (modified) ke biru (saved)
   - Status bar menunjukkan "0 changes"

### Indikator Unsaved Changes

- **Status Bar**: Menampilkan jumlah perubahan yang belum disimpan
- **Cell Color**: Hijau muda = modified, biru muda = saved
- **Browser Warning**: Jika ada unsaved changes, browser akan warning saat Anda close tab/window

### Auto-Save

**TIDAK ADA** auto-save. Anda harus klik **"Save All Changes"** secara manual.

---

## Mode Tampilan

Jadwal Pekerjaan mendukung 2 mode tampilan nilai:

### 1. Percentage (Default)
- Menampilkan nilai dalam persen (%)
- Contoh: 33.3%, 66.7%
- Cocok untuk: Melihat proporsi distribusi

### 2. Volume
- Menampilkan nilai dalam satuan volume aktual
- Contoh: 15.50 m³, 42.30 m²
- Cocok untuk: Melihat volume fisik yang dialokasikan

### Cara Mengganti Mode

1. Klik radio button **Percentage** atau **Volume**
2. Grid akan langsung update tanpa reload

---

## Visualisasi Data

### 1. Gantt Chart

**Cara Mengakses**:
- Klik tab **"Gantt Chart"** di bagian bawah

**Fitur**:
- Visualisasi timeline pekerjaan
- Bar chart horizontal per pekerjaan
- Durasi berdasarkan tanggal mulai - selesai

### 2. S-Curve

**Cara Mengakses**:
- Klik tab **"S-Curve"** di bagian bawah

**Fitur**:
- Kurva kumulatif progress project
- Line chart menunjukkan progress over time
- Cocok untuk monitoring overall project progress

---

## Tips dan Best Practices

### 1. Pilih Mode Skala Waktu yang Tepat

- **Project < 1 bulan**: Gunakan Daily mode untuk detail tinggi
- **Project 1-6 bulan**: Gunakan Weekly mode untuk balance
- **Project > 6 bulan**: Gunakan Monthly mode untuk overview

### 2. Save Secara Berkala

- Jangan tunggu sampai banyak perubahan untuk save
- Save setiap 5-10 menit atau setelah menyelesaikan 1 section
- Browser warning akan melindungi dari kehilangan data accidental close

### 3. Gunakan Tree Structure dengan Baik

- **Expand** pekerjaan parent untuk melihat sub-pekerjaan
- **Collapse** untuk fokus pada level tertentu
- Tombol **"Collapse All"** dan **"Expand All"** untuk kontrol cepat

### 4. Periksa Total Progress

- Status bar menampilkan **Total Progress** project
- Nilai ini adalah rata-rata progress semua pekerjaan
- Gunakan untuk monitoring overall progress

### 5. Validasi Proporsi

- Pastikan total proporsi per pekerjaan masuk akal
- Proporsi bisa > 100% jika ada overlap tahapan (ini diperbolehkan)
- Proporsi < 100% artinya ada volume yang belum dialokasikan

### 6. Backup Data

- Lakukan export data berkala (jika fitur tersedia)
- Simpan snapshot database sebelum perubahan besar
- Test konversi mode di project dummy terlebih dahulu

---

## Troubleshooting

### Q: Data tidak tersimpan setelah klik Save

**Solusi**:
1. Periksa console browser (F12) untuk error messages
2. Pastikan koneksi internet stabil
3. Cek apakah ada validation error (nilai diluar 0-100)
4. Refresh halaman dan coba lagi

### Q: Cell tidak bisa diedit (tidak ada input field saat double-click)

**Solusi**:
1. Pastikan cell adalah cell pekerjaan (bukan parent/sub-pekerjaan level)
2. Refresh halaman jika terjadi JavaScript error
3. Cek console browser untuk error messages

### Q: Mode switch tidak berhasil / data hilang

**Solusi**:
1. Pastikan Anda klik OK pada dialog konfirmasi
2. Periksa console untuk error messages
3. Jika data assignments hilang, check database untuk backup
4. Untuk recovery, gunakan management command jika tersedia

### Q: Warning "No auto-generated tahapan found"

**Solusi**:
1. Ini normal jika Anda belum pernah switch ke mode tersebut
2. Switch ke mode yang diinginkan, sistem akan auto-generate tahapan
3. Jika masih muncul setelah switch, refresh halaman
4. Periksa database: `TahapPelaksanaan` harus memiliki `is_auto_generated=True` dan `generation_mode` yang sesuai

### Q: Total progress tidak akurat

**Solusi**:
1. Pastikan semua pekerjaan level terendah (leaf nodes) memiliki assignments
2. Parent nodes tidak dihitung dalam progress calculation
3. Refresh halaman untuk recalculate
4. Periksa data volume pekerjaan (harus > 0)

### Q: Gantt Chart / S-Curve tidak muncul

**Solusi**:
1. Pastikan pekerjaan memiliki tanggal mulai dan selesai
2. Refresh tab dengan klik tab lain lalu kembali
3. Periksa console browser untuk JavaScript errors
4. Clear browser cache dan reload halaman

### Q: Browser warning terus muncul meskipun sudah save

**Solusi**:
1. Periksa status bar - pastikan "0 changes"
2. Jika masih ada changes setelah save, kemungkinan save gagal
3. Cek console dan network tab di DevTools
4. Refresh halaman untuk reset state

---

## Kontak Support

Jika mengalami masalah yang tidak tercantum di troubleshooting:

1. Catat langkah-langkah yang menyebabkan error
2. Screenshot error message (jika ada)
3. Copy paste console error dari browser DevTools (F12)
4. Hubungi tim development dengan informasi di atas

---

**Versi**: 1.0
**Terakhir Diperbarui**: 26 Oktober 2025
**Penulis**: Development Team
