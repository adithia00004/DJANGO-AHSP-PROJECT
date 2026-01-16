# Rollback Plan – Bundle Quantity Semantic Refactor

**Last Updated**: 2025-11-18 11:25 WIB
**Owner**: Adit / Bundle Refactor squad

---

## 1. Triggers
Rollback is initiated if any of the following occur after deployment:
1. Data corruption detected in DetailAHSPProject / DetailAHSPExpanded rows
2. Rekap RAB or Rekap Kebutuhan totals deviate >1% from baseline exports
3. Template AHSP save endpoint fails for bundles (HTTP 5xx/4xx bursts)
4. Exports (CSV/PDF/Word) show inconsistent harga satuan for bundles

---

## 2. Prerequisites
- Verified baseline backup: `backup_pre_refactor_20251118_112110.json`
- Git commit hash prior to refactor work: `1781c776a49bc2d186132c73420177539ba25122`
- Access to admin portal / Django shell for validation
- Downtime window (estimated <30 minutes)

---

## 3. Rollback Steps
1. **Notify stakeholders** that rollback is in progress; freeze bundle edits.
2. **Stop application services** (Gunicorn/Celery/worker) to prevent writes.
3. **Database restore**
   ```bash
   # Optional safety dump before rollback
   python manage.py dumpdata > rollback_snapshot_$(date +%Y%m%d_%H%M%S).json

   # Flush + restore baseline
   python manage.py flush --no-input
   python manage.py loaddata backup_pre_refactor_20251118_112110.json
   ```
4. **Code revert**
   ```bash
   git checkout main
   git reset --hard 1781c776a49bc2d186132c73420177539ba25122
   git push --force-with-lease   # only if remote needs rollback
   ```
5. **Re-run migrations** (should be no-op, but included for completeness)
   ```bash
   python manage.py migrate
   ```
6. **Restart services** and clear caches (Redis/memcached/browser assets).
7. **Validation checklist** (see Section 4).

---

## 4. Post-Rollback Validation
- `python manage.py test detail_project` → expect 50/50 passing
- Manual spot checks on:
  - Template AHSP save (bundle koef change modifies harga satuan)
  - Rincian AHSP display (harga satuan follows old multiplier logic)
  - Rekap RAB + Rekap Kebutuhan totals from baseline exports
- Run `diagnose_bundle_koef_issue.py` to confirm API still matches old semantics

Document each validation step + screenshots before declaring rollback complete.

---

## 5. Dry-Run Procedure (Dev/Staging)
1. Use a throwaway DB (e.g., local sqlite copy) to simulate flush/restore.
2. Execute Steps 3–5 against staging branch.
3. Record total duration + unexpected errors here.

### 2025-11-18 – Dry-Run Log
- **Environment**: `config.settings.test` (SQLite in-memory, migrations via `run_syncdb`)
- **Commands**:
  1. `python tmp_dry_run.py` → script menjalankan `migrate(run_syncdb)`, `dumpdata --exclude referensi.AHSPStats`, `flush`, lalu `loaddata` dengan fixture split (`contenttypes` + data utama tanpa `referensi.AHSPStats`), dan verifikasi `DetailAHSPProject.objects.count()`
  2. Fixture baseline dibagi menjadi tiga file: `..._ct.json`, `..._stats.json` (di-skip), `..._rest.json` agar kompatibel dengan SQLite
- **Hasil**:
  - Snapshot: `rollback_dry_run_snapshot_20251118_113807.json`
  - Load ulang sukses (`DetailAHSPProject.count = 133`) → memastikan perintah flush/restore berjalan
  - Catatan khusus: perlu mematikan foreign key (`PRAGMA foreign_keys = OFF`) saat mengosongkan `django_content_type`
- **Durasi**: ±55 detik (seluruh skrip)
- **Status**: ✅ Dry-run berhasil (dengan penyesuaian untuk materialized view PostgreSQL)

---

## 6. Communication Template
```
Subject: [Rollback Triggered] Bundle Quantity Semantic Refactor

Hi team,
We observed <ISSUE SUMMARY>. Initiating rollback per plan v2025-11-18.

ETA to completion: <xx minutes>. We will notify once validation passes.

Thanks,
Adit
```

---

## 7. References
- `backup_pre_refactor_20251118_112110.json`
- `BASELINE_BEHAVIOR_PRE_REFACTOR.md`
- `REFACTOR_PROGRESS_TRACKER.md` Phase 0 Task 0.5
