# Implementation Plan: Release Candidate → Public Launch

**Tanggal:** 2026-06-10 11:30 WITA
**Branch:** `checkpoint/save-sync-plan-20260608` (HEAD `51c4a0ff`, pushed; CI berjalan dengan job backend Py3.11 + frontend)
**Sumber:** `AUDIT_KESIAPAN_LAUNCH_20260609.md` (F1-F14 + verifikasi review eksternal) dan `AUDIT_UI_UX_20260610.md` (U1-U15, M1-M12, Kontrak Feedback §10)
**SSOT tracking harian:** `CHECKLIST_PROGRESS_KESIAPAN_LAUNCH_20260609.md` — dokumen ini = peta fase & acceptance; centang progres di sini, rekam bukti di SSOT.
**Status kode saat plan dibuat:** *feature-complete; layak release candidate setelah gate R1-R5 ditutup.*

## Tracker Fase

| Fase | Scope | Status | Gate keluar |
|---|---|---|---|
| R0 | Baseline RC: semua fix audit ter-commit + pushed + CI | **DONE 2026-06-10** (commit `c5442a07`..`51c4a0ff`) | [~] CI remote HIJAU di HEAD (run pertama dengan job frontend — verifikasi di GitHub Actions) |
| R1 | Penutupan temuan kode pra-UAT (F10/F11/F14, M7/M9/M12) | **DONE 2026-06-10** | Suite + guard hijau ✓; tidak ada temuan severity ≥ Sedang yang open di kode ✓ |
| R2 | L5 — Deploy production nyata (domain/TLS/secrets) | TODO (scaffolding siap) | HTTPS aktif; `check --deploy` bersih; tanpa kredensial dev |
| R3 | L6 — Data safety (backup terjadwal + restore drill) | **DONE lingkup lokal 2026-06-10** (drill PASS + B2 closed); sisa = tugas VPS (PVD-07/09) | Restore drill PASS ✓; satu jalur DB ✓ |
| R4 | L7 — UAT browser + Midtrans sandbox + Opaque sign-off | TODO | UAT sign-off tertulis di SSOT |
| R5 | L8 — RC build + GO/NO-GO | TODO | Keputusan GO terdokumentasi |
| R6 | Pasca-launch (tidak memblokir) | BACKLOG | — |

Legenda: `[x]` selesai+bukti · `[~]` sebagian · `[ ]` belum · `[!]` blocker.

---

## R0 — Baseline RC (DONE 2026-06-10)

- [x] F9 expired-user payment + 2 regression test (`c5442a07`).
- [x] F1/F2 hardening compose prod; F3/F4 CI parity Py3.11 + job frontend + trigger `checkpoint/**` (`a115296d`, `51c4a0ff`).
- [x] U1/U2/U9/U14 + Kontrak Feedback §10 + 2 guard test (`a842cb14`).
- [x] Fix import full-backup raw-only (verifikasi independen, 3 regression test) (`38046135`).
- [x] SSOT launch tunggal; dokumen Feb di-SUPERSEDED.
- [x] Push ke origin.
- [~] **CI remote hijau di `51c4a0ff`** — cek GitHub Actions; bila merah, perbaiki sebelum R1.

## R1 — Penutupan Temuan Kode Pra-UAT (estimasi total: ~1 hari)

| Item | Temuan | Aksi | Effort | Status |
|---|---|---|---|---|
| R1.1 | **F10** export referensi login-only | **KEPUTUSAN PEMILIK 2026-06-10: (b) gate permission portal.** `ReferensiPortalRequiredMixin` pada 4 view export + gate `export_task_status` (yang ternyata TANPA auth — gap bonus tertutup) + 5 test `test_export_permissions.py` | keputusan + ~1 jam | [x] 2026-06-10 |
| R1.2 | **F11** `debug_clear_data` ter-route | Gate `settings.DEBUG` + superuser (404 di production) di atas permission existing | ~15 mnt | [x] 2026-06-10 |
| R1.3 | **F14** halaman `export-test` | Decorator `staff_only_page` diterapkan | ~15 mnt | [x] 2026-06-10 |
| R1.4 | **U15/M9** `rincian-rab` legacy | View → redirect permanen ke `rincian-ahsp`; 2 API diberi `@api_deprecated` (sunset 2026-09-01, telemetry pola tahapan v1) | ~30 mnt | [x] 2026-06-10 |
| R1.5 | **M7** gating Pro tak terlihat di UI export | `subscription_context` expose `export_pdf_allowed`/`export_excel_word_allowed`; partial baru `_export_menu_item.html` (terkunci = link `/pricing/` + gembok + badge Pro); dipasang di 4 halaman (rekap_rab, harga_items, volume, rincian_ahsp — JS existing null-safe); 3 test `tests_export_button_visibility.py`. Catatan: `_export_dropdown.html` lama = partial yatim (tidak pernah di-include) | ~½ hari | [x] 2026-06-10 |
| R1.6 | **U8/M12** `<noscript>` fallback anti-FOUC | `<noscript>` di `base.html` | ~5 mnt | [x] 2026-06-10 |

**Gate R1:** pytest + vitest + 2 guard hijau; F10 tercatat keputusannya di SSOT. → **Status gate: [x] LULUS 2026-06-10 12:25 WITA** — pytest 418 passed/40 skipped (+1 test sync-LED disesuaikan: kasus rincian_rab dihapus karena halaman kini redirect, re-run file 6 passed), vitest 235 passed/25 skipped (termasuk 2 guard).

## R2 — L5: Production Deploy Nyata (dependensi: provider)

Prasyarat eksternal (tracker: `AGENDA_PROVIDER_PIHAK_KETIGA.md` PVD-01..06):
- [ ] PVD-01 domain · [ ] PVD-02 DNS · [ ] PVD-03 VPS · [ ] PVD-04 hardening server · [ ] PVD-05 deploy stack · [ ] PVD-06 SSL.

Eksekusi (runbook: `RUNBOOK_DEPLOY_TLS_L5_L6.md`; compose sudah hardened-by-default):
- [ ] Isi `.env.production` dari `.env.production.example` — **SECRET_KEY BARU** (≠ nilai dev di `SECRETS_LOCAL.md`), `FLOWER_BASIC_AUTH`, ALLOWED_HOSTS/CSRF domain nyata.
- [ ] `docker compose -f docker-compose.prod.yml -f deploy/docker-compose.prod.proxy.yml up -d` dengan `DOMAIN=...`.
- [ ] `manage.py check --deploy` bersih; HTTPS + HSTS aktif; tidak ada `admin/admin`.
- [ ] Verifikasi port: hanya 80/443 reachable dari luar (db/web/flower loopback-only by default).

## R3 — L6: Data Safety

- [x] **Restore drill LULUS 2026-06-10 12:06 WITA** (dieksekusi pemilik): dump segar dibuat DARI DALAM container (pg_dump 15↔server 15; pg_dump 16 host sengaja dihindari — arsipnya berisiko tak terbaca pg_restore 15) → `backups/ahsp_sni_db_drill_20260610_120341.dump` 21 MB, SHA-256 `aed701c1...494bc` → restore ke scratch `restore_drill_20260610_120615` → verifikasi `projects|users|ahsp|plans = 159|80|5104|3` (MATCH baseline L0) → scratch dihapus, live tak tersentuh. (PVD-08 versi lokal ✓; ulangi di staging VPS saat R2.)
- [x] **Satu jalur DB — B2 CLOSED 2026-06-10 12:45 WITA**: akar masalah = PG16 native masih memenangkan `host:5432` (host pytest selama ini mendarat di PG16 — bukti `test_ahsp_sni_db` di sana). Keputusan pemilik: pindah port (PG16 juga melayani project lain). `postgresql.conf:64` → 5433, service di-restart pemilik (Administrator). **Verifikasi:** `host:5432` → PostgreSQL 15.15 Docker SSOT ✓; `host:5433` → PG16 (project lain) ✓; listener bersih tanpa tabrakan ✓; smoke pytest host vs PG15 → 30 passed ✓. Catatan: project lain (`govautomator` dll) kini konek via port 5433.
- [ ] Jadwalkan backup otomatis + retensi + lokasi terisolasi — ditangguhkan ke VPS (PVD-07); interim: dump manual pra-perubahan-besar (pola yang sudah berjalan).
- [ ] Restriksi akses DB internal-only di production (PVD-09 — tugas VPS).

## R4 — L7: UAT & Sign-off

**Browser UAT** (prioritas risiko frontend, checklist visual `AUDIT_UI_UX` §7 + M-checks):
- [ ] Volume Pekerjaan (formula/param opaque, editor modal bertumpuk M4)
- [ ] Jadwal Pekerjaan (grid/Gantt/Kurva-S, fullscreen M5-jadwal)
- [ ] Import 3-tier referensi (WYSIWYG, file AHSP 2026 nyata)
- [ ] Checkout Midtrans **sandbox** — termasuk skenario **user EXPIRED renewal** (regresi F9 di browser) + popup Snap (M10)
- [ ] Rekap Kebutuhan (chart echarts) + semua halaman lain sapu cepat
- [ ] Verifikasi visual M1/M2 (toast vs modal — fix sudah masuk, konfirmasi di browser), M3 (select2), dark mode M5
- [ ] Uji per-role: user biasa TIDAK melihat Orphan/Audit (U14); staff melihat

**Sign-off lain:**
- [ ] Opaque ID QA Gate D + monitoring window 7 hari (`opaque_daily_monitor.sh`) — sisa dari `OPAQUE_ID_CHECKLIST.md`
- [ ] (Opsional, dicatat sadar-risiko bila dilewati) Test M5 perf 100+ param & test R1 feature-flag off
- [ ] UAT sign-off tertulis di SSOT (siapa, kapan, hasil)

## R5 — L8: Release & GO/NO-GO

- [ ] Build RC image dari HEAD hijau; catat digest di SSOT.
- [ ] Rollback plan teruji: image sebelumnya + dump DB pre-launch (pola L0).
- [ ] Review blocker list SSOT = kosong untuk P0/P1.
- [ ] Keputusan GO/NO-GO terdokumentasi (tanggal, dasar, PIC).

## R6 — Backlog Pasca-Launch (tidak memblokir GO)

1. **M6**: migrasi 37 callsite `confirm()`/`alert()` → `DP.modal` per file (budget `feedback_governance_guard` hanya boleh turun); mulai `template_ahsp.js` (9).
2. **F5-F8**: `pg_isready -U $POSTGRES_USER`; hapus `git` dari runtime image; rename `.env.pgbouncer.example`; pantau 2 moderate npm production (uuid via exceljs — JANGAN `audit fix --force`).
3. **U3/U5/U6/U7/U10**: select2 `dropdownParent` + hapus hack; token-isasi z hardcode; migrasi generasi 9999/2xxx; self-host vendor CDN + SRI (selaras CSP); sapu dark-mode referensi/dashboard.
4. **Guard z-index CSS** (usul §6): test yang menolak z-index literal >100 di luar `core.css`.
5. **Roadmap arsitektur** (catatan 06:45): entitlement decorator per-view → pecah `views_api.py` → frontend Vite bertahap → konsolidasi 3 subsistem export.
6. Follow-up lama: tampilkan `sumber` AHSP di List Pekerjaan; backfill suffix `nama_ahsp==kode_ahsp`; hapus guard `ProgrammingError` opaque (D4) setelah semua env termigrasi.

---

## Aturan pemakaian dokumen ini

1. Setiap item selesai → centang di sini + tambah baris bukti di `CHECKLIST_PROGRESS_KESIAPAN_LAUNCH_20260609.md` (Record Eksekusi).
2. Urutan wajib: R0 → R1 → (R2 ∥ R3, boleh paralel setelah provider siap) → R4 → R5. R6 kapan pun setelah launch.
3. Temuan baru selama eksekusi → tambah ke dokumen audit ber-time-mark dulu, baru masuk fase di sini.
