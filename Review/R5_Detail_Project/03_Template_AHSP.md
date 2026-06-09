# R5.3 - Review Template AHSP

**Status:** `[~]` ONGOING - hardening API template library selesai, uji UI/manual flow masih berjalan
**Terakhir diperbarui:** 2026-02-17

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/detail_project/<project_id>/template-ahsp/` |
| View | `detail_project.views.template_ahsp_view` |
| Template | `detail_project/templates/detail_project/template_ahsp.html` |
| JS | `template_ahsp.js` |
| CSS | `template_ahsp.css` |

### API Endpoints

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| GET | `api/templates/` | List all templates |
| GET | `api/templates/<id>/` | Get template detail |
| POST | `api/templates/<id>/delete/` | Delete template |
| POST | `api/project/<id>/templates/create/` | Create from project |
| POST | `api/project/<id>/templates/<tid>/import/` | Import into project |
| POST | `api/project/<id>/templates/import-file/` | Import from file |
| GET | `api/project/<id>/templates/export/` | Export template |

---

## Audit Fungsional

### Test Cases

| # | Test Case | Expected | Status | Hasil |
|---|-----------|----------|--------|-------|
| TC-1 | List semua template user | Templates tampil | `[x]` | PASS - public + private milik user tampil, private user lain tersembunyi |
| TC-2 | Create template dari project | Template tersimpan | `[ ]` | Pending uji endpoint create + UI modal |
| TC-3 | Import template ke project | Data ter-import | `[x]` | PASS - import template public lintas user berhasil |
| TC-4 | Import template from file | File parsed + imported | `[x]` | PASS - valid payload diproses; error runtime ditangani aman |
| TC-5 | Export template as JSON | File downloaded | `[ ]` | Pending uji end-to-end download |
| TC-6 | Delete template | Template terhapus | `[ ]` | Pending uji endpoint delete via UI |
| TC-7 | Template detail view | Rincian AHSP tampil | `[x]` | PASS - creator bisa akses detail private |
| TC-8 | Import template - duplicate handling | Conflict resolution | `[ ]` | Pending uji nama template duplikat/race |
| TC-9 | Import file - invalid format | Error message | `[x]` | PASS - invalid content ditolak 400 |
| TC-10 | Template ownership isolation | Only owner sees own templates | `[x]` | PASS - private template terisolasi |
| TC-11 | IDOR protection | Cannot access other user's templates | `[x]` | PASS - detail/import private user lain -> 404 |

### Tambahan Regresi API (baru)

| # | Skenario | Expected | Status | Hasil |
|---|----------|----------|--------|-------|
| API-R1 | Template stats untuk format flat (`project_template`) | `total_klasifikasi/sub/pekerjaan` akurat | `[x]` | PASS - stats terhitung sesuai flat arrays |
| API-R2 | `api/templates/` menampilkan public + private milik sendiri | Isolasi data terjaga | `[x]` | PASS - coverage test endpoint |
| API-R3 | `api/templates/<id>/` private milik user lain | 404 | `[x]` | PASS |
| API-R4 | `api/project/<id>/templates/<tid>/import/` private milik user lain | 404 | `[x]` | PASS |
| API-R5 | Error internal import-file | Pesan generik, tanpa leak detail internal | `[x]` | PASS |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Lokasi | Evidence |
|---|----------|-----------|--------|----------|
| F-1 | **RESOLVED (was HIGH)** | Statistik template (`total_sub`, `total_pekerjaan`) salah untuk format export baru (flat arrays), berpotensi menampilkan angka 0 di library. | `detail_project/models.py:1312` | Perhitungan stats kini mendukung format flat + nested; test PASS di `detail_project/tests_template_library_api.py:109`. |
| F-2 | **RESOLVED (was MEDIUM)** | Endpoint detail/import template belum membatasi akses template private secara eksplisit (risiko IDOR/read access). | `detail_project/views_api.py:8427` | Access guard `_can_access_template` diterapkan di list/detail/import; test PASS di `detail_project/tests_template_library_api.py:157` dan `detail_project/tests_template_library_api.py:186`. |
| F-3 | **RESOLVED (was LOW)** | Endpoint import-file mengembalikan detail exception mentah pada error 500 (information disclosure). | `detail_project/views_api.py:9061` | Error kini generik + logging terstruktur; test PASS di `detail_project/tests_template_library_api.py:228`. |
| F-4 | **OPEN (LOW)** | Validasi duplikasi nama template masih global (`name` unik seluruh sistem), belum ada namespace per-user/per-team. | `detail_project/models.py:1257` | Berpotensi friction saat banyak user membuat template dengan nama umum. |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort | Terkait |
|---|-------------|-----------|--------|---------|
| REC-1 | Dukungan stats untuk format content flat + nested di model template | P0 | Low | F-1 (`[DONE]`) |
| REC-2 | Tambahkan guard akses template private di list/detail/import | P0 | Low | F-2 (`[DONE]`) |
| REC-3 | Ganti debug print/error mentah menjadi logger + pesan generik | P1 | Low | F-3 (`[DONE]`) |
| REC-4 | Evaluasi perubahan unique constraint nama template ke `(created_by, name)` atau slug scoped | P2 | Medium | F-4 (`[OPEN]`) |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| 1 | 2026-02-17 | Patch `PekerjaanTemplate.save()` agar stats kompatibel format flat + nested | - | DONE |
| 2 | 2026-02-17 | Patch access control template library (`list/detail/import`) untuk private visibility | - | DONE |
| 3 | 2026-02-17 | Hardening `api_import_template_from_file` (hapus print debug + generic error message) | - | DONE |
| 4 | 2026-02-17 | Tambah suite `tests_template_library_api.py` (7 test) | - | DONE |
| 5 | 2026-02-17 | Re-run regression suite gabungan R5.1-R5.3 (`114` tests) | - | DONE |

---

## Checklist Sign-off

- [x] CRUD OK (baseline API list/detail/import)
- [x] Import/Export OK (backend import flow tervalidasi)
- [x] Authorization OK
- [x] File upload security OK (error handling hardened)
- [ ] Reviewer sign-off
