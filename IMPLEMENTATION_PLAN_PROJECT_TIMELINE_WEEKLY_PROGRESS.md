# Rencana Implementasi: Timeline Project dan Perubahan Planned Progress Mingguan

**Status:** Implementasi selesai, siap diuji di Docker  
**Tanggal:** 2026-08-02  
**Area:** `dashboard` dan `detail_project` — Timeline Project / Jadwal Pekerjaan

## 1. Tujuan

Memperbaiki pengelolaan tanggal project agar:

- `tanggal_mulai` dan `tanggal_selesai` wajib diisi user;
- sistem tidak lagi memakai 31 Desember sebagai tanggal selesai otomatis untuk project baru;
- perubahan tanggal selesai tetap menjaga konsistensi struktur mingguan;
- planned progress yang berada di luar tanggal baru tidak hilang tanpa persetujuan;
- actual progress tidak pernah dipotong otomatis;
- halaman Jadwal memiliki penjelasan dan tindakan yang jelas ketika struktur mingguan perlu diperbarui.

## 2. Temuan implementasi saat ini

### 2.1 Default tanggal selesai

`dashboard/models.py` mengisi `tanggal_selesai` ke 31 Desember tahun `tanggal_mulai` ketika field tersebut kosong. Aturan ini juga dipakai sebagai asumsi pada dokumentasi upload Excel.

Akibatnya, sistem tidak bisa membedakan:

- tanggal selesai yang benar-benar dimasukkan user;
- tanggal selesai sementara yang dibuat oleh sistem.

### 2.2 Fallback frontend

Halaman Jadwal juga memakai 31 Desember jika `projectEnd` tidak tersedia. Fallback tersebut membuat frontend menghitung jumlah minggu yang lebih panjang daripada yang mungkin dimaksud user.

### 2.3 Struktur weekly

`PekerjaanProgressWeekly` adalah sumber data canonical untuk planned/actual progress mingguan. `PekerjaanTahapan` adalah struktur/projection yang dapat dibuat ulang dari data canonical.

Ketika rentang tanggal project berubah, struktur `TahapPelaksanaan` lama tidak otomatis selalu cocok dengan rentang baru. Hal ini memicu advisory “struktur waktu mingguan belum lengkap”.

## 3. Kebijakan produk yang disepakati

### 3.1 Input timeline wajib

Project baru harus memiliki:

```text
tanggal_mulai
tanggal_selesai
```

Validasi:

```text
tanggal_selesai >= tanggal_mulai
```

`durasi_hari` boleh tetap dihitung otomatis dari kedua tanggal tersebut dan tidak perlu menjadi input wajib terpisah.

Tidak ada fallback tanggal selesai ke 31 Desember pada project baru.

### 3.2 Project lama

Project lama yang masih memiliki tanggal kosong tidak boleh langsung dianggap selesai pada 31 Desember.

Rencana penanganan:

- tampilkan status “Timeline belum lengkap”;
- minta user mengisi kedua tanggal;
- blokir pembuatan/regenerasi Jadwal sampai timeline lengkap;
- lakukan audit/migrasi data sebelum database diubah menjadi `NOT NULL`.

### 3.3 Perubahan tanggal selesai

#### A. Tanggal selesai diperpanjang

Contoh:

```text
Lama: 01-01-2026 s.d. 31-03-2026
Baru: 01-01-2026 s.d. 30-04-2026
```

Perilaku:

- minggu existing dipertahankan;
- minggu baru dibuat kosong;
- planned progress existing tidak berubah;
- actual progress existing tidak berubah;
- struktur tahapan diperbarui agar mencakup rentang baru.

#### B. Tanggal selesai berubah tetapi jumlah minggu tidak berubah

Perilaku:

- perbarui batas tanggal struktur minggu;
- jangan memindahkan nilai progress;
- jangan menghapus record weekly.

#### C. Tanggal selesai dipersingkat tanpa progress terdampak

Jika tidak ada planned maupun actual progress pada minggu yang keluar dari rentang baru, perubahan dapat dilanjutkan dan struktur diperbarui.

#### D. Tanggal selesai dipersingkat dengan planned progress terdampak

Pilihan user dibatasi menjadi:

```text
[Batalkan Perubahan]
[Potong Planned Progress]
```

Jika user memilih **Batalkan Perubahan**, tidak ada perubahan tanggal maupun data jadwal.

Jika user memilih **Potong Planned Progress**, tampilkan konfirmasi kedua sebelum mutasi data.

#### E. Tanggal selesai dipersingkat dengan actual progress terdampak

Perubahan harus diblokir. Actual progress adalah catatan realisasi dan tidak boleh dihapus, dipindahkan, atau dipotong otomatis.

## 4. Definisi progress yang terdampak

Sebuah record weekly dianggap terdampak jika periode minggu canonical melewati tanggal selesai baru.

Untuk tahap pertama, gunakan aturan konservatif:

```text
week_end_date > tanggal_selesai_baru
```

Jika satu minggu hanya sebagian yang melewati tanggal selesai baru, seluruh alokasi weekly dianggap terdampak. Sistem tidak melakukan prorata otomatis.

Contoh:

```text
Week 8: 23-03-2026 s.d. 29-03-2026
Tanggal selesai baru: 25-03-2026
```

Week 8 masuk daftar terdampak karena penyimpanan progress menggunakan unit mingguan, bukan harian.

## 5. Alur konfirmasi dua tahap

### 5.1 Dialog pertama — analisis dampak

Saat user menyimpan tanggal selesai baru yang lebih pendek, sistem menampilkan:

```text
Tanggal selesai baru memotong sebagian rentang jadwal.

Minggu terdampak: Week 9 – Week 12
Periode: 01-03-2026 – 28-03-2026
Pekerjaan terdampak: 6
Planned progress terdampak: 18 record

Pilih tindakan:

[Batalkan Perubahan]
[Potong Planned Progress]
```

Dialog harus menjelaskan bahwa actual progress, jika ada, menyebabkan perubahan tidak dapat dilanjutkan.

### 5.2 Dialog kedua — konfirmasi pemotongan

Setelah user memilih **Potong Planned Progress**, tampilkan dialog bahaya:

```text
Konfirmasi pemotongan planned progress

Planned progress berikut akan dipotong:

Minggu: Week 9 – Week 12
Tanggal: 01-03-2026 – 28-03-2026
Pekerjaan terdampak: 6
Record terdampak: 18

Nilai planned pada periode tersebut akan menjadi 0.
Data tersebut tidak akan dipindahkan atau dikompresi ke minggu lain.

[Kembali]
[Ya, Potong Planned Progress]
```

Tidak boleh ada perubahan database sebelum konfirmasi kedua selesai.

## 6. Aturan pemotongan planned progress

Jika user menyetujui:

- `planned_proportion` pada record terdampak diubah menjadi `0`;
- `actual_proportion` tidak boleh diubah;
- record tidak dihapus secara diam-diam;
- nilai sebelum pemotongan dicatat dalam audit trail;
- struktur tahapan dibuat ulang setelah project date berhasil disimpan;
- perubahan dilakukan dalam satu transaksi database.

Jika record terdampak memiliki actual progress lebih besar dari 0, proses dihentikan dan user diminta mengembalikan tanggal selesai atau menyelesaikan data actual secara manual.

## 7. Arsitektur implementasi

### Tahap A — Validasi timeline

Terapkan validasi pada semua jalur input:

- `ProjectForm`;
- formset tambah project;
- upload Excel;
- edit project;
- duplicate/copy project;
- endpoint API yang menerima tanggal project.

Validasi model/database dilakukan bertahap:

1. audit project dengan tanggal kosong;
2. perbaiki project lama melalui input user atau proses migrasi yang disetujui;
3. hapus fallback 31 Desember dari `Project.save()`;
4. hapus fallback 31 Desember dari JavaScript;
5. setelah data bersih, ubah field menjadi `NOT NULL` bila diperlukan.

### Tahap B — Layanan analisis dampak

Buat satu service terpusat untuk menghitung dampak perubahan tanggal, misalnya:

```python
analyze_project_timeline_change(
    project,
    new_start,
    new_end,
)
```

Service mengembalikan:

- jumlah minggu lama dan baru;
- minggu yang ditambah;
- minggu yang keluar dari rentang;
- planned record terdampak;
- actual record terdampak;
- daftar pekerjaan terdampak;
- tanggal awal/akhir periode terdampak;
- apakah perubahan aman dilakukan.

Frontend tidak boleh menghitung daftar dampak sendiri secara terpisah dari backend.

### Tahap C — Preview dan commit

Gunakan alur dua langkah:

1. **Preview** perubahan tanggal dan dampak.
2. **Commit** perubahan dengan pilihan eksplisit `cancel` atau `trim_planned`.

Payload commit dapat berbentuk:

```json
{
  "tanggal_mulai": "2026-01-01",
  "tanggal_selesai": "2026-02-28",
  "resolution": "trim_planned"
}
```

Backend wajib menghitung ulang dampak pada saat commit. Jangan mempercayai daftar minggu yang dikirim frontend karena data dapat berubah setelah preview.

### Tahap D — Rebuild struktur waktu

Setelah commit timeline:

- regenerate `TahapPelaksanaan` mingguan;
- pertahankan `PekerjaanProgressWeekly` yang masih berada dalam rentang;
- tambahkan minggu baru sebagai kosong jika project diperpanjang;
- sinkronkan `PekerjaanTahapan` dari weekly canonical;
- invalidate cache jadwal dan readiness;
- catat perubahan timeline dan keputusan trim.

### Tahap E — UI Jadwal

Tambahkan tombol yang benar-benar tersedia:

```text
Perbarui Struktur Waktu
```

Tombol sekarang benar-benar tersedia pada toolbar dan memicu regenerate terkontrol.
Regenerate tetap meminta konfirmasi jika ada perubahan belum disimpan, mengirim
`schedule_revision`, dan memuat ulang data setelah server berhasil menyusun ulang.
Tidak ada regenerate otomatis saat page-open.

Jika timeline belum lengkap, tampilkan pesan:

```text
Tanggal mulai dan tanggal selesai project wajib diisi sebelum struktur waktu dibuat.
```

## 8. Risiko dan mitigasi

| Risiko | Mitigasi |
|---|---|
| Project lama masih kosong tanggal | Audit dan minta input user sebelum enforcing `NOT NULL` |
| Tanggal selesai otomatis 31 Desember masih muncul dari frontend | Hapus fallback frontend setelah validasi backend siap |
| Planned progress terpotong tanpa sengaja | Preview + dua konfirmasi + audit trail |
| Actual progress ikut terhapus | Block perubahan jika actual terdampak |
| Minggu parsial dianggap aman padahal alokasinya weekly | Anggap terdampak jika `week_end_date` melewati tanggal baru |
| User melakukan double-submit | Gunakan request id/idempotency atau lock transaksi |
| Preview sudah tidak sesuai saat commit | Backend menghitung ulang dampak saat commit |
| Struktur derived tidak sinkron | Rebuild `PekerjaanTahapan` dari `PekerjaanProgressWeekly` |
| Perubahan tanggal menyebabkan cache stale | Invalidate cache timeline, assignments, chart, dan readiness |
| Project diperpanjang lalu minggu baru memiliki nilai lama tersembunyi | Minggu baru harus dibuat kosong dan diverifikasi melalui API |

## 8A. Hardening CRUD Jadwal Pekerjaan

Audit tambahan pada page Jadwal menemukan risiko yang harus ditangani bersamaan
dengan perubahan timeline. Tujuannya adalah memastikan data canonical,
projection, cache, dan tampilan selalu mengikuti transaksi yang sama.

### 8A.1 Reset progress

- Reset harus membawa `mode` secara eksplisit (`planned` atau `actual`).
- Mode tidak valid harus ditolak dengan `400`, bukan diam-diam dianggap
  `planned`.
- Reset `actual` juga mengosongkan `actual_cost`.
- Setelah reset, sinkronkan `PekerjaanTahapan` dan invalidate cache jadwal,
  assignment, readiness, chart, dan progress.
- Konfirmasi UI harus menyebut mode dan jumlah record yang akan berubah.
- Audit minimal menyimpan mode, jumlah record, user, dan waktu perubahan.

### 8A.2 Sumber data dan projection

`PekerjaanProgressWeekly` tetap menjadi satu-satunya sumber data canonical.
`PekerjaanTahapan` hanya projection dan harus selalu dibuat ulang melalui
`sync_weekly_to_tahapan`. Endpoint CRUD legacy yang masih aktif harus tidak
boleh menghasilkan perubahan yang kemudian hilang saat sinkronisasi.

### 8A.3 Stale write dan konkurensi

- Tambahkan versi struktur jadwal (`schedule_revision`) pada project.
- API baca mengembalikan versi tersebut dan API simpan wajib mengirim versi
  yang dibaca oleh browser.
- Jika versi berubah karena regenerate, perubahan batas minggu, atau perubahan
  tanggal, server menolak payload lama dengan status `409`.
- Mekanisme ini melindungi dua tab browser dan dua proses user yang menyimpan
  minggu yang sama. Pencegahan double-submit di satu tab tetap dipertahankan.

### 8A.4 Validasi server

- Timeline lengkap (`tanggal_mulai` dan `tanggal_selesai`) wajib untuk semua
  operasi jadwal write.
- `tanggal_selesai` tidak boleh sebelum `tanggal_mulai`.
- `week_number` harus berada pada rentang minggu project saat ini.
- `mode` progress yang tidak dikenal harus ditolak.
- `actual_cost` harus memiliki operasi clear yang eksplisit; field yang tidak
  dikirim tidak boleh dianggap sebagai perintah menghapus nilai.
- Backend menghitung ulang semua dampak pada saat commit dan tidak mempercayai
  daftar minggu dari frontend.

### 8A.5 Struktur tahapan dan endpoint legacy

- Regenerate harus memvalidasi timeline sebelum menyimpan batas minggu.
- Reorder harus memvalidasi bahwa semua tahapan project dikirim tepat satu kali.
- Tahapan auto-generated tidak boleh menjadi sumber edit manual yang dapat
  bertentangan dengan weekly canonical.
- Endpoint legacy yang deprecated diarahkan ke migrasi atau dibatasi agar tidak
  menulis projection secara langsung.

### 8A.6 Cache dan audit

Setiap mutasi yang mengubah weekly progress, batas minggu, timeline, reset,
atau projection wajib menggunakan invalidasi cache terpusat. Penyimpanan biasa
dan reset minimal dicatat sebagai audit batch dengan nilai ringkas sebelum dan
sesudah perubahan; tidak perlu mencatat setiap ketikan di browser.

## 9. Kriteria penerimaan

- Tanggal mulai dan tanggal selesai wajib diisi pada project baru.
- Project baru tidak lagi mendapatkan tanggal selesai otomatis 31 Desember.
- Halaman Jadwal tidak memakai fallback 31 Desember.
- Project dengan tanggal kosong mendapat pesan yang jelas.
- Perpanjangan tanggal menambah minggu kosong tanpa mengubah progress lama.
- Pemendekan tanpa progress terdampak dapat dilanjutkan.
- Pemendekan dengan planned terdampak hanya menyediakan pilihan batal atau potong planned.
- Pilihan potong planned selalu membutuhkan konfirmasi kedua.
- Dialog menampilkan nomor minggu, rentang tanggal, jumlah pekerjaan, dan jumlah record terdampak.
- Pemendekan dengan actual terdampak selalu diblokir.
- Planned yang dipotong menjadi 0 dan perubahan lama tercatat di audit trail.
- Tidak ada progress yang dipindahkan atau dikompresi otomatis.
- Rebuild struktur mempertahankan weekly canonical storage.
- Reset mode Planned dan Actual mengubah field yang benar dan projection/cache
  tidak menyisakan nilai lama.
- Payload dari browser lama ditolak ketika `schedule_revision` sudah berubah.
- Penyimpanan weekly ditolak jika timeline kosong, mode tidak valid, atau week
  berada di luar rentang project.
- Reorder tidak dapat menghasilkan `urutan` ganda atau tahapan yang tertinggal.
- Perubahan tanggal dapat diuji dari form project maupun halaman Jadwal.
- Template dan import lama tidak terpengaruh oleh fitur ini.

## 10. Test matrix

| Skenario | Hasil yang diharapkan |
|---|---|
| Tanggal selesai kosong saat membuat project | Validasi gagal |
| Tanggal selesai lebih kecil dari tanggal mulai | Validasi gagal |
| Project lama tanpa tanggal membuka Jadwal | Jadwal diblokir dengan pesan jelas |
| Tanggal selesai diperpanjang | Minggu baru kosong dibuat |
| Tanggal selesai berubah dalam minggu yang sama | Struktur tanggal diperbarui, progress tetap |
| Tanggal selesai dipersingkat tanpa progress | Perubahan berhasil |
| Planned progress berada di Week 9–12 | Preview menampilkan Week 9–12 dan tanggalnya |
| User memilih batalkan | Tidak ada data yang berubah |
| User memilih potong lalu membatalkan konfirmasi kedua | Tidak ada data yang berubah |
| User mengonfirmasi potong | Planned affected menjadi 0 dan audit tercatat |
| Actual progress berada di minggu terdampak | Perubahan ditolak |
| Preview stale sebelum commit | Backend menghitung ulang dan menolak jika kondisi berubah |
| Refresh setelah perubahan tanggal | Struktur dan progress tetap konsisten |
| Reset Planned | Hanya planned yang menjadi 0, actual dan cost tetap |
| Reset Actual | Actual menjadi 0, actual cost menjadi kosong, planned tetap |
| Reset dari UI mode Actual | API menerima `mode=actual` |
| Reset lalu baca endpoint lama/projection | Tidak ada progress lama yang tertinggal |
| Save dengan schedule revision lama | Ditolak `409`, data baru tidak berubah |
| Save dengan tanggal project kosong | Ditolak `400` |
| Save dengan week di luar rentang project | Ditolak `400` |
| Save dengan mode tidak dikenal | Ditolak `400`, bukan fallback Planned |
| Regenerate dengan timeline kosong | Tidak mengubah batas minggu atau tahapan |
| Reorder dengan tahapan hilang/duplikat | Ditolak `400` |
