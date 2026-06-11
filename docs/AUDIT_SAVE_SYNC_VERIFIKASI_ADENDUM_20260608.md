# Verifikasi Adendum Audit Save/Sync

Tanggal verifikasi: 2026-06-08

Dokumen ini memverifikasi adendum S1-S7 pada `docs/AUDIT_SAVE_SYNC_PAGES_20260608.md` terhadap kondisi working tree dan runtime lokal.

## Ringkasan

Adendum user valid secara arsitektural dan selaras dengan kondisi kode. Satu koreksi sudah diterapkan ke laporan utama: cakupan S4 diperluas dari "Rekap RAB & Rincian RAB" menjadi "Rekap RAB, Rincian RAB, dan Rekap Kebutuhan".

Celah kritis yang masih terbuka adalah S2: HTML page dinamis belum mengirim `Cache-Control: no-store`. Selama S2 belum ditutup, bootstrap SSR pada Volume/Template/Harga tetap bisa menampilkan snapshot lama walaupun database sudah benar.

## Hasil Verifikasi S1-S7

| Kode | Status verifikasi | Catatan |
|---|---|---|
| S1 | Terkonfirmasi dan kembali disinkronkan | `WHITENOISE_AUTOREFRESH=True` aktif di development. Setelah perubahan autosave 5 menit, `staticfiles/detail_project/js/volume_pekerjaan.js` sempat masih memuat default `30000`; sudah dijalankan `python manage.py collectstatic --noinput` dan static root kini memuat `DEFAULT_AUTOSAVE_MS = 5 * 60 * 1000`. |
| S2 | Terkonfirmasi | Runtime `Django Client` untuk `list_pekerjaan`, `volume_pekerjaan`, `template_ahsp`, `harga_items`, `rincian_ahsp`, `rekap_rab`, `rincian_rab`, dan `jadwal_pekerjaan` semuanya mengembalikan `Cache-Control: None`. Jadi HTML page edit/output memang belum memakai `no-store`. |
| S3 | Terkonfirmasi | Bootstrap SSR aktif di Volume (`vp-bootstrap`), Template AHSP (`ta-bootstrap-detail`), dan Harga Items (`hi-bootstrap`). Karena S2 belum tertutup, kesegaran HTML menjadi dependency penting. |
| S4 | Terkonfirmasi dan diperluas | Selain Rekap RAB dan Rincian RAB, Rekap Kebutuhan juga output hilir tanpa Sync LED/context. Jadwal juga tetap masuk kelas masalah yang sama. |
| S5 | Terkonfirmasi | Template AHSP masih `watch="pekerjaan"` padahal menampilkan harga; Volume masih `watch="all"` sehingga rentan false alert dari perubahan yang tidak memengaruhi volume. |
| S6 | Terkonfirmasi | `base_detail.html` masih memuat `sync_indicator.js`, sementara partial `_sync_indicator.html` tidak dipakai halaman aktif; sistem aktif adalah `_sync_led.html`. |
| S7 | Terkonfirmasi sebagian | Volume dan Harga sudah punya konfirmasi saved rows/optimistic conflict; Template menolak save gagal. Rincian AHSP masih belum terlihat punya optimistic lock seperti Harga Items. |

## Bukti Runtime Cache-Control

Command:

```powershell
python manage.py shell -c "... print Cache-Control untuk halaman detail_project ..."
```

Hasil ringkas:

```text
PROJECT 195
list_pekerjaan (200, None)
volume_pekerjaan (200, None)
template_ahsp (200, None)
harga_items (200, None)
rincian_ahsp (200, None)
rekap_rab (200, None)
rincian_rab (200, None)
jadwal_pekerjaan (200, None)
```

## Bukti Static Root

Sebelum refresh static root:

```text
staticfiles/detail_project/js/volume_pekerjaan.js: const AUTOSAVE_MS = Number(root.dataset.autosaveMs || 30000);
detail_project/static/detail_project/js/volume_pekerjaan.js: const DEFAULT_AUTOSAVE_MS = 5 * 60 * 1000;
```

Command refresh:

```powershell
python manage.py collectstatic --noinput
```

Hasil:

```text
128 static files copied to 'D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\staticfiles', 218 unmodified.
```

Setelah refresh, `staticfiles/detail_project/js/volume_pekerjaan.js` sudah memuat:

```text
const DEFAULT_AUTOSAVE_MS = 5 * 60 * 1000;
```

## Celah Yang Masih Terbuka

1. S2 masih P0/P1: pasang `Cache-Control: no-store` pada page dinamis detail project.
2. S4/S5 masih membuka risiko tampilan output stale tanpa indikator.
3. S7 belum seragam untuk semua page, khususnya Rincian AHSP yang belum punya optimistic lock seperti Harga Items.
4. Import Validate Report masih punya false-success save UX dan belum ada `beforeunload` guard seperti temuan audit utama.

## Prioritas Rekomendasi

1. Terapkan `no-store` untuk HTML page edit/output di `detail_project`.
2. Tambahkan Sync LED/context pada Jadwal, Rekap RAB, Rincian RAB, dan Rekap Kebutuhan.
3. Koreksi watch: Template AHSP menjadi `pekerjaan,harga`; Volume menjadi `pekerjaan`.
4. Bersihkan `sync_indicator.js` legacy atau migrasikan penuh jika masih dibutuhkan.
5. Standarkan pola read-after-write untuk page yang masih commit baseline secara optimistik.
