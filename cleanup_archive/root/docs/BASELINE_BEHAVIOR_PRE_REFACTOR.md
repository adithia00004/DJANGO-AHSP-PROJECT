# Baseline Behavior – Pre Refactor

**Captured**: 2025-11-18 11:22 WIB
**Environment**: local dev (manage.py test DB)

## Backup Snapshot
- File: `backup_pre_refactor_20251118_112110.json`
- Size: 33,843,677 bytes
- Command: `PYTHONIOENCODING=utf-8 python manage.py dumpdata | Out-File -Encoding utf8 backup_pre_refactor_20251118_112110.json`
- Notes: initial attempt without UTF-8 failed because of `UnicodeEncodeError` (see shell history)

## Baseline Automated Tests
- Command: `python manage.py test detail_project`
- Result: **PASS** (50 tests, 0 failures, runtime 18.7s)
- Notable warnings logged: repeated Bad Request notices for `/volume-pekerjaan/save/` (expected from fixture-driven tests)

## Manual Verification Checklist
| Feature | Scenario | Expected (Current System) | Evidence |
|---------|----------|---------------------------|----------|
| Template AHSP Save | Edit pekerjaan bundle, save | Harga satuan recalculates as `bundle_total / new_koef` (legacy behavior) | Pending screenshot |
| Rincian AHSP Display | Bundle koef 10➝5 | Harga satuan changes, jumlah tetap | Pending screenshot |
| Rekap RAB | Aggregation for pekerjaan with bundles | Totals remain constant when bundle koef changes | Pending screenshot |
| Rekap Kebutuhan | Same bundle used by 2 pekerjaan | Quantities double-counted via expansion multiplier | Pending screenshot |
| Export CSV/PDF | Export project with 3+ bundles | Matches current (incorrect) semantics | Pending export files |

> TODO: Capture screenshots/exports for each scenario above and store under `baseline_media/` for comparison after refactor.

## References
- Diagnostics to run later: `diagnose_bundle_koef_issue.py`
- Roadmap alignment: PHASE 0 Task 0.4 (doc) & Task 0.5 (rollback plan)
