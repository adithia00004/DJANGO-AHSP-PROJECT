# Referensi API Endpoints

## Authentication

All endpoints require a logged-in user. Unauthorized requests will be redirected to the login page.

## Endpoints

### `GET /referensi/api/search`

Search AHSP referensi records for use with Select2 dropdowns.

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Optional search keyword (matched against `kode_ahsp` or `nama_ahsp`). |

**Response**

```json
{
  "results": [
    {"id": 12, "text": "01.01 - Pekerjaan Tanah"},
    {"id": 37, "text": "02.04 - Pekerjaan Beton"}
  ]
}
```

Results are limited by `REFERENSI_CONFIG["api"]["search_limit"]` (default 30).

### HTTP Status Codes

- `200 OK` – Success.
- `302 Found` – Redirect to login (user not authenticated).

### Notes

- Endpoint is optimized via query ordering and respects cached dropdown limits.
- `text` field follows the `"KODE - NAMA"` convention for Select2 compatibility.
