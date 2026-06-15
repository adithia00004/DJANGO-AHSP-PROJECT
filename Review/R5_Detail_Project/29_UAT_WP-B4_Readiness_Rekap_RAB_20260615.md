# UAT Checklist — WP-B4 Readiness Banner (Pilot Rekap RAB)

**Tanggal:** 2026-06-15
**Scope:** Memverifikasi banner readiness (`b4.3`) di halaman **Rekap RAB** — display-only, server-authoritative.
**Yang diuji:** banner muncul saat data belum lengkap/sinkron, isinya akurat & aman (escaped), hilang saat data bersih, dan tidak mengubah perhitungan.
**Tester:** ____________  **Hasil akhir:** ☐ PASS  ☐ FAIL

> Cara pakai: kerjakan urut dari Bagian 0. Centang tiap langkah. Kolom **Hasil** isi P (pass) / F (fail) + catatan. Jika satu langkah FAIL, catat lalu lanjut bila memungkinkan.

---

## 0. Persiapan

- [ ] Stack berjalan dari root (Docker PG15 SSOT) — aplikasi terbuka di browser.
- [ ] Login sebagai akun **PRO aktif** (langganan belum kedaluwarsa). *Halaman bisa dibuka non-PRO, tetapi gunakan PRO agar konsisten dengan alur penuh.*
- [ ] Buka **DevTools → Network** dan **Console** (biarkan terbuka sepanjang UAT).
- [ ] (Opsi) Buka tab kedua untuk Dashboard agar mudah pindah halaman.

**Hasil 0:** ____

---

## A. Buat project baru

- [ ] Dari **Dashboard**, klik **Buat Project Baru**.
- [ ] Isi identitas project: Nama, Sumber Dana, Lokasi, Client/Owner, Anggaran, Tanggal mulai & selesai.
- [ ] Simpan → project baru terbuka / muncul di daftar Dashboard.
- [ ] Catat **Project ID** (terlihat di URL, mis. `/detail_project/<ID>/...`): ____

**Expected:** project tersimpan, bisa dibuka. **Hasil A:** ____

---

## B. Bangun struktur pekerjaan minimal (List Pekerjaan)

Buka **List Pekerjaan** (`/<ID>/list-pekerjaan/`).

- [ ] Tambah **1 Klasifikasi** (mis. "Pekerjaan Persiapan").
- [ ] Tambah **1 Sub-Klasifikasi** di bawahnya.
- [ ] Tambah **3 Pekerjaan custom** di sub tersebut, beri kode/uraian:
  - [ ] Pekerjaan **P-A** (akan: harga LENGKAP + volume ADA → bersih)
  - [ ] Pekerjaan **P-B** (akan: harga KOSONG/null → memicu `missing_price`)
  - [ ] Pekerjaan **P-C** (akan: TANPA volume → memicu `missing_volume`)
- [ ] Simpan. Pastikan ketiganya tampil di tree.

**Expected:** 3 pekerjaan tersimpan, tanpa error. **Hasil B:** ____

---

## C. Isi rincian AHSP (Template AHSP)

Buka **Template AHSP** (`/<ID>/template-ahsp/`).

- [ ] Untuk **P-A**: tambah ≥1 baris detail (mis. kategori BHN), isi **kode**, **uraian**, **koefisien ≥ 0**. Simpan.
- [ ] Untuk **P-B**: tambah ≥1 baris detail dengan **item harga BARU** (kode item baru, mis. `BHN-KOSONG`). Simpan.
- [ ] Untuk **P-C**: tambah ≥1 baris detail (boleh pakai item yang harganya nanti diisi). Simpan.
- [ ] Konfirmasi tiap simpan **sukses (200)**, tidak ada toast error, tidak ada pesan partial.

**Expected:** detail tersimpan & otomatis ter-expand (rekap membaca expanded). **Hasil C:** ____

---

## D. Sengaja buat kondisi "belum lengkap"

### D1 — `missing_price` (harga item belum diisi)
Buka **Harga Items** (`/<ID>/harga-items/`).

- [ ] Temukan item yang dipakai **P-B** (mis. `BHN-KOSONG`).
- [ ] **Biarkan kolom harga KOSONG** (jangan isi 0 — kosong = "belum diisi"). Pastikan baris lain milik P-A **terisi harga > 0**.
- [ ] (Kontrol negatif) Isi 1 item dengan harga **0** eksplisit → ini TIDAK boleh dianggap "belum diisi".
- [ ] Simpan.

**Expected:** harga kosong tersimpan sebagai "belum diisi" (bukan dikoersi 0). **Hasil D1:** ____

### D2 — `missing_volume` (pekerjaan tanpa volume)
Buka **Volume Pekerjaan** (`/<ID>/volume-pekerjaan/`).

- [ ] Isi volume **P-A** dan **P-B** dengan angka > 0.
- [ ] **JANGAN isi volume P-C** (biarkan tanpa nilai/baris).
- [ ] (Kontrol negatif) Boleh set 1 pekerjaan volume = **0** eksplisit → ini TIDAK boleh dianggap missing.
- [ ] Simpan.

**Expected:** P-C tetap tanpa baris volume. **Hasil D2:** ____

---

## E. Verifikasi banner di Rekap RAB (inti UAT)

Buka **Rekap RAB** (`/<ID>/rekap-rab/`).

- [ ] **Banner peringatan muncul** di atas tabel (kotak kuning), judul memuat: **"total RAB belum dapat dianggap final"**.
- [ ] Baris **"harga item belum diisi"** muncul, jumlah **= 1**, mencantumkan kode item P-B (mis. `BHN-KOSONG`), ada petunjuk "(perbaiki di Harga Items)".
- [ ] Baris **"pekerjaan belum punya volume"** muncul, jumlah **= 1**, mencantumkan kode **P-C**, ada petunjuk "(perbaiki di Volume)".
- [ ] Item harga **0** eksplisit (D1) **TIDAK** muncul di banner.
- [ ] Pekerjaan volume **0** eksplisit (D2) **TIDAK** muncul di banner.
- [ ] **Network:** buka response `GET /<ID>/rekap/` → ada field **`readiness`** dengan `schema_version: "b4.3"`; `missing_price`/`missing_volume` sesuai; `incomplete_planned_allocation`, `allocation_without_volume`, `timeline_stale` = **null**; `pending_signals` memuat ketiga nama itu.
- [ ] **Console:** tidak ada error JS.
- [ ] Tabel & total tetap tampil normal (banner tidak memblokir tampilan).

**Expected:** banner akurat, null≠zero terbukti, perhitungan tetap jalan. **Hasil E:** ____

---

## F. Verifikasi banner HILANG saat data dibereskan

- [ ] Buka **Harga Items**, isi harga item P-B (`BHN-KOSONG`) dengan angka > 0. Simpan.
- [ ] Buka **Volume Pekerjaan**, isi volume **P-C** > 0. Simpan.
- [ ] Kembali ke **Rekap RAB**, **reload** halaman.
- [ ] **Banner TIDAK muncul lagi** (tidak ada kotak kuning).
- [ ] Total RAB kini memasukkan P-B & P-C (nilai berubah dibanding Bagian E).

**Expected:** banner bersih = tidak ada banner sama sekali (tidak ada pesan "semua siap" palsu). **Hasil F:** ____

---

## G. Spot-check keamanan (escaping) — opsional tapi disarankan

- [ ] Di **List Pekerjaan** atau **Harga Items**, beri salah satu uraian/kode nilai berisi HTML, mis. `<b>x</b>` atau `<img src=x onerror=alert(1)>`. Simpan.
- [ ] Buat ulang kondisi missing (kosongkan harga item tsb) → buka **Rekap RAB**.
- [ ] Banner menampilkan teks **apa adanya** (mis. terlihat `<img ...>` sebagai teks), **TIDAK** mengeksekusi script, tidak ada popup `alert`.

**Expected:** nilai dinamis ter-escape (aman XSS). **Hasil G:** ____

---

## H. Regresi singkat

- [ ] Export Rekap RAB (XLSX/print) tetap berfungsi seperti sebelum ada banner.
- [ ] Pindah antar halaman (Volume ↔ Rekap RAB) beberapa kali → banner konsisten dengan state data, tidak "nyangkut".
- [ ] Tidak ada warning/error baru di Console pada seluruh alur.

**Expected:** tidak ada regresi. **Hasil H:** ____

---

## Catatan kondisi lanjutan (di luar alur UI normal)

Dua sinyal berikut **sulit dipicu lewat UI biasa** dan sudah dikunci oleh automated test — **tidak wajib** di UAT manual ini:

- `invalid_coefficient` (koefisien negatif): simpan menolak koef < 0 (WP-B3), jadi tak bisa dibuat dari UI. Dicakup `tests_wp_b4_readiness`.
- `expansion_not_ready` / `incomplete_expansion` / `excess_expansion`: terkait state ekspansi internal/bundle. Dicakup automated test; verifikasi manual menyusul saat fan-out + inc-4.

---

## Ringkasan

| Bagian | Hasil (P/F) | Catatan |
|---|---|---|
| 0 Persiapan | | |
| A Buat project | | |
| B Struktur pekerjaan | | |
| C Rincian AHSP | | |
| D1 missing_price | | |
| D2 missing_volume | | |
| E Banner muncul & akurat | | |
| F Banner hilang | | |
| G Escaping | | |
| H Regresi | | |

**Keputusan:** ☐ Lolos → lanjut fan-out **Rincian AHSP**  ☐ Ada temuan → catat & perbaiki sebelum fan-out

**Temuan/komentar:**
_______________________________________________________________
