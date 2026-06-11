# Review: Fitur Parameter & Formula Parameter -- Volume Pekerjaan

**Tanggal Review:** 11 Februari 2026
**Reviewer:** Tim Engineering Internal
**Scope:** Parameter Perhitungan (Base Parameter & Formula/Computed Parameter) pada halaman Volume Pekerjaan
**Versi Dokumen:** v1.2 (revisi berdasarkan feedback)
**Status:** ARSIP -- Section 1-4 tetap berlaku sebagai dokumentasi analisis.
Section 5-10 (rekomendasi, roadmap, rollback, test matrix, input contract)
telah di-supersede oleh **IMPLEMENTATION_PLAN_OPAQUE_ID.md** yang mengadopsi
pendekatan Opaque ID sebagai pengganti kode deskriptif.

---

## DAFTAR ISI

1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Arsitektur Saat Ini](#2-arsitektur-saat-ini)
3. [Analisis Masalah Penamaan & Pemanggilan Parameter](#3-analisis-masalah-penamaan--pemanggilan-parameter)
4. [Temuan & Kelemahan Detail](#4-temuan--kelemahan-detail)
5. [Rekomendasi Pengembangan & Penyempurnaan](#5-rekomendasi-pengembangan--penyempurnaan)
6. [Roadmap Prioritas (dengan Acceptance Criteria)](#6-roadmap-prioritas)
7. [Rollback Plan: Fitur Rename Kode](#7-rollback-plan-fitur-rename-kode)
8. [Test Matrix Karakter](#8-test-matrix-karakter)
9. [Input Contract & Error Handling](#9-input-contract--error-handling)
10. [Lampiran](#10-lampiran)

---

## 1. Ringkasan Eksekutif

Fitur Parameter & Formula pada halaman Volume Pekerjaan sudah cukup matang secara teknis. Namun, terdapat **masalah fundamental pada alur penamaan parameter** yang menyebabkan kebingungan user:

**Masalah Utama:**
- User membuat parameter dengan **label ramah** (misal: "Panjang Dinding Lantai 1"), tetapi yang digunakan dalam formula adalah **kode otomatis** (`panjang_dinding_lantai_1`) yang dibuat dari slugifikasi label.
- **Tidak ada UI eksplisit** untuk user melihat/memilih/mengedit kode parameter secara langsung -- kode hanya ditampilkan sebagai hint kecil.
- User harus **mengingat atau menyalin kode** secara manual untuk menulis formula, padahal kode bisa sangat panjang dan tidak intuitif.
- Ketika label diubah, **kode tidak berubah** (immutable setelah dibuat), sehingga bisa terjadi mismatch antara label yang terlihat dan kode yang dipakai di formula.

**Bug Critical Teridentifikasi:**
- Edit label pada Computed Parameter menyebabkan **kode ikut berubah** (`nextCode = slugifyName(nextLabel)` di `volume_pekerjaan.js:1847`), sehingga formula lain yang referensi kode lama langsung **rusak tanpa warning**.

---

## 2. Arsitektur Saat Ini

### 2.1 Data Model (Backend)

**`ProjectParameter`** (`detail_project/models.py:985-1038`)

| Field       | Type             | Keterangan                                                   |
|-------------|------------------|--------------------------------------------------------------|
| `name`      | CharField(100)   | Kode parameter (lowercase, underscore, auto-generated)       |
| `value`     | DecimalField(18,3)| Nilai numerik (min >= 0)                                    |
| `label`     | CharField(200)   | Label tampilan UI (ramah user)                               |
| `unit`      | CharField(50)    | Satuan (meter, m2, dll)                                      |
| `description`| TextField       | Deskripsi opsional                                           |

**`ProjectComputedParameter`** (`detail_project/models.py:1057-1116`)

| Field       | Type             | Keterangan                                                   |
|-------------|------------------|--------------------------------------------------------------|
| `name`      | CharField(100)   | Kode formula turunan (lowercase)                             |
| `expression`| TextField        | Formula (misal: `panjang_l1 * lebar_l1`)                     |
| `label`     | CharField(200)   | Label tampilan UI                                            |
| `unit`      | CharField(50)    | Satuan output                                                |
| `description`| TextField       | Deskripsi opsional                                           |

### 2.2 Alur Data (Client <-> Server)

```
+-----------------------------------------------------------+
|                     BROWSER (Client)                       |
|                                                           |
|  localStorage <-> variables{} / varLabels{} / computedParams{}
|       |                        |                          |
|       v (load/save)           v (debounced 2s)            |
|  Render UI <-------- syncParamsToServer() -------> Server |
|                      syncComputedParamsToServer()         |
|                                                           |
|  Pada init:                                               |
|  1. Load dari localStorage (instant, fallback)            |
|  2. Fetch dari server (async, AUTHORITATIVE)              |
|  3. Server data menimpa localStorage + re-render          |
|     (variables = serverParams) -- JS line 2872            |
+-----------------------------------------------------------+
```

**Catatan (koreksi v1.1):** Saat fetch server berhasil, server data **menimpa penuh** state client (`variables = serverParams`, bukan merge). Ini sudah benar sebagai "server authoritative". Masalah muncul hanya pada **arah sebaliknya**: sync dari client ke server menggunakan `mode: "merge"` (line 2808) sehingga parameter yang dihapus di client tidak terhapus di server.

### 2.3 Alur Penamaan Parameter (Saat Ini)

```
User input label: "Panjang Dinding Lt. 1"
         |
         v
normalizeParamCode() / slugifyName()
         |
         v
Kode otomatis: "panjang_dinding_lt_1"
         |
         v
Disimpan sebagai `name` di DB + key di variables{}
         |
         v
Ditampilkan di UI: "Kode: panjang_dinding_lt_1" (hint kecil)
         |
         v
User harus mengetik: = panjang_dinding_lt_1 * lebar * tinggi
```

### 2.4 Fungsi `normalizeParamCode()` (JS line 1584-1596)

```javascript
function normalizeParamCode(s) {
    let t = String(s || '').trim();
    t = t
      .replace(/['\u2018\u2019\u2032\u02BC`\u00B4]+/g, '_prime_')
      .normalize('NFKD')
      .replace(/[^A-Za-z0-9_]+/g, '_')
      .toLowerCase();
    if (/^[0-9]/.test(t)) t = '_' + t;
    t = t.replace(/_+/g, '_').replace(/^_+|_+$/g, '');
    return t || '_param';
}
```

**Catatan:** Fungsi ini memproduksi kode dari label. Hasilnya bisa sangat panjang dan tidak ramah user jika label bersifat deskriptif. Lihat [Test Matrix Karakter](#8-test-matrix-karakter) untuk daftar lengkap perilaku per-karakter.

---

## 3. Analisis Masalah Penamaan & Pemanggilan Parameter

### 3.1 Masalah: Kode Otomatis Tidak Intuitif

| Label User                  | Kode yang Dihasilkan       | Masalah                            |
|-----------------------------|----------------------------|------------------------------------|
| "Panjang Dinding Lantai 1"  | `panjang_dinding_lantai_1` | Terlalu panjang untuk formula      |
| "Lebar (m)"                 | `lebar_m`                  | Unit masuk ke kode                 |
| "D4'"                       | `d4_prime`                 | Perubahan karakter tak terduga     |
| "Koef. Beton K-300"         | `koef_beton_k_300`         | Titik dan tanda hubung dihilangkan |
| "Tinggi 2,5m"               | `tinggi_2_5m`              | Koma desimal jadi underscore       |

### 3.2 Masalah: Kode Tidak Bisa Diedit Setelah Dibuat (Base Parameter)

- Kode (`name`) adalah **primary identifier** yang digunakan sebagai key di `variables{}`, sebagai reference di formula, dan sebagai `unique_together` di database.
- Setelah parameter dibuat, **kode tidak bisa diubah** melalui UI.
- Jika user ingin kode berbeda, harus **hapus dan buat ulang** parameter -- semua formula yang referensi kode lama akan **rusak**.

### 3.3 Masalah: Autocomplete Menampilkan Label tapi Insert Kode

Di autocomplete suggestion (`showSuggest()`), user melihat:
```
Panjang Dinding Lantai 1 (panjang_dinding_lantai_1)    10
```
Tapi yang diinsert ke formula adalah **kode** (`panjang_dinding_lantai_1`).

**Gap mental:** User berpikir dalam terminologi label tapi harus menulis/debug dalam terminologi kode.

**Catatan (koreksi v1.1):** Autocomplete sudah mendukung fuzzy matching via `indexOf` scoring (bukan startsWith saja). Lihat `volume_pekerjaan.js:1033` -- matching dilakukan pada `name` DAN `label` dengan scoring berbeda (exact > startsWith > indexOf). Namun masalah UX gap tetap ada karena yang diinsert tetap kode, bukan label.

### 3.4 Masalah: Tidak Ada Validasi Preview Kode Saat Input Label

Saat user mengetik label di form "Tambah Parameter", **kode yang akan dihasilkan tidak ditampilkan secara real-time**. User baru tahu kodenya setelah klik "Simpan", dan saat itu sudah terlambat untuk mengubah.

### 3.5 Masalah: Formula Preview Menunjukkan Nilai, Bukan Label

`buildFormulaPreview()` mengganti kode dengan **nilai numerik**:
```
Formula:  = panjang * lebar * tinggi
Preview:  10 * 5 * 3 = 150
```
Ini berguna untuk verifikasi angka, tapi **tidak membantu** user memahami kode mana yang merujuk ke parameter mana jika user tidak hafal pemetaan kode <-> label.

### 3.6 Masalah: Sinkronisasi Client -> Server Tidak Hapus Parameter

- Parameter sync ke server menggunakan `mode: "merge"` (line 2808).
- Mode merge hanya **update existing + create new**, tapi **tidak menghapus** parameter yang sudah di-delete di client.
- Akibatnya: parameter "zombie" bisa muncul kembali saat page reload (karena server authoritative, line 2872).
- **Catatan (koreksi v1.1):** Arah server -> client sudah benar (server authoritative, full replace). Masalah hanya pada arah client -> server yang menggunakan merge.

---

## 4. Temuan & Kelemahan Detail

### 4.1 UX Issues

| #   | Temuan                                                                                                    | Severity   | Referensi                          |
|-----|-----------------------------------------------------------------------------------------------------------|------------|------------------------------------|
| U1  | Kode parameter dibuat otomatis tanpa konfirmasi user                                                      | **High**   | `volume_pekerjaan.js:1924-1943`    |
| U2  | Tidak ada live preview kode saat input label baru                                                         | **High**   | `volume_pekerjaan.js:1901-1906`    |
| U3  | Kode tidak bisa diedit setelah parameter dibuat                                                           | **High**   | `volume_pekerjaan.js:1648-1658`    |
| U4  | Hint kode terlalu kecil (`<small class="text-muted">`)                                                   | **Medium** | `volume_pekerjaan.js:1632`         |
| U5  | Rename label tidak update kode -- mismatch berkembang                                                     | **High**   | `volume_pekerjaan.js:1649-1658`    |
| U6  | Tidak ada fitur "rename kode" yang aman (cascade update formula)                                          | **High**   | -                                  |
| U7  | Tidak ada "palette" untuk browse semua parameter (autocomplete hanya muncul saat mengetik formula)        | **Medium** | `volume_pekerjaan.js:1006-1050`    |
| U8  | Tidak ada indikator formula mana yang menggunakan parameter tertentu (usage tracking)                     | **Medium** | -                                  |
| U9  | Tidak ada grouping/kategori parameter (misal: per-lantai, per-zona)                                       | **Low**    | -                                  |
| U10 | Bantuan formula modal terlalu sederhana -- tidak menampilkan daftar parameter aktif                       | **Medium** | `volume_pekerjaan.html:444-486`    |

### 4.2 Technical Issues

| #   | Temuan                                                                                                                                    | Severity     | Referensi                          |
|-----|-------------------------------------------------------------------------------------------------------------------------------------------|--------------|------------------------------------|
| T1  | `normalizeParamCode()` bisa menghasilkan kode duplikat dari label berbeda (misal: "Panjang (m)" dan "Panjang m" -- keduanya `panjang_m`) | **High**     | `volume_pekerjaan.js:1584-1596`    |
| T2  | Computed parameter edit mengubah kode jika label diubah (`nextCode = slugifyName(nextLabel)`) -- break formula lain tanpa warning          | **Critical** | `volume_pekerjaan.js:1847`         |
| T3  | Formula state (raw formula per-pekerjaan) masih dual-storage tanpa clear conflict resolution                                               | **Medium**   | `volume_pekerjaan.js:1052-1065`    |
| T4  | `evaluateComputedParams()` dependency resolution iteratif -- complex chains sudah ditangani via loop+guard, tapi cyclic dependency hanya di-log tanpa UI feedback yang jelas | **Low**      | `volume_pekerjaan.js:946-1004`     |
| T5  | Parameter sync client->server menggunakan `merge` mode -- deleted params di client **tidak dihapus** di server, menyebabkan "zombie" params | **High**     | `volume_pekerjaan.js:2808`         |
| T6  | Tidak ada server-side validation untuk formula expression (bisa store formula yang error)                                                  | **Low**      | `views_api.py:3078-3159`           |
| T7  | `ProjectParameter.value` hanya `MinValueValidator(0)` -- negatif tidak diperbolehkan, tapi konstruksi memerlukan nilai negatif (elevasi, offset) | **Medium**   | `models.py:1010`                   |

### 4.3 Data Integrity Issues

| #   | Temuan                                                                               | Severity     |
|-----|--------------------------------------------------------------------------------------|--------------|
| D1  | Rename computed parameter label menyebabkan kode berubah, TANPA cascade update formula yang referensi kode lama | **Critical** |
| D2  | Delete parameter TIDAK memberikan peringatan jika kode dipakai di formula aktif      | **High**     |
| D3  | Import parameter (JSON/CSV/XLSX) bisa overwrite existing tanpa undo                  | **Medium**   |
| D4  | Computed parameter expression tidak di-validasi terhadap keberadaan base parameter    | **Medium**   |

---

## 5. Rekomendasi Pengembangan & Penyempurnaan

### 5.1 [CRITICAL] Fix Rename Computed Parameter -- Kode Immutable + Rename Aman dengan Cascade

**Masalah yang diselesaikan:** T2, D1, U6

**Ini adalah item implementasi pertama dan paling urgent.**

**Kondisi saat ini (bug):**
```javascript
// volume_pekerjaan.js:1847
const nextCode = slugifyName(nextLabel);  // <-- kode berubah mengikuti label!
if (nextCode !== code && ...) { ... }
// Lalu kode lama dihapus dari computedParams, kode baru dibuat
// Formula lain yang referensi kode lama --> RUSAK
```

**Perbaikan yang diperlukan:**

**Tahap A -- Stabilkan (mencegah kerusakan):**
- Ubah perilaku edit computed parameter: **edit label TIDAK boleh mengubah kode**.
- Kode hanya bisa diubah melalui aksi "Rename Kode" yang eksplisit.

**Tahap B -- Rename Kode dengan Cascade:**
- Saat user memilih "Rename Kode", sistem:
  1. Scan semua formula quantity di `rawInputById` + semua `computedParams[*].expression` untuk menemukan penggunaan kode lama.
  2. Tampilkan confirmation dialog dengan daftar formula yang terpengaruh:
     ```
     Rename kode "area_l1" -> "luas_lt1"

     Formula yang akan diperbarui:
     - Computed: volume_l1 (expression: area_l1 * tinggi_l1)
     - Pekerjaan #42: = area_l1 * 2
     - Pekerjaan #55: = area_l1 + area_l2

     [Rename & Update Semua]  [Batal]
     ```
  3. Lakukan batch replace berbasis **token identifier** (bukan regex text replace):
      ```javascript
     // Pseudocode: parse -> transform ID token -> render ulang expression
     const tokens = VolFormulaTokenizer.tokenize(oldExpr);
     const patched = tokens.map((t) => {
       if (t.type === 'id' && t.value === oldCode) return { ...t, value: newCode };
       return t;
     });
     newExpr = VolFormulaTokenizer.stringify(patched);
      ```
  4. Update di semua tempat: `variables{}`, `varLabels{}`, `computedParams{}`, `rawInputById{}`.
  5. Sync perubahan ke server (parameters/sync + computed-parameters/sync + formula-state).
  
**Catatan:** Method final rename cascade harus mengikuti [Section 9.6](#96-rename-cascade-wajib-token-level-bukan-text-replace-buta).

**Rollback plan:** Lihat [Section 7](#7-rollback-plan-fitur-rename-kode).

### 5.2 [CRITICAL] Pisahkan Kode dan Label -- User Bisa Set Kode Sendiri

**Masalah yang diselesaikan:** U1, U2, U3, U5

**Rancangan:**
- Saat menambah parameter, sediakan **dua input field**:
  - **Label** (wajib): Nama deskriptif, bebas spasi/karakter -- `"Panjang Dinding Lt. 1"`
  - **Kode** (opsional, auto-fill dari label): Identifier untuk formula -- `"p_dd_l1"` (user bisa edit)
- Tampilkan **live preview kode** saat user mengetik label.
- Jika user mengosongkan kode, auto-generate dari label.
- Berikan **validasi real-time**: warna merah jika kode duplikat, format invalid, dll.

**Perubahan UI:**
```
+------------------------------------------+
| Tambah Parameter                         |
+------------------------------------------+
| Label:  [Panjang Dinding Lt. 1        ]  |
| Kode:   [p_dd_l1                      ]  |  <-- editable, auto-fill, live validation
|         [v] Tersedia - "= p_dd_l1 * ..."  |  <-- real-time feedback
| Nilai:  [12,500                        ]  |
| Satuan: [meter                         ]  |  <-- field baru yang lebih prominent
|                                          |
|         [Simpan]  [Batal]                |
+------------------------------------------+
```

### 5.3 [HIGH] Fix Sync Mode: Ganti Merge ke Replace untuk Delete Propagation

**Masalah yang diselesaikan:** T5

**Perubahan:**
```javascript
// SEBELUM (volume_pekerjaan.js:2808):
const res = await HTTP.jpost(EP_PARAMS_SYNC, {
    parameters: params,
    mode: 'merge'   // <-- delete tidak propagate
});

// SESUDAH:
const res = await HTTP.jpost(EP_PARAMS_SYNC, {
    parameters: params,
    mode: 'replace'  // <-- full replace, delete juga tersync
});
```

**Catatan:** Mode `replace` sudah tersedia di backend (`views_api.py:2977-3001`). Hanya perlu ubah 1 baris di client.

### 5.4 [HIGH] Warning Saat Hapus Parameter yang Masih Digunakan

**Masalah yang diselesaikan:** D2

**Rancangan:**
- Sebelum menghapus parameter, scan semua:
  1. Formula quantity di semua pekerjaan (`rawInputById`)
  2. Expression di semua Computed Parameter (`computedParams`)
- Jika kode ditemukan, tampilkan peringatan:
  ```
  [!] Parameter "panjang" digunakan di:
  - 3 formula pekerjaan
  - 1 formula turunan (area_l1)

  Hapus akan menyebabkan error pada formula tersebut.
  [Hapus Tetap]  [Batal]
  ```

### 5.5 [HIGH] Perbaiki Autocomplete & Parameter Palette

**Masalah yang diselesaikan:** U7, U4

**Catatan (koreksi v1.1):** Autocomplete sudah mendukung scoring berbasis indexOf (bukan startsWith saja, lihat JS line 1022-1045). Yang perlu diperbaiki:

- **Parameter Palette** (Ctrl+Shift+P atau button di toolbar):
  - Modal/dropdown yang menampilkan **semua parameter** dengan kolom: Label | Kode | Nilai | Satuan.
  - User bisa klik untuk **copy kode** ke clipboard.
  - Search/filter di dalam palette.
- **Perbaikan Autocomplete:**
  - Saat mengetik di formula, perkuat visual format:
    ```
    Panjang Dinding Lt.1   p_dd_l1   12.500 m
    ```
  - Tambahkan shortcut `Tab` untuk insert suggestion (selain `Enter`).
  - Tambahkan visual grouping jika ada kategori parameter.

### 5.6 [HIGH] Dual-Label Preview di Formula

**Masalah yang diselesaikan:** U5 (partial)

**Rancangan:**
- Tambahkan opsi toggle di preview formula:
  - **Mode Nilai** (default): `10 * 5 * 3 = 150`
  - **Mode Label**: `Panjang x Lebar x Tinggi = 150`
  - **Mode Kode**: `panjang * lebar * tinggi = 150`
- Ini membantu user memahami formula tanpa harus menghafal kode.

### 5.7 [MEDIUM] Grouping/Kategori Parameter

**Masalah yang diselesaikan:** U9

**Rancangan:**
- Tambahkan field `group` (opsional) pada `ProjectParameter`:
  ```python
  group = models.CharField(max_length=100, blank=True, help_text="Grup parameter")
  ```
- Di sidebar, parameter ditampilkan dalam collapsible groups.
- Filter by group di autocomplete.

### 5.8 [MEDIUM] Parameter Usage Tracking / Dependency Graph

**Masalah yang diselesaikan:** U8, D2, D4

**Rancangan:**
- Maintain peta `parameterUsage: { [kode]: Set<pekerjaanId | computedParamCode> }`.
- Update peta setiap kali formula berubah.
- Tampilkan di UI:
  - Badge di tabel parameter: "Dipakai di 5 formula"
  - Tooltip/popover: daftar pekerjaan & computed param yang menggunakan kode ini.
- Gunakan peta ini untuk warning saat hapus/rename.

### 5.9 [LOW] Perbaiki Bantuan Formula (Help Modal)

**Masalah yang diselesaikan:** U10

**Rancangan:**
- Tambahkan tab/section di modal Bantuan:
  - **Daftar Parameter Aktif**: tabel kode, label, nilai terkini.
  - **Daftar Formula Turunan**: tabel kode, expression, nilai terkini.
  - **Contoh Formula Real**: gunakan parameter yang aktual ada di project.

### 5.10 [LOW] Izinkan Nilai Parameter Negatif

**Masalah yang diselesaikan:** T7

**Rancangan:**
- Hapus `MinValueValidator(0)` dari `ProjectParameter.value`.
- Tambahkan opsi `allow_negative` di UI (checkbox) jika perlu membatasi sebagian parameter.
- Berguna untuk: elevasi di bawah permukaan, offset, koreksi.

---

## 6. Roadmap Prioritas

### Phase 1: Critical Fixes & Stabilisasi (1-2 hari)

**Fokus:** Mencegah kerusakan data dan fix bug critical.

| #   | Item                                                                         | Effort  | Ref   |
|-----|------------------------------------------------------------------------------|---------|-------|
| 1.1 | Fix: Edit label computed parameter TIDAK boleh mengubah kode (stabilkan T2)  | Rendah  | 5.1-A |
| 1.2 | Fix: Ganti sync mode dari `merge` ke `replace` (fix T5)                     | Rendah  | 5.3   |
| 1.3 | Warning saat hapus parameter yang digunakan (fix D2)                         | Sedang  | 5.4   |
| 1.4 | Live preview kode saat input label baru (fix U2)                             | Rendah  | 5.2   |
| 1.5 | Perbesar hint kode di tabel parameter agar lebih terlihat (fix U4)           | Rendah  | 5.5   |
| 1.6 | Sync API mengembalikan warning/error per-item (hindari silent skip)          | Sedang  | 9.2   |
| 1.7 | Client-side guard: panjang kode/name max 100 + validasi regex sebelum save   | Rendah  | 9.1   |
| 1.8 | Guard race condition: local dirty state tidak boleh ketimpa fetch server      | Sedang  | 9.3   |

**Acceptance Criteria Phase 1:**
- [ ] AC-1.1: Edit label computed parameter -> kode tetap sama, formula lain tidak terpengaruh.
- [ ] AC-1.2: Hapus parameter di client -> reload page -> parameter tidak muncul kembali dari server.
- [ ] AC-1.3: Hapus parameter "x" yang dipakai di formula -> muncul dialog warning dengan daftar formula terpengaruh.
- [ ] AC-1.4: Saat mengetik label "Panjang Dinding Lt. 1" -> di bawah input muncul teks "Kode: panjang_dinding_lt_1" secara real-time.
- [ ] AC-1.5: Kode parameter terlihat jelas tanpa perlu hover/scroll di tabel sidebar.
- [ ] AC-1.6: Sync payload yang berisi kode invalid/tidak lolos validasi -> response tetap `ok: false` atau `ok: true` dengan `warnings[]` per item (tidak boleh silent drop).
- [ ] AC-1.7: Input kode >100 karakter ditolak di UI sebelum request dikirim.
- [ ] AC-1.8: Saat user sedang edit (dirty), fetch server tidak boleh langsung overwrite; harus muncul prompt resolusi.

### Phase 2: Core Improvements -- Rename & Kode Editable (3-5 hari)

**Fokus:** User punya kontrol penuh atas kode parameter.

| #   | Item                                                                         | Effort  | Ref   |
|-----|------------------------------------------------------------------------------|---------|-------|
| 2.1 | Field kode editable saat tambah parameter (dengan auto-fill + validation)    | Sedang  | 5.2   |
| 2.2 | Fitur rename kode + cascade update formula (base param + computed param)     | Tinggi  | 5.1-B |
| 2.3 | Dual-label preview toggle di formula quantity                                | Sedang  | 5.6   |
| 2.4 | Parameter Palette modal (browse + copy kode)                                 | Sedang  | 5.5   |
| 2.5 | Reserved keyword guard (SUM, MIN, MAX, ROUND, PI, E, dll)                   | Rendah  | 9.5   |

**Acceptance Criteria Phase 2:**
- [ ] AC-2.1: Tambah parameter -> user bisa ketik kode sendiri (misal "p1") -> kode disimpan sesuai input user.
- [ ] AC-2.1b: Kode auto-fill dari label saat user belum mengetik di field kode.
- [ ] AC-2.1c: Duplikat kode -> border merah + pesan "Kode sudah dipakai".
- [ ] AC-2.2: Rename kode "panjang" -> "p1" -> semua formula yang berisi "panjang" terupdate menjadi "p1".
- [ ] AC-2.2b: Rename menampilkan daftar formula terpengaruh sebelum eksekusi.
- [ ] AC-2.2c: Rename gagal (misal kode baru duplikat) -> tidak ada perubahan state sama sekali (atomic).
- [ ] AC-2.2d: Substring safety: rename `a -> b` pada formula `abs(a) + a` menghasilkan `abs(b) + b` (bukan merusak token fungsi).
- [ ] AC-2.3: Klik toggle di bawah formula preview -> switch antara mode Nilai / Label / Kode.
- [ ] AC-2.4: Ctrl+Shift+P (atau klik tombol) -> modal muncul dengan semua parameter + search.
- [ ] AC-2.4b: Klik kode di palette -> kode ter-copy ke clipboard.
- [ ] AC-2.5: Kode baru yang bentrok reserved keyword ditolak dengan pesan yang jelas.

### Phase 3: Architecture & Polish (5-7 hari)

**Fokus:** Arsitektur bersih dan fitur pelengkap.

| #   | Item                                                                         | Effort  | Ref   |
|-----|------------------------------------------------------------------------------|---------|-------|
| 3.1 | Parameter usage tracking / dependency graph                                  | Tinggi  | 5.8   |
| 3.2 | Grouping/kategori parameter                                                  | Sedang  | 5.7   |
| 3.3 | Perbaiki help modal dengan daftar parameter aktif                            | Rendah  | 5.9   |
| 3.4 | Izinkan nilai negatif                                                        | Rendah  | 5.10  |
| 3.5 | Multi-tab conflict guard (revision/updated_at check + prompt resolusi)      | Sedang  | 9.4   |

**Acceptance Criteria Phase 3:**
- [ ] AC-3.1: Setiap parameter di sidebar menampilkan badge "Dipakai di N formula".
- [ ] AC-3.1b: Hover badge -> popover menampilkan daftar pekerjaan & computed param yang menggunakan kode ini.
- [ ] AC-3.2: Parameter bisa dikelompokkan (misal "Lantai 1", "Lantai 2") -> tampil sebagai collapsible section.
- [ ] AC-3.3: Modal Bantuan menampilkan daftar parameter aktif project (bukan contoh generik).
- [ ] AC-3.4: Parameter bisa memiliki nilai negatif (misal elevasi -2.5).
- [ ] AC-3.5: Jika dua tab mengedit parameter bersamaan, tab kedua mendapat conflict prompt (bukan overwrite diam-diam).

---

## 7. Rollback Plan: Fitur Rename Kode

Fitur rename kode (Phase 2, item 2.2) adalah perubahan paling berisiko karena menyentuh banyak state sekaligus. Berikut strategi rollback:

### 7.1 Snapshot Sebelum Rename

Sebelum eksekusi rename, simpan snapshot lengkap:

```javascript
function createRenameSnapshot() {
    return {
        timestamp: Date.now(),
        variables: JSON.parse(JSON.stringify(variables)),
        varLabels: JSON.parse(JSON.stringify(varLabels)),
        computedParams: JSON.parse(JSON.stringify(computedParams)),
        rawInputById: JSON.parse(JSON.stringify(rawInputById)),
        fxModeById: JSON.parse(JSON.stringify(fxModeById)),
    };
}
```

### 7.2 Undo Rename (Client-Side)

Jika user menyadari rename salah:
1. Simpan snapshot di `undoRenameStack` (max 5 entries).
2. Tampilkan toast "Kode direname. [Undo]" selama 8 detik.
3. Klik Undo -> restore seluruh snapshot -> re-sync ke server.

### 7.3 Server-Side Safety

- API `parameters/sync` dengan mode `replace` sudah atomic (dalam `@transaction.atomic`).
- Jika rename gagal di tengah jalan (network error saat sync):
  - Client state sudah berubah tapi server belum.
  - Mitigasi: setelah rename, paksa sync dan tunggu response. Jika gagal, rollback ke snapshot.

### 7.4 Migration Safety

- Tidak ada migration DB yang diperlukan untuk fitur rename -- rename hanya mengubah `name` field di record yang sama.
- Jika fitur perlu di-revert total: hapus kode JS rename, behavior kembali ke kode immutable (safe fallback).

### 7.5 Feature Flag

Pertimbangkan menambahkan feature flag saat development:
```javascript
const ENABLE_RENAME_CODE = true; // set false untuk disable fitur
```
Ini memungkinkan deploy incremental tanpa risiko.

---

## 8. Test Matrix Karakter

Berikut daftar karakter yang harus diuji terhadap `normalizeParamCode()` untuk memastikan perilaku konsisten dan terdokumentasi:

### 8.1 Karakter Umum

| Input Label       | Expected Kode    | Kategori          | Status Saat Ini |
|-------------------|------------------|--------------------|-----------------|
| `Panjang`         | `panjang`        | Basic Latin        | OK              |
| `Panjang Dinding` | `panjang_dinding`| Spasi              | OK              |
| `Lebar (m)`       | `lebar_m`        | Parenthesis        | OK, tapi unit masuk kode |
| `Tinggi [m]`      | `tinggi_m`       | Brackets           | OK, tapi unit masuk kode |
| `D4'`             | `d4_prime`       | Apostrophe (')     | Perlu verifikasi |
| `D4\u2019`        | `d4_prime`       | Right single quote  | Perlu verifikasi |
| `D4\u2032`        | `d4_prime`       | Prime symbol        | Perlu verifikasi |

### 8.2 Karakter Desimal & Angka

| Input Label       | Expected Kode    | Kategori          | Status Saat Ini |
|-------------------|------------------|--------------------|-----------------|
| `Tinggi 2,5m`     | `tinggi_2_5m`    | Koma desimal       | OK, tapi ambigu |
| `Tinggi 2.5m`     | `tinggi_2_5m`    | Titik desimal      | Perlu verifikasi |
| `100mm`           | `_100mm`         | Angka di awal      | OK (prefix `_`) |
| `3/4 inch`        | `_3_4_inch`      | Slash (/)          | Perlu verifikasi |

### 8.3 Karakter Khusus Konstruksi

| Input Label          | Expected Kode        | Kategori           | Status Saat Ini |
|----------------------|----------------------|---------------------|-----------------|
| `K-300`              | `k_300`              | Dash/hyphen         | OK              |
| `fc' (MPa)`          | `fc_prime_mpa`       | Apostrof + unit     | Perlu verifikasi |
| `phi 10`             | `phi_10`             | Greek (Latin)       | OK              |
| `dia. 10mm`          | `dia_10mm`           | Singkatan + titik   | OK              |
| `50%`                | `_50`                | Persen              | Perlu verifikasi (hilang?) |
| `Koef.`              | `koef`               | Trailing dot        | OK              |
| `m2` vs `m^2`        | `m2` vs `m_2`        | Superscript         | Perlu verifikasi |
| `+/-0.00`            | `_0_00`              | Plus/minus/dot      | Perlu verifikasi |

### 8.4 Edge Cases

| Input Label          | Expected Kode        | Kategori           | Status Saat Ini |
|----------------------|----------------------|---------------------|-----------------|
| `""`  (kosong)       | `_param`             | Empty string        | OK (fallback)   |
| `___`                | `_param`             | Only underscores    | Perlu verifikasi |
| `  spasi  depan  `   | (trimmed dulu)       | Whitespace          | OK              |
| `UPPER CASE`         | `upper_case`         | Case folding        | OK              |
| Label panjang yang menghasilkan kode/name >100 char | Truncated?  | Length limit        | **BUG POTENSIAL** -- field `name` DB max 100, JS belum guard max length |

### 8.5 Duplikasi Kode (Collision Test)

| Label A          | Label B            | Kode A       | Kode B       | Collision? |
|------------------|--------------------|--------------|--------------|------------|
| `Panjang (m)`    | `Panjang m`        | `panjang_m`  | `panjang_m`  | **YA**     |
| `Lebar-1`        | `Lebar 1`          | `lebar_1`    | `lebar_1`    | **YA**     |
| `D4'`            | `D4 prime`         | `d4_prime`   | `d4_prime`   | **YA**     |
| `Koef. K-300`    | `Koef K 300`       | `koef_k_300` | `koef_k_300` | **YA**     |

**Rekomendasi:** Collision test ini harus menjadi bagian dari automated test suite. Saat kode yang dihasilkan sudah ada, UI harus menampilkan error dan menyarankan user untuk mengedit kode secara manual (terkait Rec 5.2).

---

## 9. Input Contract & Error Handling

### 9.1 Kontrak Input (disarankan jadi single source of truth)

- `name` (kode parameter/computed): regex `^[a-z_][a-z0-9_]*$`, max 100 char, no space.
- `label`: max 200 char.
- `unit`: max 50 char.
- `value`:
  - saat ini min >= 0 (sesuai model).
  - jika fitur negatif diaktifkan, harus eksplisit via policy project/parameter.
- Validasi ini harus konsisten di:
  - UI (inline guard),
  - API (return error/warning terstruktur),
  - model (`full_clean()`).

### 9.2 Per-item Error Reporting (hindari silent skip)

Kondisi saat ini: sync API cenderung `continue` untuk item invalid tanpa feedback rinci ke user.

Rancangan response:

```json
{
  "ok": true,
  "created": 3,
  "updated": 2,
  "deleted": 1,
  "warnings": [
    { "code": "panjang_m__", "reason": "invalid_name_pattern" },
    { "code": "abc...xyz", "reason": "name_too_long" }
  ]
}
```

Jika item invalid bersifat fatal (misalnya struktur payload rusak), gunakan `ok: false` + `errors`.

### 9.3 Guard Saat Load: Cegah Local Edit Ketimpa Fetch Server

Problem: user bisa mulai edit dari snapshot local, lalu fetch server datang dan me-replace state.

Mitigasi:
- Simpan `lastLocalEditAt`.
- Saat fetch server sukses:
  - jika `isDirty === false` -> apply snapshot server normal.
  - jika `isDirty === true` -> tampilkan prompt: "Data server lebih baru. Terapkan atau pertahankan perubahan lokal?"

### 9.4 Multi-tab Conflict Handling

Mengganti `merge -> replace` menyelesaikan zombie parameter, tetapi meningkatkan risiko overwrite lintas tab.

Mitigasi:
- Sertakan `revision` atau `updated_at` pada payload sync.
- Backend reject jika revision stale (409 Conflict).
- UI tampilkan pilihan resolusi:
  - Reload dari server,
  - Keep local lalu re-apply manual.

Catatan implementasi:
- `updated_at` sudah tersedia via `TimeStampedModel` (dapat dipakai tanpa migration tambahan).
- Jika memilih strategi `revision` integer terpisah, perlu migration DB + update kontrak API.

### 9.5 Reserved Keyword Guard

Kode parameter sebaiknya tidak boleh menggunakan nama fungsi/konstanta formula engine:
- Fungsi: `sum`, `min`, `max`, `avg`, `abs`, `round`, `ceil`, `floor`, `pow`
- Konstanta: `pi`, `e`

Jika tetap diizinkan, behavior parser menjadi ambigu untuk user (terutama saat token diikuti tanda kurung).

Catatan maintainability:
- Daftar reserved keyword sebaiknya dihasilkan dari source of truth engine (`fnImpl` + `consts` di `vol_formula_engine.js`) secara programatik saat build/init, bukan hardcoded manual.
- Dengan ini, jika ada fungsi baru (mis. `sqrt`, `log`), guard otomatis ikut ter-update.

### 9.6 Rename Cascade Wajib Token-level, Bukan Text Replace Buta

Untuk rename kode lintas formula:
- Hindari replace string global tanpa parsing.
- Gunakan tokenizer/AST dari `vol_formula_engine.js` agar hanya token identifier yang diubah.
- Ini mencegah salah replace pada:
  - bagian string bantuan/UI text,
  - token yang kebetulan mengandung substring kode lama.

---

## 10. Lampiran

### 10.1 File-File Terkait

| File                                                              | Peran                                      |
|-------------------------------------------------------------------|--------------------------------------------|
| `detail_project/models.py`                                        | Model `ProjectParameter`, `ProjectComputedParameter` |
| `detail_project/views_api.py`                                     | API endpoints CRUD & sync parameter        |
| `detail_project/urls.py`                                          | URL routing API parameter                  |
| `detail_project/templates/detail_project/volume_pekerjaan.html`   | Template HTML (sidebar, tabel, modal)      |
| `detail_project/static/detail_project/js/volume_pekerjaan.js`     | Logic utama parameter & formula            |
| `detail_project/static/detail_project/js/vol_formula_engine.js`   | Formula parser & evaluator (shunting-yard) |
| `detail_project/static/detail_project/css/volume_pekerjaan.css`   | Styling sidebar parameter                  |

### 10.2 API Endpoints Terkait Parameter

| Endpoint                                          | Method     | Fungsi                        |
|---------------------------------------------------|------------|-------------------------------|
| `/api/project/{id}/parameters/`                   | GET, POST  | List & create parameter       |
| `/api/project/{id}/parameters/{param_id}/`        | GET, PUT, DELETE | Detail, update, delete  |
| `/api/project/{id}/parameters/sync/`              | POST       | Bulk sync (merge/replace)     |
| `/api/project/{id}/computed-parameters/`           | GET        | List computed parameters      |
| `/api/project/{id}/computed-parameters/sync/`      | POST       | Bulk sync computed params     |
| `/api/project/{id}/volume/formula/`                | GET, POST  | Formula state per-pekerjaan   |

### 10.3 Riwayat Revisi Dokumen

| Versi | Tanggal     | Perubahan                                                     |
|-------|-------------|---------------------------------------------------------------|
| v1.0  | 2026-02-11  | Dokumen awal                                                  |
| v1.1  | 2026-02-11  | Koreksi: autocomplete sudah indexOf scoring (bukan startsWith). Koreksi: server sudah authoritative saat fetch (full replace). Ganti metadata reviewer. Fix encoding. Reprioritasi: rename kode jadi item pertama. Tambah acceptance criteria, rollback plan, test matrix karakter. |
| v1.2  | 2026-02-11  | Tambahan section Input Contract & Error Handling: per-item error reporting (hindari silent skip), guard max length `name` 100 char, race condition local-vs-server, conflict lintas tab, reserved keyword guard, dan token-level rename cascade. Update roadmap + acceptance criteria terkait reliability. |

---

*Dokumen ini dibuat berdasarkan code review menyeluruh terhadap codebase Volume Pekerjaan. Rekomendasi diurutkan berdasarkan dampak terhadap integritas data dan pengalaman user.*
