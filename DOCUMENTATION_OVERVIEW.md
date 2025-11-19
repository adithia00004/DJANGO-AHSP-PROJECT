# Dokumentasi Proyek - Indeks Utama

Gunakan indeks ini untuk menemukan dokumen yang relevan sekaligus memahami fungsi masing-masing folder. Seluruh jalur file ditulis relatif terhadap akar repository.

## A. Ringkasan & Tracking

| File | Fungsi |
| --- | --- |
| `JADWAL_KEGIATAN_README.md` | Ringkasan status terkini (milestone, command dasar, catatan testing). Cocok untuk onboarding cepat. |
| `PROJECT_ROADMAP.md` | Roadmap enam minggu beserta timeline fase dan instruksi testing. Update ketika ada pergeseran jadwal. |
| `IMPLEMENTATION_SUMMARY.md` | Executive summary pasca Phase 1 (metric utama & dampak). Gunakan untuk laporan stakeholder. |
| `PHASE_1_QUICKSTART.md` | Panduan 5-menit menyalakan stack (npm dev + Django). Ideal untuk dev baru. |
| `QUICK_PROGRESS_DASHBOARD.md` & `PROGRESS_REPORT.txt` | Laporan otomatis yang dihasilkan script `generate_progress_report.py`. Arsipkan sesuai sesi. |
| `PROGRESS_TRACKER.json` | Sumber data untuk dashboard/laporan otomatis. Jangan ubah manual tanpa update script. |

## B. Rencana Implementasi Jadwal Kegiatan

| File | Fungsi |
| --- | --- |
| `detail_project/docs/FINAL_IMPLEMENTATION_PLAN.md` | Rencana implementasi final (stack, fase, checklist). Referensi utama sebelum memulai fitur baru. |
| `detail_project/docs/PHASE_1_IMPLEMENTATION_GUIDE.md` | Langkah detail pengerjaan Phase 1 (perintah, struktur, CYA notes). Ikuti bila perlu mengulang fase. |
| `detail_project/docs/FREE_OPENSOURCE_RECOMMENDATIONS.md` | Daftar alternatif library gratis + alasan pemilihan. Berguna saat evaluasi lisensi. |
| `detail_project/docs/TECHNOLOGY_ALTERNATIVES_ANALYSIS.md` | Analisis mendalam tiap opsi teknologi (grid/gantt/export). Gunakan saat butuh pembanding teknis. |
| `detail_project/docs/JADWAL_KEGIATAN_DOCUMENTATION.md` | Dokumentasi teknis halaman Jadwal Kegiatan (arsitektur, API, troubleshooting). Rujukan utama Dev/QA. |
| `detail_project/docs/JADWAL_KEGIATAN_CLIENT_GUIDE.md` | Panduan khusus sisi client (entry Vite, modul JS, alur data, rencana AG Grid). |
| `detail_project/docs/JADWAL_KEGIATAN_IMPROVEMENT_PRIORITIES.md` | Daftar prioritas peningkatan + effort/impact matrix. Bahan planning backlog. |
| `detail_project/docs/README.md` | Ringkasan isi folder `detail_project/docs` (lihat file tersebut untuk deskripsi singkat per dokumen). |

## C. Referensi Modul Detail Project

| Folder | Fungsi |
| --- | --- |
| `Detail_project_docs_main/README.md` | Daftar dokumentasi modul List Pekerjaan, Volume Pekerjaan, Template AHSP, dan Harga Items. |
| `detail_project/RINCIAN_AHSP_DOCUMENTATION.md` | Referensi khusus halaman Rincian AHSP (arsitektur, API, testing). |
| `detail_project/REKAP_RAB_DOCUMENTATION.md` | Dokumentasi halaman Rekap RAB. |

## D. Dokumen Refactor Bundle Quantity

| File | Fungsi |
| --- | --- |
| `REFACTOR_PROGRESS_TRACKER.md` | Timeline & status refactor bundle quantity semantic. |
| `REFACTOR_ROADMAP_BUNDLE_QUANTITY_SEMANTIC.md` | Roadmap strategis refactor. |
| `MIGRATION_GUIDE_BUNDLE_QUANTITY.md` | Panduan menjalankan migrasi data. |
| `CHECK_BUNDLE_FIX.md`, `ISSUE_BUNDLE_KOEF_CHANGE.md`, `DIAGNOSE_*` | Catatan investigasi & verifikasi bug. |
| `DEPLOYMENT_PLAN_BUNDLE_QUANTITY.md`, `ROLLBACK_PLAN_BUNDLE_QUANTITY.md` | SOP deployment & rollback refactor. |

## E. Backup & Log Teknis

| File/Folder | Fungsi |
| --- | --- |
| `logs/` | Output test/regresi yang diarsipkan per fase. |
| `backup_pre_*.json` | Dump database sebelum migrasi/deploy tertentu. Simpan untuk rollback. |
| `generate_progress_report.py` | Script untuk membuat laporan otomatis (input: `PROGRESS_TRACKER.json`). |

> Tip: Saat menambahkan dokumen baru, update file ini serta README per-folder agar struktur tetap jelas.
