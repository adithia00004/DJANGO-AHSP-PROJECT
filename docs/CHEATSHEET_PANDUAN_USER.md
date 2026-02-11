# Cheatsheet Pengguna AHSP Project

Dokumen ringkas ini untuk eksekusi cepat.  
Referensi lengkap tetap di `PANDUAN_USER.md`.

## 1) Alur Wajib (Urutan Kerja)

1. `Dashboard`: buat project, isi data wajib dan tanggal proyek.
2. `List Pekerjaan`: susun klasifikasi -> sub klasifikasi -> pekerjaan.
3. `Volume Pekerjaan`: isi volume/fx formula.
4. `Template AHSP`: cek komponen TK/BHN/ALT/LAIN.
5. `Harga Items`: isi harga item + BUK default.
6. `Rincian AHSP`: validasi detail perhitungan (hanya-baca).
7. `Rekap RAB`: cek total, PPN, pembulatan.
8. `Rekap Kebutuhan` + `Jadwal`: finalisasi kebutuhan dan timeline.

## 2) Input Minimum Agar Hasil Tidak Nol

- `Dashboard`: Nama project, sumber dana, lokasi, client, anggaran, tanggal mulai.
- `List Pekerjaan`: minimal 1 pekerjaan valid.
- `Volume`: pekerjaan utama tidak boleh kosong.
- `Harga Items`: item kritis tidak boleh nol.
- `Jadwal`: tanggal mulai + tanggal selesai wajib, rencana total 100% per pekerjaan.

## 3) Operasi Cepat Bernilai Tinggi

- Simpan struktur sebagai template: `List Pekerjaan -> Simpan Sebagai Template`.
- Pakai ulang template: `Template Library -> Import Template`.
- Backup penuh project: `Dashboard -> Export Project (JSON)`.
- Proyek serupa: gunakan `Copy Project` (single/batch).
- Perlu margin khusus: `Rincian AHSP -> Override BUK`.

## 4) Import/Export Singkat

- `Export Template JSON`: khusus struktur list pekerjaan.
- `Export Project (JSON)`: backup lengkap proyek.
- `Import Template`: menambah data (append), bukan overwrite.
- `Import Project (JSON)`: membuat project baru dari backup.
- Akses ekspor dipengaruhi status subscription.

## 5) Shortcut Penting

- `Ctrl+S`: simpan (Template AHSP/Jadwal).
- `Ctrl+K`: fokus pencarian (Rincian AHSP).
- `Shift+O`: buka override BUK.
- `Del`: hapus baris terpilih (Template AHSP).
- `Esc`: tutup modal.

## 6) Cek Sebelum Final Ekspor

1. Volume tervalidasi, formula penting benar.
2. Harga item kritis terisi.
3. BUK, PPN, pembulatan sesuai dokumen.
4. Nilai Rincian AHSP konsisten dengan Rekap RAB.
5. Filter halaman sudah sesuai data yang ingin diekspor.
6. Format ekspor sesuai kebutuhan dan hak akses user.

## 7) Troubleshooting Super Cepat

- Total RAB nol: cek volume kosong atau harga nol.
- Nilai tidak berubah: pastikan `Save`, lalu reload data terkait.
- Import template dobel: perilaku normal karena append.
- Ekspor gagal: cek subscription, koneksi, lalu ulangi sekali.
- Jadwal error: cek tanggal proyek dan total rencana 100%.
