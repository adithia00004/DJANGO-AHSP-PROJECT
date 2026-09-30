# 44 — Rencana Merge ke `main` & Review WIP Owner

| | |
|---|---|
| Tanggal | 2026-09-30 |
| Sifat | Rencana + hasil pemeriksaan. **Belum ada merge, belum ada commit WIP owner** (keputusan owner) |
| Oleh | Claude |

---

## 1. Kondisi branch

- `main` = `69059282`, terakhir **2026-06-08**. Sejak itu tidak ada yang di-merge.
- Semua pekerjaan Juni–September berada dalam **satu garis lurus** 13 branch bertumpuk. Ujungnya adalah `feat/tambahan-waktu-kerja`. Tidak ada commit di `main` yang belum ada di ujung.

| Urutan | Branch (ujung garis ↓) | Commit di atas `main` |
|---|---|---|
| 1 | `checkpoint/save-sync-plan-20260608` | 79 |
| 2 | `checkpoint/r5-planning-wp-b1-start-20260614` | 80 |
| 3 | `implementation/r5-master-plan-20260614` | 199 |
| 4 | `fix/referensi-n7-import-rate-limit` | 201 |
| 5 | `fix/referensi-low-n5-n4` | 206 |
| 6 | `fix/accounts-admin-subscription` | 207 |
| 7 | `fix/r1-pages-polish` | 209 |
| 8 | `fix/r4-dashboard-f07` | 212 |
| 9 | `feat/export-visual-refinement` | 230 |
| 10 | `fix/db-connection-leak` | 269 |
| 11 | `fix/laporan-harian` | 270 |
| 12 | `fix/laporan-bulanan` | 275 |
| 13 | `feat/edit-massal-discoverability` | 276 |
| 14 | `feat/tambahan-waktu-kerja` | 315+ |

**Uji konflik tanpa menulis** (`git merge-tree --write-tree main HEAD`): **bersih, tanpa konflik**. Merge akan berupa **fast-forward**.

Catatan skala:
- Diff `main..HEAD` menyentuh ±20.500 berkas.
- Sebagian besar adalah penghapusan `node_modules/` dan `cleanup_archive/` yang dulu ikut ter-commit di `main`. Ini memang seharusnya dihapus.

### Migrasi yang akan berjalan saat deploy (27)

- `accounts` 0003
- `dashboard` 0015–0017, termasuk **0017 `tanggal_akhir_tambahan`**
- `detail_project` 0037–0051, termasuk backfill 0047/0050 dan constraint 0051
- `referensi` 0021–0024
- `subscriptions` 0003–0006

Backfill **0047/0050** dan constraint **0051** menyentuh data. Jalankan di salinan database produksi dulu.

## 2. Rencana merge (usulan)

1. **Syarat sebelum merge:**
   - (a) cek visual owner atas sampel export dan skenario UI (doc 41 §6, doc 43 §5);
   - (b) suite penuh `detail_project` + `dashboard` hijau;
   - (c) Vitest + `npm run build`;
   - (d) `manage.py makemigrations --check`;
   - (e) WIP owner sudah di-commit atau disimpan di branch sendiri, supaya tidak tertinggal di working tree.
2. **Tag pengaman:** `git tag pre-merge-main-20260930 main`, supaya `main` lama selalu bisa dikembalikan.
3. **Merge** (pilih satu):
   - **Satu langkah:** `git switch main && git merge --ff-only feat/tambahan-waktu-kerja`. Rekomendasi, karena garisnya lurus.
   - **Bertahap:** fast-forward ke ujung tiap branch sesuai urutan tabel. Jalankan suite di tiap titik bila ingin jejak per tahap.
4. **Belum push.** Push ke remote dan deploy diputuskan owner terpisah.
5. **Sesudah merge:** hapus branch yang sudah tergabung (opsional), perbarui catatan memori/tracker.

## 3. Review WIP owner (belum di-commit)

Semua WIP diuji di database tes terpisah: **58 tes lulus**. Modul yang diuji:
- `dashboard.tests_mass_edit`
- `dashboard.tests_prelaunch_smoke`
- `detail_project.tests_list_pekerjaan_grow_tree`
- `detail_project.tests_timeline_repair_ui`

| # | Topik | Berkas | Isi | Penilaian |
|---|---|---|---|---|
| W-1 | Simpan List Pekerjaan (menambah baris) | `detail_project/views_api.py` (`api_upsert_list_pekerjaan`), `tests_list_pekerjaan_grow_tree.py` (baru) | Offset parkir `ordering_index` = max + 1.000.000 (dulu parkir bisa menabrak posisi final saat baris ditambah → UniqueViolation); `bulk_update` alih-alih save per baris; baris yang tidak berubah tidak di-`save()` (tanpa sinyal cache), urutannya dipulihkan sekali di akhir | **Siap commit.** Memperbaiki bug nyata (menambah pekerjaan gagal) dan mengurangi query/sinyal. Tes baru mengunci skenario |
| W-2 | Edit Massal: Tanggal Selesai wajib, kolom tinggi | `dashboard/static/dashboard/js/mass-edit-toggle.js`, `dashboard/templates/dashboard/dashboard.html`, `dashboard/static/dashboard/css/dashboard.css`, `dashboard/tests_mass_edit.py`, `dashboard/tests_prelaunch_smoke.py`, `dashboard/models.py` (komentar) | `tanggal_selesai` jadi wajib di Edit Massal (selaras form); Nama & Lokasi 4 baris | **Siap commit** |
| W-3 | Konfirmasi perbaikan jadwal pakai modal aplikasi | `detail_project/static/detail_project/js/shared/timeline_repair.js` | `window.confirm` diganti `DP.core.modal.confirm` (tersedia global lewat `base.html`); bila modal tak ada → batal aman | **Siap commit** |
| W-4 | Komentar template Jadwal | `detail_project/templates/detail_project/kelola_tahapan_grid_modern.html` (2 hunk) | Dua blok komentar `{# #}` dihapus | **Siap commit** (kosmetik). Hunk lain di berkas ini sudah di-commit Claude |

Usulan pemisahan commit:
- (1) W-1 di `fix/list-pekerjaan-grow-tree`;
- (2) W-2 di `feat/mass-edit-tanggal-selesai-wajib`;
- (3) W-3 + W-4 di `fix/jadwal-repair-modal`.

Atau semuanya di atas `feat/tambahan-waktu-kerja`, sebelum merge.

**Perhatian:** `detail_project/views_api.py` juga memuat hunk Claude, yaitu penghapusan endpoint export lama (butir 9). Hunk-hunk itu sudah di-commit terpisah, sehingga sisa diff berkas ini hanya W-1.
