# R5.1 - Review List Pekerjaan

**Status:** `[!]` ONGOING - backend API hardening selesai, **1 HIGH XSS ditemukan pada template library modal**, audit end-to-end UI masih berjalan
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/detail_project/<project_id>/list-pekerjaan/` |
| View | `detail_project.views.list_pekerjaan_view` |
| Template | `detail_project/templates/detail_project/list_pekerjaan.html` |
| JS | `list_pekerjaan.js` |
| CSS | `list_pekerjaan.css` |
| Auth Required | Ya (login_required + owner check) |

### API Endpoints Terkait

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| POST | `api/project/<id>/list-pekerjaan/save/` | Save pekerjaan |
| GET | `api/project/<id>/list-pekerjaan/tree/` | Get tree structure |
| POST | `api/project/<id>/list-pekerjaan/upsert/` | Upsert pekerjaan |
| GET | `api/project/<id>/export/list-pekerjaan/json/` | Export JSON |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | Load tree structure | Klasifikasi -> Sub -> Pekerjaan hierarchy | `[~]` | API/view terinspeksi; uji UI manual pending |
| TC-2 | Tambah Klasifikasi baru | Node root ditambahkan | `[ ]` | Pending uji UI/API end-to-end |
| TC-3 | Tambah SubKlasifikasi | Node child ditambahkan | `[ ]` | Pending uji UI/API end-to-end |
| TC-4 | Tambah Pekerjaan (Custom) | Pekerjaan baru tersimpan | `[ ]` | Pending uji UI/API end-to-end |
| TC-5 | Tambah Pekerjaan dari Referensi | Data referensi ter-load | `[ ]` | Pending uji UI/API end-to-end |
| TC-6 | Edit nama/uraian pekerjaan | Data updated | `[ ]` | Pending uji UI/API end-to-end |
| TC-7 | Delete pekerjaan | Cascade delete volume, AHSP, dll | `[ ]` | Pending uji UI/API end-to-end |
| TC-8 | Drag & drop reorder | Urutan tersimpan | `[~]` | Coverage parsial (move case teruji) |
| TC-9 | Drag & drop move antar klasifikasi | Parent berubah | `[x]` | PASS - regression test `tests_list_pekerjaan_upsert_drag_drop` |
| TC-10 | Expand/collapse tree nodes | Visual toggle benar | `[ ]` | Pending uji UI manual |
| TC-11 | Search/filter pekerjaan | Hasil filter akurat | `[ ]` | Pending uji UI/API |
| TC-12 | Auto-save vs manual save | Save behavior konsisten | `[ ]` | Pending uji UI manual |
| TC-13 | Concurrent edit detection | Conflict handling | `[~]` | Write diserialkan (`select_for_update`), conflict UX belum eksplisit |
| TC-14 | Empty project (0 pekerjaan) | Empty state UI | `[ ]` | Pending uji UI manual |
| TC-15 | Large project (100+ pekerjaan) | Performance acceptable | `[ ]` | Pending benchmark |
| TC-16 | XSS pada nama pekerjaan | Input sanitized | `[!]` | GAGAL - Template Library modal tidak escape `t.name`/`k.name`/`s.name` (lihat F-4) |
| TC-17 | IDOR - akses project orang lain | 403 / 404 | `[x]` | PASS - non-owner upsert ditolak (`Http404`) |
| TC-18 | Responsive - Mobile | Usable di mobile | `[ ]` | Pending uji device nyata |

### Tambahan Regresi API (baru)

| # | Skenario | Expected | Status | Hasil |
|---|----------|----------|--------|-------|
| API-R1 | Duplikat `ordering_index` pada `klasifikasi` | 400 + error path jelas | `[x]` | PASS - validasi preflight aktif |
| API-R2 | Duplikat `ordering_index` pada `sub` (dalam klasifikasi yang sama) | 400 + error path jelas | `[x]` | PASS - validasi preflight aktif |
| API-R3 | Node payload bukan objek (`string/null`) | 400 + error path jelas | `[x]` | PASS - type guard aktif |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Lokasi | Evidence |
|---|----------|-----------|--------|----------|
| F-1 | **RESOLVED (was HIGH)** | Payload dengan duplikat `ordering_index` (`klasifikasi/sub`) berpotensi memicu `IntegrityError` dan 500 saat upsert. | `detail_project/views_api.py:993` | Preflight kini menolak duplikat dengan 400 + `errors[].path`; test PASS di `detail_project/tests_list_pekerjaan_upsert_validation.py:46` dan `detail_project/tests_list_pekerjaan_upsert_validation.py:92`. |
| F-2 | **RESOLVED (was MEDIUM)** | Payload node non-objek (`string/null`) berpotensi memicu error server karena akses `.get`. | `detail_project/views_api.py:997` | Type guard untuk `klasifikasi/sub/pekerjaan` aktif; test PASS di `detail_project/tests_list_pekerjaan_upsert_validation.py:132`. |
| F-3 | **OPEN (MEDIUM)** | Conflict handling UI untuk concurrent edit belum eksplisit (lebih ke last-writer-serialized). | `detail_project/views_api.py:957` | Ada lock project (`select_for_update`) namun belum ada mekanisme versi/409 untuk konflik pengguna. |
| F-4 | **OPEN (HIGH)** | **Stored XSS via Template Library modal.** Template name/content names dirender via `innerHTML` tanpa `escapeHtml()`. `escapeHtml` sudah ada (line 933) dan dipakai di TOC/builder, tapi TIDAK di template library section. | `list_pekerjaan.js:2417,2468,2470` | Attack: template public dengan nama `<img src=x onerror=alert(1)>` mengeksekusi script pada semua user yang buka Template Library modal. Server API (`api_list_templates:8468`, `api_get_template_detail:8520`) mengembalikan nama mentah. |
| F-5 | **OPEN (MEDIUM)** | `api_save_list_pekerjaan` (line 651) tidak punya type guard `isinstance(k, dict)` sebelum `k.get('name')`. Payload malformed bisa 500. | `detail_project/views_api.py:651` | Endpoint upsert sudah punya guard (line 996), tapi full-save endpoint belum. Dimitigasi: endpoint deprecated (komentar mengarahkan ke upsert). |
| F-6 | **OPEN (LOW)** | `api_upsert_list_pekerjaan` tidak punya decorator `@rate_limit` seperti `api_save_list_pekerjaan`. | `detail_project/views_api.py:932` | Endpoint save punya `@rate_limit(category='write')` (line 619), upsert tidak. |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Validasi preflight duplikat `ordering_index` + type guard payload (API upsert) | P0 | Low | F-1, F-2 (`[DONE]`) |
| REC-2 | Tambahkan conflict token/versioning (`etag`/`updated_at` check) agar user dapat feedback konflik edit real-time | P1 | Medium | F-3 (`[OPEN]`) |
| REC-3 | **Escape template names di JS**: Tambahkan `escapeHtml()` pada `t.name`, `k.name`, `s.name` di template library rendering (lines 2417, 2468, 2470) | P0 (Pre-launch) | Low (15 min) | F-4 (`[OPEN]`) |
| REC-4 | Tambahkan type guard `isinstance(k, dict)` di `api_save_list_pekerjaan` (line 651), sama seperti di upsert | P1 | Low (10 min) | F-5 (`[OPEN]`) |
| REC-5 | Tambahkan `@rate_limit(category='write')` pada `api_upsert_list_pekerjaan` | P2 | Low (5 min) | F-6 (`[OPEN]`) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Tambah validasi preflight upsert: deteksi duplikat `ordering_index` pada `klasifikasi/sub` + type guard node payload | - | DONE |
| 2 | 2026-02-17 | Tambah regression tests untuk duplikat order, node invalid, dan non-owner upsert | - | DONE |
| 3 | 2026-02-17 | Re-run suite terkait R5.1 (`13` test) | - | DONE |

---

## Checklist Sign-off

- [ ] Tree CRUD OK (uji end-to-end belum selesai)
- [ ] Drag & drop OK (reorder full flow belum selesai)
- [ ] Reference import OK
- [x] API endpoints secure (baseline untuk endpoint upsert)
- [ ] Performance OK
- [ ] XSS protection OK
- [x] IDOR protection OK
- [ ] Reviewer sign-off
