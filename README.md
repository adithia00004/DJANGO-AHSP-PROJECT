# DJANGO AHSP PROJECT

## Numeric SSOT (Angka & Desimal)

**Tujuan:** angka konsisten dari Excel → DB → API → UI.

- **Kanonik internal:** string numerik tanpa pemisah ribuan, **titik** sebagai desimal (contoh: `"26.406"`).
- **DB:** tipe `NUMERIC/DECIMAL` (bukan `float`/`text`) untuk koefisien, harga, volume, konversi, dsb.
- **API:** kirim & terima **string kanonik** (contoh `"26.406"`). *Tidak* ada format lokal di payload.
- **UI (tampilan):** pakai `Intl.NumberFormat('id-ID')` hanya untuk **display**.
- **UI (input):** parse input user (titik/koma) → normalisasi ke string kanonik sebelum kirim ke API.

**Contoh alir:**

| Excel      | DB (kanonik) | API JSON    | UI tampil  |
|------------|---------------|-------------|------------|
| `26,406`   | `26.406`      | `"26.406"`  | `26,406`   |
| `1.234,56` | `1234.56`     | `"1234.56"` | `1.234,56` |
