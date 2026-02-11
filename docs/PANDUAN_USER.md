# Panduan Pengguna AHSP Project

Dokumen ini dibagi menjadi 2 mode:
- `Mode Normal`: fondasi yang wajib dipahami semua pengguna.
- `Mode Advance`: fitur lanjutan untuk mempercepat alur kerja dan meningkatkan kontrol.

Catatan:
- Nama tombol/menu mengikuti label di UI aplikasi (misalnya `Tambah Project`, `Save`, `Export`).
- Simbol dan contoh di dokumen ini sudah menggunakan format teks standar agar aman dibuka di semua editor.

## Informasi Dokumen

Tujuan:
- Menjadi panduan operasional pengguna dari tahap setup proyek sampai keluaran laporan.
- Menyamakan pemahaman tim agar alur kerja dan hasil perhitungan tetap konsisten.

Audiens:
- Estimator/quantity surveyor.
- Site engineer/project engineer.
- Admin proyek/PMO yang mengelola data proyek.

Sumber kebenaran UI:
- Jika ada perbedaan istilah antara dokumen dan aplikasi, ikuti label tombol/menu yang tampil di UI saat digunakan.

Versi dokumen:
- `v1.2`
- Terakhir diperbarui: `9 Februari 2026`

---

## Daftar Isi

- [Informasi Dokumen](#informasi-dokumen)
- [Cheatsheet Cepat](#cheatsheet-cepat)
- [Mulai Cepat (10 Menit)](#mulai-cepat-10-menit)
- [BAGIAN 1: NORMAL (Wajib Dipahami)](#bagian-1-normal-wajib-dipahami)
- [BAGIAN 2: ADVANCE (Optimasi dan Produktivitas)](#bagian-2-advance-optimasi-dan-produktivitas)
- [Troubleshooting Umum](#troubleshooting-umum)
- [FAQ Singkat](#faq-singkat)
- [Checklist Sebelum Final Ekspor](#checklist-sebelum-final-ekspor)
- [Standar Penamaan](#standar-penamaan)
- [Rekomendasi Urutan Belajar](#rekomendasi-urutan-belajar)
- [Riwayat Perubahan Dokumen](#riwayat-perubahan-dokumen)

---

## Cheatsheet Cepat

Ringkasan 1 halaman tersedia di:
- [`CHEATSHEET_PANDUAN_USER.md`](CHEATSHEET_PANDUAN_USER.md)

Gunakan cheatsheet untuk operasional harian cepat, lalu kembali ke dokumen ini untuk detail langkah dan aturan.

---

## Mulai Cepat (10 Menit)

Jika Anda baru pertama kali memakai aplikasi, ikuti urutan minimum ini:
1. Dashboard -> `Tambah Project` -> isi data wajib.
2. List Pekerjaan -> susun klasifikasi, sub klasifikasi, lalu tambah pekerjaan dari referensi.
3. Volume Pekerjaan -> isi volume tiap pekerjaan.
4. Harga Items -> isi harga satuan item yang sudah otomatis muncul.
5. Rekap RAB -> cek total biaya, set PPN, lalu ekspor.

Catatan: Template AHSP (langkah 3 di alur utama) otomatis terisi jika pekerjaan diambil dari referensi, sehingga bisa dilewati di tahap awal.

Setelah alur ini berjalan lancar, lanjutkan ke Bagian 1 untuk pemahaman lengkap.

---

## BAGIAN 1: NORMAL (Wajib Dipahami)

### 1.1 Alur Kerja Utama

Setelah login, pekerjaan mengikuti 8 langkah berurutan:

```text
Dashboard -> Buat Project
             |
             +-> 1. List Pekerjaan    (susun struktur pekerjaan)
             +-> 2. Volume Pekerjaan  (isi kuantitas)
             +-> 3. Template AHSP     (cek komponen TK/BHN/ALT/LAIN)
             +-> 4. Harga Items       (isi harga item)
             +-> 5. Rincian AHSP      (cek kalkulasi detail, hanya-baca)
             +-> 6. Rekap RAB         (total biaya + margin + PPN)
             +-> 7. Rekap Kebutuhan   (total kebutuhan material/tenaga/alat)
             +-> 8. Jadwal Pekerjaan  (rencana dan pemantauan progres)
```

Data mengalir seperti ini:

```text
List Pekerjaan -> menentukan item pekerjaan
Volume Pekerjaan -> menentukan kuantitas
Template AHSP -> menentukan komponen dan koefisien
Harga Items -> menentukan harga satuan komponen
Rincian AHSP -> menghitung detail biaya per pekerjaan
Rekap RAB -> menghitung total biaya proyek
Rekap Kebutuhan -> mengagregasi total kebutuhan
Jadwal Pekerjaan -> memetakan progres ke timeline
```

Aturan penting:
- Kerjakan dari atas ke bawah agar hasil kalkulasi valid.
- Sidebar kiri tersedia di halaman detail, jadi Anda bisa pindah langkah tanpa kembali ke dashboard.

---

### 1.2 Dashboard

Dashboard adalah pusat kendali seluruh proyek.

Cara membuat proyek:
- Klik `Tambah Project` (atau FAB di pojok kanan bawah).
- Isi field wajib:

| Field | Keterangan |
|---|---|
| Nama Project | Nama pekerjaan/proyek |
| Sumber Dana | Asal pendanaan |
| Lokasi | Lokasi proyek |
| Nama Client | Pemilik proyek |
| Anggaran Owner | Pagu anggaran |
| Tanggal Mulai | Awal pelaksanaan |

Field opsional:
- Tanggal selesai, durasi, jabatan client, instansi, nama kontraktor/konsultan, keterangan.

Catatan penting:
- Jika Anda akan memakai halaman `Jadwal Pekerjaan`, isi `Tanggal Selesai` sejak awal agar pembagian tahapan bisa dibuat otomatis.

Aksi per proyek:
- `Detail`: masuk ke area kerja proyek.
- `Edit`: ubah data proyek.
- `Export Project (JSON)`: unduh backup penuh per proyek (default mencakup data progres/jadwal pada tombol dashboard saat ini).
- `Delete`: hapus lunak (proyek diarsipkan, bukan dihapus permanen).

Fitur bantu:
- Pencarian cepat pada toolbar untuk menyaring data di tabel yang sedang tampil.
- Pencarian/filter lanjutan: nama, lokasi, client, tahun, sumber dana, status timeline, rentang anggaran, rentang tanggal.
- Filter status proyek: `Aktif` / `Archived` / `Semua`.
- `Export Full` untuk ekspor daftar proyek sesuai filter aktif.
- `Edit Project` untuk mode edit massal langsung di tabel.
- Statistik: total proyek, total anggaran, proyek aktif, notifikasi overdue/deadline.

Catatan:
- Tampilan default dashboard menampilkan proyek aktif. Untuk melihat arsip, ubah filter status ke `Archived` atau `Semua`.

Checklist sebelum lanjut:
- Data proyek inti sudah benar.
- Tanggal mulai sudah terisi.

---

### 1.3 List Pekerjaan

Halaman ini dipakai untuk menyusun struktur WBS proyek.

Struktur hierarki:

```text
Klasifikasi
  -> Sub Klasifikasi
      -> Pekerjaan
```

Langkah input:
1. Klik `+ Klasifikasi`.
2. Klik `+ Sub Klasifikasi` pada klasifikasi terkait.
3. Klik `+ Pekerjaan`, lalu cari dari referensi AHSP.

Menambah pekerjaan dari referensi AHSP:
- Buka modal pencarian.
- Ketik kata kunci (contoh: `pasangan batu kali`).
- Pilih item hasil pencarian.
- Data uraian, satuan, dan komponen terisi otomatis dari referensi.

Fitur penting:
- TOC (panel kanan) untuk navigasi cepat.
- Drag and drop untuk ubah urutan.
- `Save` setelah selesai menyusun.
- Dropdown `Template` berisi: Lihat Template Library, Simpan Sebagai Template, Import dari File (JSON), Export Template JSON.

Catatan:
- Template Library menyediakan struktur pekerjaan siap pakai yang bisa langsung diimpor ke proyek Anda. Import bersifat menambahkan, bukan menimpa data lama.
- Panduan lengkap operasional Template (simpan, cari, preview, validasi, impor) dibahas di Bagian 2.3.

Checklist sebelum lanjut:
- Semua pekerjaan utama sudah masuk.
- Struktur klasifikasi dan urutan sudah final.

---

### 1.4 Volume Pekerjaan

Halaman ini untuk input kuantitas per pekerjaan.

Cara input:
- Ketik angka langsung di kolom volume (contoh: `25.5`).
- Satuan mengikuti satuan pekerjaan.
- Formula sederhana didukung via `fx` atau awali dengan `=`.

Contoh formula:

```text
= 12 * 0.3 * 0.5      -> 1.8
= (5 + 3) * 2.5       -> 20
```

Operator yang didukung:
- `+` `-` `*` `/` `()`

Fitur bantu:
- Expand/collapse klasifikasi.
- Filter cepat: Semua, Terisi, Belum Diisi, Formula.
- Statistik pengisian di toolbar.
- Ekspor tersedia (lihat Bagian 2.14 untuk peta format lengkap).

Checklist sebelum lanjut:
- Tidak ada pekerjaan utama yang volume-nya kosong.
- Formula penting sudah dievaluasi dengan benar.
- Klik `Save Volume`.

---

### 1.5 Template AHSP

Halaman ini menampilkan komponen detail per pekerjaan.
Jika pekerjaan diambil dari referensi AHSP, komponen biasanya sudah otomatis terisi.

Alur pakai:
1. Pilih pekerjaan dari sidebar kiri.
2. Cek komponen di 4 segmen:

| Segmen | Isi |
|---|---|
| TK | Tenaga kerja |
| BHN | Bahan |
| ALT | Peralatan |
| LAIN | Pekerjaan lain sebagai komponen |

Konsep utama:
- Koefisien = kebutuhan per 1 satuan pekerjaan.
- Kode item terhubung ke `Harga Items`.

Relasi antarmodul:
- Item yang ada di Template AHSP otomatis muncul di halaman `Harga Items`.

Fitur tambahan:
- Ekspor tersedia (lihat Bagian 2.14 untuk peta format lengkap).
- Tombol `Reload data` saat sistem mendeteksi data berubah dari sumber lain.
- Modal bantuan untuk ringkasan cara pakai cepat.

Checklist sebelum lanjut:
- Segmen dan koefisien sudah sesuai analisa.
- Klik `Save` atau `Ctrl+S`.

---

### 1.6 Harga Items

Halaman ini adalah database harga item per proyek.
Item muncul otomatis dari komponen di `Template AHSP`.

Cara pakai:
- Isi kolom `Harga` untuk tiap item.
- Gunakan tab filter: Semua, TK, BHN, ALT, Lain, Belum Diisi.

BUK (Biaya Umum dan Keuntungan):
- Isi persentase margin/profit di field BUK.
- Nilai default ini berlaku ke seluruh proyek, kecuali ada `override` di level pekerjaan (fitur lanjutan).

Catatan:
- Jika ada perubahan komponen di Template AHSP, lakukan muat ulang di Harga Items sebelum lanjut edit.
- Ekspor tersedia (lihat Bagian 2.14 untuk peta format lengkap).

Checklist sebelum lanjut:
- Item kritis sudah punya harga.
- BUK default sudah sesuai.
- Klik `Save`.

---

### 1.7 Rincian AHSP

Halaman ini `hanya-baca` untuk menampilkan kalkulasi detail:

```text
Template AHSP (komponen + koefisien)
Harga Items (harga satuan)
Volume Pekerjaan (kuantitas)
-> Rincian AHSP (jumlah harga per item dan pekerjaan)
```

Cara pakai:
1. Pilih pekerjaan dari sidebar kiri.
2. Verifikasi kolom uraian, kode, satuan, koefisien, harga satuan, jumlah harga.
3. Pantau total keseluruhan di toolbar.

Jika ada nilai salah:
- Perbaiki dari halaman sumber (Template AHSP, Harga Items, atau Volume), bukan di halaman ini.

Fitur tambahan:
- Ekspor tersedia (lihat Bagian 2.14 untuk peta format lengkap).
- Override BUK per pekerjaan tersedia dari tombol `Override` (dibahas detail di Bagian 2.8).

Checklist sebelum lanjut:
- Tidak ada komponen dengan harga nol (jika memang seharusnya berharga).
- Nilai total masuk akal terhadap volume.

---

### 1.8 Rekap RAB

Halaman ringkasan biaya total dalam tampilan tree view.

Fungsi utama:
- Melihat subtotal per klasifikasi/sub klasifikasi.
- Melihat detail volume, harga satuan, dan total pekerjaan.

Fitur:
- Expand/Collapse All.
- Search.
- Tombol subtotal.
- Sort kolom.

Footer perhitungan:

| Baris | Keterangan |
|---|---|
| Total D | Total biaya pekerjaan |
| PPN | Persentase PPN (default 11%) |
| Grand Total | Total D + PPN |
| Pembulatan | Basis pembulatan (1 / 1.000 / 10.000 / 100.000) |

Ekspor tersedia (lihat Bagian 2.14 untuk peta format lengkap).

Checklist sebelum lanjut:
- PPN dan pembulatan sudah sesuai kebutuhan dokumen.
- Grand Total sudah diverifikasi.

---

### 1.9 Rekap Kebutuhan

Halaman ini menampilkan total kebutuhan item proyek:

```text
Rincian AHSP + Volume Pekerjaan + Harga Items
-> Total kebutuhan per item
```

Yang bisa dilakukan:
- Filter kategori (TK/BHN/ALT/Lain).
- Filter klasifikasi.
- Melihat kuantitas, harga satuan, dan total harga.
- Ekspor tersedia (lihat Bagian 2.14 untuk peta format lengkap).

Checklist sebelum lanjut:
- Kebutuhan material utama sudah tervalidasi.
- Tidak ada item penting yang hilang karena filter aktif.

---

### 1.10 Jadwal Pekerjaan

Halaman untuk perencanaan dan monitoring progres.

Prasyarat:
- Isi `Tanggal Mulai` dan `Tanggal Selesai` di data proyek.

Alur ringkas:
1. Sistem membentuk tahapan waktu dari durasi proyek.
2. Anda isi proporsi `Rencana (%)` per periode.
3. Saat pelaksanaan, isi `Realisasi (%)`.
4. Gantt dan Kurva S ter-update otomatis dari data grid.

Tiga tab utama:

| Tab | Fungsi |
|---|---|
| Grid | Input rencana dan realisasi |
| Gantt Chart | Visual timeline pekerjaan |
| Kurva S | Grafik kumulatif rencana vs realisasi |

Aturan penting:
- Total proporsi rencana per pekerjaan harus 100%.

Ekspor tersedia (lihat Bagian 2.14 untuk peta format lengkap).

Checklist sebelum lanjut:
- Distribusi rencana sudah 100% per pekerjaan.
- Realisasi diinput sesuai periode berjalan.

---

### 1.11 Subscription

| Status | Akses |
|---|---|
| Trial (14 hari) | Buat/edit proyek, tidak bisa ekspor (PDF/Excel/Word/CSV/JSON) |
| Pro | Akses penuh, semua format ekspor tersedia |
| Expired | Hanya-baca, PDF dengan watermark masih diizinkan, format ekspor lain tidak diizinkan |

Pembayaran menggunakan Midtrans dengan durasi paket 3, 6, atau 12 bulan.

---

### 1.12 Akses Saat Fitur Diblokir

| Kondisi | Gejala di UI | Tindakan yang disarankan |
|---|---|---|
| Trial | Tombol ekspor format lanjutan tidak bisa dipakai | Upgrade ke Pro jika butuh ekspor dokumen |
| Expired | Tidak bisa edit/simpan data | Perpanjang subscription untuk aktifkan write access |
| Expired | PDF masih bisa tapi bertanda watermark | Gunakan sementara untuk review internal, finalisasi setelah status aktif |
| Semua status | Tombol ada tapi proses gagal | Cek koneksi, reload halaman, lalu ulangi sekali |

---

## BAGIAN 2: ADVANCE (Optimasi dan Produktivitas)

Prasyarat:
- Sudah memahami Bagian 1.
- Sudah mencoba alur kerja dasar minimal 1 proyek dari awal sampai akhir.

Panduan label di bagian ini:
- `Level`: tingkat kesulitan.
- `Dampak`: pengaruh ke kecepatan kerja atau kualitas hasil.

---

### 2.1 Impor, Ekspor, Duplikasi, dan Aksi Massal

Level: Menengah  
Dampak: Tinggi

Fitur:
- Ekspor JSON untuk backup/migrasi data.
- Impor JSON (opsional ikutkan data jadwal/progres).
- Duplikasi proyek lengkap untuk proyek sejenis.
- Unggah massal proyek via Excel.
- Aksi massal yang terlihat di UI: `Bulk Delete` (hapus lunak/arsip) dan `Edit Data` (edit massal langsung di tabel).
- `Export Full` di dashboard untuk ekspor daftar proyek sesuai filter yang aktif.

Kapan dipakai:
- Menangani banyak proyek dengan struktur serupa.

Catatan:
- `Bulk Delete` memindahkan data ke status arsip (`Archived`), bukan hapus permanen.
- Gunakan filter status `Archived` untuk melihat proyek yang sudah diarsipkan.
- Jika tombol aktivasi tersedia pada mode arsip, gunakan aksi `Unarchive`/`Aktifkan` untuk mengembalikan proyek menjadi aktif.

---

### 2.2 Tipe Pekerjaan: REF, MOD, Custom

Level: Menengah  
Dampak: Tinggi

| Tipe | Makna | Cara membuat |
|---|---|---|
| REF | Data dari referensi standar | Pilih pekerjaan dari pencarian referensi AHSP |
| MOD | REF yang sudah dimodifikasi | Edit komponen/koefisien pekerjaan REF di Template AHSP -> status otomatis berubah ke MOD |
| Custom | Dibuat manual dari nol | Klik `+ Pekerjaan`, lalu isi uraian dan satuan secara manual (tanpa memilih dari referensi) |

Mekanisme transisi:
- REF -> MOD: terjadi otomatis saat Anda mengubah komponen atau koefisien di Template AHSP.
- MOD -> REF: gunakan `Reset to Reference` di Template AHSP (Bagian 2.5) untuk mengembalikan ke data asli.
- Custom tidak bisa diubah ke REF/MOD karena tidak punya sumber referensi.

Aturan praktis:
- Pakai REF untuk konsistensi dan kepatuhan standar.
- Pakai MOD jika perlu penyesuaian kecil dari standar (misalnya tambah komponen atau ubah koefisien).
- Pakai Custom untuk pekerjaan non-standar yang tidak ada di referensi.

---

### 2.3 Template Pekerjaan (Dapat Digunakan Ulang)

Level: Menengah  
Dampak: Tinggi

Manfaat:
- Menyimpan struktur List Pekerjaan sebagai template.
- Mengurangi input ulang untuk proyek berulang.

Alur:
- `Save as Template` dari List Pekerjaan.
- Gunakan kembali lewat `Template Library`.

Panduan operasional:
1. Simpan template: gunakan `Simpan Sebagai Template`, isi `Nama Template` (wajib), deskripsi (opsional), dan kategori.
2. Cari template: di `Template Library`, gunakan pencarian nama (`q`) dan filter kategori.
3. Pratinjau sebelum impor: periksa jumlah klasifikasi, sub, pekerjaan, dan struktur ringkasnya.
4. Impor template: klik `Import Template` untuk menambahkan struktur ke proyek aktif.
5. Impor dari file: gunakan `Import dari File` untuk file JSON template valid.

Aturan validasi:
- Nama template wajib diisi saat menyimpan.
- Nama template tidak boleh duplikat.
- File impor harus berformat template JSON yang valid (`project_template` atau `list_pekerjaan`).
- Sistem akan menolak file yang tidak memiliki data pekerjaan/klasifikasi.

Dampak impor:
- Data ditambahkan ke struktur eksisting (append, no overwrite).
- Statistik hasil impor ditampilkan setelah proses selesai.
- Jika ada item bermasalah, proses tetap bisa berhasil parsial dengan `warnings`.

Checklist setelah impor:
- Periksa jumlah klasifikasi/sub/pekerjaan bertambah sesuai ekspektasi.
- Verifikasi urutan struktur (reorder jika diperlukan).
- Klik `Save` untuk memastikan perubahan tersimpan permanen.

---

### 2.4 Volume Formula Lanjutan dan Project Parameter

Level: Lanjutan  
Dampak: Tinggi

Contoh fungsi:

```text
= sum(10, 20, 30)
= min(5, 3, 8)
= max(5, 3, 8)
= round(panjang * lebar, 2)
```

Project Parameter:
- Definisikan variabel global (contoh: `lebar_jalan = 6`).
- Pakai variabel itu di banyak formula.
- Ubah sekali, formula terkait ikut ter-update.

Manajemen:
- Impor/ekspor parameter via JSON/CSV/XLSX.

---

### 2.5 Pengeditan Komponen di Template AHSP

Level: Menengah  
Dampak: Menengah-Tinggi

Fitur:
- Tambah baris komponen.
- Hapus baris terpilih (`Del`).
- Edit langsung pada sel (uraian, kode, koefisien).
- Kode item autocomplete.
- `Reset to Reference` untuk mengembalikan MOD ke REF.
- Conflict detection saat edit bersamaan.

---

### 2.6 Bundle AHSP (Nested Component)

Level: Lanjutan  
Dampak: Tinggi

Konsep:
- Di segmen `LAIN`, Anda bisa memasukkan pekerjaan lain sebagai komponen.
- Koefisien final dihitung dari perkalian koefisien bundle dan komponen turunannya.

Contoh:

```text
Pekerjaan "Pondasi Batu Kali" memiliki komponen di segmen LAIN:
  -> "Pasangan Batu Kali 1:4" dengan koefisien 1.2

Jika "Pasangan Batu Kali 1:4" memiliki komponen BHN:
  -> Batu kali, koefisien 1.2 m3

Maka kebutuhan batu kali untuk Pondasi = 1.2 x 1.2 = 1.44 m3 per satuan pekerjaan.
```

Manfaat:
- Analisa menjadi modular dan reusable.
- Perubahan pada pekerjaan sumber otomatis berdampak ke semua pekerjaan yang menggunakannya sebagai bundle.

---

### 2.7 Konversi Satuan Pasar di Harga Items

Level: Menengah  
Dampak: Tinggi

Kasus umum:
- Analisa butuh `kg`, supplier jual per `batang` atau `zak`.

Solusi:
- Gunakan kalkulator konversi di kolom harga.
- Simpan profil konversi (`Remember`) agar bisa dipakai ulang di item lain.

Contoh langkah:
1. Buka Harga Items, cari item yang satuannya berbeda dari satuan beli.
2. Klik kalkulator konversi pada kolom harga.
3. Isi harga per satuan beli (contoh: Rp 85.000/zak) dan faktor konversi (contoh: 1 zak = 50 kg).
4. Sistem menghitung harga per satuan analisa (Rp 85.000 / 50 = Rp 1.700/kg).
5. Klik `Remember` untuk menyimpan profil konversi agar bisa digunakan kembali.

---

### 2.8 Override BUK per Pekerjaan

Level: Menengah  
Dampak: Menengah-Tinggi

Fungsi:
- Atur margin khusus untuk pekerjaan tertentu tanpa mengubah BUK default proyek.

Workflow:
- Klik `Override` di pekerjaan target.
- Isi persentase BUK khusus.
- Gunakan `Reset` untuk kembali ke default.

Shortcut:
- `Shift+O` membuka modal override.

---

### 2.9 Rekap Kebutuhan per Periode dan Analitik

Level: Lanjutan  
Dampak: Tinggi

Fitur:
- Mode per minggu/per bulan.
- Mode satuan beli (pasar).
- Kontrol visibilitas kolom.
- Grafik distribusi biaya dan top items by cost.
- Ekspor per periode spesifik.

Kapan dipakai:
- Perencanaan pengadaan material bertahap.

---

### 2.10 Fitur Lanjutan Jadwal (Grid, Gantt, Kurva S)

Level: Lanjutan  
Dampak: Tinggi

Grid:
- Time scale mingguan/bulanan.
- Mode tampilan persen, volume, biaya (realisasi).
- Navigasi keyboard untuk input cepat.

Gantt:
- Visual rentang pekerjaan.
- Perbesar/perkecil tampilan, geser tampilan, penanda hari ini, layar penuh.

Kurva S:
- Rencana di atas realisasi: terlambat.
- Rencana di bawah realisasi: lebih cepat.
- Berimpit: sesuai rencana.

Tambahan:
- Kurva S Harga untuk evaluasi biaya rencana vs aktual.
- Regenerasi tahapan saat tanggal proyek berubah.
- Setel ulang progres per mode (rencana/realisasi) tanpa menghapus mode lain.

---

### 2.11 Ekspor Jadwal Profesional (PDF)

Level: Menengah  
Dampak: Menengah

Isi dokumen ekspor bisa mencakup:
- Cover.
- Executive summary.
- Daftar isi.
- Grid rencana dan realisasi.
- Gantt chart.
- Kurva S.
- Lembar pengesahan.

Catatan format:
- Mode laporan profesional difokuskan untuk PDF.
- Untuk XLSX/JSON, sistem menggunakan format data tabel standar.

---

### 2.12 Orphan Cleanup dan Audit Trail

Level: Menengah  
Dampak: Menengah

Orphan Cleanup:
- Menghapus item harga yang sudah tidak dipakai oleh pekerjaan manapun.

Audit Trail:
- Mencatat siapa mengubah apa, kapan, dan nilai sebelum/sesudah.
- Berguna untuk akuntabilitas tim dan investigasi selisih data.

---

### 2.13 Keyboard Shortcuts

| Shortcut | Halaman | Fungsi |
|---|---|---|
| `Ctrl+S` | Template AHSP, Jadwal | Simpan |
| `Ctrl+K` | Rincian AHSP | Fokus ke pencarian |
| `Shift+O` | Rincian AHSP | Buka modal override BUK |
| `Enter` | Grid, Template | Konfirmasi/navigasi |
| `Esc` | Semua modal | Tutup modal |
| `Up/Down` | Rincian, Grid | Navigasi list/sel |
| `Del` | Template AHSP | Hapus baris terpilih |

---

### 2.14 Peta Format Ekspor per Halaman

Level: Menengah  
Dampak: Tinggi

| Halaman | Format ekspor di UI |
|---|---|
| Dashboard | Export Full (Excel), Export Project per baris (JSON) |
| List Pekerjaan | Export Template JSON |
| Volume Pekerjaan | Excel, PDF, Word, JSON |
| Template AHSP | CSV, JSON |
| Harga Items | Excel, PDF, Word, JSON |
| Rincian AHSP | Excel, PDF, Word |
| Rekap RAB | Excel, PDF, Word, JSON |
| Rekap Kebutuhan | PDF, Word, Excel |
| Jadwal Pekerjaan | PDF, Excel, JSON (Word tergantung versi UI) |

Catatan akses:
- Ketersediaan tombol ekspor juga dipengaruhi status subscription (lihat Bagian 1.11).

---

### 2.15 Detail Proyek, Copy Project, dan Proses Ekspor

Level: Menengah  
Dampak: Menengah-Tinggi

Detail Proyek dan Copy:
- Pada halaman `Detail Proyek`, tersedia fitur `Copy Project`.
- Copy tunggal: buat 1 proyek baru dari proyek asal.
- Batch copy: membuat banyak salinan sekaligus (maksimal 50 per proses).
- Opsi copy jadwal: dapat menyalin data jadwal pelaksanaan.
- Opsi tanggal mulai baru: bisa diisi saat proses copy.

Perilaku proses ekspor:
- Beberapa ekspor berjalan dengan proses bertahap (menampilkan modal/progress).
- Hindari klik tombol ekspor berulang saat proses masih berjalan.
- Jika ekspor lama pada data besar, tunggu sampai notifikasi selesai muncul.
- Jika proses gagal, ulangi sekali setelah memastikan koneksi stabil.

Catatan:
- Beberapa fitur ekspor tertentu dapat berubah status sesuai kebijakan rilis/maintenance.

---

### 2.16 Matriks Data Yang Terbawa

Level: Menengah  
Dampak: Tinggi

| Fitur | Data yang terbawa | Catatan |
|---|---|---|
| Export Project (JSON) | Data proyek, struktur pekerjaan, volume, template AHSP, harga items, rincian, parameter, dan data jadwal/progres (sesuai konfigurasi tombol/dashboard saat ini) | Cocok untuk backup penuh atau migrasi antar akun |
| Import Project (JSON) | Membuat proyek baru dari file JSON backup | Opsi import jadwal/progres dapat diaktifkan/nonaktifkan saat impor |
| Save as Template (List Pekerjaan) | Struktur List Pekerjaan dan konten terkait template | Dipakai untuk reuse struktur berulang |
| Import Template Library | Menambah klasifikasi/sub/pekerjaan ke proyek aktif | Append (no overwrite), bisa ada warning parsial |
| Import Template dari File | Menambah struktur dari file JSON template valid | Wajib tipe `project_template` atau `list_pekerjaan` |
| Copy Project (Single/Batch) | Menyalin data proyek secara menyeluruh, termasuk opsi salin jadwal | Batch copy maksimal 50 salinan per proses |

---

### 2.17 Batasan Saat Ini (Known Limitations)

Level: Dasar  
Dampak: Menengah

- Sebagian label/tombol dapat berubah antar versi UI; ikuti label yang tampil pada aplikasi.
- Format ekspor tertentu bergantung status subscription dan versi build aktif.
- Pada beberapa rilis, opsi ekspor tertentu dapat dinonaktifkan sementara (maintenance/performa).
- Ekspor PDF dari halaman tertentu dapat diarahkan ke format alternatif jika fitur sedang maintenance.
- Fitur teknis internal yang tidak muncul di menu utama tidak perlu dipakai user umum.

---

## Troubleshooting Umum

### 1) Nilai di Rincian AHSP tidak berubah setelah edit
- Pastikan `Save` sudah diklik di halaman sumber (Volume/Template/Harga).
- Muat ulang halaman `Harga Items` jika sebelumnya ada perubahan di `Template AHSP`.

### 2) Total RAB terlihat nol atau tidak masuk akal
- Cek volume belum kosong.
- Cek harga item kritis belum nol.
- Cek komponen Template AHSP tidak terhapus tanpa sengaja.

### 3) Jadwal tidak bisa dihitung
- Pastikan `Tanggal Mulai` dan `Tanggal Selesai` sudah terisi.
- Pastikan proporsi rencana per pekerjaan totalnya 100%.

### 4) Formula volume error
- Gunakan operator yang valid: `+ - * / ()`.
- Periksa penulisan variabel jika memakai Project Parameter.

### 5) Data tim berubah tidak terduga
- Buka `Audit Trail` untuk melihat histori perubahan.

### 6) Tombol ekspor tidak bisa dipakai
- Cek status subscription Anda di bagian akun.
- Pastikan format yang dipilih sesuai hak akses.

### 7) Import Template dari file gagal
- Pastikan file berformat JSON valid.
- Pastikan tipe ekspor file template adalah `project_template` atau `list_pekerjaan`.
- Pastikan konten memiliki data pekerjaan atau klasifikasi.

### 8) Hasil impor template terasa dobel
- Impor template bersifat menambahkan data, bukan mengganti data lama.
- Hapus item yang tidak diperlukan atau gunakan project baru jika ingin struktur bersih.

### 9) Copy Project gagal
- Pastikan nama proyek baru tidak kosong dan tidak duplikat.
- Untuk Batch Copy, pastikan jumlah copy berada dalam batas (1-50).
- Jika gagal parsial, cek pesan warning/error lalu ulangi hanya untuk item yang gagal.

### 10) Ekspor lama atau tampak berhenti
- Tunggu hingga modal/progress selesai; hindari klik ulang tombol ekspor.
- Coba ulang sekali setelah refresh halaman jika proses sebelumnya gagal.
- Untuk data besar, lakukan ekspor per periode bila tersedia.

---

## FAQ Singkat

### Q1: Kenapa total RAB nol?
- Biasanya karena volume atau harga item belum terisi.

### Q2: Apakah import template menimpa data lama?
- Tidak. Import template bersifat menambahkan data.

### Q3: Kapan saya harus pakai MOD dibanding REF?
- Gunakan MOD saat REF perlu penyesuaian komponen/koefisien.

### Q4: Kenapa tombol ekspor tidak aktif?
- Umumnya karena batasan subscription atau kondisi fitur pada rilis saat ini.

### Q5: Kapan pakai Copy Project dibanding Template?
- Copy Project untuk menyalin proyek lengkap.
- Template untuk menyalin struktur pekerjaan saja.

---

## Checklist Sebelum Final Ekspor

1. Semua volume utama terisi dan formula penting tervalidasi.
2. Harga item kritis sudah terisi, tidak ada nilai nol yang tidak semestinya.
3. BUK, PPN, dan pembulatan sudah sesuai kebutuhan dokumen.
4. Rincian AHSP dan Rekap RAB sudah dicek silang (nilai masuk akal).
5. Untuk jadwal: total rencana per pekerjaan = 100%.
6. Filter halaman sudah diatur sesuai cakupan data yang akan diekspor.
7. Format ekspor sesuai kebutuhan (PDF/Excel/Word/JSON) dan hak akses user.

---

## Standar Penamaan

- Nama Project: gunakan format konsisten, contoh `Jenis Proyek - Lokasi - Tahun`.
- Nama Template: gunakan format `Template - Jenis - Skala`.
- Klasifikasi/Sub: gunakan istilah teknis baku dan hindari singkatan tidak umum.
- Hindari karakter khusus berlebihan agar aman untuk ekspor file.

---

## Rekomendasi Urutan Belajar

1. Selesaikan 1 proyek kecil penuh dengan `Mode Normal`.
2. Aktifkan 2 fitur lanjutan berdampak tinggi: `Template Pekerjaan` (2.3) dan `Project Parameter` (2.4).
3. Lanjutkan ke kontrol lanjutan: `Override BUK` (2.8), `Rekap per Periode` (2.9), dan `Audit Trail` (2.12).

---

## Riwayat Perubahan Dokumen

| Versi | Tanggal | Ringkasan |
|---|---|---|
| v1.0 | 2026-02-08 | Draft awal panduan mode normal dan advance |
| v1.1 | 2026-02-09 | Sinkronisasi fitur aktual, pendalaman Template Library, matriks akses, FAQ, checklist final ekspor, dan standar penamaan |
| v1.2 | 2026-02-09 | Penambahan Daftar Isi dan cheatsheet operasional 1 halaman |
