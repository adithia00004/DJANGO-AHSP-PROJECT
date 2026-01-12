# Timeline Tenaga Kerja - Debug Guide

**Created:** 2025-12-03
**Issue:** Banyak item tenaga kerja tidak ditampilkan pada mode Timeline

---

## 1. Gejala Masalah

User melaporkan bahwa pada mode "Timeline", banyak item tenaga kerja (TK) yang tidak ditampilkan atau tidak sesuai dengan jumlah tenaga kerja yang sebenarnya ada.

## 2. Area yang Perlu Diperiksa

### 2.1 Frontend Filter

**File:** `detail_project/static/detail_project/js/rekap_kebutuhan.js`

**Lokasi Kode:**
- Line 350-352: Filter kategori
  ```javascript
  if (currentFilter.kategori.length && currentFilter.kategori.length < 4) {
    params.kategori = currentFilter.kategori.join(',');
  }
  ```

**Kemungkinan Masalah:**
- Jika checkbox kategori "TK" tidak tercentang, maka tenaga kerja tidak akan dimuat
- Periksa apakah default kategori di HTML sudah include TK (line 282 dalam `rekap_kebutuhan.html`)

**Cara Debug:**
1. Buka Chrome DevTools → Console
2. Ketik: `window.location.search` untuk melihat query params aktif
3. Periksa apakah `kategori=TK` ada dalam URL saat timeline dimuat
4. Cek `currentFilter.kategori` di console untuk melihat kategori yang aktif

### 2.2 Timeline Render Limit

**File:** `detail_project/static/detail_project/js/rekap_kebutuhan.js`

**Lokasi:** Line 610
```javascript
const limit = costChartMode === 'compact' ? 5 : null;
```

**Kemungkinan Masalah:**
- Jika `costChartMode = 'compact'`, hanya 5 item pertama yang ditampilkan per period
- Tenaga kerja mungkin tidak masuk dalam top 5 berdasarkan biaya

**Cara Debug:**
1. Periksa nilai `costChartMode` di console
2. Klik tombol "Tampilkan lengkap" pada Top Item card untuk toggle ke mode `full`
3. Periksa apakah item tenaga kerja muncul setelah di-toggle

**Fix Sementara:**
Ganti line 610 menjadi:
```javascript
const limit = null; // Always show all items for debugging
```

### 2.3 Backend Data Query

**File:** `detail_project/views_api.py` atau `detail_project/services.py`

**Endpoint yang Perlu Diperiksa:**
- Timeline endpoint (kemungkinan: `/api/project/<pid>/rekap-kebutuhan-timeline/`)
- Fungsi yang memproses timeline data (kemungkinan dalam `services.py`)

**Hal yang Perlu Diverifikasi:**
1. Query yang mengambil data timeline apakah sudah include kategori=TK
2. Filter `periode_mode`, `period_start`, `period_end` - apakah tenaga kerja ter-assign ke tahapan/jadwal yang benar
3. Apakah ada `LIMIT` atau pagination di query backend

**Debug Query Backend:**
```python
# Tambahkan logging di services.py untuk melihat query
import logging
logger = logging.getLogger(__name__)

def compute_timeline_data(project, filters):
    # ... existing code ...
    logger.debug(f"Timeline query filters: {filters}")
    logger.debug(f"Kategori filter: {filters.get('kategori', 'ALL')}")
    logger.debug(f"Total TK items found: {len([r for r in rows if r['kategori'] == 'TK'])}")
    # ... rest of code ...
```

### 2.4 Data Assignment di Database

**Table yang Perlu Diperiksa:**
- `DetailAHSPExpanded` - cek apakah tenaga kerja sudah ada dengan `kategori='TK'`
- `PekerjaanTahapan` - cek apakah pekerjaan yang menggunakan TK sudah di-assign ke tahapan
- `VolumePekerjaan` - cek volume pekerjaan untuk menghitung kuantitas TK

**SQL Debug Query:**
```sql
-- Cek total tenaga kerja per project
SELECT COUNT(*) as total_tk
FROM detail_project_detailahspexpanded
WHERE project_id = <project_id> AND kategori = 'TK';

-- Cek tenaga kerja dengan tahapan assignment
SELECT dah.kode, dah.uraian, pt.tahapan_id, pt.pekerjaan_id
FROM detail_project_detailahspexpanded dah
LEFT JOIN detail_project_pekerjaan p ON dah.pekerjaan_id = p.id
LEFT JOIN detail_project_pekerjaan_tahapan pt ON p.id = pt.pekerjaan_id
WHERE dah.project_id = <project_id> AND dah.kategori = 'TK';

-- Cek tenaga kerja yang tidak punya tahapan
SELECT dah.kode, dah.uraian, dah.pekerjaan_id
FROM detail_project_detailahspexpanded dah
LEFT JOIN detail_project_pekerjaan p ON dah.pekerjaan_id = p.id
LEFT JOIN detail_project_pekerjaan_tahapan pt ON p.id = pt.pekerjaan_id
WHERE dah.project_id = <project_id> AND dah.kategori = 'TK' AND pt.id IS NULL;
```

## 3. Langkah Debug Sistematis

### Step 1: Verifikasi Data di Snapshot Mode
1. Buka halaman Rekap Kebutuhan
2. Pastikan mode = "Snapshot" (bukan Timeline)
3. Set filter kategori = hanya TK
4. Catat jumlah item TK yang muncul (lihat badge di toolbar)

### Step 2: Bandingkan dengan Timeline Mode
1. Switch ke mode "Timeline"
2. Hitung total item TK di semua periode
3. Bandingkan dengan jumlah di Step 1

### Step 3: Analisis Periode
1. Untuk setiap periode di timeline, catat:
   - Nama periode (minggu/bulan)
   - Jumlah item total
   - Jumlah item TK (manual count jika perlu expand)
2. Identifikasi periode mana yang "missing" TK items

### Step 4: Debug Backend
1. Enable Django debug toolbar atau logging
2. Capture SQL query yang dijalankan saat load timeline
3. Run query manual di database dan lihat hasil
4. Periksa apakah filter periode mengeliminasi TK items

## 4. Kemungkinan Root Cause

### A. Filter Kategori Tidak Aktif
**Probabilitas:** ⭐⭐⭐ (Tinggi)
**Lokasi:** Frontend JavaScript
**Fix:** Pastikan checkbox TK tercentang default

### B. Cost Chart Mode = Compact
**Probabilitas:** ⭐⭐ (Medium)
**Lokasi:** Frontend JavaScript line 610
**Fix:** Toggle ke mode "full" atau ubah default

### C. Tenaga Kerja Tidak Punya Assignment Tahapan
**Probabilitas:** ⭐⭐⭐⭐ (Sangat Tinggi)
**Lokasi:** Database - PekerjaanTahapan table
**Fix:** Assign pekerjaan yang menggunakan TK ke tahapan/jadwal yang sesuai

### D. Backend Query Filter Terlalu Ketat
**Probabilitas:** ⭐⭐ (Medium)
**Lokasi:** Backend services.py
**Fix:** Review logic filter timeline untuk kategori TK

## 5. Quick Fix (Temporary)

Jika ingin quick fix untuk testing, edit `rekap_kebutuhan.js`:

```javascript
// Line 610 - BEFORE
const limit = costChartMode === 'compact' ? 5 : null;

// Line 610 - AFTER (show all items always)
const limit = null;
```

Dan tambahkan console logging:

```javascript
// After line 612 (dalam renderTimeline function)
const source = period.items || [];
console.log(`[DEBUG] Period ${period.label}:`, {
  total: source.length,
  TK: source.filter(i => i.kategori === 'TK').length,
  BHN: source.filter(i => i.kategori === 'BHN').length,
  ALT: source.filter(i => i.kategori === 'ALT').length,
});
```

Refresh halaman dan buka console untuk melihat breakdown per kategori.

## 6. Next Steps

1. **User action required:** Run debug steps di atas dan catat hasil
2. **Backend investigation:** Perlu akses ke `views_api.py` atau `services.py` untuk melihat timeline endpoint logic
3. **Database check:** Verifikasi PekerjaanTahapan assignments untuk items TK
4. **Report findings:** Share hasil debug untuk analisis lebih lanjut

---

**Note:** Masalah ini memerlukan investigasi lebih dalam pada backend dan database. Frontend fixes di atas hanya temporary workaround untuk debugging purposes.
