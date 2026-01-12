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

## Development Quick Start

- **Install dependencies:** `pip install -r requirements.txt`
- **Run tests + coverage:** `pytest` (fails if referensi app coverage < 80%)
- **Local permissions:** assign users to the new `Referensi Viewer`, `Editor`, or `Admin` groups (see `docs/PERMISSIONS.md`)
- **Audit history:** every AHSP & Rincian change is available via the Django admin “History” view (django-simple-history)
- **CI:** GitHub Actions workflow (`.github/workflows/ci.yml`) runs pytest on pushes and pull requests

## Browser Requirements

> ⚠️ **Minimum browser versions required due to CSS `color-mix()` usage**

| Browser | Minimum Version | Release Date |
|---------|-----------------|--------------|
| Chrome | 111+ | March 2023 |
| Firefox | 113+ | May 2023 |
| Safari | 16.4+ | March 2023 |
| Edge | 111+ | March 2023 |

**Note:** Internet Explorer is NOT supported.

## Production Deployment

```bash
# Environment variables
export DJANGO_SETTINGS_MODULE="config.settings.production"
export DJANGO_SECRET_KEY="your-production-secret-key"
export DJANGO_ALLOWED_HOSTS="yourdomain.com"
export SENTRY_DSN="your-sentry-dsn"  # Optional

# Deploy
python manage.py collectstatic --noinput
python manage.py migrate
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

See `docs/backup-guide.md` for database backup procedures.
