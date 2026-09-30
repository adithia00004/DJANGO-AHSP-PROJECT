# 43 — Export Jadwal: Penambahan Waktu Kerja — Rencana & Tracker

| | |
|---|---|
| Tanggal | 2026-09-30 |
| Dasar | Doc 42 (kondisi saat ini, temuan X-1..X-8, L-1..L-6, keputusan K-1..K-16) |
| Pelaksana | **Codex** (eksekutor). **Claude** mengawasi: review diff, menjalankan tes di DB terpisah, memeriksa hasil export sungguhan |
| Branch | `feat/tambahan-waktu-kerja` (lanjutan). WIP owner di working tree **tidak disentuh**; commit hanya memuat hunk milik langkahnya |
| Aturan tampilan | Wajib cek `docs/DESIGN_REGISTRY_EXPORT.md` sebelum mengubah visual; keputusan baru dicatat sebagai R-38 dst. |

Dokumen ini adalah **satu-satunya sumber status** pekerjaan export Penambahan Waktu Kerja.

---

## 1. Ringkasan keputusan yang dieksekusi (dari doc 42 §9)

| # | Isi |
|---|---|
| K-1..K-7 | Lembar **"Rangkuman Progress Akhir Waktu Kerja"**, PDF & Word saja, akumulasi saat kontrak berakhir (s.d. minggu batas + catatan "progres dicatat per minggu"), tabel pekerjaan belum 100% (No, Uraian, Bobot, Realisasi Kumulatif, Sisa, Sisa Bobot, Keterangan kosong), halaman sendiri sebelum pengesahan, tanpa pengesahan di harian |
| §9.2 | Susunan per tipe (tabel §3 di bawah) |
| K-8 | Ekspor yang hanya berisi periode tambahan → Rangkuman di depan |
| K-9 | Laporan masa tambahan **isinya sama** dengan laporan normal; beda hanya teks penanda |
| K-10 | Cover tidak diubah |
| K-11 | Penanda tabel PDF/Excel **sama dengan web**: satu garis tebal di tepi kanan kolom minggu batas + label "Penambahan" di header kolom tambahan |
| K-12 | Excel mingguan **ditambah realisasi** |
| K-13 | Tidak ada keterangan tambahan untuk rencana 100%/deviasi/status |
| K-14 | L-1..L-6 dikerjakan di fase ini |
| K-15 | **Tidak ada kata "terlambat/keterlambatan"** di hasil export; penanda = **"Penambahan Waktu Kerja"** |

---

## 2. Aturan teknis bersama

1. **Satu sumber batas.**
   - Akhir kontrak, minggu batas, minggu/hari tambahan, dan akhir rentang **hanya** dihitung lewat helper `timeline_utils`: `work_period_end`, `contract_boundary_week`, `is_extension_week`, `is_extension_day`.
   - Ini invariant I-5 doc 41. Exporter tidak menghitung sendiri.
2. **Adapter meneruskan metadata.**
   - Kolom minggu membawa `is_boundary_week` dan `is_extension_week`.
   - Data laporan membawa `contract_end`, `additional_end`, `boundary_week`.
   - Proyek tanpa tambahan: semua penanda `False`/`None`, keluaran **identik** dengan sebelum fase ini (I-1).
3. **Angka tidak berubah.** Bobot, kumulatif, deviasi, dan nilai resmi Excel (A-1 doc 30) tetap. Fase ini hanya menambah penanda, lembar Rangkuman, realisasi Excel mingguan, dan perbaikan L-1..L-6.
4. **Tes di lapisan render.** Tes harus membuka file hasil (teks PDF via `pdf_page_texts`, DOCX via python-docx, XLSX via openpyxl), bukan hanya data adapter. Ini pelajaran registri: tes penyedia data lolos meski perender membuang data.
5. **Fixture wajib dua tipe.**
   - **Tipe 1:** akhir kontrak Rabu, tambahan Sabtu di minggu yang sama, tidak ada minggu baru.
   - **Tipe 2:** seperti proyek 217. Akhir kontrak Sabtu; minggu batas memuat satu hari tambahan (Minggu); lalu satu minggu baru.

---

## 3. Susunan dokumen yang harus dihasilkan

"Masa tambahan" = periode sesudah akhir kontrak. **"Periode batas"** = minggu/bulan yang memuat akhir kontrak.

| Laporan | Tipe 1 | Tipe 2 |
|---|---|---|
| Harian (Word) | [hari ≤ akhir kontrak] **[Rangkuman]** [hari tambahan, bertanda PWK] | sama |
| Mingguan (PDF) | [… minggu batas] **[Rangkuman]** | [… minggu batas] **[Rangkuman]** [minggu tambahan, bertanda PWK] |
| Bulanan (PDF) | [… bulan batas] **[Rangkuman]** | [… bulan batas] **[Rangkuman]** [bulan sesudahnya, bertanda PWK, bila ada] |

PWK = "Penambahan Waktu Kerja".

Aturan penempatan:
- **Harian:** setiap hari **sesudah** akhir kontrak bertanda PWK, termasuk hari tambahan di minggu batas.
- Rangkuman muncul bila periode yang dipilih mencakup periode batas atau periode sesudahnya (K-7).
- Ekspor yang hanya berisi masa tambahan: Rangkuman di depan (K-8).
- Ekspor yang hanya berisi periode sebelum periode batas: tidak ada Rangkuman.
- Periode batas sendiri memakai teks normal. Kolom tambahan di dalamnya ditandai lewat K-11.

---

## 4. Langkah

### E0 — Fixture & baseline

- **Isi:** fixture tes tipe 1 dan tipe 2 (bisa di modul tes baru `tests_export_penambahan_waktu_kerja.py`).
- **Baseline:** rekam suite penuh `detail_project` + `dashboard` di DB terisolasi, serta Vitest.
- **Selesai bila:** baseline tercatat di §6. Kegagalan yang diketahui hanya 3 tes lama (lihat doc 41 §3).

### E1 — Metadata batas di adapter

- **Isi:** aturan §2 butir 1–2 di `jadwal_pekerjaan_adapter.py` (kolom minggu, data rekap/bulanan/mingguan, data harian).
- **Tes:**
  - tipe 1: minggu batas benar, tidak ada minggu tambahan;
  - tipe 2: W6 batas, W7 tambahan;
  - proyek tanpa tambahan: semua `False`.
- **Selesai bila:** metadata dipakai dari helper; tidak ada perhitungan tanggal baru di exporter.

### E2 — Laporan harian di masa tambahan (X-1)

- **Isi:**
  - batas akhir `_build_laporan_harian_sheets`/`_resolve_laporan_harian_dates` = `work_period_end` (`export_manager.py:1284`);
  - halaman hari sesudah akhir kontrak diberi penanda PWK (K-15);
  - isi halaman sama dengan hari normal (K-9).
- **Tes (render DOCX):**
  - tipe 2 minggu 7 kini berhasil;
  - minggu 6 memuat hari tambahan 20/09 dengan penanda;
  - hari masa kontrak tanpa penanda;
  - tidak ada kata "terlambat".
- **Selesai bila:** periode di luar `work_period_end` tetap ditolak (`ExportValidationError`, R-30).

### E3 — Rangkuman Progress Akhir Waktu Kerja

- **Data:** satu metode adapter (misalnya `get_contract_end_summary`), dipakai PDF dan Word.
  - Akumulasi rencana/realisasi/deviasi s.d. minggu batas, berbobot, **memakai fungsi bobot yang sama** dengan laporan lain.
  - Daftar pekerjaan dengan realisasi < 100% s.d. minggu batas.
  - Kolom per pekerjaan: bobot, realisasi kumulatif, sisa, sisa bobot.
  - Catatan "progres dicatat per minggu; minggu batas dd/mm–dd/mm".
- **Render:** PDF (mingguan, bulanan) dan Word (harian), sebagai halaman sendiri, dengan penempatan sesuai §3.
- **Tes (render):**
  - urutan halaman untuk semua kasus §3: tipe 1 dan tipe 2, campuran, hanya-tambahan, hanya-sebelum-batas;
  - angka Rangkuman = kumulatif laporan mingguan minggu batas;
  - Excel **tidak** memuat Rangkuman (K-2).
- **Selesai bila:** registri R-38 (Rangkuman) tercatat.

### E4 — Penanda masa tambahan di PDF (K-11, K-9)

- **Isi:**
  - garis tebal di tepi kanan kolom minggu batas dan label "Penambahan" di header kolom tambahan, pada semua tabel mingguan PDF: grid Rencana/Realisasi Rekap, tabel Kurva S, Gantt;
  - subjudul PWK pada laporan mingguan/bulanan untuk periode tambahan (tipe 2).
- **Periksa juga X-8:** apakah Kurva S muncul dua kali di PDF Rekap (gambar browser + gambar server). Laporkan temuannya; putuskan bersama owner sebelum mengubah.
- **Tes (render):** penanda ada hanya pada proyek bertambahan; posisinya di kolom minggu batas yang benar.
- **Selesai bila:** registri R-39 tercatat.

### E5 — Excel (K-11, K-12)

- **Isi:**
  - penanda K-11 di sheet Excel yang memiliki kolom minggu: Data Master, Rincian, Kurva S, Input Progress-Gantt;
  - Excel mingguan ditambah realisasi (K-12).
- **Perhatian:** doc 30 §8.3 mengunci Excel mingguan sebagai "planned-only" beserta gate-nya. Perbarui gate dan doc 30. Nilai tetap nilai backend (A-1), tanpa formula recompute di sheet resmi.
- **Tes (render XLSX):**
  - minggu tambahan tipe 2 menampilkan realisasi (proyek 217 W7 = 9,45%);
  - gate paritas doc 30 tetap hijau.
- **Selesai bila:** registri R-40 (penanda Excel) dan revisi R-14/doc 30 tercatat.

### E6 — Perbaikan L-1..L-6

| # | Isi |
|---|---|
| L-1 | Anggaran cover Excel Rekap = anggaran pemilik, format id-ID, sama dengan PDF |
| L-2 | Label Indonesia di tabel/Excel ("Minggu", "Bulan", "Realisasi"); status Ahead/Behind tidak dicetak (K-13), jadi cukup dibiarkan |
| L-3 | Label bulan tidak melebihi minggu nyata (M2 = "W5–W7") |
| L-4 | Footer halaman cover laporan kedua memakai judul yang benar |
| L-5 | Sisa float (`2e-28`) dibulatkan di boundary exporter |
| L-6 | Doc 12 diperbarui ke jalur export saat ini |

- **Tes:** satu tes render per butir L-1, L-3, L-4, L-5.
- **Selesai bila:** registri diperbarui bila menyangkut tampilan.

### E7 — Verifikasi akhir

1. Suite penuh `detail_project` + `dashboard` di DB terisolasi: tidak ada kegagalan di luar baseline.
2. Vitest penuh dan `npm run build` (bila JS berubah).
3. Probe export proyek 217 (semua laporan × format, di transaksi rollback) dan fixture tipe 1: urutan halaman, penanda, Rangkuman, tanpa kata "terlambat".
4. UAT owner (§5).

---

## 5. Checklist UAT (owner)

| # | Skenario | Diharapkan | Hasil |
|---|---|---|---|
| U-1 | Harian minggu 7 proyek 217 | Berhasil; halaman 21/09 bertanda PWK; Rangkuman di depan | |
| U-2 | Harian minggu 6 proyek 217 | 14–19/09 normal, Rangkuman, lalu 20/09 bertanda PWK | |
| U-3 | Mingguan W6+W7 PDF | [W6] [Rangkuman] [W7 bertanda PWK] | |
| U-4 | Bulanan M1+M2 PDF | [M1] [M2] [Rangkuman]; kolom W7 berlabel "Penambahan", garis di tepi W6 | |
| U-5 | Rekap PDF & Excel | Garis batas di W6, label "Penambahan" di W7, tanpa Rangkuman di Excel | |
| U-6 | Mingguan Excel W7 | Realisasi 9,45% tampil | |
| U-7 | Proyek tanpa tambahan | Tidak ada perbedaan dari sebelum fase ini | |
| U-8 | Proyek tipe 1 | Mingguan/bulanan hanya menambah Rangkuman; harian menandai hari tambahan | |
| U-9 | Semua file | Tidak ada kata "terlambat/keterlambatan" | |

---

## 6. Progres

| Langkah | Status | Commit | Tanggal | Catatan |
|---|---|---|---|---|
| E0 | REVIEW | commit ini | 2026-09-30 | Fixture tipe 1, tipe 2, tanpa tambahan lulus; baseline backend 894 tes/3 gagal lama/40 skipped, frontend 431 lulus/25 skipped |
| E1 | TODO | | | |
| E2 | TODO | | | |
| E3 | TODO | | | |
| E4 | TODO | | | |
| E5 | TODO | | | |
| E6 | TODO | | | |
| E7 | TODO | | | |

Status: `TODO` / `WIP` / `REVIEW` (menunggu pemeriksaan Claude) / `DONE` / `BLOCKED`.
Setiap langkah = satu commit kode + catatan bukti uji di bawah.

## 7. Log bukti uji

| Tanggal | Langkah | Perintah | Hasil |
|---|---|---|---|
| 2026-09-30 | E0 baseline backend | `docker exec -e POSTGRES_TEST_DB=test_twk_export_43_20260930 ahsp_web python manage.py test detail_project dashboard --settings=config.settings.test_pg --noinput --verbosity=1` | 894 tes; 3 gagal baseline yang sama dengan doc 41 §3; 40 skipped. DB terisolasi dibuat dan dihancurkan. |
| 2026-09-30 | E0 baseline frontend | `npm run test:frontend -- --reporter=dot --silent` | 39 file; 431 lulus, 25 skipped. |
| 2026-09-30 | E0 fixture | `docker exec -e POSTGRES_TEST_DB=test_twk_export_43_e0 ahsp_web python manage.py test detail_project.tests_export_penambahan_waktu_kerja --settings=config.settings.test_pg --noinput --verbosity=1` | 3 lulus: tambahan satu minggu yang sama, tambahan sampai W7, tanpa tambahan. |

## 8. Log temuan & keputusan tambahan

| Tanggal | Langkah | Temuan / keputusan | Oleh |
|---|---|---|---|
| | | | |
