# WP Export — Audit & Dokumen Keputusan K2/K3 (excel_exporter.py)

**Tanggal:** 20 Juni 2026
**Status:** **KEPUTUSAN OWNER DITERIMA 2026-06-20 — semua Opsi A.** Implementasi mengikuti urutan §6.1.

## KEPUTUSAN OWNER (terkunci, 2026-06-20)

Prinsip: **Excel = representasi laporan dari SSOT backend, bukan mesin perhitungan paralel.**

- **K3** — Excel menulis **nilai kanonik hasil backend**, bukan formula hidup. Formula boleh disimpan sebagai informasi tambahan (komentar/sheet sekunder), **bukan** sumber nilai sel resmi.
- **K2** — Adapter menyerahkan **Decimal** langsung ke exporter. Konversi ke tipe Excel dilakukan **di boundary exporter**; **jangan** parsing string locale.
- **Presisi** — **2 desimal konsisten** untuk harga & nilai finansial. Rupiah bulat hanya boleh format presentasi terpisah, **tidak** menghilangkan presisi nilai sel.
- **Kontrak tipe** — Decimal berlaku pada jalur **Python adapter → exporter**. Bila melewati **JSON**, gunakan **string desimal kanonik** (mis. `"1500.00"`), **bukan** float atau string berformat locale.

**Urutan implementasi (owner):**
1. Inventarisasi tipe output seluruh adapter.
2. Tambah contract test: nilai backend → adapter → workbook.
3. Tutup K2 dulu.
4. Ganti formula hidup → nilai backend (K3).
5. Terapkan format 2 desimal.
6. Regresi kelima report + parity "dataset backend = nilai sel Excel".

> Status awal dokumen (di bawah) dipertahankan sebagai catatan audit. Bagian implementasi/progress ditambahkan di §6.x.
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

---

## 6. Implementasi (mengikuti keputusan owner)

### 6.1 Urutan (diulang dari keputusan)
1. Inventarisasi tipe output adapter · 2. Contract test backend→adapter→workbook · 3. K2 · 4. K3 · 5. Presisi 2-desimal · 6. Regresi 5 report + parity.

### 6.2 LANGKAH 1 — Inventarisasi tipe output adapter (SELESAI 2026-06-20)

**Temuan utama: setiap adapter punya `_format_number(value, decimals) -> str` yang menghasilkan STRING berformat id-ID** (`f"{x:,.2f}"` lalu swap `,`↔`.` → mis. `"1.500.000"` / `"1.500,50"`). Akibatnya angka kanonik di-*downgrade* jadi string presentasi **di adapter**, lalu exporter harus mem-parse ulang / menulis sebagai teks.

| Adapter | Tipe numerik dikirim | Jalur exporter | Masalah |
|---|---|---|---|
| **Rekap RAB** (`:123-181`) | `_format_number(volume,3)`, `_format_number(harga,0)`, `_format_number(jumlah,0)` = **string id-ID** | `export()` generic → `ws.cell(value=str)` | Sel = **TEKS** di Excel (tak bisa dijumlah), presisi hilang di `decimals=0` |
| **Rekap Kebutuhan** | `_format_number(...)` = string | `export()` generic | sama (teks, presisi hilang) |
| **Harga Items** | `_format_number(...)` = string | `export()` generic | sama |
| **Rincian AHSP** (`:169-246`) | `_format_number(subtotal,0)`, `f"{eff:.2f}"` = string | `_export_rincian_ahsp_2sheet` → `_parse_number` (**K2 heuristik**) + formula `=E*F` (**K3**) | round-trip lossy + formula≠backend |
| **Volume** | campuran string `_format_number` + `_convert_volume_formula` (**K3**) | `export_volume_pekerjaan` → `_parse_number` (**K2**) | sama |
| **Jadwal** (`:1180-1282`) | **campur**: `float(volume)`, `float(harga)` (OK-ish) + `_format_number(volume,3)` string utk `*_display` + formula `=C*D`/bobot (**K3**) | `export_professional/monthly/weekly` | float kehilangan presisi Decimal; display string; formula |

**Kesimpulan inventaris:**
1. **Akar tunggal**: adapter memformat angka jadi **string id-ID** (sering `decimals=0` → presisi hilang **sebelum** sampai exporter). Ini menyebabkan K2 (exporter mem-parse ulang) **dan** kasus lebih buruk (jalur generic menulis string sebagai **teks sel**).
2. **K3** (formula hidup) menumpuk di atasnya untuk Rincian/Volume/Jadwal.
3. **Jadwal** memakai `float()` (bukan Decimal) → kehilangan presisi & melanggar kontrak owner "Decimal pada jalur adapter→exporter".

**Implikasi desain (sesuai kontrak owner):**
- Adapter harus mengirim **`Decimal` kanonik** (atau **string desimal kanonik** `"1500.00"` bila lewat JSON), **bukan** hasil `_format_number`.
- `_format_number` (string id-ID) **hanya** untuk sel label/teks non-data atau format presentasi terpisah — bukan untuk nilai data.
- Boundary konversi **Decimal→tipe Excel** + `number_format='#,##0.00'` dilakukan **di exporter** (satu tempat).
- `_parse_number`/`parse_number` (K2) di exporter di-pensiun untuk jalur data; sisakan guard tipis numeric-passthrough.
- Formula hidup (K3) diganti nilai; rumus boleh jadi komentar/sheet sekunder.

### 6.3 Desain boundary (keputusan owner 2026-06-20)
**`column_formats` metadata per report.** Adapter mengirim **Decimal** di sel + `table_data.column_formats` (mis. `['@','@','@','#,##0.000','#,##0.00','#,##0.00']`) + opsional `footer_value_format`. Exporter (`_write_value_cell`) menulis `float(Decimal)` + stamp `number_format` per kolom. **Backward-compatible**: report tanpa metadata = perilaku lama → migrasi **satu report per slice**.

### 6.4 Progress slice (vertical, tiap report parity-tested)

| Report | Status | Catatan |
|---|---|---|
| **Rekap RAB** | ✅ SELESAI (`e2d7b85e`) | adapter Decimal + `column_formats`; exporter boundary; manager propagasi 2 page; parity web==export diperkuat exact-Decimal |
| **Harga Items** | ✅ SELESAI (`4ce0870f`) | Satuan Dasar harga→Decimal 2dp; NULL→`'-'` tetap beda dari `0.00` (D-HI-01); konversi page = narasi by-design |
| **Rekap Kebutuhan** | ✅ SELESAI (`0e27a719`) | Qty 3dp + harga/total 2dp Decimal; grand-total footer numeric; scheduled/unscheduled & total tak berubah |
| **Rincian AHSP** | ✅ SELESAI (`786d2834`) | hapus `=E*F`/`=SUM`/E-F-G formula + cross-ref `=Rincian!` + `_parse_number`; adapter Decimal; Rekap sheet pakai nilai (refs bawa value); gate **no `data_type='f'`** |
| **Volume** | ✅ SELESAI (`33e0dfe0`) | nilai numeric kanonik (`VolumePekerjaan.quantity`); rumus = teks audit; computed param Nilai=`-`/Expression teks (Opsi C); `_convert_volume_formula` di-retire (reserved "Template Kalkulasi") |
| Jadwal | ⏳ terakhir | `float()`→Decimal + K3 `=C*D`/bobot (monthly/weekly/professional) |

### 6.5 Temuan penting — boundary teks-exporter (PDF/Word/CSV)
Adapter dipakai **semua format**, bukan hanya Excel. PDF (`pdf_table_builder` `Paragraph(str(...))`) + Word + CSV merender sel via `str(...)`. Saat adapter beralih ke Decimal, mereka akan menampilkan `str(Decimal)` = `"1500000.00"` (kehilangan grouping). **Keputusan owner (2026-06-20): 2 desimal konsisten semua format.**

Solusi: `exports/cell_format.py` → `materialize_display_rows(data)` memformat sel Decimal pada tabel ber-`column_formats` jadi string id-ID 2dp, dipanggil di awal `export()` PDF/Word/CSV (Excel TIDAK — pakai Decimal numeric langsung). Tabel tanpa `column_formats` (report belum dimigrasi) lewat tanpa diubah → aman. Boundary ini juga mengamankan PDF/Word/CSV untuk RAB & Harga yang sudah dimigrasi.

### 6.6 Gate setelah Harga + Kebutuhan (SELESAI 2026-06-20)
- ✅ Seluruh test export jalan: **121 PASS**.
- ✅ PDF/Word tidak rusak: boundary materialize → Word render test assert `"220,00"`/`"660,00"` (bukan `"220.00"` mentah).
- ✅ Tidak ada `_format_number()` pada **raw data output** kedua adapter (page-1 harga & rows kebutuhan). Narasi konversi Harga + footer label = prosa by-design.
- ✅ Workbook menyimpan **numeric cell**, bukan string id-ID (parity test Excel).

**Pola reusable**: Excel `_write_value_cell` + text `materialize_display_rows`, dipandu `column_formats`/`footer_value_format`.

### 6.7 Slice 4 — Rincian AHSP (SELESAI 2026-06-20, commit kode `786d2834`)
Blast radius terbesar (jalur exporter khusus `_export_rincian_ahsp_2sheet`, bukan generic):
- **Excel**: sebelumnya tiap baris `=E{r}*F{r}`, subtotal `=SUM(...)`, E/F/G chain formula, dan **sheet "Rekap" pakai cross-ref `=Rincian!G..`**. Semua diganti **nilai kanonik backend** via `_write_value_cell`; `pekerjaan_refs` kini membawa `e_val/f_val/g_val` (bukan alamat sel). `_parse_number` dibuang dari jalur ini.
- **Adapter**: `groups[].rows` (koef/harga/jumlah), `subtotal`, `totals{E,F,G,markup_eff}`, `pekerjaan.total`, `recap.rows`, `summary` → Decimal kanonik. `detail_table` + `recap` deklarasi `column_formats` (Koef `#,##0.000000`, uang `#,##0.00`).
- **PDF/Word/CSV**: `materialize_display_rows` dapat cabang `sections`/`recap`/`summary` (`_materialize_rincian`) → format id-ID 2dp.
- **Formula**: dihapus total (bukan dijadikan komentar) — paling bersih utk gate "bukan nilai sel".

**Gate Rincian (semua ✅):** parity backend→adapter→workbook (komponen koef/harga/jumlah + E/F/G); **tak ada sel `data_type='f'`** (di-assert lintas semua sheet); explicit-zero numeric (None→0 coercion lama Rincian dipertahankan, beda dari Harga Items yg NULL→`-`); markup default/override + bundle expanded tak berubah (tetap dari canonical rekap + `bundle_totals`); **123 export test PASS**; Word render `"220,00"` (bukan `"220.00"`).

**Berikutnya — Volume** (slice tersendiri): lihat §6.8 (mapping read-only).

### 6.8 EVALUASI VOLUME — Mapping (read-only, 2026-06-20; belum ubah kode)

**Keputusan desain owner (2026-06-20):** Nilai Volume = numeric backend (resmi). Rumus Input = teks/audit (kolom "Rumus Volume"). Parameter = sheet terpisah nama/label/nilai kanonik. `_convert_volume_formula()` **tidak lagi** hasilkan formula Excel hidup di laporan resmi. Bila kelak butuh file yang dapat dihitung-ulang → tipe export **terpisah "Template Kalkulasi"**, bukan laporan Volume resmi.

**(1) Bentuk formula & parameter didukung**
- Formula disimpan pakai **opaque code** (`bp_N` base, `cp_N` computed); operator `+ - * / ^ ( )` + fungsi `sum/min/max/round/avg/abs/floor/ceil/pow`. `_humanize_formula`→`remap_expression` ubah code→label utk display.
- **Base param** `ProjectParameter(name,label,value,unit)` — **punya `value`**. **Computed param** `ProjectComputedParameter(name,label,expression,unit)` — **TIDAK punya field value** (hanya expression).

**(2) Semua pemanggil `_convert_volume_formula()`** (semua di `excel_exporter.py`):
| Baris | Konteks | Status target |
|---|---|---|
| `:446` | **kolom Volume** → formula hidup (nilai resmi jadi `=Parameters!..`) | **GANTI ke nilai numeric backend (vol_map)** |
| `:346/:348` | **kolom Value param** (computed) → formula hidup | **GANTI ke nilai kanonik** (lihat blocker) |
| `:431` | kolom Formula saat `formula_display_mode != 'label'` | **inactive** (adapter set `'label'` → cabang `:437` apostrophe = teks). Bisa di-retire |
| `:502` | definisi | retire dari jalur resmi; simpan utk "Template Kalkulasi" |

**(3) Nilai backend kanonik tersedia?**
- **Volume**: ✅ `VolumePekerjaan.quantity` (`vol_map`, sudah di adapter `:207`) — nilai resmi tersimpan, **bukan** hasil recompute formula.
- **Base param**: ✅ `ProjectParameter.value` (`name_to_value`).
- **Computed param**: ❌ **TIDAK tersedia server-side.** Tak ada field cache, tak ada evaluator server (tokenizer hanya tokenize/remap; evaluasi `evaluateComputedParams` ada di **frontend**). Payload `?params=` opsional & sering kosong → computed value default **0**. **Saat ini nilai computed "benar" di Excel HANYA karena formula hidup** — persis anti-pola yang owner ingin hapus.

**(4) Struktur sheet pertahankan formula sebagai teks** — SUDAH ADA:
- Sheet "Volume Pekerjaan": kolom `[No, Uraian, Formula, Satuan, Volume]`. Kolom **Formula** (col 3) di mode `'label'` ditulis text-prefixed `'=...` (`:437`) → tak dievaluasi Excel. = kolom "Rumus Volume" yang owner mau.
- Sheet "Parameters" (appendix): `[No, Label, Value, Unit]` + `param_codes`/`param_formulas`/`_parameter_cells`.
- Jadi struktur owner (Rumus teks + Nilai numeric + Parameter sheet) **sudah ada**; tinggal hentikan konversi formula hidup pada Volume-value & computed-value.

**(5) Rencana contract test** (formula-text + numeric-result parity):
- Kolom Volume = **numeric** == `VolumePekerjaan.quantity` (3 dp), `data_type='n'`.
- Kolom Formula = **teks** `"=panjang*lebar"` (humanized), `data_type='s'`, **bukan** `'f'`.
- **Tak ada sel `data_type='f'`** di sheet manapun (Volume + Parameters).
- Param value = numeric kanonik (base dari `value`; computed lihat blocker).
- PDF/Word/CSV via `materialize_display_rows` (tambah `column_formats`: Volume `['@','@','@','@','#,##0.000']`, Param `['@','@','#,##0.00','@']`).

**⛔ BLOCKER DESAIN — sumber nilai kanonik computed-param.** Untuk menulis VALUE (bukan formula hidup) computed-param, butuh salah satu:
- **(A)** Evaluator computed-param **server-side** (tokenizer sudah ada; tambah evaluator yang resolve graf `cp_*` dari `bp_*` value + fungsi). Paling kokoh & sejalan "Excel=laporan SSOT backend".
- **(B)** Endpoint export **wajib terima** nilai ter-evaluasi dari client (`?params=` selalu diisi frontend). Lebih cepat tapi mengikat export ke state client (rapuh; tak konsisten "nilai resmi dari backend").
- **(C)** Laporan resmi tampilkan **expression saja** utk computed (tanpa value, atau "—") sampai (A) tersedia. Degraded tapi aman (tak ada formula hidup, tak ada nilai salah).

Rekomendasi: **(A)** — selaras kontrak SSOT. Bila (A) di luar scope slice ini, **(C)** sebagai langkah aman sementara (jangan (B)).

**Catatan precision param value**: base param `_format_number(value,2)` (2dp) saat ini. Perlu konfirmasi: param value 2dp cukup, atau presisi penuh? (param bisa integer/desimal panjang).

### 6.9 Slice 5 — Volume (SELESAI 2026-06-20, kode `33e0dfe0`)
**Keputusan owner (final, Opsi C diperketat):** TIDAK bangun evaluator baru, TIDAK pakai nilai computed dari frontend.
- **Base param** → nilai numeric dari backend (`ProjectParameter.value`, **bukan** payload `?params=`).
- **Computed param** → kolom **Expression** = formula teks (humanized); kolom **Nilai** = `-` (jangan 0 = kesan resmi salah; jangan formula hidup).
- **Volume pekerjaan** → numeric dari `VolumePekerjaan.quantity` (kanonik tersimpan, 3dp).
- `_convert_volume_formula()` **di-retire** dari laporan resmi (0 caller; disimpan untuk WP "Template Kalkulasi" mendatang).
- Nilai computed-param resmi → **WP terpisah "Canonical Formula Evaluation Service"** (dipakai page Volume + validasi save + export sekaligus, dengan parity test JS↔server). **Jangan** bikin evaluator khusus exporter.

**Implementasi:** Parameters sheet jadi 5 kolom `[No, Nama, Expression, Nilai, Satuan]` + `column_formats`; Volume sheet Volume→Decimal 3dp + `column_formats`; exporter tulis numeric via `_write_value_cell`, Formula tetap text-prefixed; PDF/Word/CSV lewat `materialize_display_rows` (jalur `pages`).

**Gate (semua ✅):** Volume cell `data_type='n'` == quantity; base param numeric == backend (bukan payload 12); computed Nilai `-`; **tak ada sel `data_type='f'`** (di-assert 2 sheet); Word render `"125,500"`; **135 export test PASS**. Test lama yang meng-assert anti-pola live-formula **di-rewrite** ke kontrak baru.

### 6.10 Status WP Export
**5 dari 6 report SELESAI**: Rekap RAB, Harga Items, Rekap Kebutuhan, Rincian AHSP, Volume. **Sisa: Jadwal** (`float()`→Decimal + K3 `=C*D`/bobot di 3 metode professional/monthly/weekly — sheet Kurva-S/SSOT). **Backlog terpisah (bukan WP Export):** Canonical Formula Evaluation Service (nilai computed-param resmi, parity JS↔server) + "Template Kalkulasi" export type (workbook editable dgn formula hidup).

---

## 7. Lapisan Kontrol Formula (forward implementation, 2026-06-20)

**Perubahan arah owner:** pertahankan formula Excel native sebagai **lapisan kontrol/audit** — BUKAN revert. Sheet utama tetap nilai backend (K2/presisi/no-formula tetap berlaku); formula ditambahkan kembali di **sheet terpisah** yang menghitung ulang lalu membandingkan. Riwayat Git = sumber kode converter lama, bukan untuk memulihkan desain lama.

**Keputusan owner (2026-06-20):** penempatan = **sheet "Kontrol Kalkulasi" di dalam file resmi**; pilot = **Rincian AHSP**.

**Pilot Rincian AHSP — SELESAI (commit `62c688e3`).** Sheet ke-3 "Kontrol Kalkulasi" per pekerjaan:
| Kolom | Isi |
|---|---|
| Nilai Resmi | G backend (numeric) |
| Nilai Kontrol | formula hidup `=Rincian!{E}+Rincian!{F}` (Excel recompute dari sheet resmi) |
| Selisih | `=Resmi-Kontrol` |
| Status | `=IF(ABS(Selisih)<0.01,"OK","PERIKSA")` |

Section writer kembali melacak alamat sel E/F/G (di samping nilai) agar formula kontrol menunjuk sel yang benar. Hasil formula kontrol **tak pernah** dipakai import/perhitungan aplikasi.

**Gate:** sheet resmi (Rincian, Rekap) tetap **tanpa sel `data_type='f'`** (test no-`f` kini meng-exclude "Kontrol Kalkulasi"); test baru memastikan kolom kontrol = formula, menunjuk sel E/F Rincian, dan rekonsiliasi (E+F == G resmi → Status OK). **136 export test PASS**.

**Aturan lapisan kontrol (berlaku semua report):**
- Sheet utama = nilai backend kanonik (tak berubah).
- Sheet "Kontrol Kalkulasi" = formula hidup referensi eksplisit + diuji.
- Hasil formula kontrol TIDAK dipakai import/perhitungan.

**Sisa rollout lapisan kontrol:** Rekap RAB (kontrol = Σ(volume×harga)+PPN vs grand total — formula 100% baru), Jadwal (Σbobot vs 100% / Σperiode vs total — converter `=C*D`/bobot dari riwayat). **Volume:** laporan resmi tetap; converter `_convert_volume_formula` (di-retire, tersedia di `33e0dfe0^`) → tipe export **"Template Kalkulasi"** terpisah (bukan sheet kontrol).
