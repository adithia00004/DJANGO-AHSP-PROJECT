# Rencana UI/UX: Formula Lebih Human-Readable

## Status
- Draft v3.1 (ditambah 2 enhancement UX berdampak tinggi)
- Tanggal: 12 Februari 2026
- Tujuan: disetujui sebelum implementasi kode

## Latar Belakang
Sistem opaque ID (`bp_*` / `cp_*`) sudah berjalan dan stabil. Phase 2 (Chip/Tag UI) telah mengimplementasikan banyak komponen label-first. Namun audit kode menunjukkan **masih ada beberapa titik kebocoran** dimana user melihat kode opaque langsung, serta beberapa area yang bisa diperbaiki konsistensinya. Dokumen ini fokus pada **gap yang tersisa**, bukan mengulang apa yang sudah jadi.

## Kebijakan Tampilan Kode: Label-Dominant (Hybrid)

> **Keputusan:** Dokumen ini menggunakan kebijakan **label-dominant**, bukan zero-opaque absolut.

**Definisi:**
- **Layer utama (teks, input, error, badge):** user melihat **label saja**. Kode opaque **tidak boleh** tampil sebagai teks primer.
- **Layer sekunder (tooltip, konteks debug):** kode opaque **boleh** tampil sebagai informasi pendukung yang hanya muncul saat user sengaja mencari (hover, klik, expand).

**Alasan:** Zero-opaque absolut tidak praktis karena:
1. Support ticket butuh referensi kode untuk reproduksi bug.
2. Power users yang menulis formula perlu tahu identifier yang tersimpan di database.
3. Error fallback memerlukan kode saat label missing (data corrupt/stale).

**Aturan konkret:**

| Layer | Boleh tampilkan kode? | Contoh |
|-------|----------------------|--------|
| Teks primer (label, input, badge, toast) | **Tidak** | Badge: "Dipakai di 5 formula" (bukan "bp_1 dipakai...") |
| Tooltip / hover | **Ya** | `title="bp_1"` pada chip |
| Konteks sekunder (parenthetical) | **Ya, jika label juga ada** | Delete: `"Panjang" (kode: bp_1)` |
| Error fallback (label missing) | **Ya, sebagai last resort** | `"Parameter tidak ditemukan (mungkin sudah dihapus)"` |
| Console/log (developer only) | **Ya** | `console.warn('[VP] sync:', rawCode)` |
| Export kolom dedicated | **Hapus** | Kolom "Kode Parameter" dihapus dari export user-facing |
| Palette kode sekunder | **Pindah ke tooltip** | Kode hanya muncul saat hover label |

---

## Prinsip Desain
1. **Storage != Display**: yang disimpan tetap kode opaque; yang ditampilkan ke user berbasis label.
2. **Label-Dominant Feedback**: semua pesan validasi/error memprioritaskan label. Kode hanya di layer sekunder.
3. **Backward Compatible API Transition**: perubahan response API menggunakan dual-field sementara (`name` + `index`), bukan breaking replace.
4. **Patch, Bukan Rebuild**: fokus tambal titik kebocoran spesifik, bukan rewrite komponen yang sudah bekerja.

## Kesepakatan Diskusi: Inline dan Modal Wajib Aktif (12 Februari 2026)

### Tujuan Utama
1. Inline input area dan modal popup editor harus sama-sama bisa dipakai end-to-end, bukan hanya satu jalur utama.
2. Inline diposisikan sebagai jalur cepat (quick edit), modal diposisikan sebagai jalur kompleks (guided edit).
3. Hasil akhir dari dua jalur harus identik: preview, validasi, status dirty, dan data tersimpan.

### Kanal Interaksi dan Trigger

| Kanal | Trigger Masuk | Trigger Keluar | Tujuan |
|-------|---------------|----------------|--------|
| Inline (`.qty-input`) | klik/focus cell quantity, aktifkan tombol `fx`, ketik/paste formula | blur, Enter, Ctrl/Cmd+S | Edit cepat angka, formula pendek, dan koreksi minor |
| Modal (`#vp-fe-input`) | klik tombol editor, double-click quantity, `Alt+Enter`, klik chip preview | tombol `Apply`, tutup modal, `Esc` | Formula kompleks, resolver unknown token, penggunaan palette/autocomplete intensif |

### Nilai yang Diterima (Harus Konsisten di Inline dan Modal)

| Jenis | Contoh | Inline | Modal | Catatan |
|------|--------|--------|-------|---------|
| Angka literal | `10`, `10,5`, `1.000,25`, `1_000.25`, `-3` | Ya | Ya | Parsing mengikuti engine formula, lokal ID/EN didukung |
| Parameter base | `bp_*` (display sebagai label) | Ya | Ya | Insert via autocomplete/palette, bukan ketik label bebas |
| Parameter computed | `cp_*` (display sebagai label) | Ya | Ya | Perlakuan sama dengan base parameter |
| Operator aritmatika | `+`, `-`, `*`, `/`, `^` | Ya | Ya | Prioritas operator mengikuti engine |
| Kurung | `(`, `)` | Ya | Ya | Harus seimbang |
| Fungsi bawaan | `MIN`, `MAX`, `SUM`, `AVG`, `ABS`, `ROUND`, `CEIL`, `FLOOR`, `POW` | Ya | Ya | Case-insensitive, argumen dipisah koma |
| Prefix formula | `=` di awal ekspresi | Ya | Ya | Opsional, mode formula tetap harus terdeteksi |
| Spasi | whitespace antar token | Ya | Ya | Boleh, tidak mengubah makna ekspresi |

### Nilai/Keadaan yang Harus Ditolak
1. Token tidak dikenal (parameter hilang/typo) tanpa resolver.
2. Kurung tidak seimbang.
3. Operator tanpa operand yang valid.
4. Pembagian dengan nol.
5. Fungsi tidak dikenal atau jumlah argumen tidak valid.
6. Ekspresi kosong saat mode formula aktif.

### Kontrak Interaksi (Agar Tidak Sekadar Pajangan)
1. User harus bisa membuat, mengedit, dan menyimpan formula penuh dari inline tanpa wajib membuka modal.
2. User harus bisa membuat, mengedit, dan menyimpan formula penuh dari modal tanpa kembali ke inline.
3. Perpindahan inline <-> modal tidak boleh mengubah makna formula (semantic identity tetap).
4. Kedua kanal harus memakai source of truth yang sama (`rawInputById`/raw expression), bukan state terpisah.
5. Pesan validasi dan preview hasil hitung harus konsisten di kedua kanal.
6. Dirty state dan status sinkronisasi harus merepresentasikan perubahan dari kedua kanal secara setara.

---

## Baseline: Yang Sudah Jadi (Phase 2 + 3B)

Komponen berikut sudah **benar label-first** dan **tidak perlu diubah**:

| Komponen | Fungsi | Status |
|----------|--------|--------|
| Chip/tag di formula editor sidebar | `buildFormulaChipHtml()` | OK -- label sebagai teks, kode di tooltip |
| Autocomplete | Scoring prioritas label (1300+) > code (900+) | OK |
| Parameter Palette modal | Label primary, kode secondary | **Needs Patch (L9)** -- kode visible melanggar kebijakan teks primer |
| Preview formula (sidebar) | `translateFormulaForPreview()` mode label | OK |
| Error formula evaluasi | `humanizeFormulaError()` translate `bp_*` -> `Label (bp_*)` | OK |
| Delete warning | `buildDeleteWarningMessage()` label-first | OK |
| Usage badge | "Dipakai di N formula" | OK |
| Export XLSX/CSV adapter | `_humanize_formula()` via `remap_expression()` | OK |
| Tabel parameter sidebar | Tampil label only, kode hidden | OK |
| Tabel computed sidebar | Tampil label + chip formula | OK |
| Dirty-state guard | `shouldProtectLocalBaseState()` / computed | OK |
| Conflict UX 409 | Modal Reload / Tetap Lokal | OK |
| PANDUAN_USER.md | Referensi kode manual sudah dihapus | OK |
| Help text + placeholder | Menjelaskan opaque ID system | OK |

---

## Temuan Audit: Titik Kebocoran yang Perlu Dipatch

### L1 [Tinggi] -- Import validation error menampilkan raw code

**Lokasi:** `volume_pekerjaan.js` fungsi `parseJSONToVarsLabels()`, `parseCSVToVarsLabels()`, `parseXLSXToVarsLabels()`

**Yang user lihat saat ini:**
```
"Kode bp_1: format bp_N tidak valid"
"Kode cp_3: Nilai tidak valid"
"Baris 3: Kode harus format bp_N"
```

**Masalah:** Fungsi parser import menampilkan raw code di error dialog tanpa label translation.

**Fix:** Ganti referensi kode dengan nomor baris / label dari file import:

```javascript
// SEBELUM (di parseJSONToVarsLabels):
errors.push(`Kode ${code}: format ${baseCodeExpectedText()} tidak valid`);

// SESUDAH:
const importLabel = String((srcLabels && srcLabels[code]) || '').trim();
const displayRef = importLabel || `Baris ${idx + 1}`;
errors.push(`${displayRef}: format parameter tidak valid`);
```

```javascript
// SEBELUM (di parseCSVToVarsLabels / parseXLSXToVarsLabels):
errors.push(`Baris ${idx + 1}: Kode harus format ${baseCodeExpectedText()}`);

// SESUDAH:
errors.push(`Baris ${idx + 1}: Format parameter tidak sesuai`);
```

**File terdampak:** `volume_pekerjaan.js` (4 lokasi di parser functions)

---

### L2 [Sedang] -- API sync warnings response berisi raw code

**Lokasi:** `views_api.py` fungsi sync endpoint (base params + computed params)

**Yang backend kirim saat ini:**
```json
{"name": "bp_5", "error": "Kode tidak sesuai format opaque (bp_N)"}
```

**Masalah:** Field `"name"` berisi raw opaque code. Frontend saat ini menampilkan pesan generik (aman), tapi data mentah tersedia di response -- fragile terhadap perubahan frontend di masa depan.

**Fix backend (backward compatible transition):**

Tambahkan field `"index"` **tanpa menghapus** `"name"` dulu. Setelah semua client mengadopsi `index`, `name` bisa di-deprecate.

```python
# SEBELUM (di sync endpoint warning builder):
warnings.append({"name": str(raw_code), "error": _base_name_format_error_text()})

# SESUDAH (dual-field, backward compatible):
warnings.append({
    "name": str(raw_code),   # deprecated, akan dihapus di versi berikutnya
    "index": idx,
    "error": "Format parameter tidak valid"
})
```

**Fix frontend (hardening):** Preferensikan `index` jika tersedia, fallback ke `name` dengan label translation:

```javascript
// Di handler sync warning toast:
const labels = getFormulaScopeLabels();
const detail = res.data.warnings.slice(0, 3).map(w => {
    if (w.index != null) return `item #${w.index + 1}`;
    return labels[w.name] || `item`;
}).join(', ');
TOAST.warn(`${res.data.warnings.length} parameter di-skip: ${detail}`);
```

**Deprecation timeline:** Hapus field `"name"` dari response setelah 1 release cycle (atau setelah konfirmasi tidak ada client lain yang konsumsi API ini).

**File terdampak:** `views_api.py` (5 lokasi di sync endpoints), `volume_pekerjaan.js` (2 lokasi di sync handler)

---

### L3 [Sedang] -- Formula input di tabel volume menampilkan raw code

**Lokasi:** `volume_pekerjaan.js` fungsi `bindRow()`, `openFormulaEditorForRow()`, `updateRowFromInput()`

**Yang user lihat saat ini:**

Tabel volume `.qty-input`: `=bp_1 * bp_2 + cp_1`

Di bawah input ada `.fx-chip-preview` (compact mode) yang sudah label-first, tapi input box sendiri tetap tampil raw. Saat buka formula editor modal (`#vp-fe-input`), textarea juga berisi raw opaque code.

**Masalah:** Dua titik dimana raw code terlihat:
1. Input `.qty-input` di tabel volume -- saat formula mode aktif, user melihat raw di input box
2. Textarea `#vp-fe-input` di formula editor modal/fullscreen -- user melihat raw saat mengedit

**Fix:**

1. **Tabel volume inline:** Saat formula mode aktif dan row TIDAK sedang di-edit, sembunyikan `.qty-input` dan tampilkan `.fx-chip-preview` (compact, label-only). User klik chip preview → buka formula editor modal untuk edit.

```javascript
// Di bindRow() dan updateRowFromInput(), saat formula mode aktif:
if (isFormulaMode(id, raw) && !row.classList.contains('is-editing-formula')) {
    input.classList.add('d-none');           // sembunyikan raw input
    chipPreview.classList.remove('d-none');  // tampilkan chip label
    chipPreview.style.cursor = 'pointer';   // indikasi klik-untuk-edit
    chipPreview.onclick = () => openFormulaEditorForRow(id);
} else {
    input.classList.remove('d-none');
    chipPreview.classList.add('d-none');
}
```

2. **Formula editor modal:** Implementasikan **dual-view** -- chip view sebagai default, raw textarea sebagai edit mode:

```javascript
// Di openFormulaEditorForRow():
// State: CHIP VIEW (default saat buka)
formulaEditorChipPreviewEl.classList.remove('d-none');
formulaEditorInputEl.classList.add('d-none');

// Toggle ke EDIT MODE saat user klik chip area atau tekan tombol "Edit Formula"
function toggleFormulaEditorRawMode() {
    const isRaw = !formulaEditorInputEl.classList.contains('d-none');
    if (isRaw) {
        // Switch ke chip view
        formulaEditorInputEl.classList.add('d-none');
        formulaEditorChipPreviewEl.classList.remove('d-none');
    } else {
        // Switch ke raw edit (autocomplete aktif di sini)
        formulaEditorInputEl.classList.remove('d-none');
        formulaEditorInputEl.focus();
        formulaEditorChipPreviewEl.classList.add('d-none');
    }
}
```

**Kenapa dual-view, bukan chip-only:** Textarea raw **wajib tetap accessible** karena:
- Autocomplete engine mendengarkan input events di textarea
- Keyboard navigation (arrow keys, selection) bergantung pada native textarea behavior
- Accessibility: screen reader membaca textarea, bukan custom chip DOM
- User perlu bisa copy-paste formula antar row

**Mitigasi risiko regresi:** Tambahkan toggle button eksplisit ("Edit Formula" / "Lihat Chip") agar user selalu punya akses ke kedua mode. Jangan hanya mengandalkan keyboard shortcut tersembunyi.

**File terdampak:** `volume_pekerjaan.js` (3 fungsi), `volume_pekerjaan.css` (styling toggle button)

---

### L4 [Sedang] -- Usage badge di sidebar parameter table terlalu ramai

**Lokasi:** `volume_pekerjaan.js` fungsi `buildUsageBadgeHtml()`, CSS `volume_pekerjaan.css`

**CSS selector referensi:** `#vp-var-table > tbody > tr > td:first-child > small > span`

**Yang user lihat saat ini:**
```
[Panjang Dinding          ]   <- input label
 Dipakai di 5 formula        <- badge langsung visible, warna warning kuning
```

Badge `.vp-usage-badge` (`text-bg-warning`) selalu tampil langsung di bawah label parameter. Pada tabel dengan banyak parameter, badge ini membuat tampilan **terlalu ramai** dan mengalihkan fokus dari data yang lebih penting (nama + nilai).

**Fix:** Sembunyikan badge secara default, tampilkan saat hover row atau saat aksi tertentu (edit/delete):

```css
/* Default: badge tersembunyi */
#vp-var-table .vp-usage-badge {
    opacity: 0;
    transition: opacity 0.15s ease;
    pointer-events: none;
}

/* Tampil saat hover baris */
#vp-var-table tr:hover .vp-usage-badge,
#vp-var-table tr:focus-within .vp-usage-badge {
    opacity: 1;
    pointer-events: auto;
}

/* Tampil saat row sedang di-edit */
#vp-var-table tr.is-editing .vp-usage-badge {
    opacity: 1;
    pointer-events: auto;
}
```

**Alternatif:** Jika badge hanya perlu muncul saat user klik tombol delete/edit, bisa trigger via JS: tambahkan class `.is-editing` ke `<tr>` saat user klik edit, hapus saat selesai.

**File terdampak:** `volume_pekerjaan.css`

---

### L5 [Sedang] -- Chip formula tidak membedakan parameter vs formula turunan

**Lokasi:** `volume_pekerjaan.js` fungsi `buildFormulaChipHtml()`, CSS `volume_pekerjaan.css` (chip rules)

**Masalah saat ini:** Semua chip formula (`vp-formula-chip`) tampil dengan warna dan style yang sama, baik untuk base parameter (`bp_*`) maupun computed/formula parameter (`cp_*`). User tidak bisa membedakan secara visual mana yang parameter input dan mana yang formula turunan.

**Fix:** Tambahkan CSS class berbeda berdasarkan prefix, dengan warna yang subtle dan kompatibel dark/light mode. Class diterapkan di **kedua mode** (compact dan non-compact):

```javascript
// Di buildFormulaChipHtml(), saat generate chip untuk identifier:
if (type === 'id' && Object.prototype.hasOwnProperty.call(labels, value)) {
    const label = String(labels[value] || value);
    const isComputed = value.startsWith('cp_');
    const chipClass = isComputed ? 'vp-formula-chip vp-chip-computed' : 'vp-formula-chip vp-chip-base';
    if (compact) {
        return `<span class="${chipClass}" title="${escapeHtml(value)}">${escapeHtml(label)}</span>`;
    }
    return `<span class="${chipClass}" title="${escapeHtml(value)}">${escapeHtml(label)} <span class="chip-code">${escapeHtml(value)}</span></span>`;
}
```

```css
/* Base parameter chip (bp_*) -- default primary color, sudah ada */
.vp-formula-chip.vp-chip-base {
    background: color-mix(in srgb, var(--dp-c-primary) 10%, transparent);
    border-color: color-mix(in srgb, var(--dp-c-primary) 32%, var(--dp-c-border));
    color: var(--dp-c-text);
}

/* Computed/formula parameter chip (cp_*) -- warna berbeda, subtle */
.vp-formula-chip.vp-chip-computed {
    background: color-mix(in srgb, var(--dp-c-info, #0dcaf0) 10%, transparent);
    border-color: color-mix(in srgb, var(--dp-c-info, #0dcaf0) 32%, var(--dp-c-border));
    color: var(--dp-c-text);
}

/* Dark mode auto-adjust via color-mix -- tidak perlu override khusus */
/* Karena menggunakan CSS variables, dark mode akan auto-resolve */
```

**Efek visual:**
- Chip `bp_*` (parameter): border/background nuansa **biru** (primary) -- sudah ada
- Chip `cp_*` (formula turunan): border/background nuansa **cyan/teal** (info) -- baru

Perbedaan warna halus tapi cukup untuk membedakan. `color-mix()` memastikan kompatibilitas dark/light mode karena menggunakan CSS variables yang sudah didefinisikan di codebase.

**File terdampak:** `volume_pekerjaan.js` (1 lokasi di `buildFormulaChipHtml`), `volume_pekerjaan.css` (2 rule baru)

---

### L6 [Sedang] -- Formula engine error "Variabel tidak dikenal" menampilkan raw code

**Lokasi:** `vol_formula_engine.js` fungsi evaluator (throw Error), `volume_pekerjaan.js` fungsi `humanizeFormulaError()`

**Yang user lihat saat ini:**
```
"Variabel tidak dikenal: bp_99"
```

**Masalah:** Saat user menulis formula yang mereferensi variabel yang tidak ada, engine melempar error `Variabel tidak dikenal: ${name}`. Fungsi `humanizeFormulaError()` sudah menangani translasi pattern `bp_*`/`cp_*` -> `Label (kode)`, tapi hanya jika variabel tersebut ada di lookup labels. Jika variabel benar-benar tidak ada (typo, sudah dihapus), user tetap melihat raw code.

**Fix:** Perkuat `humanizeFormulaError()` agar pesan "Variabel tidak dikenal" selalu humanized:

```javascript
// Tambahkan di humanizeFormulaError(), setelah regex replace existing:
text = text.replace(/Variabel tidak dikenal:\s*(\S+)/gi, (match, varName) => {
    const label = labels[varName];
    if (label) return `Parameter tidak ditemukan: ${label} (${varName})`;
    if (/^(?:bp|cp)_[1-9][0-9]*$/.test(varName)) return `Parameter tidak ditemukan (mungkin sudah dihapus)`;
    return `Parameter tidak ditemukan: "${varName}"`;
});
```

**File terdampak:** `volume_pekerjaan.js` (1 lokasi di `humanizeFormulaError`)

---

### L7 [Rendah] -- Help modal contoh formula tidak konsisten dengan chip UI

**Lokasi:** `volume_pekerjaan.html` template help modal section

**Yang user lihat:**
```
= [Panjang Dinding] * [Lebar Dinding] * [Tinggi Dinding]
```

**Masalah:** Help modal menampilkan contoh formula dengan notasi bracket `[Label]`, tapi di editor aktual user melihat chip/tag visual. Inkonsistensi ini bisa membingungkan user baru.

**Fix:** Update teks help agar sesuai dengan UX aktual:

```html
<!-- SEBELUM: -->
<li><code>= [Panjang Dinding] * [Lebar Dinding] * [Tinggi Dinding]</code></li>

<!-- SESUDAH: -->
<li><code>= Panjang Dinding * Lebar Dinding * Tinggi Dinding</code></li>
<small class="text-muted">Parameter ditampilkan sebagai chip/tag di editor formula.</small>
```

**File terdampak:** `volume_pekerjaan.html` (3-4 baris)

---

### L8 [Wajib] -- Export kolom "Kode Parameter" menampilkan opaque code

**Lokasi:** `volume_pekerjaan_adapter.py` fungsi export parameter table section

**Yang user lihat di Excel:**
```
| No | Kode Parameter | Nama Parameter | Nilai |
| 1  | bp_1           | Panjang        | 10    |
```

**Keputusan:** Hapus kolom "Kode Parameter" dari export user-facing. Kolom ini melanggar kebijakan label-dominant karena menampilkan kode opaque sebagai teks primer di dokumen yang dibagikan ke stakeholder.

**Fix:** Hapus kolom "Kode Parameter", sisakan "No" + "Nama Parameter" + "Nilai" + "Satuan":

```python
# SEBELUM:
headers = ['No', 'Kode Parameter', 'Nama Parameter', 'Nilai']

# SESUDAH:
headers = ['No', 'Nama Parameter', 'Nilai', 'Satuan']
```

**File terdampak:** `volume_pekerjaan_adapter.py` (header + row builder)

---

### L9 [Wajib] -- Palette menampilkan kode sebagai referensi sekunder

**Lokasi:** `volume_pekerjaan.js` fungsi palette builder (di `openParameterPalette` atau equivalent)

**Yang user lihat:**
```
[Panjang Dinding]    bp_1
[Lebar Ruangan]      bp_2
```

**Keputusan:** Pindahkan kode ke tooltip. Teks visible hanya label. Sesuai kebijakan label-dominant: kode boleh di layer sekunder (tooltip), tidak di teks primer.

**Fix:**
```javascript
// SEBELUM:
<span class="vp-palette-label">${label}</span>
<span class="vp-palette-code">${code}</span>

// SESUDAH:
<span class="vp-palette-label" title="Kode: ${code}">${label}</span>
```

**File terdampak:** `volume_pekerjaan.js` (1 lokasi di palette builder)

---

### L10 [Tinggi] -- Preview formula belum menampilkan substitusi nilai inline

**Lokasi:** `volume_pekerjaan.js` fungsi preview formula (builder/evaluator preview), area preview di modal formula editor

**Masalah:** User melihat formula label sudah lebih readable, tetapi belum langsung paham "angka apa yang dipakai saat ini". Ini membuat validasi mental hasil masih lambat.

**Fix:** Tambahkan mode preview substitusi nilai inline (label + nilai):

```text
Luas Dinding = Panjang Dinding (10) × Lebar Dinding (5) = 50
```

Aturan:
1. Default ON di editor formula (bisa ditoggle OFF jika ingin ringkas).
2. Jika nilai tidak tersedia, tampilkan placeholder aman: `(?)`.
3. Jangan ubah raw expression/storage; hanya render layer preview.

**File terdampak:** `volume_pekerjaan.js`, `volume_pekerjaan.html` (toggle UI)

---

### L11 [Tinggi] -- Unknown token masih berhenti di pesan error tanpa jalur perbaikan cepat

**Lokasi:** `volume_pekerjaan.js` fungsi `humanizeFormulaError()`, handler submit/evaluate formula editor

**Masalah:** Saat muncul error unknown token, user hanya melihat pesan. Tidak ada aksi langsung untuk resolve.

**Fix:** Tambahkan resolver CTA pada error unknown token:
1. Tampilkan tombol: `Pilih Parameter Pengganti`.
2. Tombol membuka palette/autocomplete dengan fokus ke token bermasalah.
3. User pilih parameter -> token diganti otomatis pada formula input.
4. Re-evaluate otomatis setelah replacement.

**Contoh alur:**
```text
Error: Parameter tidak ditemukan: "panjang_lama"
[Pilih Parameter Pengganti]
-> pilih "Panjang Dinding" -> formula terupdate -> preview refresh
```

**File terdampak:** `volume_pekerjaan.js`, `volume_pekerjaan.html`, `volume_pekerjaan.css` (UI CTA ringan)

---

## Rencana Implementasi

### Milestone 1: MVP Release (Error Messages + UX Polish)
**Scope:** Patch 1-6 -- semua kebocoran teks primer ditutup.

#### Patch 1: Import Error Messages [Tinggi]
**Effort:** Rendah (4 baris ubah)
**File:** `volume_pekerjaan.js`
1. Fungsi `parseJSONToVarsLabels()`: Ganti `Kode ${code}:` dengan label dari import data atau `Baris N:`
2. Fungsi `parseJSONToVarsLabels()`: Ganti `Kode ${code}:` kedua (value validation)
3. Fungsi `parseCSVToVarsLabels()`: Hapus referensi format kode spesifik, ganti pesan generik
4. Fungsi `parseXLSXToVarsLabels()`: Sama -- pesan generik

#### Patch 2: API Sync Warnings [Tinggi]
**Effort:** Sedang (5 lokasi backend + 2 frontend)
**File:** `views_api.py`, `volume_pekerjaan.js`
1. Sync endpoint (base params): Tambahkan `"index": idx` ke warning dict (**tanpa menghapus** `"name"` -- backward compat)
2. Sync endpoint (computed params): Sama -- dual-field transition
3. Frontend sync handler: Preferensikan `index`, fallback `name` + label translation
4. **Deprecation note:** Hapus field `"name"` di release berikutnya setelah konfirmasi tidak ada client lain

#### Patch 3: Formula Input Display [Sedang]
**Effort:** Sedang
**File:** `volume_pekerjaan.js`, `volume_pekerjaan.css`
1. `bindRow()` + `updateRowFromInput()`: Saat formula mode aktif dan row TIDAK sedang di-edit, sembunyikan input, tampilkan chip preview. Klik chip → buka editor modal.
2. `openFormulaEditorForRow()`: Default ke chip view, tambahkan toggle button "Edit Formula" / "Lihat Chip"
3. Pertahankan raw textarea accessible (autocomplete, keyboard nav, a11y)
4. Tambahkan visual indicator untuk toggle state (icon atau label button)

#### Patch 4: Usage Badge Hide-on-Hover [Sedang]
**Effort:** Rendah (CSS only)
**File:** `volume_pekerjaan.css`
1. Rule default: `#vp-var-table .vp-usage-badge { opacity: 0; transition: opacity 0.15s; pointer-events: none; }`
2. Rule reveal: hover/focus-within pada `tr` → `opacity: 1`
3. Opsional: class `.is-editing` di JS saat user klik edit/delete

#### Patch 5: Chip Color Differentiation [Sedang]
**Effort:** Rendah (JS 2 baris + CSS 2 rule)
**File:** `volume_pekerjaan.js`, `volume_pekerjaan.css`
1. `buildFormulaChipHtml()`: deteksi `value.startsWith('cp_')` → class `vp-chip-computed`, else `vp-chip-base`. Diterapkan di **compact DAN non-compact mode**.
2. CSS: `.vp-chip-base` → `--dp-c-primary` (biru), `.vp-chip-computed` → `--dp-c-info` (cyan/teal)
3. `color-mix()` memastikan dark/light mode otomatis

#### Patch 6: Formula Engine Error Humanization [Sedang]
**Effort:** Rendah (5 baris)
**File:** `volume_pekerjaan.js`
1. `humanizeFormulaError()`: Tambah regex untuk `Variabel tidak dikenal: X`
2. Jika variabel ada di labels → `Parameter tidak ditemukan: Label (kode)`
3. Jika variabel format opaque tapi tidak di labels → `Parameter tidak ditemukan (mungkin sudah dihapus)`
4. Fallback (bukan format opaque) → tampilkan input apa adanya (aman, bukan kode internal)

### Milestone 2: Full Completion (Cosmetic + Export)
**Scope:** Patch 7-9 -- konsistensi UI dan export.

#### Patch 7: Help Modal Contoh Formula [Rendah]
**Effort:** Rendah (3-4 baris HTML)
**File:** `volume_pekerjaan.html`
1. Ganti notasi bracket `[Label]` dengan teks plain label
2. Tambahkan keterangan bahwa parameter ditampilkan sebagai chip/tag di editor

#### Patch 8: Export Kolom Kode [Wajib per Kebijakan]
**Effort:** Rendah
**File:** `volume_pekerjaan_adapter.py`
1. Hapus kolom "Kode Parameter" dari export user-facing
2. Sesuaikan row builder untuk skip kode

#### Patch 9: Palette Kode ke Tooltip [Wajib per Kebijakan]
**Effort:** Rendah
**File:** `volume_pekerjaan.js`
1. Pindahkan `vp-palette-code` ke `title` attribute pada label element
2. Hapus elemen teks kode visible

### Milestone 3: UX+ Dampak Tinggi (Readability & Recovery)
**Scope:** Patch 10-11 -- percepatan pemahaman formula dan percepatan perbaikan error.

#### Patch 10: Inline Value Substitution Preview [Tinggi]
**Effort:** Sedang
**File:** `volume_pekerjaan.js`, `volume_pekerjaan.html`
1. Tambahkan mode preview: `Label (nilai)` untuk setiap token identifier.
2. Tambahkan toggle `Tampilkan Nilai`.
3. Placeholder `(?)` untuk nilai yang belum tersedia.
4. Tetap gunakan expression raw opaque sebagai source of truth.

#### Patch 11: Unknown Token Resolver UX [Tinggi]
**Effort:** Sedang
**File:** `volume_pekerjaan.js`, `volume_pekerjaan.html`, `volume_pekerjaan.css`
1. Saat error unknown token, tampilkan CTA `Pilih Parameter Pengganti`.
2. Integrasi dengan palette/autocomplete untuk replacement token.
3. Apply replacement + re-evaluate otomatis.
4. Simpan jejak perubahan di state editor agar undo lokal tetap mungkin.

---

## Acceptance Criteria

### MVP Release (Patch 1-6)
1. **AC-HR1:** Import parameter dengan kode invalid -- error dialog **tidak** menampilkan raw opaque code. Hanya nomor baris atau label dari file import.
2. **AC-HR2:** API sync warnings response menyertakan field `index` (backward compatible). Frontend toast **tidak** menampilkan raw code.
3. **AC-HR3:** Tidak ada regresi pada fitur existing (import tetap berfungsi, sync tetap berfungsi).
4. **AC-HR4:** Input formula di tabel volume -- saat formula mode aktif, user melihat chip/label preview, **bukan** raw `=bp_1 * bp_2`. Toggle ke raw mode tersedia dan berfungsi.
5. **AC-HR5:** Formula editor modal -- default menampilkan chip view. Toggle "Edit Formula" membuka textarea raw dengan autocomplete aktif. Toggle "Lihat Chip" kembali ke chip view.
6. **AC-HR6:** Usage badge di sidebar parameter table **tidak** langsung visible. Badge muncul saat hover baris atau saat user melakukan aksi edit/delete.
7. **AC-HR7:** Chip formula base parameter (`bp_*`) dan computed parameter (`cp_*`) memiliki **warna berbeda** yang subtle, di **compact maupun non-compact mode**. Perbedaan terlihat di light mode dan dark mode.
8. **AC-HR8:** Error formula "Variabel tidak dikenal" -- kode opaque **tidak** tampil sebagai teks primer. Boleh di konteks sekunder (parenthetical) jika label juga ada, sesuai kebijakan label-dominant.

### Full Completion (Patch 7-9)
9. **AC-HR9:** Help modal contoh formula konsisten dengan UI chip/tag aktual.
10. **AC-HR10:** Export Excel **tidak** memiliki kolom "Kode Parameter". Hanya "No", "Nama Parameter", "Nilai", "Satuan".
11. **AC-HR11:** Palette parameter menampilkan **label saja** sebagai teks. Kode hanya muncul di tooltip saat hover.

### UX+ Dampak Tinggi (Patch 10-11)
12. **AC-HR12:** Preview formula dapat menampilkan substitusi nilai inline (`Label (nilai)`) tanpa mengubah raw expression.
13. **AC-HR13:** Saat unknown token terjadi, user mendapat jalur perbaikan langsung via CTA resolver dan dapat menyelesaikan error tanpa edit manual penuh.

---

## Test Plan

### Otomatis
1. Import JSON dengan kode invalid -> pesan error tidak mengandung regex `bp_\d+` atau `cp_\d+`.
2. Sync dengan kode invalid -> response warnings mengandung field `index` DAN `name` (backward compat).
3. Export adapter regression -> formula tetap label-first.
4. Formula engine: referensi variabel `bp_999` (tidak ada) -> error **tidak** menampilkan raw code.
5. Export parameter table -> output **tidak** mengandung kolom "Kode Parameter".
6. Preview substitution -> token identifier merender `Label (nilai)` saat value tersedia.
7. Unknown token resolver -> replacement flow memperbarui expression dan menghilangkan error unknown token.

### Manual
1. Buka tabel volume pekerjaan, aktifkan formula mode -> pastikan input menampilkan **chip preview** (bukan raw). Klik chip -> editor modal terbuka.
2. Di editor modal: default chip view. Klik "Edit Formula" -> textarea muncul, autocomplete berfungsi. Klik "Lihat Chip" -> kembali ke chip.
3. Import file CSV/JSON/XLSX dengan data invalid -> cek error dialog (tidak ada raw code).
4. Trigger sync warning (corrupt localStorage) -> cek toast message (tidak ada raw code).
5. Buka sidebar parameter table, pastikan usage badge **tidak visible** secara default. Hover baris -> badge muncul. Mouse leave -> badge hilang.
6. Buat formula yang mengandung `bp_*` dan `cp_*` -> chip tampil dengan **warna berbeda** (biru vs cyan). Test di light mode dan dark mode. Verifikasi di **compact mode** (tabel) dan **non-compact** (editor).
7. Buka palette -> kode **tidak** tampil sebagai teks. Hover label -> tooltip menampilkan kode.
8. Export Excel -> kolom "Kode Parameter" **tidak ada**.
9. Gunakan `docs/QA_GATE_D_PHASE2_CHECKLIST.md` untuk regression pass/fail.
10. Di editor formula, aktifkan mode `Tampilkan Nilai` -> pastikan preview berubah ke format `Label (nilai)` dan hasil akhir konsisten.
11. Trigger unknown token -> klik `Pilih Parameter Pengganti` -> pilih parameter -> pastikan formula ter-replace dan error hilang.

---

## Risiko dan Mitigasi

| Risiko | Mitigasi |
|--------|----------|
| Import error jadi kurang informatif tanpa kode | Gunakan nomor baris + label dari file import sebagai pengganti |
| Sync warnings API breaking client lain | Dual-field transition (`name` + `index`), deprecate `name` setelah 1 release |
| Chip-only view di tabel volume mematikan edit/autocomplete | Dual-view dengan toggle eksplisit. Textarea raw tetap accessible. Default = chip view, user toggle ke raw saat perlu edit |
| Usage badge hover tidak terlihat di mobile/touch | Pertimbangkan long-press atau tap-to-reveal untuk touch device |
| Warna chip terlalu mirip / kurang kontras | Gunakan `color-mix()` dengan persentase cukup tinggi (10% bg, 32% border), test di dark + light mode |
| Hapus kolom kode di export menghilangkan data interop | Export JSON/backup tetap menyertakan kode (machine-readable). Hanya export user-facing (Excel/CSV/PDF) yang dihapus |
| Regresi import/sync flow | Test otomatis + manual sebelum deploy |

---

## Rollout

### Milestone 1: MVP Release
1. **Batch A:** Patch 1 + 2 + 6 deploy bersamaan (error messages -- frontend + backend).
2. **Batch B:** Patch 3 + 4 + 5 deploy bersamaan (formula input UX + badge + chip color -- semua CSS/JS).

### Milestone 2: Full Completion
3. Patch 7 + 8 + 9 deploy bersamaan (help modal + export + palette).

### Milestone 3: UX+ Dampak Tinggi
4. Patch 10 + 11 deploy bersamaan (inline substitution + unknown token resolver).

### Rollback
Semua patch murni UI layer, data backend tidak berubah. Rollback = revert JS/CSS/HTML. Field `index` di API response **tidak perlu dihapus** saat rollback -- field ini backward compatible dan tidak merusak client manapun.

---

## Definition of Done

### MVP Release
1. Semua AC MVP (HR1-HR8) terpenuhi.
2. Tidak ada regresi test existing.
3. Dual-view formula editor berfungsi (chip default + toggle raw).
4. API sync warning backward compatible (dual-field).

### Full Completion
5. Semua AC Full (HR9-HR11) terpenuhi.
6. Dokumentasi user (`docs/PANDUAN_USER.md`) diupdate jika ada perubahan perilaku UI.
7. Field `"name"` di-deprecate dari API sync warnings (setelah 1 release cycle).

### UX+ Completion
8. Semua AC UX+ (HR12-HR13) terpenuhi.
9. User dapat memahami nilai formula lebih cepat dan menyelesaikan unknown token tanpa trial-and-error berulang.
