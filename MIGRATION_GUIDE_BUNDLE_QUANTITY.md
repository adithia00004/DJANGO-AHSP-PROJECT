# Migration Guide - Bundle Quantity Semantic

**Last Updated:** 2025-11-19
**Scope:** Memigrasikan data `DetailAHSPExpanded` agar menyimpan koef komponen per unit bundle.

---

## 1. Prasyarat
- Django settings siap (gunakan `config.settings` / environment produksi sesuai SOP).
- Pastikan tidak ada job async/background yang sedang menulis ke `DetailAHSPProject`.
- Siapkan window maintenance ±30 menit (eksekusi penuh <10 menit, sisanya verifikasi).

Checklist:
- [ ] Database backup terbaru tersedia di folder aman.
- [ ] Repo berada di branch `refactor/bundle-quantity-semantic` atau release tag yang sudah diuji.
- [ ] Virtualenv aktif (`pip install -r requirements.txt` sudah dilakukan).

---

## 2. Backup
1. Jalankan dumpdata (atau mekanisme backup DB produksi) sebelum migrasi:
   ```bash
   python manage.py dumpdata > backup_pre_migration_$(date +%Y%m%d_%H%M%S).json
   ```
2. Simpan file backup di lokasi aman (lihat contoh `backup_pre_migration_20251118_142958.json`).

---

## 3. Dry-Run
Gunakan opsi `--dry-run` untuk memastikan scope migrasi:
```bash
python manage.py migrate_bundle_quantity_semantic --all --dry-run
```
Output yang diharapkan:
- Menampilkan daftar project + jumlah bundle yang akan diproses.
- Mengakhiri dengan ringkasan (`Project diproses`, `Total bundle`, `Dry-run: tidak ada perubahan yang disimpan`).
Jika terjadi error, **jangan lanjut** ke langkah berikutnya dan perbaiki dulu (cek log).

---

## 4. Eksekusi Aktual
Setelah dry-run bersih:
```bash
python manage.py migrate_bundle_quantity_semantic --all
```
Catatan:
- Command membungkus `_populate_expanded_from_raw` dalam `transaction.atomic`, sehingga jika terjadi error seluruh update akan di-rollback otomatis.
- Monitor output; pastikan tidak ada exception.

---

## 5. Verifikasi
1. Jalankan diagnostic untuk memastikan seluruh bundle memiliki `DetailAHSPExpanded` per-unit:
   ```bash
   python manage.py shell --command="exec(open('diagnose_bundle_koef_issue.py').read())"
   ```
2. Jalankan regression minimal:
   ```bash
   pytest detail_project/tests/test_bundle_quantity_semantic.py
   pytest detail_project/tests/test_dual_storage.py -k bundle
   ```
3. Opsional: full suite `pytest detail_project/tests/ -v` (lihat `logs/phase5_test_run_20251119_full.md`).
4. Sampling manual: buka beberapa project (rincian/template) dan ubah koef bundle → `harga_satuan` tetap, `jumlah` mengikuti koef baru.

---

## 6. Troubleshooting
- **Command timeout / crash:** cek log output. Jalankan ulang command; karena atomic, data tidak akan setengah migrasi.
- **Bundle tidak berubah:** jalankan diagnostic script untuk memastikan pekerjaan bersangkutan ikut scope (kategori LAIN + referensi).
- **Harga satuan tetap salah setelah migrasi:** pastikan frontend sudah diperbarui (build terbaru) dan cache browser dibersihkan.

---

## 7. Rollback (Jika Diperlukan)
Jika perlu revert, ikuti `ROLLBACK_PLAN_BUNDLE_QUANTITY.md`:
1. Stop app (jika produksi).
2. Restore database dari backup `backup_pre_migration_YYYYMMDD_HHMMSS.json` atau snapshot DB.
3. Revert kode ke commit sebelum migrasi (`git checkout <pre-migration-commit>`).
4. Jalankan kembali regresi minimal.

---

## 8. Referensi
- `detail_project/management/commands/migrate_bundle_quantity_semantic.py`
- `logs/phase5_test_run_20251119_full.md`
- `detail_project/BUNDLE_SYSTEM_ARCHITECTURE.md`
- `detail_project/RINCIAN_AHSP_DOCUMENTATION.md`
