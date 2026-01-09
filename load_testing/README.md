# Load Testing Guide for DJANGO AHSP PROJECT

## Ringkasan

Load testing menggunakan **Locust** untuk mensimulasikan traffic pengguna concurrent dan mengukur performa aplikasi.

---

## Quick Start

### 1. Install Dependencies

```bash
cd "d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"
pip install -r requirements/development.txt
# atau install locust saja:
pip install locust
```

### 2. Jalankan Django Server

```bash
python manage.py runserver
```

### 3. Jalankan Locust (Web UI)

```bash
# Di terminal terpisah
locust -f load_testing/locustfile.py --host=http://localhost:8000
```

Buka browser: http://localhost:8089

### 4. Konfigurasi Test

| Level | Users | Spawn Rate | Durasi |
|-------|-------|------------|--------|
| Light | 10 | 2/s | 2 min |
| Medium | 50 | 5/s | 5 min |
| Heavy | 100 | 10/s | 5 min |
| Stress | 200 | 20/s | 10 min |

---

## Mode Headless (CLI)

```bash
# Test ringan - 10 users, 1 menit
locust -f load_testing/locustfile.py --headless -u 10 -r 2 -t 60s --host=http://localhost:8000

# Test medium - 50 users, 5 menit
locust -f load_testing/locustfile.py --headless -u 50 -r 5 -t 5m --host=http://localhost:8000 --csv=results/medium

# Test berat - 100 users, 5 menit
locust -f load_testing/locustfile.py --headless -u 100 -r 10 -t 5m --host=http://localhost:8000 --csv=results/heavy
```

---

## User Types

| Type | Weight | Behavior |
|------|--------|----------|
| **BrowsingUser** | 60% | Browsing halaman (dashboard, list, rekap) |
| **APIUser** | 30% | Panggilan API (tree, chart-data, rekap) |
| **HeavyUser** | 10% | Operasi berat (export PDF, Excel) |

---

## Endpoints yang Ditest

### 🔴 Critical (High Load)
- `/jadwal-pekerjaan/` - Gantt + Kurva S
- `/api/rekap/` - Agregasi RAB
- `/api/chart-data/` - Time-series data
- `/api/export/*/pdf/` - PDF generation

### 🟡 Medium
- `/api/list-pekerjaan/tree/` - Tree structure
- `/api/harga-items/list/` - Price list
- `/api/tahapan/` - Scheduling

### 🟢 Light
- `/dashboard/` - Dashboard
- Static pages

---

## Interpretasi Hasil

### Metrics Kunci

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Avg Response Time | < 200ms | 200-500ms | > 500ms |
| P95 Response Time | < 500ms | 500-1000ms | > 1000ms |
| P99 Response Time | < 1000ms | 1-2s | > 2s |
| Failure Rate | < 0.5% | 0.5-2% | > 2% |
| Requests/sec | Tergantung server | - | - |

### Output Report

Setelah test selesai, Anda akan mendapat:

```
LOAD TEST COMPLETED
============================================================
Total Requests: 5000
Total Failures: 12
Average Response Time: 180.45ms
P95 Response Time: 420.00ms
============================================================
```

---

## Troubleshooting

### Error: Connection Refused
- Pastikan Django server sudah running di port 8000
- Cek firewall tidak block koneksi

### Error: Too Many Open Files (Linux/Mac)
```bash
ulimit -n 10000
```

### High Failure Rate
1. Cek Django logs untuk error details
2. Periksa database connections
3. Cek memory usage server

---

## Tips Performa

1. **Gunakan database production** - SQLite lambat untuk concurrent access
2. **Enable caching** - Redis caching sangat membantu
3. **Gunakan Gunicorn/uWSGI** - Lebih baik dari runserver untuk load test
4. **Monitor resources** - CPU, Memory, DB connections

---

## File Reference

```
load_testing/
├── __init__.py           # Package init
├── locustfile.py         # Main test scenarios
├── benchmarks.py         # Performance benchmarks
├── setup_test_data.py    # Import test data from JSON
├── config.json           # Test configuration
├── run_load_test.bat     # Windows helper script
└── README.md             # This guide
```
