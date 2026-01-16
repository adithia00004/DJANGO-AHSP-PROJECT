# Manual Verification - Phase 4 (Bundle Quantity Semantic)
Tanggal: 2025-11-19 16:10 WIB
Penanggung jawab: Codex assistant (berdasarkan data aktual di DB dev)

## Langkah Verifikasi
1. Pastikan hasil migrasi terbaru sudah ter-load (perintah: `python manage.py migrate_bundle_quantity_semantic --all`).
2. Ambil seluruh `DetailAHSPProject` kategori LAIN yang memiliki referensi bundle (`ref_ahsp` != NULL).
3. Untuk setiap pekerjaan bundle:
   - Tarik seluruh `DetailAHSPExpanded` dengan `source_detail` ke bundle tersebut.
   - Hitung koefisien satuan (`per_unit_koef`) dan nilai per-unit (`per_unit_totals = koef x harga_satuan`).
   - Kalikan kembali dengan `koef` bundle guna mendapatkan ekspektasi kontribusi terhadap kategori TK/BHN/ALT.
   - Ambil hasil `compute_rekap_for_project(project)` dan cocokkan kolom `A/B/C` terhadap ekspektasi bundle.
4. Catat hasil ke tabel di bawah dan tandai deviasi (jika ada).

Script yang dipakai berada di catatan kerja: `python manage.py shell --command "exec(open('tmp_phase4_verify.py', encoding='utf-8-sig').read())"` dengan isi skrip yang menghitung ringkasan JSON (lihat output terlampir di prompt CLI).

## Hasil Sample (semua bundle yang ada di DB = 5 pekerjaan, 6 detail)
| Project | Project ID | Pekerjaan | Bundle Count | Expanded Rows | Bundle Koef | Per-unit Koef (TK/BHN/ALT) | Bundle Expected (TK/BHN/ALT) | Rekap (A/B/C) | Selisih |
|---------|------------|-----------|--------------|---------------|-------------|-----------------------------|-------------------------------|---------------|---------|
| Project template test 5 | 94 | CUST-0001 (Dinding Bata costum) | 2 | 14 | 10 + 10 | TK:1.1283 / BHN:91.316 / ALT:0 | TK:1,328,525 / BHN:1,217,205 / ALT:0 | TK:1,328,525 / BHN:1,217,205 / C:1,100,000* | TK/BHN: 0 ; ALT: N/A (bukan bundle) |
| Project template test 9 | 98 | mod.1-1.1.4.2 | 1 | 7 | 1 | TK:0.815 / BHN:0.418 / ALT:0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 |
| Project test 9 | 110 | CUST-0001 (Kustom 1) | 1 | 7 | 5 | TK:0.815 / BHN:0.418 / ALT:0 | TK:515,100 / BHN:658,500 / ALT:0 | TK:515,100 / BHN:658,500 / C:0 | 0 |
| Project test 9 | 110 | CUST-0002 (Kostum 2) | 1 | 7 | 10 | TK:0.815 / BHN:0.418 / ALT:0 | TK:1,030,200 / BHN:1,317,000 / ALT:0 | TK:1,030,200 / BHN:1,317,000 / C:0 | 0 |
| Project test 10 | 111 | CUST-0001 | 1 | 9 | 100 | TK:1.034 / BHN:1.3817 / ALT:0 | TK:12,672,000 / BHN:7,926,325 / ALT:0 | TK:12,672,000 / BHN:7,926,325 / C:0 | 0 |

*Keterangan*: Kolom ALT pada pekerjaan 94 memiliki nilai 1.100.000 karena ada detail ALT langsung (bukan hasil bundle). Kolom `bundle_expected` hanya memeriksa kontribusi LAIN->TK/BHN sehingga selisih ALT sengaja ditandai N/A.

## Observasi Tambahan
- Total bundle pekerjaan yang ada di database saat ini hanya 5 pekerjaan (4 project). Seluruhnya diverifikasi manual sehingga kriteria ">=10 sample" diadaptasi menjadi "100% bundle yang tersedia".
- Semua `DetailAHSPExpanded` menampung `koefisien` sesuai komponen per-unit (terlihat dari nilai TK/BHN yang jauh lebih kecil dibanding total rekap dan stabil saat koef bundle berubah).
- API/JS memakai output standar `jumlah = koef x harga`; pengujian ini memastikan rekap backend menambah kembali multiplier bundlenya.

## Kesimpulan
- Tidak ditemukan deviasi antara perhitungan manual dan `compute_rekap_for_project` untuk komponen TK/BHN hasil bundle.
- Phase 4 Task 4.5 dapat ditandai selesai; siap lanjut ke persiapan Phase 5 (test suite besar).
