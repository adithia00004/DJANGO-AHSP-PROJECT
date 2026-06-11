# Save/Sync Hardening Baseline

Tanggal: 2026-06-08

## Git Checkpoint

- Branch aktif: `main`
- HEAD awal: `69059282`
- Snapshot commit: `8495de6e73e16606f62c99de70a37973de7d7b8c`
- Tag: `pre-sync-hardening-20260608`

Checkpoint dibuat melalui temporary Git index. Branch dan staging utama tidak diubah.
Scope checkpoint:

- `config/settings`
- `detail_project`
- `referensi/templates/referensi/import_validate_report.html`
- `referensi/views/import_views.py`
- `referensi/tests`
- dokumen audit dan implementation plan save/sync
- `Dockerfile` dan `docker-entrypoint.sh`

## Baseline Validation

### Django system check

```text
System check identified no issues (0 silenced).
```

### JavaScript syntax

Target berikut lulus `node --check`:

- `volume_pekerjaan.js`
- `template_ahsp.js`
- `harga_items.js`
- `detail_ahsp_gabungan.js`
- `sync_led.js`
- `jadwal_kegiatan_app.js`
- `src/modules/core/save-handler.js`

### Pytest detail_project

```text
246 passed, 6 failed, 4 warnings
```

Failure baseline:

1. `tests_phase1_opaque_api.py::test_c3_replace_sync_keeps_database_consistent`
2. `tests_phase4_negative_param.py::test_model_allows_negative_value`
3. `tests_phase4_negative_param.py::test_sync_endpoint_accepts_negative_value`
4. `tests_template_ahsp_formula_state.py::test_formula_save_keeps_harga_item_and_rekap_computation_consistent`
5. `tests_template_ahsp_formula_state.py::test_save_detail_uses_last_save_wins_even_with_stale_client_timestamp`
6. `tests_template_ahsp_formula_state.py::test_save_detail_without_formula_still_succeeds_and_keeps_sidecar_empty`

Tiga failure pertama adalah mismatch ekspektasi representasi `Decimal` 3 digit vs model 12 digit.
Tiga failure berikutnya berada pada penyimpanan Template AHSP formula/detail.

Failure tersebut sudah ada sebelum implementasi hardening save/sync dimulai dan dipakai sebagai pembanding regresi.

### Diff check

Baseline `git diff --check` memiliki issue yang sudah ada:

- blank line di EOF `detail_project/static/detail_project/js/rincian_ahsp.js`
- trailing whitespace `docs/PANDUAN_USER.md`
- trailing whitespace pada dua baris `referensi/views/import_views.py`

Implementasi save/sync tidak boleh menambah issue `diff --check` baru.
