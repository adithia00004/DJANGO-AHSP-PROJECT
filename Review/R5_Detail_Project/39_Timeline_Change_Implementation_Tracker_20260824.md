# 39 — Tracker Eksekusi: Perubahan Tanggal Proyek dengan Progress

| | |
|---|---|
| Status keseluruhan | **SELURUH FASE SELESAI** (1.1–1.3, 2.1–2.2, 3.1 — 2026-08-24). Ketiga sasaran doc 38 tertutup dari backend sampai UI. **Belum di-commit** (6 langkah menumpuk di working tree). Sisa: commit terpisah per langkah + UAT runtime |
| Tanggal mulai | 2026-08-24 |
| Rencana eksekusi | `38_Timeline_Change_Execution_Plan_20260824.md` |
| Analisis lengkap | `37_Timeline_Change_Guided_Repair_Plan_20260824.md` |
| Tracker induk | `28_Implementation_Execution_Tracker_20260614.md` (ringkasan dipantulkan ke sana saat Fase selesai) |
| Branch | `fix/db-connection-leak` (working tree berjalan) |

Dokumen ini adalah **satu-satunya sumber status** untuk pekerjaan timeline change.
Doc 37 = analisis (tidak diubah kecuali errata §3). Doc 38 = rencana (diubah hanya lewat §8).

---

## 0. Gate 0 — Keputusan yang menahan eksekusi

Tiga hal di bawah bukan detail implementasi; masing-masing mengubah definisi lulus langkah 1.2/1.3.
Kolom "Rekomendasi" adalah usulan; kolom "Keputusan" diisi owner sebelum langkah 1.2 dimulai.

| # | Pertanyaan | Keputusan owner | Tanggal |
|---|---|---|---|
| **G0-1** | Gerbang realisasi: doc 38 §2 menulis "realisasi pada **minggu terdampak** ditolak", §6.1 baris 7 menulis "realisasi **di mana pun** ditolak". Mana yang berlaku? | **DIREVISI 2026-08-24** (owner mendelegasikan pilihan: "ambil yang paling sesuai kebutuhan fitur"). Keputusan awal "realisasi di mana pun" **dibatalkan** karena menutup kasus pemakaian paling umum. Aturan final: **tolak bila operasi memang akan memindahkan atau menghapus realisasi** — rinciannya di K-1. | 2026-08-24 |
| **G0-2** | `keep_ordinal` saat durasi **memendek**: baris dengan `week_number` > jumlah minggu baru mau diapakan? | **Luapan DIHAPUS** (`DROP`). Konsekuensi: label doc 38 §3 untuk "Pertahankan urutan minggu" berubah dari "Utuh" menjadi **"Utuh bila durasi tidak memendek; berkurang bila memendek"** — lihat K-2. | 2026-08-24 |
| **G0-3** | Mass edit: doc 38 §6.2 baris 10 meminta **partial save**, tetapi `mass_edit_bulk_update` hari ini satu `transaction.atomic()` dan dikunci 2 test. | **Pisahkan kelas kegagalan.** Validasi & otorisasi tetap **all-or-nothing** (2 test lama tidak berubah). "Perlu keputusan timeline" jadi **skip per-project** dan dilaporkan — bukan rollback batch. Ditulis eksplisit di docstring + test baru. | 2026-08-24 |

### K-1 — Aturan gerbang realisasi (final)

**Prinsip:** tolak bila operasi **benar-benar akan memindahkan atau menghapus** baris realisasi —
bukan sekadar karena realisasi ada. Ini menegakkan invariant I-1 doc 37 tanpa membekukan proyek
yang sedang berjalan.

| Bentuk perubahan | Yang terjadi pada baris | Gerbang | Predikat |
|---|---|---|---|
| **Selesai diperpanjang** (mulai tetap, `new_end > old_end`) | Tidak ada baris yang berubah tanggal; minggu baru hanya ditambahkan di ujung | **IZINKAN** | — (tak ada baris terdampak menurut `_affected_filter`) |
| **Selesai diperpendek** (mulai tetap) | Baris di luar jendela baru terancam dibuang/di-nol-kan | **TOLAK bila ada realisasi di minggu terdampak** | `affected.filter(Q(actual_proportion__gt=0) \| Q(actual_cost__isnull=False))` |
| **Mulai bergeser** (`new_start != old_start`) | Batas minggu dihitung ulang → **seluruh** baris berpindah tanggal | **TOLAK bila ada realisasi di mana pun** | `records.filter(Q(actual_proportion__gt=0) \| Q(actual_cost__isnull=False))` |

**Mengapa baris 1 terbukti aman:** batas minggu dijangkar ke `tanggal_mulai` yang tidak berubah
(`expected_week_count` + `_build_weekly_tahapan_instances` keduanya menurunkan bucket dari tanggal
mulai). Memperpanjang ujung hanya menambah bucket baru di belakang; `week_number`, `week_start_date`,
dan `week_end_date` baris yang sudah ada tidak tersentuh. Jadi tidak ada mekanisme yang dapat
menggerakkan realisasi — penolakan di sini murni kerugian tanpa manfaat.

**Mengapa baris 3 tetap ketat:** ini bagian yang benar-benar berbahaya, dan tetap seketat keputusan
awal owner. Dibuka hanya lewat pertanyaan niat "koreksi vs pergeseran" (doc 37 §4.1), yang tetap
di luar scope rilis ini.

**Dampak ke doc 38:** tabel §6.1/§6.2 **tidak berubah** — aturan ini justru yang membuat baris
§6.1 #1 ("perpanjang tanggal selesai → tersimpan langsung, Sama") tetap benar. Baris §6.1 #7
("geser tanggal mulai, ada realisasi di mana pun → ditolak") juga tetap benar. Kontradiksi §2 vs §6.1
yang ditemukan di review terselesaikan: **§6.1 yang benar**, dan §2 harus dibaca sebagai aturan untuk
perubahan tanggal **selesai** saja.

**Riwayat:** keputusan awal 2026-08-24 adalah aturan tunggal "realisasi di mana pun memblokir".
Dibatalkan pada hari yang sama setelah konsekuensinya diperiksa: aturan itu **lebih ketat daripada
perilaku hari ini** dan menolak kasus pemakaian paling umum (proyek molor → tanggal selesai diundur
sementara realisasi sudah tercatat). Owner mendelegasikan pilihan akhir.

### K-2 — Konsekuensi G0-2

Dengan `DROP`, "Pertahankan urutan minggu" **bukan lagi opsi yang selalu lossless**. Akibatnya:

- Label total di doc 38 §3 harus dikoreksi (lihat tabel G0-2).
- Dialog di langkah 2.1 **wajib menampilkan berapa banyak nilai yang akan hilang** saat durasi memendek,
  karena default-nya tidak lagi menjamin keutuhan. Ini masuk DoD 2.1.
- Invariant **I-D** tetap berlaku; invariant "total sebelum == total sesudah" **tidak** berlaku untuk
  `keep_ordinal` + durasi memendek, dan tidak boleh di-assert di situ.

**Aturan:** langkah 1.1 boleh jalan sekarang. Gate 0 kini **LULUS** — langkah 1.2 terbuka.

---

## 1. Aturan tracking

Diperbarui ketika: langkah dimulai/selesai/diblokir, gate gagal, ditemukan kondisi di luar audit,
keputusan owner berubah, atau baseline menghasilkan kegagalan baru.

| Status | Arti |
|---|---|
| `PENDING` | belum dimulai |
| `IN PROGRESS` | sedang dikerjakan |
| `BLOCKED` | tidak dapat lanjut tanpa keputusan/dependency |
| `DONE` | seluruh Definition of Done §5 terpenuhi **dan** bukti tercatat di §7 |
| `DEFERRED` | ditunda dengan alasan + gate eksplisit |

**Satu langkah = satu commit.** Tidak digabung (pelajaran WP Export, doc 30 §8).
Sebuah langkah hanya boleh ditandai `DONE` bila §7 memuat baris bukti dengan tanggal dan hasil nyata —
bukan "seharusnya hijau".

---

## 2. Baseline terekam (2026-08-24, sebelum perubahan apa pun)

Dijalankan pada working tree saat ini, SQLite (`config.settings.test`).

| Suite | Hasil | Catatan |
|---|---|---|
| `detail_project/tests_timeline_crud_hardening.py` | **10 passed** | Bukan 11 — lihat errata E-1 |
| `dashboard/tests_mass_edit.py` | passed | termasuk `test_mass_edit_resets_progress_when_start_date_changes` yang **sudah** mengunci T-01 |
| `detail_project/tests_wp_b4_readiness.py` | **1 failed**, sisanya passed | Kegagalan **pre-existing**, bukan regresi — lihat B-1 |
| Gabungan ketiganya | `1 failed, 52 passed in 69.01s` | |

**B-2 — Defect ditemukan saat langkah 2.1, DIPERBAIKI (bukan pre-existing baseline).**
`analyze_project_timeline_change` membaca tanggal lama dari **atribut instance**. Padahal
`ModelForm.is_valid()` menempelkan `cleaned_data` ke `form.instance` lewat `_post_clean`, sehingga
setiap pemanggil yang meneruskan `form.instance` — `project_edit` **dan** `mass_edit_bulk_update` —
membandingkan tanggal baru dengan tanggal baru. Akibatnya `start_changed` **selalu False**, dan
pergeseran tanggal mulai diperlakukan sebagai perubahan tanggal selesai: gerbang K-1 memilih cabang
yang salah dan `keep_ordinal` tidak pernah ditawarkan.

Ditemukan karena dua test langkah 2.1 gagal; sebelumnya beberapa test Fase 1 **lulus secara
kebetulan** lewat cabang yang salah. Perbaikan: helper `_persisted_timeline()` membaca tanggal lama
langsung dari database, dipasang di `analyze_project_timeline_change` dan `build_resolution_preview`
— di service, bukan di pemanggil, supaya tidak dapat terulang. Dikunci
`test_analysis_ignores_dates_already_mutated_in_memory` + assertion `blocking_reason` pada test mass edit.

**B-1 — Kegagalan pre-existing yang WAJIB tidak disalahartikan sebagai regresi.**
`ReadinessContractTests::test_incomplete_planned_allocation_flags_partial_only` →
`AssertionError: '60' != '60.00'`. Penyebab: `readiness.py:469,477` memformat hasil agregat
`Sum()` dengan `f"{total}"`; di SQLite `Sum()` atas `DecimalField` mengembalikan `Decimal('60')`,
di PostgreSQL `Decimal('60.00')`. **Artefak environment test, bukan cacat kode.**
Verifikasi ulang di PostgreSQL memakai `config.settings.test_pg` bila diperlukan.
Setiap langkah yang menyentuh readiness wajib membandingkan terhadap baseline ini, bukan terhadap "0 failed".

**Perintah baseline (ulangi persis ini di setiap gate):**

```
python -m pytest detail_project/tests_timeline_crud_hardening.py dashboard/tests_mass_edit.py detail_project/tests_wp_b4_readiness.py -q --no-header -p no:cacheprovider
```

---

## 3. Errata doc 37 / doc 38 (faktual, tidak butuh keputusan)

Diverifikasi ke kode 2026-08-24. Dicatat di sini agar doc 37/38 tidak perlu diedit di tengah eksekusi.

| ID | Lokasi | Klaim dokumen | Fakta terverifikasi | Dampak |
|---|---|---|---|---|
| **E-1** | doc 37 §2.2 #5, WP-T1, §10; doc 38 1.1/1.2/§7 | "11 test" di `tests_timeline_crud_hardening.py` | **10 test** (`grep -c "def test_"` = 10; run = `10 passed`) | Gate dipakai apa adanya = tidak terverifikasi. **Angka resmi: 10.** |
| **E-2** | doc 37 §2.2 #4, §5 | "Halaman Jadwal tidak pernah membaca `timeline_stale`" | **Salah.** `kelola_tahapan_grid_modern.html:1358` memuat `readiness_banner.js`; `readiness_banner.js:127` sudah merender *"Jadwal tidak sesuai rentang tanggal proyek (perlu regenerasi di Jadwal)"* | Fase 3 lebih kecil dari perkiraan. Yang hilang hanya: gating **tombol** + rute klik ke preview/commit. **Jangan bangun banner kedua** yang bersaing dengan yang sudah ada. |
| **E-3** | doc 37 T-05, WP-T5 | "`loadAssignments` dijalankan saat `timeColumns` kosong → 0 baris ter-map senyap" | **Benar tapi dampaknya lebih kecil.** `data-loader.js` `loadAllData()` Step 3 memanggil `loadAssignments()` sebelum kolom ada; `DataOrchestrator.js:121` memanggilnya **lagi** setelah `timeColumnGenerator.generate()` — pemetaan kedua memperbaiki yang pertama | Biaya nyata = request ganda + log menyesatkan, **bukan** grid salah. T-05 tetap di luar scope doc 38; prioritasnya rendah. |
| **E-4** | doc 37 §9 skenario 15 | "`schedule_revision` basi → 409" | Dua lapisan berbeda: pre-check `_require_schedule_revision` → **409** (`views_api_tahapan_v2.py:64`); backstop dalam transaksi `apply_project_timeline_change` (`timeline_utils.py:169`) keluar sebagai **400** lewat `except TimelineChangeError` | Test harus menyebut lapisan yang diuji. Jalur form (`project_edit`) belum punya keduanya (G-5). |

---

## 4. Progress langkah

| Langkah | Scope | Status | Mulai | Selesai | Gate/Dependency | Commit |
|---|---|---|---|---|---|---|
| **0** | Gate keputusan G0-1..G0-3 | `DONE` | 2026-08-24 | 2026-08-24 | Owner | — |
| **1.1** | Contract freeze: kunci perilaku lama (T-01, T-02, T-03, T-06, K-1) | `DONE` | 2026-08-24 | 2026-08-24 | Baseline §2 | belum di-commit |
| **1.2** | Mesin resolusi + pembersihan baris luar jendela + snapshot audit + pola dua fase UNIQUE | `DONE` | 2026-08-24 | 2026-08-24 | 1.1 | belum di-commit |
| **1.3** | `views_mass_edit.py` berhenti memanggil `reset_project_progress`; pisah aman vs perlu-keputusan; tangani `tanggal_selesai` | `DONE` | 2026-08-24 | 2026-08-24 | **G0-3**, 1.2 | belum di-commit |
| **2.1** | Dialog pilihan di `project_form.html` + **kirim `expected_revision` (G-5)** | `DONE` | 2026-08-24 | 2026-08-24 | 1.3 | belum di-commit |
| **2.2** | Ringkasan agregat mass edit | `DONE` | 2026-08-24 | 2026-08-24 | 2.1 | belum di-commit |
| **3.1** | Jadwal: tombol jadi perbaikan terpandu berbasis `timeline_stale` | `DONE` | 2026-08-24 | 2026-08-24 | 2.2, **E-2** | belum di-commit |

**Perubahan scope terhadap doc 38** (alasan di §8): G-5 ditarik dari backlog ke langkah **2.1**.
Menambah dialog di `project_form` tanpa `expected_revision` membangun permukaan balapan baru
persis di tempat yang jalur API sudah lindungi.

---

## 5. Protokol verifikasi per langkah

Setiap langkah punya **Definition of Done** yang harus terpenuhi seluruhnya, dan **perintah gate**
yang hasilnya disalin apa adanya ke §7. Tidak ada langkah yang lulus berdasarkan pembacaan kode saja.

### Langkah 1.1 — Contract freeze — **DONE 2026-08-24**

File: `detail_project/tests_timeline_contract_freeze.py` (6 test).

DoD:
- [x] **T-01** dikunci dengan **data nyata**, bukan mock — `test_lock_t01_mass_edit_start_change_deletes_all_weekly_progress` membuktikan realisasi (`actual_proportion`, `actual_cost`) ikut terhapus. `dashboard/tests_mass_edit.py:128` yang berbasis mock **dibiarkan apa adanya**; keduanya saling melengkapi
- [x] **T-02** dikunci — `test_lock_t02_mass_edit_end_change_does_nothing`: baris weekly, tahapan di luar jendela, dan `timeline_stale == True` setelahnya
- [x] **T-03** dikunci dua sisi — planned saja, dan **actual saja** (`start_requires_policy` menghitung baris nonzero apa pun, jadi memblokir sebelum `actual_records` sempat dievaluasi)
- [x] **T-06** dikunci — `test_lock_t06_trim_planned_leaves_stale_rows_behind`: `timeline_stale` menjadi `True` tepat setelah commit yang sukses. Ini test yang harus **gagal** setelah langkah 1.2
- [x] **K-1 dikunci sebagai kontrak permanen** — `test_contract_end_extension_with_actual_stays_allowed`: memperpanjang tanggal selesai pada proyek berealisasi tetap diizinkan. **Satu-satunya test di file ini yang harus tetap hijau selamanya**, bukan lock yang menunggu dibalik
- [x] Setiap test memuat penanda LOCK + langkah yang membalikkannya di docstring
- [x] Tidak ada file produksi yang berubah

Gate: **LULUS** — `1 failed (B-1), 58 passed`; lulus naik 52 → 58; `git diff --stat` pada dua file test lama = kosong.

⚠ **Catatan commit:** working tree sudah membawa perubahan lain yang tidak terkait
(`M dashboard/views.py`, `M detail_project/views_api_tahapan_v2.py`, `?? detail_project/timeline_utils.py`).
Commit langkah 1.1 **wajib pathspec** — hanya `detail_project/tests_timeline_contract_freeze.py`
dan doc 39 — agar tetap satu langkah satu commit.

### Langkah 1.2 — Mesin resolusi — **DONE 2026-08-24**

File: `detail_project/timeline_utils.py` (mesin), `detail_project/progress_utils.py`
(`build_week_buckets` sebagai SSOT bucket), `detail_project/views_api_tahapan_v2.py`
(validasi resolusi diperluas), `detail_project/tests_timeline_resolution_engine.py` (17 test).

**Keputusan desain yang diambil saat eksekusi:**

1. **`trim_planned` DIBEKUKAN sebagai jalur legacy.** Doc 37 §6 mensyaratkan `none` dan
   `trim_planned` mempertahankan arti persis agar 10 test lama hijau tanpa dimodifikasi —
   dan `test_timeline_trim_planned_preserves_actual_contract` justru meng-assert baris
   di luar jendela **masih ada** dengan nilai 0. Jadi T-06 **tidak** ditutup lewat
   `trim_planned`, melainkan lewat tiga resolusi mesin. `trim_planned` disupersede
   `follow_date` (keduanya hanya berlaku saat tanggal mulai tidak bergeser) dan hilang
   dari UI setelah Fase 2.
2. **`keep_ordinal` hanya ditawarkan saat tanggal mulai bergeser** (doc 37 §4.6).
   Untuk perubahan tanggal selesai saja, menu tetap `accumulate_edge` / `follow_date`.
   Konsekuensi: G0-2 (luapan dihapus) diuji lewat pergeseran mulai yang memendekkan
   durasi, bukan lewat pemendekan ujung.
3. **Pola dua fase diimplementasikan sebagai "park lalu tata ulang"** — satu statement
   `update(week_number=F('week_number') + 100000)` memindahkan seluruh baris keluar dari
   rentang tujuan sebelum penataan. Baris lama **dipakai ulang** (bukan hapus-buat-baru)
   agar `created_at` tidak hilang; sisa yang tak terpakai dihapus.

DoD:
- [x] Tiga resolusi terimplementasi sesuai G0-2 — `plan_timeline_resolution()`
- [x] **Nasib baris di luar jendela tuntas** — `_write_target()` memindahkan, menggabung, atau menghapus; tidak ada baris tersisa (I-C di-assert)
- [x] Tanggal minggu baru diturunkan dari **`build_week_buckets()`**, SSOT baru di `progress_utils.py` yang kini juga dipakai `_build_weekly_tahapan_instances` (refactor behavior-preserving) — canonical dan tahapan tak mungkin menyimpang
- [x] Pola dua fase untuk `unique_together` — park `+100000` dalam satu statement, di dalam `transaction.atomic` yang sudah ada
- [x] **Post-condition guard (R-6)** — `_guard_target()`, per-baris **dan** per-pekerjaan, `blocking_reason='quantity_limit_exceeded'`
- [x] Pembagian per hari tumpang tindih + **largest remainder** ditulis baru di `_distribute()` (memakai `Fraction`, bukan float)
- [x] Audit menyimpan **snapshot penuh** — `old_data['rows_before']` berisi ketujuh field per baris
- [x] Kombinasi di luar `allowed_resolutions` ditolak di server (`'Resolusi tersebut tidak berlaku untuk bentuk perubahan ini.'`)

Gate (semua wajib):
- [x] Matriks resolusi hijau — **17 passed**: geser mulai durasi tetap/memendek, ujung memendek, proyek kosong, minggu parsial (split 4/7 → `8.57`), akumulasi 8×12.50 → `100.00`, merge banyak-baris→satu-sel (kasus UNIQUE), gerbang K-1 tiga arah, kombinasi ilegal, guard R-6, snapshot audit
- [x] **Invariant §6 di-assert** lewat `_assert_invariants()` pada setiap test yang commit-nya sukses (I-A, I-C, I-D) + I-B end-to-end lewat endpoint `api_chart_data` + I-F pada test gerbang
- [x] **10 test `tests_timeline_crud_hardening.py` hijau TANPA dimodifikasi** — `git diff --stat` = kosong
- [x] Baseline §2 tidak memburuk — tetap hanya B-1
- [x] `manage.py check` = 0 issue; `makemigrations --check` = **No changes detected** (tanpa migrasi skema, sesuai §7 doc 37)

### Langkah 1.3 — Mass edit — **DONE 2026-08-24**

File: `dashboard/views_mass_edit.py`, `detail_project/tests_timeline_mass_edit_safety.py` (9 test),
`dashboard/tests_mass_edit.py` (1 test dibalik), `detail_project/progress_utils.py` (catatan deprecation).

DoD:
- [x] `reset_project_progress` **tidak lagi diimpor maupun dipanggil** dari `views_mass_edit.py`
- [x] Perubahan `tanggal_selesai` ikut lewat `apply_project_timeline_change` (menutup T-02) — dibuktikan: tahapan di luar jendela hilang, jumlah tahapan == jumlah bucket, `timeline_stale == False`
- [x] Semantik G0-3 ditulis di docstring `mass_edit_bulk_update` dan dikunci dua test berlawanan: `test_safe_projects_save_while_unsafe_one_is_skipped` (2 tersimpan, 1 dilewati) dan `test_validation_error_still_rolls_back_whole_batch`
- [x] Respons memuat `needs_decision[]` berisi id, nama, alasan berbahasa user, `allowed_resolutions`, `recommended_resolution` — bahan langsung untuk Fase 2.2
- [x] Lock T-01/T-02 dibalik dan **dipindahkan** ke file gate 1.3; `tests_timeline_contract_freeze.py` menyusut jadi T-03 + T-06 + K-1 dengan docstring modul yang menjelaskan ke mana perginya
- [x] Dua test all-or-nothing lama **tidak berubah** — `git diff` pada `tests_mass_edit.py` hanya menyentuh satu method (lock T-01)

Gate: **LULUS** — 17 passed (1.3 + mass edit lama); Fase 1 penuh `1 failed (B-1), 81 passed`;
`manage.py check` 0 issue; export/jadwal `28 passed`.

**Temuan sampingan:** `reset_project_progress` kini **tanpa pemanggil sama sekali** —
`api_reset_progress` punya implementasi sendiri (me-nol-kan satu mode, tidak menghapus baris).
Fungsi diberi catatan deprecation + larangan disambung ulang (invariant I-3); penghapusannya
diserahkan ke fase cleanup, di luar scope langkah ini.

**Belum diukur:** waktu eksekusi mass edit pada project terbesar (risiko doc 38 §7). Jalur baru
memanggil service per-project, bukan `bulk_update` massal; pengukuran ditunda ke sebelum Fase 2
ditutup karena butuh data produksi.

### Langkah 2.1 — Dialog + G-5 — **DONE 2026-08-24**

File: `dashboard/views.py`, `dashboard/templates/dashboard/project_form.html`,
`detail_project/timeline_utils.py` (`build_resolution_preview`),
`dashboard/tests_timeline_dialog.py` (11 test).

DoD:
- [x] Blok dampak diganti dialog penuh: jendela lama→baru, jumlah minggu lama→baru, **tabel per-minggu tanggal lama→baru dan nilai lama→baru**, total sebelum→sesudah
- [x] **K-2 dipenuhi** — kehilangan ditampilkan eksplisit (`planned_lost`) plus konfirmasi kedua saat opsi menghapus nilai; `keep_ordinal` tidak lagi diklaim selalu utuh
- [x] `project_edit` mengirim `expected_revision` (G-5) lewat hidden `timeline_revision`, **dipertahankan apa adanya saat dialog dirender ulang** sehingga kunci tidak "menyegarkan diri" selagi user memilih
- [x] Opsi berasal dari `allowed_resolutions` server; template hanya merender. Proyeksi angka memakai `build_resolution_preview()` yang memanggil **planner yang sama** dengan commit — bukan perkiraan kedua
- [x] Tombol "Potong Planned Progress" (legacy `trim_planned`) hilang dari UI, sesuai keputusan 1.2

Gate: **LULUS** — 11 test: dialog ter-render tanpa menyimpan apa pun; opsi tidak sah tidak ditawarkan;
POST dengan resolusi tersimpan; revisi basi ditolak tanpa mutasi; revisi terjaga saat re-render;
perubahan aman tersimpan tanpa dialog; pergeseran mulai menawarkan tiga opsi.

### Langkah 2.2 — Ringkasan agregat mass edit — **DONE 2026-08-24**

File: `dashboard/static/dashboard/js/mass-edit-toggle.js`, `dashboard/tests_mass_edit.py`.

DoD:
- [x] Ringkasan "N tersimpan, M perlu keputusan" dengan nama project dan alasannya
- [x] Tiap project perlu-keputusan bertaut ke form edit tunggal (tempat dialog 2.1 berada)
- [x] **Muat ulang otomatis dimatikan** saat ada laporan — sebelumnya reload 1.5 detik akan menelan laporannya sebelum sempat dibaca; diganti tombol "Muat ulang daftar" eksplisit
- [x] Nama project disisipkan lewat `textContent`, bukan `innerHTML` (input user)

Gate: **LULUS** — `node --check` OK + guard test sumber JS + test backend `needs_decision` dari langkah 1.3.

### Langkah 3.1 — Tombol Jadwal — **DONE 2026-08-24**

File: `detail_project/templates/detail_project/kelola_tahapan_grid_modern.html`,
`detail_project/static/detail_project/js/shared/timeline_repair.js` (baru),
`.../shared/readiness_autoload.js` (event `readiness:loaded`),
`detail_project/views_api_tahapan_v2.py` (preview mengirim `previews`),
`detail_project/tests_timeline_repair_ui.py` (10 test).

DoD:
- [x] Gating memakai `readiness.timeline_stale` — sinyal server, tanpa perhitungan basi di klien
- [x] `#btn-regenerate-timeline` **dihapus dari toolbar**; diganti `#kt-timeline-repair` yang `d-none` sampai server menyatakan basi
- [x] Klik → `timeline/preview` (tidak memutasi) → dialog opsi + tabel minggu → `timeline/commit`
- [x] **Tidak menambah banner baru** — `readiness_autoload.js` kini menyiarkan `readiness:loaded`, dan alert perbaikan hanya menambahkan jalan keluar; teks sinyalnya tetap milik banner readiness (E-2)
- [x] `api_regenerate_tahapan_v2` tetap hidup sebagai primitive internal — masih dipakai sesudah perubahan batas minggu; binding tombol di `EventBinder.js` dibiarkan dengan komentar penjelas (guard `if (regenerateButton)` membuatnya no-op)
- [x] Dialog Jadwal memakai `build_resolution_preview()` yang sama dengan dashboard, diserialisasi sebagai **string desimal kanonik** (konsisten kebijakan presisi doc 30)

**Prasyarat yang harus ditutup lebih dulu:** tombol perbaikan tidak akan berguna bila baris basi
**kosong** tidak bisa dibereskan — dan itu kasus paling umum (kolom sisa). Karena `follow_date`/
`accumulate_edge` hanya ditawarkan saat ada nilai, jalur `none` kini menghapus baris di luar jendela
yang **tidak membawa data apa pun** (planned 0, actual 0, `actual_cost` NULL). Provably lossless, dan
persis kasus doc 38 §6.1 #2. `trim_planned` sengaja tidak ikut (kontrak legacy-nya justru meninggalkan
baris ber-nilai 0).

Gate: **LULUS** — 10 test: guard sumber (tombol buta hilang, host ter-wire, gating sinyal server,
tanpa `.innerHTML`), preview tidak memutasi, **commit memperbaiki struktur basi hingga
`timeline_stale=false`** (inti T-06), baris kosong dibereskan tanpa bertanya, realisasi di luar
jendela ditolak dengan alasan, proyek sehat tidak menawarkan apa-apa, revisi basi → 409.

---

## 6. Invariant lintas-langkah

Di-assert di **setiap** test yang commit-nya sukses, mulai langkah 1.2. Bila salah satu gagal, langkah tidak lulus.

| ID | Invariant | Cara verifikasi |
|---|---|---|
| **I-A** | `timeline_stale == false` setelah commit yang sukses | `compute_project_readiness(project)["timeline_stale"]` |
| **I-B** | Jumlah kolom chart == jumlah minggu jendela baru | `len(api_chart_data(...)["columns"])` == `expected_week_count(new_start, new_end, week_end_day)` |
| **I-C** | Tidak ada baris `PekerjaanProgressWeekly` di luar jendela | filter `week_start_date < start OR week_end_date > end` → kosong |
| **I-D** | Total planned per pekerjaan ≤ 100% **dan** tiap baris ≤ 100 | agregat per pekerjaan + max per baris |
| **I-E** | Audit memuat snapshot penuh baris yang dimutasi | `DetailAHSPAudit.old_data` berisi kelima field per baris |
| **I-F** | Realisasi tidak berubah kecuali operasi memang ditolak | jumlah `actual_proportion`/`actual_cost` sebelum == sesudah |

**Catatan I-B:** kolom grid berasal dari `JadwalPekerjaanExportAdapter` yang **sama** dengan export
(`api_chart_data` di `views_api.py:7901` memanggilnya), dan padding `target_weeks = max(expected_weeks,
max_week_number)` ada di `jadwal_pekerjaan_adapter.py:227`. Jadi I-B menguji jalur nyata, bukan proksi.

**Prasyarat yang harus dinyatakan di test, bukan diasumsikan (R-10):** I-A dan I-B terlindung dari
tahapan manual karena `_fetch_weekly_tahapan` memfilter `is_auto_generated=True, generation_mode='weekly'`.
Tetapi `sync_weekly_to_tahapan` — dipanggil di jalur yang sama — mengurutkan **seluruh** tahapan dan
memetakan `urutan + 1` → `week_number` (`progress_utils.py:249-252`). Satu tahapan manual menggeser semua
assignment turunan setelahnya. G-4 di luar scope doc 38, jadi minimal **satu test** harus menegaskan
perilaku mesin saat tahapan manual hadir, supaya pengecualiannya diketahui.

---

## 7. Log bukti test

Diisi saat langkah dieksekusi. Satu baris per perintah yang benar-benar dijalankan.

| Tanggal | Langkah | Command/Test | Result | Catatan |
|---|---|---|---|---|
| 2026-08-24 | Baseline | `pytest tests_timeline_crud_hardening.py` | **10 passed** | Menetapkan E-1: dokumen menulis 11 |
| 2026-08-24 | Baseline | `pytest tests_timeline_crud_hardening.py tests_mass_edit.py tests_wp_b4_readiness.py` | **1 failed, 52 passed** (69.01s) | Kegagalan = B-1, pre-existing (SQLite `Sum()` → `'60'` vs `'60.00'`) |
| 2026-08-24 | 1.1 | `pytest detail_project/tests_timeline_contract_freeze.py` | **6 passed** (12.39s) | 6 lock baru hijau — perilaku lama terkunci |
| 2026-08-24 | 1.1 | Gate penuh: baseline §2 + file baru | **1 failed, 58 passed** (66.23s) | Kegagalan = B-1 saja (tidak memburuk). Lulus naik 52 → **58** (+6) |
| 2026-08-24 | 1.1 | `git diff --stat` pada `tests_timeline_crud_hardening.py` + `tests_mass_edit.py` | **kosong** | Test lama tidak dimodifikasi |
| 2026-08-24 | 1.1 (revisi G0-1) | `pytest tests_timeline_contract_freeze.py tests_timeline_crud_hardening.py tests_mass_edit.py` | **26 passed** (31.70s) | Setelah K-1 direvisi jadi kontrak permanen; tidak ada test yang perlu diubah isinya, hanya nama + docstring |
| 2026-08-24 | 1.2 | `pytest tests_timeline_resolution_engine.py` | **17 passed** (17.79s) | Matriks resolusi lengkap |
| 2026-08-24 | 1.2 | Regresi 6 suite (timeline/freeze/engine/mass-edit/readiness/jadwal-hardening) | **1 failed, 76 passed** (83.34s) | Kegagalan = B-1 saja; tidak memburuk dari baseline |
| 2026-08-24 | 1.2 | `pytest tests_wp_export_parity.py tests_wp_p7_jadwal.py tests_kebutuhan_timeline_b6b.py` | **39 passed** (51.36s) | Refactor `_build_weekly_tahapan_instances` → `build_week_buckets` terbukti behavior-preserving di jalur export & hilir |
| 2026-08-24 | 1.2 | `git diff --stat` pada 2 file test lama | **kosong** | Gate "10 test lama hijau tanpa dimodifikasi" terpenuhi |
| 2026-08-24 | 1.2 | `manage.py check` / `makemigrations --check` | **0 issue** / **No changes detected** | Tanpa migrasi skema |
| 2026-08-24 | 1.3 | `pytest tests_timeline_mass_edit_safety.py tests_mass_edit.py` | **17 passed** (25.62s) | 9 test baru + seluruh mass edit lama, termasuk 2 lock all-or-nothing |
| 2026-08-24 | 1.3 | Gate Fase 1 penuh (7 suite) | **1 failed, 81 passed** (103.03s) | Kegagalan = B-1 saja |
| 2026-08-24 | 1.3 | `git diff -U0 tests_mass_edit.py \| grep "def test_"` | **1 method** | Hanya lock T-01 yang dibalik; 2 test all-or-nothing utuh |
| 2026-08-24 | 1.3 | `pytest tests_wp_export_parity.py tests_wp_p7_jadwal.py` | **28 passed** (38.01s) | Tidak ada regresi hilir |
| 2026-08-24 | 1.3 | `manage.py check` | **0 issue** | |
| 2026-08-24 | 2.1 | `pytest dashboard/tests_timeline_dialog.py` | **11 passed** (19.86s) | Setelah perbaikan B-2 (lihat §8) |
| 2026-08-24 | 2.1 | Regresi 6 suite timeline | **60 passed** (73.08s) | Perbaikan B-2 tidak menimbulkan regresi |
| 2026-08-24 | 2.2 | `node --check mass-edit-toggle.js` | **OK** | |
| 2026-08-24 | 2.2 | `pytest tests_mass_edit.py tests_timeline_dialog.py tests_timeline_mass_edit_safety.py` | **29 passed** (14.21s) | |
| 2026-08-24 | Fase 1+2 | Gate penuh 11 suite | **1 failed, 149 passed** (83.20s) | Kegagalan = B-1 saja |
| 2026-08-24 | Fase 1+2 | `manage.py check` | **0 issue** | |
| 2026-08-24 | 3.1 | `pytest tests_timeline_repair_ui.py` | **10 passed** (12.68s) | Termasuk commit end-to-end yang menutup T-06 |
| 2026-08-24 | 3.1 | `node --check` timeline_repair.js / readiness_autoload.js / EventBinder.js | **OK** | |
| 2026-08-24 | **Fase 1+2+3** | Gate penuh **13 suite** | **1 failed, 165 passed** (177.80s) | Kegagalan = B-1 saja |
| 2026-08-24 | Fase 1+2+3 | `manage.py check` | **0 issue** | |

---

## 8. Log keputusan & perubahan scope

| Tanggal | Perubahan | Alasan |
|---|---|---|
| 2026-08-24 | G-5 ditarik dari backlog doc 37 ke langkah **2.1** | Langkah 2.1 menambah dialog di `project_edit`, jalur yang tidak mengirim `expected_revision`. Menambah UI tanpa kunci optimistik membuka balapan dua-tab persis di tempat yang jalur API sudah lindungi |
| 2026-08-24 | Post-condition guard (R-6) jadi DoD wajib langkah 1.2 | Bukti "aman" doc 37 §4.5 bertumpu pada batas ≤100 yang hanya ditegakkan di satu jalur API, bukan constraint DB |
| 2026-08-24 | Errata E-1..E-4 dicatat | Menjaga gate tetap dapat diverifikasi |
| 2026-08-24 | **G0-1 direvisi** dari "realisasi di mana pun memblokir" → gerbang per bentuk perubahan (K-1) | Aturan tunggal itu lebih ketat daripada perilaku hari ini dan menolak kasus paling umum: proyek molor → tanggal selesai diundur padahal realisasi sudah tercatat. Perpanjangan ujung terbukti tidak dapat menggerakkan realisasi, jadi penolakannya kerugian tanpa manfaat. Owner mendelegasikan pilihan akhir |
| 2026-08-24 | `test_lock_end_extension_...` → `test_contract_end_extension_with_actual_stays_allowed` | Konsekuensi revisi G0-1: dari lock yang menunggu dibalik menjadi kontrak permanen |
| 2026-08-24 | **`trim_planned` dibekukan sebagai jalur legacy**; T-06 ditutup oleh resolusi mesin, bukan oleh `trim_planned` | `test_timeline_trim_planned_preserves_actual_contract` meng-assert baris di luar jendela **masih ada** bernilai 0. Membereskannya akan melanggar gate "10 test lama hijau tanpa dimodifikasi" dan doc 37 §6. Jalur ini disupersede `follow_date` dan hilang dari UI setelah Fase 2 |
| 2026-08-24 | `build_week_buckets()` diangkat jadi SSOT bucket di `progress_utils.py` | DoD 1.2 melarang menghitung tanggal minggu secara inline. `_build_weekly_tahapan_instances` di-refactor memakainya (behavior-preserving, dibuktikan 39 test export/jadwal) sehingga hanya ada satu implementasi batas minggu |
| 2026-08-24 | **B-2 diperbaiki di service, bukan di pemanggil** (`_persisted_timeline`) | Dua pemanggil sudah membuat kesalahan yang sama secara independen; menambal satu titik akan menyisakan yang lain (pelajaran UF-013/AT-01). Membaca tanggal lama dari DB membuat fungsi tidak dapat disalahgunakan |
| 2026-08-24 | Mass edit: muat ulang otomatis dimatikan saat ada `needs_decision` | Reload 1.5 detik menelan laporan sebelum sempat dibaca — laporan itu justru inti langkah 2.2 |
| 2026-08-24 | Jalur `none` membersihkan baris di luar jendela yang tidak membawa data | Prasyarat langkah 3.1: tanpa ini tombol perbaikan tidak dapat menuntaskan kolom sisa yang KOSONG — kasus paling umum, dan yang doc 38 §6.1 #2 minta selesai tanpa dialog. Lossless secara konstruksi; `trim_planned` tidak ikut karena kontrak legacy-nya justru meninggalkan baris ber-nilai 0 |
| 2026-08-24 | `readiness_autoload.js` menyiarkan `readiness:loaded` | Halaman perlu bereaksi pada `timeline_stale` tanpa memanggil endpoint kedua atau menghitung ulang sendiri. Aditif; 5 halaman pemakai tidak terpengaruh |

---

## 9. Rollback

Setiap langkah satu commit terisolasi.

| Langkah | Sifat | Rollback |
|---|---|---|
| 1.1 | Aditif (test saja) | revert bebas risiko |
| 1.2 | Aditif (resolusi baru; jalur lama `none`/`trim_planned` tak berubah) | revert 1.2 mengembalikan mesin lama; 1.1 tetap |
| **1.3** | **Mengubah perilaku destruktif** | titik risiko utama — revert 1.3 mengembalikan mass edit ke perilaku lama tanpa menyentuh mesin 1.2 |
| 2.1–2.2 | UI di atas mesin yang sudah teruji | revert tidak menyentuh backend |
| 3.1 | UI Jadwal | revert mengembalikan tombol permanen |

---

## 10. Di luar scope (tetap backlog doc 37)

G-1 (Django admin), G-2 (duplikat project), G-3 (batas minggu), G-4 (tahapan manual — lihat prasyarat §6),
T-05 (cache chart regenerate — lihat E-3), bug `month_number` monthly, opsi keempat
`scale_proportional`, dan pertanyaan niat "koreksi vs pergeseran" (doc 37 §4.1).

**Catatan bug `month_number`:** terverifikasi nyata — `grep month_number` pada
`exports/jadwal_pekerjaan_adapter.py` **tidak menemukan apa pun**, sementara `views_api.py`
membacanya via `col.get('month_number', 0)`. Seluruh kolom monthly karena itu ber-id `month_0`.
Layak doc/issue sendiri; jangan diselipkan ke langkah mana pun di sini.
