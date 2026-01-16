# Deployment Phase 7 Log

## Backup & Migration

| Step | Timestamp (WIB) | Detail |
|------|-----------------|--------|
| Backup pre-deploy | 2025-11-18 21:31:49 | `backup_pre_deploy_20251118_213149.json` (33,818,039 bytes) |
| Backup hash | 2025-11-18 21:32:10 | SHA256 `D6DBDF7874E6546A7E54D4AA3FC35CD680BD6124A4563477BE3ED09E44837898` |
| migrate_bundle_quantity_semantic --all | 2025-11-19 15:05-15:12 | 111 project diproses, 6 bundle row (4 project, 5 pekerjaan) semua `[OK] Re-expand sukses`, tidak ada error |

Catatan:
- Backup dibuat memakai `PYTHONIOENCODING=utf-8 python manage.py dumpdata`.
- Command migrasi dijalankan setelah backup, output identik dengan log terminal (lihat prompt user 2025-11-19).
