# 34 — Implementation Plan Perbaikan API Rate Limiter

**Tanggal:** 2026-08-01  
**Sumber:** Audit 33 dan verifikasi ulang terhadap repository pada 2026-08-01  
**Status:** **IMPLEMENTASI SELESAI — SIAP UNTUK CANARY STAGING; KALIBRASI LIVE MASIH TERBUKA**  
**Prioritas:** P0 untuk fondasi limiter; P1 untuk kalibrasi endpoint dan UX 429

---

## 1. Tujuan

Memperbaiki rate limiter endpoint `detail_project` agar:

- benar-benar menghitung request dalam window waktu yang didefinisikan;
- aman terhadap request bersamaan pada deployment multi-worker;
- GET tidak menghabiskan kuota write;
- pekerjaan normal user tidak menghasilkan 429 palsu setelah sesi panjang;
- request otomatis atau script yang berlebihan tetap dibatasi;
- respons 429 memberi waktu retry yang benar dan tidak menghilangkan perubahan user;
- angka limit dapat dikalibrasi berdasarkan kategori workload, bukan angka ad-hoc.

Plan ini tidak sekadar menaikkan limit `20` menjadi `240`. Perbaikan algoritma
menjadi dependency wajib sebelum kalibrasi angka endpoint.

---

## 2. Baseline Terverifikasi

### 2.1 Inventaris

Terdapat 30 endpoint dengan decorator `@rate_limit`:

| Konfigurasi saat ini | Jumlah |
|---|---:|
| `category='write'` = 20/60 detik | 20 |
| eksplisit `240/60 detik` | 8 |
| `category='bulk'` = 5/300 detik | 2 |

### 2.2 Defect algoritma saat ini

Implementasi menggunakan urutan:

```python
current_count = cache.get(key, 0)
new_count = current_count + 1
cache.set(key, new_count, window)
```

Setiap `cache.set()` me-reset TTL ke window penuh. Counter baru hilang apabila
endpoint tidak menerima request sama sekali selama satu window. Ini bukan fixed
window, sliding window, atau token bucket yang valid.

Reproduksi baseline:

- request dikirim setiap 50 detik;
- hanya 21 request selama 1.000 detik;
- request ke-21 tetap diblokir oleh limit `20/60s`;
- tidak pernah terjadi 20 request dalam satu menit.

### 2.3 Defect concurrency

Operasi `cache.get()` lalu `cache.set()` tidak atomik. Dua worker dapat membaca
counter yang sama dan menulis nilai increment yang sama. Redis membuat cache
terpusat, tetapi tidak otomatis membuat rangkaian read-modify-write tersebut atomik.

### 2.4 Mixed-method endpoint

Lima view berikut melayani GET dan POST pada fungsi yang sama sehingga kedua method
berbagi counter:

- `api_project_pricing`;
- `api_project_parameters`;
- `api_project_computed_parameters`;
- `api_volume_formula_state`;
- `api_pekerjaan_pricing`.

### 2.5 Scope key

Key saat ini dibentuk per `user_id + endpoint`, tidak per project. Repository
mendukung satu user memiliki beberapa project. Plan ini sengaja mempertahankan
quota global per-user-per-endpoint agar pembuatan banyak project tidak menjadi cara
melewati abuse guard. `project_id` dicatat untuk observability, tetapi tidak menjadi
bagian key pada fase ini.

---

## 3. Keputusan Teknis yang Dikunci

### D-01 — Gunakan atomic fixed window sebagai implementasi v2

Gunakan bucket waktu absolut dan operasi atomic `cache.add()`/`cache.incr()`:

```text
bucket_start = floor(now / window) * window
reset_at     = bucket_start + window
key          = rate_limit:v2:<user>:<endpoint>:<method>:<bucket_start>

atomic increment
allow jika count <= limit
429 jika count > limit
```

Alasan memilih fixed window untuk fase ini:

- sederhana untuk diaudit dan diuji;
- menghilangkan TTL yang terus bergeser;
- `cache.add` dan `cache.incr` atomik pada Redis;
- dapat dijalankan pada LocMem untuk unit test/development;
- tidak membutuhkan database model atau migration;
- cukup untuk pola interaksi manusia pada aplikasi ini.

Token bucket dapat dipertimbangkan kemudian bila telemetry menunjukkan burst di
batas antar-window menjadi masalah. Token bucket bukan dependency untuk remediasi
ini.

### D-02 — Increment dilakukan sebelum view dieksekusi

Request yang menghasilkan validasi 400/413 tetap dihitung. Limiter adalah abuse
guard terhadap request masuk, bukan penghitung save yang sukses.

### D-03 — Fail-open bila backend limiter gagal

Exception cache pada limiter tidak boleh membuat user kehilangan kemampuan save.
Request diteruskan, tetapi error dicatat dengan level `ERROR` dan metric khusus.
Proteksi login, CSRF, body limit, validasi, dan transaksi tetap berlaku.

### D-04 — Production wajib memakai Redis

Atomicity lintas worker hanya dijamin pada backend Redis yang didukung deployment
production. Tambahkan deployment check yang memberi error konfigurasi apabila mode
production memakai limiter v2 tanpa Redis.

### D-05 — HTTP method menjadi bagian kontrak

Signature decorator ditambah parameter method:

```python
@rate_limit(category="write_interactive", methods=("POST",))
```

Request dengan method yang tidak terdaftar langsung diteruskan dan tidak menyentuh
counter kategori tersebut.

Untuk view GET/POST, gunakan limit terpisah:

```python
@rate_limit(category="read_interactive", methods=("GET",))
@rate_limit(category="write_interactive", methods=("POST",))
```

### D-06 — Key v2 tidak memakai `project_id`

Quota tetap per user, endpoint, dan method. Hal ini mempertahankan perlindungan
global per akun. Evaluasi secondary per-project quota hanya dilakukan bila telemetry
menunjukkan kebutuhan nyata.

### D-07 — Retry time harus berasal dari sisa bucket

Response 429 wajib memiliki:

- HTTP header `Retry-After` dengan detik tersisa sampai `reset_at`;
- `retry_after` yang sama dalam JSON;
- `limit`, `remaining=0`, dan `reset_at` dalam detail respons;
- pesan user berdasarkan sisa waktu nyata, bukan selalu "60 detik".

### D-08 — Dirty state dan draft tidak boleh dibersihkan saat 429

Template AHSP harus tetap `dirty`; pricing Rekap RAB tetap mempertahankan nilai
input/localStorage. Retry tidak boleh membuat save ganda atau pindah pekerjaan
sebelum save berhasil.

---

## 4. Kategori Target

Kategori awal berikut digunakan setelah algoritma v2 aktif:

| Kategori | Default awal | Penggunaan |
|---|---:|---|
| `bulk` | 5/300s | deep copy dan batch copy |
| `write` | 20/60s | aksi write yang jarang/eksplisit |
| `write_interactive` | 60/60s | save manual yang wajar dilakukan berulang |
| `sync_frequent` | 240/60s | endpoint sync/autosave yang saat ini sudah 240 |
| `read` | 100/60s | pembacaan biasa bila limiter read diaktifkan |
| `read_interactive` | 240/60s | GET polling atau panel interaktif mixed-method |

`60/60s` untuk `write_interactive` adalah nilai rollout awal, bukan angka permanen.
Nilai tersebut memberi ruang untuk workflow 25–30 pekerjaan per menit tanpa membuka
hingga empat write berat per detik. Kalibrasi akhir dilakukan setelah telemetry.

Environment/settings harus dapat mengubah nilai kategori tanpa mengedit decorator,
tetapi default aman tetap tersimpan di repository.

---

## 5. Pemetaan Endpoint Target

### 5.1 Endpoint yang dipindah ke `write_interactive`

| Endpoint | Method yang dihitung | Alasan |
|---|---|---|
| `api_save_detail_ahsp_for_pekerjaan` | POST | satu save per pekerjaan yang diedit |
| `api_pekerjaan_pricing` | POST | override BUK dilakukan per pekerjaan |

### 5.2 Mixed-method endpoint

| Endpoint | GET | POST |
|---|---|---|
| `api_project_pricing` | `read_interactive` | `sync_frequent` |
| `api_project_parameters` | `read_interactive` | `sync_frequent` |
| `api_project_computed_parameters` | `read_interactive` | `sync_frequent` |
| `api_volume_formula_state` | `read_interactive` | `sync_frequent` |
| `api_pekerjaan_pricing` | `read_interactive` | `write_interactive` |

Alias `api_volume_formula_state` harus tetap berbagi quota dengan route utamanya
karena keduanya memanggil fungsi yang sama.

### 5.3 Endpoint 240 lainnya

Endpoint POST yang sudah memakai explicit `240/60` dipindahkan ke kategori
`sync_frequent` tanpa mengubah angka rollout awal:

- `api_save_volume_pekerjaan`;
- `api_project_parameters_sync`;
- `api_project_computed_parameters_sync`;
- `api_assign_pekerjaan_weekly`.

### 5.4 Endpoint yang tetap `write` atau `bulk`

Seluruh aksi langka seperti reset, delete template, sync reference, regenerate,
cleanup, dan reset override tetap memakai kategori sekarang. Tidak ada kenaikan
limit tanpa bukti workflow.

---

## 6. Work Package

### WP-RL0 — Contract Freeze dan Baseline

**Status:** `DONE`  
**Dependency:** tidak ada

Scope:

- simpan inventaris 30 endpoint sebagai fixture/test parametrik;
- catat konfigurasi backend cache development, test, Docker, dan production;
- reproduksi defect request berjarak 50 detik;
- ambil baseline test governance dan API terkait;
- tetapkan daftar mixed-method endpoint;
- pastikan tidak ada perubahan existing user yang ikut tertimpa.

Definition of Done:

- reproduksi lama menghasilkan 429 palsu dan terdokumentasi dalam test yang awalnya
  gagal terhadap implementasi lama;
- baseline 30 endpoint cocok dengan audit;
- status worktree sebelum implementasi dicatat.

### WP-RL1 — Core Rate Limiter v2

**Status:** `DONE`  
**Dependency:** WP-RL0

File utama:

- `detail_project/api_helpers.py`;
- `config/settings/base.py` atau modul setting rate limit terpisah;
- test baru `detail_project/tests_rate_limit_v2.py`.

Scope:

- buat helper penghitung fixed-window v2;
- gunakan `time.time()` melalui clock injectable agar test deterministik;
- gunakan `cache.add` untuk counter pertama dan `cache.incr` berikutnya;
- tangani race key-expired antara `add` dan `incr` dengan retry terbatas;
- gunakan prefix key versi baru agar tidak berbenturan dengan counter legacy;
- tambahkan parameter `methods`;
- hitung `reset_at`, `remaining`, dan `retry_after`;
- tambahkan header `Retry-After` pada 429;
- implementasikan fail-open terobservasi saat cache error;
- pertahankan format error lama secara backward-compatible.

Kontrak respons 429 minimum:

```json
{
  "success": false,
  "code": "RATE_LIMIT_EXCEEDED",
  "message": "Terlalu banyak permintaan. Coba lagi dalam 17 detik.",
  "retry_after": 17,
  "details": {
    "limit": 60,
    "window_seconds": 60,
    "remaining": 0,
    "reset_at": 1785552017,
    "category": "write_interactive"
  }
}
```

Definition of Done:

- TTL tidak berubah setelah increment kedua dan seterusnya;
- request setelah melewati boundary window kembali diizinkan;
- request paralel tidak kehilangan increment pada Redis integration test;
- cache error tidak mengubah save menjadi HTTP 500;
- 429 mempunyai header dan JSON retry yang konsisten;
- legacy API response consumer tetap berfungsi.

### WP-RL2 — Method Separation dan Category Migration

**Status:** `DONE`  
**Dependency:** WP-RL1

File utama:

- `detail_project/views_api.py`;
- `detail_project/views_api_tahapan_v2.py`;
- test governance yang saat ini melakukan assertion string decorator.

Scope:

- tambahkan kategori `write_interactive`, `sync_frequent`, dan
  `read_interactive`;
- migrasikan delapan decorator explicit 240 ke kategori bernama;
- terapkan GET/POST limiter terpisah pada lima mixed-method view;
- pindahkan dua hot-path ke `write_interactive`;
- pertahankan `key_prefix` eksplisit untuk route alias bila diperlukan;
- ganti brittle source-string assertions dengan behavioral/metadata assertions
  bila memungkinkan.

Definition of Done:

- GET tidak menambah counter POST;
- POST tidak menambah counter GET;
- user A dan user B mempunyai counter terpisah;
- dua project milik user yang sama tetap berbagi quota sesuai D-06;
- route alias volume tidak menggandakan quota;
- inventaris tetap 30 endpoint atau perubahan jumlah dijelaskan eksplisit.

### WP-RL3 — UX dan Error Handling 429

**Status:** `DONE`  
**Dependency:** WP-RL1, WP-RL2

File kandidat:

- `detail_project/static/detail_project/js/core/http.js`;
- `detail_project/static/detail_project/js/template_ahsp.js`;
- `detail_project/static/detail_project/js/rekap_rab.js`;
- `detail_project/static/detail_project/js/rincian_ahsp.js`;
- test JS terkait.

Scope:

- shared HTTP helper membaca `message`, `user_message`, `code`, dan
  `retry_after` secara konsisten;
- raw `fetch()` pada Template AHSP tidak mengganti pesan 429 dengan pesan network
  generik;
- save sebelum pindah pekerjaan tetap berhenti apabila mendapat 429;
- dirty state Template AHSP tetap aktif;
- draft pricing tetap tersedia dan tombol retry memakai payload terbaru;
- tampilkan satu toast yang jelas, bukan toast error berlapis;
- tidak membuat retry loop otomatis tanpa tindakan user.

Definition of Done:

- simulasi 429 pada Template AHSP mempertahankan edit dan selection pekerjaan;
- simulasi 429 pricing mempertahankan input dan localStorage;
- countdown/pesan menggunakan `retry_after` aktual;
- tidak ada double-submit setelah retry.

### WP-RL4 — Observability dan Calibration Gate

**Status:** `DONE — telemetry tersedia; review kalibrasi menunggu traffic representatif`  
**Dependency:** WP-RL1, WP-RL2

Scope:

- log structured: endpoint, method, category, limit, count, retry_after,
  project_id bila tersedia, dan user ID internal;
- jangan log body request atau data AHSP;
- metric counter untuk `allowed`, `blocked`, dan `backend_error`;
- metric tidak memakai user/project sebagai label agar cardinality terkendali;
- log warning saat pemakaian mencapai minimal 80% quota, dengan sampling agar
  tidak spam;
- dashboard/query operasional untuk melihat endpoint penyebab 429;
- review telemetry minimal 3 hari penggunaan representatif sebelum menurunkan
  atau menaikkan angka rollout.

Definition of Done:

- endpoint penyebab 429 dapat diidentifikasi tanpa membaca payload;
- false-positive dan script flood dapat dibedakan dari frekuensi/log;
- tersedia keputusan tertulis untuk mempertahankan atau mengubah `60/60s`.

### WP-RL5 — Rollout, Cleanup, dan Dokumentasi

**Status:** `DONE — rollout switch dan rollback drill terverifikasi lokal`  
**Dependency:** WP-RL1–WP-RL4

Scope:

- sediakan mode `observe`, `v2`, dan `off` melalui `DETAIL_PROJECT_RATE_LIMIT_MODE`;
- `observe`: v2 menghitung/log `would_block` tanpa memblokir;
- validasi staging dengan Redis dan minimal dua worker;
- aktifkan v2 setelah perbandingan counter dinilai benar;
- `off` hanya digunakan untuk emergency rollback; proteksi body/auth/CSRF tetap aktif;
- perbarui komentar/docstring yang masih menyebut angka sebagai “per minute”
  tanpa menjelaskan algoritma;
- buat evidence hasil implementasi terpisah dari plan ini.

Definition of Done:

- production aktif di mode v2;
- tidak ada peningkatan 500/cache error;
- warning 429 palsu pada workflow normal tidak dapat direproduksi;
- legacy code dihapus setelah rollback window berakhir;
- runbook rollback tersedia.

---

## 7. Test Matrix Wajib

### 7.1 Unit test waktu

| Kasus | Ekspektasi |
|---|---|
| 20 request dalam bucket limit 20 | seluruhnya diizinkan |
| request ke-21 dalam bucket yang sama | 429 |
| request setelah boundary | 200 dan counter baru |
| 21 request berjarak 50 detik | tidak menghasilkan pola 429 kumulatif legacy |
| request tepat di boundary | masuk tepat satu bucket |
| clock fractional/rounding | `Retry-After` minimal 1 detik |

### 7.2 Unit test key dan method

- user berbeda tidak berbagi counter;
- endpoint berbeda tidak berbagi counter;
- GET dan POST tidak berbagi counter;
- kategori berbeda tidak berbagi counter;
- alias yang disengaja tetap berbagi counter;
- beberapa project user yang sama tetap berbagi counter.

### 7.3 Concurrency dan backend

- jalankan request increment paralel terhadap Redis test container;
- final count harus sama dengan jumlah attempt;
- tidak ada lost update;
- expiry tidak diperpanjang oleh increment;
- cache timeout/disconnect menjalankan fail-open dan menghasilkan log/metric.

### 7.4 Endpoint integration

- Template AHSP: save normal, limit, retry setelah reset;
- pricing pekerjaan: GET tidak menghabiskan quota POST;
- project pricing/parameter/formula: pemisahan GET/POST;
- bulk endpoint tetap 5/300;
- unauthorized dan method-not-allowed tetap mengikuti decorator order yang benar;
- body 413 tetap dihitung sebagai attempt sesuai D-02.

### 7.5 Frontend regression

- Template AHSP dirty-state pada 429;
- tidak pindah pekerjaan ketika pre-switch save gagal;
- pricing draft tidak hilang;
- pesan retry aktual tampil;
- tidak ada toast ganda atau retry loop;
- Vitest governance terkait decorator/category diperbarui bila ada.

### 7.6 Full verification gate

Minimal command sebelum handoff:

```text
python manage.py check --settings=config.settings.test
python manage.py test detail_project.tests_rate_limit_v2 --settings=config.settings.test
python manage.py test detail_project.tests_hi10_write_governance --settings=config.settings.test
python manage.py test detail_project.tests_template_ahsp_ta_followups --settings=config.settings.test
python manage.py test detail_project.tests_jadwal_api_hardening --settings=config.settings.test
npm test -- --run
python manage.py makemigrations --check --dry-run
git diff --check
```

Redis concurrency test dijalankan terpisah dengan backend Redis nyata; LocMem test
tidak dianggap bukti atomicity lintas worker.

---

## 8. Rollout Plan

### Tahap 1 — Local/test

- implementasikan v2 dan seluruh deterministic test;
- jalankan existing regression suite;
- verifikasi tidak ada migration.

### Tahap 2 — Staging `observe`

- v2 menghitung secara paralel tanpa memblokir;
- review metric `would_block`, endpoint, method, dan reset time;
- uji minimal dua worker dengan Redis.

### Tahap 3 — Staging `v2`

- lakukan UAT workflow 30+ pekerjaan Template AHSP;
- lakukan browsing dan update override BUK lintas pekerjaan;
- lakukan save Volume dan Jadwal;
- jalankan script flood terkontrol untuk memastikan 429 tetap bekerja.

### Tahap 4 — Production canary

- aktifkan v2 pada stability window dengan monitoring aktif;
- pantau 429, cache error, latency, dan save failure;
- jangan sekaligus mengubah batching frontend List Pekerjaan/Rekap RAB agar sumber
  regresi tetap mudah diisolasi.

### Tahap 5 — Cleanup

- setelah minimal 7 hari stabil, kunci mode `v2` dan hapus penggunaan mode `observe`;
- review angka `write_interactive` berdasarkan telemetry;
- arsipkan evidence dan keputusan kalibrasi.

---

## 9. Rollback Plan

Trigger rollback:

- lonjakan HTTP 500 terkait cache/limiter;
- request normal diblokir sebelum batas v2;
- counter berbeda signifikan dari attempt pada Redis;
- regression save/dirty-state;
- latency limiter bertambah material.

Langkah rollback:

1. ubah mode ke `off` melalui konfigurasi emergency, atau deploy revision sebelumnya;
2. restart worker/web sesuai runbook deployment;
3. jangan menghapus key v2 secara manual — biarkan expire alami;
4. kumpulkan log endpoint/method/reset time;
5. perbaiki dan ulangi staging `observe`.

Rollback tidak memerlukan migration atau perubahan data bisnis.

---

## 10. Di Luar Scope Remediasi Wajib

Item berikut dicatat tetapi tidak digabung ke deployment limiter v2:

- menyatukan destructive preview dan upsert List Pekerjaan;
- mengubah debounce Rekap RAB menjadi commit-on-blur;
- batch-save Template AHSP lintas pekerjaan;
- bulk override BUK;
- memasang rate limit ke seluruh export/read yang saat ini belum dilindungi;
- audit query/performa cascade bundle re-expansion;
- membersihkan modul Jadwal/performance monitor legacy.

Masing-masing dapat menjadi work package lanjutan setelah limiter stabil. Pemisahan
ini mencegah perubahan UX/kontrak API yang tidak diperlukan masuk ke perbaikan P0.

---

## 11. Risiko dan Mitigasi

| Risiko | Level | Mitigasi |
|---|---|---|
| Burst dua kali limit di batas fixed-window | Rendah | telemetry; evaluasi token bucket bila nyata |
| Backend non-Redis pada production | Tinggi | deployment/system check wajib |
| Decorator GET/POST salah urut | Sedang | integration test seluruh mixed-method view |
| Response 429 tidak dibaca raw fetch | Sedang | WP-RL3 + JS regression |
| Limit 60 terlalu rendah/tinggi | Sedang | config override + calibration gate |
| Redis error membebaskan limiter | Sedang | fail-open terlog, alert backend error, guard lain tetap aktif |
| Dual implementation menambah kompleksitas sementara | Rendah | hapus legacy setelah stability window |

---

## 12. Definition of Done Keseluruhan

- [x] algoritma tidak lagi me-reset window pada setiap request;
- [x] increment atomik pada Redis multi-worker (process-level Docker smoke lulus: 8 proses menghasilkan count 1–8, final 8);
- [x] GET dan POST mempunyai quota terpisah;
- [x] dua hot-path memakai kategori `write_interactive`;
- [x] seluruh explicit 240 memakai kategori bernama;
- [x] response 429 mempunyai `Retry-After` aktual;
- [x] Template AHSP dan pricing mempertahankan draft ketika 429;
- [x] endpoint penyebab 429 terlihat pada structured warning dan metric per endpoint/method/kategori;
- [x] test waktu, method, key, concurrency, endpoint, dan frontend lulus;
- [ ] UAT 30+ pekerjaan tidak menghasilkan 429 palsu;
- [ ] flood terkontrol tetap diblokir;
- [x] rollout mode `observe` dan `v2`, serta rollback mode `off`, terbukti pada Docker smoke;
- [x] tidak ada migration atau perubahan data bisnis;
- [ ] evidence kalibrasi akhir diterbitkan setelah minimal 3 hari traffic representatif.

### Execution checkpoint — 2026-08-01

Selesai:

- `detail_project/api_helpers.py`: fixed-window v2, atomic `add/incr`, method
  filtering, headers `X-RateLimit-*`/`Retry-After`, fail-open terobservasi;
- kategori `write_interactive`, `sync_frequent`, dan `read_interactive`;
- lima mixed-method endpoint dipisahkan GET/POST;
- production settings menolak cache non-Redis;
- Template AHSP, Rekap RAB, dan shared HTTP helper membaca kontrak 429;
- metric limiter v2 global dan per endpoint/method/kategori dengan label terbatas;
- ringkasan `rate_limits` tersedia pada endpoint performance admin;
- rollout switch `v2`/`observe`/`off` tersedia melalui setting deployment;
- test backend limiter/governance/monitoring/API access: 28/28 lulus;
- frontend suite: 394 lulus, 25 skip.
- Redis container smoke test: sequential atomic counts `[1, 2, 3]`, 100 concurrent
  increments menghasilkan final count `100` dan 100 nilai unik.
- Docker production-settings check dengan Redis dan staging host/CSRF override:
  **lulus tanpa issue**.
- Docker `observe` smoke test: dua request pada limit 1/60 tetap HTTP 200 dan
  menghasilkan metric/log `would_block`.

Masih pending sebelum canary production:

- kalibrasi akhir limit kategori berdasarkan traffic staging/production yang representatif;
- UAT workflow 30+ pekerjaan dan stability window minimal 3 hari.

Dashboard UI bukan blocker: endpoint performance admin sudah memuat ringkasan
limiter, sedangkan endpoint/method/kategori tersedia pada structured warning dan
metric key ber-cardinality rendah.

Gate yang sudah diverifikasi lokal/Docker:

- process-level Redis smoke dengan 8 proses independen (tidak ada lost update);
- rollback drill `off` (dua request tetap 200) dan `v2` (request kedua 429 dengan header retry);
- metric global terakhir: `allowed=4`, `blocked=2`, `would_block=1`, `near_limit=3`, `backend_error=0` (synthetic smoke, bukan traffic produksi).
- evidence lengkap disimpan pada `Review/R5_Detail_Project/35_API_Rate_Limiter_Remediation_Evidence_20260801.md`.

---

## 13. Urutan Eksekusi Ringkas

```text
WP-RL0 baseline
    ↓
WP-RL1 core atomic fixed-window v2
    ↓
WP-RL2 method separation + category migration
    ↓
WP-RL3 UX/error 429
    ↓
WP-RL4 observability + calibration
    ↓
WP-RL5 observe → v2 → cleanup
```

Tidak ada perubahan endpoint batching atau layout UI dalam jalur kritis ini.
