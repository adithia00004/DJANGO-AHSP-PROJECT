# Rencana: Tambahan Waktu Kerja pada Jadwal Pekerjaan

| | |
|---|---|
| **Status** | v9 — siap dieksekusi mulai Tahap 0; keputusan terbuka tinggal di [bagian 8.2](#82-masih-terbuka) |
| **Tanggal** | 2026-09-29 |
| **Dokumen terkait** | Audit backend: [REVIEW_BACKEND_JADWAL_KETERLAMBATAN_20260929.md](REVIEW_BACKEND_JADWAL_KETERLAMBATAN_20260929.md) · Rencana implementasi: [doc 40](../Review/R5_Detail_Project/40_Tambahan_Waktu_Kerja_Implementation_Plan_20260929.md) · Tracker: [doc 41](../Review/R5_Detail_Project/41_Tambahan_Waktu_Kerja_Implementation_Tracker_20260929.md) |
| **Cakupan fase ini** | Data & aturan, halaman Jadwal (grid, Kurva S, Gantt), perubahan waktu kerja di Dashboard, backup/restore/duplikasi. **Export dibahas di fase berikutnya** ([bagian 9](#9-fase-berikutnya-export)) |

---

## 1. Ringkasan

**Masalah.** Proyek bisa belum selesai saat waktu kerja kontrak berakhir. Saat ini
grid Jadwal hanya menyediakan kolom sampai akhir waktu kerja, sehingga realisasi
sesudahnya tidak bisa dicatat. Satu-satunya jalan keluar — mengubah akhir waktu
kerja di Dashboard — menghapus jejak batas kontrak.

**Solusi.** Tambah satu konsep: **Tambahan Waktu Kerja**, yaitu tanggal akhir
perpanjangan yang diisi user di halaman Jadwal (mode Realisasi). Akhir waktu
kerja di Dashboard tetap berarti batas kontrak. Minggu-minggu sesudahnya hanya
menerima realisasi, sehingga rencana tetap berhenti di batas kontrak dan
keterlambatan terlihat jelas di Kurva S.

**Urutan kerja.** Inti arsitektur Jadwal kuat, tetapi pinggirannya (backup,
restore, duplikasi, hitungan minggu) menulis ulang aturan yang sama di banyak
tempat dan sebagian sudah tidak utuh. Maka:

1. **Tahap 0 — konsolidasi pinggiran** (tanpa fitur baru, sekaligus memperbaiki
   bug lama);
2. **Tahap 1 — fitur Tambahan Waktu Kerja**, dipasang di titik-titik tunggal hasil
   Tahap 0;
3. **Fase berikutnya — export.**

---

## 2. Konsep

### 2.1 Istilah

| Istilah | Diisi di | Arti | Disimpan di |
|---|---|---|---|
| **Awal waktu kerja** | Dashboard (sudah ada) | Tanggal mulai proyek | `Project.tanggal_mulai` (tetap) |
| **Akhir waktu kerja** | Dashboard (sudah ada) | Tanggal selesai menurut kontrak | `Project.tanggal_selesai` (tetap, **maknanya tidak berubah**) |
| **Tambahan waktu kerja** | Halaman Jadwal, mode Realisasi (**baru**) | Tanggal akhir perpanjangan, mis. 31 Des | Kolom baru `Project.tanggal_akhir_tambahan` (boleh kosong) |
| **Masa waktu kerja** | Dihitung | Rentang dari awal waktu kerja sampai akhir tambahan, jika ada; bila tidak ada tambahan, sampai akhir waktu kerja. Inilah rentang pencatatan di grid | — (satu helper, 5.2) |
| **Durasi (hari)** | Dashboard (sudah ada) | **Tetap** mengikuti rentang Dashboard (awal–akhir waktu kerja). Panjang masa tambahan dihitung lewat helper, tidak disimpan di field ini | `Project.durasi_hari` (tetap) |

Pembagian minggu di grid:

| Istilah | Arti |
|---|---|
| **Minggu waktu kerja** | Minggu 1 sampai minggu yang memuat akhir waktu kerja |
| **Minggu batas** | Minggu yang **memuat** akhir waktu kerja. Bisa sebagian harinya di dalam waktu kerja, sebagian di masa tambahan |
| **Minggu tambahan** | Minggu **sesudah** minggu batas, sampai akhir tambahan. Seluruh harinya di masa tambahan |
| **Hari tambahan** | Tanggal apa pun **setelah** akhir waktu kerja — termasuk sisa hari di minggu batas |

### 2.2 Aturan dasar

- `awal waktu kerja ≤ akhir waktu kerja`; bila ada tambahan: `akhir tambahan > akhir waktu kerja`.
- Mengubah **akhir waktu kerja** (Dashboard) **tidak pernah** memendekkan
  tambahan waktu kerja. Masa waktu kerja = waktu kerja + tambahan.
- Tambahan waktu kerja hanya diubah lewat **"Perpanjang Waktu Kerja"** di
  halaman Jadwal.

### 2.3 Keputusan owner yang mengikat

- Rencana pada **minggu waktu kerja** dan **seluruh realisasi** tetap dapat diedit kapan pun.
- **Tidak ada pembekuan baseline.**
- **Minggu tambahan hanya menerima realisasi.** Rencana berhenti di batas kontrak.
- Minggu tambahan yang kosong **boleh dibiarkan** setelah pekerjaan mencapai 100%.
- Perpanjangan **hanya tersedia di mode Realisasi**, dengan **satu input tanggal**.
  Sistem yang menentukan jenis perpanjangannya.
- **Tidak ada pengingat/banner** keterlambatan.
- Penanda di grid dan laporan memakai istilah **"Penambahan Waktu Kerja"**.
- Status proyek di Dashboard (mis. badge "Terlambat") **di luar cakupan**.

### 2.4 Keterbatasan yang disadari

- Data progres disimpan **per minggu**. Di minggu batas, sistem **tidak bisa
  memisahkan** progres sebelum dan sesudah akhir waktu kerja.
- Tidak ada **riwayat** perubahan akhir waktu kerja (adendum). Nilai lama tertimpa.

---

## 3. Pengalaman User (UI/UX)

### 3.1 Prinsip

- **Satu tombol, satu input:** **"Perpanjang Waktu Kerja"** hanya meminta
  **tanggal akhir tambahan**. Jenis perpanjangan dideteksi sistem.
- **Hanya di mode Realisasi**, tempat user memang mengisi progres setelah
  kontrak. Tidak ada perpindahan mode di tengah alur.
- **Ikuti pola yang sudah ada:** dialog pratinjau timeline (`timeline_repair.js`),
  saklar Rencana/Realisasi, mode input persen/volume/biaya, penjaga editan belum
  disimpan (`state.isDirty`).
- **Proyek tanpa tambahan tidak melihat apa pun yang baru** selain tombol di mode
  Realisasi.
- **Label selalu berupa teks**, tidak hanya warna.

### 3.2 Alur utama — Perpanjang Waktu Kerja

1. User di mode **Realisasi** menekan **"Perpanjang Waktu Kerja"**.
2. Bila ada editan belum disimpan, dialog tidak dibuka dan muncul pesan
   (lihat 3.8).
3. Dialog:

   | Elemen | Isi |
   |---|---|
   | Informasi | Akhir waktu kerja: **30 Sep 2026** · Tambahan: **belum ada** |
   | Input | **Tanggal akhir tambahan: [ 31 Des 2026 ]** — hanya tanggal setelah akhir waktu kerja yang bisa dipilih |
   | Hasil deteksi | "**+13 minggu tambahan** (M27–M39). Akhir waktu kerja tetap 30 Sep." |
   | Jaminan | "Nilai rencana dan realisasi yang sudah ada tidak berubah." |
   | Tombol | **[Batal]** **[Simpan]** — dan **[Hapus tambahan]** bila tambahan sudah ada |

4. **Simpan** → grid dimuat ulang **tetap di mode Realisasi**, kolom baru bisa
   langsung diisi, muncul pesan berhasil.
5. User mengisi realisasi seperti biasa (persen, volume, atau biaya), lalu **Simpan**.

### 3.3 Deteksi jenis perpanjangan (oleh server)

Tanggal input dibandingkan dengan **akhir masa waktu kerja saat ini** dan batas
minggunya:

| Tanggal input | Terdeteksi | Yang terjadi | Teks hasil deteksi |
|---|---|---|---|
| Masih di **minggu terakhir yang sama** (mis. Rabu → Jumat) | **Tipe 1** | Tidak ada kolom baru; rentang minggu terakhir diperpanjang | "Diperpanjang dalam minggu yang sama (M26: 28 Sep–2 Okt)." |
| **Melewati** minggu terakhir | **Tipe 2** | Minggu terakhir menjadi penuh, lalu *n* minggu tambahan ditambahkan | "+*n* minggu tambahan (M27–M39)." |
| **Lebih awal** dari akhir tambahan saat ini (tetapi setelah akhir waktu kerja) | **Pengurangan** | Tambahan dipendekkan; ditolak bila minggu yang dibuang berisi realisasi/biaya aktual | "Tambahan dipendekkan: M39 → M30." |
| **Hapus tambahan** | **Pengurangan penuh** | Masa waktu kerja kembali ke akhir waktu kerja; aturan tolak sama | "Tambahan dihapus; masa waktu kerja kembali s.d. 30 Sep." |
| Sama dengan akhir tambahan saat ini | Tidak ada perubahan | Tombol Simpan nonaktif | "Tanggal sama dengan tambahan saat ini." |

Semua jenis: **nomor minggu dan nilai progres yang ada tidak berubah.**

### 3.4 Dampak kedua tipe

| | **Tipe 1 — hari di minggu yang sama** | **Tipe 2 — minggu baru** |
|---|---|---|
| Contoh | Akhir waktu kerja Rabu, tambahan s.d. **Jumat** | Akhir waktu kerja 30 Sep, tambahan s.d. **31 Des** |
| Kolom grid | Tidak ada kolom baru; rentang di header minggu terakhir berubah | Kolom minggu tambahan muncul |
| Rencana di minggu itu | **Tetap bisa diisi** (minggu batas)* | Minggu tambahan: **terkunci** di mode Rencana |
| Penanda header | Minggu batas: **"Waktu kerja berakhir Rab"** | Minggu batas: sama; minggu tambahan: **"Penambahan"** |
| Realisasi hari tambahan | Menyatu dengan hari sebelumnya dalam satu angka mingguan (2.4) | Diisi di kolom minggu tambahan |
| Kurva S / Gantt | Garis "Akhir Waktu Kerja" di posisi tanggalnya | Sama; realisasi berlanjut ke minggu tambahan |

\* Contoh tipe 1 ini untuk **minggu batas**. Bila minggu yang diperpanjang dalam
minggu yang sama sudah merupakan **minggu tambahan** (mis. tambahan s.d. Rabu
minggu ke-30, diperpanjang ke Jumat), rencana di minggu itu **tetap terkunci**.

### 3.5 Mode Rencana pada proyek yang punya tambahan

Tombol "Perpanjang Waktu Kerja" **tidak tampil**. Kolom minggu tambahan terlihat
tetapi **terkunci**:

| Keadaan | Perilaku |
|---|---|
| Sel | Latar abu/arsir tipis, `aria-disabled="true"` |
| Klik sel | "Minggu penambahan waktu kerja hanya menerima realisasi." |
| Keyboard | Sel terkunci dilewati (perilaku read-only yang sudah ada) |
| Tooltip header | "Penambahan waktu kerja setelah 30 Sep 2026. Hanya realisasi." |

Minggu batas **tidak** terkunci — sebagian harinya masih di dalam waktu kerja.

### 3.6 Mengubah waktu kerja di Dashboard (fitur yang sudah ada)

Perubahan awal/akhir waktu kerja saat data sudah diisi **sudah ditangani**, tetapi
kedua jalurnya berbeda:

| Kondisi data | **Edit Project** (`dashboard/views.py:642-735`) | **Edit Massal** (`views_mass_edit.py:197-267`) |
|---|---|---|
| Tidak ada data terdampak | Langsung tersimpan; kolom minggu dibentuk ulang | Sama |
| Ada **rencana** terdampak | Dialog **"Ringkasan dampak"**: tabel per minggu lama → baru, dengan pilihan *Pertahankan urutan minggu* / *Padatkan ke minggu batas* / *Hapus yang di luar jadwal baru* | **Tidak ada dialog.** Proyek itu dilewati utuh dan dilaporkan: "… project memerlukan keputusan Anda dan belum tersimpan" |
| Ada **realisasi atau biaya aktual** yang akan tergeser/terbuang | Ditolak dengan penjelasan | Dilewati & dilaporkan |
| Dua tab mengubah bersamaan | Ditolak; user diminta memuat ulang | Ditolak per proyek |

Pola ini dipertahankan: **dialog pilihan hanya di Edit Project**; Edit Massal
melewati dan melaporkan proyek yang butuh keputusan, termasuk kasus baru di
bawah.

**Yang ditambahkan**, ketika proyek sudah punya tambahan waktu kerja:

| Perubahan di Dashboard | Hasil |
|---|---|
| Akhir waktu kerja diubah, tetapi **masih sebelum** akhir tambahan | Akhir waktu kerja berubah; **tambahan tetap**; masa waktu kerja tidak berubah |
| Akhir waktu kerja diubah **sampai/melewati** akhir tambahan | Tambahan tidak berlaku lagi (dikosongkan); masa waktu kerja = akhir waktu kerja baru |
| Akhir waktu kerja **dimajukan** dan ada **rencana** di minggu yang kini menjadi minggu tambahan | **Edit Project:** dialog "Ringkasan dampak" menampilkan pekerjaan & minggu terdampak, dengan dua pilihan: **Pindahkan rencana ke minggu batas** (hanya rencana; realisasi & biaya tidak berubah) atau **Batalkan perubahan**. **Edit Massal:** proyek dilewati & dilaporkan (pola yang sudah ada) |

Formulir menampilkan informasi di bawah field akhir waktu kerja:
"Tambahan waktu kerja: s.d. 31 Des 2026 · ubah lewat Perpanjang Waktu Kerja di
halaman Jadwal (mode Realisasi)".

### 3.7 Tampilan grid

| Kolom | Header | Sel mode Rencana | Sel mode Realisasi |
|---|---|---|---|
| Minggu waktu kerja | Seperti sekarang | Dapat diisi | Dapat diisi |
| Minggu batas, tanpa tambahan | Seperti sekarang | Dapat diisi | Dapat diisi |
| Minggu batas, ada tambahan | "M26" + baris kecil **"Waktu kerja berakhir Rab"** | Dapat diisi | Dapat diisi |
| Minggu tambahan | "M27" + baris kecil **"Penambahan"**, latar header berbeda | **Terkunci** | Dapat diisi |

- Garis pemisah tebal antara minggu batas dan minggu tambahan pertama.
- Tampilan bulanan (sudah read-only): bulan yang memuat hari tambahan diberi baris
  kecil "penambahan waktu kerja".
- Kurva S dan Gantt: garis vertikal **"Akhir Waktu Kerja"**.

### 3.8 Teks pesan

| Situasi | Teks |
|---|---|
| Editan belum disimpan | Simpan atau batalkan perubahan di grid terlebih dahulu. Perpanjangan waktu kerja membentuk ulang kolom minggu. |
| Deteksi tipe 1 | Diperpanjang dalam minggu yang sama ({minggu}: {rentang}). |
| Deteksi tipe 2 | +{n} minggu tambahan ({dari}–{sampai}). |
| Deteksi pengurangan | Tambahan dipendekkan: {dari} → {sampai}. |
| Berhasil | Waktu kerja diperpanjang sampai {tgl} ({n} minggu tambahan). |
| Pengurangan ditolak | Minggu {a}–{b} berisi realisasi atau biaya aktual, sehingga tidak bisa dibuang. |
| Klik sel terkunci | Minggu penambahan waktu kerja hanya menerima realisasi. |
| Server menolak rencana | Rencana tidak bisa diisi pada minggu penambahan waktu kerja (setelah {tgl}). |
| Konflik sesi | Jadwal sudah diubah di tab/sesi lain. Muat ulang halaman, lalu coba lagi. |

### 3.9 Aksesibilitas

- Penanda berupa teks, bukan hanya warna.
- Sel terkunci: `aria-disabled="true"` dan tooltip yang terbaca pembaca layar.
- Dialog: fokus pertama di input tanggal; `Esc` menutup; tombol dapat dicapai keyboard.

---

## 4. Kondisi Sistem Saat Ini

Semua butir di bagian ini sudah diverifikasi di kode; A–D juga direproduksi oleh
audit backend.

### 4.1 Penilaian arsitektur

| | Keadaan |
|---|---|
| **Inti — kuat, tidak dirombak** | `PekerjaanProgressWeekly` sebagai satu sumber progres (rencana, realisasi, biaya aktual terpisah); layanan perubahan timeline yang transaksional dengan pratinjau, gerbang perlindungan realisasi/biaya, dan revisi jadwal; aturan minggu kanonik `build_week_buckets` / `expected_week_count` |
| **Pinggiran — rapuh** | Aturan yang sama ditulis ulang di banyak jalur: hitungan minggu di import, daftar field di export/import/duplikasi, aturan tulis rencana di beberapa endpoint |

Menyuntikkan fitur ke setiap jalur satu per satu akan memperburuk kerapuhan itu.
Karena itu pinggiran disatukan dulu (Tahap 0), baru fitur dipasang.

### 4.2 Yang bisa dipakai ulang

| Komponen | Lokasi |
|---|---|
| Layanan perubahan timeline + pratinjau + resolusi | `timeline_utils.analyze_project_timeline_change`, `apply_project_timeline_change` (`:642-783`), `build_resolution_preview` |
| Endpoint pratinjau & eksekusi di halaman Jadwal | `views_api_tahapan_v2.py:619, 662` |
| Dialog "Ringkasan dampak" (hanya Edit Project) | `dashboard/views.py:642-735`, `project_form.html` |
| Edit Massal: lewati & laporkan proyek yang butuh keputusan | `dashboard/views_mass_edit.py:197-267` |
| Revisi jadwal (penguncian optimistik) | `Project.schedule_revision`, `dashboard/models.py:150-157` |
| Perlindungan realisasi & biaya aktual | `timeline_utils._actual_filter` |
| Kolom read-only di grid; semua jalur edit memeriksanya | `tanstack-grid-manager.js:240, 773, 1097, 1227, 1269` |
| Saklar mode (grid dibangun ulang saat ganti mode) | `jadwal_kegiatan_app.js:2015-2054` |
| Penjaga editan belum disimpan | `jadwal_kegiatan_app.js` (`state.isDirty`) |

### 4.3 Celah

| # | Celah | Lokasi |
|---|---|---|
| C-1 | Grid, penyimpanan (`week_number` 1–N), import, dan export hanya mengenal rentang sampai `tanggal_selesai` | `views_api_tahapan_v2.py:174, 219`; `views_api.py:9683-9701`; `project_report_period_counts` |
| C-2 | **Minggu terakhir yang pendek:** bila rentang berakhir di tengah minggu lalu diperpanjang, kolom dibentuk ulang tetapi tanggal baris progres lama tidak diselaraskan (baru diperbarui saat disimpan ulang) | `progress_utils.build_week_buckets:296`; `timeline_utils:620, 722-745`; `views_api_tahapan_v2.py:330-334` |
| C-3 | Mesin resolusi memindahkan rencana, realisasi, dan biaya sebagai satu paket, dengan tepi = akhir rentang — tidak bisa dipakai apa adanya untuk "pindahkan rencana saja" | `timeline_utils.plan_timeline_resolution:335-415` |

### 4.4 Masalah transfer data yang sudah ada (audit backend)

| # | Masalah | Bukti percobaan | Lokasi |
|---|---|---|---|
| A | **Duplikasi tidak menyalin data progres utama** — hanya proyeksi `PekerjaanTahapan`; tanggal selesai & hari batas minggu juga tidak disalin service | Sumber 1 baris → salinan 0 baris | `services.py:4348-4407, 5134-5176` |
| B | **Restore membuang minggu terakhir yang sah** — jumlah minggu `ceil(hari/7)`, tanggal fallback `mulai + 7n` | Proyek 6–13 Sep 2026 (2 minggu) → realisasi M2 tidak kembali | `views_api.py:9683-9719` (juga `9292-9301`) |
| C | **Biaya aktual & catatan hilang saat backup–restore** | Realisasi 15% kembali, biaya 5.000 → kosong | `views_api.py:8919-8926, 9267-9278, 9721-9729` |
| D | **Mengubah hari batas minggu menggeser minggu batas** — minggu yang tadinya waktu kerja bisa menjadi minggu tambahan | Minggu berakhir Minggu → Senin: minggu batas M2 → M1 | `views_api_tahapan_v2.py:525-570` |

### 4.5 Jalur yang menulis rencana (`planned_proportion`)

| # | Jalur | Lokasi | Jenis tulisan |
|---|---|---|---|
| P-1 | Simpan grid (API v2) | `views_api_tahapan_v2.py:315-347` | Rencana **baru** |
| P-2 | Import JSON | `views_api.py:9721-9729` | **Historis** |
| P-3 | Duplikasi (setelah A diperbaiki) | `services.py` | **Historis** |
| P-4 | Mesin resolusi timeline | `timeline_utils.py:335, 582, 594` | **Pemindahan** pilihan user |
| P-5 | Pembentukan ulang struktur | `timeline_utils._regenerate_weekly_structure:620` | Membentuk ulang tahapan — tidak mengubah nilai |
| P-6 | Migrasi data lama | `progress_utils.migrate_existing_data_to_weekly_canonical:419` | Satu kali; memakai argumen legacy, **tidak siap dijalankan ulang**; bukan bagian fitur |

Catatan: `PekerjaanProgressWeekly.save()` menjalankan `full_clean()`, sedangkan
penulisan massal tidak. Aturan kunci rencana **tidak** dipasang di validasi
model, supaya simpan realisasi pada baris historis tidak ikut ditolak.

### 4.6 Titik yang membaca akhir rentang untuk menghitung minggu

Dengan konsep ini, titik-titik berikut harus dipilah menurut **dua acuan** di 5.2:
yang menghitung **rentang pencatatan** beralih ke `work_period_end`, sedangkan
yang menentukan **batas rencana** tetap memakai `tanggal_selesai` lewat helper.
Pemakaian `tanggal_selesai` di Dashboard (status, filter, form, tampilan)
**tetap** — di sana ia memang berarti akhir waktu kerja.

| Modul | Pemakaian |
|---|---|
| `detail_project/timeline_utils.py` | `project_report_period_counts`, `analyze/apply_project_timeline_change`, `_persisted_timeline`, pembentukan ulang |
| `detail_project/progress_utils.py` | Pembentukan tahapan mingguan |
| `detail_project/views_api_tahapan_v2.py` | Batas `week_number` saat simpan (`:174`), pratinjau/eksekusi timeline |
| `detail_project/exports/jadwal_pekerjaan_adapter.py` | Rentang & kolom mingguan export |
| `detail_project/exports/export_manager.py` | Rentang laporan harian |
| `detail_project/readiness.py` | Pemeriksaan jadwal basi |
| `detail_project/views_api.py` | Export/import JSON |
| `detail_project/services.py` | Duplikasi & signature cache jadwal |
| `detail_project/views.py` + template Jadwal | Jumlah periode modal, `data-project-end` |
| `dashboard/models.py` | Pemicu kenaikan `schedule_revision` (tambah field baru) |

Daftar ini titik awal; Tahap 1.1 melakukan **penyisiran penuh** (lihat 6.2).

---

## 5. Rancangan Teknis

### 5.1 Data

- Kolom baru `Project.tanggal_akhir_tambahan` (tanggal, boleh kosong). Perlu
  **migrasi skema** untuk menambah kolom, tetapi **tidak perlu migrasi data**:
  proyek yang ada kosong → perilaku tidak berubah.
- Validasi: bila terisi, harus **setelah** `tanggal_selesai`.
- Kolom ini ikut memicu kenaikan `schedule_revision`.
- Proyek lama yang dulu "diperpanjang" dengan menggeser akhir waktu kerja tetap
  seperti adanya (tidak ada tambahan); pemilik dapat merapikannya manual bila perlu.

### 5.2 Satu sumber aturan (helper di `timeline_utils`)

| Helper (nama indikatif) | Mengembalikan |
|---|---|
| `work_period_end(project)` | Akhir masa waktu kerja: `tanggal_akhir_tambahan` bila terisi, selain itu `tanggal_selesai` |
| `boundary_week(project)` | Nomor minggu yang memuat akhir waktu kerja |
| `is_extension_week(project, week_number)` | `week_number > boundary_week` dan ada tambahan |
| `is_extension_day(project, date)` | `date > tanggal_selesai` dan ada tambahan |

Ada **dua acuan yang berbeda**, dan penyisiran (Tahap 1.1) tidak boleh
menukarnya:

| Acuan | Dipakai untuk | Sumber |
|---|---|---|
| **Rentang pencatatan** | Jumlah & kolom minggu, batas `week_number` saat simpan, rentang export | `work_period_end` (tambahan bila ada) |
| **Batas rencana** | Minggu batas, kunci rencana, penanda, garis "Akhir Waktu Kerja" | `tanggal_selesai`, **lewat** `boundary_week` / `is_extension_week` / `is_extension_day` |

Semua perhitungan memakai helper ini. **Dilarang** menghitung ulang dari tanggal
di tempat lain.

### 5.3 Aturan tulis rencana

Dipasang di **layanan tulis progres** tunggal (Tahap 0.4), yang tahu jenis
tulisannya:

| Jenis tulisan | Jalur | Aturan di minggu tambahan |
|---|---|---|
| Rencana baru | P-1 | **Tolak** rencana > 0 |
| Realisasi & biaya | P-1 (mode Realisasi) | Diterima |
| Historis | P-2, P-3 | **Pertahankan apa adanya**; tandai "rencana di masa tambahan (data lama)" di readiness |
| Pemindahan pilihan user | P-4, operasi 5.5 | Tujuan pemindahan rencana **dibatasi ke minggu waktu kerja** |
| Pembentukan ulang | P-5 | **Tidak memindahkan** nilai apa pun |

### 5.4 Perubahan rentang

**Field yang boleh diubah setiap tindakan** — aturan ini mengikat implementasi:

| Tindakan | `tanggal_mulai` | `tanggal_selesai` | `durasi_hari` | `tanggal_akhir_tambahan` |
|---|---|---|---|---|
| Perpanjang / pendekkan / hapus tambahan (halaman Jadwal) | **Tidak** | **Tidak** | **Tidak** | Ya |
| Edit Project / Edit Massal (Dashboard) | Ya | Ya | Ya (mengikuti rentang Dashboard) | Hanya dikosongkan, bila akhir waktu kerja baru mencapai/melewati tambahan |
| Ubah hari batas minggu | Tidak | Tidak | Tidak | Tidak |

**Penting:** layanan timeline yang ada (`apply_project_timeline_change`,
`timeline_utils.py:778-781`) saat ini **menulis langsung** `tanggal_selesai` dan
`durasi_hari`. Bila dipakai apa adanya untuk tombol perpanjangan, tombol itu akan
mengubah akhir waktu kerja kontrak. Layanan harus menerima **field target** — akhir
rentang disimpan ke `tanggal_akhir_tambahan` untuk tindakan dari halaman Jadwal,
dan ke `tanggal_selesai` untuk tindakan dari Dashboard.

| Tindakan | Implementasi |
|---|---|
| Perpanjang / pendekkan / hapus tambahan (3.2–3.3) | Layanan timeline yang ada, dengan rentang baru = awal waktu kerja s.d. tanggal tambahan baru; field target = `tanggal_akhir_tambahan` saja (tabel di atas). Pratinjau mengembalikan jenis (tipe 1 / tipe 2 / pengurangan) untuk ditampilkan dialog |
| Selaraskan tanggal minggu pendek (C-2) | Saat rentang berubah, tanggal `week_start_date`/`week_end_date` baris progres yang minggunya berubah rentang **ikut diselaraskan**; nomor minggu & nilai tetap |
| Ubah akhir waktu kerja di Dashboard (3.6) | Hitung dulu pasangan hasil: akhir waktu kerja baru, dan tambahan (tetap / dikosongkan bila terlampaui). Validasi pasangan **hasil**, bukan terhadap nilai lama. Bila ada rencana di minggu yang menjadi minggu tambahan → dialog 3.6 |
| Ubah hari batas minggu (D) | `api_update_week_boundaries`, `api_regenerate_tahapan_v2`: bila minggu batas bergeser dan ada rencana di minggu yang menjadi minggu tambahan → pratinjau dan pilihan yang sama dengan 3.6; tidak ada pemindahan otomatis |
| Invariant tanggal | Ditegakkan di lapisan layanan (Dashboard, API timeline, import, duplikasi), bukan hanya form |

### 5.5 Operasi "Pindahkan rencana ke minggu batas"

Operasi khusus (bukan mesin resolusi apa adanya, C-3). Contoh — akhir waktu kerja
dimajukan dari M10 ke M8:

| Data | M8 sebelum | M9 sebelum | M8 sesudah | M9 sesudah |
|---|---|---|---|---|
| Rencana | 10% | 20% | **30%** | **0%** |
| Realisasi | 12% | 15% | 12% | 15% |
| Biaya aktual | Rp3 jt | Rp5 jt | Rp3 jt | Rp5 jt |

Contoh ini berlaku ketika **tambahan waktu kerja tetap mencakup M9**, sehingga
realisasi M9 masih berada di dalam masa waktu kerja. Tanpa tambahan, perubahan yang
memotong realisasi mengikuti **penolakan timeline yang sudah ada**.

Hanya `planned_proportion` yang dipindahkan. Setelahnya: sinkronkan proyeksi
`PekerjaanTahapan`, naikkan revisi jadwal, bersihkan cache jadwal.

### 5.6 Backup, restore, duplikasi (W-1)

| # | Isi | Menutup |
|---|---|---|
| W-1a | Duplikasi menyalin `PekerjaanProgressWeekly` (rencana, realisasi, biaya aktual, catatan) lewat pemetaan ID pekerjaan; proyeksi `PekerjaanTahapan` disinkronkan **dari** data itu | A |
| W-1b | Duplikasi menyalin metadata timeline: akhir waktu kerja, **tambahan**, hari batas minggu; kebijakan untuk duplikasi dengan tanggal mulai baru dinyatakan eksplisit | A |
| W-1c | Restore memakai helper minggu kanonik untuk jumlah minggu & tanggal fallback | B |
| W-1d | Backup–restore membawa biaya aktual & catatan (0 ≠ kosong); backup lama tetap bisa direstore | C |
| W-1e | `tanggal_akhir_tambahan` ikut backup, restore, duplikasi | Fitur ini |

### 5.7 Frontend

| Kebutuhan | Yang ditambahkan |
|---|---|
| Tombol "Perpanjang Waktu Kerja" | Tampil hanya di mode Realisasi (diatur di `_applyProgressModeSwitch`) |
| Dialog | Satu input tanggal + hasil deteksi dari endpoint pratinjau; pola `timeline_repair.js` |
| Status kolom | **Server** mengirim per kolom: `is_extension_week`, `is_boundary_week`, `work_end_date`. Frontend tidak menghitung sendiri |
| Kunci | `readOnly` minggu tambahan **hanya di mode Rencana** (persen & volume) |
| Header | Baris kecil penanda + kelas CSS di render header yang ada |
| Kurva S & Gantt | Garis "Akhir Waktu Kerja" |
| Build | Grid ada di bundle Vite → **build ulang frontend** |

---

## 6. Tahapan Eksekusi

Setiap langkah = satu commit + uji. Uji dijalankan di Docker/PostgreSQL.

### 6.1 Tahap 0 — Konsolidasi pinggiran (tanpa fitur baru)

| Langkah | Isi | Selesai bila |
|---|---|---|
| 0.1 | Uji bolak-balik backup → restore → duplikasi yang membandingkan **seluruh baris** progres (rencana, realisasi, biaya, catatan, nomor & tanggal minggu) | Uji ada dan **gagal** pada kode sekarang, sesuai A–C |
| 0.2 | Import & statistik export JSON memakai helper minggu kanonik (W-1c) | Minggu pertama/terakhir pendek dan hari batas minggu nondefault: tidak ada baris terbuang |
| 0.3 | Satu penyalin data progres untuk export JSON, import JSON, duplikasi (W-1a, b, d) | Uji 0.1 lulus; backup lama tetap bisa direstore |
| 0.4 | Satu layanan tulis progres dengan parameter jenis tulisan, dipakai simpan grid, import, duplikasi — **tanpa** aturan tambahan dulu | Semua uji simpan grid, import, duplikasi, dan 42 uji timeline tetap lulus |

### 6.2 Tahap 1 — Tambahan Waktu Kerja

| Langkah | Isi | Selesai bila |
|---|---|---|
| 1.1 | Kolom `tanggal_akhir_tambahan` (migrasi skema) + helper 5.2 + **penyisiran** semua titik 4.6 menurut dua acuan 5.2 + layanan timeline menerima **field target** (5.4) | Tanpa tambahan: seluruh uji lama lulus tanpa perubahan perilaku. Rentang pencatatan memakai `work_period_end`; batas rencana memakai `tanggal_selesai` lewat helper batas waktu kerja — tidak ada acuan yang tertukar. Perpanjangan dari halaman Jadwal tidak mengubah `tanggal_mulai`, `tanggal_selesai`, maupun `durasi_hari` |
| 1.2 | W-1e: tambahan ikut backup/restore/duplikasi | Uji 0.1 memeriksa tambahan |
| 1.3 | Aturan tulis rencana 5.3 di layanan tulis progres | Rencana di minggu tambahan ditolak; realisasi & biaya diterima; restore historis dipertahankan & ditandai; pembentukan ulang tidak memindahkan nilai (restore rencana M9 → tetap M9) |
| 1.4 | Perpanjang / pendekkan / hapus tambahan + deteksi jenis + penyelarasan minggu pendek (5.4) | Rabu → Jumat: tipe 1, jumlah minggu tetap, tanggal kolom & baris progres sampai Jumat, nilai tetap. 30 Sep → 31 Des: tipe 2, +n minggu, nilai lama tetap. Pendekkan ditolak bila minggu yang dibuang berisi realisasi/biaya |
| 1.5 | Perubahan akhir waktu kerja di Dashboard & Edit Massal dengan tambahan (3.6, 5.4) + operasi 5.5 | Semua baris tabel 3.6 lulus; operasi 5.5 hanya memindahkan rencana, lalu proyeksi/revisi/cache diperbarui |
| 1.6 | Perubahan hari batas minggu (D) | Minggu batas bergeser dengan rencana terdampak → pratinjau & pilihan; tanpa pemindahan otomatis |
| 1.7 | Frontend: tombol & dialog (3.2–3.3), grid (3.7), mode Rencana (3.5), pesan (3.8), Kurva S & Gantt; build Vite | Tombol hanya di mode Realisasi; grid tetap di mode Realisasi setelah simpan; minggu tambahan terkunci di mode Rencana, minggu batas tidak; garis di posisi tanggal akhir waktu kerja |

---

## 7. Risiko dan Mitigasi

| Risiko | Mitigasi |
|---|---|
| Penyisiran 4.6 terlewat satu titik → grid dan export berbeda rentang | Satu helper (5.2); uji paritas: grid, pratinjau, dan jumlah periode export sama untuk proyek dengan tambahan |
| Menyuntikkan aturan per jalur membuat arsitektur berantakan | Tahap 0 menyatukan dulu; aturan hanya di layanan tulis progres |
| Kunci rencana menolak simpan realisasi di baris historis | Aturan di lapisan layanan, bukan `full_clean()` |
| Pembentukan ulang diam-diam memindahkan data historis | Pembentukan ulang tidak memindahkan nilai; pemindahan hanya atas pilihan user |
| Tanggal kolom dan baris progres berbeda setelah perpanjangan | Penyelarasan minggu pendek (5.4) + uji Rabu → Jumat |
| Perubahan hari batas minggu menggeser minggu batas diam-diam | Pratinjau & pilihan (1.6) |
| Dua sesi mengubah rentang bersamaan | Revisi jadwal (sudah ada), tambahan ikut pemicunya |

---

## 8. Keputusan

### 8.1 Sudah diputuskan owner

| # | Keputusan |
|---|---|
| 1 | Minggu tambahan hanya untuk realisasi; tidak ada pembekuan baseline |
| 2 | Waktu kerja = rentang di Dashboard; masa waktu kerja = waktu kerja + tambahan; mengubah akhir waktu kerja tidak memendekkan tambahan |
| 3 | Tambahan diubah (termasuk dipendekkan) hanya lewat "Perpanjang Waktu Kerja" di Jadwal |
| 4 | Satu input tanggal; jenis perpanjangan dideteksi sistem |
| 5 | Hanya di mode Realisasi; tanpa pengingat/banner |
| 6 | Label penanda: "Penambahan Waktu Kerja" |
| 7 | Rencana terdampak karena akhir waktu kerja dimajukan: lewat dialog "Ringkasan dampak" (pindahkan rencana saja / batalkan) |
| 8 | Teks tanggal di export (dulu K-4): tidak sekarang, ikut fase export |
| 9 | Export dibahas setelah fase ini |
| 10 | Status Dashboard di luar cakupan |

### 8.2 Masih terbuka

| # | Pertanyaan | Saran |
|---|---|---|
| T-2 | Kerapian git sebelum Tahap 0: tiga branch bertumpuk belum masuk `main`, WIP belum di-commit, dokumen ini belum di-commit | Rapikan dulu |

### 8.3 Catatan terpisah (tidak menghambat fitur ini)

- **Bobot laporan bisa berubah mundur.** Bobot pekerjaan dihitung ulang dari harga
  RAB saat laporan dibuat, sehingga angka laporan minggu lalu berubah bila RAB
  berubah di tengah proyek. Dibahas sebagai topik tersendiri.

---

## 9. Fase Berikutnya: Export

Dibahas setelah fase ini selesai. Bahan yang sudah terkumpul:

| Bahan | Isi |
|---|---|
| Jalur export Jadwal | E-1 Rekap, E-2 Bulanan, E-3 Mingguan (PDF/Excel); E-4 Harian (Word); E-5 PNG Kurva S/Gantt; E-6 gambar di PDF |
| Yang sudah otomatis benar | Validasi periode & kolom mingguan export membaca satu sumber (R-30) → setelah Tahap 1.1 otomatis mencakup masa tambahan |
| Laporan Harian | Daftar pekerjaan di hari tambahan saat ini kosong sebelum realisasi diisi. Usulan: pekerjaan yang belum selesai s.d. minggu sebelumnya + yang punya realisasi di minggu laporan, dengan keterangan "isian awal" |
| Penanda per format | Teks akhir waktu kerja & tambahan; garis/warna di tabel & Kurva S; subjudul "Penambahan Waktu Kerja" di laporan harian; garis di PNG |
| Endpoint export generik lama | `urls.py:239-253` (CSV/PDF/Word/Excel) tidak dipanggil UI aktif (bundle hanya memakai `professional`; satu-satunya pemanggil, `export-coordinator.js:543`, tidak masuk bundle) → kandidat penghapusan terpisah |

---

## 10. Di Luar Cakupan

- Rencana revisi di minggu tambahan (jadwal *catch-up* terpisah dari baseline).
- Riwayat adendum dan perhitungan denda.
- Pemisahan progres harian di dalam minggu batas (data tetap mingguan).
- Status proyek di Dashboard.
- Pembekuan baseline dan penghapusan otomatis minggu tambahan yang kosong.

---

## Lampiran: Riwayat Revisi

| Versi | Perubahan utama |
|---|---|
| v1 | Draft awal: kolom akhir kontrak, tombol perpanjangan, penanda |
| v2–v4 | Tiga putaran review: aturan minggu vs tanggal, daftar laporan harian, validasi pasangan tanggal, jalur tulis rencana, pembentukan ulang tanpa pemindahan, minggu pendek, operasi pindahkan rencana saja |
| v5 | Audit backend: masalah transfer data A–D, konsolidasi Tahap 0 |
| v6–v7 | Rancangan UI/UX; penyederhanaan owner (satu input tanggal, hanya mode Realisasi, tanpa banner) |
| **v8** | **Konsep diganti mengikuti Dashboard:** akhir waktu kerja tetap berarti batas kontrak; kolom baru menyimpan **tambahan waktu kerja** (bukan sebaliknya) → tidak perlu migrasi data dan Dashboard tidak berubah maknanya. Dokumen disusun ulang: konsep → UI/UX → kondisi sistem → rancangan teknis → tahapan dengan kriteria selesai. Export dipindah ke fase berikutnya |
| v9 | Penegasan dari review v8: tabel field yang boleh diubah tiap tindakan, layanan timeline menerima field target (tombol Jadwal tidak mengubah `tanggal_selesai`/`durasi_hari`); `durasi_hari` tetap rentang Dashboard; dua acuan (rentang pencatatan vs batas rencana) untuk penyisiran; Edit Project (dialog) dibedakan dari Edit Massal (lewati & laporkan); kondisi contoh M10 → M8; catatan tipe 1 di minggu tambahan; migrasi skema vs data; bobot laporan menjadi catatan terpisah |
