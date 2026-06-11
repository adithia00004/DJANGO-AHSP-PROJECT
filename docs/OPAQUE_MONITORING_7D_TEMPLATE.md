# Monitoring Template: Opaque ID (7 Hari)

## Tujuan
Template pencatatan monitoring harian pasca deploy.

## Command Harian
```bash
bash scripts/opaque_daily_monitor.sh
```

Opsional strict gate:
```bash
python manage.py opaque_post_deploy_status --strict --window-days 7
```

## Tabel Monitoring
| Hari | Tanggal | 4xx/5xx endpoint parameter | Error formula | Keluhan user | non_opaque_base | non_opaque_computed | Catatan |
|------|---------|----------------------------|---------------|--------------|-----------------|---------------------|---------|
| Day 1 |  |  |  |  |  |  |  |
| Day 2 |  |  |  |  |  |  |  |
| Day 3 |  |  |  |  |  |  |  |
| Day 4 |  |  |  |  |  |  |  |
| Day 5 |  |  |  |  |  |  |  |
| Day 6 |  |  |  |  |  |  |  |
| Day 7 |  |  |  |  |  |  |  |

## Kriteria Exit Monitoring
1. Tidak ada regresi kritis selama 7 hari.
2. `non_opaque_base = 0` dan `non_opaque_computed = 0` konsisten.
3. Tidak ada anomali conflict sync yang berulang.

## Setelah Monitoring
1. Jalankan cleanup dry-run:
```bash
python manage.py cleanup_parameter_migration_logs --older-than-days 7 --dry-run --yes
```
2. Jika hasil sesuai, eksekusi cleanup:
```bash
python manage.py cleanup_parameter_migration_logs --older-than-days 7 --yes
```
