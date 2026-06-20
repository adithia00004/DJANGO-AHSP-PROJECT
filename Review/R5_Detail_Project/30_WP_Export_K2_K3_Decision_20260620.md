# WP Export — Audit & Dokumen Keputusan K2/K3 (excel_exporter.py)

**Tanggal:** 20 Juni 2026
**Status:** AUDIT-ONLY (belum ada perubahan kode — menunggu keputusan produk)
**Scope:** `detail_project/exports/excel_exporter.py` (4044 baris) — modul export Excel **bersama** lintas-report.
**Konteks:** Lanjutan WP Export. `str(e)`-leak (TA-08/JDW-19/RK-23) sudah ditutup. Sisa = K2 (locale parse) + K3 (rumus hidup) + presisi (`number_format`). Ketiganya **kebijakan presentasi** + **risiko regresi lintas-report**, jadi diaudit dulu.

---

## 0. Report yang dilayani modul ini

| Method | Report | Dipakai |
|---|---|---|
| `export_volume_pekerjaan` (:269) | Volume Pekerjaan XLSX | live |
| `_export_rincian_ahsp_2sheet` (:578) | Rincian AHSP XLSX (2-sheet) | live |
| `export_professional` (:1103) | Jadwal — Kurva S professional | live |
| `export_monthly_professional` (:2101) | Jadwal — bulanan | live |
| `export_weekly_professional` (:3547) | Jadwal — mingguan | live |
| `export` (:172) generic | fallback | live |

**Konsekuensi:** setiap perubahan pada helper bersama (`parse_number`, `_parse_number`, `number_format`, penulisan rumus) berpotensi mengubah **semua** report di atas → wajib regresi lintas-report.

---

## 1. K3 — Rumus Excel hidup vs nilai backend

### 1.1 Keadaan saat ini
Export menulis **rumus Excel hidup** di 7 titik:

| Baris | Rumus | Report / sheet |
|---|---|---|
| `:345/347/430/445` | `_convert_volume_formula(...)` → `=Parameters!$D$5*$D$6` | **Volume** (formula parameter user → rumus Excel) |
| `:759`, `:982` | `=E{r}*F{r}` (koef × harga) | **Rincian AHSP** 2-sheet |
| `:781`, `:1007` | `=SUM(G{a}:G{b})` (subtotal) | **Rincian AHSP** 2-sheet |
| `:2422` | `=C{r}*D{r}` (volume × harga) | **Jadwal bulanan** detail |
| `:2494`, `:2982` | `=IF(E>0, E{r}/E{tot}, 0)` (bobot %) | **Jadwal** bulanan/mingguan kurva |

### 1.2 Tegangan dengan keputusan owner
Keputusan **D-RR-06** (Rekap RAB) dan **D-RK-06** (Rekap Kebutuhan) sudah menetapkan:
> *"formula spreadsheet bukan SSOT; nilai resmi berasal dari dataset backend."*

Rumus hidup berisiko **berbeda dari nilai backend** karena:
- Excel menghitung ulang dengan presisi/pembulatan sendiri (mis. `=E*F` pada sel 0-desimal bisa berbeda dari hasil Decimal 2-desimal backend);
- `_convert_volume_formula` memetakan **label parameter → cell**; bila label duplikat/whitespace/alias, mapping bisa salah (ini akar kekhawatiran "K3 label-only/mapping");
- bila satu sel sumber kosong/`-`, rumus dependen menghasilkan angka yang berbeda dari kebijakan backend (yang mungkin "Belum diisi"/"Total sementara").

### 1.3 Opsi
- **Opsi A (rekomendasi) — nilai backend authoritative.** Tulis **nilai hasil kalkulasi backend** ke sel (Decimal→float). Rumus boleh tetap disertakan sebagai **komentar sel** atau sheet sekunder "Rumus" untuk transparansi, tapi nilai yang ditampilkan = backend. Selaras D-RR-06/D-RK-06; layar == export dijamin.
- **Opsi B — pertahankan rumus hidup, jamin parity.** Tambah **contract test**: render rumus via lib (mis. `formulas`/`pycel`) lalu assert hasil == nilai backend untuk fixture kecil/menengah/besar. Lebih rapuh, tetap ada risiko Excel-version-specific.

**Rekomendasi:** Opsi A. Effort sedang, hilangkan kelas bug "layar ≠ file" permanen. `_convert_volume_formula` (Volume) bisa di-*demote* jadi sheet/komentar opsional.

### 1.4 Permukaan regresi
Volume (param formula), Rincian AHSP (E*F/SUM), Jadwal bulanan & mingguan (C*D, bobot). **Tidak** menyentuh Rekap RAB/Kebutuhan (keduanya sudah pakai nilai, bukan rumus, di jalur masing-masing — perlu konfirmasi saat implementasi).

---

## 2. K2 — `parse_number` heuristik locale

### 2.1 Keadaan saat ini
`parse_number` (:31) adalah **parser heuristik** yang menebak apakah `,`/`.` adalah desimal atau ribuan berdasarkan posisi & jumlah digit. Dipakai via `_parse_number` (:1082) di **4 call-site aktif**: `:762/765` + `:986/990` — keduanya di **Rincian AHSP 2-sheet** (kolom 5 koefisien `0.000000`, kolom 6 harga `#,##0`).

### 2.2 Risiko
Heuristik hanya berbahaya bila adapter mengirim **string** (bukan Decimal/float — kalau numeric, `parse_number` langsung `float(value)` di `:51-54`, aman). Kasus ambigu:
- `"150.000"` → ditebak **150000** (titik=ribuan). Bila nilai kanonik sebenarnya koefisien **150,0** (3 desimal), hasilnya salah 1000×.
- `"150,000"` → 150000; padahal bisa jadi `150.0`.

Ini **kelas yang sama** dengan VP-A1 (Volume locale 1000×) yang sudah kita perbaiki di input — tapi di sisi **export**.

### 2.3 Opsi
- **Opsi A (rekomendasi) — adapter kirim Decimal/float kanonik, exporter berhenti mem-parse.** Hilangkan jalur string→heuristik. Exporter terima angka kanonik; `_parse_number` hanya jadi guard tipis (numeric passthrough). Hilangkan tebakan locale sepenuhnya.
- **Opsi B — pertahankan parser, kunci ke Strict id-ID.** Samakan dengan parser input kanonik (`numeric.parse_any`), buang cabang US/Euro yang menimbulkan ambiguitas. Lebih kecil tapi tetap parse string.

**Rekomendasi:** Opsi A — selaras prinsip "nilai resmi dari backend"; exporter tak seharusnya menebak locale. Verifikasi dulu apakah adapter Rincian AHSP mengirim string atau Decimal (bila sudah Decimal, K2 secara praktis **tidak aktif** dan cukup ditambah guard test).

### 2.4 Permukaan regresi
Rincian AHSP 2-sheet (4 call-site). Perlu cek apakah adapter lain memanggil `parse_number` modul (alias `safe_float`) di luar excel_exporter.

---

## 3. Presisi — `number_format`

### 3.1 Keadaan saat ini (distribusi)
| Format | Jumlah | Arti |
|---|---|---|
| `#,##0` | 29 | uang/qty **0 desimal** |
| `#,##0.00` | 5 | uang **2 desimal** |
| `0.000000` | 2 | koefisien 6 desimal |
| `0.00%` / `0.0%` / varian | 57 | bobot/persen kurva |

29 sel uang memakai **0 desimal** sementara nilai kanonik **2 desimal** (temuan **RR-19** Rekap RAB & precision Rincian/RA). Inkonsisten dengan 5 sel `#,##0.00`.

### 3.2 Keputusan owner terkait
**D-RR-04:** *"harga satuan dan total kanonik dua desimal. Dokumen boleh menampilkan rupiah penuh bila presentation policy disepakati."* → presisi adalah **pilihan presentasi yang harus dinyatakan**, lalu diterapkan **konsisten**.

### 3.3 Opsi
- **Opsi A — 2 desimal konsisten** (`#,##0.00` untuk semua sel uang). Cocok nilai kanonik; tidak ada pembulatan presentasi yang menyembunyikan selisih.
- **Opsi B — rupiah penuh 0 desimal sebagai presentation policy resmi**, tapi nilai kanonik (raw/JSON) tetap 2 desimal, dan kebijakan dinyatakan di header laporan.

**Rekomendasi:** putuskan satu kebijakan lalu terapkan ke **29 sel** sekaligus. Default aman: **Opsi A (2 desimal)** kecuali owner memang ingin tampilan rupiah bulat.

---

## 4. Rangkuman & sequencing usulan

| Item | Rekomendasi | Effort | Regresi |
|---|---|---|---|
| **K3** rumus hidup → nilai backend | Opsi A | Sedang | Volume, Rincian, Jadwal bln/mgg |
| **K2** stop parse string di exporter | Opsi A (cek adapter dulu) | Kecil–sedang | Rincian AHSP |
| **Presisi** `#,##0` → konsisten | Opsi A 2-desimal (atau owner pilih) | Kecil | Semua report uang |

**Sequencing aman:**
1. **Verifikasi adapter** (apakah kirim string atau Decimal) — menentukan apakah K2 aktif.
2. **Snapshot regresi**: render fixture kecil/menengah/besar per report → simpan nilai sel acuan **sebelum** ubah.
3. K2 (paling sempit) → K3 → presisi, masing-masing dengan **contract test "layar == file"** per report.
4. Tidak ada perubahan tanpa contract test parity; ini syarat karena modul bersama.

**Belum dieksekusi.** Dokumen ini menunggu pilihan owner untuk K3 (A/B), K2 (A/B), dan presisi (A/B) sebelum implementasi.

---

## 5. Yang SUDAH selesai di WP Export (konteks)
- `str(e)`-leak endpoint **export**: 25 endpoint via `export_error_response` (WP-B5).
- **JDW-19**: kurva/chart API tak bocor exception.
- **RK-23** (commit `09538fbf`): endpoint **data** Rekap Kebutuhan tak bocor `str(e)`.
- Sisa leak yang **sengaja** dibiarkan: `json.JSONDecodeError` import (input user) + legacy tahapan v1 (→ Fase-3).

*Audit oleh Claude, 2026-06-20. Tidak ada perubahan kode pada `excel_exporter.py`.*
