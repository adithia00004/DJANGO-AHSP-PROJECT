# R5 Comprehensive UAT Execution

**Tanggal:** 21 Juni 2026
**Scope:** hasil implementasi Master Plan 27, tracker 28, audit page 09 dan 16-24,
serta WP Export pada dokumen 30.
**Tujuan:** membuktikan alur pengguna, integritas lintas-page, aksesibilitas dasar,
dan kesamaan web/backend/export setelah seluruh perbaikan R5.
**Di luar scope:** payment/subscription dan portal referensi. Gunakan UAT R4 untuk area itu.

## 1. Aturan Eksekusi

1. Jalankan kasus sesuai urutan. Kasus bertanda `BLOCKER` harus lulus sebelum melanjutkan.
2. Jangan memakai project produksi. Gunakan project UAT yang boleh dihapus.
3. Catat bukti minimal: screenshot, file export, serta console/network untuk kegagalan.
4. Jangan mengubah database manual selama journey utama. Kasus seed khusus ditandai jelas.
5. Setelah suatu langkah gagal, hentikan langkah yang dapat menimpa bukti/data kegagalan.
6. `PASS` berarti hasil aktual sama dengan expected. `PASS WITH NOTE` hanya untuk kosmetik.

Status kasus: `[ ] NOT RUN` · `[x] PASS` · `[!] FAIL` · `[-] N/A` · `[~] PASS WITH NOTE`.

## 2. Lingkungan dan Checkpoint

| ID | Pemeriksaan | Expected | Status/Bukti |
|---|---|---|---|
| ENV-01 | Pastikan branch/checkpoint implementasi R5 aktif dan worktree tercatat | SHA commit dicatat; tidak ada perubahan tak dikenal | [ ] |
| ENV-02 | `docker compose ps` | Web, DB, worker terkait berstatus healthy/running | [ ] |
| ENV-03 | Jalankan migrasi dan `manage.py check` di container | Tidak ada migration pending atau system-check issue | [ ] |
| ENV-04 | Buka login, dashboard, satu detail project | HTTP 200; tidak ada asset 404 | [ ] |
| ENV-05 | Buka DevTools Console + Network, disable cache | Tidak ada error JS baru; CSP report-only boleh dicatat terpisah | [ ] |
| ENV-06 | Siapkan browser normal dan incognito/clean profile | Keduanya dapat login dan membuka project UAT | [ ] |

**Checkpoint SHA:** `________________`
**Browser/versi:** `________________`
**Docker image/build:** `________________`

## 3. Data UAT

### 3.1 Project utama `UAT-R5-MAIN`

- Identitas: nama, lokasi, pemilik, sumber dana, tanggal mulai/selesai terisi.
- Struktur: 2 klasifikasi, minimal 2 sub-klasifikasi, minimal 5 pekerjaan.
- Dua pekerjaan sengaja memiliki **uraian sama tetapi kode/ID berbeda**.
- Mode: minimal satu REF, satu MOD, dan dua CUSTOM.
- CUSTOM A: item langsung Tenaga/Bahan/Alat + Biaya Lain.
- CUSTOM B: bundle AHSP referensi + bundle pekerjaan project.
- Volume: campuran manual, formula, nol eksplisit, dan satu belum diisi.
- Harga: campuran harga normal, nol eksplisit, dan satu NULL/belum diisi.
- Jadwal: minimal 6 minggu; planned dan actual berbeda; satu pekerjaan belum 100%.

### 3.2 Project pendukung

| Project | Kegunaan |
|---|---|
| `UAT-R5-EMPTY` | Empty state dan first-use journey |
| `UAT-R5-ZERO` | Semua harga nol; kurva/export tidak boleh NaN/division-by-zero |
| `UAT-R5-LARGE` | Payload besar, performa, export range, keepalive/autosave |
| `UAT-R5-LEGACY` | Data lama: raw AHSP ada, expanded belum ada; uji backfill/readiness |

## 4. Journey Utama Lintas-Page

Urutan ini penting karena List Pekerjaan adalah input utama dan page lain adalah consumer.

### 4.1 List Pekerjaan

| ID | Prioritas | Aksi | Expected | Status/Bukti |
|---|---|---|---|---|
| LP-01 | BLOCKER | Buat klasifikasi, sub, dan 3 pekerjaan; simpan | ID tersimpan; reload menampilkan struktur/urutan sama | [ ] |
| LP-02 | BLOCKER | Edit pekerjaan kedua setelah save pertama | Hanya pekerjaan kedua berubah; baris lain tidak tertimpa | [ ] |
| LP-03 | BLOCKER | Hapus pekerjaan CUSTOM yang punya volume/detail/jadwal, lalu tambah CUSTOM baru pada posisi sama | Pekerjaan baru tidak mewarisi volume, detail, formula, jadwal, atau BAC lama | [ ] |
| LP-04 | BLOCKER | Reorder, pindahkan sub, tambah baris, lalu simpan dua kali | Save kedua menarget baris yang sama; tidak ada baris hilang/kolaps | [ ] |
| LP-05 | HIGH | Gunakan dua pekerjaan dengan uraian sama; edit salah satunya | Sistem membedakan berdasarkan ID/kode; data tidak silang | [ ] |
| LP-06 | HIGH | Ganti REF/MOD/CUSTOM atau referensi pekerjaan yang telah memiliki data turunan | Preview menyebut pekerjaan dan jumlah Volume/Detail/Jadwal/Formula/BAC yang direset | [ ] |
| LP-07 | HIGH | Pada preview destruktif pilih Batal | Tidak ada perubahan atau data turunan terhapus | [ ] |
| LP-08 | HIGH | Ulangi perubahan lalu konfirmasi | Data turunan yang disebut benar-benar reset; page lain menampilkan status perlu diisi ulang | [ ] |
| LP-09 | MED | Buat perubahan belum disimpan lalu klik Export Template JSON | Sistem menyimpan dahulu atau membatalkan export; file tidak berisi state server lama | [ ] |
| LP-10 | MED | Simpan lalu hard refresh | Uraian/sumber/mode tetap sesuai pilihan terakhir; tidak ada nama mode lama tertinggal | [ ] |

**Cross-page setelah LP-08:** buka Volume, Template, Harga, Rincian, RAB, Jadwal, dan
Kebutuhan. Hanya pekerjaan yang benar yang boleh ditandai/reset.

### 4.2 Volume Pekerjaan

| ID | Prioritas | Aksi | Expected | Status/Bukti |
|---|---|---|---|---|
| VP-01 | BLOCKER | Ketik `1.500` pada volume manual dan simpan | Tersimpan sebagai 1500, bukan 1,5 atau 1.500.000 | [ ] |
| VP-02 | BLOCKER | Ketik `1,5`, lalu `0,123`, simpan dan reload | Tersimpan sebagai 1.5 dan 0.123; tidak terjadi salah 1000x | [ ] |
| VP-03 | BLOCKER | Edit digit terakhir lalu langsung klik Simpan | Ketikan terakhir ikut tersimpan; tombol kembali clean | [ ] |
| VP-04 | HIGH | Reload normal dan incognito | Nilai backend sama pada kedua browser; localStorage lama tidak mengalahkan server | [ ] |
| VP-05 | HIGH | Formula memakai base parameter dan computed parameter | Preview label/nilai benar; token valid tidak dianggap invalid | [ ] |
| VP-06 | HIGH | Masukkan token tidak ada dan buat siklus computed parameter | Save ditolak dengan pesan jelas; snapshot lama tetap utuh | [ ] |
| VP-07 | HIGH | Satu input invalid + beberapa baris valid dirty, lalu klik Simpan | Invalid ditandai; tidak ada sukses palsu/partial state | [ ] |
| VP-08 | HIGH | Ubah sumber pekerjaan di List lalu buka Volume | Hanya pekerjaan terdampak berlabel perlu isi ulang; jumlah banner sama dengan baris nyata | [ ] |
| VP-09 | MED | Project legacy: jalankan aksi sinkron/backfill yang disediakan | Expanded terbangun atomik; RAB tetap sama untuk item direct | [ ] |
| VP-10 | A11Y | Trigger validasi input | `aria-invalid=true`, pesan terkait input, fokus/label terbaca screen reader | [ ] |

### 4.3 Template AHSP

| ID | Prioritas | Aksi | Expected | Status/Bukti |
|---|---|---|---|---|
| TA-01 | BLOCKER | Simpan koefisien negatif | Ditolak UI/backend; data lama tetap | [ ] |
| TA-02 | BLOCKER | DevTools Slow 3G: pilih pekerjaan A lalu cepat pilih B | Respons A tidak melukis tabel B | [ ] |
| TA-03 | BLOCKER | Edit/simpan A lalu pindah B saat request berjalan | Save A tidak membersihkan dirty B dan tidak menulis komponen A ke B | [ ] |
| TA-04 | HIGH | CUSTOM: tambah item langsung, Biaya Lain, AHSP Referensi, dan Pekerjaan Project | Segmen item langsung dan bundle terpisah; masing-masing tersimpan sesuai tipe | [ ] |
| TA-05 | HIGH | Reset ke referensi pada pekerjaan yang punya dependent bundle | Konfirmasi muncul; reset dan cascade atomik; dependent tidak stale | [ ] |
| TA-06 | HIGH | Koreksi master referensi in-place | Banner `reference_update_available` muncul; detail sumber teridentifikasi | [ ] |
| TA-07 | HIGH | Klik Sinkronkan Referensi | Koefisien bundle user tetap; komponen sumber diperbarui; banner hilang | [ ] |
| TA-08 | HIGH | Alert ekspansi muncul | Detail menunjukkan pekerjaan, kode/baris, masalah, actual/expected, dan aksi | [ ] |
| TA-09 | HIGH | Simpan ulang/rebuild ekspansi | Alert hanya hilang setelah ekspansi benar; RAB tidak under/over-count | [ ] |
| TA-10 | A11Y | Navigasi tab/panel dan koef invalid dengan keyboard/screen reader | `aria-controls`, `tabpanel`, scope header, dan `aria-invalid` benar | [ ] |

### 4.4 Harga Items

| ID | Prioritas | Aksi | Expected | Status/Bukti |
|---|---|---|---|---|
| HI-01 | BLOCKER | Biarkan satu harga kosong dan set item lain `0` | Reload: kosong tetap NULL/belum diisi; nol tetap 0 eksplisit | [ ] |
| HI-02 | HIGH | Terapkan konversi satuan dan harga | Profil konversi + harga tersimpan atomik; Rincian/RAB memakai harga dasar benar | [ ] |
| HI-03 | HIGH | Override harga setelah konversi | Profil popup lama dihapus sesuai keputusan; harga override tersimpan | [ ] |
| HI-04 | HIGH | Bulk paste campuran valid/invalid | Tidak ada partial commit; error menunjuk item bermasalah | [ ] |
| HI-05 | MED | Kirim payload besar/klik save berulang cepat | Normal workflow tetap berhasil; rate/payload guard memberi pesan terkontrol | [ ] |

### 4.5 Rincian AHSP dan Rekap RAB

| ID | Prioritas | Aksi | Expected | Status/Bukti |
|---|---|---|---|---|
| RA-01 | BLOCKER | Bandingkan E/F/G dan markup default 10% | Nilai sama dengan service/RAB; override per-pekerjaan hanya memengaruhi target | [ ] |
| RA-02 | HIGH | Set dan reset markup override | Status override jelas; perubahan tercatat audit writer | [ ] |
| RA-03 | A11Y | Fokus baris bundle; tekan Enter dan Space | Bundle expand/collapse; `aria-expanded` berubah | [ ] |
| RR-01 | BLOCKER | Bandingkan subtotal, PPN, pembulatan, grand total dengan Rincian | Semua sama; filter/search tidak mengubah grand total project | [ ] |
| RR-02 | HIGH | Toggle Subtotal dan Compact | Visual berubah dan `aria-pressed` mengikuti status | [ ] |
| RR-03 | HIGH | Harga/volume belum siap | Warning/readiness menyebut penyebab; tidak fallback ke harga salah | [ ] |

### 4.6 Jadwal Pekerjaan

| ID | Prioritas | Aksi | Expected | Status/Bukti |
|---|---|---|---|---|
| JDW-01 | BLOCKER | Buka page dengan timeline valid | Tidak ada auto-regenerate/mutasi senyap saat load | [ ] |
| JDW-02 | BLOCKER | Edit planned/actual, ubah batas minggu sebelum save | Konfirmasi muncul sebelum perubahan batas; Batal mempertahankan edit | [ ] |
| JDW-03 | BLOCKER | Simpan mode aktif | Hanya mode aktif tersimpan; reload mempertahankan planned/actual | [ ] |
| JDW-04 | HIGH | Buat harga belum siap | Kurva tidak memakai bobot volume/rata-rata; tampil status bobot belum siap | [ ] |
| JDW-05 | HIGH | Planned dan actual berbeda | Grid, Kurva S layar, dan data tersimpan menunjukkan seri terpisah | [ ] |
| JDW-06 | HIGH | Paksa assignment API gagal (staging/proxy) | Page menampilkan error-state, bukan tabel kosong palsu | [ ] |
| JDW-07 | HIGH | Ubah tanggal awal/akhir project dari Dashboard | Timeline ditandai stale; update dilakukan lewat aksi terkontrol | [ ] |
| JDW-08 | DOC | Export Jadwal | Lokasi/nama/pemilik/tanggal project berasal dari identitas Dashboard | [ ] |

### 4.7 Rekap Kebutuhan

| ID | Prioritas | Aksi | Expected | Status/Bukti |
|---|---|---|---|---|
| RK-01 | BLOCKER | Buka total kebutuhan | Tampil Total Kebutuhan, Terjadwal, dan Belum Terjadwal | [ ] |
| RK-02 | BLOCKER | Filter W4-W8 | Hanya proporsi planned pada W4-W8 yang dihitung | [ ] |
| RK-03 | BLOCKER | Pekerjaan tanpa jadwal | Tidak dihitung penuh pada tiap periode; masuk Belum Terjadwal | [ ] |
| RK-04 | HIGH | Pilih mode Weekly lalu Periode 4 Minggu | Mode terpisah; label 4 minggu, bukan kalender bulan | [ ] |
| RK-05 | HIGH | Bandingkan total semua minggu + unscheduled | Sama persis dengan total kebutuhan item | [ ] |
| RK-06 | HIGH | Item harga NULL dan nol eksplisit | Status berbeda; angka mengikuti Harga Items SSOT | [ ] |
| RK-07 | ERROR | Simulasikan kegagalan endpoint | Pesan generik dan dapat dipahami; tidak ada traceback/`str(e)` | [ ] |

### 4.8 Dashboard

| ID | Prioritas | Aksi | Expected | Status/Bukti |
|---|---|---|---|---|
| DB-01 | HIGH | Ubah identitas project dan reload detail/export | Semua page/export membaca identitas terbaru | [ ] |
| DB-02 | HIGH | Quick search 1 karakter dan query penuh | Tidak ada TypeError; hasil/count benar | [ ] |
| DB-03 | HIGH | Mass edit tanggal mulai | Save atomik; progress/timeline direset sesuai konfirmasi | [ ] |
| DB-04 | MED | Light/dark + desktop/mobile | Status/badge konsisten; tidak ada kontrol terpotong | [ ] |

### 4.9 Canonical Readiness (menggantikan eksekusi terpisah dokumen 29)

Bagian ini mengadopsi seluruh tujuan UAT pilot WP-B4 pada dokumen 29 dan memperbaruinya
dari schema lama `b4.3` menjadi kontrak aktif `b4.5`. Dokumen 29 tetap disimpan sebagai
bukti historis pilot `missing_price`/`missing_volume`, tetapi tidak perlu dieksekusi ulang
secara terpisah bila seluruh kasus RD berikut dijalankan.

| ID | Prioritas | Aksi | Expected | Status/Bukti |
|---|---|---|---|---|
| RD-01 | BLOCKER | Buat pekerjaan A lengkap, B harga kosong/NULL, C tanpa VolumePekerjaan | Banner menunjukkan tepat item B sebagai `missing_price` dan C sebagai `missing_volume` | [ ] |
| RD-02 | BLOCKER | Set item lain harga `0` dan pekerjaan lain volume `0` eksplisit | Keduanya tidak dianggap missing; NULL/absen tetap berbeda dari nol | [ ] |
| RD-03 | HIGH | Buka Rekap RAB dan inspect response `/rekap/` | `readiness.schema_version=b4.5`; affected item/pekerjaan, source table/page, dan issue akurat | [ ] |
| RD-04 | HIGH | Buka Rincian, Template, Jadwal, dan Rekap Kebutuhan | Kelima consumer menampilkan verdict server yang sama; tidak ada kalkulasi hint paralel | [ ] |
| RD-05 | HIGH | Isi harga B dan volume C, lalu refresh semua consumer | Warning missing hilang; tidak muncul pesan “semua siap” palsu; total berubah sesuai data | [ ] |
| RD-06 | HIGH | Project direct/raw-only valid tanpa bundle dan tanpa expanded | Tidak muncul false-positive “sumber AHSP belum sinkron”; raw fallback dianggap valid | [ ] |
| RD-07 | BLOCKER | Project bundle legacy dengan expanded hilang/parsial | Banner menyebut pekerjaan, detail/baris, issue, actual/expected, dan lokasi perbaikan | [ ] |
| RD-08 | HIGH | Klik `Bangun ulang ekspansi` di Template | Hanya pekerjaan terdampak diproses; raw/koef user utuh; warning hilang setelah benar | [ ] |
| RD-09 | HIGH | Koreksi master referensi in-place | `reference_update_available` muncul pada 5 consumer; aksi sync hanya tersedia di Template | [ ] |
| RD-10 | HIGH | Jadwalkan pekerjaan 40%, jadwal tanpa volume, dan minggu di luar tanggal project | Tiga sinyal live tampil: incomplete allocation, allocation without volume, timeline stale | [ ] |
| RD-11 | HIGH | Perbaiki alokasi/volume/timeline | Sinyal terkait hilang; `pending_signals` kosong, bukan null/default yang disalahartikan | [ ] |
| RD-12 | SECURITY | Gunakan kode/uraian `<img src=x onerror=alert(1)>` pada item missing | Seluruh banner/detail menampilkan teks aman; tidak ada script/popup | [ ] |

## 5. UAT Export Resmi

### 5.1 Kontrak umum

| ID | Aksi | Expected | Status/Bukti |
|---|---|---|---|
| EX-01 | Export XLSX tiap report | File terbuka tanpa repair warning; nama `Project_YYYY-MM-DD` | [ ] |
| EX-02 | Klik sel uang/qty di Excel | Tipe numeric, dapat `SUM`, sort, filter; bukan string locale | [ ] |
| EX-03 | Periksa format | Uang 2 dp; qty kebutuhan/volume sesuai presisi kontrak | [ ] |
| EX-04 | Bandingkan web dengan XLSX/PDF/Word | Nilai resmi identik pada dataset/range yang sama | [ ] |
| EX-05 | Kosongkan metadata project | Export tetap diizinkan; placeholder `.` atau `-` sesuai kontrak | [ ] |
| EX-06 | PDF dengan tanda tangan dekat page break | Signature tidak berdiri sendiri; ikut minimal beberapa baris tabel | [ ] |
| EX-07 | Export range minggu parsial awal/akhir | Label/rentang benar; total tidak hilang/berlipat | [ ] |
| EX-08 | Paksa kegagalan export terkontrol | Pesan generik + correlation-ID; tidak ada traceback rahasia | [ ] |

### 5.2 Matriks per report

| ID | Report | Pemeriksaan khusus | Expected | Status |
|---|---|---|---|---|
| XR-01 | Rekap RAB | Sel harga/total + PPN/grand total | Numeric 2dp dan sama dengan web | [ ] |
| XR-02 | Harga Items | Item NULL vs nol | NULL=`-`; nol adalah angka 0.00 | [ ] |
| XR-03 | Rekap Kebutuhan | Qty/harga/total + unscheduled | Qty 3dp, uang 2dp, parity timeline | [ ] |
| XR-04 | Rincian AHSP | Sheet resmi | Tidak ada formula kalkulasi hidup | [ ] |
| XR-05 | Rincian AHSP | `Kontrol Kalkulasi` | Nilai Resmi/Kontrol/Selisih/Status; formula hanya di sheet kontrol | [ ] |
| XR-06 | Volume | Formula dan Volume | Formula teks audit; Volume = quantity backend numeric | [ ] |
| XR-07 | Volume | Base/computed parameter | Base numeric; computed Nilai=`-`, Expression berisi rumus teks | [ ] |
| XR-08 | Jadwal Professional | Input/Kurva/Cover | Tepat jumlah pekerjaan; hierarchy bukan pekerjaan; chart dua seri | [ ] |
| XR-09 | Jadwal Monthly | Data Master/Rincian/Kurva | Data Master dan Kurva nilai; Rincian hanya mirror satu-sel yang disetujui | [ ] |
| XR-10 | Jadwal Weekly | Data Master/Rincian | Planned parity; actual tetap di Data Master; tidak ada recompute formula | [ ] |
| XR-11 | Jadwal duplicate-name | Dua pekerjaan uraian sama | Harga/bobot/progress tidak tertukar; final planned/actual sama backend | [ ] |
| XR-12 | Jadwal zero-total | Semua harga nol | Bobot/kurva nol; tidak ada NaN/`#DIV/0!` | [ ] |

## 6. Race, Multi-Tab, dan Ketahanan

| ID | Aksi | Expected | Status/Bukti |
|---|---|---|---|
| RES-01 | Template Slow 3G + switch A/B berulang | Tidak ada stale paint/cross-job save | [ ] |
| RES-02 | Dua tab edit project sama | Last-save-wins; tidak ada partial write atau 409 stale-lock | [ ] |
| RES-03 | Putus jaringan saat save | UI tetap dirty/error; tidak menampilkan sukses palsu | [ ] |
| RES-04 | Reload saat ada dirty state | Warning sesuai page; backend data terakhir tetap utuh | [ ] |
| RES-05 | Project besar: save dan export range maksimal | Tidak timeout normal; error bila ada bersifat terkontrol | [ ] |
| RES-06 | Hard refresh seluruh page setelah save | Tampilan sama dengan backend; tidak ada cache/script basi | [ ] |

## 7. Aksesibilitas dan Visual

Jalankan minimal pada List, Volume, Template, Rincian, RAB, Jadwal, dan Kebutuhan.

| ID | Pemeriksaan | Expected | Status/Bukti |
|---|---|---|---|
| A11Y-01 | Keyboard-only: Tab/Shift+Tab/Enter/Space/Escape | Semua aksi utama dapat dijalankan; fokus terlihat | [ ] |
| A11Y-02 | Screen reader pada invalid input/toggle/tab/bundle | Label, error, state aktif/expanded diumumkan | [ ] |
| A11Y-03 | Zoom 200% desktop | Tidak ada aksi penting hilang/overlap horizontal tak terkendali | [ ] |
| A11Y-04 | Mobile viewport | Toolbar/modal/tabel-card dapat digunakan | [ ] |
| A11Y-05 | Light/dark | Kontras warning, badge, progress, input invalid terbaca | [ ] |
| A11Y-06 | Reduced motion | Tidak ada animasi wajib atau perubahan state yang hilang | [ ] |

## 8. Security dan Governance Smoke

| ID | Aksi | Expected | Status/Bukti |
|---|---|---|---|
| SEC-01 | Nama/uraian mengandung `<img onerror=...>` dan markup sederhana | Ditampilkan sebagai teks; tidak dieksekusi di Dashboard/List/RAB/Audit render terkait | [ ] |
| SEC-02 | Periksa response header | CSP Report-Only aktif; report sink menerima laporan | [ ] |
| SEC-03 | Endpoint write spam/payload melebihi limit pada environment UAT | 429/413 atau respons terkontrol; server tetap sehat | [ ] |
| SEC-04 | Akses project user lain | 404/forbidden; tidak bocor data/readiness/export | [ ] |

## 9. Regression Sweep dan Exit Criteria

### 9.1 Otomatis sebelum sign-off

| Gate | Expected | Status |
|---|---|---|
| Django full/targeted test sesuai CI | 0 fail | [ ] |
| Frontend Vitest | 0 fail selain skip terdaftar | [ ] |
| `manage.py check` + migration check | Bersih | [ ] |
| Export suite | 86/86 atau lebih, 0 fail | [ ] |
| Docker smoke + asset/network | Healthy, tidak ada asset 404 | [ ] |

### 9.2 Exit criteria

UAT dinyatakan **PASS** hanya bila:

- seluruh `BLOCKER` dan `HIGH` lulus;
- tidak ada data silang, partial-write, silent reset, atau perbedaan web-export;
- tidak ada traceback/internal exception pada respons user;
- seluruh temuan Medium/Low memiliki disposition dan owner;
- bukti export final disimpan bersama hasil UAT;
- checkpoint commit dan Docker image yang diuji tercatat.

## 10. Hasil dan Temuan

| ID Temuan | Kasus UAT | Severity | Expected | Aktual | Bukti | Disposition/Owner | Status |
|---|---|---|---|---|---|---|---|
| UAT-R5-001 | | | | | | | OPEN |

### Ringkasan Eksekusi

| Area | Pass | Fail | N/A | Catatan |
|---|---:|---:|---:|---|
| Environment | | | | |
| List Pekerjaan | | | | |
| Volume | | | | |
| Template AHSP | | | | |
| Harga/Rincian/RAB | | | | |
| Jadwal/Kebutuhan | | | | |
| Dashboard | | | | |
| Canonical Readiness | | | | |
| Export | | | | |
| A11y/Visual | | | | |
| Security/Resilience | | | | |

**Keputusan akhir:** `[ ] PASS` `[ ] PASS WITH CONDITIONS` `[ ] FAIL`
**Disetujui oleh:** `________________`
**Tanggal:** `________________`
