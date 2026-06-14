# Rekonsiliasi Lintas-Page (Project-Wide) — Dasar Implementation Plan

**Tanggal:** 14 Juni 2026
**Cakupan:** Dashboard (09), List Pekerjaan (16), Volume (17), Template AHSP (18), Harga Items (19), Rincian AHSP (20), Rekap RAB (21), Jadwal (22), Rekap Kebutuhan (23), **Audit Trail (24)**
**Dokumen terkait:** Cleanup & Deprecation Roadmap (`25_Project_Cleanup_Deprecation_Roadmap_20260614.md`)
**Tujuan:** memastikan temuan antar-page tersinkron, tidak ada keputusan ganda/ambigu, dan tidak ada fitur/mode terlewat — sebelum menyusun implementation plan.
**Status keputusan:** **B-1, B-2, B-5 DIKUNCI (owner, 14 Juni 2026).**

> Aturan baca: dokumen ini tidak mengubah temuan tiap audit. Ia peta dedup + resolusi konflik + urutan kerja. Keputusan owner (D-xx) pada audit terkait tetap otoritatif.
> **Penting:** sebelum memperbaiki sesuatu, cek Section E — artefak yang akan **dihapus** (per roadmap 25) **tidak perlu diperbaiki dahulu**.

---

## A. Temuan duplikat lintas-page (satu akar → satu fix shared)

### A-1. Satu calculation service Rekap (markup default + basis nilai)
RA-01 = RR-02 (jalur kode identik `services.py:2293` + `api_get_rekap_rab`); adapter Rincian RA-03 hitung ulang; bobot Kurva S KS-05 = `G×volume` dari `compute_rekap_for_project`. **Fix tunggal:** satu default markup + satu calculation builder dipakai web + export semua consumer (Rincian, RAB, Jadwal-KS, Kebutuhan).

### A-2. Cache signature lupa `HargaItemProject` (+ markup)
RR-11, KS-03 (`views_api.py:7286`), RK-04 (`_kebutuhan_signature:101`). **Fix tunggal:** satu helper signature bersama yang selalu menyertakan `HargaItemProject.updated_at` + revisi markup.

### A-3. Bocoran `str(e)` pada error (export + API)
TA-08, HI, RA-15, RR-17, dan RK-23. **Fix tunggal:** wrapper error bersama — log + correlation ID server-side, pesan generik + kode error stabil. API Audit tidak ikut diperbaiki karena dihapus melalui CL-17.

### A-4. XSS via `innerHTML` (data user → HTML), tanpa CSP
F-01 (Dashboard), LP-01 (List Pekerjaan preview), RR-01 + RR-18 (Rekap RAB + print). **Fix tunggal (2 lapis):** (a) render `textContent`/escape di tiap titik; (b) **CSP bertahap** tingkat aplikasi (belum ada di `config/`) + CDN ber-SRI/self-host (VP-08, TA-11, RR-15).

**Pengecualian cleanup:** AT-01 tidak diperbaiki sebagai surface aktif karena
Audit Trail telah diputuskan untuk dipensiunkan. Stored XSS dan mismatch
permission pada page tersebut ditutup dengan menghapus UI/API pembacaan
(CL-17), sementara model dan writer backend dipertahankan sementara.

### A-5. Atomicity / partial-write — **dengan koreksi status code (lihat B-1)**
LP-02, VP-01/VP-03, HI-01/HI-16, JDW-01, JDW-03, RK timeline. **Fix tunggal (konvensi, dikoreksi):** satu aksi save = atomik (semua-atau-tidak). **Status code untuk save atomik:**

```text
200      = seluruh aksi berhasil
400/422  = seluruh aksi ditolak, TIDAK ada perubahan
500      = rollback, TIDAK ada perubahan
```

**`207` TIDAK boleh dipakai untuk satu form/save.** `207` hanya untuk **batch yang secara produk independen** (mis. beberapa export, beberapa Project). Validasi seluruh payload **sebelum** mutasi; jangan `ok:true` saat ada error; validate-before-delete (jangan hapus sebelum payload lolos validasi penuh).

### A-6. localStorage conversion tidak project-scoped
HI-08, RK-10. **Fix:** server/DB = SSOT conversion profile; hapus fallback localStorage (D-HI-*, D-RK-03).

### A-7. Unit conversion tidak mengubah total kanonik
HI-03, RK-09. **Fix:** total selalu dari harga dasar kanonik backend; satuan beli hanya presentasi (D-HI-03 + D-RK-03).

### A-8. Readiness / `expanded_ready` kontrak bersama
Template AHSP D-06, RA-08, RR-08, Rekap Kebutuhan **D-RK-07** (superset). **Fix:** jadikan **D-RK-07 schema readiness kanonik** untuk semua consumer (lihat B-4).

### A-9. Missing-vs-zero konvensi tunggal
Template D-04, Harga D-HI-01, RR-07, RK-19/D-RK-07, Volume. **Fix:** `null=belum diisi`, `0.00=eksplisit`, koefisien 0 sah vs invalid dipisah — sama untuk volume, harga, koefisien.

### A-10. Snapshot identitas pada histori (Audit Trail)
AT-03/AT-07 merupakan temuan valid, tetapi **DEFER** setelah keputusan pensiun
page Audit Trail. Model, histori, dan writer dipertahankan apa adanya untuk
diagnosis sementara; migrasi snapshot baru hanya dibuat jika kebutuhan audit
operasional muncul kembali.

---

## B. Keputusan — STATUS

### B-1. Kebijakan concurrency — **DIKUNCI: Last-Write-Wins**
Kebijakan resmi aplikasi:
- **last-write-wins**;
- satu aksi save **atomik**;
- **validasi seluruh payload sebelum mutasi**;
- **tidak ada** dialog konflik atau HTTP **409**;
- response **tidak boleh** menyatakan sukses jika transaksi dibatalkan;
- kegagalan parsial hanya untuk operasi **batch yang produknya independen**.

**Koreksi A-5 (penting):** atomic save **tidak** mengembalikan `207` berisi sebagian sukses. Gunakan `200` / `400`–`422` / `500` (lihat A-5). `207` hanya untuk batch independen (beberapa export/Project), bukan satu form/save.

**Konsekuensi:** seluruh rekomendasi audit awal "aktifkan optimistic locking/409" (VP-06 catatan, LP-03, TA-02, HI-09, RA-11, RR-20) **dibatalkan** dan dibaca sebagai "pastikan atomik + tanpa partial-write". **Pengecualian yang tetap dibereskan:** prompt merge/override Volume (VP-06) = bug UX false-positive (deteksi `Max(updated_at)`+`last_sync_at` opt-in), bukan locking.

### B-2. Semantik JSON — **DIKUNCI: JSON = paket data terstruktur, bukan laporan**
Tiga tipe eksplisit:

| Tipe | Sumber | Fungsi |
|---|---|---|
| `project_backup` | seluruh Project | copy/backup/restore — **format JSON kanonik utama** |
| `work_structure_template` | List Pekerjaan / Template AHSP | paket transfer dengan pasangan import; wajib `schema_version`, `package_type`, validasi atomik |
| `diagnostic_snapshot` | admin/debug | bukan format laporan user |

JSON pada **Harga Items, Volume, Rekap RAB, Rekap Kebutuhan, Jadwal dipensiunkan** jika tidak punya workflow import yang sah. **Laporan user = PDF/XLSX/Word/CSV** sesuai konteks. Dengan ini List Pekerjaan & Template AHSP tidak bertentangan: JSON mereka adalah paket transfer (`work_structure_template`), bukan laporan.

### B-3. Penamaan nilai kanonik — arah jelas (Template AHSP D-01)
`component_cost_before_markup` (E_base) / `markup_amount` (F) / `unit_price_after_markup` (G); total pekerjaan = `G×volume`. **Jaga ambiguitas:** Rekap RAB pakai **G** (post-markup); **Rekap Kebutuhan pakai harga dasar (pra-markup)** dengan label `Total Harga Dasar Kebutuhan` + catatan "belum termasuk markup/PPN" (D-RK-05). Tidak boleh ada dua field `total` tanpa kualifikasi.

### B-4. Readiness — arah jelas: satukan ke D-RK-07
Gabungkan Template D-06 + RA-08 + RR-08 ke **satu schema D-RK-07** (`missing_volume/missing_price/invalid_coefficient/expansion_not_ready/incomplete_planned_allocation/timeline_stale`).

### B-5. Export app-wide — **DIKUNCI: server-authoritative (laporan)**
Berlaku untuk **PDF, Word, XLSX, dan CSV berbasis kalkulasi**:
- seluruh export laporan resmi **server-authoritative**;
- layar & export mengambil **calculation service/dataset canonical yang sama**;
- client hanya memilih parameter + menampilkan preview;
- **draft belum disimpan tidak masuk export**;
- background export hanya setelah threshold beban terlampaui;
- identitas Project dari **Dashboard** (`_project_identity`);
- **signature & aturan pagination hanya** pada dokumen yang memerlukan pengesahan.

**Paket JSON copy/import (B-2) mengikuti framework package terpisah, bukan framework laporan.**

### B-6. Penghapusan jalur Tahapan & Orphan — pastikan tuntas (lihat Section E)
D-RK-08 (hapus `mode=tahapan` kalkulasi) + D-HI-05 (pensiun Orphan page) + Jadwal (`PekerjaanTahapan` = projection). Eksekusi via roadmap cleanup (CL-06, CL-01).

---

## C. Kelengkapan fitur/mode per page

| Page | Status | Catatan |
|---|---|---|
| 09 Dashboard | Lengkap | F-03 quick search rusak, F-02 mass edit. Tidak ada mode terlewat. |
| 16 List Pekerjaan | Lengkap (template terverifikasi) | add-klas, compact, nav-search, filter, template library, export-json, save FAB. |
| 17 Volume | Lengkap | sesuai VP. |
| 18 Template AHSP | Lengkap | sesuai TA. |
| 19 Harga Items | Lengkap | sesuai HI. |
| 20 Rincian AHSP | Lengkap (template terverifikasi) | `ra-btn-save`/`rk-btn-reset` ada = konfirmasi RA-05 dead controls. |
| 21 Rekap RAB | Lengkap | sesuai RR. |
| 22 Jadwal | Lengkap + gap dicatat | Kurva S jalur ganda (KS-01..05). Harian/Custom backend tak terekspos (benar). `undo-manager.js` dead. |
| 23 Rekap Kebutuhan | Lengkap (banyak kontrol tersembunyi/mati = sudah jadi temuan RK-13/14/18) | |
| 24 Audit Trail | Dipensiunkan | UI/API pembacaan dihapus melalui CL-17; model, histori, dan writer backend dipertahankan sementara. |

**Kesimpulan:** tidak ada mode user-facing yang terlewat. Yang ada: (i) gap Kurva S Jadwal (tercatat KS), (ii) kontrol mati/tersembunyi yang sudah jadi temuan. **Langkah-0 tiap implementation plan:** konfirmasi permukaan template (toolbar/modal/mode) vs audit — murah, mencegah implementasi dead control.

---

## D. Urutan implementasi (mengikuti dependensi A & B)

**Fase 0 — Keputusan:** B-1, B-2, B-5 **DIKUNCI**. B-3/B-4/B-6 arah jelas. → siap lanjut.

**Fase 1 — Shared fondasi (A), urutan:**
1. Shared calculation service Rekap + default markup (A-1).
2. Shared cache signature + harga (A-2).
3. Atomic save convention + status code (A-5/B-1).
4. Readiness/missing-value schema kanonik (A-8/A-9/B-4).
5. Shared export framework + identitas project terpusat (A-3, B-5) + paket JSON terpisah (B-2).
6. CSP bertahap + SRI (A-4).

**Fase 2 — Per-page** (consumer hilir terakhir agar SSOT hulu stabil): Harga Items → Template AHSP → Volume → List Pekerjaan → Rincian AHSP → Rekap RAB → Jadwal → Rekap Kebutuhan. **Dashboard** dapat berjalan paralel karena relatif independen. Audit Trail tidak masuk perbaikan per-page dan mengikuti cleanup CL-17.

**Fase 3 — Cleanup** (Section E): hapus consumer lama **setelah** penggantinya terverifikasi.

---

## E. Integrasi Cleanup Roadmap (25) — JANGAN perbaiki yang akan dihapus

Beberapa "temuan" sebenarnya **artefak yang dihapus**, bukan diperbaiki. Implementation plan harus memetakannya agar tidak buang effort:

| Temuan | Tindakan | Cleanup ID |
|---|---|---|
| Dashboard mass_edit lama (F-10) | **Hapus**, jangan perbaiki | CL-04 |
| List Pekerjaan legacy full-save (LP-05) | Pensiun setelah telemetry | CL-05 |
| Rekap Kebutuhan mode Tahapan (RK-01/02 cabang tahapan) | **Hapus** (D-RK-08) → RK-02 ikut selesai | CL-06 |
| Kurva S jalur client sebagai SSOT (KS-01) | Pensiun setelah server adapter canonical | CL-07 |
| Auto-reload Template AHSP page-open (TA-17) | Hapus trigger massal | CL-08 |
| Duplicate ExportManager/SheetJS/Excel exporter | Hapus setelah parity server export (B-5) | CL-09 |
| Dead controls/CSS (RA-05 save/reset, RK-18 column visibility, undo-manager) | Hapus setelah selector-contract scan | CL-12 |
| Orphan Cleanup page (D-HI-05) | Pensiun UI, housekeeping backend | CL-01 |
| Audit Trail UI/API pembacaan | **Hapus**, pertahankan histori + writer backend | CL-17 |

**Pertahankan sementara (jangan hapus):** Tahapan API v1 + projection models (CL-13), alias HSP/raw fallback (CL-14), parameter legacy + migration guards (CL-15). Migration Django, data canonical, dan audit history tidak dihapus.

---

## F. Prioritas P0 gabungan (project-wide)

| P0 | Sumber | Aksi |
|---|---|---|
| XSS innerHTML | F-01, LP-01, RR-01/RR-18 | A-4 (textContent + CSP) |
| Markup default 0%/10% | RA-01/RR-02 | A-1 calculation service |
| Atomicity/partial-write | LP-02, VP-01/03, HI-01, JDW-01/03 | A-5/B-1 |
| Null→0 / harga | HI-01 | A-9 |
| Konversi atomik & export≠calc | HI-02/HI-03 | A-7/B-5 |
| Timeline ≠ weekly canonical | RK-01 (+RK-03/05) | A-1 + distribute_by_week |

AT-01 dan AT-02 tidak menjadi work package security. Keduanya ditutup melalui
penghapusan UI/API Audit Trail pada cleanup CL-17.
| Print PPN dobel & identitas palsu | RR-03/RR-04 | A-1 + B-5 (identitas terpusat) |

Catatan: tidak ada migrasi DB besar untuk mayoritas fix; migrasi terbatas hanya
item legacy aditif yang benar-benar dibutuhkan (`actual_cost`, kategori
LAIN→tipe, dan week number otoritatif Jadwal R1). Snapshot identitas Audit Trail
tidak masuk implementation plan setelah keputusan CL-17.

---

## G. Reconciliation Ledger — rekomendasi per-page yang DIBATALKAN/diubah oleh keputusan terkunci

Hasil verifikasi sync per-page (14 Juni 2026). Dokumen audit asli **tidak diedit**; daftar ini **otoritatif** dan menggantikan teks rekomendasi lama yang bertabrakan. Implementation plan WAJIB mengikuti ini, bukan teks asli.

### G-1. Dibatalkan oleh **B-1** (last-write-wins; TANPA optimistic locking / 409 / revision token)
| Page | Teks lama (lokasi) | Status baru |
|---|---|---|
| 16 List Pekerjaan | Exec #3 + LP-03; "optimistic concurrency + 409 + revision token" (`:216,389,408,450`); **P0 "Revision token dan stale-write rejection" (`:462`)** | **DIBATALKAN** → ganti jadi "pastikan upsert atomik (A-5)". P0 itu **bukan lagi P0**. |
| 17 Volume | revision token per row (`:117,391`); reject stale `409` (`:398,570`) | **DIBATALKAN**. (VP-06 prompt merge/override = **tetap diperbaiki** sebagai bug UX, bukan locking.) |
| 18 Template AHSP | "version token wajib" (`:665`), "aktifkan optimistic locking UI" (`:675`), "reset revision token" (`:678`), reset stale `409` (`:400`); test "dua tab → 409" (`:757`); **P0 "TA-02 optimistic locking aktif" (`:777`)** | **DIBATALKAN**. **TA-02 di-reframe**: "pastikan save atomik + tanpa partial-write" (tetap P0 untuk atomicity, BUKAN locking). Test diubah jadi "dua tab → last-write-wins, save atomik". |
| 19 Harga Items | "aktifkan optimistic token" (`:299`); P1 "HI-09 optimistic locking" (`:368`) | **DIBATALKAN** → HI-09 jadi "pastikan save atomik". |
| 20 Rincian AHSP | RA-11 "tambah concurrency guard" | **DIBATALKAN**. |
| 22 Jadwal | **Inkonsistensi internal**: §10 P1 "Tambahkan optimistic concurrency" (`:1331`) **bertentangan** dengan keputusan JDW-08 (`:407-414` "tidak ditambahkan") | **JDW-08 otoritatif**; hapus `:1331`. |

### G-2. Diubah oleh **A-5** (atomic save = 200 / 400–422 / 500; `207` BUKAN untuk satu form/save)
| Page | Teks lama (lokasi) | Status baru |
|---|---|---|
| 17 Volume | VP-01 "Gunakan HTTP `207` atau `422` untuk mixed result" (`:297`); verifikasi "hasil campuran selalu `207/422`" (`:711`) | **DIUBAH** → formula save = single atomic: `200/400-422/500`. **Bukan 207.** |
| 16 List Pekerjaan | LP-02 "Gunakan `400`, `409`, atau `422`" (`:201`) | drop `409`; sisanya OK ("jangan 207" `:202` sudah benar). |
| 17 Volume | **VP-02 DELETE param "kembalikan `409 Conflict`+usage" (`:323`)** | **DIKUNCI: gunakan `422 Unprocessable Entity`** dengan daftar dependency/usage. `409` tidak digunakan agar tidak ambigu dengan stale-write/concurrency yang dibatalkan B-1. |

### G-3. Diubah oleh **B-2** (JSON = paket data, bukan laporan)
| Page | Status |
|---|---|
| 09 Dashboard | import/export backup JSON = **`project_backup`** → **SUDAH SELARAS** (tinggal beri nama tipe). |
| 16 List Pekerjaan / 18 Template AHSP | export JSON = **`work_structure_template`** (paket transfer + import) → **SELARAS**; pastikan `schema_version`/`package_type`/import atomik. |
| 17 Volume / 19 Harga Items | export JSON → **DIPENSIUNKAN** sebagai laporan jika tak ada workflow import sah (verifikasi consumer). |
| 21 Rekap RAB | JSON terdaftar sebagai format laporan (`:31,644,675`) → **DIPENSIUNKAN**; laporan = PDF/XLSX/Word. |
| 22 Jadwal | JSON-in-formats (`:55,570`) → ikuti Export-9 + B-2: JSON = paket copy/`project_backup` atau dipensiun sebagai laporan; baris "PDF/XLSX/JSON same dataset" (`:570`) hanya berlaku bila JSON dipertahankan sebagai paket data. |
| 23 Rekap Kebutuhan | sudah menyatakan JSON bukan laporan (`:37,969`) → **SELARAS**. |

### G-4. Catatan sync lain (bukan pembatalan, hanya penegasan)
- **Status concurrency di tiap audit** ("tidak ada optimistic locking" sebagai *temuan*) tetap **fakta yang benar**; yang berubah hanya **rekomendasinya** (B-1: itu memang disengaja). Jadi temuan tidak dihapus, rekomendasinya yang di-reframe.
- **Markup/naming** (B-3), **readiness** (B-4), **missing-vs-zero** (A-9), **export server-authoritative** (B-5) — tidak ada teks per-page yang *bertentangan*; hanya perlu konsolidasi ke kontrak bersama saat implementasi.

**Kesimpulan verifikasi sync:** seluruh ketidaksesuaian terkonsentrasi pada **concurrency (G-1), status code (G-2), dan JSON (G-3)** — semuanya kini punya resolusi terkunci di atas. Tidak ditemukan konflik baru pada calculation/markup/readiness/export selain yang sudah dipetakan di Section A–B. Fitur/mode: lengkap (Section C). Project siap masuk penyusunan implementation plan.
