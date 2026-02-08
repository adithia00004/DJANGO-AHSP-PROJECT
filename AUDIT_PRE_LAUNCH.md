# LAPORAN AUDIT PRE-LAUNCH PRODUCTION
## Django AHSP Project
**Tanggal audit:** 2026-02-08
**Status dokumen:** Disesuaikan dengan kondisi codebase saat ini (verifikasi langsung file utama)

---

## RINGKASAN EKSEKUTIF

| Kategori | Status Saat Ini | Catatan |
|---|---|---|
| Keamanan aplikasi | CUKUP BAIK DENGAN GAP | Gap IDOR pada 4 endpoint API v2 chart/kurva/rekap sudah ditutup (2026-02-08); lanjut hardening endpoint `project_id` lain |
| Secret & credential hygiene | CLOSED (CORE) | `.env` sudah di-untrack, hardcoded credential dihapus, secret inti (`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`) sudah dirotasi dan diterapkan di `.env`, `.env.local`, `.env.production` (2026-02-08) |
| API hardening | CUKUP BAIK DENGAN GAP | `@csrf_exempt` pada endpoint export POST sudah dihapus (2026-02-08); lanjutkan audit endpoint POST lain |
| Data model & retensi | CLOSED (P1 CORE) | Strategi retensi sudah ditetapkan: hard-delete guard + proteksi relasi inti diterapkan (2026-02-08) |
| Performa | CLOSED (P1 CORE) | Hotspot utama N+1 di dashboard + export builder sudah dioptimasi (2026-02-08) |
| Deployment readiness | CUKUP BAIK DENGAN GAP | Docker/Gunicorn/health check ada, tetapi hardening production belum lengkap |

Catatan penting:
- Dokumen lama mengandung beberapa klaim overconfident yang perlu direvisi (contoh: "tidak ada IDOR", "semua endpoint terproteksi ownership check").
- Temuan di bawah ini berfokus pada hal yang terverifikasi langsung dari source saat ini.
- Topik `role/account/subscription` dipisahkan ke dokumen khusus: `AUDIT_ROLE_SUBSCRIPTION_FACILITY_TEST.md`.

---

## REVISI DARI DOKUMEN LAMA

1. Klaim "IDOR prevention: tidak ditemukan" tidak akurat.
Ada endpoint login-only yang mengambil `Project` tanpa filter owner.

2. Klaim "ownership check pada semua operasi project" tidak akurat.
Mayoritas endpoint sudah benar memakai `_owner_or_404`, tetapi tidak semuanya.

3. Klaim "default insecure key tidak dipakai di production" sudah diperketat (**CLOSED 2026-02-08**).
`config/settings/production.py` kini menolak `DJANGO_SECRET_KEY` yang kosong/default/insecure/terlalu pendek.

4. Klaim "cache backend default locmem harus redis" perlu dipresisikan.
`.env` saat ini sudah set `CACHE_BACKEND=redis`, tetapi fallback code masih memungkinkan turun ke `locmem` jika modul redis tidak tersedia.

---

## TEMUAN TERVERIFIKASI

### P0 - KRITIS (WAJIB SEBELUM LANJUT IMPLEMENTASI FITUR)

1. Potensi IDOR pada endpoint API v2 chart/kurva/rekap (**CLOSED 2026-02-08**)
- Endpoint yang sudah ditutup: `api_kurva_s_data`, `api_kurva_s_harga_data`, `api_rekap_kebutuhan_weekly`, `api_chart_data`.
- Implementasi: ownership check diseragamkan ke `_owner_or_404(project_id, request.user)`.
- File: `detail_project/views_api.py`.
- Verifikasi: `python manage.py test detail_project.tests_api_v2_access --keepdb --noinput` PASS (non-owner diblok 404 pada 4 endpoint).

2. Endpoint export POST masih `@csrf_exempt` (**CLOSED 2026-02-08**)
- Endpoint yang sudah ditutup: `export_init`, `export_upload_pages`, `export_finalize`, `api_start_export_async`.
- Implementasi: hapus seluruh decorator `@csrf_exempt`.
- File: `detail_project/views_export.py`.
- Verifikasi: `python manage.py test detail_project.tests_export_csrf --keepdb --noinput` PASS.

3. Secret/credential hygiene (update 2026-02-08, **CLOSED untuk core credential**)
- `.env` sudah tidak lagi ter-track (`git ls-files .env` -> kosong setelah `git rm --cached .env`).
- `cleanup_archive/root/load_testing/locustfile.py` sudah tidak menyimpan username/password hardcoded; sekarang wajib dari env var (`TEST_USER_POOL` atau `TEST_USERNAME`+`TEST_PASSWORD`).
- `DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD` sudah dirotasi dan diterapkan di `.env`, `.env.local`, `.env.production`.
- Nilai provider eksternal (`MIDTRANS_*`, `EMAIL_HOST_PASSWORD`, `SENTRY_DSN`) tetap dipisah: hanya diisi saat credential resmi provider tersedia.

### P1 - TINGGI (SEGERA SETELAH P0)

1. Data retention strategy untuk risiko `on_delete=CASCADE` (**CLOSED 2026-02-08**)
- Perubahan yang diterapkan:
  - `dashboard/models.py:12` -> `Project.owner` diubah ke `on_delete=PROTECT` agar hapus user tidak menghapus seluruh project.
  - `detail_project/models.py:554` -> `DetailAHSPAudit.pekerjaan` diubah ke `on_delete=SET_NULL` (nullable) agar audit trail tetap ada walau pekerjaan dihapus.
  - `dashboard/admin.py` -> hard delete Project dinonaktifkan (`has_delete_permission=False`), flow resmi tetap soft delete (`is_active=False`).
- Keputusan arsitektur:
  - Relasi turunan project-operasional (`Klasifikasi/SubKlasifikasi/Pekerjaan` dst.) tetap `CASCADE` untuk mendukung sinkronisasi data terkontrol.
  - Risiko accidental hard delete diturunkan melalui guard admin + kebijakan operasional soft delete.
- Verifikasi:
  - `python manage.py test dashboard.tests_data_retention detail_project.tests_data_retention --keepdb --noinput` PASS.

2. XSS risk di audit detail template (**CLOSED 2026-02-08**)
- `referensi/templates/referensi/audit/log_detail.html` sudah migrasi ke `json_script` (escaping aman) untuk metadata JSON.
- Regression test ditambahkan agar `{{ log.metadata|safe }}` tidak kembali.

3. Monitoring endpoint publik tanpa proteksi default (**CLOSED 2026-02-08**)
- `detail_project/views_monitoring.py` sekarang fail-closed: wajib `METRICS_API_KEY`, jika kosong endpoint nonaktif (`503`).
- Endpoint sekarang punya rate limit berbasis cache+IP (`METRICS_RATE_LIMIT`, `METRICS_RATE_WINDOW`) dan menolak abuse (`429`).
- Error response disanitasi (tanpa expose `str(e)` ke client).

4. N+1/performance hotspot (**CLOSED 2026-02-08**)
- `dashboard/views.py` (perhitungan progress dashboard) sudah dioptimasi: batch preload `Pekerjaan` lintas project + fallback `compute_rekap_for_project` hanya untuk project yang butuh.
- `dashboard/views_export.py` (export XLSX dashboard) sudah dioptimasi: pola batch yang sama, tidak lagi query `Pekerjaan` per project.
- `detail_project/views_api.py` (builder export) dioptimasi: `total_items` dihitung saat iterasi (tanpa pass kedua), mode template `HargaItemProject` pakai `values_list`, dan beberapa queryset berat dipersempit dengan `only(...)` untuk mengurangi overhead.

### P2 - SEDANG

1. Migrasi data irreversible
- `referensi/migrations/0004_alter_rincianreferensi_kategori_and_more.py:70`
- `referensi/migrations/0008_dedupe_ahsp_per_sumber.py:66`

2. `.gitignore` hygiene (**CLOSED 2026-02-08**)
- Duplikasi dan typo pattern sudah dirapikan.
- Pattern artefak dump/load testing lokal ditambahkan agar working tree tidak kotor.

3. Hardening production config (update 2026-02-08)
- Guard `SECRET_KEY` default/insecure sudah ditambahkan di `config/settings/production.py` (**CLOSED**).
- Fallback password lemah di `docker-compose.prod.yml` sudah dihapus (`POSTGRES_PASSWORD`, `REDIS_PASSWORD` wajib diisi) (**CLOSED**).
- Source map production sudah dinonaktifkan (`sourcemap` hanya aktif saat non-production) di `vite.config.js` (**CLOSED 2026-02-08**).

---

## KONDISI POSITIF YANG TERVERIFIKASI

- `config/settings/production.py:11` memaksa `DEBUG=False`.
- `config/settings/production.py:23`-`config/settings/production.py:24` menolak production tanpa `ALLOWED_HOSTS`.
- Middleware exception handler berada di posisi awal (`config/settings/base.py:71`).
- Docker multi-stage build, non-root user, health check, dan startup script sudah tersedia (`Dockerfile`, `docker-entrypoint.sh`).

---

## CHECKLIST PRIORITAS UPDATE

### P0 - Sebelum lanjut implementasi fitur baru
- [x] Tutup potensi IDOR: ganti semua `get_object_or_404(Project, id=project_id)` raw menjadi `_owner_or_404(...)` pada 4 endpoint v2.
- [x] Hapus `@csrf_exempt` pada endpoint export POST dan aktifkan validasi CSRF token yang benar.
- [x] Untrack `.env` dari git (`git rm --cached .env`) agar tidak ikut commit berikutnya.
- [x] Rotasi semua secret/password yang sempat tersimpan di `.env` lama (core credential lokal/repo).
- [x] Hapus hardcoded credential di `locustfile.py`, pindah ke env var wajib.

### P1 - Minggu pertama
- [x] Putuskan strategi retensi data untuk field `CASCADE` kritis (`PROTECT`/`SET_NULL`/soft delete).
- [x] Hardening endpoint monitoring client metric (wajib API key + rate limiting).
- [x] Perbaiki hotspot query tersisa pada builder export detail_project (optimasi dashboard + dashboard export sudah selesai 2026-02-08).
- [x] Ganti `log.metadata|safe` dengan rendering JSON tersanitasi.

### P2 - Minggu kedua
- [x] Rapikan `.gitignore` dan tambah pattern untuk artefak dump/load testing.
- [x] Tambah guard di `production.py` untuk menolak `SECRET_KEY` default/insecure.
- [x] Hapus fallback password lemah di `docker-compose.prod.yml` (`POSTGRES_PASSWORD`, `REDIS_PASSWORD`).
- [x] Nonaktifkan source map di production build jika tidak dibutuhkan.
- [x] Dokumentasikan prosedur rollback untuk migrasi data yang irreversible.

---

## AUDIT PER-PAGE & INTERAKSI ANTAR-PAGE (TAMBAHAN)

### A. Peta Page Utama yang Wajib Diaudit

| Area | URL Utama | Status Audit | Catatan |
|---|---|---|---|
| Landing | `/` | PERLU E2E | Entry point publik, validasi CTA utama ke area aplikasi |
| Dashboard | `/dashboard/` | SECURITY E2E CLOSED | Ownership dan akses non-owner sudah diuji; functional/business E2E tetap perlu |
| Project detail | `/dashboard/project/<id>/` | SECURITY E2E CLOSED | Direct URL non-owner terblokir, owner flow tervalidasi |
| Detail Project module | `/detail_project/<id>/*` | SECURITY E2E CLOSED | F1-F4 (ownership, export access, reset progress) tervalidasi via regression suite |
| Referensi admin | `/referensi/admin-portal/` + `/referensi/import/*` | SECURITY E2E CLOSED | Permission gate + sanitasi audit metadata sudah diuji |
| Monitoring | `/detail_project/monitoring/*` + API monitoring | HARDENING DASAR CLOSED | Endpoint client metric sudah fail-closed + API key wajib + rate limiting; lanjutkan observability tuning bila diperlukan |

### B. Catatan Audit Cepat Per-Page (Dari Kode Saat Ini)

1. Detail Project (API v2 chart/kurva/rekap) ownership check sudah ditutup (**CLOSED 2026-02-08**).
- Implementasi: `_owner_or_404(...)` pada 4 endpoint v2 kritis.
- Verifikasi: regression test non-owner untuk 4 endpoint PASS.

2. Export flow antar halaman (jadwal/detail -> export API) kini memakai CSRF gate Django normal (**CLOSED 2026-02-08**).
- Implementasi: `@csrf_exempt` di endpoint export POST dihapus.
- Verifikasi: regression test CSRF endpoint export init PASS.

### C. Matriks Interaksi Antar-Page (Wajib Uji Sebelum Launch)

| Flow | Skenario | Expected Result |
|---|---|---|
| F1 | User A buka URL project User B langsung | Harus 403/404 di page dan API (tanpa kebocoran data) |
| F2 | Dashboard -> Project Detail -> semua sub-page detail_project | State project konsisten, tidak cross-project |
| F3 | Edit data di detail_project -> reload -> kembali ke dashboard | Data tersimpan benar, ringkasan dashboard update |
| F4 | Trigger export dari page detail -> polling status -> download | Hanya owner bisa start/status/download export |
| F5 | Referensi import -> audit log detail | Metadata tampil aman (tanpa XSS) |

### D. Checklist Eksekusi Audit Per-Page

- [x] Siapkan 2 akun uji: `owner`, `non_owner`.
- [x] Jalankan F1-F5 dengan bukti hasil test/regression log.
- [x] Tambahkan negative test khusus IDOR untuk seluruh endpoint `project_id`.
- [x] Validasi redirect antar-page konsisten (request non-owner tetap terblokir, tidak pernah 200).
- [x] Validasi error state page/API (403/404/500) tidak mengekspos stack trace ke response client.
- [x] Update dokumen ini dengan hasil PASS/FAIL per flow.

### E. Hasil Audit Per-Page Security (PASS/FAIL)

| Flow | Hasil | Bukti |
|---|---|---|
| F1 | PASS | `detail_project.tests_page_security_audit::test_f1_non_owner_blocked_from_owner_pages` + `detail_project.tests_api_v2_access` |
| F2 | PASS | `detail_project.tests_page_security_audit::test_f2_owner_navigation_dashboard_to_detail_pages` |
| F3 | PASS | `detail_project.tests_page_security_audit::test_f3_owner_edit_in_detail_project_persists` |
| F4 | PASS | `detail_project.tests_page_security_audit::test_f4_non_owner_blocked_from_async_export_start`, `detail_project.tests_export_access`, `detail_project.tests_export_csrf` |
| F5 | PASS | `referensi.tests.test_import_permissions`, `referensi.tests.test_audit_template_security` |

Command verifikasi yang dijalankan:
- `python manage.py test detail_project.tests_page_security_audit detail_project.tests_api_v2_access detail_project.tests_export_csrf detail_project.tests_export_access referensi.tests.test_audit_template_security referensi.tests.test_import_permissions --keepdb --noinput` -> PASS (30 tests)
- `python manage.py check` -> PASS

---

## AUDIT APP DASHBOARD (LANJUTAN)

### Scope Audit Dashboard

- `dashboard/views.py`
- `dashboard/views_export.py`
- `dashboard/views_bulk.py`
- `dashboard/forms.py`
- `dashboard/templates/dashboard/dashboard.html`
- `dashboard/templates/dashboard/_project_stats_and_table.html`
- `dashboard/templates/dashboard/project_detail.html`

### Temuan Kritis (P0)

1. Flow copy project di halaman detail berpotensi rusak karena path API hardcoded tidak sesuai route aktif.
- `dashboard/templates/dashboard/project_detail.html:450`
- `dashboard/templates/dashboard/project_detail.html:687`
- Kode memanggil `/detail-project/api/...`, sementara route aktif app adalah `/detail_project/...`.

2. Redirect setelah deep copy mengarah ke path yang kemungkinan tidak valid.
- `dashboard/templates/dashboard/project_detail.html:608`
- Redirect menggunakan `/project/${data.new_project.id}/` (bukan route namespaced dashboard).

3. Filter export dashboard tidak sinkron dengan `ProjectFilterForm` saat ini.
- `dashboard/views_export.py:28` (`cleaned_data.get('q')` tidak ada di form)
- `dashboard/views_export.py:37` (`cleaned_data.get('tahun')` tidak ada di form)
- `dashboard/views_export.py:42` dan `dashboard/views_export.py:43` (`tanggal_from`/`tanggal_to` tidak ada di form)
- `dashboard/views_export.py:25` form dipanggil tanpa `user=...`, padahal pilihan dinamis tahun/sumber dana dibangun dari user.
- Dampak: export berpotensi tidak mengikuti filter dashboard aktual.

### Temuan Tinggi (P1)

1. Endpoint export CSV/PDF dashboard belum diproteksi `login_required`.
- `dashboard/views_export.py:245`
- `dashboard/views_export.py:249`
- Endpoint ini dipublish di `dashboard/urls.py`, tetapi tidak diberi decorator akses seperti endpoint export excel.

2. Endpoint mass edit bypass validasi form dan dapat menyimpan data tidak valid.
- `dashboard/views.py:694`-`dashboard/views.py:704` (field wajib dapat di-set string kosong)
- `dashboard/views.py:706`-`dashboard/views.py:710` (parse numeric gagal -> `pass`, tanpa error ke user)
- `dashboard/views.py:776`-`dashboard/views.py:777` (`project.save()` langsung tanpa `full_clean()`/form validation)

3. Endpoint mass edit mengekspose detail error internal ke response client.
- `dashboard/views.py:795`-`dashboard/views.py:798`
- Mengembalikan `str(e)` langsung pada status 500.

4. Hotspot performa (N+1) masih ada di render dashboard dan export.
- `dashboard/views.py:266`-`dashboard/views.py:274` (loop project + query/compute per project)
- `dashboard/views_export.py:125`-`dashboard/views_export.py:140` (loop project + query/compute per project)

### Temuan Sedang (P2)

1. Inline chart data memakai `mark_safe` + `|safe` (perlu hardening ke `json_script`).
- `dashboard/views.py:475`-`dashboard/views.py:477`
- `dashboard/templates/dashboard/dashboard.html:709`-`dashboard/templates/dashboard/dashboard.html:711`

2. Helper CSRF di template rawan error jika token field tidak ditemukan.
- `dashboard/templates/dashboard/_project_stats_and_table.html:695`-`dashboard/templates/dashboard/_project_stats_and_table.html:697`

3. Beberapa URL API masih hardcoded string, belum `url` template tag.
- `dashboard/templates/dashboard/_project_stats_and_table.html:270`
- `dashboard/templates/dashboard/_project_stats_and_table.html:437`
- Risiko maintainability tinggi saat path berubah.

4. Mismatch label kolom vs data yang ditampilkan.
- Header: `dashboard/templates/dashboard/_project_stats_and_table.html:216` (`Nama Owner`)
- Isi cell: `dashboard/templates/dashboard/_project_stats_and_table.html:339` (`project.nama_client`)

### Rekomendasi Eksekusi Audit Dashboard

1. Perbaiki semua path hardcoded copy/export menjadi route yang konsisten dengan `url` namespaced.
2. Satukan logika filter export dengan logika filter dashboard (reuse function/helper yang sama).
3. Tambahkan `@login_required` pada endpoint stub export agar konsisten policy akses.
4. Hardening mass edit:
   - Validasi server-side pakai `ProjectForm`/serializer.
   - Return error terstruktur per field, bukan silent `pass`.
   - Jangan expose `str(e)` langsung ke client.
5. Refactor perhitungan progress dashboard/export agar query tidak per-project.

---

## LOG PERUBAHAN IMPLEMENTASI (WAJIB UPDATE)

Aturan kerja:
- Setiap perubahan kode wajib ditulis di tabel ini pada hari yang sama.
- Tiap entry minimal memuat: area, ringkasan perubahan, file terdampak, status verifikasi.
- Sebelum lanjut task baru, cek apakah perubahan terakhir sudah tercatat.

| Tanggal | Area | Perubahan | File Terdampak | Verifikasi |
|---|---|---|---|---|
| 2026-02-08 | Dashboard P0 | Sinkronisasi filter export dengan `dashboard_view` (field filter + sort + active filter konsisten) | `dashboard/views_export.py` | `python manage.py check` PASS |
| 2026-02-08 | Dashboard P1 | Tambah proteksi `@login_required` untuk endpoint stub export CSV/PDF | `dashboard/views_export.py` | `python manage.py check` PASS |
| 2026-02-08 | Dashboard P0 | Perbaiki endpoint deep copy/batch copy dari path hardcoded ke URL namespaced | `dashboard/templates/dashboard/project_detail.html` | Uji statis path + `manage.py check` PASS |
| 2026-02-08 | Dashboard P0 | Perbaiki redirect hasil deep copy ke route detail dashboard yang valid | `dashboard/templates/dashboard/project_detail.html` | Uji statis redirect + `manage.py check` PASS |
| 2026-02-08 | Dashboard P2 | Ganti hardcoded URL export JSON project menjadi URL namespaced | `dashboard/templates/dashboard/_project_stats_and_table.html` | Uji statis template + `manage.py check` PASS |
| 2026-02-08 | Dashboard P2 | Ganti hardcoded URL import JSON + link hasil import menjadi URL namespaced | `dashboard/templates/dashboard/dashboard.html` | Uji statis template + `manage.py check` PASS |
| 2026-02-08 | Audit dokumen | Pisahkan seluruh pembahasan role/account/subscription ke dokumen khusus | `AUDIT_ROLE_SUBSCRIPTION_FACILITY_TEST.md`, `AUDIT_PRE_LAUNCH.md` | Review manual dokumen |
| 2026-02-08 | Role/Subscription P0 | Tutup gap kritis export tier + webhook idempotency (decorator aktif di endpoint export, download tier-protected, webhook duplicate-safe) dan tambah regression test | `detail_project/views_export.py`, `subscriptions/views.py`, `detail_project/tests_export_access.py`, `subscriptions/tests.py`, `AUDIT_ROLE_SUBSCRIPTION_FACILITY_TEST.md` | `python manage.py check` PASS; `python manage.py test subscriptions.tests detail_project.tests_export_access --keepdb --noinput` PASS |
| 2026-02-08 | Role/Subscription P0 | Hardening endpoint export legacy + dashboard export: terapkan tier policy untuk PDF/Word/XLSX/CSV/JSON dan professional dynamic format, plus regression test tambahan | `detail_project/views_api.py`, `dashboard/views_export.py`, `detail_project/tests_export_access.py`, `AUDIT_ROLE_SUBSCRIPTION_FACILITY_TEST.md`, `AUDIT_PRE_LAUNCH.md` | `python manage.py check` PASS; `python manage.py test subscriptions.tests detail_project.tests_export_access --keepdb --noinput` PASS |
| 2026-02-08 | Security P0 | Tutup gap IDOR API v2 (4 endpoint chart/kurva/rekap pakai `_owner_or_404`) + aktifkan CSRF default pada export POST (hapus `@csrf_exempt`) serta tambah regression test | `detail_project/views_api.py`, `detail_project/views_export.py`, `detail_project/tests_api_v2_access.py`, `detail_project/tests_export_csrf.py`, `AUDIT_PRE_LAUNCH.md` | `python manage.py check` PASS; `python manage.py test detail_project.tests_api_v2_access detail_project.tests_export_csrf --keepdb --noinput` PASS |
| 2026-02-08 | Role/Subscription Closeout | Tutup agenda role/subscription: policy engine entitlement terpusat + matrix data-driven (feature/plan entitlement), wiring middleware/mixins, dan negative test referensi/import tanpa permission | `subscriptions/models.py`, `subscriptions/entitlements.py`, `subscriptions/migrations/0002_subscriptionfeature_planfeatureentitlement.py`, `subscriptions/tests.py`, `accounts/models.py`, `accounts/middleware.py`, `accounts/mixins.py`, `referensi/tests/test_import_permissions.py`, `AUDIT_ROLE_SUBSCRIPTION_FACILITY_TEST.md` | `python manage.py check` PASS; `python manage.py test subscriptions.tests referensi.tests.test_import_permissions detail_project.tests_export_access accounts.tests --keepdb --noinput` PASS |
| 2026-02-08 | Security P0 | Secret hygiene remediation tahap 1: `.env` di-untrack dari git index dan credential hardcoded load testing dihapus (wajib env var) | `cleanup_archive/root/load_testing/locustfile.py`, `.env.example`, `AUDIT_PRE_LAUNCH.md` | `git ls-files .env` kosong; `python -m py_compile cleanup_archive/root/load_testing/locustfile.py` PASS |
| 2026-02-08 | Security Docs | Tambah indeks terpusat variabel sensitif (secret/password/token) lengkap dengan lokasi file+baris agar pencarian tidak terpisah | `ENV_SENSITIVE_VARIABLES_INDEX.md`, `AUDIT_PRE_LAUNCH.md` | Review manual referensi file+baris |
| 2026-02-08 | Security Docs | Tambah directory credential terstruktur + script lookup + template vault lokal agar rotasi secret/password bisa dari satu titik referensi | `SECRETS_DIRECTORY.json`, `scripts/find_secret_refs.ps1`, `SECRETS_LOCAL.template.md`, `.gitignore`, `ENV_SENSITIVE_VARIABLES_INDEX.md` | `powershell -ExecutionPolicy Bypass -File scripts/find_secret_refs.ps1` PASS; `powershell -ExecutionPolicy Bypass -File scripts/find_secret_refs.ps1 -Key DJANGO_SECRET_KEY` PASS |
| 2026-02-08 | Security Docs | Tambah file siap-isi untuk inventorisasi nilai secret/password lokal agar user tidak perlu pindah file saat audit/rotasi | `SECRETS_LOCAL.md`, `ENV_SENSITIVE_VARIABLES_INDEX.md`, `AUDIT_PRE_LAUNCH.md` | `git check-ignore -v SECRETS_LOCAL.md` PASS |
| 2026-02-08 | Security Docs (Simplifikasi) | Sederhanakan pendekatan penyimpanan secret ke satu file privat saja (`SECRETS_LOCAL.md`) dan hentikan penggunaan file helper tambahan | `SECRETS_LOCAL.md`, `.gitignore`, `AUDIT_PRE_LAUNCH.md` | Verifikasi manual: hanya `SECRETS_LOCAL.md` dipakai sebagai vault lokal |
| 2026-02-08 | Launch Ops Docs | Tambah checklist eksekusi pre-production terpisah (GO/NO-GO, smoke test, post-launch, rollback) agar siap dipakai saat launching | `PRE_PRODUCTION_LAUNCH_CHECKLIST.md`, `AUDIT_PRE_LAUNCH.md` | Review manual kelengkapan gate/checklist |
| 2026-02-08 | Security Docs | Generate usulan secret/password untuk review manual (belum diterapkan) dan simpan di file private review | `SECRETS_PROPOSED_REVIEW.md`, `.gitignore`, `AUDIT_PRE_LAUNCH.md` | Review manual nilai usulan + `git check-ignore -v SECRETS_PROPOSED_REVIEW.md` PASS |
| 2026-02-08 | Security Apply (Local) | Terapkan secret/password yang disetujui ke runtime lokal dengan nama variabel identik terhadap kode (`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_URL`, `CELERY_*`, `TEST_PASSWORD`) | `.env`, `.env.local`, `SECRETS_LOCAL.md`, `SECRETS_PROPOSED_REVIEW.md`, `AUDIT_PRE_LAUNCH.md` | `python manage.py check` PASS; verifikasi grep env key match code PASS |
| 2026-02-08 | Security Hardening P2 | Tutup hardening config produksi: tambah guard `SECRET_KEY` insecure/default di production settings dan jadikan `POSTGRES_PASSWORD`/`REDIS_PASSWORD` mandatory di compose prod (tanpa fallback lemah) | `config/settings/production.py`, `docker-compose.prod.yml`, `AUDIT_PRE_LAUNCH.md`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md` | `python manage.py check` PASS; `python manage.py check --settings=config.settings.production` fail expected untuk insecure key dan PASS untuk secure key |
| 2026-02-08 | Security Apply (Production Env) | Terapkan secret/password yang sudah disetujui ke `.env.production` dengan nama variabel identik terhadap kode (`DJANGO_SECRET_KEY`, `POSTGRES_PASSWORD`, `REDIS_PASSWORD`) dan update status review file | `.env.production`, `SECRETS_PROPOSED_REVIEW.md`, `AUDIT_PRE_LAUNCH.md` | `rg -n \"CHANGE-THIS|insecure-dev-key\" .env.production` bersih untuk key inti; `python manage.py check` PASS |
| 2026-02-08 | Security Closeout | Finalisasi closeout credential/secret: placeholder provider sensitif di `.env.production` dikosongkan, tambah key Midtrans explicit, dan validasi ulang `production settings` dengan env file production | `.env.production`, `SECRETS_LOCAL.md`, `SECRETS_PROPOSED_REVIEW.md`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md`, `AUDIT_PRE_LAUNCH.md` | `python manage.py check` PASS; `python manage.py check --settings=config.settings.production` PASS (env dari `.env.production`) |
| 2026-02-08 | Security P1 | Hardening endpoint monitoring client metrics: fail-closed API key, tambah rate limit IP, sanitasi error response, dan regression test | `detail_project/views_monitoring.py`, `detail_project/tests_monitoring_security.py`, `.env.example`, `.env.production`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md`, `AUDIT_PRE_LAUNCH.md` | `python manage.py test detail_project.tests_monitoring_security --noinput` PASS; `python manage.py check` PASS |
| 2026-02-08 | Security P1 | Sanitasi metadata audit detail template: ganti `|safe` ke `json_script` + parser aman di frontend, tambah regression test anti-regresi XSS | `referensi/templates/referensi/audit/log_detail.html`, `referensi/tests/test_audit_template_security.py`, `AUDIT_PRE_LAUNCH.md`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md` | `python manage.py test referensi.tests.test_audit_template_security --noinput` PASS; `python manage.py check` PASS |
| 2026-02-08 | Security P2 | Rapikan `.gitignore` (hapus duplikasi/typo + ignore artefak dump/load testing) dan nonaktifkan source map untuk production build Vite | `.gitignore`, `vite.config.js`, `AUDIT_PRE_LAUNCH.md` | `npm run build -- --mode production` PASS; `rg --files detail_project/static/detail_project/dist | rg "\\.map$"` kosong; `git check-ignore -v cleanup_archive/root/dump/xlsx/hasil_test_v10_phase4_stats.csv` PASS; `python manage.py check` PASS |
| 2026-02-08 | Launch Ops P2 | Dokumentasikan SOP rollback khusus migrasi irreversible (backup, restore, verifikasi) di checklist launch agar incident handling siap pakai | `PRE_PRODUCTION_LAUNCH_CHECKLIST.md`, `AUDIT_PRE_LAUNCH.md` | Review manual langkah rollback + command operasional |
| 2026-02-08 | Data Retention P1 | Terapkan strategi retensi CASCADE: `Project.owner` -> `PROTECT`, `DetailAHSPAudit.pekerjaan` -> `SET_NULL` (nullable), nonaktifkan hard delete Project di admin, dan tambah regression test | `dashboard/models.py`, `detail_project/models.py`, `dashboard/admin.py`, `dashboard/tests_data_retention.py`, `detail_project/tests_data_retention.py`, `dashboard/migrations/0014_alter_project_owner.py`, `detail_project/migrations/0036_alter_detailahspaudit_pekerjaan.py`, `AUDIT_PRE_LAUNCH.md`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md` | `python manage.py check` PASS; `python manage.py test dashboard.tests_data_retention detail_project.tests_data_retention --keepdb --noinput` PASS |
| 2026-02-08 | Performance P1 | Optimasi hotspot N+1 pada dashboard list dan export XLSX: preload `Pekerjaan` batch lintas project, hindari query per-project, dan jalankan fallback `compute_rekap_for_project` hanya pada project yang membutuhkan | `dashboard/views.py`, `dashboard/views_export.py`, `AUDIT_PRE_LAUNCH.md` | `python manage.py check` PASS; `python manage.py test dashboard.tests_data_retention --keepdb --noinput` PASS |
| 2026-02-08 | Performance P1 | Optimasi builder export detail_project: kurangi overhead query/object (`values_list` untuk template harga, `only(...)` pada queryset besar, hapus pass kedua untuk hitung total item) | `detail_project/views_api.py`, `AUDIT_PRE_LAUNCH.md` | `python manage.py check` PASS; `python manage.py test detail_project.tests_export_access detail_project.tests_export_csrf --keepdb --noinput` PASS |
| 2026-02-08 | Security E2E P0/P1 | Tutup audit per-page security: harden ownership check async export + v2 reset progress, validasi metadata `projectId` saat export init, tambah regression suite F1-F5 + static scan endpoint `project_id`, dan sinkronkan hasil PASS/FAIL di dokumen audit | `detail_project/views_export.py`, `detail_project/views_api_tahapan_v2.py`, `detail_project/tests_page_security_audit.py`, `AUDIT_PRE_LAUNCH.md` | `python manage.py test detail_project.tests_page_security_audit detail_project.tests_api_v2_access detail_project.tests_export_csrf detail_project.tests_export_access referensi.tests.test_audit_template_security referensi.tests.test_import_permissions --keepdb --noinput` PASS; `python manage.py check` PASS |
| 2026-02-08 | Launch Gate P0 | Verifikasi gate production settings/runtime: `DJANGO_ENV=production`, `check --settings production`, koneksi DB production, dan migrate production; sinkronkan status checklist launch | `PRE_PRODUCTION_LAUNCH_CHECKLIST.md`, `AUDIT_PRE_LAUNCH.md` | `DJANGO_ENV=production python manage.py check --settings=config.settings.production` PASS; `DJANGO_ENV=production python manage.py shell --settings=config.settings.production -c "SELECT 1"` PASS; `DJANGO_ENV=production python manage.py migrate --settings=config.settings.production --noinput` PASS |
| 2026-02-08 | Launch Gate Automation | Tambah automation gate `scripts/prelaunch_autocheck.py` untuk validasi env production final, check runtime production, DB/migration gate, security regression, dan functional smoke satu perintah | `scripts/prelaunch_autocheck.py`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md` | `python scripts/prelaunch_autocheck.py` -> PASS untuk runtime/tests; FAIL expected pada placeholder domain `.env.production` |
| 2026-02-08 | Launch Smoke Automation | Tambah regression smoke test flow inti (login/logout/signup baseline, dashboard, create/edit/delete project owner, non-owner access block) | `dashboard/tests_prelaunch_smoke.py`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md` | `python manage.py test dashboard.tests_prelaunch_smoke --keepdb --noinput` PASS |
| 2026-02-08 | Production Hardening | Tambah guard production untuk menolak host/origin placeholder/dev (`localhost`, `yourdomain.com`, non-HTTPS CSRF origin) agar tidak lolos ke production | `config/settings/production.py` | `python scripts/prelaunch_autocheck.py` memvalidasi fail bila placeholder masih ada |
| 2026-02-08 | Test Infrastructure | Stabilkan discovery `pytest` dengan `pytest.ini` (set `DJANGO_SETTINGS_MODULE`, batasi `testpaths` ke app aktif, exclude `cleanup_archive`) untuk menghindari false-error dari test arsip | `pytest.ini`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md` | `pytest -q` PASS (`79 passed, 1 warning`) |
| 2026-02-08 | Env Launch Candidate | Set domain kandidat launch `rabdashboard.com` pada `.env.production` (`ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, `SITE_URL`) dan pertahankan kompatibilitas localhost di `.env` (`CSRF_TRUSTED_ORIGINS`) | `.env.production`, `.env`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md` | `python manage.py check` PASS; `python scripts/prelaunch_autocheck.py` PASS |
| 2026-02-08 | Launch Ops Docs | Tambah dokumen kontrol khusus provider/pihak ketiga untuk domain, hosting, server, email, payment, dan bukti eksekusi agar alur non-kode tetap terkontrol | `AGENDA_PROVIDER_PIHAK_KETIGA.md`, `PRE_PRODUCTION_LAUNCH_CHECKLIST.md` | Review struktur agenda + tracker provider |
| 2026-02-08 | Launch Ops Docs | Tambah urutan purchasing pihak ketiga + rekomendasi vendor + baseline spesifikasi server untuk target launch awal agar keputusan procurement terstruktur | `AGENDA_PROVIDER_PIHAK_KETIGA.md` | Review section 8-10 + tracker update DOC-02 |
| 2026-02-08 | Production Safeguard | Tambah startup guard di entrypoint container agar deployment production fail-fast jika konfigurasi production tidak valid (validasi `check --settings=production` + assert `DEBUG=False`) | `docker-entrypoint.sh` | `python manage.py check` PASS; `python scripts/prelaunch_autocheck.py` PASS |

Checklist disiplin update:
- [ ] Tiap commit/patch baru sudah ditambahkan ke tabel log.
- [ ] Status verifikasi tiap perubahan sudah diisi (PASS/FAIL + metode).
- [ ] Jika ada rollback/perubahan arah, tambahkan entry koreksi (jangan hapus histori lama).

---

## CATATAN IMPLEMENTASI BERIKUTNYA

Urutan eksekusi yang disarankan:
1. Selesaikan semua P0.
2. Jalankan audit per-page + antar-page (F1-F6) sampai semua temuan P0/P1 tertutup.
3. Jalankan smoke test akses project lintas user (negative test IDOR).
4. Baru lanjut implementasi fitur berikutnya di branch terpisah.
