# Deployment Plan - Bundle Quantity Semantic

**Last Updated:** 2025-11-19
**Scope:** Langkah-langkah men-deploy perubahan quantity semantic (Phase 7) dari branch `refactor/bundle-quantity-semantic` ke environment staging/production.

## 1. Prasyarat
- Semua perubahan sudah di-merge ke branch release (atau siap PR merge).
- Database backup terbaru tersedia.
- Migration command `migrate_bundle_quantity_semantic` sudah diuji (dry-run + run di dev/staging).
- Log regression terbaru: `logs/phase5_test_run_20251119_full.md`.

## 2. Final Backup (Task 7.1)
1. Aktifkan virtualenv & masuk project root.
2. Jalankan:
   ```bash
   python manage.py dumpdata > backup_pre_deploy_$(date +%Y%m%d_%H%M%S).json
   ```
3. Simpan file di folder backup + catat checksum/S3 path.
4. Verifikasi cepat:
   ```bash
   python manage.py loaddata backup_pre_deploy_YYYYMMDD_HHMMSS.json --dry-run
   ```

## 3. Merge & Tag (Task 7.2)
1. Buka PR `refactor/bundle-quantity-semantic` → `main`.
2. Pastikan CI hijau + reviewer approve.
3. Merge dan buat tag `bundle-quantity-semantic-release-2025-11-19`.
4. Catat commit hash di tracker + change log release.

## 4. Deploy ke Staging (Task 7.3 - Opsional)
1. Pull commit terbaru di staging server.
2. Jalankan:
   ```bash
   python manage.py migrate_bundle_quantity_semantic --all
   python manage.py collectstatic --noinput
   ```
3. Smoke test Rincian AHSP (ubah koef bundle, cek export) + jalankan subset pytest bila perlu.
4. Tandai hasil di tracker.

## 5. Deploy ke Production (Task 7.4)
1. Pastikan backup final tersedia (Task 7.1).
2. SSH ke server production:
   ```bash
   git pull origin main
   python manage.py migrate_bundle_quantity_semantic --all
   python manage.py collectstatic --noinput
   sudo systemctl restart gunicorn  # contoh
   ```
3. Monitor log & dashboard (APM/Log aggregation) minimal 30 menit.
4. Jika terjadi error fatal, ikuti rollback plan (`ROLLBACK_PLAN_BUNDLE_QUANTITY.md`).

## 6. Post-Deployment Verification (Task 7.5)
- Jalankan smoke test UI (Template AHSP, Rincian AHSP, Export) dan subset pytest:
  ```bash
  pytest detail_project/tests/test_bundle_quantity_semantic.py -k bundle --maxfail=1
  ```
- Jalankan `diagnose_bundle_koef_issue.py` untuk sampling project bundle.
- Minta owner melakukan UAT singkat (cek pekerjaan custom/bundle).
- Catat hasil + waktu verifikasi di tracker.

## 7. Rollback Referensi
- Lihat `ROLLBACK_PLAN_BUNDLE_QUANTITY.md` untuk langkah detail (restore backup, revert code, smoke test ulang).

## 8. Dokumentasi Pendukung
- `MIGRATION_GUIDE_BUNDLE_QUANTITY.md`
- `REFACTOR_PROGRESS_TRACKER.md`
- `logs/phase5_test_run_20251119_full.md`
- `detail_project/BUNDLE_SYSTEM_ARCHITECTURE.md`
