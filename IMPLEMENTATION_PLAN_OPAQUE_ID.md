# Rencana Implementasi: Opaque ID Parameter System

**Tanggal:** 12 Februari 2026
**Penyusun:** Tim Engineering Internal
**Referensi:** REVIEW_PARAMETER_FORMULA.md v1.2
**Status:** IMPLEMENTED v1.11 -- migration executed on current target env, menunggu QA sign-off Gate D/Phase 2 + monitoring window
**Checklist:** OPAQUE_ID_CHECKLIST.md

---

## DAFTAR ISI

1. [Ringkasan Perubahan](#1-ringkasan-perubahan)
2. [Arsitektur Baru vs Lama](#2-arsitektur-baru-vs-lama)
3. [Skema Penamaan Kode & ID Generation](#3-skema-penamaan-kode--id-generation)
4. [Dampak ke Komponen (Full Surface Audit)](#4-dampak-ke-komponen-full-surface-audit)
5. [Agenda Implementasi](#5-agenda-implementasi)
6. [Strategi Migrasi Data Existing](#6-strategi-migrasi-data-existing)
7. [Import/Export, Template, Backup & Copy](#7-importexport-template-backup--copy)
8. [Acceptance Criteria](#8-acceptance-criteria)
9. [Test Plan](#9-test-plan)
10. [Rollback Plan](#10-rollback-plan)
11. [Item yang Gugur dari Roadmap v1.2](#11-item-yang-gugur-dari-roadmap-v12)

---

## 1. Ringkasan Perubahan

### Prinsip Utama

**SEBELUM (kode deskriptif):**
- Kode di-generate dari label via `slugifyName()` / `normalizeParamCode()`
- User harus tahu kode untuk menulis formula
- Rename label bisa merusak kode (bug T2)
- Collision kode mungkin terjadi ("Panjang (m)" dan "Panjang m" -> `panjang_m`)

**SESUDAH (opaque ID):**
- Kode di-generate otomatis oleh **server** (`bp_1`, `bp_2`, `cp_1`, `cp_2`, ...)
- User **tidak pernah melihat atau mengetik kode** -- interaksi sepenuhnya via label
- Rename label **100% aman** -- kode tidak pernah berubah
- Collision dicegah melalui **server-side generation** dengan DB-level uniqueness constraint

### Konsep Inti

```
User membuat parameter:
  Label: "Panjang Dinding Lt. 1"   ->  Kode: bp_1  (server-generated)
  Label: "Lebar Dinding Lt. 1"     ->  Kode: bp_2  (server-generated)

User membuat formula:
  Label: "Luas Dinding Lt. 1"      ->  Kode: cp_1  (server-generated)

Storage formula:   bp_1 * bp_2
Display formula:   Panjang Dinding Lt. 1 * Lebar Dinding Lt. 1
                   (ditampilkan sebagai chip/tag berwarna)
```

---

## 2. Arsitektur Baru vs Lama

### 2.1 Alur Pembuatan Parameter

**LAMA:**
```
User ketik label -> slugifyName(label) [CLIENT] -> kode deskriptif -> sync ke server
                    (bisa collision, bisa panjang, bisa ambigu, multi-tab race)
```

**BARU:**
```
User ketik label -> POST ke server -> server generate kode -> response ke client
                    (unik, pendek, stabil, no race condition)
```

### 2.2 Alur Penulisan Formula

**LAMA:**
```
User ketik di formula editor: = panjang_dinding_lt_1 * lebar_dinding_lt_1
                                (harus hafal/copy kode)
Display:                      = panjang_dinding_lt_1 * lebar_dinding_lt_1
Preview:                      10 * 5 = 50
```

**BARU:**
```
User ketik di formula editor: = [Panjang Dinding Lt. 1] * [Lebar Dinding Lt. 1]
                                (pilih dari autocomplete, muncul sebagai chip)
Storage:                      = bp_1 * bp_2
                                (opaque, untuk sistem)
Display:                      = [Panjang Dinding Lt. 1] * [Lebar Dinding Lt. 1]
                                (chip berwarna, untuk manusia)
Preview nilai:                10 * 5 = 50
```

### 2.3 Data Flow

```
+-------------------------------------------------------------------+
|                        BROWSER (Client)                            |
|                                                                    |
|  State:                                                            |
|    variables    = { bp_1: 10, bp_2: 5, ... }                       |
|    varLabels    = { bp_1: "Panjang Dinding Lt.1", bp_2: "Lebar.."}|
|    computedParams = { cp_1: { expression: "bp_1 * bp_2", ... } }  |
|                                                                    |
|  TIDAK ADA counter di client -- kode selalu dari server.           |
|                                                                    |
|  Display Layer:                                                    |
|    formula editor   -> chip/tag UI (tampil label, simpan kode)     |
|    formula preview  -> translate kode -> label untuk tampilan      |
|    error messages   -> "Variabel: Panjang Dinding (bp_1) error"   |
|    autocomplete     -> search by label, insert kode                |
|                                                                    |
|  Sync: debounced -> server (mode: replace)                         |
|  Create: POST -> server generate name -> response with name        |
+-------------------------------------------------------------------+
          |                                        ^
          v                                        |
+-------------------------------------------------------------------+
|                        SERVER (Django)                              |
|                                                                    |
|  ID Generation (authoritative):                                    |
|    ParameterSequence.last_num++ (SELECT FOR UPDATE, monotonic)     |
|    next_bp = bp_{last_num}, next_cp = cp_{last_num}                |
|    DB unique_together (project, name) sebagai safety net            |
|                                                                    |
|  ProjectParameter:      name="bp_1", label="Panjang...", value=10 |
|  ProjectComputedParameter: name="cp_1", expression="bp_1 * bp_2"  |
|                                                                    |
|  Validasi (konsisten di semua jalur, per-model):                   |
|    ProjectParameter.name:        ^bp_[1-9][0-9]*$                  |
|    ProjectComputedParameter.name: ^cp_[1-9][0-9]*$                 |
|    Diterapkan di: model clean(), API sync, API create,             |
|                   import, backup restore, copy service              |
+-------------------------------------------------------------------+
```

---

## 3. Skema Penamaan Kode & ID Generation

### 3.1 Format

| Tipe | Prefix | Format | Contoh |
|------|--------|--------|--------|
| Base Parameter | `bp_` | `bp_{counter}` | `bp_1`, `bp_2`, `bp_3` |
| Computed Parameter | `cp_` | `cp_{counter}` | `cp_1`, `cp_2`, `cp_3` |

### 3.2 Server-Side ID Generation (Keputusan Arsitektur)

**Mengapa server-side, bukan client-side:**

| Aspek | Client-side | Server-side (dipilih) |
|-------|-------------|----------------------|
| Multi-tab race | 2 tab bisa buat `bp_6` bersamaan -> collision | Server serialize via SELECT FOR UPDATE -> aman |
| Multi-user race | Sama -- collision | Sama -- aman |
| Offline support | Bisa buat ID tanpa server | Tidak bisa buat parameter offline |
| Kompleksitas | Butuh lock/revision di client | Sederhana, DB sebagai source of truth |

**Trade-off:** Mengorbankan offline-create (yang saat ini juga tidak benar-benar reliable karena sync bisa conflict). Gain: collision dicegah melalui row-level locking + DB unique constraint sebagai safety net.

**Implementasi server-side: dedicated counter table**

Menggunakan `max(existing) + 1` **tidak menjamin monoton naik** -- jika ID tertinggi dihapus, nomor bisa terpakai lagi. Solusi: dedicated counter table yang hanya naik, tidak pernah turun.

```python
# Model counter baru (perlu migration)
class ParameterSequence(models.Model):
    """Monotonic counter per project per type. Never decrements."""
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    prefix = models.CharField(max_length=4)  # 'bp' atau 'cp'
    last_num = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [('project', 'prefix')]


def generate_bp_name(project):
    return _next_opaque_name(project, 'bp')

def generate_cp_name(project):
    return _next_opaque_name(project, 'cp')

def _next_opaque_name(project, prefix):
    """
    Atomic increment counter. Menjamin:
    - Monoton naik (hapus bp_5 lalu create -> bp_6, bukan bp_5 lagi)
    - No race condition (SELECT FOR UPDATE pada 1 row counter)
    - No reuse
    """
    seq, created = ParameterSequence.objects.select_for_update().get_or_create(
        project=project, prefix=prefix,
        defaults={'last_num': 0}
    )
    seq.last_num += 1
    seq.save(update_fields=['last_num'])
    return f'{prefix}_{seq.last_num}'
```

**Inisialisasi counter saat migration data existing:**
```python
# Dalam migration script, setelah remap semua params:
for project in Project.objects.all():
    for prefix, model in [('bp', ProjectParameter), ('cp', ProjectComputedParameter)]:
        max_num = 0
        for name in model.objects.filter(
            project=project, name__startswith=f'{prefix}_'
        ).values_list('name', flat=True):
            try:
                max_num = max(max_num, int(name.split('_', 1)[1]))
            except (ValueError, IndexError):
                pass
        if max_num > 0:
            ParameterSequence.objects.update_or_create(
                project=project, prefix=prefix,
                defaults={'last_num': max_num}
            )
```

**Catatan penting:**
- `select_for_update()` pada **1 row counter** -- minimal locking, maximal concurrency.
- `unique_together (project, name)` di DB parameter sebagai safety net.
- Counter **monoton naik** -- `last_num` hanya increment, tidak pernah decrement meskipun parameter dihapus.
- Base parameter generate `bp_N`, computed generate `cp_N` -- tidak ada cross-model query.
- Client tidak perlu track counter -- selalu minta ke server.
- Perlu **1 migration DB** untuk create tabel `ParameterSequence`.

### 3.3 Keuntungan Format Ini

- `bp_` vs `cp_` membedakan tipe saat debugging/logging.
- Pendek (max ~8 char untuk ratusan parameter) -- jauh di bawah limit 100 char DB.
- Tidak akan pernah collision dengan reserved keyword (`sum`, `min`, `pi`, dll).
- Regex validasi **per-model** (bukan shared):
  - `ProjectParameter.name`: `^bp_[1-9][0-9]*$`
  - `ProjectComputedParameter.name`: `^cp_[1-9][0-9]*$`
  - Ini mencegah `cp_` masuk ke tabel base dan sebaliknya.
  - `[1-9][0-9]*` mencegah `bp_0` atau `bp_01` (leading zero).

---

## 4. Dampak ke Komponen (Full Surface Audit)

### 4.1 File yang Perlu Diubah

| File | Perubahan | Effort |
|------|-----------|--------|
| **Core JS/HTML/CSS** | | |
| `volume_pekerjaan.js` | Code generation, render, formula editor, autocomplete, preview, sync | **Tinggi** |
| `volume_pekerjaan.html` | Update sidebar UI, chip styling, help text, placeholder formula | **Sedang** |
| `volume_pekerjaan.css` | Styling chip/tag parameter di formula editor | **Sedang** |
| `vol_formula_engine.js` | Expose tokenizer sebagai public API (saat ini hanya `evaluate` ter-expose) | **Rendah** |
| **Backend API** | | |
| `views_api.py` (sync/CRUD) | Server-side ID generation, update regex, per-item warnings, name immutable on PUT | **Sedang** |
| `models.py` | Update `clean()` validation di kedua model untuk enforce format opaque ID | **Rendah** |
| **Export/Import/Backup** | | |
| `views_api.py` (`_build_export_data`) | Tambah export ProjectComputedParameter (saat ini TIDAK diekspor) | **Sedang** |
| `views_api.py` (`export_project_full_json`) | Tambah computed params di full backup export | **Sedang** |
| `views_api.py` (`import_project_from_json`) | Tambah import ProjectComputedParameter + remap kode | **Sedang** |
| `views_api.py` (`_import_template_data`) | Tambah computed params + remap kode saat import template | **Sedang** |
| **Copy Service** | | |
| `services.py` (`_copy_project_parameters`) | Remap kode di project target + copy computed params (saat ini TIDAK di-copy) | **Sedang** |
| `services.py` (copy orchestrator) | Tambah step `_copy_project_computed_parameters()` | **Sedang** |
| **Volume Export Adapter** | | |
| `volume_pekerjaan_adapter.py` | Update `_build_parameter_segment()`: pakai label dari DB, bukan `name.replace('_',' ')` | **Rendah** |
| **Dokumentasi** | | |
| `PANDUAN_USER.md` | Update panduan formula: hilangkan referensi kode manual, jelaskan chip/autocomplete | **Rendah** |

### 4.2 Temuan Kritis dari Audit: ProjectComputedParameter Gap

**Saat ini ProjectComputedParameter TIDAK di-handle di:**

| Jalur Data | ProjectParameter | ProjectComputedParameter | Status |
|-----------|------------------|--------------------------|--------|
| Export full backup (`_build_export_data`) | Diekspor | **TIDAK diekspor** | BUG |
| Export template | Diekspor | **TIDAK diekspor** | BUG |
| Import full backup (`import_project_from_json`) | Diimpor | **TIDAK diimpor** | BUG |
| Import template (`_import_template_data`) | Diimpor | **TIDAK diimpor** | BUG |
| Copy project (`services.py`) | Di-copy | **TIDAK di-copy** | BUG |
| API sync/list | Ada | Ada | OK |
| Volume export adapter | Dipakai (display) | Tidak relevan | OK |

**Ini adalah bug existing yang harus diperbaiki sebelum migrasi opaque ID.**
Jika computed params hilang saat backup/copy, formula yang mereferensikan `cp_N` akan rusak.

### 4.3 Tokenizer Engine: Perlu Expose Public API

**Temuan:** `vol_formula_engine.js` saat ini hanya expose `evaluate()` (line 380):
```javascript
G.VolFormula = { evaluate };
```

**Kebutuhan migration & runtime:**
- Migration script perlu tokenizer untuk token-level replace kode lama -> kode baru.
- Runtime display layer perlu tokenizer untuk translate kode -> label di formula.

**Solusi:** Expose `tokenize()` sebagai public API:
```javascript
G.VolFormula = { evaluate, tokenize };
```

Untuk migration script Python, buat Python tokenizer sederhana yang mirror logika JS, atau jalankan migration via Django management command yang memanggil Node.js script.

### 4.4 Fungsi JS yang Terdampak

| Fungsi | Line | Perubahan |
|--------|------|-----------|
| `normalizeParamCode()` | 1584-1596 | **Hapus** -- tidak perlu slugify lagi |
| `slugifyName()` | 1598-1600 | **Hapus** |
| Add parameter handler | 1893-1954 | Ubah: POST ke server, terima `bp_N` dari response |
| Add computed handler | 1958-2019 | Ubah: POST ke server, terima `cp_N` dari response |
| `renderVarTable()` | 1602-1757 | Ubah: tampilkan label saja, hilangkan hint kode |
| `renderComputedTable()` | 1760-1889 | Ubah: tampilkan label, formula preview pakai label |
| `buildFormulaPreview()` | 1454-1474 | Ubah: tambah mode Label (translate kode -> label) |
| `getCaretIdentifier()` | 761-773 | **Perlu evaluasi** -- mungkin diganti dengan chip-based input |
| Autocomplete system | 798-830+ | Ubah: search by label, insert kode di belakang layar |
| `evaluateComputedParams()` | 946-1012 | **Minimal** -- scope sudah pakai kode sebagai key |
| `syncParamsToServer()` | 2795-2823 | Ubah: mode `merge` -> `replace` |
| `loadParamsFromServer()` | 2856-2890 | Ubah: tidak perlu recalculate counter (server handle) |

### 4.5 Backend yang Terdampak (Semua Jalur)

| Jalur | File:Line | Perubahan |
|-------|-----------|-----------|
| API create parameter | `views_api.py:2793` | Server generate `bp_N`, return ke client |
| API sync parameters | `views_api.py:2938-3040` | Update regex `^bp_[1-9][0-9]*$`, warnings[] |
| API sync computed | `views_api.py:3078-3159` | Update regex `^cp_[1-9][0-9]*$`, warnings[] |
| API detail PUT | `views_api.py:~2862` | `name` field immutable on update |
| Model clean() base | `models.py:1040` | Enforce opaque ID format |
| Model clean() computed | `models.py:1105` | Enforce opaque ID format |
| Export full backup | `views_api.py:~7305` | Tambah computed params |
| Export template | `views_api.py:~7100` | Tambah computed params |
| Import full backup | `views_api.py:~7656` | Tambah computed params + remap |
| Import template | `views_api.py:~8225` | Tambah computed params + remap |
| Copy service | `services.py:~3718` | Tambah `_copy_project_computed_parameters()` |

### 4.6 Gap Kondisi Kode Saat Ini vs Target

Untuk kejelasan: berikut titik-titik kode aktual yang **harus berubah** saat implementasi.

| Komponen | Kondisi Saat Ini | Target Opaque ID |
|----------|-----------------|------------------|
| Backend sync (base) | Client kirim nama, regex `^[a-z_][a-z0-9_]*$` (`views_api.py:2984,3008`) | Server generate `bp_N`, regex `^bp_[1-9][0-9]*$` |
| Backend sync (computed) | Client kirim nama, regex sama (`views_api.py:3119`) | Server generate `cp_N`, regex `^cp_[1-9][0-9]*$` |
| Frontend create base | `slugifyName(label)` (`volume_pekerjaan.js:1931`) | POST ke server, terima `bp_N` dari response |
| Frontend create computed | `slugifyName(label)` (`volume_pekerjaan.js:1995`) | POST ke server, terima `cp_N` dari response |
| Frontend sync mode | `mode: 'merge'` (`volume_pekerjaan.js:2808`) | `mode: 'replace'` + `updated_at` check |
| Backend conflict detection | Tidak ada -- sync selalu diterima (`views_api.py:2938,3078`) | Sertakan `updated_at`, reject 409 jika stale |
| Export key naming | Campuran `parameters` / `project_parameters` (`views_api.py:7052,7135,7344`) | Canonical `project_parameters` + `project_computed_parameters` |
| Import key reading | Baca `parameters` / `project_parameters` tanpa fallback (`views_api.py:8226`) | Baca canonical + fallback legacy |

---

## 5. Agenda Implementasi

### Phase 0: Impact Audit & Prerequisites (1-2 hari)

**Fokus:** Tutup gap existing sebelum migrasi. Tanpa phase ini, migrasi akan kehilangan data.

| # | Item | Effort | Detail |
|---|------|--------|--------|
| 0.1 | Tambah ProjectComputedParameter di export full backup | Sedang | `_build_export_data()`, `export_project_full_json()` |
| 0.2 | Tambah ProjectComputedParameter di export template | Sedang | `_build_export_data()` template mode |
| 0.3 | Tambah ProjectComputedParameter di import full backup | Sedang | `import_project_from_json()` |
| 0.4 | Tambah ProjectComputedParameter di import template | Sedang | `_import_template_data()` |
| 0.5 | Tambah `_copy_project_computed_parameters()` di copy service | Sedang | `services.py`, termasuk remap expression |
| 0.6 | Expose `tokenize()` di `vol_formula_engine.js` | Rendah | Tambah ke `G.VolFormula` |
| 0.7 | Buat Python tokenizer mirror untuk migration script | Sedang | Management command atau standalone script |
| 0.8 | Definisikan format export v2 (backward compatible) | Rendah | Bump `export_version` ke `"3.0"` + tambah `project_computed_parameters` section |

**Mengapa Phase 0 terpisah:** Item 0.1-0.5 adalah bug fixes yang berdiri sendiri dan bermanfaat bahkan tanpa migrasi opaque ID. Bisa di-deploy duluan.

### Phase 1: Foundation -- Server-Side Opaque ID (2-3 hari)

**Fokus:** Ganti sistem kode, stabilkan sync, server-side generation.

| # | Item | Effort | Detail |
|---|------|--------|--------|
| 1.1 | Server-side `generate_next_param_name()` dalam `@transaction.atomic` | Sedang | Prevent multi-tab/user collision |
| 1.2 | Update API create: server generate kode, return di response | Sedang | Client tidak generate kode sendiri |
| 1.3 | Update API sync: regex per-model (`^bp_[1-9][0-9]*$` / `^cp_[1-9][0-9]*$`), per-item warnings | Sedang | Semua jalur sync |
| 1.4 | Update model `clean()` di ProjectParameter dan ProjectComputedParameter | Rendah | Enforce opaque format |
| 1.5 | Ubah add parameter flow di JS: POST ke server, terima kode dari response | Sedang | Handler line 1893-1954 |
| 1.6 | Ubah add computed flow di JS: POST ke server, terima kode dari response | Sedang | Handler line 1958-2019 |
| 1.7 | Fix sync mode: `merge` -> `replace` untuk base parameter | Rendah | Line 2808 |
| 1.8 | Minimal conflict detection: sertakan `updated_at` di sync payload, backend reject jika stale (409) | Sedang | Lihat detail implementasi di bawah tabel |
| 1.9 | Hapus `normalizeParamCode()`, `slugifyName()` dari JS | Rendah | Dead code removal |
| 1.10 | Ubah render: tampilkan label saja, hilangkan hint kode | Sedang | `renderVarTable()`, `renderComputedTable()` |
| 1.11 | Validasi konsisten di semua jalur create/update (API, import, backup, copy) | Sedang | Guard di semua entry points |

**Detail implementasi item 1.8 -- Conflict Detection 409:**

Endpoint yang perlu diubah:
- `api_project_parameters_sync()` (`views_api.py:2938`) -- base parameter sync
- `api_project_computed_parameters_sync()` (`views_api.py:3078`) -- computed parameter sync

Mekanisme:
```
Client mengirim (format sesuai kontrak sync saat ini -- dict, bukan array):
  {
    "parameters": {
      "bp_1": { "value": 10, "label": "Panjang Dinding" },
      "bp_2": { "value": 5, "label": "Lebar Dinding" }
    },
    "mode": "replace",
    "last_sync_at": "2026-02-11T10:00:00Z"   // <-- field baru
  }

Server memeriksa (SEBELUM proses replace/merge):
  latest_update = ProjectParameter.objects.filter(project=project) \
                    .aggregate(Max('updated_at'))['updated_at__max']
  client_ts = parse_datetime(payload.get('last_sync_at'))
  if latest_update and client_ts and latest_update > client_ts:
      return JsonResponse({
          'ok': False,
          'error': 'conflict',
          'server_updated_at': latest_update.isoformat()
      }, status=409)
  # ... lanjut proses sync ...
  # Setelah sukses, response sertakan timestamp:
  return JsonResponse({'ok': True, ..., 'synced_at': now().isoformat()})

Client handle 409:
  -> Simpan `synced_at` dari response sukses sebagai `last_sync_at` berikutnya
  -> Jika 409: Phase 1 = simple alert + reload
  -> Phase 4: UX prompt dengan opsi reload/keep local (item 4.3)
```

Kontrak yang sama berlaku untuk `api_project_computed_parameters_sync()` dengan
key `computed_parameters` (dict) dan query ke `ProjectComputedParameter`.

**Catatan:** `updated_at` sudah tersedia di kedua model karena inherit `TimeStampedModel`. Client harus track `last_sync_at` saat terakhir berhasil sync/load dari server.

### Phase 2: Formula Editor -- Chip/Tag UI (3-4 hari)

**Fokus:** User menulis formula via autocomplete dengan tampilan chip/label.

| # | Item | Effort | Detail |
|---|------|--------|--------|
| 2.1 | Chip/tag rendering di formula editor (display label, store kode) | Tinggi | Komponen UI baru |
| 2.2 | Autocomplete wajib: search by label, insert kode sebagai chip | Sedang | Refactor system line 798-830+ |
| 2.3 | `buildFormulaPreview()` mode Label (translate kode -> label) | Sedang | Pakai exposed tokenizer |
| 2.4 | Parameter Palette modal (browse semua parameter, klik insert) | Sedang | Komponen UI baru |
| 2.5 | Error messages pakai label: "Variabel: Panjang Dinding (bp_1) error" | Rendah | Update evaluateComputedParams + formula error |
| 2.6 | Guard race condition: dirty state tidak ketimpa fetch server | Sedang | isDirty flag + prompt |
| 2.7 | Update help text + placeholder di `volume_pekerjaan.html` | Rendah | Line 462, 508 |
| 2.8 | Update `PANDUAN_USER.md` | Rendah | Hilangkan referensi kode manual |

### Phase 3: Migration & Data Integrity (2-3 hari)

**Fokus:** Migrasi data existing, import/export remap, backward compatibility.

| # | Item | Effort | Detail |
|---|------|--------|--------|
| 3.1 | Migration script: rename kode existing ke opaque format | Tinggi | Lihat [Section 6](#6-strategi-migrasi-data-existing) |
| 3.2 | Cross-project remap: import/copy/restore selalu regenerate kode target | Sedang | Lihat [Section 7](#7-importexport-template-backup--copy) |
| 3.3 | Export ke Excel/CSV: formula ditampilkan dengan label | Sedang | Volume adapter update |
| 3.4 | Backward compatibility: import file v1 (kode deskriptif lama) | Sedang | Auto-remap ke opaque |
| 3.5 | Backup restore: computed params + remap kode | Sedang | Full cycle test |

### Phase 4: Reliability & Polish (2-3 hari)

**Fokus:** Edge cases, safety features, monitoring.

| # | Item | Effort | Detail |
|---|------|--------|--------|
| 4.1 | Warning saat hapus parameter yang digunakan di formula | Sedang | Scan formulas sebelum delete |
| 4.2 | Parameter usage tracking (badge "Dipakai di N formula") | Sedang | Scan all formulas |
| 4.3 | Multi-tab conflict UX: user-facing prompt resolusi (reload/keep local) | Sedang | Build on Phase 1 basic 409 detection |
| 4.4 | Izinkan nilai parameter negatif | Rendah | Hapus MinValueValidator(0) |
| 4.5 | Rollback drill: test full revert scenario | Sedang | Lihat [Section 10](#10-rollback-plan) |

---

## 6. Strategi Migrasi Data Existing

### 6.1 Masalah

Project yang sudah ada memiliki parameter dengan kode deskriptif (misal `panjang_dinding_lt_1`). Kode ini dipakai di formula (computed param expressions + per-pekerjaan formula state). Kita perlu memigrasikan ke format opaque tanpa merusak formula.

### 6.2 Pendekatan: Django Management Command (Satu Kali, Atomic per-Project)

```
Langkah per project (dalam @transaction.atomic):

1. Ambil semua ProjectParameter, urutkan by id (urutan pembuatan).
   Assign kode baru: bp_1, bp_2, ..., sesuai urutan.
   Buat mapping: { "panjang_dinding_lt_1": "bp_1", ... }

2. Ambil semua ProjectComputedParameter, urutkan by id.
   Assign kode baru: cp_1, cp_2, ...
   Tambah ke mapping: { ..., "area_l1": "cp_1", ... }

3. Untuk setiap ProjectComputedParameter.expression:
   Span-based replace menggunakan Python tokenizer (Section 6.3):
   - Tokenize pada **string asli** (tanpa strip/slice)
   - Replace dari belakang (reversed) agar offset tidak bergeser
   - Reconstruct via `result[:start] + new + result[end:]`

4. Untuk setiap VolumeFormulaState (formula per-pekerjaan):
   Token-level replace pada field `raw` (atau field formula terkait).

5. Update semua record di DB.

6. Validasi: parse setiap expression yang sudah di-replace,
   pastikan semua identifier merujuk ke kode yang valid.
   Jika ada yang gagal -> ROLLBACK seluruh project.

7. Log hasil per-project: {project_id, params_migrated, formulas_updated, status}.
```

### 6.3 Python Tokenizer untuk Migration

`vol_formula_engine.js` tokenizer perlu di-mirror di Python untuk migration script. Tokenizer ini **lebih sederhana** dari full engine -- hanya perlu:
- Identify token types: NUM, ID, OP, LP, RP, COMMA
- Untuk migration, hanya token ID yang perlu dimodifikasi
- Reconstruct expression = **span-based replace pada string asli** (bukan join token -- lihat `remap_expression()` di bawah)

```python
# Simplified Python tokenizer for migration

def tokenize_formula(expr):
    """Tokenize formula expression.
    Returns list of (type, value, start_pos, end_pos).
    start/end = posisi dalam STRING ASLI (expr), bukan dalam substring.
    TIDAK melakukan strip() atau slice '=' -- posisi harus absolute."""
    tokens = []
    i = 0
    while i < len(expr):
        ch = expr[i]

        # Whitespace -> skip (tapi posisi tetap benar karena i advance)
        if ch in ' \t\n\r':
            i += 1
            continue

        # Leading '=' (opsional) -> skip sebagai non-token
        if ch == '=' and i == 0:
            i += 1
            continue

        # Identifier: [A-Za-z_][A-Za-z0-9_]*
        if ch.isalpha() or ch == '_':
            j = i + 1
            while j < len(expr) and (expr[j].isalnum() or expr[j] == '_'):
                j += 1
            tokens.append(('id', expr[i:j], i, j))
            i = j
            continue

        # Number: [0-9]+ (simplified, cukup untuk migration)
        if ch.isdigit() or (ch == '.' and i + 1 < len(expr) and expr[i+1].isdigit()):
            j = i + 1
            while j < len(expr) and (expr[j].isdigit() or expr[j] in '.,_'):
                j += 1
            tokens.append(('num', expr[i:j], i, j))
            i = j
            continue

        # Operator, paren, comma -> single char token
        tokens.append(('op', ch, i, i + 1))
        i += 1

    return tokens


def remap_expression(expr, mapping):
    """Token-level replace menggunakan span-based reconstruction.
    PENTING: tokenize pada string ASLI, replace pada string ASLI.
    Tidak ada strip/slice yang menggeser offset."""
    tokens = tokenize_formula(expr)
    # Rebuild dari belakang agar posisi tidak bergeser
    result = expr
    for tok_type, tok_value, start, end in reversed(tokens):
        if tok_type == 'id' and tok_value.lower() in mapping:
            result = result[:start] + mapping[tok_value.lower()] + result[end:]
    return result
```

**Catatan kritis:**
- `tokenize_formula()` beroperasi pada **string asli tanpa modifikasi** (tidak strip, tidak slice `=`).
- Leading `=` di-skip sebagai non-token tapi posisi `i` tetap advance, sehingga offset token berikutnya benar.
- `remap_expression()` replace pada string asli menggunakan offset yang sama.
- Ini menjamin whitespace dan formatting asli tidak berubah.

### 6.4 Fallback: Dual-Mode Sementara

Jika migration satu kali terlalu berisiko:
- Parameter lama tetap pakai kode deskriptif.
- Parameter baru pakai format `bp_N`.
- Formula engine resolve keduanya (sudah case-insensitive lookup).
- Secara bertahap, user bisa "upgrade" project via tombol "Migrasi ke Opaque ID".
- Regex validasi terima kedua format selama transisi: `^[a-z_][a-z0-9_]*$` (lama) atau `^bp_[1-9][0-9]*$` / `^cp_[1-9][0-9]*$` (baru, per-model).

**Kebijakan per-phase (strict vs dual):**

| Phase | Mode Validasi | Penjelasan |
|-------|---------------|------------|
| Phase 0 | **Tidak ada perubahan** -- regex lama masih berlaku | Hanya tutup gap computed params |
| Phase 1 (deploy) | **Strict opaque** -- regex `^bp_[1-9][0-9]*$` / `^cp_[1-9][0-9]*$` | Semua parameter baru wajib opaque. Deploy SETELAH Phase 3 migration |
| Phase 3 (migration) | **Dijalankan SEBELUM Phase 1 deploy** | Semua kode lama sudah di-remap sebelum strict mode aktif |
| Jika dual-mode fallback | **Dual** -- `ProjectParameter.name`: `^([a-z_][a-z0-9_]*|bp_[1-9][0-9]*)$`, `ProjectComputedParameter.name`: `^([a-z_][a-z0-9_]*|cp_[1-9][0-9]*)$` | Hanya jika migration gagal dan butuh partial rollback |

**Urutan deploy yang benar:**
1. Deploy Phase 0 (bug fixes, backward compatible)
2. Jalankan Phase 3 migration script (data migration)
3. Deploy Phase 1 + 2 (strict opaque mode ON)

Ini menghindari situasi dimana strict mode aktif tapi data belum dimigrasikan.

**Rekomendasi:** Migration script (6.2) + strict mode lebih bersih. Dual-mode hanya sebagai fallback darurat, bukan strategi utama.

### 6.5 Pertimbangan localStorage

- Setelah migration, localStorage masih menyimpan kode lama.
- Saat `loadParamsFromServer()` fetch data baru (server authoritative), server data menimpa state lokal.
- **Namun:** Jika user sudah edit secara lokal sebelum fetch selesai, perubahan lokal bisa hilang.
- **Mitigasi:** Setelah deploy migration, tambahkan one-time flag **per-project** yang memaksa full reload dari server pada kunjungan pertama:
  ```javascript
  const MIGRATION_VERSION = 'v2';  // Naikkan jika ada migration tambahan
  const key = `opaque_migrated:${projectId}:${MIGRATION_VERSION}`;
  const oldVars = localStorage.getItem(`volvars:${projectId}`);
  const oldVarLabels = localStorage.getItem(`volvars_labels:${projectId}`);
  const oldCParams = localStorage.getItem(`volcparams:${projectId}`);

  const retryLoad = () => loadParamsFromServer();

  if (!localStorage.getItem(key)) {
      // Force full reload dari server, abaikan cache lokal
      localStorage.removeItem(`volvars:${projectId}`);
      localStorage.removeItem(`volvars_labels:${projectId}`);
      localStorage.removeItem(`volcparams:${projectId}`);
      retryLoad().then(() => {
          // Set flag HANYA setelah load berhasil
          localStorage.setItem(key, Date.now().toString());
      }).catch((err) => {
          // Load gagal (network error) -> flag TIDAK di-set
          // Restore snapshot lama agar UI tidak kosong
          if (oldVars !== null) localStorage.setItem(`volvars:${projectId}`, oldVars);
          if (oldVarLabels !== null) localStorage.setItem(`volvars_labels:${projectId}`, oldVarLabels);
          if (oldCParams !== null) localStorage.setItem(`volcparams:${projectId}`, oldCParams);

          console.warn('Migration load gagal, retry otomatis 3 detik lagi', err);
          if (typeof TOAST !== 'undefined' && TOAST.warn) {
              TOAST.warn('Sinkronisasi migration gagal. Sistem akan retry otomatis.');
          }

          // Retry otomatis sekali lagi (bisa diulang sesuai kebutuhan)
          setTimeout(() => {
              retryLoad()
                  .then(() => localStorage.setItem(key, Date.now().toString()))
                  .catch(() => {});
          }, 3000);
      });
      return;  // Skip local state init, tunggu server response
  }
  ```
  Flag per-project + versi memastikan: (a) project yang belum pernah dibuka tidak kena, (b) jika ada migration tambahan di masa depan, flag versi baru bisa ditambahkan, (c) jika fetch migration gagal, snapshot lokal lama dipulihkan dan sistem melakukan retry otomatis.

  **Prasyarat:** `loadParamsFromServer()` saat ini (`volume_pekerjaan.js:2856`) tidak return Promise -- perlu di-refactor agar return `fetch().then(...)` sebelum snippet di atas bisa bekerja. Ini tercakup dalam item Phase 1.

---

## 7. Import/Export, Template, Backup & Copy

### 7.1 Schema Mapping: Current vs v2

Saat ini ada inkonsistensi key naming di berbagai jalur export:

| Jalur | Key Saat Ini | Key v2 (Canonical) | Computed Params |
|-------|--------------|--------------------|-----------------|
| `_build_export_data()` full | `parameters` | `project_parameters` | **Tambah** `project_computed_parameters` |
| `_build_export_data()` template | `parameters` | `project_parameters` | **Tambah** `project_computed_parameters` |
| `export_project_full_json()` | `project_parameters` | `project_parameters` (sudah benar) | **Tambah** `project_computed_parameters` |
| `import_project_from_json()` | Baca `project_parameters` | Tetap + fallback `parameters` | **Tambah** reader |
| `_import_template_data()` | Baca `parameters` | Tetap + fallback `project_parameters` | **Tambah** reader |

**Keputusan:** Key canonical v2 = `project_parameters` + `project_computed_parameters`.
Import harus fallback ke key lama (`parameters`) untuk backward compatibility.

### 7.2 Format Export v2 (Canonical Schema)

```json
{
  "export_type": "project_full_backup",
  "export_version": "3.0",
  "project_parameters": [
    { "name": "bp_1", "label": "Panjang Dinding", "value": "10.000", "unit": "m", "description": "" },
    { "name": "bp_2", "label": "Lebar Dinding", "value": "5.000", "unit": "m", "description": "" }
  ],
  "project_computed_parameters": [
    { "name": "cp_1", "label": "Luas Dinding", "expression": "bp_1 * bp_2", "unit": "m2", "description": "" }
  ]
}
```

**Relasi metadata v1 (existing) vs v2 (opaque):**

Kode existing menggunakan `export_type` + `export_version` (bukan `version` + `format`).
Format v2 harus **konsisten dengan konvensi existing** agar import parser tidak ambigu:

| Jalur Export | `export_type` (existing) | `export_version` saat ini | `export_version` v2 | Cara Import Membedakan |
|-------------|--------------------------|---------------------------|----------------------|------------------------|
| Full backup | `project_full_backup` | `1.1` / `2.0` | `3.0` | `export_version >= 3.0` → opaque + computed |
| Template | `project_template` | `2.2` | `3.0` | Sama |
| List pekerjaan | `list_pekerjaan` | `1.0` | Tidak berubah | Tidak memuat parameter |
| Template AHSP | `template_ahsp` | `1.0` | Tidak berubah | Tidak memuat parameter |

**Aturan import parser:**
```python
import re

def to_version_tuple(raw):
    """
    Parse '3.0', '3.0.1', '3.0-beta' -> tuple numerik.
    Fallback aman ke (1, 0) jika format tidak valid.
    """
    parts = re.findall(r'\d+', str(raw or '1.0'))
    if not parts:
        return (1, 0)
    nums = tuple(int(x) for x in parts[:3])  # major.minor.patch
    return nums if nums else (1, 0)

export_type = str(data.get('export_type', '')).strip().lower()
version = to_version_tuple(data.get('export_version', '1.0'))

# Guard: hanya jalur export yang memang membawa parameter
if export_type not in ('project_full_backup', 'project_template'):
    params = []
    computed = []
elif version >= (3, 0):
    # Opaque format
    params = data.get('project_parameters', [])
    computed = data.get('project_computed_parameters', [])
else:
    # Legacy format
    params = data.get('project_parameters') or data.get('parameters', [])
    computed = []
```

**Catatan:** Field `"version"` dan `"format"` di contoh schema v2 sebelumnya **dihapus** -- cukup gunakan `export_version: "3.0"` yang sudah jadi konvensi existing. Ini menghindari dua system versioning yang tumpang tindih.

### 7.3 Kebijakan Final Cross-Project (Opsi B)

**Keputusan final:** semua operasi lintas project wajib **regenerate opaque ID di project target**.

Scope kebijakan:
- Import template -> regenerate `bp_N/cp_N` di target.
- Import backup full -> regenerate `bp_N/cp_N` di target.
- Copy/clone project -> regenerate `bp_N/cp_N` di target.

Catatan:
- Berlaku juga saat target project kosong (bukan hanya saat ada conflict).
- Stabilitas dijaga melalui mapping token-level pada expression/formula.

### 7.4 Import ke Project Target (Remap Kode Wajib)

```
Template kode:  bp_1, bp_2, cp_1
Project sudah punya: bp_1 s/d bp_5, cp_1 s/d cp_3

Proses (server-side, dalam transaction):
1. Server hitung next available: bp_6, bp_7, cp_4
2. Buat mapping remap:
   bp_1 (template) -> bp_6
   bp_2 (template) -> bp_7
   cp_1 (template) -> cp_4

3. Token-level replace semua expression:
   "bp_1 * bp_2" -> "bp_6 * bp_7"

4. Insert dengan kode baru.
```

### 7.5 Backward Compatibility Matrix

| Format Source | `export_version` | Computed Params | Handling |
|--------------|------------------|-----------------|----------|
| Export legacy | `< 3.0` (misal `1.1`, `2.0`, `2.2`) | **Tidak ada** | Import as-is, remap kode deskriptif -> opaque |
| Export v2 opaque | `>= 3.0` | **Ada** | Import + **selalu regenerate kode target** + remap expression |
| Excel/CSV | N/A | Tidak ada | Generate kode baru, reverse-lookup label untuk formula |

### 7.6 Export ke Excel/CSV (Untuk Manusia)

```
| Label              | Nilai | Satuan | Formula (readable)                    |
|--------------------|-------|--------|---------------------------------------|
| Panjang Dinding    | 10    | m      |                                       |
| Lebar Dinding      | 5     | m      |                                       |
| Luas Dinding       | 50    | m2     | Panjang Dinding * Lebar Dinding       |
```

- Formula ditampilkan dengan **label** (bukan kode opaque) via tokenizer translate.
- Kode opaque **tidak ditampilkan** ke manusia.
- `volume_pekerjaan_adapter.py` line 116: ganti `param.replace('_', ' ').title()` dengan lookup ke `label` field dari DB.

### 7.7 Copy Project (`services.py`)

Saat ini `_copy_project_parameters()` (line 3718) copy base params tapi **tidak copy computed params**.

**Perubahan yang diperlukan (sesuai Opsi B):**

```
Tambah method baru: _copy_project_computed_parameters(new_project)
1. Fetch semua ProjectComputedParameter dari source project
2. Untuk setiap computed param:
   a. Generate kode baru di project target via `_next_opaque_name()` (ParameterSequence), **selalu** (tidak preserve kode lama)
   b. Buat mapping: old_name -> new_name
3. Token-level replace semua expression menggunakan mapping
   (karena base param names juga di-remap saat copy)
4. Bulk create di project target
5. Pastikan dipanggil SETELAH _copy_project_parameters()
   agar mapping base params sudah tersedia
```

---

## 8. Acceptance Criteria

### Phase 0: Prerequisites

- [ ] **AC-0.1**: Export full backup JSON mengandung section `project_computed_parameters`.
- [ ] **AC-0.2**: Import full backup JSON dengan computed params -> computed params tersedia di project.
- [ ] **AC-0.3**: Copy project -> computed parameters ikut ter-copy, expression valid.
- [ ] **AC-0.4**: `VolFormula.tokenize()` tersedia sebagai public API.
- [ ] **AC-0.5**: Export template mengandung computed parameters.

### Phase 1: Foundation

- [ ] **AC-1.1**: Parameter baru mendapat kode `bp_N` dari server (bukan client-generated).
- [ ] **AC-1.2**: Computed parameter baru mendapat kode `cp_N` dari server.
- [ ] **AC-1.3**: Dua tab membuat parameter bersamaan -> kode berbeda (tidak collision).
- [ ] **AC-1.4**: Edit label parameter -> kode tetap sama (`bp_1` tetap `bp_1`).
- [ ] **AC-1.5**: Kode opaque **tidak ditampilkan** di sidebar tabel parameter.
- [ ] **AC-1.6**: Hapus parameter di client -> reload -> tidak muncul kembali (sync replace).
- [ ] **AC-1.7**: Counter monoton: hapus `bp_3`, buat baru -> `bp_4` (bukan `bp_3`).
- [ ] **AC-1.8**: Sync dari tab dengan data stale -> server respond 409 Conflict (bukan silent overwrite).
- [ ] **AC-1.9**: `normalizeParamCode()` dan `slugifyName()` dihapus dari JS, tidak ada dead code reference.
- [ ] **AC-1.10**: Sync payload berisi kode non-opaque (misal `panjang_dinding`) -> response `200 OK` dengan `warnings[]` per-item yang di-skip, item valid tetap diproses (partial success). Bukan 400 fatal -- agar client tidak kehilangan seluruh batch hanya karena 1 item invalid. Format: `{ "ok": true, "created": N, "warnings": [{"name": "panjang_dinding", "error": "Kode tidak sesuai format opaque"}] }`.
- [ ] **AC-1.11**: `ProjectParameter.clean()` reject `cp_*`, `ProjectComputedParameter.clean()` reject `bp_*`.
- [ ] **AC-1.12**: Validasi opaque format konsisten di: model clean(), API sync, API create, import, copy.

### Phase 2: Formula Editor

- [ ] **AC-2.1**: User ketik "panjang" di formula -> autocomplete muncul -> klik -> chip ter-insert.
- [ ] **AC-2.2**: Formula tersimpan `bp_1 * bp_2`, ditampilkan `[Panjang Dinding] * [Lebar Dinding]`.
- [ ] **AC-2.3**: Preview toggle: mode Label dan mode Nilai.
- [ ] **AC-2.4**: Parameter Palette modal: search by label, klik insert.
- [ ] **AC-2.5**: Error message menyertakan label: "Variabel: Panjang Dinding (bp_1) error".
- [ ] **AC-2.6**: Dirty state + fetch server -> prompt resolusi (bukan silent overwrite).
- [ ] **AC-2.7**: Help text dan placeholder formula tidak lagi referensi kode manual.
- [ ] **AC-2.8**: PANDUAN_USER.md terupdate dengan alur baru.

### Phase 3: Migration

- [ ] **AC-3.1**: Migration script berhasil: semua formula lama berfungsi dengan kode baru.
- [ ] **AC-3.2**: Import file v1 (kode deskriptif) -> auto-remap ke opaque.
- [ ] **AC-3.3**: Import file v2 ke project target (kosong maupun existing) -> kode target selalu diregenerate, formula valid.
- [ ] **AC-3.4**: Export Excel -> kolom formula menampilkan label (bukan `bp_1 * bp_2`).
- [ ] **AC-3.5**: Backup restore -> computed params tersedia, kode target diregenerate, formula valid.

### Phase 4: Reliability

- [ ] **AC-4.1**: Hapus parameter dipakai di 3 formula -> warning dialog muncul.
- [ ] **AC-4.2**: Badge "Dipakai di N formula" di sidebar.
- [ ] **AC-4.3**: Dua tab edit bersamaan -> conflict prompt dengan opsi reload/keep (UX layer di atas AC-1.8).
- [ ] **AC-4.4**: Parameter bisa memiliki nilai negatif.
- [ ] **AC-4.5**: Rollback drill berhasil: opaque -> deskriptif -> formula tetap valid.

---

## 9. Test Plan

### 9.1 Migration Script Tests

| # | Test Case | Input | Expected |
|---|-----------|-------|----------|
| M1 | Basic migration | Project dengan 3 base + 2 computed | Semua kode berubah, formula valid |
| M2 | Formula dengan multi-ref | `panjang * lebar + panjang` | `bp_1 * bp_2 + bp_1` (semua instance) |
| M3 | Computed referencing computed | `cp_area * tinggi` | `cp_1 * bp_3` (cross-type ref) |
| M4 | Empty project | Project tanpa parameter | Sukses tanpa error |
| M5 | Large project | 100+ params, 50+ formulas | Sukses dalam < 10 detik |
| M6 | Substring safety | param `a`, formula `abs(a) + a * max(a, b)` | `abs(bp_1) + bp_1 * max(bp_1, bp_2)` |
| M7 | Transaction rollback | Formula invalid setelah replace | Seluruh project tidak berubah |

### 9.2 Multi-Tab/User Conflict Tests

| # | Test Case | Expected |
|---|-----------|----------|
| C1 | Tab A dan Tab B create parameter bersamaan | Kode berbeda (`bp_6`, `bp_7`) |
| C2 | Tab A delete, Tab B edit parameter sama | Tab B mendapat error/conflict prompt |
| C3 | Tab A sync replace, Tab B sync replace bersamaan | DB serial via transaction, tidak corrupt |

### 9.3 Import/Export Round-Trip Tests

| # | Test Case | Expected |
|---|-----------|----------|
| IE1 | Export v2 -> Import v2 ke project kosong | Struktur/hasil formula identik, kode target boleh berbeda |
| IE2 | Export v2 -> Import v2 ke project dengan params | Remap berhasil, formula valid |
| IE3 | Export v1 (legacy) -> Import ke opaque project | Auto-remap, formula valid |
| IE4 | Export Excel -> Human readable formula | Label, bukan kode opaque |
| IE5 | Backup full -> Restore ke project baru | Base + computed lengkap, kode target regenerated, formula valid |
| IE6 | Copy project | Base + computed lengkap, kode target regenerated, formula valid |

### 9.4 Rollback Drill

| # | Test Case | Expected |
|---|-----------|----------|
| R1 | Feature flag off | Sistem kembali ke kode deskriptif |
| R2 | Reverse migration | Opaque -> deskriptif, formula valid |
| R3 | Mixed state (partial migration) | Dual-mode handler resolve keduanya |

---

## 10. Rollback Plan

### 10.1 Jika Perlu Revert ke Kode Deskriptif

**Masalah dengan re-slugify:** Rollback via `re-slugify(label)` **tidak deterministik** karena:
- Label bisa sudah berubah sejak parameter dibuat.
- Dua label berbeda bisa menghasilkan slug yang sama (collision).
- Slug historis mungkin berbeda dari slug saat ini (jika `normalizeParamCode()` berubah).

**Solusi: Simpan kode lama sebelum migration.**

### 10.2 Backup Kode Lama (Wajib Sebelum Migration)

Migration script HARUS menyimpan mapping lama sebagai backup:

```python
# Simpan di tabel baru atau JSON field
class ParameterMigrationLog(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    old_name = models.CharField(max_length=100)
    new_name = models.CharField(max_length=100)  # bp_N / cp_N
    param_type = models.CharField(max_length=10)  # 'base' / 'computed'
    migrated_at = models.DateTimeField(auto_now_add=True)
```

Atau lebih sederhana: dump mapping ke JSON file per-project sebelum migration.

### 10.3 Reverse Migration (Deterministik)

```
1. Baca ParameterMigrationLog untuk project.
2. Buat reverse mapping: { "bp_1": "panjang_dinding", "cp_1": "area_l1", ... }
3. Token-level replace semua expression (reverse).
4. Update name field di DB.
5. Hapus migration log.
```

Ini **deterministik** karena menggunakan mapping aktual, bukan re-slugify.

### 10.4 Feature Flag

```javascript
const OPAQUE_ID_ENABLED = true;  // Set false untuk fallback
```

Selama development, kode baru di-gate di balik flag. Jika masalah besar post-deploy:
1. Set flag false.
2. Jalankan reverse migration.
3. Deploy.

### 10.5 Mitigasi Risiko

| Risiko | Mitigasi |
|--------|----------|
| Migration gagal di tengah jalan | `@transaction.atomic` per-project |
| Formula rusak setelah migration | Validasi setiap formula post-replace |
| Reverse migration data hilang | Backup mapping di `ParameterMigrationLog` |
| User bingung dengan UI baru | Tooltip/onboarding saat pertama load |
| Import file lama gagal | Backward compatibility handler (detect version) |
| Collision saat concurrent create | Server-side generation + DB unique constraint |

---

## 11. Item yang Gugur dari Roadmap v1.2

Dengan pendekatan opaque ID, beberapa item dari REVIEW_PARAMETER_FORMULA.md v1.2 **tidak lagi relevan**:

| Item Lama | Alasan Gugur |
|-----------|-------------|
| 1.1 (Fix kode ikut berubah saat edit label) | **Otomatis solved** -- kode opaque, label bebas |
| 1.4 (Live preview kode saat input label) | **Tidak relevan** -- user tidak lihat kode |
| 1.5 (Perbesar hint kode di tabel) | **Tidak relevan** -- kode tidak ditampilkan |
| 1.7 (Max length guard kode) | **Otomatis solved** -- kode max ~8 char |
| 2.1 (Field kode editable) | **Tidak relevan** -- sistem generate |
| 2.2 (Rename kode + cascade) | **Tidak relevan** -- kode stabil |
| 2.5 (Reserved keyword guard) | **Otomatis solved** -- `bp_1` tidak bentrok |
| 5.1 (Rename kode stabilisasi) | **Tidak relevan** |
| 5.2 (User set kode sendiri) | **Diganti** -- sistem generate |
| 7 (Rollback plan rename) | **Diganti** dengan rollback plan migration |
| 8 (Test matrix karakter) | **Tidak relevan** -- tidak ada slugify |
| 9.5 (Reserved keyword guard) | **Otomatis solved** |
| 9.6 (Token-level rename cascade) | **Tetap relevan** untuk migration script, bukan runtime |

**Item yang tetap relevan:**

| Item Lama | Status di Agenda Baru |
|-----------|----------------------|
| 1.2 (Sync merge -> replace) | Phase 1, item 1.7 |
| 1.3 (Warning hapus parameter) | Phase 4, item 4.1 |
| 1.6 (Per-item error reporting) | Phase 1, item 1.3 |
| 1.8 (Race condition guard) | Phase 2, item 2.6 |
| 2.3 (Dual-label preview) | Phase 2, item 2.3 |
| 2.4 (Parameter palette) | Phase 2, item 2.4 |
| 3.1 (Usage tracking) | Phase 4, item 4.2 |
| 3.4 (Nilai negatif) | Phase 4, item 4.4 |
| 3.5 (Multi-tab conflict) | Phase 1 item 1.8 (basic 409) + Phase 4 item 4.3 (UX prompt) |
| 9.1 (Input contract) | Phase 1, item 1.11 |
| 9.3 (Race condition guard) | Phase 2, item 2.6 |
| 9.4 (Multi-tab conflict) | Phase 1 item 1.8 (basic 409) + Phase 4 item 4.3 (UX prompt) |

---

## Riwayat Dokumen

| Versi | Tanggal | Perubahan |
|-------|---------|-----------|
| v1.0 | 2026-02-11 | Dokumen awal |
| v1.1 | 2026-02-11 | [MAJOR] 8 temuan: server-side ID gen, Phase 0, full surface audit, tokenizer expose, localStorage fix, rollback deterministik, validasi semua jalur, UX docs, test plan. |
| v1.2 | 2026-02-11 | [REVISION] 6 temuan: (1) Generator ID pakai SELECT FOR UPDATE + retry IntegrityError, bukan scan max+1 tanpa lock. (2) Regex per-model: `^bp_[1-9][0-9]*$` untuk base, `^cp_[1-9][0-9]*$` untuk computed -- mencegah cross-prefix. (3) Tabel mapping schema export canonical vs legacy + adapter kompatibilitas. (4) Naikkan minimal conflict detection (updated_at + 409) ke Phase 1, Phase 4 jadi UX layer. (5) Remap expression pakai span-based reconstruction, bukan join. (6) Tambah AC untuk per-model prefix enforcement dan conflict detection. |
| v1.3 | 2026-02-11 | [REVISION] 8 temuan: (1) **[Kritis]** Ganti `max(existing)+1` dengan dedicated `ParameterSequence` counter table -- monoton naik, never decrements, no reuse setelah delete. (2) **[Kritis]** Fix tokenizer Python: operasi pada string asli tanpa strip/slice, offset absolute. (3) **[Tinggi]** Tambah Section 4.6 gap table: kondisi kode saat ini vs target dengan line references. (4) **[Tinggi]** Tambah detail implementasi 409 conflict di endpoint sync (`views_api.py:2938,3078`) + mekanisme `last_sync_at`. (5) **[Sedang]** Perjelas kebijakan dual-mode vs strict-mode per-phase + urutan deploy yang benar (Phase 0 → Migration → Phase 1+2). (6) **[Sedang]** Schema inconsistency tercakup di gap table 4.6. (7) **[Rendah]** localStorage migration flag diubah ke per-project + versi (`opaque_migrated:${projectId}:v2`). (8) **[Rendah]** UI/help sudah tercakup di Phase 2 item 2.7-2.8. Update diagram data flow Section 2.3 sesuai ParameterSequence. |
| v1.4 | 2026-02-11 | [REVISION] 6 temuan: (1) **[Tinggi]** Payload conflict-check 409 disesuaikan dengan format sync aktual (dict, bukan array) + contoh response `synced_at`. (2) **[Sedang]** Hapus narasi "join token raw values" yang kontradiktif dengan span-based replace. (3) **[Sedang]** Tambah tabel transisi metadata export: gunakan `export_version: "3.0"` (konvensi existing), bukan field `version`/`format` baru. Update contoh schema v2 sesuai. (4) **[Sedang]** AC-1.9 ditegaskan: partial success 200 + `warnings[]` per-item (bukan 400 fatal). (5) **[Rendah]** localStorage migration flag di-set setelah `loadParamsFromServer()` berhasil (`.then()`), bukan sebelum. (6) **[Rendah]** Regex dual-mode ditulis eksplisit penuh per-model. |
| v1.5 | 2026-02-11 | [REVISION] 4 temuan: (1) **[Sedang]** Version compare di import parser diganti dari string-compare ke tuple numerik `(3, 0)` -- aman untuk versi multi-digit. (2) **[Sedang]** Backward compatibility matrix diupdate: hapus referensi `"version": "2.0"`, konsistenkan ke `export_version`. (3) **[Rendah]** Tambah `.catch()` di localStorage migration snippet agar network error tidak berhenti tanpa fallback. (4) **[Rendah]** Phase 0.8 detail diganti dari "Version field" ke `export_version: "3.0"`. |
| v1.6 | 2026-02-11 | [HARDENING] Dokumen dipoles untuk eksekusi: (1) Parser version dibuat robust untuk format non-murni numerik (`3.0-beta`) via `to_version_tuple()` + fallback aman. (2) Ditambahkan guard `export_type` agar parsing parameter hanya berjalan pada jalur export relevan (`project_full_backup`/`project_template`). (3) Snippet localStorage migration diperkuat: restore snapshot lokal lama saat fetch gagal + warning ke user + retry otomatis agar tidak berakhir state kosong. (4) Status dokumen dinaikkan menjadi siap eksekusi. |
| v1.7 | 2026-02-11 | [MINOR] 3 fix dari review final: (1) Renomor AC -- AC-1.9 sekarang untuk dead code removal, AC-1.10 untuk partial success warnings, AC-1.11 untuk cross-prefix rejection, AC-1.12 untuk validasi konsistensi. (2) Copy remap (Section 7.6) eksplisit referensi `_next_opaque_name()` via ParameterSequence. (3) Tambah catatan prasyarat: `loadParamsFromServer()` perlu return Promise. Buat OPAQUE_ID_CHECKLIST.md untuk tracking implementasi. |
| v1.8 | 2026-02-11 | [DECISION] Kebijakan final lintas project ditetapkan ke **Opsi B**: import/template backup/copy/restore wajib regenerate opaque ID di target (tidak preserve), dengan remap expression token-level. AC dan test round-trip disesuaikan: validasi semantik + integritas formula, bukan kesamaan kode literal. |
| v1.9 | 2026-02-12 | [EXECUTION UPDATE] Status dinaikkan ke IMPLEMENTED (dev/staging validated). Phase 1 C2/C3 manual E2E (multi-tab conflict + concurrent sync) lulus; Phase 4.3 conflict UX dikonfirmasi aktif (409 -> prompt Reload/Tetap Lokal). Sisa operasional: gate deploy production, monitor pasca rilis, cleanup window rollback. |
| v1.10 | 2026-02-12 | [OPERATIONS] Ditambahkan runbook produksi terstruktur (`docs/RUNBOOK_OPAQUE_ID_PRODUCTION.md`) dengan gate pass/fail, command exact staging/production, prosedur rollback, dan prosedur cleanup `ParameterMigrationLog` via command baru `cleanup_parameter_migration_logs`. |
| v1.11 | 2026-02-12 | [OPERATIONS HARDENING] Ditambahkan command status `opaque_post_deploy_status` + script monitoring harian `scripts/opaque_daily_monitor.sh` + checklist QA `docs/QA_GATE_D_PHASE2_CHECKLIST.md` + template monitoring `docs/OPAQUE_MONITORING_7D_TEMPLATE.md`. Bukti eksekusi env saat ini: backup DB sukses, dry-run+real migration `failed: 0`, validasi global `NON_OPAQUE_BASE=0`, `NON_OPAQUE_CP=0`, dan `OPAQUE_ID_ENABLED=True`. |

---

*Dokumen ini adalah rencana implementasi berdasarkan keputusan arsitektur untuk beralih dari kode deskriptif ke opaque ID. Lihat REVIEW_PARAMETER_FORMULA.md v1.2 untuk analisis masalah lengkap.*
