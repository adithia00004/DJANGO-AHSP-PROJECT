# Roadmap Mitigasi Perubahan Tipe Pekerjaan

Dokumen ini merangkum celah yang terdeteksi ketika user mengubah `source_type` pekerjaan (REF -> REF_MODIFIED / CUSTOM) beserta rencana perbaikan dan ujiannya. Gunakan sebagai referensi saat menyiapkan peluncuran.

## Status Eksekusi (Log 2025-11-14)

| Tahap | Status | Catatan terbaru |
|-------|--------|-----------------|
| Persiapan sample project & baseline logging | DONE | Dataset uji (REF, CUSTOM, bundle, volume) siap |
| Implementasi Template reload & sink indicator | DONE | Banner + auto lock diterapkan (2025-11-16) |
| Implementasi Harga Items wait state | DONE | Form terkunci saat Template belum sinkron (2025-11-16) |
| Validasi bundle & cascade | TODO | Dieksekusi setelah sinkronisasi Template/Harga stabil |
| Peringatan volume/tahapan | DONE | Badge Volume/Tahapan aktif + highlight (2025-11-16) |
| Observability & housekeeping | TODO | Audit summary + jadwal `validate_ahsp_data` |

Catatan: update tabel ini setiap ada progres agar roadmap berfungsi sebagai log kemajuan.

## Sample Project Uji (Mapping)

| Project | Fokus Sumber | Tujuan Test |
|---------|--------------|-------------|
| Test 1 | Referensi only | Validasi Template read-only & perubahan upstream AHSP |
| Test 2 | Referensi modified only | Uji clone/override serta sinkronisasi Harga/Rincian pasca source change |
| Test 3 | Custom A/B/C | Verifikasi input manual, volume & badge peringatan setelah perubahan struktur |
| Test 4 | Custom + Bundle ke AHSP | Pastikan cascade bundle ke referensi master & audit CASCADE |
| Test 5 | Custom + Bundle antar pekerjaan | Uji chain dependency internal & deteksi bundle orphan |

Beri label jelas di dashboard (mis. `SRC_REF_01`, `SRC_REFMOD_02`, dst.) agar hasil audit mudah dilacak per skenario.

## 1. Template Reload & Sink Indicator
- **Masalah**: Setelah source change, Template masih memegang payload lama dan user bisa menyimpan sebelum data baru dimuat.
- **Perbaikan**:
  - Lock tombol simpan sampai `api_get_detail_ahsp` (prefill) selesai.
  - Paksa reload otomatis setelah response `api_upsert_list_pekerjaan` yang mengubah source.
  - Tambahkan banner "menunggu sinkronisasi" hingga timestamp di change-status diakui.
  - [2025-11-15] Backend `api_upsert_list_pekerjaan` kini mengirim `change_flags.reload_job_ids` dan `change_flags.volume_reset_job_ids` untuk menginformasikan halaman Template tentang pekerjaan yang wajib reload/reset.
  - [2025-11-16] Frontend Template menampilkan banner, overlay blocker, dan modal konflik baru sehingga user wajib memuat ulang sebelum mengedit ulang.
- **Pengujian**:
  - Ubah source lalu langsung klik simpan di Template; UI harus menolak.
  - Pastikan badge sinkron hilang hanya setelah halaman memuat data baru.

## 2. Harga Items Menunggu Sinkronisasi
- **Masalah**: REF -> REF_MODIFIED sempat membuat daftar harga kosong karena ekspansi belum selesai.
- **Perbaikan**:
  - Harga page membaca `/api/project/<id>/change-status`; jika `last_ahsp_change` lebih baru dari acknowledged timestamp, disable form dan tampilkan spinner.
  - Pastikan backend selalu memanggil `_populate_expanded_from_raw` setelah adopt (sudah diterapkan di `views_api.py:680`).
  - [2025-11-16] Harga Items terkunci otomatis saat ada `change_flags.reload_job_ids` dan menampilkan banner/overlay untuk memaksa user membuka Template.
- **Pengujian**:
  - Jalankan source change lalu buka Harga segera. Data harus muncul setelah sinkronisasi selesai (tidak langsung kosong).
  - Lakukan regression test otomatis `TestSourceChangeREFtoREFMOD`.

## 3. Validasi Bundle & Cascade
- **Masalah**: Bundle LAIN dapat menunjuk ke pekerjaan yang sedang dihapus/diganti sehingga cascade gagal.
- **Perbaikan**:
  - Tambah preflight di `api_upsert_list_pekerjaan` untuk menolak payload yang membuat bundle orphan.
  - Setelah transaksi selesai, jalankan `cascade_bundle_re_expansion` via `transaction.on_commit`.
- **Pengujian**:
  - Payload yang menghapus target bundle harus menghasilkan error terarah.
  - Nested bundle test memastikan cascade berjalan dengan order baru.

## 4. Peringatan Volume & Tahapan
- **Masalah**: Volume/tahapan lama bisa tersisa setelah source change sehingga nilai tidak sesuai komponen baru.
- **Perbaikan**:
  - Bandingkan `detail_last_modified` vs `volume.updated_at` dan `tahapan.updated_at`; tampilkan badge "Perlu update volume/jadwal".
  - Blok ekspor Rincian jika badge masih aktif untuk pekerjaan bersangkutan.
  - [2025-11-16] Volume/Tahapan serta Rincian AHSP menyorot pekerjaan pending dan menyediakan banner/peringatan lintas halaman.
- **Pengujian**:
  - Ubah CUSTOM -> REF, cek halaman Volume/Tahapan untuk memastikan badge muncul hingga user menyimpan ulang.
  - Jalankan ekspor saat badge aktif untuk memastikan sistem memberi peringatan.

## 5. Audit Trail yang Jelas
- **Masalah**: Source change menimbulkan banyak entri CREATE/DELETE tanpa penjelasan.
- **Perbaikan**:
  - Di `log_audit`, tambahkan `change_summary` seperti "Source change: CUSTOM -> REF_modified".
  - Kelompokkan entri otomatis (cascade) dengan flag `triggered_by='system'`.
- **Pengujian**:
  - Lakukan rangkaian source change; pastikan timeline audit mudah dibaca dan bisa membedakan aksi user vs sistem.

## 6. Optimistic Locking di List Pekerjaan
- **Masalah**: Payload tree lama bisa menimpa perubahan terbaru (multi-user).
- **Perbaikan**:
  - Tambah `client_version`/timestamp per pekerjaan; backend menolak update jika versi tidak cocok.
  - Kirim pesan "data sudah berubah, silakan refresh".
- **Pengujian**:
  - Dua browser mengedit tree yang sama; salah satunya harus menerima error konflik.

## 7. Validasi AHSP Referensi
- **Masalah**: REF/REF_MOD bisa mengacu ke AHSP yang sudah dihapus di modul referensi.
- **Perbaikan**:
  - Jalankan `python manage.py validate_ahsp_data --all-projects` secara terjadwal, laporkan pekerjaan bermasalah.
  - Di UI, tandai pekerjaan dengan status "referensi tidak ditemukan".
- **Pengujian**:
  - Hapus AHSP master, jalankan command, pastikan laporan muncul dan UI menampilkan badge error.

## Roadmap Refactor Penyetaraan Source Workflow

| Fase | Fokus | Aktivitas Utama | Pengujian |
|------|-------|-----------------|-----------|
| Fase 1 – Layer Backend | Generalisasi handler `source_type` change | - Buat service tunggal yang menangani RESET/clone untuk REF/REF_MOD/CUSTOM.<br>- Response API menambahkan flag `requires_reload`, `new_version`, dan metadata volume/tahapan yang harus direset.<br>- Pastikan audit + change-status di-update konsisten. | - Pytest: extend `test_list_pekerjaan_source_change` untuk semua kombinasi source.<br>- Manual: gunakan Project test 1–5 untuk memastikan log audit dan storage sinkron. |
| Fase 2 – Template Frontend | Otomatis reload + dialog baru | - Template membaca flag `requires_reload` dan otomatis fetch ulang sebelum user mengedit.<br>- Redesign toast menjadi pilihan eksplisit: *Muat ulang* vs *Timpa perubahan terbaru*.<br>- Nonaktifkan tombol simpan sampai fetch selesai. | - Manual: workflow REF→CUSTOM dan CUSTOM→REF tidak lagi memunculkan 409.<br>- UI/UX review dialog baru. |
| Fase 3 – Harga & Rincian | Sinkronisasi lintas halaman | - Harga Items memblokir form sampai Template mengakui versi terbaru (poll change-status).<br>- Rincian menampilkan notifikasi seragam dan bisa menandai sinkron untuk ketiga source.<br>- Volume/Tahapan badge terhubung ke metadata dari Fase 1. | - Pytest/selenium: jalankan scenario Project test 2–5 untuk memastikan Harga/Rincian tidak menampilkan data kosong.<br>- Manual: cek badge volume di Project test 3. |
| Fase 4 – Observability & Otomasi | Monitoring & maintenance | - Update audit trail summary ("Source change: X → Y").<br>- Jadwalkan `validate_ahsp_data` + cleanup report.<br>- Tambahkan telemetry untuk mendeteksi reload paksa/konflik residual. | - Review log setelah regresi; jalankan command di lingkungan staging dan verifikasi output. |

Setiap fase baru boleh dimulai setelah fase sebelumnya lulus uji Project test 1–5 dan update status di tabel eksekusi.

---
Terakhir diperbarui: 2025-11-14. Update dokumen ini setiap kali perbaikan diterapkan atau muncul celah baru.

