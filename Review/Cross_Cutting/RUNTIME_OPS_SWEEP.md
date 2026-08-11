# Runtime & Ops Sweep — 2026-08-11

## Kenapa dokumen ini ada

Audit R1–R6 mencakup **lapisan aplikasi** secara menyeluruh: model, view, endpoint,
template, kontrol akses. Insiden `OperationalError: sorry, too many clients already`
pada 2026-08-11 memperlihatkan bahwa seluruh temuan hari itu berada di lapisan yang
**belum pernah diaudit**: proses, container, layering settings, dan konfigurasi
observability.

Aturan sapuan ini, dan alasannya:

1. **Ukur sistem berjalan, jangan baca kode.** Kebocoran 85 koneksi hanya terlihat di
   `pg_stat_activity`; 1212 restart hanya di `docker inspect`; polusi test hanya muncul
   saat suite dijalankan penuh. Audit gaya baca-kode melewatkan semuanya — empat kali.
2. **Temuan yang bisa jadi guard otomatis, jadikan guard.** Paragraf jadi basi; test
   berteriak sendiri.
3. **Dokumennya triase, bukan narasi.** Perbaiki sekarang / backlog / terima sadar.

Pengecualian yang paling tajam: bug middleware itu **terbaca di kode**, mekanismenya
bahkan tertulis sebagai komentar di `config/settings/test.py` — *"it breaks force_login
by using separate threads"*. Gejalanya dilihat, workaround dibuat, lalu jalan terus
selama tujuh bulan. Jadi celahnya bukan hanya cakupan, tapi **workaround yang diterima
tanpa ditanya "kenapa?"**.

## Hasil probe

| Probe | Perintah | Hasil 2026-08-11 |
|---|---|---|
| Koneksi DB | `SELECT count(*), state FROM pg_stat_activity GROUP BY state` | 4, datar setelah 120 request ✅ |
| Restart container | `docker inspect <c> --format '{{.RestartCount}}'` | `celery_beat` **1212**, sisanya 0 ⚠️ |
| Healthcheck | `docker inspect <c> --format '{{.State.Health.Status}}'` | `celery_beat` **none**, sisanya healthy ⚠️ |
| Migrasi tertunda | `manage.py showmigrations --plan \| grep '^\[ \]'` | 0 ✅ |
| Tabel terbesar | `pg_stat_user_tables ORDER BY pg_total_relation_size` | Silk 94 MB dari 217 MB ⚠️ |
| Tugas terjadwal | `docker logs ahsp_celery_beat` | Tidak ada yang pernah jalan ⚠️ |
| Divergensi settings | impor tiap modul settings, bandingkan MIDDLEWARE | Prod tidak kehilangan middleware ✅ |
| Dependency drift | paket yang dirujuk compose vs `requirements.txt` | 1 kasus: `django-celery-beat` ⚠️ |
| Suite penuh vs per-file | `pytest` penuh vs per file | Sudah ditutup (`20764342`) ✅ |

## Temuan & triase

| ID | Temuan | Bukti | Aksi |
|---|---|---|---|
| RT-01 | `celery_beat` crash-loop; semua tugas terjadwal (`config/celery.py:32`) tidak pernah berjalan | `RestartCount=1212`, `ModuleNotFoundError: django_celery_beat` | **Perbaiki** — buang flag `--scheduler` (nol dependency, nol migrasi) atau hentikan container |
| RT-02 | Healthcheck `celery_beat` dimatikan, sehingga crash-loop tak pernah terdeteksi | `healthcheck: disable: true` di compose; `State.Health = none` | **Perbaiki** — container yang rusak justru satu-satunya yang tak dipantau |
| RT-03 | Silk memakan 94 MB dan ~5 transaksi DB per request di dev | `silk_sqlquery` 54 MB/25197, `silk_response` 25 MB, `silk_request` 15 MB; 152 xact / 30 request | **Backlog** — turunkan `SILKY_INTERCEPT_PERCENT` atau nyalakan hanya saat profiling |
| RT-04 | Tidak ada memory limit di container mana pun | `HostConfig.Memory = 0` | **Terima** di dev; tetapkan di prod |
| RT-05 | `web` menjalankan gunicorn tanpa `--reload`; perubahan kode butuh `docker restart` manual | `CMD` di Dockerfile; tidak ada auto-reload | **Terima sadar** — dokumentasikan, atau aktifkan runserver bersama RT-06 |
| RT-06 | Tidak ada pelindung request menggantung di jalur `runserver` | `TimeoutMiddleware` dihapus (`53edafe7`); `--timeout` gunicorn tak berlaku di runserver | **Backlog** — wajib dikerjakan bersama jika RT-05 diaktifkan |

## Kandidat yang gugur setelah diverifikasi

Dicatat supaya tidak diselidiki ulang:

- **"Statistik planner kosong."** `pg_stat_user_tables` menunjukkan `n_live_tup = 0` dan
  `last_autoanalyze` NULL pada tabel 54 MB. Verifikasi: `pg_class.reltuples` = 275.285
  dan `pg_stats` punya 12 kolom berstatistik. Yang kosong hanya counter aktivitas
  (efek restore), bukan statistiknya. **Tidak ada aksi.**
- **"Audit log tak pernah dibersihkan membengkakkan DB."** `referensi_security_audit_log`
  = **0 baris / 424 kB**. Yang membengkak adalah Silk (RT-03). **Tidak ada aksi.**
- **"Memperbaiki beat akan menghapus setahun audit log."** Task `cleanup_audit_logs_task`
  menghapus log >90 hari, tapi tabelnya kosong; `send_audit_alerts_task` keluar lebih awal
  tanpa critical event dan dev memakai `console.EmailBackend`. **Risiko gugur.**
- **"Dependency drift adalah pola."** Dicek: `celery`, `flower`, `gunicorn`, `whitenoise`,
  `django-silk` semuanya cocok. **Kasus tunggal**, jangan dibesarkan.
- **"runserver akan memunculkan lagi kebocoran koneksi."** Django menutupnya sendiri —
  `ThreadedWSGIServer.close_request()` memanggil `connections.close_all()`
  (`django/core/servers/basehttp.py:105-111`). **Risiko gugur.**

## Guard yang sudah dipasang

Temuan yang sudah berubah dari paragraf menjadi test:

| Guard | Berkas | Menangkap |
|---|---|---|
| Paritas middleware test vs produksi | `dashboard/tests_middleware_parity.py` | Middleware disaring keluar dari test agar suite lulus |
| Larangan middleware men-spawn thread | `dashboard/tests_middleware_parity.py` | Kebocoran koneksi thread-local terulang |
| `idle_session_timeout` > `CONN_MAX_AGE` | `dashboard/tests_db_connection_guardrails.py` | Jaring pengaman berubah jadi sumber error acak |
| `CONN_HEALTH_CHECKS` menyala | `dashboard/tests_db_connection_guardrails.py` | Koneksi mati diserahkan ke request berikutnya |
| Isolasi cache antar-test | `conftest.py` | Counter limiter bocor lintas test (429 palsu) |

## Baseline merah yang diketahui

Per 2026-08-11 sesudah `20764342`: **`detail_project` 4 gagal / 604 lulus; app lain 243 lulus.**
Keempatnya nyata dan berada di area WIP — perlakukan sebagai baseline, bukan regresi baru:

1. `tests_rekap_calculation_contract` — anggaran query 30 > 15
2. `tests_wp_b4_readiness::test_query_budget_constant_no_n_plus_1` — 16 > 12
3. `tests_wp_b4_readiness::test_incomplete_planned_allocation_flags_partial_only` — `'60' != '60.00'`
4. `tests_formula_ui_regressions` — `scheduleAutoReloadPendingJobs` hilang dari `template_ahsp.js`

## Putaran berikutnya

Belum diprobe, kandidat sapuan kedua: kebijakan backup/restore (dump terakhir sebelum
hari ini dari Februari), rotasi log container, perilaku di bawah beban bersamaan
(4 sync worker), dan parity dev↔prod untuk Redis/cache.
