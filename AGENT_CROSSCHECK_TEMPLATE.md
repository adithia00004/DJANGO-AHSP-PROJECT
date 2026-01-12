# Agent Crosscheck Template
## Tujuan
Template ini dipakai oleh Codex (executor) dan Claude (reviewer) untuk saling
crosscheck progress, bukti pekerjaan, dan status roadmap secara konsisten.

## Single Source of Truth
- `MASTER_EXECUTION_TRACKER.md`
- `WEEKLY_REPORT_YYYY-MM-DD.md` (dibuat tiap akhir week)
- Opsional: `CHANGELOG.md` (jika digunakan untuk ringkasan release)

## Peran
- Codex: eksekusi task, update tracker, tulis bukti pekerjaan
- Claude: verifikasi bukti, cek konsistensi status, catat temuan

## Protokol Interaksi (Per Task)
1) Codex membuat/menentukan Task ID dan target deliverable.
2) Codex eksekusi dan update tracker + laporan mingguan.
3) Codex menulis bukti pekerjaan (files/tes/log).
4) Claude crosscheck bukti dan mengisi bagian review.
5) Jika ada gap, status diubah menjadi `Needs Rework`.

## Template Catatan Task
```
### Task ID: W1-D1-1.2
Status: Planned | In Progress | Done | Blocked | Needs Rework
Owner: Codex
Reviewer: Claude
Tanggal:

Ringkasan:
- Apa yang dikerjakan (1-3 bullet)

Perubahan:
- File(s): path, dan ringkas perubahan
- Konfigurasi: jika ada perubahan env atau infra

Perintah yang dijalankan:
- Command(s) penting (mis. migrate/test)

Hasil tes:
- Test suite / load test / manual test (jika ada)

Metrik dampak (opsional):
- P99 / error rate / throughput / cache hit

Bukti pekerjaan:
- Path file yang diubah
- Hash commit (jika ada)
- Log/hasil test (ringkas)

Risiko/Regresi:
- Catatan potensi masalah atau follow-up

Next step:
- Task lanjutan yang disarankan

Review (Claude):
- Verifikasi langkah:
- Hasil verifikasi:
- Verdict: Pass | Needs Rework
- Catatan:
```

## Template Laporan Mingguan
```
# Weekly Report YYYY-MM-DD
Week: W-<number>

Ringkasan Minggu Ini:
- Completed:
- In Progress:
- Blocked:

Perubahan Utama:
- File(s) penting:
- Perubahan konfigurasi:
- Migrasi DB (jika ada):

Tes dan Validasi:
- Test yang dijalankan:
- Hasil singkat:

Metrik:
- Baseline -> Current (jika relevan)

Risiko/Issue:
- Issue baru:
- Mitigasi:

Rencana Minggu Depan:
- Prioritas 1-3

Crosscheck (Claude):
- Status review:
- Temuan:
- Konfirmasi konsistensi tracker:
```

## Checklist Bukti Pekerjaan
- Ada path file yang diubah
- Ada ringkasan perubahan yang jelas
- Ada hasil test/log (jika dijalankan)
- Status di tracker konsisten dengan laporan mingguan

