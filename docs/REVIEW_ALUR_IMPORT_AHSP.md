# Review Profesional: Alur Kerja Import AHSP

**Tanggal:** 2026-06-02
**Revisi:** v7 (sinkron dengan kode: R1 Interchange v1 + Bug A/B SUDAH diimplementasikan; tambah Bagian 1.1 Status Implementasi; perbaiki peta alur & temuan yang kini usang).
**Lingkup:** Subsistem import referensi AHSP (`referensi/`), dari PDF -> Excel -> validasi -> staging -> database.
**Tujuan:** Pendapat profesional apakah alur ini bisa disederhanakan/dirampingkan, dan usulan standarisasi agar prosesnya tidak terlalu panjang dan rapuh.

> Catatan: dokumen ini sengaja ditulis ASCII-only (memakai `->` dan `--`, bukan panah/em-dash Unicode) agar tidak muncul karakter rusak (mojibake) di berbagai editor/terminal.

---

## 1. Ringkasan Eksekutif (Verdict)

Pembagian menjadi tiga tahap (konversi -> validasi -> staging/import) **secara konsep sudah benar** -- ia memberi titik kontrol bagi manusia untuk membetulkan hasil ekstraksi PDF yang kotor sebelum data masuk database referensi yang dipakai semua proyek. **Masalahnya bukan pada jumlah tahapnya**, melainkan pada **kontrak data antar tahap yang terlalu implisit dan bergantung pada bentuk Excel**:

> Data di-serialisasi bolak-balik ke file Excel dengan **kontrak berbasis posisi kolom**, dan tiap tahap menuntut **download lalu upload manual**. Inilah sumber kerapuhan (semua bug sesi ini -- sheet salah, kolom geser, kode terpotong, tag template, "tidak ada data valid" -- berasal dari titik serialisasi ini) sekaligus sumber "beban" yang dirasakan.

**Tiga perubahan berdampak terbesar:**

1. **Standarkan satu kontrak data** ("AHSP Interchange v1") untuk Excel yang memang harus melintas batas: satu sheet data, kolom bernama tetap, `sumber` + `schema_version` tertanam, **parse selalu by-nama, tidak pernah by-posisi**. Ini fondasi semua langkah lain.
2. **Pangkas round-trip Excel** antara validasi -> staging: sediakan tombol **"Kirim ke Staging" langsung** dari halaman validasi (memakai payload/preflight yang sama). Excel menjadi **artefak opsional**, bukan jembatan wajib.
3. **Bereskan kode mati dengan hati-hati**: arsipkan **alur web yang tidak ter-route**, tetapi **jangan hapus service yang masih dipakai CLI/Task** (lihat Temuan B).

Catatan strategi: revisi ini soal **prioritas dan kehati-hatian cleanup**, bukan perubahan strategi besar. Staging **tetap dipertahankan sebagai quality gate terakhir** -- target adalah "Kirim ke Staging", **bukan** "commit langsung ke database".

---

## 1.1 Status Implementasi (sinkron dengan kode, per 2026-06-02)

| Item | Status | Bukti / catatan |
|---|---|---|
| Bug A -- nama AHSP suffix | **SELESAI** | regex suffix-aware di `import_validate_report.html`; test guard `tests_import_multi_source_regressions` |
| Bug B -- resolusi multi-sumber | **SELESAI** | `detail_project/services.py::_resolve_ahsp_by_code_in_source` (by `(kode_ahsp, sumber)`); fallback read-only hanya resolve bila `count()==1`; `source_badge()` pakai `sumber` |
| **R1 -- AHSP Interchange v1** | **SELESAI** | service `referensi/services/import_schema.py` (`dump_workbook`/`load_workbook_rows`/`is_interchange_workbook`, `SCHEMA_VERSION=ahsp-interchange-1.0`, sheet `Data`+`Meta`). `export_from_frontend` menulis interchange; `excel_clean_upload` mendeteksi & membaca interchange (`_stage_rincian_from_interchange`) dengan **fallback** ke format lama -> round-trip aman & backward-compatible. Tests: `test_import_schema`, `test_import_repair`. |
| R4 -- tanam `sumber` di file | **SEBAGIAN** | `Meta!sumber` ditulis saat export & dibaca saat import; deklarasi manual masih sebagai fallback untuk file non-interchange |
| R6 -- service standar wajib | **SEBAGIAN** | `ahsp_code`/`import_repair` dipakai lintas-jalur web + interchange; jalur CLI `ahsp_parser` belum diselaraskan |
| R2 -- "Kirim ke Staging" langsung | **BELUM** | belum ada endpoint `validate/stage/`; masih download->upload |
| R3 -- model `AHSPImportBatch` + lifecycle | **BELUM** | belum ada model batch; `AHSPImportStaging` masih global per-user (Temuan D belum tertutup) |
| R7 -- satukan endpoint export | **BELUM** | `export_valid_excel`/`export_anomaly_excel` masih format lama ("Daftar Isi"/"Data Valid") & ter-route |
| R8 -- pipeline async konversi+validasi | **BELUM** | belum ada; blocker B1/B2/B3 di Bagian 10 wajib dihormati |
| R5 -- arsip orphan web | **BELUM** | belum dibersihkan |

> Ringkas: **fondasi sudah berdiri** (R1 + dua bug korektnes). Sisa adalah perampingan alur operator (R2/R3/R8) dan kebersihan (R5/R7). Bagian-bagian di bawah yang membahas R1/format lama dipertahankan sebagai **konteks historis**; status terkini ada di tabel ini.

---

## 2. Peta Alur Saat Ini (yang aktif)

Rute aktif (lihat `referensi/urls.py`, blok "3-Tier Import System"):

```
OPSI 1  PDF  --> _process_pdf_pages --> Excel (sheet "Data" + "Summary")
        (mode: import / validation / source / validation_hybrid)        |  download manual
                                                                         v
OPSI 2  upload Excel --> excel_validate_report / _get_validation_results
        --> laporan interaktif (Edit Mode, repair_preflight)
        --> "Download Data Valid" (export_from_frontend, WYSIWYG)
            = AHSP Interchange v1: sheet "Data" + "Meta"  [R1 SELESAI]   |  download manual
                                                                         v
OPSI 3  upload file --> excel_clean_upload
        --> is_interchange_workbook? ya: _stage_rincian_from_interchange (by-nama, sumber dari Meta)
                                    tidak: fallback format lama / flat
        --> AHSPImportStaging --> staging_view --> (deklarasi/auto Sumber)
        --> staging_commit --> AHSPReferensi + RincianReferensi
```

Happy-path **masih** menuntut ~3 siklus upload/download (R2/R8 belum), tetapi **kontrak file antar-tahap kini terstandar & tervalidasi versi** (R1 selesai), sehingga kelas bug sheet/kolom/posisi sudah hilang dari sambungan ini. Yang tersisa adalah memangkas hop manual (R2/R8).

### Komponen single-source-of-truth (sudah dibangun sesi ini -- pertahankan)
- `referensi/services/ahsp_code.py` -- parsing/klasifikasi/normalisasi kode AHSP (termasuk suffix `2.2.1.1.5.a`).
- `referensi/services/import_repair.py` -- `compute_block_status`, `validate_frontend_payload`, deteksi wrapped row, blocker vs warning pasif.

---

## 3. Temuan

### A. Round-trip Excel = sumber kerapuhan utama (Impact: tinggi)
Tiap sambungan antar-opsi menulis lalu membaca ulang Excel dengan kontrak yang tidak eksplisit:
- Opsi 2->3 menulis **2 sheet** ("Daftar Isi" lebih dulu) + baris header + kolom "No"; `excel_clean_upload` dulu membaca sheet pertama secara posisional -> semua bug "Tidak ada data valid" & `kode_item` tertukar berasal dari sini.
- Tidak ada penanda versi/format pada file, sehingga importer harus menebak struktur.

**Inti:** kontrak berbasis posisi + serialisasi berulang = titik patah berlipat.

### B. Alur web orphan vs jalur CLI/Task yang masih aktif (Impact: tinggi; perlu hati-hati)
Ada pipeline parsing terstruktur paralel. **Penting: tidak semuanya mati.** Klasifikasi yang benar:

**Orphan murni (web tidak ter-route -- aman diarsipkan lebih dulu):**
- `referensi/views/preview.py` (`preview_import`, `commit_import`) -- tidak ada di `urls.py` (hanya `debug_clear_data` yang dipakai).
- `referensi/templates/referensi/preview_import.html`.
- `referensi/services/preview_service.py`.
- `referensi/views/import_pdf.py` (punya `staging_commit` versinya sendiri, tidak ter-route).

**Tidak ter-route saat ini, tetapi JANGAN dihapus -- kandidat refactor untuk R8 (async):**
- `referensi/views/api/import_progress.py`, `referensi/services/chunked_import.py`, `referensi/tasks.py` (pola async/progress), `referensi/templates/referensi/import_upload.html`. Lihat R8: dipakai sebagai **referensi pola**, bukan implementasi final.

**MASIH AKTIF (JANGAN hapus):**
- `referensi/services/ahsp_parser.py` dan `referensi/services/import_writer.py` dipakai oleh:
  - `referensi/management/commands/import_ahsp.py` (baris 5-6, 62) -- jalur CLI.
  - `referensi/tasks.py` (baris 47-48, 82) -- jalur Celery task.

**Rekomendasi:** pisahkan tegas "orphan web flow" vs "jalur CLI/Task aktif". Arsipkan dulu view/template yang tidak ter-route; lalu **audit tiap service satu per satu** sebelum dihapus. Jangan generalisasi "hapus subsistem mati".

### C. Format tidak terstandar & berbasis posisi (Impact: tinggi)
Minimal 3 "bentuk" Excel berbeda untuk data yang sama:
1. Output PDF->Excel: `[judul baris-sel-tunggal]` + `[parent, segmen, no, uraian, kode, satuan, koef]` + kolom Status.
2. Export "Data Valid": sheet "Daftar Isi" + "Data Valid" (`Kode Induk, Segment, No, Uraian, Kode Referensi, Satuan, Koefisien`).
3. Format yang diharapkan parser legacy `excel_clean_upload`: flat `[parent, segmen(A/B/C), kode_item, uraian, ...]`.
Ketiganya tidak saling kompatibel tanpa adapter khusus.

### D. Staging global per-user -> risiko integritas data (Impact: tinggi)
`staging_commit` memproses **semua** staging milik user (tidak per-file/batch). Jika user meng-upload dua file sebelum commit, datanya **tercampur** dan satu `sumber` diterapkan ke semuanya. Ini bukan sekadar kerapian -- ini risiko data masuk database dengan sumber yang salah. (Reviewer benar: ini layak prioritas tinggi, bukan rendah.)

### E. Metadata `sumber` (versi/tahun) tidak terbawa (Impact: sedang)
Tidak ada format yang menyimpan `sumber`. Sesi ini menambah deklarasi manual (field staging + input form). Selama belum tertanam di file, user mengetik ulang tiap commit dan keunikan AHSP per `(sumber, kode_ahsp)` rawan salah-deklarasi.

### F. Duplikasi logika (Impact: sedang -- sebagian sudah beres)
Deteksi wrapped/segmen & regex kode dulu tersebar di `_process_pdf_pages` dan `_get_validation_results`. Sudah disatukan ke `ahsp_code.py` + `import_repair.py`. Sisa: jalur CLI/Task (`ahsp_parser`) punya logika parsing sendiri -- perlu diselaraskan agar memakai service standar yang sama.

### G. Endpoint export ganda (Impact: rendah)
`export_valid_excel`/`export_anomaly_excel` (berbasis session temp file) ter-route tetapi **tombol UI memakai `export_from_frontend`** (WYSIWYG). Yang pertama efektif legacy dan punya bug pemetaan segmen lama.

---

## 4. Rekomendasi & Standarisasi

### R1 -- Kontrak kanonik "AHSP Interchange v1" [SELESAI]
> **Terimplementasi** di `referensi/services/import_schema.py` (`dump_workbook`, `load_workbook_rows`, `is_interchange_workbook`, `SCHEMA_VERSION="ahsp-interchange-1.0"`). `export_from_frontend` menulis interchange; `excel_clean_upload` mendeteksi & membaca interchange dengan fallback ke format lama. Spesifikasi di bawah dipertahankan sebagai acuan kontrak.

Tetapkan **satu** format untuk Excel apa pun yang melintas batas modul. R1 adalah **prasyarat** R2.

| Aturan | Detail |
|---|---|
| Sheet data | **Satu** sheet bernama `Data` (boleh ada sheet `Meta` opsional) |
| Header | Baris pertama = nama kolom, **wajib**; parsing **by-nama**, bukan posisi |
| Kolom wajib | `kode_ahsp`, `segmen` (A/B/C), `kode_item`, `uraian`, `satuan`, `koefisien` |
| Kolom judul | `nama_ahsp` |
| Metadata | `sumber` di **`Meta!sumber` (batch-level, BUKAN per-row)**; `schema_version: ahsp-interchange-1.0` |
| Segmen | Selalu kode dokumen `A/B/C` (peta TK->A dst. dilakukan eksportir) |
| Kode | Selalu dinormalisasi via `normalize_ahsp_code` di kedua sisi |

Importer mendeteksi `schema_version`; cocok -> parser kanonik by-nama; tidak cocok -> tolak dengan pesan jelas (bukan menebak).

**Wujudkan sebagai service, bukan sekadar aturan dokumen.** R1 harus jadi modul tunggal `referensi/services/import_schema.py` yang mengekspos kontrak (mis. `dump_workbook(rows, meta)`, `load_workbook(file) -> (rows, meta)`, `SCHEMA_VERSION`). **Parser, exporter, dan direct-staging WAJIB memakai service ini** -- tujuannya menghindari jebakan "format kanonik di dokumen tapi implementasi tetap tersebar". Jika tidak dipusatkan ke satu service, kerapuhan posisi/format akan muncul lagi.

**`sumber` diputuskan per-batch, bukan per-row.** Pakai `Meta!sumber` / metadata batch. Kolom `sumber` per-row dihindari karena berisiko satu file berisi sumber campuran tanpa sengaja.

**Lingkup R1 = file Excel saja.** Kontrak ini berlaku untuk **file Excel** (export opsional, import file eksternal). Data **internal** antar-tahap (job async -> report -> draft staging di R8) **tidak** harus melewati workbook; ia memakai kontrak payload internal sendiri (`ValidationBatchPayload`, lihat R8). Tujuannya agar data internal tidak dipaksa serialisasi ke Excel.

### R2 -- Tombol "Kirim ke Staging" dari validation report (setelah R1)
Tambah aksi di halaman validasi yang mengirim payload WYSIWYG/preflight yang sama ke endpoint baru (mis. `validate/stage/`) yang menulis langsung ke `AHSPImportStaging` lewat `validate_frontend_payload`.
- Alur happy-path: **PDF -> validasi/edit/repair -> Kirim ke Staging -> Review Staging -> Commit DB**.
- **Staging tetap quality gate terakhir** -- ini "Kirim ke Staging", bukan "commit langsung ke DB".
- Download Excel **tetap ada sebagai opsi arsip/koreksi manual**, bukan jalur wajib.
- Bonus: kelas bug sheet/kolom (Temuan A & C) hilang dari happy-path.

**Kontrak idempotency (wajib).** Endpoint baru harus membawa `import_batch_id` dan berperilaku jelas saat klik ganda / reload / kirim ulang payload sama: **REPLACE draft batch yang sama**, bukan append diam-diam (agar tidak menumpuk duplikasi). Batch baru dibuat hanya jika `import_batch_id` baru. Tegaskan: `import_batch_id` di-generate saat staging dari validation/upload (lihat R3).

### R3 -- Model `AHSPImportBatch` + pemisahan data lifecycle (prioritas tinggi -- integritas data)
**Jangan** sekadar menambah field `import_batch_id` di tiap row staging -- metadata batch akan tersebar dan status job/idempotency sulit dijaga. Buat **model batch tersendiri** dan **pisahkan dua lapis data** (lihat §8):

- **`AHSPImportBatch`** -- satu baris per impor: menyimpan `sumber`, `file_name`, `status` (uploaded/processing/validation_ready/staged/committed/failed), `celery_task_id`, `schema_version`, `counts/summary`, `created_by`, timestamp. Ini sumber kebenaran status & idempotency.
- **`AHSPImportStaging`** -- punya FK `import_batch`; **HANYA berisi data yang sudah lolos validasi dan siap review/commit**. Hasil validasi yang masih warning/blocked/perlu repair **TIDAK** ditulis ke sini -- ia hidup di payload/report batch (`ValidationBatchPayload`, R8), bukan di staging.

`staging_view`/`staging_commit` beroperasi **per-batch** dengan `sumber` per-batch. Mencegah pencampuran lintas-file (Temuan D) **dan** mencegah staging berubah jadi campuran valid+warning+blocked (masalah lama dalam bentuk baru).

### R4 -- Tanam `sumber` (batch-level) di file (prioritas sedang)
Eksportir menulis `sumber` di **metadata batch (`Meta!sumber`)**, bukan kolom per-row; importer membacanya; **hanya** meminta input manual bila absen. Menghilangkan ketik-ulang & salah-deklarasi, sekaligus mencegah sumber campuran dalam satu file.

### R5 -- Pisahkan: ARSIP (orphan murni) vs HIDUPKAN (aset async)
Penting -- jangan samaratakan jadi "hapus":
- **Arsipkan** (orphan web murni, setelah audit import-chain + test): `preview_import`/`commit_import` (view), `preview_import.html`, `preview_service`, `import_pdf.py`.
- **REFACTOR jadi backbone async (lihat R8) -- aset awal, BUKAN siap pakai:** `tasks.py` (Celery), `views/api/import_progress.py` (belum ter-route), `services/chunked_import.py`, `import_upload.html` (mengacu route lama). Pola async + chunk-nya berharga sebagai **referensi teknis**, tetapi implementasinya harus ditulis ulang agar lewat staging/validation gate + service standar (jangan tulis langsung ke DB seperti task lama).
- **Pertahankan** `ahsp_parser` + `import_writer` (dipakai CLI `import_ahsp` & `tasks.py`). Selaraskan agar memakai service standar (R1/R6).
- **Cleanup adalah langkah TERAKHIR**, bukan pertama.

### R8 -- Pipeline async "Konversi+Validasi" jadi satu (gabung Langkah 1+2 -- TANPA blocker)
Lever beban-operator terbesar. **WAJIB async, BUKAN fusi sinkron** (lihat Batasan di Bagian 10). Lifecycle data dipisah tegas (lihat R3/§8):

1. Operator upload PDF + pilih `sumber` **sekali** -> buat `AHSPImportBatch` (status `uploaded`), enqueue Celery.
2. **Background job** (status `processing`): konversi PDF (chunk per 50-halaman di dalam job) -> validasi (pakai `import_repair`) -> simpan hasil ke **`ValidationBatchPayload`/report batch** (status `validation_ready`). **Bukan ke staging.** Hasil ini boleh mengandung warning/blocked/repair-candidate. Tidak ada kerja berat di request HTTP.
3. Operator melihat **progress**, lalu **mendarat di report validasi** (paginasi) -- review/edit/repair. Tanpa download/upload Excel manual.
4. **Kirim ke Staging** (R2): hanya **baris yang lolos** (`not is_blocked`) ditulis ke `AHSPImportStaging` ber-FK `import_batch` (status `staged`). Baris blocked tetap di report batch, **tidak** masuk staging.
5. **Review Staging -> Commit DB** (status `committed`).

- Excel tetap dihasilkan job sebagai **opsi arsip/koreksi**, bukan transport wajib.
- Hasil: menghapus 4-5 hop file menjadi 1 upload, **sambil menghormati** blocker timeout/beban (async + ter-chunk) **dan** menjaga staging tetap bersih (hanya data siap-commit).

**PENTING -- R8 adalah BUILD/REFACTOR, bukan "hidupkan apa adanya".** Komponen async yang ada **belum siap pakai langsung**:
- `tasks.py::async_import_ahsp` saat ini memakai `ahsp_parser` + `import_writer` dan **menulis LANGSUNG ke database** (mem-bypass staging/validation gate). **Tidak boleh** dipakai untuk jalur baru -- jalur baru wajib lewat draft staging + `compute_block_status`/`validate_frontend_payload`.
- `process_ahsp_pdf_task` memakai parsing PDF sederhana (mis. pseudo `PDF.page.table`, batas 50 halaman) yang **tidak setara** dengan pipeline validasi sekarang (hierarchy, suffix huruf, blocker, repair, WYSIWYG). Anggap task lama sebagai **referensi teknis (pola async + chunk), bukan implementasi final**.
- `import_progress.py` **belum ter-route** di `urls.py` -- R8 harus menambah URL endpoint progress, UI polling, dan status job Celery yang jelas.
- `import_upload.html` mengacu route lama yang tidak aktif (mis. `referensi:import_pdf_verification`) -- perlakukan sebagai **bahan UI lama yang bisa diadaptasi**, bukan siap pakai.
- Komponen async lama (`tasks.py`, `chunked_import.py`, `import_progress.py`, `import_upload.html`) perlu **direfactor agar memakai** `ahsp_code.py`, `import_repair.py`, `import_schema.py`, dan `import_batch_id` (R3).

**Kontrak payload internal != Excel Interchange (R1).** Jalur async R8 **tidak harus** mem-passing data lewat workbook Excel. Definisikan kontrak payload internal sendiri -- mis. `ValidationBatchPayload` (struktur in-memory/JSON: rows ter-normalisasi + meta batch) -- yang dipakai job -> report -> draft staging. R1 (Excel Interchange) tetap **wajib hanya untuk file Excel** (export opsional, import file eksternal). Jangan paksa seluruh data internal melewati Excel.

### R6 -- Service single-source-of-truth sebagai standar wajib (prioritas sedang)
Semua jalur (konversi, validasi, staging, commit, CLI, task) **wajib** memakai `ahsp_code.py` + `import_repair.py`. Larang regex/aturan kode AHSP lokal baru. Tambah test guard.

### R7 -- Satukan endpoint export (prioritas rendah)
Pensiunkan `export_valid_excel`/`export_anomaly_excel`; jadikan `export_from_frontend` (memakai skema R1) satu-satunya. Hapus bug pemetaan segmen lama.

---

## 5. Roadmap yang Direkomendasikan (urutan eksekusi)

**Prioritas inti: R1 -> R3 -> (R8+R2), lalu cleanup.** JANGAN mulai dari menghapus kode legacy. **Prinsip non-negotiable: kerja berat (parse PDF, validasi tabel besar) WAJIB async**, tidak pernah sinkron dalam satu request (lihat Bagian 10).

1. ~~Bersihkan encoding dokumen + revisi "subsistem mati"~~ (SELESAI, v2-v4).
2. ~~**AHSP Interchange v1** (R1) sebagai service `import_schema.py`~~ **(SELESAI)** -- export+import sudah memakai kontrak; round-trip aman.
3. **Model `AHSPImportBatch` + lifecycle** (R3) -- **FOKUS BERIKUTNYA.** Agar commit tidak mencampur file & staging tidak jadi campuran valid/warning/blocked. Risiko integritas, dahulukan.
4. **Pipeline async Konversi+Validasi** (R8) -- **refactor/bangun pipeline async baru dengan mengambil pola dari `tasks.py`/`import_progress`** (bukan menghidupkan apa adanya); upload PDF -> job background -> `ValidationBatchPayload`/report, tanpa hop file manual. Inti optimasi beban operator, **tanpa** menghidupkan blocker timeout/beban.
5. **"Kirim ke Staging" + commit in-app** (R2) -- continuity dalam aplikasi + idempotency (replace draft batch). Hanya baris lolos yang masuk staging. Sebagian sudah terpenuhi oleh R8.
6. **Download Excel jadi opsi arsip/koreksi manual** -- bukan jalur wajib (mengikuti R1).
7. **Pensiunkan/arsipkan legacy** yang benar-benar orphan (R5: preview flow, R7 export ganda), **setelah audit import-chain + test**. Langkah terakhir. (Komponen async di R5 di-HIDUPKAN, bukan dihapus.)

Pemeliharaan berkelanjutan: R4 (tanam sumber batch-level), R6 (standar service).

---

## 6. Apakah ini jalan terbaik?

**Sebagian ya, sebagian tidak.**
- **Pertahankan:** empat-langkah logis **Validasi/Edit/Repair -> Kirim ke Staging -> Review Staging -> Commit DB**. Checkpoint manusia + staging sebagai gate terakhir itu berharga karena DB referensi dipakai banyak proyek; menghapusnya berbahaya.
- **Ubah:** jangan jadikan Excel sebagai *bus data wajib* antar tahap. Excel bagus sebagai **artefak opsional** (koreksi manual/arsip), bukan satu-satunya jembatan yang memaksa download->upload dan kontrak posisi.

Dengan R1 (kontrak) + R3 (batch) + R2 (kirim ke staging), alur tetap punya tahapan yang sama tetapi:
- happy-path menjadi **satu kali upload di awal** lalu **lanjut di dalam aplikasi** hingga commit,
- format yang dipertukarkan **terstandar & tervalidasi versi**,
- integritas terjaga (tidak mencampur file),
- permukaan kode menyusut (arsip orphan), tanpa merusak jalur CLI/Task.

Kesimpulan: arah workflow sudah benar. Revisi utamanya adalah **prioritas (batch naik, R1 fondasi) dan kehati-hatian cleanup (jangan hapus service CLI/Task)** -- bukan perubahan strategi besar.

---

## 7. Acceptance Criteria (untuk implementasi)

- Direct staging **tidak boleh** memasukkan tabel `blocked`/anomali (lewat `compute_block_status`/`validate_frontend_payload`).
- Satu batch import hanya boleh commit data **dari batch itu** (tidak mencampur file lain milik user).
- Klik ulang / reload "Kirim ke Staging" **tidak membuat duplikasi** (replace draft batch yang sama).
- Export Excel opsional **harus mengikuti** kontrak AHSP Interchange v1 (`import_schema.py`).
- Jalur CLI/Task (`import_ahsp`, `tasks.py`) **tetap berjalan** -- atau, jika diputuskan ditinggalkan, dinyatakan **legacy secara eksplisit** (bukan dibiarkan menggantung).

### Acceptance Criteria khusus R8 (pipeline async)
- Job async menghasilkan **validation report / draft batch**, **bukan** langsung commit ke DB.
- Endpoint progress **ter-route** (ditambahkan ke `urls.py`) dan **diuji**; status job Celery jelas (queued/progress/done/error).
- Job memakai `compute_block_status` / `validate_frontend_payload` (bukan parser/penulisan langsung lama).
- PDF besar diproses **chunked** (mempertahankan batas 50-halaman) **tanpa pseudo AHSP code**; pakai pipeline parsing yang setara dengan jalur web (hierarchy, suffix, blocker, repair).
- Task lama (`async_import_ahsp`/`process_ahsp_pdf_task`) tetap berjalan untuk jalur CLI/legacy **atau** dinyatakan `deprecated` secara eksplisit -- tidak dipakai diam-diam untuk jalur baru.
- **Baris `blocked` TIDAK ditulis ke `AHSPImportStaging`** (commit-ready). Metadata blocker/warning/repair-candidate boleh disimpan di `AHSPImportBatch`/report, tetapi staging hanya menerima baris yang lolos. Acceptance: tidak ada satu pun row staging dengan status blocked.

## 8. Keputusan Desain Eksplisit

- **`schema_version`:** `ahsp-interchange-1.0`.
- **Metadata `sumber`:** **batch-level** (`Meta!sumber`), bukan kolom per-row sebagai default.
- **`import_batch_id`:** UUID, dibuat saat staging dari validation/upload.
- **Perilaku staging:** **replace draft batch yang sama**, bukan append diam-diam.
- **Pemrosesan berat WAJIB async:** parse PDF + validasi tabel dijalankan via Celery (`tasks.py`), bukan inline di request. Request web hanya enqueue + poll progress.
- **Chunking dipertahankan:** batas 50-halaman/part tetap dipakai **di dalam job async** untuk PDF besar; report validasi **paginasi** untuk baris besar; tulis staging via `bulk_create`.
- **Payload internal terpisah dari Excel:** data antar-tahap async memakai `ValidationBatchPayload` (in-memory/JSON), bukan workbook. Excel Interchange (R1) hanya untuk file eksternal/opsional.
- **Task lama bukan fondasi langsung:** `async_import_ahsp` (tulis langsung ke DB) **tidak** dipakai untuk jalur baru; ia legacy/CLI. Jalur baru wajib lewat draft staging + validation gate. Pola chunk/async task lama = referensi teknis saja.

### 8.1 Pemisahan data lifecycle (KEPUTUSAN INTI)
Dua lapis terpisah -- jangan dicampur:

**`AHSPImportBatch`** (satu baris per impor; sumber kebenaran status & idempotency):
```
id / uuid
user (created_by)
sumber
file_name
status        : uploaded | processing | validation_ready | staged | committed | failed
celery_task_id
schema_version
counts / summary   (mis. valid/warning/blocked, jumlah tabel & rincian)
error_summary
created_at / updated_at
```

**`AHSPImportStaging`** (data siap review/commit saja):
```
import_batch        : FK -> AHSPImportBatch
... (field rincian existing) ...
# HANYA baris yang lolos validasi (not is_blocked). Tidak ada warning/blocked di sini.
```

**Batas tegas:** hasil validasi yang masih bisa bermasalah (warning/blocked/repair-candidate) hidup di **`ValidationBatchPayload`/report batch** (in-memory/JSON, terikat ke `AHSPImportBatch`), **bukan** di `AHSPImportStaging`. Staging adalah "sudah lolos, tinggal review akhir + commit". Ini mencegah staging berubah jadi tempat campuran data valid+warning+blocked -- yaitu masalah lama yang muncul kembali dalam bentuk baru.

---

## 9. Workflow Operator: Saat Ini vs Usulan

### 9.1 Workflow SAAT INI (dan kenapa berbentuk begini)
Operator berperan sebagai "kurir file" antar tiga tahap, dengan Excel sebagai transport wajib:

| # | Aksi operator | Hop file | Beban berat |
|---|---|---|---|
| 1 | Opsi 1: upload PDF + **pilih mode**, submit | upload PDF | konversi PDF (sinkron) |
| 2 | **Download** Excel hasil (PDF besar -> pecah per 50 hal / ZIP) | turun | -- |
| 3 | Opsi 2: **upload** Excel itu | naik | validasi seluruh baris (sinkron) |
| 4 | Review/Edit/Repair, **Download "Data Valid"** | turun | -- |
| 5 | Opsi 3: **upload** "Data Valid" | naik | parse ulang (sinkron) |
| 6 | Staging: deklarasi `sumber`, **Commit** | -- | tulis DB |

≈ **6 navigasi + 5 hop file.** **Alasan desain ini ada:** kerja berat dipecah & di-"parkir" ke file supaya tidak ada satu request yang memproses semuanya sekaligus -- inilah mitigasi blocker timeout/beban (BATCH_SIZE=50, ZIP-all). Jadi alur panjang ini **bukan tanpa sebab**; ia menukar kenyamanan demi menghindari timeout.

### 9.2 Workflow USULAN (async, menghormati blocker yang sama)
Mitigasi yang sama (jangan proses berat dalam satu request) dicapai lewat **async**, bukan lewat memaksa operator memindah file:

| # | Aksi operator | Hop file | Beban berat |
|---|---|---|---|
| 1 | Upload PDF + pilih `sumber` (sekali) | upload PDF | -- (hanya enqueue) |
| 2 | Lihat **progress bar** (job background) | -- | konversi+validasi **di worker, ter-chunk** |
| 3 | Mendarat di **report validasi** (paginasi), Review/Edit/Repair | -- | -- |
| 4 | **Kirim ke Staging** (draft batch) -> Review -> **Commit** | -- | tulis DB (bulk) |

≈ **1 upload, 0 hop file perantara.** Download Excel tetap tersedia sebagai **opsi**.

### 9.3 Perbandingan ringkas
| Aspek | Saat ini | Usulan (async) |
|---|---|---|
| Navigasi | ~6 | ~3-4 |
| Hop file manual | 5 | 1 (upload PDF) |
| Risiko salah-file/sheet | tinggi | hilang (tanpa hop) |
| Blocker timeout/beban | dihindari via pecah-file manual | dihindari via **async + chunk** (lihat Bagian 10) |
| Koreksi manual di Excel | wajib lewati file | opsi (escape hatch) |
| Gate kualitas (staging) | tetap ada | tetap ada |

**Inti:** usulan **tidak menghapus** mitigasi blocker -- ia **memindahkannya** dari "operator memecah file" ke "sistem memproses async + ter-chunk". Beban operator turun tanpa mengembalikan timeout.

## 10. Batasan & Blocker yang WAJIB Dihormati (jangan diregresi)

Dikonfirmasi sebagai blocker yang pernah dihadapi & dieliminasi. Setiap implementasi optimasi **harus** lulus ini:

- **B1 -- Timeout konversi PDF besar.** Jangan pernah konversi PDF besar dalam satu request sinkron. Wajib: job async + chunk 50-halaman (pertahankan mekanisme `BATCH_SIZE`). *Acceptance:* PDF besar tidak pernah memicu 504/hang di request web.
- **B2 -- Beban server saat banyak file / bersamaan.** Konversi/validasi di worker (Celery), terbatas concurrency; request web hanya enqueue + poll. *Acceptance:* N file bersamaan tidak memblok web worker.
- **B3 -- Timeout karena baris/tabel terlalu besar.** Validasi & penulisan staging diproses **bertahap/chunk** (mis. iterasi per-batch, `bulk_create`), report **paginasi** (jangan render semua baris sekaligus). *Acceptance:* file dengan ribuan baris selesai tanpa timeout dan UI tetap responsif.

> Konsekuensi desain: **R8 (gabung Konversi+Validasi) WAJIB async.** Versi sinkron dari R8 DITOLAK secara eksplisit karena meregresi B1/B2/B3. Inilah jawaban atas kekhawatiran reviewer: optimasi ini aman **hanya** dalam bentuk async + chunk; bukan sebagai fusi satu-request.

---

## Lampiran: Referensi Kode
- Rute aktif: `referensi/urls.py` (blok "3-Tier Import System").
- Konversi PDF: `referensi/views/import_views.py::_process_pdf_pages`.
- Validasi: `..::_get_validation_results`, `..::excel_validate_report`, `repair_preflight`.
- Export WYSIWYG: `..::export_from_frontend`.
- Clean import & staging: `..::excel_clean_upload`, `_stage_rincian_from_export`, `_stage_rincian_legacy_flat`, `staging_view`, `staging_commit`.
- Service standar: `referensi/services/ahsp_code.py`, `referensi/services/import_repair.py`.
- **AKTIF (CLI/Task) -- jangan hapus:** `referensi/services/ahsp_parser.py`, `referensi/services/import_writer.py` (dipakai `referensi/management/commands/import_ahsp.py`, `referensi/tasks.py`).
- **ASET ASYNC AWAL -- REFAKTOR untuk R8 (referensi teknis, BUKAN siap pakai):** `referensi/tasks.py` (`async_import_ahsp` tulis-langsung-DB; `process_ahsp_pdf_task` parsing sederhana), `referensi/views/api/import_progress.py` (belum ter-route), `referensi/services/chunked_import.py`, `referensi/templates/referensi/import_upload.html` (mengacu route lama `import_pdf_verification`).
- **Orphan web murni (kandidat ARSIP, audit dulu):** `referensi/views/preview.py` (`preview_import`/`commit_import`), `referensi/views/import_pdf.py`, `referensi/services/preview_service.py`, `referensi/templates/referensi/preview_import.html`.
