# Rencana Eksekusi & Tracking: Label-Only Formula Input

## Status
- Versi: v2.0
- Tanggal: 12 Februari 2026
- Owner: Tim implementasi Volume Pekerjaan
- Dokumen ini adalah source of truth untuk eksekusi fitur label-only formula input.

## Changelog
| Versi | Tanggal | Perubahan |
|---|---|---|
| v1.0 | 2026-02-12 | Draft awal: policy label-only, 6 temuan (T1-T6), 5 phase, chip composer sebagai editor utama. |
| v1.1 | 2026-02-12 | Review codebase: T5 dipecah jadi T5a/T5b, tambah T7 (import error) dan T8 (sync warning). |
| v1.2 | 2026-02-12 | Tambah sinkronisasi dokumen, test coverage matrix, QA gate checklist. |
| v1.3 | 2026-02-12 | Keputusan arsitektur: chip composer dipindah jadi spike opsional, go-live pakai dual-view hardened. Tracker diperluas (P1-6, P1-7, P2-4 spike). Phase 4 detail fungsi terdampak. |
| v2.0 | 2026-02-12 | **[ARSITEKTUR]** Ganti pendekatan Phase 2 dari dual-view hardened ke **Opsi C: Hybrid (Chip Preview + Label Input Masking)**. Textarea tetap dipakai tapi menampilkan label, bukan raw code. Serializer `rawToDisplay`/`displayToRaw` menggantikan chip composer. Effort turun signifikan, keyboard UX native, rollback lebih mudah. |

## Policy Tunggal (Wajib)
1. Semua surface user-facing wajib label-only.
2. User tidak boleh melihat atau mengetik `bp_*` / `cp_*` pada UI utama.
3. Kode internal hanya boleh dipakai di layer sistem:
   - penyimpanan DB
   - payload API internal
   - log server/telemetry
4. Larangan tampil di UI user:
   - input/textarea formula utama
   - chip/tag
   - autocomplete/suggestion list
   - modal warning/error/delete
   - tooltip user-facing
   - export user-facing
5. Pengecualian hanya untuk debug internal non-production, wajib di belakang akses staff-only.

## Mode Interaksi Resmi (Final)
Hanya ada 2 mode interaksi quantity/formula:
1. Inline input area di tabel volume (input cepat per baris).
2. Modal popup editor formula (editor utama).

Ketentuan:
- Tidak ada mode fullscreen terpisah.
- Modal formula selalu tampil sebagai popup standar.
- Inline dan modal wajib mengikuti policy label-only yang sama.

## Tujuan Utama
1. Menyederhanakan input quantity dan formula agar minim salah.
2. Menjadikan alur formula sepenuhnya berbasis label.
3. Menjaga kompatibilitas backend (raw code tetap internal).
4. Menyediakan rollback operasional yang jelas dan cepat.

## Kenapa Gate Harus Terukur
Tidak digunakan metrik persentase abstrak.
Gate menggunakan skenario pass/fail yang relevan langsung ke UX formula input.

Definisi lulus:
- Semua skenario mandatory di phase tersebut `PASS`.
- Tidak ada kebocoran kode internal di UI user-facing.

## Ruang Lingkup
- In scope:
  - Editor formula berbasis label (transparent masking).
  - Chip preview sebagai display default (read-only visual).
  - Resolver unknown token berbasis picker label.
  - Penyederhanaan flow quantity vs formula.
  - Penghapusan kebocoran kode internal di seluruh UI utama.
- Out of scope:
  - Perubahan schema DB.
  - Perubahan kontrak API inti yang bersifat breaking.
  - Full chip composer (rich-text editor) -- dijadwalkan sebagai spike opsional terpisah.

## Keputusan Arsitektur Phase 2: Opsi C (Hybrid)

### Pendekatan yang Dipilih
**Chip Preview + Transparent Label Input Masking**

Arsitektur 3 layer:
1. **Display layer (chip preview):** Read-only chip visual sebagai tampilan default. User melihat chip berwarna dengan label parameter.
2. **Edit layer (label input):** Saat user mengedit, input/textarea menampilkan **label** (bukan raw code). Contoh: `Panjang Dinding * Lebar Dinding + 10`.
3. **Data layer (raw code):** Di belakang layar, raw value tetap `bp_1 * bp_2 + 10`. Disimpan di `rawInputById`, dikirim ke server.

### Fungsi Inti Baru (2 fungsi)
```
rawToDisplayText(rawExpr, labels)
  Input:  "bp_1 * bp_2 + 10"
  Output: "Panjang Dinding * Lebar Dinding + 10"
  Cara:   Tokenize raw (VolFormula.tokenize) -> setiap token type=id -> lookup label -> reconstruct dengan whitespace asli.

displayToRaw(displayText, cursorMap)
  Input:  "Panjang Dinding * Lebar Dinding + 10"
  Output: "bp_1 * bp_2 + 10"
  Cara:   Lookup dari cursor position map yang dibangun saat rawToDisplayText() atau saat autocomplete insert.
```

### Aturan Parsing: Insert-Only (Bukan Free-Text Parse)

**Masalah:** Label parameter bisa mengandung karakter operator (contoh: `A2'-A'5`, `B3-B5`, `Panjang/2`). Free-text parsing `displayToRaw()` tidak bisa membedakan `-` sebagai operator vs `-` di dalam label.

**Solusi:** `displayToRaw()` **tidak melakukan free-text parsing**. Sebaliknya, digunakan **cursor position map**:

1. Saat `rawToDisplayText()` dijalankan (focus/load), bangun map: `{ charStart: code, charEnd: code }` untuk setiap label span di display text.
2. Saat autocomplete meng-insert label, tambahkan entry baru ke map: `{ insertStart: code, insertEnd: code }`.
3. Saat user mengetik di luar span yang ter-map (angka, operator), karakter langsung pass-through ke raw.
4. `displayToRaw()` hanya perlu: iterate map entries + literal characters -> reconstruct raw.

**Konsekuensi:**
- User **tidak bisa** mengetik label secara manual (karena tidak akan ter-map). Insert parameter **harus** via autocomplete/palette.
- Ini sekaligus menyelesaikan P3-1 (insert hanya dari picker) secara arsitektural, bukan hanya sebagai policy.
- Label dengan karakter spesial (`-`, `'`, `/`) aman karena tidak pernah di-parse sebagai operator.

### Alur Interaksi

**Inline (tabel volume):**
```
[Chip Preview: Panjang Dinding × Lebar Dinding]  ← default view
       ↓ klik / focus
[Input: Panjang Dinding * Lebar Dinding + 10]     ← edit mode (label text)
       ↓ user ketik / autocomplete insert label
[Input berubah] → displayToRaw() → rawInputById   ← data layer update
       ↓ blur / enter
[Chip Preview refresh dari raw baru]               ← kembali ke chip
```

**Modal editor:**
```
[Chip Preview area]        ← bagian atas, read-only visual
[Input/Textarea: label]    ← bagian bawah, edit area menampilkan label
[Autocomplete: label+nilai] ← suggestion tanpa kode
[Preview hasil: Label (nilai) = hasil] ← live preview
```

### Kenapa Opsi C, Bukan Chip Composer
| Aspek | Chip Composer | Opsi C: Hybrid |
|---|---|---|
| Effort kode baru | ~1000 baris (DOM model, cursor, serializer, keyboard nav) | ~250 baris (2 fungsi + integrasi) |
| Risiko bug | Tinggi (mini rich-text editor) | Rendah (translate string) |
| Keyboard UX | Custom (perlu belajar) | Native browser (familiar) |
| Copy-paste | Perlu handler khusus | Natural |
| Undo/redo | Perlu custom implementation | Browser native |
| Rollback | Tinggi (banyak kode baru) | Rendah (revert 2 fungsi) |
| Tujuan label-only | Tercapai | Tercapai |

### Edge Case: Label Duplikat
Dengan arsitektur insert-only, label duplikat **bukan masalah parsing**:
- Setiap insert dari autocomplete/palette sudah membawa code unik di cursor map.
- Dua parameter dengan label identik akan tampil sama di display, tapi map entries mereka berbeda.
- User membedakan via autocomplete suggestion (yang menampilkan label + nilai berbeda).

### Definisi Round-Trip Identity
Round-trip **bukan string equality** (`===`), melainkan **semantic identity**:
- Normalize whitespace (collapse multiple spaces, trim).
- Bandingkan token stream: sequence `[type, value]` harus identik.
- Contoh: `"bp_1*bp_2 + 10"` dan `"bp_1 * bp_2 + 10"` dianggap **identik** secara semantik.
- Test round-trip: `tokenize(displayToRaw(rawToDisplay(raw))) === tokenize(raw)`.

## Hasil Review Kondisi Saat Ini

| ID | Severity | Temuan | Dampak ke User | Target Perbaikan |
|---|---|---|---|---|
| T1 | Tinggi | Chip editor modal masih menampilkan `bp_*`/`cp_*` | User tetap terekspos kode internal | Hapus `chip-code` dari UI utama |
| T2 | Tinggi | Autocomplete menampilkan `Label (kode)` | User belajar kode, bukan label | Suggestion jadi label + nilai |
| T3 | Tinggi | Edit formula bergantung textarea raw | Alur tetap code-first | Label input masking: textarea menampilkan label |
| T4 | Sedang | Dialog delete masih ada `(kode: bp_*)` | Konsistensi label-only bocor | Ubah copy jadi label-only |
| T5a | Sedang | Humanizer error sudah ada, tapi belum konsisten di semua jalur | Pesan error bisa campur label + token mentah | Samakan formatter error label-only |
| T5b | Sedang | Resolver unknown token menampilkan token mentah | User tetap lihat simbol internal | Resolver copy label-only + CTA picker |
| T6 | Sedang | Mode formula bergantung awalan `=` | Membingungkan user non-teknis | Formula mode jadi aksi eksplisit |
| T7 | Sedang | Import parser bisa menampilkan kode mentah saat label kosong | Kebocoran kode di error import | Error import wajib row-based/label-only |
| T8 | Sedang | Sync warning response masih membawa `name` raw code | Potensi kebocoran saat dirender frontend | Warning UI wajib index-based + label-safe |

## Sinkronisasi Dokumen
1. Plan utama: `docs/RENCANA_LABEL_ONLY_FORMULA_INPUT.md` (dokumen ini).
2. QA eksekusi: `docs/QA_GATE_D_PHASE2_CHECKLIST.md` (6 gate, berurutan sesuai phase).
3. Dokumen historis: `docs/RENCANA_UI_UX_FORMULA_HUMAN_READABLE.md` (referensi lama, bukan source of truth eksekusi).

## Tracker Status
Gunakan status: `TODO`, `IN_PROGRESS`, `BLOCKED`, `DONE`.

| ID | Phase | Task | File/Area | Status | Evidensi |
|---|---|---|---|---|---|
| P0-1 | Phase 0 | Freeze baseline UX + rekam flow saat ini | Browser QA note | TODO | Video/screenshot baseline |
| P0-2 | Phase 0 | Definisikan skenario QA mandatory | QA checklist | TODO | Daftar skenario final |
| P0-3 | Phase 0 | Siapkan feature flag rollback UI label-only | settings + JS template data | TODO | Flag aktif di env |
| P1-1 | Phase 1 | Stabilkan kolom quantity tetap user-adjustable | `volume_pekerjaan.css/js` | DONE | Width control stabil |
| P1-2 | Phase 1 | Pastikan mode formula tidak memicu reflow liar | `volume_pekerjaan.css/js` | DONE | Tidak ada kolom loncat |
| P1-3 | Phase 1 | Hapus kode dari chip modal | `volume_pekerjaan.js` | TODO | Chip label-only |
| P1-4 | Phase 1 | Hapus kode dari autocomplete list | `volume_pekerjaan.js` | TODO | Suggestion label+nilai |
| P1-5 | Phase 1 | Ubah copy delete/resolver jadi label-only | `volume_pekerjaan.js` | TODO | Dialog tanpa `(kode: ...)` |
| P1-6 | Phase 1 | Import error message wajib label/row-only | `volume_pekerjaan.js` | TODO | Error import tanpa code leak |
| P1-7 | Phase 1 | Sync warning UI wajib index-based, non-code-leak | `views_api.py` + `volume_pekerjaan.js` | TODO | Warning aman di UI |
| P2-1 | Phase 2 | Implementasi `rawToDisplayText()` | `volume_pekerjaan.js` | TODO | Fungsi convert raw→label |
| P2-2 | Phase 2 | Implementasi `displayToRaw()` | `volume_pekerjaan.js` | TODO | Fungsi convert label→raw |
| P2-3 | Phase 2 | Integrasi label masking di inline input | `volume_pekerjaan.js` | TODO | Inline input menampilkan label |
| P2-4 | Phase 2 | Integrasi label masking di modal editor | `volume_pekerjaan.js/html` | TODO | Modal textarea menampilkan label |
| P2-5 | Phase 2 | Autocomplete insert label (bukan code) | `volume_pekerjaan.js` | TODO | Insert label, simpan raw |
| P2-6 | Phase 2 | Round-trip test: raw→display→raw identity | `volume_pekerjaan.js` | TODO | Tidak ada data drift |
| P2-7 | Phase 2 | Insert parameter hanya dari picker/autocomplete (enforced by cursor map) | `volume_pekerjaan.js` | TODO | Free-text label insert diblokir |
| P3-2 | Phase 3 | Unknown token resolver via picker + auto replace | `volume_pekerjaan.js/html` | TODO | Recovery cepat |
| P3-3 | Phase 3 | Validasi realtime sintaks (kurung/operator/kosong) | `volume_pekerjaan.js` | TODO | Error preventif jelas |
| P4-1 | Phase 4 | Formula mode jadi aksi eksplisit (bukan `=`-driven) | `volume_pekerjaan.js/html` | TODO | Flow lebih sederhana |
| P4-2 | Phase 4 | Preview hasil konsisten label + nilai | `volume_pekerjaan.js` | TODO | Preview konsisten |
| P5-1 | Phase 5 | Regression test kritikal (unit/integration/e2e) | tests + manual QA | TODO | Semua case mandatory PASS |
| P5-2 | Phase 5 | Update panduan user | `docs/PANDUAN_USER.md` | TODO | Panduan sinkron |
| P5-3 | Phase 5 | Rollback drill verifikasi di staging | runbook + env toggle | TODO | Bukti drill PASS |

## Phase Plan

## Phase 0 - Baseline, Policy, dan Guardrail
Tujuan: menyepakati aturan dan menyiapkan safety rail.

Checklist:
- [ ] Baseline flow saat ini didokumentasikan.
- [ ] Skenario QA mandatory disepakati.
- [ ] Feature flag rollback label-only tersedia.

Gate:
- [ ] Policy tunggal diterapkan sebagai referensi tim.
- [ ] Semua pihak sepakat source of truth dokumen.
- [ ] `P0-3` selesai sebelum phase dengan perubahan behavior editor dijalankan.

## Phase 1 - Quick Win Kebocoran Kode
Tujuan: menutup kebocoran kode internal dengan risiko rendah.

Checklist:
- [x] Kolom quantity stabil dan tetap user-adjustable.
- [x] Tidak ada layout jump saat hide/show input formula.
- [ ] Chip editor modal label-only.
- [ ] Autocomplete label-only.
- [ ] Copy delete/resolver label-only.
- [ ] Import error message label/row-only.
- [ ] Sync warning UI tidak menampilkan raw code.

Gate (mandatory):
- [ ] `G1-1` Di chip editor modal tidak ada teks `bp_`/`cp_`.
- [ ] `G1-2` Di autocomplete tidak ada pola `(...)` berisi kode.
- [ ] `G1-3` Dialog delete/resolver tidak menampilkan kode.
- [ ] `G1-4` Error import tidak menampilkan `bp_`/`cp_`.
- [ ] `G1-5` Toast/sync warning tidak menampilkan `name` raw.

## Phase 2 - Core Label-Only Editor (Opsi C: Hybrid)
Tujuan: user mengedit formula tanpa interaksi raw code. Input menampilkan label, chip preview sebagai tampilan default.

Checklist:
- [ ] `rawToDisplayText()` berfungsi: raw→label text untuk semua token.
- [ ] `displayToRaw()` berfungsi: label text→raw untuk semua token.
- [ ] Inline input menampilkan label saat formula mode aktif.
- [ ] Modal editor textarea menampilkan label.
- [ ] Autocomplete meng-insert label (data layer menyimpan raw).
- [ ] Round-trip `raw→display→raw` semantic identity (token stream ekuivalen).
- [ ] Cursor map akurat setelah insert/edit/load.
- [ ] Formula legacy bisa dibaca dan diedit lewat label view.
- [ ] Chip preview auto-refresh setiap input berubah.

Gate (mandatory):
- [ ] `G2-1` User membuat formula baru tanpa melihat kode.
- [ ] `G2-2` User edit formula lama tanpa mengetik kode.
- [ ] `G2-3` Save/reload tidak mengubah makna formula.
- [ ] `G2-4` Round-trip test `raw→display→raw` semantic identity pass untuk semua formula existing.

## Phase 3 - Anti-Keliru dan Recovery
Tujuan: mengurangi human error dan mempercepat perbaikan.

Catatan: Insert parameter hanya via picker sudah di-enforce oleh cursor map di Phase 2 (P2-7).

Checklist:
- [ ] Unknown token dapat diselesaikan via resolver picker.
- [ ] Validasi sintaks realtime aktif.

Gate (mandatory):
- [ ] `G3-1` Unknown token bisa diperbaiki tanpa raw edit.
- [ ] `G3-2` Error sintaks utama tertangkap sebelum apply.

## Phase 4 - Simplifikasi Flow Quantity
Tujuan: alur input lebih mudah dipahami user non-teknis.

Checklist:
- [ ] Numeric quantity flow tetap paling sederhana.
- [ ] Formula mode aktif dari aksi eksplisit user.
- [ ] Preview label+nilai konsisten antar area.
- [ ] Refactor fungsi terdampak:
  - `isFormulaMode`
  - auto-enable handler saat input `=`
  - shortcut `Ctrl+Space`
  - state `fxModeById`

Gate (mandatory):
- [ ] `G4-1` User baru bisa menyelesaikan 3 skenario formula dasar tanpa arahan teknis.

## Phase 5 - QA, Dokumentasi, Rollout
Tujuan: siap produksi dengan risiko rendah.

Checklist:
- [ ] Semua test kritikal lulus.
- [ ] Manual E2E mandatory lulus.
- [ ] Dokumentasi user sudah sinkron.
- [ ] Rollback drill lulus.

Gate (mandatory):
- [ ] Semua acceptance criteria final `PASS`.

## Acceptance Criteria Final
1. Tidak ada kebocoran `bp_*`/`cp_*` di UI user-facing utama.
2. User dapat membuat/mengedit formula melalui label text dan chip preview.
3. Formula legacy tetap kompatibel setelah load/save.
4. Round-trip `raw→display→raw` semantic identity terjaga (token stream ekuivalen, no data drift).
5. Unknown token bisa diselesaikan via picker tanpa raw edit.
6. Lebar kolom quantity stabil dan tetap bisa diatur user.
7. Tidak ada regresi save/sync/import/export utama.
8. Keyboard shortcut native (copy/paste, undo/redo, arrow keys) tetap berfungsi.

## Test Coverage Matrix (Kritikal)

| Area | Jenis Test | Wajib |
|---|---|---|
| `rawToDisplayText` | Unit: semua token type (id, number, operator, function, paren) | Ya |
| `displayToRaw` | Unit: label→raw untuk single/multi token, edge cases | Ya |
| Round-trip identity | Unit: `tokenize(displayToRaw(rawToDisplayText(raw))) === tokenize(raw)` (semantic) | Ya |
| Cursor map integrity | Unit: map entries akurat setelah insert/edit/load, label dengan `-`/`'`/`/` aman | Ya |
| Formula evaluator | Unit: operator, fungsi, kurung, edge case | Ya |
| Import validation | Integration: error import label/row-only | Ya |
| API sync | Integration: create/sync/conflict 409 | Ya |
| Sync warning safety | Integration: warning payload tidak leak ke UI | Ya |
| Legacy compatibility | Integration: formula lama tetap valid via label masking | Ya |
| Inline label input | E2E manual: focus→label view, blur→chip preview | Ya |
| Modal label editor | E2E manual: create/edit/delete formula via label | Ya |
| Unknown resolver | E2E manual: replace token & re-evaluate | Ya |
| No-code leak | E2E manual: chip/autocomplete/modal/export/import/sync | Ya |

## Fallback & Rollback Operasional
Prinsip: rollback harus cepat tanpa migrasi data.

Prasyarat:
- Feature flag `FORMULA_LABEL_ONLY_UI_ENABLED` tersedia.
- Mode lama tetap tersedia saat flag dimatikan.

Rollback langkah cepat:
1. Set env `FORMULA_LABEL_ONLY_UI_ENABLED=0`.
2. Restart/reload service aplikasi.
3. Invalidate cache static assets (jika ada CDN).
4. Jalankan smoke test:
   - buka page volume
   - edit quantity numeric
   - edit formula dasar
   - simpan dan reload
5. Verifikasi tidak ada data loss pada formula tersimpan.

Kriteria rollback sukses:
- UI kembali ke mode stabil sebelumnya.
- Save/sync tetap berjalan.
- Tidak ada error server baru setelah rollback.
- `rawInputById` tidak terkorupsi oleh label masking (karena data layer selalu raw).

Catatan: Rollback mode adalah **emergency non-compliant sementara** -- raw code akan visible di input selama flag dimatikan. Ini bukan kondisi target, melainkan fallback darurat sampai bug diperbaiki dan flag diaktifkan kembali. Policy label-only tetap berlaku sebagai target permanen.

## Risiko & Mitigasi
1. **Risiko:** `displayToRaw()` gagal resolve label ke code (label berubah setelah save).
   **Mitigasi:** Simpan mapping snapshot saat focus, validasi sebelum blur/save, fallback ke raw terakhir yang valid.

2. **Risiko:** Label mengandung karakter operator (`-`, `'`, `/`) menyebabkan parsing error.
   **Mitigasi:** Arsitektur insert-only dengan cursor map. Label tidak pernah di-parse sebagai formula -- posisi setiap label span sudah diketahui dari map. Free-text typing label diblokir.

3. **Risiko:** Round-trip `raw→display→raw` tidak semantic-identity (data drift).
   **Mitigasi:** Unit test wajib blocker. Bandingkan token stream, bukan string literal. Jika token stream berbeda, jangan save (tampilkan warning).

4. **Risiko:** Rollback tidak bisa cepat.
   **Mitigasi:** Feature flag wajib tersedia sebelum Phase 2 dimulai. Data layer selalu raw, tidak ada migrasi data saat rollback.

5. **Risiko:** Autocomplete insert mismatch (insert label tapi raw tidak update).
   **Mitigasi:** Autocomplete handler wajib update kedua layer (display + raw) secara atomik.

## Rencana Rollout
1. Tahap A (internal): aktif di dev/staging.
2. Tahap B (limited): 1-2 project real sebagai pilot.
3. Tahap C (full): aktif global setelah gate Phase 5 PASS.

## Log Eksekusi
Isi harian:
- Tanggal:
- Task ID:
- Perubahan:
- Hasil test:
- Issue/Blocker:
- Next action:
