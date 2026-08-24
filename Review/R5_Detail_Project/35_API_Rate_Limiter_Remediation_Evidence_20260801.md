# 35 — Evidence Implementasi API Rate Limiter v2

**Tanggal:** 2026-08-01  
**Scope:** verifikasi lokal dan Docker setelah implementasi plan 34

## Hasil verifikasi

| Gate | Hasil |
|---|---|
| Backend limiter/governance/monitoring/API access | 28/28 test lulus |
| Frontend regression suite | 394 lulus, 25 skip |
| `manage.py check` + `makemigrations --check --dry-run` | lulus; tidak ada migration baru |
| Redis atomic smoke (sequential) | `[1, 2, 3]` |
| Redis atomic smoke (100 concurrent) | final `100`, 100 nilai unik |
| Process-level Redis smoke (8 proses independen) | count `1..8`, final `8` |
| Observe mode, limit 1/60 | request 1 dan 2 HTTP 200; `would_block` tercatat |
| Rollback mode `off` | dua request HTTP 200; counter tidak diberlakukan |
| Enforcement mode `v2`, limit 1/60 | request 1 HTTP 200; request 2 HTTP 429 dengan `Retry-After` |
| Production settings guard | lulus dengan Redis dan host/CSRF staging yang valid |

## Telemetry smoke terakhir

Counter global Redis saat verifikasi:

```text
allowed=4
blocked=2
would_block=1
near_limit=3
backend_error=0
```

Angka tersebut berasal dari smoke test sintetis, bukan traffic pengguna. Karena
itu angka kategori `write_interactive=60/60s` tetap harus dikalibrasi setelah
minimal tiga hari traffic staging/production yang representatif.

## Rollback runbook

1. Set `DETAIL_PROJECT_RATE_LIMIT_MODE=off` pada konfigurasi deployment.
2. Restart worker/web; jangan menghapus key v2 secara manual.
3. Validasi endpoint write dan observasi `backend_error`, 500, serta save failure.
4. Setelah perbaikan, aktifkan `observe`, review telemetry, lalu kembali ke `v2`.

Tidak ada migration atau perubahan data bisnis yang diperlukan untuk rollback.
