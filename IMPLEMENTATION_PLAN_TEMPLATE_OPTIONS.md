# Rencana Implementasi: Opsi Harga Items dan Jadwal pada Template Pekerjaan

**Status:** Draft untuk review, belum diimplementasikan  
**Tanggal:** 2026-08-02  
**Area:** `detail_project` — List Pekerjaan / Template Library

## 1. Tujuan

Menambahkan pilihan saat user menekan **Simpan Sebagai Template**:

1. **Template standar** — perilakunya tetap seperti saat ini.
2. **Sertakan Harga Items** — template membawa master harga item dan nilai `harga_satuan`.
3. **Jadwal Pekerjaan** — dicatat sebagai ide lanjutan, belum masuk implementasi tahap pertama karena ketergantungan tanggal dan weekly schedule cukup kompleks.

Pilihan tambahan harus bersifat opt-in. Template lama dan template baru yang disimpan tanpa checkbox harus tetap dapat di-import dengan perilaku saat ini.

## 2. Temuan pada implementasi saat ini

### 2.1 Frontend

Handler Simpan Sebagai Template di `detail_project/static/detail_project/js/list_pekerjaan.js` hanya mengirim:

```json
{
  "name": "...",
  "description": "...",
  "category": "..."
}
```

Tidak ada flag untuk meminta export harga atau jadwal.

### 2.2 Backend export template

`api_create_template()` memanggil:

```python
_build_export_data(project, mode='template', template_meta=template_meta)
```

Pada mode `template` saat ini:

- hierarchy klasifikasi/sub/pekerjaan disimpan;
- detail AHSP dan koefisien disimpan;
- formula volume dan formula koefisien disimpan;
- `HargaItemProject.harga_satuan` tidak disimpan;
- `ItemConversionProfile` tidak disimpan;
- `VolumePekerjaan` tidak disimpan;
- `TahapPelaksanaan` tidak disimpan;
- `PekerjaanProgressWeekly` tidak disimpan.

Mode `full` sudah memiliki sebagian struktur harga dan jadwal, tetapi tidak boleh langsung disalin tanpa review karena template lintas-project membutuhkan pemetaan ID dan tanggal relatif.

### 2.3 Backend import template

`_import_template_data()` membuat atau mengambil `HargaItemProject` melalui `_upsert_harga_item()`. Fungsi tersebut hanya memperbarui metadata (`kode`, `uraian`, `satuan`, kategori) dan memang tidak mengubah `harga_satuan`.

Untuk jadwal, `PekerjaanProgressWeekly` adalah sumber data canonical. `PekerjaanTahapan` merupakan data turunan yang sebaiknya dibuat ulang melalui mekanisme sinkronisasi, bukan dianggap sebagai sumber utama.

## 3. Perilaku produk yang direkomendasikan

### 3.1 Modal

Pada tahap pertama, tambahkan checkbox pada `saveTemplateModal`:

```text
[ ] Sertakan Harga Items
```

Checkbox tidak dicentang secara default. Opsi Jadwal Pekerjaan tetap menjadi backlog dan tidak ditampilkan/diaktifkan pada tahap pertama.

Tambahkan teks bantuan singkat:

- Harga Items: menyertakan kode, uraian, satuan, kategori, harga satuan, dan profil konversi bila ada.

### 3.2 Template standar

Jika checkbox harga tidak dicentang:

- format konten tetap sama secara semantik;
- tidak ada harga dan jadwal yang disisipkan;
- import template lama tetap berjalan;
- tidak ada perubahan pada data project target selain hierarchy/detail/formula yang memang sudah di-import saat ini.

### 3.3 Harga Items

Jika opsi harga aktif, simpan section opsional berikut:

```json
{
  "harga_items": [
    {
      "kode_item": "BHN.001",
      "uraian": "Semen",
      "satuan": "zak",
      "kategori": "BHN",
      "harga_satuan": "75000.00"
    }
  ],
  "conversion_profiles": [
    {
      "harga_item_kode": "BHN.001",
      "market_unit": "zak",
      "market_price": "75000.00",
      "factor_to_base": "1",
      "density": null,
      "capacity_m3": null,
      "capacity_ton": null,
      "method": "direct"
    }
  ]
}
```

Referensi harga memakai `kode_item`, bukan primary key database sumber.

Saat import dengan opsi harga:

- item dibuat jika belum ada;
- metadata item diperbarui mengikuti template;
- `harga_satuan` hanya diisi jika nilai target masih `NULL`;
- profil konversi hanya dibuat jika target belum memilikinya;
- nilai harga tetap mengikuti aturan canonical server.

Rekomendasi UX: tampilkan ringkasan bahwa harga item dengan kode sama akan dipertahankan jika target sudah memiliki angka, dan hanya diisi jika target masih `NULL`.

### 3.4 Jadwal Pekerjaan — backlog

Fitur ini belum diimplementasikan pada tahap pertama. Ide desain yang disimpan:

```json
{
  "jadwal": {
    "tahapan": [],
    "progress_weekly": []
  }
}
```

Isi yang direkomendasikan:

- `TahapPelaksanaan`: nama, urutan, deskripsi, dan atribut auto-generation yang relevan;
- `PekerjaanProgressWeekly`: export reference pekerjaan, nomor minggu, planned proportion;
- tanggal minggu disimpan sebagai informasi relatif atau dihitung ulang dari tanggal mulai project tujuan;
- `PekerjaanTahapan` tidak dijadikan sumber utama karena merupakan projection/turunan dari weekly canonical storage.

`VolumePekerjaan` bukan jadwal secara teknis. Jika kelak template harus langsung menjadi template pekerjaan siap pakai, volume perlu dibahas sebagai opsi terpisah atau bagian dari paket jadwal.

Rekomendasi awal: sertakan volume bersama paket jadwal hanya jika definisi produk yang diinginkan adalah “template pekerjaan siap pakai”; jika tidak, jangan mencampurkan volume dengan jadwal.

### 3.5 Actual progress

Untuk template reusable, yang disalin sebaiknya hanya `planned_proportion`. `actual_proportion` dan `actual_cost` tidak disalin karena dapat membocorkan atau mencampur progres aktual project sumber ke project baru.

Jika bisnis memang membutuhkan snapshot progres aktual, itu harus menjadi pilihan terpisah dengan konfirmasi yang lebih kuat.

## 4. Rencana perubahan teknis

### Tahap A — Kontrak payload dan schema

1. Tambahkan flag frontend untuk tahap pertama:

   ```json
   {
     "include_harga_items": false
   }
   ```

2. Tambahkan metadata `template_options` pada konten template, misalnya:

   ```json
   {
     "include_harga_items": true
   }
   ```

3. Pertahankan `export_type: "project_template"`.
4. Naikkan versi format secara kompatibel, misalnya ke `3.1`, atau gunakan section opsional tanpa memaksa template lama melakukan migrasi.

### Tahap B — Export

1. Ubah signature `_build_export_data()` agar menerima opsi harga:

   ```python
   include_harga_items=False,
   ```

2. Pada mode template dan `include_harga_items=True`:

   - export master harga;
   - export harga satuan;
   - export conversion profile dengan referensi kode item;
   - tambahkan statistik jumlah harga dan conversion profile.

3. Jangan menyertakan section harga ketika flag false agar template standar tetap ringan dan kompatibel.

### Tahap C — Import

1. Baca section opsional secara defensif dengan default kosong.
2. Import hierarchy dan pekerjaan terlebih dahulu agar `pkj_map` tersedia.
3. Import/upsert harga setelah `HargaItemProject` dapat dipetakan berdasarkan kode.
4. Terapkan kebijakan **fill only empty** untuk harga/profil dan tampilkan ringkasan item yang diisi serta yang dipertahankan.
5. Gunakan transaksi atomic dan tetapkan apakah error kritis menyebabkan seluruh import dibatalkan atau hanya baris bermasalah yang dilewati.

### Tahap D — Frontend UX

1. Tambahkan checkbox dan help text di modal.
2. Kirim flag ke endpoint create template.
3. Tampilkan ringkasan opsi yang dipilih sebelum penyimpanan.
4. Pada import, tampilkan informasi apakah template berisi harga.
5. Tampilkan ringkasan item dengan kode sama yang dipertahankan karena target sudah memiliki harga/profil.
6. Setelah berhasil, tampilkan statistik tambahan:

   - jumlah harga item;
   - jumlah conversion profile.

### Tahap E — Test dan verifikasi

1. Unit test `_build_export_data()` untuk semua kombinasi checkbox.
2. Test import template lama tanpa section opsional.
3. Test harga baru, harga existing, kode sama dengan kategori berbeda, dan harga null/zero.
4. Test conversion profile dengan factor invalid atau item tidak ditemukan.
5. Test bahwa ID/reference pekerjaan hanya dipakai untuk mapping internal dan tidak diasumsikan sama antar-project.
6. Test rollback ketika import mengalami error kritis.
7. Jalankan:

   ```text
   python manage.py check
   python manage.py test detail_project
   node --check detail_project/static/detail_project/js/list_pekerjaan.js
   docker compose exec -T web python manage.py check
   ```

## 5. Ketentuan dan risiko yang perlu ditangani

| Risiko/ketentuan | Dampak | Mitigasi |
|---|---|---|
| Template lama tidak memiliki section baru | Import dapat gagal jika parser menganggap section wajib | Section opsional, default kosong, regression test template lama |
| Reference pekerjaan/tahapan salah dipetakan | Detail dapat terhubung ke pekerjaan yang keliru | Gunakan `_export_id` dan map ID pada tahap import |
| Tanggal absolut dari project sumber | Jadwal bergeser atau menjadi tidak relevan | Simpan referensi minggu/offset dan hitung ulang berdasarkan project target |
| Harga existing tertimpa | Data harga project tujuan berubah tanpa sengaja | Isi hanya ketika target `NULL`; pertahankan angka termasuk `0` |
| Kategori kode item berbeda | `_upsert_harga_item()` dapat menolak import | Preflight konflik kategori dan tampilkan error yang jelas |
| Conversion profile tidak konsisten dengan harga dasar | Harga market/base menjadi tidak sinkron | Simpan profile dan harga bersama dalam satu transaksi; harga base tetap dihitung server-side |
| Actual progress ikut tersalin pada fitur jadwal | Kebocoran data dan laporan target tidak valid | Fitur jadwal ditunda; bila diaktifkan kelak, default hanya planned schedule |
| `PekerjaanTahapan` dianggap sumber utama | Projection jadwal dapat konflik dengan weekly canonical | Import weekly canonical lalu regenerate projection |
| Project target tidak memiliki `tanggal_mulai` | Jadwal mingguan tidak dapat dihitung | Tolak opsi jadwal dengan pesan validasi atau minta tanggal mulai terlebih dahulu |
| Import berulang | Hierarchy dan jadwal dapat terduplikasi | Tampilkan kebijakan append/replace; minimal deteksi duplikasi dan beri peringatan |
| Error parsial saat import | Sebagian data masuk, sebagian gagal | Preflight validation dan transaction rollback untuk error kritis |
| Template publik berisi harga/progres | Informasi komersial atau operasional bocor | Template berharga/jadwal tetap private secara default; warning saat publish |
| Payload template menjadi besar | Response preview/import lebih lambat | Jangan mengirim section ketika tidak dipilih; batasi ukuran; gunakan query efisien |
| Perubahan harga belum tersimpan di database | Template menangkap nilai lama | Pastikan sumber export adalah data tersimpan; beri status/warning bila halaman masih dirty |
| Perbedaan konfigurasi minggu project | Jadwal tidak cocok dengan boundary project tujuan | Recalculate menggunakan konfigurasi minggu target dan dokumentasikan hasil |
| Format versi tidak jelas | Parser masa depan sulit membedakan payload | Tambahkan `template_options` dan versi format yang terdokumentasi |

## 6. Kriteria penerimaan tahap pertama

- Template standar tanpa checkbox menghasilkan perilaku yang sama seperti sebelum perubahan.
- Harga item hanya masuk ke template jika checkbox harga dipilih.
- Import template dengan harga dapat mengisi harga target yang masih `NULL`.
- Harga target yang sudah memiliki angka, termasuk `0`, tidak berubah.
- Profil konversi target yang sudah ada tidak berubah.
- Profil konversi dapat dibuat untuk item target yang belum memilikinya.
- Template lama tetap dapat di-import tanpa error.
- Konflik kode/kategori dan kegagalan validasi harga ditampilkan jelas.
- Tidak ada migrasi database wajib jika hanya memakai `PekerjaanTemplate.content` JSONField.
- Test Django, syntax JavaScript, dan pemeriksaan Docker berhasil.

## 7. Keputusan lanjutan yang belum masuk tahap pertama

1. Apakah **VolumePekerjaan** ikut dalam paket Jadwal, atau dibuat opsi terpisah?
2. Jika fitur Jadwal diaktifkan kelak, apakah hanya planned schedule atau actual progress juga diperlukan?
3. Apakah template yang menyertakan harga/jadwal boleh dipublikasikan, atau harus selalu private?
4. Saat import template yang sama dua kali, apakah perilakunya append seperti sekarang atau perlu replace/deduplication?

## 8. Keputusan hasil diskusi

### 8.1 Harga existing dan profil konversi

Kebijakan yang disepakati:

- Jika `HargaItemProject.harga_satuan` target masih `NULL`, import boleh mengisi nilai dari template.
- Jika target sudah memiliki angka, nilai target dipertahankan dan tidak dioverwrite.
- Angka `0` diperlakukan sebagai nilai yang sudah diinput, bukan sebagai kondisi kosong.
- Jika target belum memiliki `ItemConversionProfile`, profil dari template boleh dibuat.
- Jika target sudah memiliki `ItemConversionProfile`, seluruh nilai profil target dipertahankan.
- Jika item belum ada di target, item dan nilai harga/profil dari template boleh dibuat.
- Konflik kategori tetap menjadi error yang harus ditampilkan, bukan alasan untuk mengganti kategori existing.
- Jika hanya salah satu sisi (harga dasar atau profil) yang sudah ada, nilai yang akan diisi harus divalidasi terhadap sisi yang sudah ada. Jika hasilnya tidak konsisten, jangan mengisi otomatis dan laporkan konflik.

Dengan aturan ini, checkbox harga berfungsi sebagai **isi data yang kosong**, bukan overwrite massal. Implementasi perlu membedakan `NULL` dari `0` secara eksplisit; jangan menggunakan pemeriksaan truthy seperti `if not harga_satuan`.

Contoh konflik yang harus dilaporkan: target memiliki profil konversi aktif, tetapi `harga_satuan` masih `NULL`, sementara harga dari template tidak sama dengan hasil `market_price / factor_to_base`. Sistem tidak boleh mengisi secara diam-diam karena dapat menghasilkan harga dasar yang tidak sesuai dengan profil existing.

### 8.2 ID pekerjaan dan tahapan

Perbedaan ID antar-project bukan masalah; justru itu perilaku yang benar. ID database hanya berlaku di project masing-masing.

Yang wajib dilakukan adalah:

- export memakai reference internal seperti `_export_id` atau kode stabil;
- import membuat map dari reference template ke ID baru;
- semua detail yang menunjuk pekerjaan memakai map tersebut;
- test memastikan pekerjaan A tidak tertukar dengan pekerjaan B setelah import.

Jadi risiko yang perlu ditangani bukan “ID berbeda”, melainkan **kesalahan pemetaan reference saat import**.

### 8.3 Jadwal dan tanggal

Fitur jadwal ditunda sebagai ide/backlog. Tidak ada checkbox jadwal pada implementasi tahap pertama.

Alternatif desain untuk tahap lanjutan:

1. Hanya izinkan import jadwal jika tanggal mulai dan selesai project sumber sama persis dengan target; atau
2. Berikan pilihan agar sistem menyesuaikan tanggal awal/akhir target dan menghitung ulang seluruh minggu.

Pilihan kedua membutuhkan desain lebih lanjut karena menyentuh `TahapPelaksanaan`, `PekerjaanProgressWeekly`, konfigurasi batas minggu, volume, dan projection `PekerjaanTahapan`.
