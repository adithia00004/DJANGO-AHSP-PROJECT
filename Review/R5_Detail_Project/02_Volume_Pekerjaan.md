# R5.2 - Review Volume Pekerjaan & Formula Engine

**Status:** `[~]` ONGOING - hardening API + regression suite backend selesai, uji manual UI/performance lanjutan masih berjalan
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/detail_project/<project_id>/volume-pekerjaan/` |
| View | `detail_project.views.volume_pekerjaan_view` |
| Template | `detail_project/templates/detail_project/volume_pekerjaan.html` |
| JS | `volume_pekerjaan.js` (~3500+ lines), `vol_formula_engine.js` |
| CSS | `volume_pekerjaan.css` |
| Tokenizer | `detail_project/formula_tokenizer.py` |

### API Endpoints Terkait

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| POST | `api/project/<id>/volume-pekerjaan/save/` | Save volume |
| GET | `api/project/<id>/volume-pekerjaan/list/` | List volumes |
| GET/POST | `api/project/<id>/volume-formula-state/` | Formula state |
| GET | `api/project/<id>/parameters/` | List parameters |
| POST | `api/project/<id>/parameters/sync/` | Sync parameters |
| GET | `api/project/<id>/computed-parameters/` | Computed params |
| POST | `api/project/<id>/computed-parameters/sync/` | Sync computed |

---

## Audit Fungsional

### Volume Input

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | Input volume numerik langsung | Nilai tersimpan | `[x]` | PASS - save API test |
| TC-2 | Input volume = 0 | Diterima, disimpan | `[x]` | PASS - save API test |
| TC-3 | Input volume negatif | Handled (block/allow per setting) | `[x]` | PASS - ditolak 400 |
| TC-4 | Input volume sangat besar | No overflow | `[ ]` | Pending stress test |
| TC-5 | Decimal precision | Akurasi digit desimal | `[x]` | PASS - quantize HALF_UP 3 desimal |

### Formula Engine

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-6 | Formula sederhana: `bp_1 * bp_2` | Evaluated correctly | `[x]` | PASS - validator test |
| TC-7 | Formula dengan nested: `(bp_1 + bp_2) * bp_3` | Parentheses respected | `[x]` | PASS - validator test |
| TC-8 | Formula dengan computed param: `cp_1 * 2` | cp value resolved | `[x]` | PASS - validator + integration test |
| TC-9 | Circular reference detection | Error message | `[ ]` | Pending dedicated scenario test |
| TC-10 | Division by zero | Error / Infinity handled | `[ ]` | Pending dedicated scenario test |
| TC-11 | Invalid formula syntax | Error message yang jelas | `[x]` | PASS - invalid/injection/unknown function rejected |
| TC-12 | Formula preview (live) | Real-time calculation | `[~]` | Guard UI regression covered; uji interaksi browser manual pending |
| TC-13 | Undefined parameter reference | Error highlighted | `[x]` | PASS - unknown identifier/function rejected |
| TC-14 | Formula state persistence | State saved across sessions | `[x]` | PASS - lifecycle integration test |

### Parameter Management

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-15 | Create base parameter (bp_N) | Server-generated ID | `[x]` | PASS - opaque ID generation test |
| TC-16 | Create computed parameter (cp_N) | Server-generated ID | `[x]` | PASS - opaque ID generation test |
| TC-17 | Edit parameter label | Label updated, ID unchanged | `[x]` | PASS - edit label keep code test |
| TC-18 | Delete parameter used in formula | Warning / block | `[ ]` | Pending explicit behavior test case |
| TC-19 | Parameter chip/tag UI | Autocomplete, palette modal | `[~]` | Coverage regression UI statik ada; uji browser manual pending |
| TC-20 | ParameterSequence monotonic | IDs always increment | `[x]` | PASS - monotonic counter test |

### Security

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-21 | Formula injection (eval-based XSS) | Sandbox prevents execution | `[x]` | PASS - injection payload rejected |
| TC-22 | Server-side formula validation | Python tokenizer validates | `[x]` | PASS - validator suite + API integration |
| TC-23 | IDOR on parameter endpoints | Owner check | `[x]` | PASS - non-owner blocked (`Http404`) |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Lokasi | Evidence |
|---|----------|-----------|--------|----------|
| F-1 | **RESOLVED (was MEDIUM)** | `api_save_volume_pekerjaan` belum guard ketika item payload bukan objek; berpotensi 500 pada `row.get(...)`. | `detail_project/views_api.py:1656` | Type guard ditambahkan (`"Setiap item harus objek"`), test PASS di `detail_project/tests_volume_pekerjaan_save_api.py:134`. |
| F-2 | **OPEN (LOW)** | Belum ada test terdedikasi untuk circular reference dan division-by-zero di jalur runtime formula end-to-end. | `detail_project/tests_formula_server_validation.py` | Coverage validator luas sudah ada, namun dua skenario ini belum eksplisit sebagai acceptance test runtime. |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Tambahkan guard tipe item payload pada save volume API + regression test malformed payload | P0 | Low | F-1 (`[DONE]`) |
| REC-2 | Tambahkan acceptance tests khusus circular dependency dan divide-by-zero pada workflow formula runtime | P2 | Medium | F-2 (`[OPEN]`) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Patch `api_save_volume_pekerjaan` dengan type guard item payload | - | DONE |
| 2 | 2026-02-17 | Tambah suite `tests_volume_pekerjaan_save_api.py` (validasi numerik, owner guard, malformed payload, partial success) | - | DONE |
| 3 | 2026-02-17 | Tambah suite owner guard parameter/formula (`tests_volume_formula_owner_guard.py`) | - | DONE |
| 4 | 2026-02-17 | Jalankan suite backend R5.2 (`90` tests) | - | DONE |

---

## Checklist Sign-off

- [x] Volume CRUD OK (baseline API)
- [x] Formula engine correct (server validation + lifecycle backend)
- [x] Parameter management OK (opaque ID + sync/versioning backend)
- [x] Formula security (no eval injection)
- [x] Server-side validation OK
- [ ] Performance OK (large formulas)
- [ ] UX/UI OK (manual browser check pending)
- [ ] Reviewer sign-off
