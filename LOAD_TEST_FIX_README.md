# Load Test v4 - Analisis & Perbaikan

## 🔍 Masalah yang Ditemukan

### Hasil Test v4 (Sebelum Perbaikan)
- **Total Requests:** 172
- **Total Failures:** 129 (75% failure rate!)
- **Root Cause:** URL prefix salah

### Detail Masalah

Test v4 gagal karena **kesalahan URL prefix**:

❌ **Yang Digunakan di Test v4:**
```
/detail-project/api/project/{id}/...  (dengan DASH/hyphen)
```

✅ **Yang Benar (Django URL Pattern):**
```
/detail_project/api/project/{id}/...  (dengan UNDERSCORE)
```

### Bukti dari Django show_urls:
```
/detail_project/<int:project_id>/list-pekerjaan/
/detail_project/api/project/<int:project_id>/parameters/
/detail_project/api/v2/project/<int:project_id>/chart-data/
```

## 🔧 Perbaikan yang Dilakukan

### File: `load_testing/locustfile.py` (Baris 41)

**Sebelum:**
```python
DETAIL_PROJECT_PREFIX = os.getenv("DETAIL_PROJECT_PREFIX", "/detail-project")
```

**Sesudah:**
```python
DETAIL_PROJECT_PREFIX = os.getenv("DETAIL_PROJECT_PREFIX", "/detail_project")
```

### Perubahan Komentar:
```python
# Django uses /detail_project (underscore) - verified from show_urls output
```

## 📊 Endpoint yang Gagal di Test v4

Semua endpoint berikut gagal dengan HTTP 404 karena URL prefix salah:

| Endpoint | Failures | Penyebab |
|----------|----------|----------|
| `/api/project/[id]/list-pekerjaan/tree/` | 14 | Wrong prefix |
| `/detail-project/[id]/list-pekerjaan/` | 16 | Wrong prefix |
| `/detail-project/[id]/rekap-rab/` | 11 | Wrong prefix |
| `/api/project/[id]/harga-items/list/` | 9 | Wrong prefix |
| `/detail-project/[id]/jadwal-pekerjaan/` | 9 | Wrong prefix |
| `/detail-project/[id]/template-ahsp/` | 9 | Wrong prefix |
| `/api/v2/project/[id]/assignments/` | 8 | Wrong prefix |
| `/api/project/[id]/volume/formula-state/` | 7 | Wrong prefix |
| `/api/project/[id]/rekap/` | 7 | Wrong prefix |
| Dan 20+ endpoint lainnya... | 129 total | Wrong prefix |

## ✅ Endpoint yang Berhasil di Test v4

Hanya endpoint TANPA prefix detail_project yang berhasil:

| Endpoint | Success Rate | Response Time (Median) |
|----------|--------------|------------------------|
| `/accounts/login/` (GET) | 10/10 | 2100ms |
| `/accounts/login/` (POST) | 10/10 | 1200ms |
| `/dashboard/` | 22/22 | 230ms |
| `/api/project/[id]/detail-ahsp/[id]/` | 1/1 | 99ms |

## 🚀 Menjalankan Test Ulang

### Opsi 1: Menggunakan Script (Recommended)
```batch
run_loadtest_v5.bat
```

### Opsi 2: Manual Command
```batch
cd "d:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT"
locust -f load_testing/locustfile.py ^
    --headless ^
    -u 10 ^
    -r 2 ^
    -t 60s ^
    --host=http://localhost:8000 ^
    --csv=hasil_test_v5 ^
    --html=hasil_test_v5.html
```

### Prerequisites
1. Django server harus running:
   ```batch
   python manage.py runserver
   ```

2. Pastikan user test tersedia:
   - Username: `aditf96@gmail.com`
   - Password: `Ph@ntomk1d`

3. Pastikan project IDs exist di database:
   - Project IDs: [160, 161, 163, 139, 162]

## 📈 Expected Results (Test v5)

Dengan perbaikan ini, kita expect:

- ✅ Failure rate turun dari 75% ke < 5%
- ✅ Semua endpoint dengan prefix `/detail_project/` akan sukses
- ✅ Response time untuk API endpoints: 80-200ms (median)
- ✅ Response time untuk page views: 200-400ms (median)
- ✅ Login flow: 100% success

## 📝 Files Changed

1. **load_testing/locustfile.py**
   - Line 41: Fixed `DETAIL_PROJECT_PREFIX` dari `/detail-project` ke `/detail_project`
   - Added comment explaining the fix

2. **run_loadtest_v5.bat** (NEW)
   - Quick runner script untuk test v5
   - Includes clear instructions and configuration

3. **LOAD_TEST_FIX_README.md** (NEW)
   - Dokumentasi lengkap masalah dan solusi

## 🔄 Comparison v4 vs v5 (Expected)

| Metric | Test v4 (Broken) | Test v5 (Fixed) |
|--------|------------------|-----------------|
| Total Requests | 172 | ~172 |
| Failures | 129 (75%) | < 10 (< 5%) |
| Login Success | 100% | 100% |
| API Success | 0% | > 95% |
| Page View Success | 0% | > 95% |

## 🎯 Next Steps

Setelah test v5 selesai:

1. **Verify hasil:**
   ```batch
   type hasil_test_v5_failures.csv
   ```

2. **Compare metrics:**
   - Check failure rate < 5%
   - Check response times acceptable
   - Verify no 404 errors

3. **Jika masih ada error:**
   - Check project IDs exist: `[160, 161, 163, 139, 162]`
   - Verify user credentials valid
   - Check Django server running properly

4. **Performance tuning** (jika sudah zero errors):
   - Run dengan lebih banyak users (50-100)
   - Identify slow endpoints
   - Optimize database queries

## 📞 Troubleshooting

### Error: "Connection refused"
- Django server belum running
- Solution: `python manage.py runserver`

### Error: "Login failed"
- User credentials salah
- Solution: Verify username/password di locustfile.py

### Error: "404 Not Found"
- Check URL prefix di locustfile.py
- Verify dengan: `python manage.py show_urls | findstr detail`

### Error: "Project does not exist"
- Project IDs tidak ada di database
- Solution: Update `TEST_PROJECT_IDS` di locustfile.py

---

**Created:** 2026-01-10
**Author:** Claude (Load Test Analysis)
**Status:** Ready for testing
