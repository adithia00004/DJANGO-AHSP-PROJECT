# Runbook Production: Opaque ID Parameter

## Tujuan
Eksekusi rollout Opaque ID (`bp_N`/`cp_N`) ke production secara aman, terukur, dan bisa rollback.

## Ruang Lingkup
- Phase 0 deploy gate
- Phase 3A data migration
- Phase 1 deploy gate (strict mode)
- Phase 2 deploy gate (UI formula chip/tag)
- Post-deploy monitoring + cleanup migration log

## Prasyarat
- Akses shell server (`python manage.py ...`).
- Backup database production dapat dibuat dan diverifikasi restore-nya.
- Kode branch release sudah berisi migration:
  - `0037_projectcomputedparameter`
  - `0038_alter_projectparameter_value`
  - `0039_parametersequence`
  - `0040_parametermigrationlog`

## Gate Checklist (Pass/Fail)
- Gate A (Staging): semua test release pass.
- Gate B (Production pre-migration): backup DB sukses.
- Gate C (Migration): `migrate_parameters_to_opaque` selesai tanpa `failed`.
- Gate D (Strict mode): CRUD/sync parameter di UI normal, conflict 409 UX normal.
- Gate E (Post deploy 1 minggu): error rate stabil, tidak ada lonjakan bug formula.
- Gate F (Cleanup): `ParameterMigrationLog` tua sudah dibersihkan sesuai rollback window.

## 1) Staging Rehearsal (Wajib)
Jalankan di staging lebih dulu:

```bash
python manage.py check
python manage.py migrate
python manage.py test --noinput detail_project.tests_phase0_data_safety detail_project.tests_phase1_opaque_api detail_project.tests_phase3a_migration detail_project.tests_phase45_rollback detail_project.tests_phase4_negative_param detail_project.tests_volume_export_adapter detail_project.tests_cleanup_parameter_migration_logs
```

Kriteria pass:
- Semua command exit code `0`.
- Test suite pass 100%.

## 2) Production Pre-Migration (Wajib)
1. Freeze deploy window.
2. Backup database production (`scripts/safe_backup_db.sh`).
3. Simpan metadata backup: waktu, ukuran, lokasi file, operator.

Kriteria pass:
- Backup sukses dan bisa di-restore (minimal metadata verifikasi).

## 3) Apply App + DB Migration (Production)
```bash
python manage.py check
python manage.py migrate
```

Kriteria pass:
- Tidak ada migration failure.
- Endpoint app kembali healthy.

## 4) Dry-Run Data Migration (Production)
Semua project:

```bash
python manage.py migrate_parameters_to_opaque --dry-run --yes
```

Atau per project:

```bash
python manage.py migrate_parameters_to_opaque --project-id <PROJECT_ID> --dry-run --yes
```

Kriteria pass:
- Summary `failed: 0`.
- Tidak ada error identifier invalid.

## 5) Execute Data Migration (Production)
Semua project:

```bash
python manage.py migrate_parameters_to_opaque --yes
```

Atau per project:

```bash
python manage.py migrate_parameters_to_opaque --project-id <PROJECT_ID> --yes
```

Kriteria pass:
- Summary `failed: 0`.
- Statistik migrasi masuk akal (`base_migrated`, `computed_migrated`, `volume_formulas_updated`).

## 6) Spot Verification (Production)
Verifikasi cepat satu project sampel:

```bash
python manage.py shell -c "from detail_project.models import ProjectParameter, ProjectComputedParameter; pid=<PROJECT_ID>; print('BASE sample:', list(ProjectParameter.objects.filter(project_id=pid).values_list('name','label')[:10])); print('CP sample:', list(ProjectComputedParameter.objects.filter(project_id=pid).values_list('name','label')[:10]))"
```

Kriteria pass:
- Nama base dominan `bp_*`.
- Nama computed dominan `cp_*`.
- Label tetap benar.

Validasi global cepat:

```bash
python manage.py opaque_post_deploy_status --strict --window-days 7
```

Kriteria pass:
- `STRICT_GATE=PASS`

## 7) Strict Mode Deploy (Phase 1)
Pastikan env:

```text
OPAQUE_ID_ENABLED=True
```

Lalu deploy/restart service app.

Smoke test minimal:
1. Buat parameter baru di UI, pastikan tersimpan.
2. Edit label parameter, pastikan formula tetap valid.
3. Multi-tab test: tab A update, tab B sync -> muncul conflict modal 409.

## 8) Phase 2 Gate (UI Formula)
Manual QA:
1. Autocomplete label bekerja.
2. Chip/tag formula tampil normal.
3. Error message formula pakai label (bukan hanya kode mentah).
4. Export formula human-readable (label) tetap benar.

Jika pass, lakukan deploy phase 2.

## 9) Rollback Procedure
### 9.1 Rollback cepat runtime
Set env:

```text
OPAQUE_ID_ENABLED=False
```

Deploy ulang app untuk fallback mode legacy runtime.

### 9.2 Rollback data (jika diperlukan)
Dry-run dulu:

```bash
python manage.py rollback_parameters_from_opaque --project-id <PROJECT_ID> --dry-run --yes
```

Eksekusi rollback:

```bash
python manage.py rollback_parameters_from_opaque --project-id <PROJECT_ID> --yes
```

Untuk state campuran (mapping log tidak lengkap), gunakan:

```bash
python manage.py rollback_parameters_from_opaque --project-id <PROJECT_ID> --allow-missing-log --yes
```

## 10) Post-Deploy Monitoring (7 Hari)
Checklist harian:
1. Pantau 4xx/5xx endpoint parameter sync.
2. Pantau error formula evaluation.
3. Pantau keluhan user terkait formula/parameter hilang.

Command harian:

```bash
bash scripts/opaque_daily_monitor.sh
```

Template pencatatan:
- `docs/OPAQUE_MONITORING_7D_TEMPLATE.md`

## 11) Cleanup Migration Log (Setelah Rollback Window Lewat)
Dry-run:

```bash
python manage.py cleanup_parameter_migration_logs --older-than-days 7 --dry-run --yes
```

Eksekusi:

```bash
python manage.py cleanup_parameter_migration_logs --older-than-days 7 --yes
```

Opsional per project:

```bash
python manage.py cleanup_parameter_migration_logs --project-id <PROJECT_ID> --older-than-days 7 --yes
```

Kriteria pass:
- Hanya log di luar rollback window yang terhapus.

Validasi cleanup gate:

```bash
python manage.py opaque_post_deploy_status --strict --require-cleanup --window-days 7
```
