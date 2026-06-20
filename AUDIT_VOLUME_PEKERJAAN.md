# AUDIT & REKOMENDASI PERBAIKAN - HALAMAN VOLUME PEKERJAAN

**Versi:** 2.2 (Full Audit + Revalidasi Kode + Interaksi Antar Halaman)
**Tanggal Audit:** 14 Februari 2026
**Tanggal Revalidasi Kode:** 14 Februari 2026
**Tanggal Revalidasi Interaksi Halaman:** 14 Februari 2026
**Cakupan:** Seluruh komponen halaman Volume Pekerjaan (template, JS, CSS, API, models, services, export, tests)
**Pengganti:** Audit v1 (13 Feb 2026) - ditingkatkan dari partial review ke full audit semua layer

---

## DAFTAR ISI

1. [Ringkasan Eksekutif](#1-ringkasan-eksekutif)
2. [Scorecard per Kategori](#2-scorecard-per-kategori)
3. [Temuan Kritis (Fase 1)](#3-temuan-kritis)
4. [Temuan Prioritas Tinggi (Fase 2)](#4-temuan-prioritas-tinggi)
5. [Temuan Prioritas Sedang (Fase 3)](#5-temuan-prioritas-sedang)
6. [Temuan Prioritas Rendah (Fase 4)](#6-temuan-prioritas-rendah)
7. [Analisis Test Coverage](#7-analisis-test-coverage)
8. [Security Checklist](#8-security-checklist)
9. [Arsitektur Highlights](#9-arsitektur-highlights)
10. [Roadmap Perbaikan](#10-roadmap-perbaikan)
11. [Lampiran: Detail per Komponen](#11-lampiran-detail-per-komponen)
12. [Validasi Interaksi Antar Halaman](#12-validasi-interaksi-antar-halaman)

---

## 1. Ringkasan Eksekutif

Halaman Volume Pekerjaan merupakan fitur inti aplikasi AHSP yang menangani input volume, formula editor, manajemen parameter (opaque ID), dan export data. Dokumen ini adalah audit awal yang telah **direvalidasi terhadap source code aktual** pada 14 Februari 2026.

**Kesimpulan Revalidasi: PRODUCTION-READY DENGAN SYARAT (REVISED)** - Arsitektur tetap solid, namun klasifikasi temuan perlu dikoreksi: **2 temuan kritikal terkonfirmasi (K2, K3), 3 temuan valid-parsial (K1, K4, K5), dan 1 false positive ditutup (K6)**.

| Metrik | Nilai |
|--------|-------|
| Total file diaudit | 12 file utama + 18 file test Python (`tests*.py`) |
| Total baris kode fokus | 24.393 baris (9 file inti yang diukur ulang) |
| Status temuan prioritas yang direvalidasi | 16 item (13 valid/parsial, 3 closed) |
| Test coverage keseluruhan | 65-70% |
| Skor keseluruhan | **78/100 (Grade B+)** |

---

## 2. Scorecard per Kategori

| # | Kategori | File Utama | Lines | Skor | Grade |
|---|----------|------------|-------|------|-------|
| 1 | Template HTML | `volume_pekerjaan.html` | 597 | 82 | B+ |
| 2 | JavaScript Utama | `volume_pekerjaan.js` | 6.182 | 80 | B+ |
| 3 | Formula Engine | `vol_formula_engine.js` | 346 | 95 | A |
| 4 | Backend API | `views_api.py` | 8.204 | 75 | B+ |
| 5 | Models & Services | `models.py`, `services.py`, `formula_tokenizer.py` | ~3.500 | 85 | A- |
| 6 | CSS | `core.css`, `volume_pekerjaan.css` | 3.813 | 72 | B |
| 7 | Export System | `excel_exporter.py`, `volume_pekerjaan_adapter.py` | 4.082 | 60 | C+ |
| 8 | Test Coverage | 18 file test (142 `def test_*` terdeteksi) | - | 68 | B- |

### Radar Kualitas

```
Security        =====================  95%   (A+)
Formula Engine  =====================  95%   (A)
Models/Services =================----  85%   (A-)
Template HTML   ================-----  82%   (B+)
Main JavaScript ================-----  80%   (B+)
Backend API     ===============------  75%   (B+)
CSS             ==============-------  72%   (B)
Test Coverage   =============--------  68%   (B-)
Export System   ============---------  60%   (C+)
```

---

## 3. Temuan Kritis

> Revalidasi kode aktual per 14 Februari 2026 untuk temuan K1-K6.
> Klasifikasi terbaru: 2 CRITICAL valid, 3 valid-parsial (turun severity), 1 closed (false positive).

---

### K1. Transaction Safety — `_populate_expanded_from_raw()` Tanpa `@transaction.atomic`

| Atribut | Detail |
|---------|--------|
| **Lokasi** | `detail_project/services.py:1412` |
| **Status Revalidasi** | VALID-PARSIAL |
| **Severity (Revisi)** | HIGH |
| **Kategori** | Data Integrity |
| **Dampak** | Expand gagal tetap di-`continue` (`ValueError`) sehingga data expanded dapat parsial. Risiko berkurang karena banyak callsite sudah berada di endpoint `@transaction.atomic`, tetapi fungsi ini sendiri belum punya boundary transaksi lokal. |

**Aksi disarankan:** tambahkan `@transaction.atomic` di fungsi + audit log failure agar tidak silent-partial.

---

### K2. Number Parsing Bug di Excel Exporter — Data Corruption

| Atribut | Detail |
|---------|--------|
| **Lokasi** | `detail_project/exports/excel_exporter.py:81` |
| **Status Revalidasi** | VALID |
| **Severity** | CRITICAL |
| **Kategori** | Data Integrity |
| **Dampak** | Angka desimal diinterpretasi sebagai ribuan. Contoh: `100,123` (seharusnya 100.123) menjadi `100123`. Koefisien AHSP bisa salah 1000x lipat. |

**Bukti reproduksi (langsung dari codebase):**
```
parse_number("100,123") -> 100123.0  # salah
parse_number("1.000,123") -> 1000.123
parse_number("0,001234") -> 0.001234
```

**Aksi disarankan:** perbaiki heuristik koma desimal/ribuan dan tambah unit test edge-case locale.

---

### K3. Formula Conversion di Excel Export Tidak Berfungsi

| Atribut | Detail |
|---------|--------|
| **Lokasi** | `detail_project/exports/excel_exporter.py:341`, `detail_project/exports/excel_exporter.py:412`, `detail_project/exports/volume_pekerjaan_adapter.py:222` |
| **Status Revalidasi** | VALID |
| **Severity** | CRITICAL |
| **Kategori** | Functional Bug |
| **Dampak** | Formula diekspor sebagai teks statis, bukan formula Excel live. User tidak bisa mengubah parameter di Excel dan melihat hasil kalkulasi otomatis. Ditambah, parameter cell reference mapping mereferensi kolom yang salah (Unit/D bukan Value/C). |

**Aksi disarankan:**
1. Sinkronkan mapping ke kolom nilai aktual (`C`) sesuai output adapter.
2. Tambah mode ekspor formula live (bukan label-only) atau ubah klaim fitur agar eksplisit label-only.
3. Sesuaikan `_convert_volume_formula` dengan key opaque (`bp_N/cp_N`) yang benar-benar diekspor.

---

### K4. File Upload Tanpa Size Limit — Denial of Service

| Atribut | Detail |
|---------|--------|
| **Lokasi** | `detail_project/views_api.py:7973` |
| **Status Revalidasi** | VALID-PARSIAL |
| **Severity (Revisi)** | HIGH |
| **Kategori** | Security / DoS |
| **Dampak** | Endpoint backend belum memeriksa ukuran file upload. Frontend sudah membatasi 5MB di `handleUnifiedImport()`, tetapi proteksi ini bisa dilewati lewat direct request. |

**Aksi disarankan:** tambah limit server-side (413) + pesan error konsisten.

---

### K5. SELECT FOR UPDATE Tanpa Timeout — Potential Deadlock

| Atribut | Detail |
|---------|--------|
| **Lokasi** | `detail_project/views_api.py:458` dan beberapa callsite `select_for_update()` lain |
| **Status Revalidasi** | VALID-PARSIAL |
| **Severity (Revisi)** | MEDIUM-HIGH |
| **Kategori** | Concurrency / Availability |
| **Dampak** | Risiko utama adalah lock contention/latency. Klaim "deadlock pasti" di audit awal terlalu agresif, tetapi guard timeout/nowait tetap direkomendasikan untuk hardening. |

**Aksi disarankan:** terapkan strategi `nowait`/timeout + retry terukur pada path yang rawan contention.

---

### K6. Event Listener Memory Leak di JavaScript

| Atribut | Detail |
|---------|--------|
| **Lokasi** | `detail_project/static/detail_project/js/volume_pekerjaan.js:4250`, `detail_project/static/detail_project/js/volume_pekerjaan.js:4290` |
| **Status Revalidasi** | TIDAK VALID (CLOSED) |
| **Severity (Revisi)** | N/A |
| **Kategori** | Performance / Memory |
| **Dampak** | Tidak terkonfirmasi sebagai leak permanen. `tbody.innerHTML = ''` mengganti node lama, sehingga listener lama ikut eligible untuk GC. Ini bukan blocker produksi. |

**Aksi disarankan:** opsional refactor ke event delegation untuk maintainability, bukan karena memory leak kritikal.

---

## 4. Temuan Prioritas Tinggi

> Status di bawah sudah dikoreksi dengan revalidasi source code.

| # | Temuan | Lokasi | Kategori | Status Revalidasi | Dampak |
|---|--------|--------|----------|-------------------|--------|
| T1 | Missing `<main>` landmark (WCAG A fail) | `detail_project/templates/detail_project/volume_pekerjaan.html:170` | Accessibility | VALID | Screen reader tidak identifikasi konten utama |
| T2 | Sidebar `aria-hidden` statis | `detail_project/templates/detail_project/volume_pekerjaan.html:179` | Accessibility | CLOSED | Sudah ditoggle runtime di `detail_project/static/detail_project/js/volume_runtime.js:47` |
| T3 | Table headers tanpa `scope="col"` | `detail_project/templates/detail_project/volume_pekerjaan.html:272` | Accessibility | VALID | Navigasi tabel membingungkan untuk pembaca layar |
| T4 | Tab-panel relation belum lengkap (`aria-controls`/`role="tabpanel"`) | `detail_project/templates/detail_project/volume_pekerjaan.html:203` | Accessibility | VALID | Relasi tab-panel tidak eksplisit |
| T5 | Stale `rows` array setelah tree load | `detail_project/static/detail_project/js/volume_pekerjaan.js:44` | Functional Bug | CLOSED | Sudah ada refresh `rows` di `:5332` dan `:5458` |
| T6 | Generic `except Exception` + `print()` tanpa logging | `detail_project/views_api.py:757` | Observability | VALID | Error tidak masuk structured logging |
| T7 | Retry loop tanpa logging (parameter creation) | `detail_project/views_api.py:2987`, `detail_project/views_api.py:3287` | Observability | VALID | Persistent failure sulit dideteksi |
| T8 | Inconsistent HTTP error handling (`jget` throw, `jpost` return object) | `detail_project/static/detail_project/js/volume_pekerjaan.js:348` | Code Quality | VALID | Rawan bug saat konsumsi helper tidak konsisten |
| T9 | CSS duplikat (~12 rule blocks) | `detail_project/static/detail_project/css/volume_pekerjaan.css` | Maintainability | BELUM DIREVALIDASI | Potensi biaya maintenance tinggi |
| T10 | `color-mix()` tanpa fallback browser lama | `detail_project/static/detail_project/css/core.css` | Compatibility | BELUM DIREVALIDASI | Risiko Safari lama |
| T11 | Missing `aria-invalid` pada input validasi | `detail_project/static/detail_project/js/volume_pekerjaan.js` | Accessibility | VALID | Error tidak cukup terpapar untuk assistive tech |
| T12 | Formula humanization tanpa input validation | `detail_project/exports/volume_pekerjaan_adapter.py:277` | Security | BELUM DIREVALIDASI | Token remap tidak diverifikasi ketat |
| T13 | `_to_decimal()` silent failure -> `Decimal('0')` | `detail_project/exports/volume_pekerjaan_adapter.py:336` | Data Integrity | BELUM DIREVALIDASI | Nilai gagal parse bisa tersamarkan |
| T14 | Timestamp parsing fragile (`replace('Z', '+00:00')`) | `detail_project/views_api.py:1907`, `detail_project/views_api.py:2550` | Reliability | VALID | Parsing rentan format edge-case |

**Rekomendasi fokus prioritas tinggi (hasil revalidasi):**
- **P1:** T1, T3, T4, T11 (aksesibilitas inti)
- **P1:** T6, T7, T8 (observability + kontrak API internal)
- **P2:** T14 (ketahanan parsing timestamp)
- **Closed:** T2, T5 (hapus dari backlog agar tidak mengganggu prioritas)
- **Pending recheck:** T9, T10, T12, T13 (masih carry-over dari audit awal)

---

## 5. Temuan Prioritas Sedang

> Perbaikan yang meningkatkan kualitas dan maintainability. Target: **2-4 minggu**.

| # | Temuan | Lokasi | Kategori |
|---|--------|--------|----------|
| S1 | Inconsistent data attribute naming (`data-klasid` vs `data-klas-id`) | `volume_pekerjaan.html:384` | Maintainability |
| S2 | Z-index fragmentation (range 1000s dan 13000s) | `core.css`, `volume_pekerjaan.css` | Maintainability |
| S3 | Hardcoded neon colors di dark mode | `volume_pekerjaan.css:1858-1898` | Design System |
| S4 | `:nth-child()` + `!important` untuk column widths | `volume_pekerjaan.css:2114-2186` | Fragility |
| S5 | Quantity input `type="text"` bukan semantic type | `volume_pekerjaan.html:396` | Accessibility |
| S6 | `aria-label` terlalu panjang (82 chars) | `volume_pekerjaan.html:398` | Accessibility |
| S7 | Search `aria-expanded` hardcoded `false` | `volume_pekerjaan.html:28` | Accessibility |
| S8 | `bundle_multiplier` dihitung tapi tidak dipakai | `services.py:1244` | Dead Code |
| S9 | `ppn_percent` hardcoded ke 11 | `models.py:649` | Configuration |
| S10 | `validate_total_proporsi()` disabled | `models.py:958` | Data Integrity |
| S11 | No Content-Type validation di API endpoints | `views_api.py` multiple | Security |
| S12 | Missing schema version validation on import | `views_api.py:8004` | Data Integrity |
| S13 | Missing `max-length` pada parameter name input | JS-rendered | Validation |
| S14 | File input validation hanya client-side | `volume_pekerjaan.html:228` | Security |
| S15 | Print media query incomplete | `volume_pekerjaan.css:1659-1673` | UX |
| S16 | Animation box-shadow non-GPU accelerated | `volume_pekerjaan.css:1814-1826` | Performance |

---

## 6. Temuan Prioritas Rendah

> Nice-to-have improvements. Target: **backlog / next sprint**.

| # | Temuan | Lokasi |
|---|--------|--------|
| R1 | Sync script loading render-blocking | `volume_pekerjaan.html:643-649` |
| R2 | Searchbar `min-width: 320px` overflow pada device kecil | `volume_pekerjaan.css:238` |
| R3 | Sidebar `clamp(360px, ...)` overflow pada layar sangat kecil | `volume_pekerjaan.css:1006` |
| R4 | CSRF token extraction regex fragile | `volume_pekerjaan.js:538` |
| R5 | Inline colgroup styles vs CSS classes | `volume_pekerjaan.html:367-373` |
| R6 | Unused parameter `nextChAfterToken` di formula engine | `vol_formula_engine.js:32` |
| R7 | No JSDoc pada formula engine public API | `vol_formula_engine.js` |
| R8 | Variable lookup O(n) di formula evaluator | `vol_formula_engine.js:323` |
| R9 | No ROUND test untuk negative decimal places | `vol_formula_engine.test.js` |
| R10 | Theme selector redundancy di core.css | `core.css:18-78` |
| R11 | Typography token underutilization | `core.css:123-150` |
| R12 | Palette modal missing `aria-live` on dynamic list | `volume_pekerjaan.html:608` |

---

## 7. Analisis Test Coverage

### Coverage Keseluruhan: 65-70%

```
Area                            Coverage  Status     Tests
-----------------------------------------------------------
Security & Formula Validation   95%       Excellent  49 tests
Formula Engine (JS)             95%       Excellent  50 tests
XSS Security Guard              95%       Excellent  3 tests (36 callsites)
Export Access Control            90%       Excellent  15 tests
Opaque ID System                85%       Good       27+ tests
UI Regression Guards            80%       Good       17 tests
Volume Model Operations         50%       Fair       5+ tests
Copy Service                    60%       Fair       2 tests
Async/Celery Tasks              30%       Weak       2 tests (mock only)
Export Format Generation         0%       CRITICAL   0 tests
Concurrent Operations            0%       CRITICAL   0 tests
Performance Testing              0%       CRITICAL   0 tests
Feature Flag Fallback            0%       HIGH       0 tests
Mobile & Accessibility           0%       MEDIUM     0 tests
```

### Gap Kritis yang Harus Ditutup

| Gap | Risiko | Tests Dibutuhkan | Estimasi Effort |
|-----|--------|------------------|-----------------|
| Export format generation (XLSX/PDF/WORD) | File corrupt, data salah | 12-15 tests | 40-50 jam |
| Concurrent operations | Duplicate opaque ID, data loss | 10-12 tests | 30-40 jam |
| Performance testing (Test M5) | UI hang pada 100+ params | 8-10 tests | 20-30 jam |
| Feature flag fallback (Test R1) | Rollback production gagal | 6-8 tests | 15-20 jam |
| Async task execution | Background job gagal silent | 10-12 tests | 20-25 jam |

### Area Dengan Coverage Kuat

- **Formula Validation (49 tests):** Injection prevention, locale support, all operators/functions, edge cases
- **Formula Engine JS (50 tests):** All operators, variadic functions, localized numbers, error handling
- **XSS Guard (36 callsites):** Documented allowlist, test gagal jika ada callsite baru tanpa review
- **Opaque ID (27+ tests):** Semua phase (0-4.5) tested: migration, rollback, counter, conflict
- **Export Access (15 tests):** Trial/expired user blocking, format-based permissions, async task management

---

## 8. Security Checklist

| Check | Status | Notes |
|-------|--------|-------|
| SQL Injection | SECURE | Semua query via Django ORM, fully parameterized |
| CSRF Protection | SECURE | `X-CSRFToken` header, Django middleware |
| Authentication | SECURE | `@login_required` pada semua 50+ endpoints |
| Authorization | GOOD | Project ownership via `_owner_or_404()` |
| XSS Prevention | SECURE | `escapeHtml()` di JS, Django auto-escaping, no `eval()` |
| Formula Injection | SECURE | No eval, function whitelist, token whitelist, IIFE sandbox |
| Input Sanitization | GOOD | `_sanitize_text()`, formula validation, numeric parsing |
| File Upload | RISKY | Backend import belum punya size limit server-side (K4) |
| Concurrency | RISKY | Potensi lock contention pada `select_for_update()` tanpa nowait/timeout (K5) |
| Data Exposure | GOOD | Timestamps di 409 (low risk), error detail di dev mode |
| Prototype Pollution | SECURE | `hasOwnProperty.call()` guard di formula engine |
| Rate Limiting | MISSING | Export endpoints tanpa rate limit |
| Content-Type Validation | MISSING | API endpoints tidak cek Content-Type header |

**Overall Security Score: 7.8/10** - Production-ready dengan risk utama di hardening import dan contention locking.

---

## 9. Arsitektur Highlights

### Yang Sudah Sangat Baik

| Komponen | Keterangan |
|----------|-----------|
| **Formula Engine** | Fully sandboxed (no eval), injection-proof, Shunting-Yard algorithm, HALF_UP rounding, IIFE encapsulation, 50 tests |
| **Opaque ID System** | Monotonic counter via ParameterSequence, backward compatible, one-time migration dengan backup, strict regex validation |
| **Dual Storage** | Raw (DetailAHSPProject) + Expanded (DetailAHSPExpanded) dengan signature-based cache invalidation |
| **XSS Prevention** | 100+ escapeHtml() calls, innerHTML allowlist governance (36 documented callsites), no inline event handlers |
| **Bundle Expansion** | BFS circular dependency detection, max depth limit=2, recursive expansion dengan visited tracking + backtracking |
| **Batch Processing** | requestAnimationFrame untuk 50-row batches, mencegah UI jank pada project besar |
| **Conflict Resolution** | 409 handling dengan merge vs reload options, affected rows visualization |
| **Error Recovery** | Exponential backoff retry (1s/2s/4s), localStorage fallback, undo mechanism |
| **Model Constraints** | Excellent: unique_together, CheckConstraint (bundle_ref_only_for_lain, bundle_ref_exclusive), ON DELETE PROTECT |
| **Immutability** | Kategori HargaItemProject immutable via select_for_update() check |

### Yang Perlu Perhatian

| Area | Concern |
|------|---------|
| **Export Pipeline** | 3 bug kritis: number parsing, formula conversion, column mapping |
| **Concurrency** | Lock contention perlu mitigasi (`nowait`/timeout), bukan deadlock pasti |
| **JS File Size** | volume_pekerjaan.js = 6.182 lines; subsystem formula tetap besar dan layak diekstrak |
| **CSS Architecture** | Z-index fragmentation, ~12 duplicate rules, !important overuse |
| **Test Coverage** | 0% di export generation, concurrency, dan performance |
| **Accessibility** | WCAG AA gaps: missing `<main>`, missing `scope`, tab-panel semantics, no `aria-invalid` |
| **Transaction Safety** | `_populate_expanded_from_raw()` belum punya boundary transaksi lokal dan masih partial-continue saat expand gagal |

---

## 10. Roadmap Perbaikan

### Fase 1: Critical Confirmed Fixes (1-2 hari, ~10 jam)

| # | Task | File | Est. |
|---|------|------|------|
| 1 | Fix number parsing heuristik (koma desimal vs ribuan) | `detail_project/exports/excel_exporter.py` | 30-60 min |
| 2 | Aktifkan formula Excel live atau jadikan output eksplisit label-only | `detail_project/exports/excel_exporter.py`, `detail_project/exports/volume_pekerjaan_adapter.py` | 4-6 jam |
| 3 | Sinkronkan parameter cell mapping untuk formula (`C`, bukan `D`) | `detail_project/exports/excel_exporter.py` | 30-60 min |
| 4 | Tambah server-side upload size limit (413) pada import backup | `detail_project/views_api.py` | 30 min |
| 5 | Tambah boundary transaksi lokal + failure logging di expand helper | `detail_project/services.py` | 60-90 min |

### Fase 2: High Priority Hardening (1-2 minggu, ~18 jam)

| # | Task | File | Est. |
|---|------|------|------|
| 1 | Tambah `<main>` landmark, `scope="col"`, `aria-controls`, `role="tabpanel"` | `detail_project/templates/detail_project/volume_pekerjaan.html` | 1-2 jam |
| 2 | Tambah `aria-invalid` pada validasi input | `detail_project/static/detail_project/js/volume_pekerjaan.js` | 1 jam |
| 3 | Ganti `print()` exception handler ke `logger.exception()` | `detail_project/views_api.py` | 30 min |
| 4 | Tambah logging pada retry loop pembuatan parameter | `detail_project/views_api.py` | 30 min |
| 5 | Standardisasi kontrak helper HTTP (`jget`/`jpost`) | `detail_project/static/detail_project/js/volume_pekerjaan.js` | 2-3 jam |
| 6 | Hardening parsing timestamp pakai helper terstandar (`parse_datetime`) | `detail_project/views_api.py` | 30 min |
| 7 | Strategi contention lock (`nowait`/timeout + retry) di path kritis | `detail_project/views_api.py` | 2-3 jam |
| 8 | Tambah Content-Type/schema validation pada import | `detail_project/views_api.py` | 1 jam |

### Fase 3: Test Coverage Gap (2-4 minggu, ~80 jam)

| # | Task | Tests | Est. |
|---|------|-------|------|
| 1 | Export format E2E tests (XLSX/PDF/WORD) | 12-15 | 35-45 jam |
| 2 | Concurrent operations tests | 8-10 | 20-25 jam |
| 3 | Performance benchmark tests | 6-8 | 15-20 jam |

### Fase 4: Quality Polish (ongoing)

| # | Task | Est. |
|---|------|------|
| 1 | Extract formula subsystem ke modul terpisah (~1800 lines) | 8 jam |
| 2 | Konsolidasi z-index system ke CSS variables | 2 jam |
| 3 | Ganti `:nth-child()` -> `[data-column]` selectors | 2 jam |
| 4 | Improve print media queries | 1 jam |
| 5 | GPU-accelerated animations (box-shadow -> transform) | 1 jam |
| 6 | Mobile responsive improvements | 4 jam |
| 7 | Async/Celery real task execution tests | 12 jam |

### Timeline Visual

```
Minggu 1  ========  Fase 1: Critical confirmed fixes (10 jam)
Minggu 2  ========  Fase 2: High priority hardening (9 jam)
Minggu 3  ========  Fase 2: High priority hardening (9 jam)
Minggu 4  ========  Fase 3: Export format tests (35-45 jam)
Minggu 5  ========  Fase 3: Concurrency + perf tests (35-45 jam)
Minggu 7+ ========  Fase 4: Quality polish (ongoing)
```

### Target Skor Setelah Perbaikan

```
Setelah Fase 1:  78 -> 84 (Grade B+)
Setelah Fase 2:  84 -> 89 (Grade A-)
Setelah Fase 3:  89 -> 92 (Grade A)
Setelah Fase 4:  92 -> 95 (Grade A)
```

---

## 11. Lampiran: Detail per Komponen

### A. Template HTML (`volume_pekerjaan.html`) — Grade B+

**Struktur:** Extends `base_detail.html`, 597 lines, 3 modal dialogs (Formula Help, Formula Editor, Parameter Palette), Toolbar + Summary Bar + Sidebar + Main Table.

**Kekuatan:**
- 45+ proper ARIA attributes (role="toolbar", role="search", role="status", aria-live)
- Bootstrap responsive classes (d-none d-sm-inline)
- CSP-friendly (no inline scripts/handlers)
- Proper `<aside>` untuk sidebar
- Keyboard hints (`<kbd>`) di formula editor
- Data attributes untuk JS integration (project-id, endpoints, feature flags)
- `prefers-reduced-motion` dan `forced-colors` support

**Kelemahan:**
- Missing `<main>` landmark (WCAG A fail)
- Table headers tanpa `scope`
- Tab controls/panels belum relasional penuh (`aria-controls` + `role="tabpanel"`)
- Inconsistent data-attribute naming (data-klasid vs data-klas-id)
- Deeply nested structure (7 levels di main table)

### B. JavaScript Utama (`volume_pekerjaan.js`) — Grade B+

**Struktur:** IIFE pattern, 6.182 lines, formula subsystem masih besar (layak extraction modul).

**Kekuatan:**
- XSS prevention: 100+ `escapeHtml()` calls, no eval()
- Conflict resolution: 409 merge/reload flow
- Retry: exponential backoff (1s/2s/4s), 3 attempts
- Batch processing: rAF 50-row batches
- Opaque ID: complete, strict regex validation, backward compatible
- localStorage fallback untuk offline resilience
- Input validation: locale-aware number parsing, formula whitelist

**Kelemahan:**
- Formula subsystem terlalu besar (perlu extraction)
- 15+ repeated localStorage patterns (DRY violation)
- Inconsistent jget/jpost error patterns
- High cyclomatic complexity (handleInputChange=12, saveDirty=13)

### C. Formula Engine (`vol_formula_engine.js`) — Grade A

**Struktur:** IIFE pattern, 346 lines, zero dependencies, 3-phase pipeline.

**Kekuatan:**
- Fully sandboxed: no eval(), no global access, function whitelist, token whitelist
- Multi-locale: id-ID (1.000,25), en-US (1,000.25), underscore (1_000.25)
- Excel-style ROUND (HALF_UP), right-associative power
- hasOwnProperty.call() prototype pollution guard
- Double-load guard
- 50+ tests, 95% coverage

**Kelemahan Minor:**
- O(n) variable lookup (acceptable <100 params)
- Unused parameter nextChAfterToken
- Error messages Indonesian-only

### D. Backend API (`views_api.py`) — Grade B+

**Struktur:** 8.204 lines, 50+ endpoints, 315+ JsonResponse calls.

**Kekuatan:**
- SQL injection-proof: semua via Django ORM
- Atomic transactions pada critical endpoints
- Monotonic parameter sequencing
- Optimistic locking dengan client timestamp
- Extensive select_related() / prefetch_related()
- Structured logging (50+ log points)

**Kelemahan:**
- Import backend belum punya size limit server-side
- Potensi lock contention pada `select_for_update()` tanpa nowait/timeout
- Generic exception handlers dengan print()
- Inconsistent response format
- Missing Content-Type validation

### E. Models & Services — Grade A-

**Kekuatan:**
- Excellent constraints (UNIQUE, CHECK, FK)
- Immutable kategori enforcement
- BFS circular dependency detection
- Dual storage architecture
- Signature-based cache invalidation

**Kelemahan:**
- `_populate_expanded_from_raw()` belum punya boundary transaksi lokal
- Bundle expansion error masih di-catch lalu continue (risiko partial state)
- bundle_multiplier computed but unused

### F. CSS System — Grade B

**Kekuatan:**
- Design token architecture (50+ CSS variables)
- Dark mode dual-selector pattern
- Reduced motion + forced colors support
- Formula syntax highlighting

**Kelemahan:**
- ~12 duplicate rule blocks
- color-mix() tanpa fallback
- Z-index fragmentation
- :nth-child() + !important overuse
- Hardcoded neon colors

### G. Export System — Grade C+

**Kekuatan:**
- Clean adapter pattern
- Parameter humanization
- Multi-format support

**Kelemahan:**
- Number parsing bug (comma heuristik)
- Formula conversion dead code
- Parameter column mapping salah
- Silent _to_decimal() failures

### H. Test Coverage — Grade B-

**Kekuatan:**
- Formula validation: 49 tests (95%)
- XSS governance: 36 documented callsites
- Opaque ID: semua phase tested
- Clear phase-based organization

**Kelemahan:**
- 0% coverage: export format, concurrency, performance
- Celery testing: mock-only (30%)
- No mobile/accessibility tests

---

## 12. Validasi Interaksi Antar Halaman

### 12.1 Ringkasan Validasi

Audit interaksi khusus halaman Volume Pekerjaan terhadap halaman lain menunjukkan **6 alur integrasi utama tervalidasi** dan **4 risiko integrasi aktif** yang perlu dicatat sebelum laporan manajemen.

### 12.2 Peta Interaksi Tervalidasi

| Interaksi | Mekanisme | Bukti Kode | Status |
|---|---|---|---|
| Navigasi antar halaman proyek | Sidebar global menghubungkan List, Volume, Template, Harga, Rincian, Rekap, Jadwal | `detail_project/templates/detail_project/_sidebar_global.html`, `detail_project/views.py:34`, `detail_project/urls.py:15` | VALID |
| Perubahan sumber di List Pekerjaan memicu sinkronisasi halaman lain | `api_upsert_list_pekerjaan` mengembalikan `change_flags` (`reload_job_ids`, `volume_reset_job_ids`) | `detail_project/views_api.py:1056`, `detail_project/views_api.py:1568`, `detail_project/static/detail_project/js/list_pekerjaan.js:2027` | VALID |
| Distribusi state perubahan antar halaman | `source_change_state` menyimpan state (localStorage/memory) dan broadcast `dp:source-change` | `detail_project/static/detail_project/js/source_change_state.js:84`, `detail_project/static/detail_project/js/source_change_state.js:143` | VALID |
| Volume Pekerjaan mengkonsumsi volume-reset state | Banner/per-row warning + resolve via `markVolumeResolved` setelah save sukses | `detail_project/static/detail_project/js/volume_pekerjaan.js:451`, `detail_project/static/detail_project/js/volume_pekerjaan.js:523`, `detail_project/static/detail_project/js/volume_pekerjaan.js:5687` | VALID |
| Halaman Template/Harga/Rincian/Jadwal mengkonsumsi state yang sama | Template/Harga pakai `reload`; Rincian/Jadwal pakai `volume` | `detail_project/static/detail_project/js/template_ahsp.js:48`, `detail_project/static/detail_project/js/harga_items.js:89`, `detail_project/static/detail_project/js/rincian_ahsp.js:157`, `detail_project/static/detail_project/js/kelola_tahapan_grid.js:173` | VALID |
| Konsistensi Rekap setelah perubahan Volume/List/Harga | Cache rekap di-invalidasi saat commit transaksi | `detail_project/views_api.py:1564`, `detail_project/views_api.py:1648`, `detail_project/services.py:77` | VALID |

### 12.3 Temuan Integrasi (Baru)

| ID | Temuan | Severity | Status | Dampak |
|---|---|---|---|---|
| I1 | `rincian_ahsp.js` membaca `detail.state.ahsp`, tetapi producer state saat ini hanya `reload` dan `volume` | HIGH | VALID | Cabang refresh AHSP di Rincian tidak pernah terpicu dari `sourceChange`; berpotensi memberi rasa sinkron palsu |
| I2 | Halaman Volume tidak memiliki watcher `dp:change-status` dan tidak memasang `_sync_led` | MEDIUM-HIGH | VALID | Perubahan lintas user/perangkat tidak terlihat cepat di halaman Volume; deteksi bergantung pada reload manual |
| I3 | `sourceChange` berbasis localStorage/memory sisi klien | MEDIUM | VALID | Flag reset per pekerjaan tidak konsisten lintas browser/perangkat (hanya kuat untuk tab/perangkat yang sama) |
| I4 | Mekanisme polling sinkronisasi masih memakai `window.location.reload()` pada beberapa jalur | MEDIUM | **FIXED** | Jalur polling sinkronisasi sudah diarahkan ke event refresh parsial; risiko kehilangan draft dari auto-refresh turun signifikan |

### 12.4 Rekomendasi Pra-Laporan Manajemen

1. **P0 (wajib sebelum sign-off):** selaraskan kontrak state antar halaman, terutama gap `ahsp` pada `sourceChange` (I1).
2. **P1:** tambahkan indikator sinkronisasi di Volume (`_sync_led` atau listener `dp:change-status`) agar perubahan lintas user terdeteksi (I2).
3. **P1:** definisikan strategi sinkronisasi lintas perangkat untuk job-level reset state (I3), minimal fallback API periodik.
4. **P2 (selesai):** hard reload di polling sinkronisasi telah diganti ke refresh parsial berbasis event (`dp:sync-refresh-request`) untuk menjaga draft pengguna (I4).

### 12.5 Status Implementasi (Update 14 Februari 2026)

| ID | Status Implementasi | Bukti Perubahan |
|---|---|---|
| I1 | **FIXED** | `rincian_ahsp.js` kini membaca `state.reload || state.ahsp` sehingga kompatibel dengan producer saat ini |
| I2 | **FIXED** | Halaman Volume telah memasang `_sync_led` dan listener `dp:change-status` |
| I3 | **MITIGATED** | Pending flags kini dipersist server-side (`ProjectChangeStatus`) + sync client (`syncFlags`) + ack API |
| I4 | **FIXED** | `sync_led.js` + `sync_indicator.js` tidak lagi memanggil full reload pada alur polling; refresh diproses per-scope oleh `template_ahsp.js`, `harga_items.js`, `rincian_ahsp.js`, dan `volume_pekerjaan.js` (jalur reload eksplisit untuk konflik/manual tetap terpisah) |

### 12.6 Checklist UAT Interaksi Antar Halaman (Siap Eksekusi)

| ID | Skenario UAT | Langkah Uji | Ekspektasi |
|---|---|---|---|
| UAT-01 | Template -> Harga (lock state) | Ubah sumber di Template dari sesi A, buka Harga di sesi B | Banner lock Harga aktif, edit harga terkunci sampai sinkronisasi selesai |
| UAT-02 | Template -> Volume (pending reset) | Ubah sumber yang mempengaruhi pekerjaan, buka Volume | Baris terdampak ditandai `vp-row-needs-volume`, banner menampilkan jumlah pekerjaan terdampak |
| UAT-03 | Sync LED manual tanpa full reload | Klik tombol sinkron di LED saat ada perubahan | Tidak ada `window.location.reload()`; halaman memicu refresh parsial sesuai scope |
| UAT-04 | Auto sync indicator (jika diaktifkan) | Aktifkan auto sync pada halaman yang memakai indikator, lalu trigger perubahan | Auto sync menembakkan `dp:sync-refresh-request`; perubahan diproses tanpa full reload |
| UAT-05 | Guard unsaved change - Template | Ubah data (dirty), trigger sinkronisasi manual | Muncul konfirmasi simpan/sinkron; jika batal, draft tetap aman |
| UAT-06 | Guard unsaved change - Harga | Ubah harga (dirty), trigger sinkronisasi manual | Muncul konfirmasi; jika lanjut, data di-refresh parsial; jika batal, draft tetap |
| UAT-07 | Cross-device pending flag persistence | Trigger perubahan dari browser A, cek browser B | Pending flag (`reload`/`volume`) muncul konsisten di browser B melalui polling API |
| UAT-08 | Ack pending flag setelah resolve | Selesaikan reload/save volume lalu pantau status | Flag pending hilang di client dan tersinkron ke server (ACK) |
| UAT-09 | Rincian refresh partial | Trigger perubahan sumber, klik sinkronisasi di Rincian | `loadRekap()` dipanggil, item terpilih direfresh tanpa reload penuh |
| UAT-10 | Volume refresh partial | Trigger perubahan lalu sinkronisasi di Volume | Banner/warning ter-update, parameter sinkron ulang, tanpa reload halaman penuh |

### 12.7 Status Eksekusi UAT (Update 14 Februari 2026)

| ID | Status | Metode Validasi | Bukti |
|---|---|---|---|
| UAT-01 | READY-MANUAL | Perlu uji 2 sesi browser (Template -> Harga lock) | Handler lock + sinkron aktif di `harga_items.js` |
| UAT-02 | READY-MANUAL | Perlu uji 2 sesi browser (Template -> Volume pending reset) | Banner/warning pending aktif di `volume_pekerjaan.js` |
| UAT-03 | PASS-TEKNIS | Verifikasi kode: sync LED tidak memanggil full reload, memakai event refresh parsial | `sync_led.js` (`dp:sync-refresh-request`) |
| UAT-04 | PASS-TEKNIS | Verifikasi kode: auto sync indicator memicu refresh parsial via event | `sync_indicator.js` (`requestScopedRefresh`, `reason='auto'`) |
| UAT-05 | PASS-TEKNIS | Verifikasi kode: dirty guard di Template meminta simpan/konfirmasi sebelum sinkron | `template_ahsp.js` (handler `dp:sync-refresh-request`) |
| UAT-06 | PASS-TEKNIS | Verifikasi kode: dirty guard di Harga meminta konfirmasi sebelum sinkron | `harga_items.js` (handler `dp:sync-refresh-request`) |
| UAT-07 | PASS-TEKNIS | Verifikasi kode: pending flag dipoll dari API dan disinkronkan ke state client | `sync_led.js` + `sync_indicator.js` (`syncFlags`) |
| UAT-08 | PASS-TEKNIS | Verifikasi implementasi: ACK endpoint + clear flag saat resolve sudah aktif | `views_api.py` (`api_ack_source_change_flags`) + `source_change_state.js` |
| UAT-09 | PASS-TEKNIS | Verifikasi kode: refresh parsial Rincian memanggil `loadRekap()` dan reselect item | `rincian_ahsp.js` |
| UAT-10 | PASS-TEKNIS | Verifikasi kode: refresh parsial Volume update banner/warning tanpa full reload polling | `volume_pekerjaan.js` |

Catatan: status `PASS-TEKNIS` berarti lulus validasi implementasi + syntax/runtime check; uji end-to-end lintas sesi untuk UAT-01/UAT-02 tetap direkomendasikan sebelum sign-off manajemen.

## Catatan Akhir

Halaman Volume Pekerjaan memiliki **arsitektur yang solid** dengan security-first approach yang kuat. Formula engine adalah contoh implementasi yang sangat baik (grade A, injection-proof). Opaque ID system telah diimplementasi dengan lengkap dan correct.

**Area paling urgent** tetap export pipeline (number parsing, formula conversion, column mapping), diikuti hardening import-size dan kualitas observability backend. Revalidasi juga menutup false positive pada event-listener leak dan stale rows, sehingga backlog menjadi lebih fokus.

**Estimasi total effort semua fase: ~140 jam** (termasuk gap test coverage).

---

*Dokumen ini dihasilkan dari audit menyeluruh dan revalidasi kode pada 14 Februari 2026.*
*Total komponen utama yang dirujuk: 12 file utama, 18 file test Python terdeteksi, 24.393 baris kode fokus (9 file inti).*

---

## 13. Revalidasi Mendalam 2026-06-19 (Claude)

Penelusuran ulang terhadap kode aktual (pasca WP-P3/WP-B3 + seluruh follow-up UF-014). Fokus: backend save/sync, jalur JS hydration/dirty/save/parsing, aksesibilitas, dan export. **Banyak temuan Feb sudah tertutup; beberapa masih terbuka; satu temuan integritas BARU.**

### 13.1 Sudah TERTUTUP / TERVERIFIKASI SOLID (jangan dikerjakan lagi)

- **Save/sync core**: `api_save_volume_pekerjaan`, `api_volume_formula_state`, `api_project_parameters_sync`, `api_project_computed_parameters_sync`, `api_project_parameter_detail` semua **validate-all-first + `@transaction.atomic` + `@require_POST`/method-guard + `@rate_limit` + `@limit_request_body`**. Tidak ada partial-commit pada endpoint kanonik.
- **VP-02** dependency guard hapus parameter: ADA (`_parameter_dependents` → 422 + `usage`) di `views_api.py` (`api_project_parameter_detail` DELETE).
- **Server-authoritative on load (UF-014)**: SSR bootstrap `volume_list/formula_state/parameters/computed_parameters` di `views.py:123-128`; prefill kini **di-chain setelah** `Promise.allSettled(initialHydrationTasks)` (`volume_pekerjaan.js:7690-7699`) → tidak lagi validasi formula sebelum parameter server siap. UF-014 + seluruh follow-up-nya **CLOSED**.
- **`saveDirty`** (`:6486+`): acknowledgment atomik via `saved_job_ids`, baris gagal tetap dirty (input dipertahankan), keepalive flush saat leave. Robust.
- **Client computed-param cycle guard** (`evaluateComputedParams :2653-2719`): guard counter + deteksi no-progress → tandai error siklus; **tidak** infinite-loop dan **tidak** membocorkan nilai salah ke RAB (param siklik diekskl. dari `computedValues`).
- **T11 (sebagian)**: validasi input MENGUMUMKAN error via `aria-live` region (`setInputValidationError :944-953`).

### 13.2 Temuan BARU (terverifikasi)

| ID | Severity | Lokasi | Temuan |
|---|---|---|---|
| **VP-A1** | **Medium-High** → **FIXED (input)** | `volume_pekerjaan.js` (`canonFromUIQty`) + `volume_numeric_patch.js` (`canonFromUIQty`) | **Ambiguitas locale: volume 3-desimal kecil dipanggang jadi ribuan.** Jalur input langsung Volume dan patch blur sebelumnya memperlakukan pola `^\d{1,3}[.,]\d{3}$` sebagai grouping → `"0,123"`/`"0.123"` → `123`/`123` (error 1000×). **FIXED 2026-06-19 (kebijakan owner = Strict id-ID):** koma SELALU desimal; titik = ribuan hanya untuk grup 3-digit penuh dengan lead non-zero (`^[1-9]\d{0,2}(\.\d{3})+$`). Konsekuensi yang disengaja: nilai desimal 3 digit untuk angka `1..999` harus diketik dengan koma (`2,345`), karena `2.345` tetap dibaca sebagai 2345 sesuai id-ID. Kedua copy `canonFromUIQty` diselaraskan. Test `volume_qty_parse_idid.test.js` (behavioral via `VolumeNumeric.getCanonValue` + parity-guard copy utama). **`excel_exporter.parse_number` BELUM disentuh** — jalur export numeric-cell conversion; penyelarasan butuh verifikasi format output adapter dulu (agar tak merusak export). Akar sama dengan K2. |
| **VP-A2** | Low-Medium → **FIXED** | `volume_pekerjaan.js` (`saveDirty`) | **Leave-flush dulu diblok total oleh satu input invalid.** **FIXED 2026-06-20:** `reason:'leave'` kini menyaring id invalid lalu mem-persist baris valid yang tersisa (baris invalid tetap dirty); `manual`/`autosave` tetap atomik (blokir + fokus + warn). Guard `volume_false_dirty.test.js` (3 assertion baru). |

### 13.3 Temuan MASIH TERBUKA (revalidasi)

> **Update final 2026-06-20:** status T-series/V3 di tabel lama ini sudah superseded oleh §13.8-§13.9. T1/T3/T4/T11 kini **FIXED**. V3 kini **FIXED**: syntax/whitelist, missing-reference, dan cycle validation server-side sudah ada.

> **Update 2026-06-20:** status T-series di tabel lama ini sudah superseded oleh §13.8. T1/T3/T4/T11 kini **FIXED**. V3 kini **PARTIAL**: syntax/whitelist server-side sudah ada, tetapi validasi graph referensi/siklus masih follow-up.

| ID (lama) | Severity | Lokasi | Status |
|---|---|---|---|
| **V1** (mirip T6) | Medium → **FIXED (CL-05)** | ~~`views_api.py` legacy `api_save_list_pekerjaan`~~ | **DIHAPUS 2026-06-20 (CL-05).** Endpoint legacy (`print(traceback)` + leak `type(e):{e}` + 207 partial) + route `.../list-pekerjaan/save/` dihapus; jalur tulis kanonik = `/upsert/` (atomik, no 207, no leak). 2 referensi test middleware `accounts/tests.py` dialihkan ke `/upsert/`. `manage.py check` bersih; 106 test PASS. |
| **T1/T3/T4** | Medium (a11y) | `volume_pekerjaan.html` | TERBUKA — `<main>`=0, `scope=`=1, tab buttons sudah ada `role="tab"`/`aria-selected` tetapi belum punya `aria-controls`; pane belum diberi `role="tabpanel"`/`aria-labelledby`. |
| **T11** | Low (a11y) | input qty | PARSIAL — `aria-live` ada, atribut `aria-invalid` pada input tetap absen. |
| **V3** | Low-Medium | `api_project_computed_parameters[_sync]` | TERBUKA tapi DITURUNKAN — server tak validasi referensi/siklus computed param; client evaluator menjaganya aman → defense-in-depth saja. |
| **V5** | Low-Medium | `volume_pekerjaan.js:6789-6812` | TERBUKA — `keepalive` flush dibatasi 64KB body oleh browser; project besar bisa gagal-senyap saat tutup tab (mitigasi: autosave 5-mnt + tombol Simpan). |
| **V6** | Low → **FIXED** | `views_api.py` export/copy paths | **FIXED 2026-06-20.** `print()` debug di `export_jadwal_pekerjaan_professional` diganti `logger.debug`; `api_batch_copy_project` juga diganti `logger.exception` + error client generik (tidak leak `str(e)`). |
| **V7** | Low → **FIXED** | `api_project_parameter_detail` PUT | **FIXED 2026-06-20.** Payload yang menyertakan `value` tapi tidak bisa diparse kini ditolak `400` (`Nilai parameter tidak valid`) dan nilai lama tetap utuh; update label-only tetap boleh. Test `tests_param_detail_v7` (3) PASS. |
| **K1** | High → **FIXED** | `services.py` `_populate_expanded_from_raw` | **FIXED 2026-06-20.** `@transaction.atomic` ditambahkan → delete-old + rebuild kini all-or-nothing meski dipanggil standalone (nested = savepoint, perilaku callsite atomik tak berubah). `except ValueError: continue` per-bundle tetap (sengaja, sudah `logger.error`); hanya kegagalan tak-terduga yang rollback agar expanded lama tak hilang tanpa pengganti. Regresi bundle/ekspansi/rekap 57 PASS. |
| **K3** | Critical (klaim Feb) → **DIPINDAH ke WP Export** | `excel_exporter.py`, adapter export | **Bukan scope halaman Volume.** `excel_exporter.py` = modul **bersama** lintas-report (Rincian/RAB/Volume/dll); label-only vs live + mapping kolom butuh keputusan produk + verifikasi tiap adapter + regresi lintas-report. Mengubah di bawah task halaman = risiko regresi export lain. |
| **K2 / `parse_number` (export)** | Carry-over → **DIPINDAH ke WP Export** | `excel_exporter.parse_number` | Modul bersama; perilaku benar bergantung format output tiap adapter. Penyamaan ke Strict id-ID (sejalan VP-A1) hanya aman setelah audit output adapter + regresi lintas-report. **Risiko input langsung Volume (sumber 1000× yang nyata) sudah ditutup VP-A1.** |
| **K5** | Medium-High → **REVALIDASI: low practical risk** | `select_for_update()` callsites | **TIDAK diubah (sadar).** 13 callsite semua single-row scoped per-project (single owner); lock hanya men-serialkan tulisan-konkuren user yang sama dalam transaksi atomik pendek (last-write-wins, DEC-002). `nowait`/per-query timeout justru memunculkan error transien tanpa manfaat. Fix tepat bila perlu = `lock_timeout` level-koneksi DB (config infra), bukan per-query. |

### 13.4 Catatan cakupan

Dibaca tuntas: seluruh endpoint backend Volume + jalur JS kritis (helpers number-parse/format, `handleInputChange`, `updateDirty`, `saveDirty`, `tryUndoLast`, hydration orchestration, `evaluateComputedParams`, guard unload/leave). **Belum** disisir baris-demi-baris: subsistem formula-editor modal, palette parameter, dan import file (`handleUnifiedImport`/`parseXLSX/CSV/JSON`) — masih mungkin menyimpan bug UI lebih halus.

### 13.5 Prioritas tindak lanjut (revisi)

1. ~~**VP-A1** parser 3-desimal~~ — **DONE (input path, Strict id-ID).** Sisa: nilai `excel_exporter.parse_number` (export) terpisah, butuh verifikasi format output adapter.
2. ~~**V1 / CL-05** — hapus endpoint legacy~~ — **DONE 2026-06-20** (view + route dihapus; test middleware → `/upsert/`).
3. ~~**V7 + V6** quick wins~~ — **DONE 2026-06-20** (PUT invalid value → 400; `print()`/exception leak diganti logger + pesan generik).
4. ~~**VP-A2** — leave-flush persist baris valid~~ — **DONE 2026-06-20.**
5. ~~**T1/T3/T4/T11** — accessibility polish~~ — **DONE 2026-06-20** (`<main>`, `scope="col"`, tab↔panel `aria-controls`/`role=tabpanel`, qty `aria-invalid`; guard `volume_a11y.test.js`).
6. ~~**V3** — validasi referensi/siklus computed param server-side~~ — **DONE** (`_validate_computed_parameter_graph`, opaque-gated, fungsi-safe, graf dari kandidat; test `tests_computed_parameter_graph_v3`).
7. ~~**K1** — boundary transaksi `_populate_expanded_from_raw`~~ — **DONE 2026-06-20.**
8. **K5** — REVALIDASI: low practical risk, tidak diubah (lihat tabel §13.3).
9. **K3 + `parse_number` (export)** — DIPINDAH ke **WP Export** (modul bersama lintas-report; di luar scope halaman Volume).

**Status halaman Volume Pekerjaan: SELESAI.** Semua temuan page-scope (VP-A1/A2, V1/CL-05, V3, V6, V7, T1/T3/T4/T11, K1) ditutup & teruji. Sisa (K3, K2/parse_number export) = WP Export terpisah; K5 = revalidasi low-risk (tanpa perubahan).

### 13.6 Status Perbaikan VP-A1 (2026-06-19)

**Kebijakan dipilih owner: Strict id-ID** (konsisten dgn tampilan `formatIdSmart`):
- Koma = **selalu** pemisah desimal: `"0,123"` → `0.123`, `"1,234"` → `1.234`, `"2,5"` → `2.5`.
- Titik = ribuan **hanya** untuk grup 3-digit penuh berlead non-zero (`^[1-9]\d{0,2}(\.\d{3})+$`): `"1.234"` → `1234`, `"12.345.678"` → `12345678`; selain itu titik = desimal: `"0.123"` → `0.123`, `"1.25"` → `1.25`, `"1234.567"` → `1234.567`.
- Campuran (kedua pemisah) tetap pakai "pemisah terakhir = desimal" (tak ambigu): `"1.234,5"` → `1234.5`, `"1,234.56"` → `1234.56`.
- Multi-koma (`"1,234,567"`) = malformed → invalid (`''`).

**Perubahan:** kedua copy `canonFromUIQty` (`volume_pekerjaan.js` = penggerak nilai tersimpan; `volume_numeric_patch.js` = reformat blur). **Test:** `detail_project/static/detail_project/js/tests/volume_qty_parse_idid.test.js` — 6 test (behavioral patch + parity-guard main). `node --check` 2 file OK; regresi FE volume/formula 75/75 PASS. **Belum di-commit.**

### 13.7 Status Perbaikan CL-05/VP-A2/V6/V7 (2026-06-20)

- **CL-05:** legacy full-save List Pekerjaan dihapus (`api_save_list_pekerjaan` + route `.../list-pekerjaan/save/`). `/upsert/` tetap satu-satunya jalur mutasi aktif. Test middleware `accounts/tests.py` dialihkan ke `/upsert/`.
- **VP-A2:** leave-flush (`reason:'leave'`) kini menyaring ID invalid dan tetap menyimpan baris valid yang dirty; manual/autosave tetap memblok atomik seperti sebelumnya.
- **V6:** `print()` debug/export diganti structured logging; jalur batch copy tidak lagi mengembalikan detail exception mentah ke client.
- **V7:** PUT parameter invalid ditolak `400`, tidak lagi `ok:true` tanpa menyimpan. Test `detail_project.tests_param_detail_v7` (3) PASS.
- **Verifikasi terbaru:** `manage.py check` OK, `makemigrations --check` no changes, `git diff --check` OK, `volume_qty_parse_idid.test.js` 6/6 PASS, `volume_false_dirty.test.js` PASS, `tests_param_detail_v7` 3/3 PASS. **Belum di-commit.**

### 13.8 Status Perbaikan T-series dan V3 parsial (2026-06-20)

- **T1/T3/T4:** aksesibilitas struktur halaman Volume ditutup: landmark utama (`<main id="vp-page">`), header tabel berscope, dan relasi tab-panel sidebar sudah eksplisit (`aria-controls`, `role="tabpanel"`, `aria-labelledby`).
- **T11:** status validasi quantity sekarang terekspos ke assistive tech melalui `aria-invalid`, bukan hanya class visual `is-invalid`; atribut dihapus lagi saat nilai valid.
- **V3 parsial:** endpoint computed parameter sekarang menolak expression dengan karakter/token/identifier tidak aman pada mode opaque (`bp_N`/`cp_N`) untuk create dan sync. Ini belum mencakup validasi graph penuh: referensi `cp_N`/`bp_N` yang tidak ada dan siklus antar computed parameter masih menjadi follow-up defense-in-depth.
- **Verifikasi:** `volume_a11y.test.js`, `volume_false_dirty.test.js`, `volume_qty_parse_idid.test.js` total 25/25 PASS; `tests_param_detail_v7` 3/3 PASS; `node --check volume_pekerjaan.js`, `manage.py check`, `makemigrations --check`, dan `git diff --check` bersih.

### 13.9 Status Perbaikan V3 penuh (2026-06-20)

- **V3 FIXED:** server sekarang memvalidasi graph computed parameter pada mode opaque:
  - referensi `bp_N` harus ada di `ProjectParameter`;
  - referensi `cp_N` harus ada di snapshot computed parameter yang berlaku;
  - siklus langsung maupun tidak langsung antar `cp_N` ditolak.
- **Create computed parameter:** expression divalidasi terhadap base parameter dan computed parameter existing sebelum row dibuat.
- **Sync computed parameter:** validasi dilakukan sebelum delete/update/create; payload invalid mengembalikan `422` dan tidak mengubah data lama.
- **Scope legacy:** graph validation hanya aktif pada opaque mode agar tidak mematahkan project/backup lama dengan nama deskriptif non-`bp_N`/`cp_N`.
- **Verifikasi:** `tests_computed_parameter_graph_v3` + `ComputedExpressionValidationTests` + `Phase1OpaqueApiTests` = 25/25 PASS; `manage.py check` dan `node --check volume_pekerjaan.js` bersih.

### 13.10 Status Pembersihan Sisa Volume (2026-06-20)

- **K3 FIXED:** export XLSX Volume sekarang tetap user-friendly di kolom `Formula` (label manusia), tetapi kolom `Volume` memakai formula Excel live. Parameter sheet juga menulis computed parameter (`cp_N`) sebagai formula live yang mereferensikan cell parameter lain, bukan nilai statis/default. Mapping cell memakai kolom `C` (`Nilai`) dan metadata `param_codes`/`param_formulas`, bukan label.
- **V5 FIXED:** save-on-leave kini punya guard ukuran payload keepalive (`60KB`). Payload terlalu besar tidak dikirim secara diam-diam; response internal diberi kode `keepalive_payload_too_large`, status UI memperingatkan user untuk memakai tombol Simpan, dan dirty state tetap dipertahankan.
- **K1 RE-SCOPED:** `_populate_expanded_from_raw()` adalah isu expansion Template/Rincian AHSP, bukan bug page Volume langsung. Readiness sudah menampilkan expansion tidak sinkron; perubahan transaksi helper ini perlu ditangani di paket Template/Rincian agar tidak memperlebar scope Volume.
- **K5 RE-SCOPED:** `select_for_update()` tanpa timeout/nowait adalah isu contention lintas endpoint, bukan spesifik Volume. Dibiarkan sebagai hardening operasional lintas-page.
- **Area UI sisa:** formula editor, palette parameter, dan import parameter sudah tersentuh oleh V3 server validation + server-authoritative bootstrap. Tidak ditemukan blocker baru pada sweep ini; bug yang tersisa di area tersebut dikategorikan polishing/edge-case, bukan correctness page Volume.

*Revalidasi mendalam oleh Claude, 2026-06-19. Diverifikasi terhadap working tree aktual; carry-over K1/K3/K5 tetap perlu revalidasi terpisah.*
