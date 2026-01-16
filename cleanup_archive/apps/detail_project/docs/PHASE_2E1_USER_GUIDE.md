# Phase 2E.1: User Guide - Planned vs Actual Progress

**Versi**: 1.0
**Tanggal**: 2025-11-26
**Status**: ✅ Production Ready

---

## Ringkasan Fitur

Fitur baru ini memungkinkan Anda untuk:
1. ✅ Memasukkan **Progress Perencanaan** (planned progress)
2. ✅ Memasukkan **Progress Realisasi** (actual progress)
3. ✅ Melihat kedua data secara terpisah melalui tab
4. ✅ Membandingkan rencana vs realisasi
5. ✅ Chart Kurva S menampilkan data sesuai mode yang aktif

---

## Tampilan UI Baru

### 1. Tab Progress Mode (Toolbar Atas)

Di toolbar atas, Anda akan melihat **2 tab baru** di samping Time Scale Selector:

```
┌─────────────┬──────────────┐
│ Perencanaan │   Realisasi  │  ← Tab baru!
└─────────────┴──────────────┘
    (biru)       (kuning)
```

**Tab Perencanaan** (Biru):
- Icon: 📅 Calendar Check
- Warna: Info (biru cerah)
- Fungsi: Mode input untuk progress yang **direncanakan**

**Tab Realisasi** (Kuning):
- Icon: 📋 Clipboard Data
- Warna: Warning (kuning/oranye)
- Fungsi: Mode input untuk progress yang **sudah terealisasi**

### 2. Mode Indicator Badge

Di sebelah judul halaman, ada **badge indicator** yang menunjukkan mode aktif:

```
Jadwal Pekerjaan (Modern)  [Mode: Perencanaan]  ← Badge biru
                                    atau
Jadwal Pekerjaan (Modern)  [Mode: Realisasi]    ← Badge kuning
```

Badge ini akan **otomatis berubah warna** saat Anda switch tab.

---

## Cara Menggunakan

### Skenario 1: Input Progress Perencanaan

**Langkah-langkah:**

1. **Buka halaman Jadwal Pekerjaan**
   - Akses: `/detail_project/<project_id>/jadwal-pekerjaan/`

2. **Pastikan tab "Perencanaan" aktif** (biru)
   - Default: Tab perencanaan sudah aktif saat pertama kali load
   - Badge indicator menunjukkan: `Mode: Perencanaan` (biru)

3. **Input persentase rencana progress**
   - Klik cell di grid untuk edit
   - Masukkan persentase (contoh: 25.5)
   - Cell akan berubah warna kuning (modified)

4. **Klik tombol "Save All"**
   - Data disimpan ke database field `planned_proportion`
   - Toast notification: "Data berhasil disimpan"
   - Cell kembali warna normal (saved)

5. **Kurva S chart menampilkan kurva perencanaan**
   - Garis menunjukkan progress yang direncanakan
   - Warna sesuai theme (default: biru untuk planned)

---

### Skenario 2: Input Progress Realisasi

**Langkah-langkah:**

1. **Klik tab "Realisasi"** (kuning)
   - Tab berubah warna aktif
   - Badge indicator berubah: `Mode: Realisasi` (kuning)
   - Toast notification: "Mode progress diubah ke Realisasi"

2. **Grid akan reload**
   - Menampilkan data actual progress
   - Jika belum ada data: semua cell bernilai 0%

3. **Input persentase realisasi progress**
   - Sama seperti input perencanaan
   - Klik cell → edit → masukkan persentase

4. **Klik tombol "Save All"**
   - Data disimpan ke database field `actual_proportion`
   - Toast notification: "Data berhasil disimpan"

5. **Kurva S chart menampilkan kurva realisasi**
   - Garis menunjukkan progress yang sudah terealisasi
   - Warna sesuai theme (default: oranye untuk actual)

---

### Skenario 3: Membandingkan Planned vs Actual

**Langkah-langkah:**

1. **Lihat data perencanaan**
   - Klik tab "Perencanaan"
   - Perhatikan nilai-nilai di grid
   - Lihat kurva di chart

2. **Switch ke data realisasi**
   - Klik tab "Realisasi"
   - Bandingkan nilai dengan rencana

3. **Identifikasi gap/variance**
   - Jika actual < planned → behind schedule ⚠️
   - Jika actual > planned → ahead of schedule ✅
   - Jika actual = planned → on schedule 👍

**Tips:** Buka 2 tab browser untuk melihat planned dan actual side-by-side!

---

## Fitur Validasi

### 1. Input Type Validation
- ✅ Hanya angka yang diterima
- ❌ Huruf, simbol, atau karakter lain ditolak

### 2. Range Validation
- ✅ Nilai 0 - 100 diterima
- ❌ Nilai negatif ditolak
- ❌ Nilai > 100 ditolak

### 3. Cumulative Validation
- ✅ Total per pekerjaan ≤ 100%
- ❌ Jika total > 100%, muncul error modal
- ⚠️ Harus adjust nilai sebelum bisa save

---

## Perbedaan Planned vs Actual

| Aspek | Perencanaan (Planned) | Realisasi (Actual) |
|-------|----------------------|-------------------|
| **Warna Tab** | Biru (Info) | Kuning (Warning) |
| **Icon** | 📅 Calendar | 📋 Clipboard |
| **Database Field** | `planned_proportion` | `actual_proportion` |
| **Kapan Diisi** | Awal proyek / planning phase | Selama eksekusi proyek |
| **Update Frequency** | Jarang (hanya saat replan) | Sering (weekly/daily) |
| **Total Constraint** | Harus = 100% | Bisa < 100% (work in progress) |

---

## FAQ (Frequently Asked Questions)

### Q1: Apakah data lama saya hilang setelah update ini?

**A:** Tidak! Semua data existing otomatis dimigrasikan ke field `planned_proportion`. Data Anda 100% aman.

### Q2: Bagaimana jika saya sudah input di mode Perencanaan, lalu switch ke Realisasi?

**A:** Data tersimpan terpisah. Saat switch ke Realisasi, Anda akan melihat data actual (default 0%). Data planned tidak berubah.

### Q3: Bisakah saya copy nilai dari Planned ke Actual?

**A:** Belum ada fitur auto-copy. Untuk saat ini, Anda perlu input manual di tab Realisasi. (Feature request untuk Phase 2E.2)

### Q4: Apakah Kurva S bisa menampilkan kedua kurva sekaligus?

**A:** Untuk versi ini, chart menampilkan satu kurva sesuai mode aktif. Fitur dual-curve bisa ditambahkan di Phase 2E.2.

### Q5: Bagaimana cara export data Planned dan Actual?

**A:** Export saat ini mengekspor data dari mode yang aktif. Untuk export keduanya, export sekali di mode Perencanaan, lalu sekali lagi di mode Realisasi.

### Q6: Apakah ada notifikasi jika actual progress behind schedule?

**A:** Belum ada untuk versi ini. Fitur variance analysis dan alerts bisa ditambahkan di Phase 2E.2.

---

## Keyboard Shortcuts

| Shortcut | Aksi |
|----------|------|
| `Tab` | Pindah ke cell berikutnya |
| `Shift + Tab` | Pindah ke cell sebelumnya |
| `Enter` | Edit cell / Simpan edit |
| `Esc` | Cancel edit |
| `Ctrl + S` | Save All (works di grid) |

---

## Tips & Best Practices

### ✅ DO:

1. **Input Planned dulu, baru Actual**
   - Rencanakan dulu semua progress di tab Perencanaan
   - Baru track realisasi di tab Realisasi

2. **Update Actual secara rutin**
   - Weekly atau daily sesuai kebutuhan
   - Jangan tunggu sampai akhir proyek

3. **Validasi total = 100%**
   - Pastikan total planned = 100% per pekerjaan
   - Actual boleh < 100% jika work in progress

4. **Save frequently**
   - Jangan input banyak sekaligus tanpa save
   - Save setiap beberapa row untuk avoid data loss

### ❌ DON'T:

1. **Jangan mix Planned dan Actual**
   - Jangan input actual di tab Perencanaan
   - Jangan input planned di tab Realisasi

2. **Jangan lupa switch tab**
   - Cek mode indicator badge sebelum input
   - Pastikan tab yang aktif sesuai data yang mau di-input

3. **Jangan input asal-asalan**
   - Data ini untuk monitoring dan reporting
   - Input yang akurat dan realistis

---

## Troubleshooting

### Masalah: Tab tidak muncul

**Solusi:**
1. Hard refresh browser: `Ctrl + Shift + R`
2. Clear browser cache
3. Pastikan sudah `npm run build` dan restart server

### Masalah: Data tidak ter-save

**Solusi:**
1. Cek console browser untuk error (F12 → Console tab)
2. Pastikan tidak ada validation error (total > 100%)
3. Cek koneksi internet
4. Pastikan sudah login

### Masalah: Badge tidak update saat switch tab

**Solusi:**
1. Refresh halaman
2. Cek JavaScript tidak ada error di console
3. Pastikan file `jadwal-kegiatan-B_nDeds9.js` ter-load

### Masalah: Chart tidak update

**Solusi:**
1. Tab Kurva S akan otomatis update setelah save
2. Jika tidak: klik refresh button di chart
3. Jika masih: hard refresh browser

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-26 | Initial release - Planned vs Actual tabs |

---

## Feedback & Support

Jika menemukan bug atau punya saran improvement:
1. 📧 Email ke development team
2. 💬 Report via internal chat
3. 📝 Create issue di project tracker

**Prioritas fitur Phase 2E.2:**
- [ ] Dual chart view (both curves simultaneously)
- [ ] Variance analysis column
- [ ] Export both datasets at once
- [ ] Copy planned to actual button
- [ ] Variance alerts & notifications

---

**Selamat menggunakan fitur baru! 🎉**

**Report Generated**: 2025-11-26
**Author**: Phase 2E.1 Team
**Status**: Production Ready
