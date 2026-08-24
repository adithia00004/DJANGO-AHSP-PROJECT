# 37 — Guided Timeline Change & Repair

**Perubahan tanggal proyek tanpa menghapus progress tanpa sepengetahuan user**

| | |
|---|---|
| Status | DRAFT — menunggu keputusan owner (§12) |
| Tanggal | 2026-08-24 |
| Scope | `dashboard` (project edit, mass edit) + `detail_project` (Jadwal Pekerjaan, timeline service) |
| Dokumen terkait | 22 (Audit Jadwal), 26 (Cross-Page Reconciliation), 28 (Execution Tracker), 36 (Sync Over-Notification) |
| Non-goal | Bug `month_number` pada Kurva S monthly, sync over-notification (doc 36), Canonical Formula Service |

---

## 1. Ringkasan Eksekutif

Perubahan tanggal proyek dilakukan di **level dashboard**, sementara konsekuensinya jatuh di
**Jadwal Pekerjaan**. Saat ini ada **enam jalur tulis berbeda** (§2.1 + §2.4) dengan perilaku yang
berbeda-beda untuk kejadian yang sama, mulai dari yang sangat hati-hati sampai yang menghapus seluruh
progress tanpa peringatan spesifik — bahkan sampai yang tanpa pengaman sama sekali. Tombol "Perbarui Struktur Waktu" di Jadwal adalah katup perbaikan manual yang
menambal celah antar jalur itu, bukan fitur yang berdiri sendiri.

Dokumen ini menetapkan satu kebijakan tunggal — **tidak ada nilai progress yang berubah atau hilang
tanpa keputusan sadar user** — merancang mesin resolusi yang hilang (kebijakan pergeseran minggu),
dan menyusun rencana implementasi bertahap dengan gate test per tahap.

Kabar baiknya: sebagian besar fondasi **sudah ada di repo dan tinggal disambung**.

---

## 2. Baseline Terverifikasi

Seluruh isi bagian ini dibaca langsung dari kode pada 2026-08-24, bukan ekstrapolasi.

### 2.1 Tiga jalur utama perubahan timeline

(Sweep lanjutan di §2.4 menemukan tiga jalur lagi — totalnya enam.)

| # | Jalur | Kode | Perilaku saat ini |
|---|---|---|---|
| P1 | Edit project tunggal | `dashboard/views.py:605-676` → `apply_project_timeline_change` (`detail_project/timeline_utils.py:154`) | **Paling matang.** Analisis dampak → blokir bila kena actual → `trim_planned` dengan dua konfirmasi → audit `DetailAHSPAudit` → `_regenerate_weekly_structure` → invalidate cache |
| P2 | Mass edit | `dashboard/views_mass_edit.py:144` → `reset_project_progress` (`detail_project/progress_utils.py:348`) | **Destruktif.** `PekerjaanProgressWeekly.objects.filter(project).delete()` — SELURUH progress planned + actual hilang. Hanya bereaksi pada perubahan `tanggal_mulai`; perubahan `tanggal_selesai` **tidak memicu apa pun** |
| P3 | Tombol "Perbarui Struktur Waktu" | `EventBinder.js:76` → `DataOrchestrator.regenerateTimeline` (`:172`) → `api_regenerate_tahapan_v2` (`views_api_tahapan_v2.py:1017`) | **Buta.** Tanpa analisis dampak. Data server aman, tapi editan belum disimpan dibuang dan seluruh state client di-reset |

Ketiganya memanggil primitive yang mirip (`_build_weekly_tahapan_instances` + `sync_weekly_to_tahapan`)
dengan kebijakan keselamatan yang berbeda-beda. Itu akar masalahnya.

### 2.2 Aset yang sudah ada tetapi menganggur

Ini yang membuat pekerjaan ini jauh lebih murah dari kelihatannya:

1. **Service analisis + mutasi terpusat** — `analyze_project_timeline_change` (`timeline_utils.py:70`)
   sudah mengembalikan payload dampak lengkap: `planned_records`, `actual_records`,
   `affected_week_numbers`, `affected_week_start/end`, `new_week_count`, `start_requires_policy`.
   Docstring modulnya sudah menyatakan niat yang benar: *"keeps timeline impact analysis and the
   mutation path in one place so the project form and API cannot implement different trimming rules"* —
   niat itu belum ditegakkan karena P2 melewatinya.
2. **API preview/commit sudah ada dan ter-route** — `api_preview_project_timeline` dan
   `api_commit_project_timeline` (`views_api_tahapan_v2.py:585,617`), terdaftar di `urls.py:363-368`,
   ber-`schedule_revision` wajib (`required=True`) sebagai kunci optimistik.
   **Tidak ada satu pun konsumen di frontend.** Kode hidup tanpa pemakai.
3. **UI ringkasan dampak sudah ada** — `dashboard/templates/dashboard/project_form.html:41-70`
   sudah menampilkan minggu terdampak, jumlah record planned/actual, tombol batal, dan tombol
   "Potong Planned Progress" dengan konfirmasi kedua.
4. **Sinyal basi otoritatif sudah ada** — `readiness.py:482-512` menghitung `timeline_stale`
   (ada baris weekly di luar jendela proyek), sudah ada test (`tests_wp_b4_readiness.py:186-209`).
   **Halaman Jadwal tidak pernah membacanya** — satu-satunya jejak adalah komentar di
   `DataOrchestrator.js:109` yang menyebut sinyal ini *seharusnya* jadi acuan.
5. **Test kontrak sudah ada** — `tests_timeline_crud_hardening.py` (11 test), termasuk
   `test_timeline_trim_planned_preserves_actual_contract` dan `test_stale_schedule_revision_is_rejected`.

### 2.3 Defect yang menjadi target

| ID | Severity | Defect | Bukti |
|---|---|---|---|
| **T-01** | **Tinggi** | Mass edit menghapus SELURUH `PekerjaanProgressWeekly` saat `tanggal_mulai` berubah, tanpa analisis dampak, tanpa perlindungan actual, tanpa audit timeline | `views_mass_edit.py:144`, `progress_utils.py:362` |
| **T-02** | **Tinggi** | Mass edit tidak melakukan apa pun saat `tanggal_selesai` berubah → struktur tahapan langsung basi tanpa perbaikan otomatis | `views_mass_edit.py:140-144` (hanya membandingkan `original_start`) |
| **T-03** | **Tinggi** | `start_requires_policy` adalah jalan buntu: setiap perubahan tanggal **mulai** pada proyek yang punya progress apa pun ditolak mentah, tanpa jalan keluar yang ditawarkan | `timeline_utils.py:100-109`, pesan di `views.py:631` |
| **T-04** | Sedang | Tombol "Perbarui Struktur Waktu" selalu aktif di toolbar utama meski `timeline_stale` bernilai false; membuang editan belum disimpan untuk operasi yang no-op di kondisi sehat | `kelola_tahapan_grid_modern.html:161`, `DataOrchestrator.js:183-195` |
| **T-05** | Sedang | Regenerate tidak meng-invalidate `stateManager._chartDataCache`, dan `loadAssignments` dijalankan saat `timeColumns` masih kosong → 0 baris ter-map secara senyap | `data-loader.js:319-320,598`, `state-manager.js:555` |
| **T-06** | **Tinggi** | Baris `PekerjaanProgressWeekly` di luar jendela baru **tidak pernah dibersihkan atau dipindahkan**. `trim_planned` hanya menulis `planned_proportion=0`; baris beserta tanggal lamanya tetap ada. Akibatnya `timeline_stale` menjadi **true tepat setelah perubahan yang sukses**, dan grid tetap memadding kolom sampai `week_number` tertinggi yang tersimpan. **Tombol "Perbarui Struktur Waktu" tidak dapat memperbaikinya** — satu-satunya kondisi di mana tombol itu benar-benar dibutuhkan justru tidak bisa ia tangani | `timeline_utils.py:209` (`rows.update(planned_proportion=0)`), `jadwal_pekerjaan_adapter.py:227` (`target_weeks = max(expected_weeks, max_week_number)`), `readiness.py:484-492` |

**Catatan penting yang sudah diverifikasi (repro dijalankan 2026-08-24, file test dihapus setelahnya):**
`api_regenerate_tahapan_v2` **tidak** menghapus progress. `api_chart_data` mengembalikan sel identik
sebelum/sesudah regenerate untuk tiga skenario (boundary sama, boundary berubah, regenerate ke monthly);
`PekerjaanProgressWeekly` tetap utuh. Jadi T-04/T-05 adalah cacat **presentasi dan UX**, bukan kehilangan
data. Kehilangan data yang nyata hanya ada di T-01.

**Bukti T-06 (repro terpisah, dijalankan 2026-08-24):** proyek 1 Jan – 28 Feb (9 minggu) dengan progress
di minggu 1, 2, dan 8; diperpendek ke 31 Jan dengan `trim_planned`.

| | Sebelum | Sesudah trim | Sesudah tekan tombol |
|---|---|---|---|
| Jendela proyek | 1 Jan – 28 Feb | 1 Jan – 31 Jan | 1 Jan – 31 Jan |
| `TahapPelaksanaan` weekly | 9 | **5** (benar) | **5** (benar) |
| Kolom di grid/chart | 9 | **8** (salah) | **8** (tidak berubah) |
| Baris weekly minggu 8 | 16–22 Feb, planned 40 | 16–22 Feb, planned **0** (tetap ada) | tetap ada |
| `timeline_stale` | false | **true** | **true** |

Konsekuensinya untuk rencana: setiap resolusi di §4 **wajib** menuntaskan nasib baris di luar jendela —
digeser, dijangkar, atau dihapus — bukan sekadar di-nol-kan. Ini menjadi syarat kelulusan WP-T1.

### 2.4 Jalur dan objek yang belum terinventarisasi (sweep 2026-08-24)

Sweep lanjutan setelah §2.1 ditulis. Ternyata jalur perubahan timeline **bukan tiga, melainkan enam**,
dan ada objek yang tidak pernah dibereskan oleh jalur mana pun. Semua dibaca langsung dari kode.

| ID | Gap | Bukti |
|---|---|---|
| **G-1** | **Django admin.** `ProjectAdmin` fieldset "Timeline Pelaksanaan" mengekspos `tanggal_mulai`, `tanggal_selesai`, `durasi_hari` sebagai field editable (tidak ada di `readonly_fields`). Simpan dari sana hanya memanggil `Project.save()`: `schedule_revision` naik, tetapi **tidak ada** analisis dampak, rebuild tahapan, audit timeline, maupun perlindungan realisasi. Jalur paling telanjang dari semuanya | `dashboard/admin.py:23,60-64,83-105` |
| **G-2** | **Duplikat project.** `project_duplicate` mengizinkan user mengubah tanggal mulai **dan** selesai saat menduplikasi, lalu `duplicated.save()` — bypass penuh. Ditambah dua inkonsistensi di `DeepCopyService`: (a) tahapan disalin dengan **tanggal sumber apa adanya**, tidak digeser ke jendela baru; (b) `PekerjaanProgressWeekly` (SSOT) **tidak disalin sama sekali**, padahal `PekerjaanTahapan` (turunannya) disalin. Akibatnya Jadwal hasil duplikat tampak kosong, dan sinkronisasi pertama akan menghapus assignment yang barusan disalin karena dibangun ulang dari canonical yang kosong | `dashboard/views.py:696-745`, `services.py:4348` (`_copy_project`), `services.py:5134` (`_copy_jadwal_pekerjaan`), `_copy_tahapan` |
| **G-3** | **Perubahan batas minggu adalah perubahan timeline yang tidak diperlakukan sebagai perubahan timeline.** `api_update_week_boundaries` hanya menyimpan preferensi lalu invalidate cache — tanpa analisis dampak dan **tanpa rebuild tahapan**. Padahal mengubah `week_start_day`/`week_end_day` **memotong ulang seluruh minggu**: tanggal yang sama berpindah bucket, sehingga makna setiap nilai — termasuk realisasi — bergeser tanpa satu pun konfirmasi. Frontend kebetulan memanggil regenerate sesudahnya, tetapi kontrak API tidak menjaminnya | `views_api_tahapan_v2.py:523-570` |
| **G-4** | **Tahapan manual tidak pernah dibereskan.** `_regenerate_weekly_structure` hanya menghapus tahapan `is_auto_generated=True, generation_mode='weekly'`. Tahapan manual (dibuat lewat `api_list_create_tahapan`, masih ter-route) mempertahankan tanggal lamanya yang bisa jatuh di luar jendela baru. Lebih halus: `sync_weekly_to_tahapan` memakai **seluruh** tahapan dan pada mode weekly memetakan berdasarkan `urutan + 1` — sehingga tahapan manual ikut menyerap nilai minggu menurut urutannya | `timeline_utils.py:134-139`, `progress_utils.py:212-216,249-252`, `urls.py:279` |
| **G-5** | **`project_edit` tidak mengirim `expected_revision`** ke `apply_project_timeline_change`, padahal parameternya tersedia dan dipakai oleh endpoint API. Dua tab dashboard dapat saling menimpa; hanya jalur API yang benar-benar terkunci | `dashboard/views.py:639-645` vs `timeline_utils.py:160,168-175` |
| **G-6** | **Hilir belum dikunci test.** Rekap Kebutuhan menurunkan kebutuhan material per minggu dari canonical yang sama (doc 23). Cache-nya di-invalidate lewat signal, tetapi belum ada test yang menegakkan "setelah timeline berubah, Rekap Kebutuhan ikut bergeser". Export yang sudah terlanjur dibuat juga menjadi tidak sinkron | `signals.py:92-113`, doc 23 |

Konsekuensi untuk rencana: invariant **I-3 (satu service, satu kebijakan)** belum dapat dinyatakan
tercapai hanya dengan menutup P1/P2/P3. G-1 s/d G-3 adalah jalur tulis penuh yang setara, dan G-4
adalah objek yang bocor dari semua jalur.

---

## 3. Prinsip Kebijakan (invariant)

Empat aturan ini mengikat seluruh desain di bawah. Setiap WP punya test yang menegakkannya.

- **I-1 — Actual adalah fakta historis; hanya user yang boleh menyatakan fakta itu salah.**
  `actual_proportion` / `actual_cost` tidak pernah digeser, ditumpuk, diskalakan, atau dihapus oleh
  operasi timeline — **kecuali** user secara eksplisit menyatakan niat **koreksi** (§4.1), yang
  artinya tanggal lama memang tidak pernah valid. Di bawah niat **pergeseran**, realisasi paling jauh
  hanya boleh di-*re-bucket* per hari tumpang tindih (jumlah tidak berubah). Bila perubahan tanggal
  membuat baris actual jatuh di luar jendela proyek, operasi **ditolak** — bukan diselesaikan diam-diam.
- **I-2 — Tidak ada mutasi tanpa preview.** Setiap jalur tulis timeline wajib melewati
  `analyze_project_timeline_change` dan menampilkan hasilnya sebelum commit. Tanpa pengecualian
  untuk mass edit.
- **I-3 — Satu service, satu kebijakan.** Semua jalur (form tunggal, mass edit, tombol Jadwal)
  memanggil `apply_project_timeline_change`. `reset_project_progress` tidak boleh lagi dipanggil
  dari jalur perubahan tanggal — hanya dari aksi "Reset progres" yang eksplisit.
- **I-4 — Setiap perubahan meninggalkan jejak.** Satu entri `DetailAHSPAudit` per commit, berisi
  timeline lama/baru, resolusi yang dipilih, dan daftar baris yang tergeser/ter-trim.

---

## 4. Bagian yang Hilang: Kebijakan Resolusi Minggu

Inti masalah T-03: `PekerjaanProgressWeekly` dikunci pada `(pekerjaan, week_number)` di mana
`week_number` **relatif terhadap tanggal mulai proyek**, sementara `week_start_date`/`week_end_date`
disimpan sebagai tanggal absolut. Saat tanggal mulai bergeser, dua semantik itu bertabrakan dan sistem
saat ini memilih untuk menyerah (`start_requires_policy = True`).

### 4.1 Niat user adalah input, bukan sesuatu yang bisa disimpulkan sistem

Dua perubahan tanggal yang **identik secara data** menuntut perlakuan yang berlawanan:

- **N-A — Koreksi.** Tanggal lama memang salah (salah ketik, lupa diisi, template dipakai ulang).
  Angka progress yang sudah diinput dimaksudkan untuk "minggu ke-1 pekerjaan", bukan untuk
  "1–7 Januari". Tanggal lama **tidak pernah valid**, termasuk untuk realisasi.
- **N-B — Pergeseran nyata.** Tanggal lama benar untuk masanya; jadwal proyek betul-betul berubah
  (permintaan owner, kebutuhan administratif, penundaan). Realisasi yang tercatat adalah **fakta
  historis** yang terjadi pada tanggal itu dan tidak boleh pindah.

Tidak ada sinyal di database yang membedakan keduanya. Karena itu **langkah pertama dialog adalah
menanyakan niat**, dan opsi resolusi yang ditawarkan disaring berdasarkan jawabannya. Ini juga
satu-satunya cara sah untuk membuka kunci T-03: perubahan tanggal mulai boleh memindahkan realisasi
**hanya** bila user menyatakan ini koreksi.

### 4.2 Model dua sumbu

Secara internal, resolusi bukan satu daftar datar melainkan kombinasi dua keputusan ortogonal:

**Sumbu 1 — Pemetaan (apa yang menjangkar sebuah nilai):**

| Kode | Semantik |
|---|---|
| `BY_ORDINAL` | Minggu ke-N tetap minggu ke-N; hanya tanggalnya dihitung ulang |
| `BY_DATE` | Nilai tetap pada tanggal kalendernya; `week_number` dihitung ulang terhadap tanggal mulai baru |
| `BY_SCALE` | Seluruh kurva dipadatkan/diregangkan proporsional ke jumlah minggu baru (posisi relatif dipertahankan) |

**Sumbu 2 — Nasib nilai yang tidak dapat ditempatkan:**

| Kode | Semantik |
|---|---|
| `ACCUMULATE_EDGE` | Ditumpuk ke minggu batas terdekat (minggu pertama bila jatuh sebelum jendela, minggu terakhir bila sesudah) |
| `DROP` | Dihapus; baris di luar jendela dibuang, baris di dalam jendela tidak tersentuh |
| `BLOCK` | Operasi ditolak; user harus membereskan dulu atau memilih niat/opsi lain |

`BY_SCALE` menurut definisi tidak pernah meninggalkan sisa, jadi sumbu 2 tidak berlaku untuknya.

### 4.3 Opsi yang dilihat user

User tidak melihat matriks. Ia melihat daftar skenario bernama yang dihasilkan dari kombinasi sah:

| Opsi (label user) | Kombinasi | Kapan tepat | Total progress |
|---|---|---|---|
| **Pertahankan urutan minggu** | `BY_ORDINAL` + `ACCUMULATE_EDGE`/`DROP` bila durasi menyusut | Koreksi salah input; proyek diundur/dimajukan utuh dengan durasi sama | Utuh (kecuali `DROP`) |
| **Ikuti tanggal kalender** | `BY_DATE` + `DROP` | Pergeseran nyata; pekerjaan yang jatuh di luar jadwal baru memang batal | Berkurang, disengaja |
| **Padatkan ke minggu batas** | `BY_DATE` + `ACCUMULATE_EDGE` | Pergeseran nyata; pekerjaan tetap harus dilakukan, dipadatkan di awal/akhir | Utuh, distribusi berubah |
| **Padatkan/regangkan proporsional** | `BY_SCALE` | Durasi berubah signifikan, lingkup kerja sama (proyek dipercepat/diperpanjang) | Utuh, distribusi diskalakan |
| **Hapus semua progress** | — | Rencana lama dibuang total | Nol |

Opsi 1, 2, dan 3 dari usulan owner (2026-08-24) masing-masing memetakan ke baris 1, 3, dan 2.
**Padatkan proporsional** adalah tambahan yang menutup kasus "durasi berubah, lingkup sama" — kasus
yang ditangani canggung oleh tiga opsi lainnya.

### 4.4 Aturan realisasi (turunan I-1)

| Niat | Perlakuan `actual_proportion` / `actual_cost` |
|---|---|
| **N-A Koreksi** | Ikut pemetaan yang sama dengan planned — tanggal lama memang tidak pernah valid |
| **N-B Pergeseran** | **Tidak pernah dipindah antar minggu.** Bila boundary bergeser, hanya di-*re-bucket* berdasarkan tumpang tindih hari (jumlah tetap sama = tidak ada pemalsuan). Bila jatuh di luar jendela baru → `BLOCK`, dengan penyebutan minggu yang bermasalah |

`ACCUMULATE_EDGE` dan `BY_SCALE` **tidak pernah** berlaku untuk realisasi di bawah niat N-B.

### 4.5 Batas kuantitas — terverifikasi aman

`api_assign_pekerjaan_weekly` (`views_api_tahapan_v2.py:414-448`) menegakkan tiga batas per pekerjaan:
total planned lintas minggu ≤ 100%, kapasitas volume master, dan validator per baris ≤ 100.

Karena `ACCUMULATE_EDGE` dan `BY_SCALE` hanya **memindahkan** nilai (total tidak bertambah), dan total
sebelumnya sudah ≤ 100%, hasil akumulasi tertinggi yang mungkin sama dengan total lama — yaitu ≤ 100%.
**Tidak ada resolusi di §4.3 yang bisa melanggar batas ini.** `DROP` hanya mengurangi.

Satu-satunya kehati-hatian adalah pembulatan: `BY_SCALE` dan re-bucket proporsional harus memakai
metode **sisa terbesar (largest remainder)** agar jumlah 2 desimal persis terjaga, bukan pembulatan
per baris yang bisa menggeser total.

### 4.6 Penyaringan opsi menurut bentuk perubahan

Menampilkan lima opsi setiap saat adalah beban kognitif yang tidak perlu; sebagian besar perubahan
hanya punya satu jawaban benar.

| Bentuk perubahan | Opsi yang ditawarkan | Default |
|---|---|---|
| Tanggal selesai diperpanjang | — (tidak ada konflik) | Simpan langsung, tanpa dialog |
| Tanggal selesai diperpendek, minggu terbuang kosong | — | Simpan langsung, baris kosong dibersihkan |
| Tanggal selesai diperpendek, ada planned di minggu terbuang | Padatkan ke minggu terakhir / Ikuti kalender (hapus) | Padatkan |
| Tanggal mulai bergeser, durasi sama | Pertahankan urutan minggu / Ikuti kalender | Pertahankan urutan |
| Tanggal mulai bergeser, durasi berubah | Keempat opsi | Pertahankan urutan (N-A) atau Padatkan proporsional (N-B) |
| Ada realisasi di luar jendela baru, niat N-B | Hanya "Batalkan" + petunjuk membereskan realisasi | — |

`allowed_resolutions` dan `recommended_resolution` di payload preview (§6) adalah implementasi
tabel ini; UI tidak boleh menghitungnya sendiri.

### 4.7 Definisi presisi "minggu terganggu"

Sebuah baris dianggap terganggu bila rentang tanggalnya **tidak sepenuhnya** berada di dalam jendela
baru: `week_start_date < new_start OR week_end_date > new_end`. Ini persis `_affected_filter`
(`timeline_utils.py:66`) yang sudah dipakai hari ini, jadi tidak ada semantik baru yang perlu dipelajari.

Kasus yang perlu ditangani eksplisit: bila tanggal mulai bergeser, batas minggu **di-slice ulang**,
sehingga baris yang "aman" pun bisa tidak lagi sejajar dengan bucket baru. Untuk `BY_DATE`, baris
seperti ini dibagi ke bucket baru **secara proporsional berdasarkan jumlah hari tumpang tindih** —
pola yang sudah ada dan terbukti di `get_weekly_progress_for_monthly_view`
(`progress_utils.py:133-176`), bukan mekanisme baru.

### 4.8 Reversibilitas

`ACCUMULATE_EDGE`, `BY_SCALE`, dan `DROP` tidak dapat dipulihkan dari data hasil. Audit karena itu
wajib menyimpan **snapshot penuh** setiap baris yang dimutasi (`week_number`, kedua tanggal,
`planned_proportion`, `actual_proportion`, `actual_cost`) — bukan hanya nilai planned lama seperti
`trimmed_planned` hari ini. Dengan itu pemulihan manual selalu mungkin, dan opsi "Undo" dapat
ditambahkan belakangan tanpa perubahan skema.

---

## 5. Desain UX: tiga pintu masuk, satu dialog

```
        ┌──────────────────────┐   ┌──────────────────────┐   ┌───────────────────────┐
        │ Edit project tunggal │   │      Mass edit       │   │ Jadwal: timeline_stale│
        └──────────┬───────────┘   └──────────┬───────────┘   └───────────┬───────────┘
                   │                          │                           │
                   └──────────────┬───────────┴───────────────────────────┘
                                  ▼
                 ┌────────────────────────────────────────────┐
                 │  LANGKAH 1 — NIAT (§4.1)                   │
                 │  ( ) Koreksi: tanggal lama memang salah    │
                 │  ( ) Pergeseran: jadwal proyek berubah     │
                 └────────────────────┬───────────────────────┘
                                      ▼
           POST timeline/preview (intent) → analyze_project_timeline_change
                                      ▼
                 ┌────────────────────────────────────────────┐
                 │  LANGKAH 2 — DIALOG DAMPAK (dipakai 3x)    │
                 │  • jendela lama → baru                     │
                 │  • jumlah minggu lama → baru               │
                 │  • tabel per-minggu: nilai lama → baru     │
                 │  • total planned sebelum → sesudah         │
                 │  • baris actual ditandai "tidak digeser"   │
                 │  • HANYA opsi yang sah untuk niat + bentuk │
                 │    perubahan ini (§4.6), default ditandai  │
                 └────────────────────┬───────────────────────┘
                                      ▼
              POST timeline/commit (intent + resolution + schedule_revision)
                                      ▼
                   apply_project_timeline_change → audit → regenerate → invalidate
```

**Perubahan pada tombol "Perbarui Struktur Waktu":**
tidak lagi ditampilkan permanen di toolbar utama. Muncul sebagai alert kondisional di halaman
**hanya bila `readiness.timeline_stale == true`**, dan klik-nya membuka dialog dampak yang sama
(preview dulu), bukan langsung memutasi. Di kondisi sehat user tidak pernah melihatnya.

**Perubahan pada mass edit:** sebelum menyimpan, tampilkan ringkasan dampak agregat per project
("3 project aman, 1 project memerlukan keputusan"). Project yang tidak aman **tidak ikut tersimpan**
sampai diselesaikan satu per satu lewat form tunggal. Ini menutup T-01 dan T-02 sekaligus tanpa
membangun dialog per-baris di grid mass edit.

---

## 6. Kontrak API

Memakai dua endpoint yang sudah ada, dengan penambahan field. Tidak ada endpoint baru.

**`POST /detail_project/api/v2/project/<id>/timeline/preview/`**

```jsonc
// request
{ "tanggal_mulai": "2026-02-01", "tanggal_selesai": "2026-05-31",
  "intent": "correction",                // BARU: "correction" | "reschedule" (§4.1)
  "resolution": "keep_ordinal",          // BARU: preview per-resolusi; opsional saat menjajaki
  "schedule_revision": 12 }

// response — field baru ditandai (+)
{ "ok": true, "impact": {
    "safe": false, "start_changed": true, "end_changed": true,
    "planned_records": 14, "actual_records": 3,
    "affected_week_numbers": [9, 10, 11],
    "new_week_count": 18,
    "start_requires_policy": false,                    // (+) tidak lagi buntu bila intent+resolution sah
    "allowed_resolutions": ["keep_ordinal", "follow_date", "accumulate_edge"],  // (+) hasil §4.6
    "recommended_resolution": "keep_ordinal",          // (+)
    "blocking_reason": null,                           // (+) null | "actual_out_of_window"
    "total_planned_before": "100.00",                  // (+) supaya user lihat total terjaga
    "total_planned_after": "100.00",                   // (+)
    "week_diff": [                                     // (+) inti dialog dampak
      { "pekerjaan_id": 1101,
        "week_number_old": 9, "week_number_new": 5,
        "week_start_old": "2026-03-02", "week_start_new": "2026-03-02",
        "planned_old": "12.50", "planned_new": "12.50",
        "actual_old": "0.00", "actual_new": "0.00",
        "disposition": "moved" }                       // moved|accumulated|scaled|dropped|unchanged
    ]
  },
  "schedule_revision": 12 }
```

**`POST .../timeline/commit/`** — sama seperti hari ini, ditambah `intent`, dengan `resolution`
diperluas menjadi `none | keep_ordinal | follow_date | accumulate_edge | scale_proportional |
trim_planned | reset_all`. Server **menghitung ulang** dampak sebelum commit (sudah jadi perilaku
sekarang) dan **menolak kombinasi `intent` × `resolution` yang tidak ada di `allowed_resolutions`**,
sehingga preview tidak bisa dipakai untuk menyelundupkan resolusi yang tidak sah — termasuk
memindahkan realisasi dengan berpura-pura `intent="correction"` tanpa user menyatakannya.
`schedule_revision` tetap wajib.

**Kompatibilitas:** `resolution: "none"` dan `"trim_planned"` mempertahankan arti persis seperti
sekarang, sehingga `tests_timeline_crud_hardening.py` harus tetap hijau tanpa diubah. Itu gate WP-T1.
`intent` bersifat opsional pada jalur lama dan default ke `reschedule` (perilaku paling konservatif:
realisasi tidak pernah bergerak).

---

## 7. Model Data

Tidak ada migrasi skema pada `PekerjaanProgressWeekly`. Resolusi bekerja dengan meng-`update`
`week_number` + `week_start_date` + `week_end_date` pada baris yang ada.

Satu pertimbangan yang harus diuji lebih dulu (WP-T1): `unique_together = ('pekerjaan', 'week_number')`
membuat pergeseran ordinal berisiko bentrok UNIQUE di tengah operasi. Gunakan **pola dua fase** yang
sudah terbukti di proyek ini pada `rollback_parameters_from_opaque` (prefix sementara → nilai final):
geser ke rentang `week_number` sementara di luar jangkauan (mis. `+10000`), lalu turunkan ke nilai final.
Seluruhnya di dalam `transaction.atomic` yang sudah membungkus `apply_project_timeline_change`.

---

## 8. Work Package

Setiap WP = satu commit, satu gate test. **Jangan digabung** — pelajaran dari WP Export (doc 30 §8).

### WP-T0 — Contract freeze
Tambah test yang mengunci perilaku **saat ini** sebelum apa pun diubah: mass edit menghapus progress
(T-01), `tanggal_selesai` tidak memicu rebuild (T-02), start+progress ditolak (T-03).
Test ini sengaja mendokumentasikan bug; diubah menjadi test perilaku baru di WP masing-masing.
**Gate:** `tests_timeline_crud_hardening.py` + test baru hijau.

### WP-T1 — Mesin resolusi (pure, tanpa UI)
Implementasi model dua sumbu §4.2 di `timeline_utils.py`: pemetaan `keep_ordinal` / `follow_date` /
`scale_proportional`, kebijakan sisa `accumulate_edge` / `drop` / `block`, gerbang `intent`
(§4.1), aturan realisasi §4.4, pembulatan largest-remainder §4.5, dan pola dua fase UNIQUE.
`analyze_project_timeline_change` mengembalikan `week_diff`, `allowed_resolutions`,
`recommended_resolution`, `blocking_reason`, `total_planned_before/after`.
Tabel penyaringan §4.6 hidup di sini, bukan di UI.
Termasuk **penuntasan baris di luar jendela (T-06)**: setiap resolusi wajib menetapkan nasib baris
tersebut (digeser / dijangkar / dihapus), sehingga `timeline_stale` bernilai `false` setelah commit
yang sukses.
**Gate:** unit test matriks resolusi (geser maju/mundur, durasi berubah, actual di dalam/di luar
jendela, proyek kosong, minggu parsial di awal/akhir) + assert `timeline_stale == False` dan jumlah
kolom chart == `expected_week_count` setelah setiap resolusi + 11 test lama tetap hijau tanpa diubah.

### WP-T2 — Satukan jalur tulis (enam jalur, bukan tiga)
`views_mass_edit.py` berhenti memanggil `reset_project_progress`; memakai
`analyze_project_timeline_change` untuk memisahkan project aman vs perlu-keputusan, dan
`apply_project_timeline_change` untuk yang aman. Tangani `tanggal_selesai` (T-02).

Termasuk jalur §2.4: kunci field timeline di `ProjectAdmin` menjadi read-only atau arahkan ke service
(G-1); rutekan perubahan tanggal pada duplikat lewat service yang sama dan perbaiki inkonsistensi
salin canonical vs turunan (G-2); jadikan perubahan batas minggu memakai preview/commit yang sama
(G-3); bersihkan/tinjau tahapan manual di luar jendela (G-4); kirim `expected_revision` dari
`project_edit` (G-5).
**Gate:** test T-01/T-02 dari WP-T0 dibalik menjadi test perilaku baru; tidak ada progress terhapus
tanpa resolusi eksplisit.

### WP-T3 — Dialog dampak di dashboard
Perluas blok `project_form.html:41-70` menjadi komponen dampak penuh dengan tabel `week_diff` dan
pemilihan resolusi. Sambungkan mass edit ke ringkasan agregat.
**Gate:** test view (POST tanpa resolusi → form error + impact ter-render; POST dengan resolusi →
tersimpan) + smoke render.

### WP-T4 — Jadwal: tombol menjadi perbaikan terpandu
Konsumsi `readiness.timeline_stale` di context halaman Jadwal. Tombol keluar dari toolbar utama →
alert kondisional. Klik memanggil `timeline/preview` dan menampilkan dialog yang sama; commit lewat
`timeline/commit`. `api_regenerate_tahapan_v2` tetap ada sebagai primitive internal.
**Gate:** test bahwa tombol/alert tidak ter-render saat `timeline_stale=false`; test bahwa jalur
regenerate buta tidak lagi terpasang di UI.

### WP-T5 — Perbaikan efek samping regenerate (T-05)
Tiga perbaikan kecil dari investigasi sesi ini: pindahkan `loadAssignments` ke setelah
`timeColumnGenerator.generate()`; panggil `stateManager.invalidateChartCache()` di
`regenerateTimeline`; beri warning bila `_applyAssignmentsData` memetakan 0 dari >0 assignment.
**Gate:** unit test JS / test manual terdokumentasi bahwa jumlah assignment ter-map == jumlah yang
diterima API.

### WP-T6 — Dokumentasi & observability
Update `docs/PANDUAN_USER.md` (apa arti tiap resolusi bagi user), catat di doc 28 tracker, dan
tambahkan log terstruktur pada setiap commit resolusi.

**Urutan wajib:** T0 → T1 → T2 → T3 → T4 → T5 → T6. T5 boleh didahulukan bila ingin cepat menghilangkan
gejala visual, tetapi tidak boleh menggantikan T1-T4.

---

## 9. Matriks Test

**Invariant lintas-skenario (di-assert di setiap test yang commit-nya sukses):**
`timeline_stale == false`; jumlah kolom chart == jumlah minggu jendela baru; tidak ada baris di luar
jendela; total planned per pekerjaan ≤ 100%; audit berisi snapshot penuh baris yang dimutasi.

| # | Skenario | Niat | Resolusi | Ekspektasi |
|---|---|---|---|---|
| 1 | Proyek tanpa progress, tanggal berubah | — | `none` | Rebuild senyap, tidak ada dialog |
| 2 | Selesai diperpanjang, progress ada | — | `none` | Tersimpan langsung; nilai utuh; minggu baru kosong |
| 3 | Mulai mundur 7 hari, durasi tetap, hanya planned | koreksi | `keep_ordinal` | Semua nilai utuh, `week_number` tetap, hanya tanggal bergeser |
| 4 | Sama seperti #3, ada actual di W2 | **koreksi** | `keep_ordinal` | Planned **dan** actual ikut bergeser (tanggal lama memang salah); audit mencatat alasan |
| 5 | Sama seperti #3, ada actual di W2 | **pergeseran** | `keep_ordinal` | Planned bergeser, actual **tidak**; bila actual jatuh di luar jendela → ditolak |
| 6 | Mulai maju, actual jatuh sebelum jendela baru | pergeseran | apa pun | **Ditolak**, `blocking_reason = actual_out_of_window`, menyebut minggu bermasalah |
| 7 | Selesai dimajukan, planned di minggu terakhir | pergeseran | `trim_planned` | Persis perilaku hari ini (regresi `test_timeline_trim_planned_preserves_actual_contract`) **plus** invariant T-06 |
| 8 | Mulai 01/01→01/03, planned 10% di W1 lama | pergeseran | `accumulate_edge` | Seluruh planned dari 01/01–28/02 menumpuk di minggu pertama jendela baru; **total sebelum == total sesudah** |
| 9 | Sama seperti #8 | pergeseran | `follow_date` | Baris ≥ 08/03 tidak tersentuh; baris < 01/03 dihapus; total berkurang sesuai yang dibuang |
| 10 | Durasi 12 minggu → 8 minggu, lingkup sama | pergeseran | `scale_proportional` | Kurva dipadatkan; total terjaga persis 2 desimal (largest remainder); tidak ada sisa di luar |
| 11 | Bucket lama tidak sejajar bucket baru | pergeseran | `follow_date` | Nilai dibagi proporsional per hari tumpang tindih; jumlah terjaga |
| 12 | Akumulasi dari 8 minggu × 12.5% ke satu minggu | pergeseran | `accumulate_edge` | Hasil 100.00% — **tidak** melanggar batas per baris maupun total (§4.5) |
| 13 | Kombinasi `intent` × `resolution` di luar `allowed_resolutions` | — | ilegal | Commit ditolak 400 meski preview mengembalikannya |
| 14 | Mass edit 4 project, 1 tidak aman | — | — | 3 tersimpan, 1 dilaporkan dan **tidak** tersimpan; tidak ada progress terhapus |
| 15 | `schedule_revision` basi | — | apa pun | 409, tidak ada mutasi |
| 16 | Pergeseran menabrak UNIQUE `(pekerjaan, week_number)` | — | `keep_ordinal` | Sukses lewat pola dua fase |
| 17 | `timeline_stale=false` | — | — | Alert perbaikan tidak muncul di Jadwal |

---

## 10. Risiko

| Risiko | Mitigasi |
|---|---|
| Pergeseran ordinal menabrak UNIQUE | Pola dua fase dalam satu transaksi (§7); test khusus |
| Proyek besar → update massal lambat | `bulk_update` berbasis `week_number`; ukur pada proyek terbesar sebelum WP-T2 ditutup |
| User salah pilih resolusi | Preview wajib menampilkan `week_diff` konkret; `RESET_ALL` tidak pernah jadi default; audit memungkinkan forensik |
| Regresi pada jalur P1 yang sudah matang | WP-T1 mensyaratkan 11 test lama hijau **tanpa dimodifikasi** |
| Scope creep ke bug monthly / doc 36 | Dinyatakan non-goal di header |

**Rollback:** setiap WP satu commit terisolasi. WP-T1 murni aditif (resolusi baru), WP-T2 yang mengubah
perilaku destruktif — bila bermasalah, revert T2 mengembalikan mass edit ke perilaku lama tanpa
menyentuh T1.

---

## 11. Yang TIDAK dikerjakan di sini

- Bug `month_number` hilang di `_build_monthly_columns` (`jadwal_pekerjaan_adapter.py`) yang membuat
  Kurva S/Gantt monthly kosong — **temuan terpisah, layak doc/issue sendiri**.
- Sync over-notification (doc 36).
- Legacy `api_regenerate_tahapan` v1 dan mode `daily`/`custom` — masuk Fase-3 cleanup (doc 25).

---

## 12. Keputusan yang Menunggu Owner

| # | Keputusan | Rekomendasi |
|---|---|---|
| **K-1** | Apakah langkah "niat" (koreksi vs pergeseran, §4.1) dipakai sebagai gerbang pertama dialog | **Ya.** Ini satu-satunya cara sah membuka kunci T-03 tanpa mengizinkan realisasi berpindah diam-diam |
| **K-2** | Resolusi default saat tanggal mulai bergeser dan durasi tetap | `keep_ordinal` (lossless; benar untuk koreksi maupun proyek diundur utuh) |
| **K-3** | Resolusi default saat durasi berubah | Niat koreksi → `keep_ordinal`; niat pergeseran → `scale_proportional` |
| **K-4** | Apakah `scale_proportional` masuk lingkup rilis pertama atau ditunda | Masuk — ia yang menutup kasus "durasi berubah, lingkup sama" yang ditangani canggung oleh tiga opsi lain |
| **K-5** | Apakah `reset_all` tetap ditawarkan di UI, atau dihapus sama sekali | Tetap ditawarkan, tidak pernah default, butuh konfirmasi kedua |
| **K-6** | Mass edit: blokir project yang tidak aman (rekomendasi) atau sediakan dialog per-project di grid | Blokir — jauh lebih murah dan menutup T-01/T-02 sepenuhnya |
| **K-7** | Apakah WP-T5 didahulukan sebagai quick win visual | Boleh, asalkan tidak menunda T1-T4 |
| **K-8** | G-1: field timeline di Django admin dijadikan read-only, atau tetap editable dengan peringatan | Read-only — admin bukan tempat yang tepat untuk operasi yang butuh dialog dampak |
| **K-9** | G-2: apakah duplikat project seharusnya ikut menyalin progress (canonical), atau justru tidak menyalin `PekerjaanTahapan` juga | Salin keduanya atau tidak sama sekali; keadaan sekarang (turunan tanpa canonical) tidak konsisten dan akan terhapus sendiri saat sync pertama |
| **K-10** | G-3: apakah perubahan batas minggu memakai dialog dampak yang sama, atau cukup dikunci saat sudah ada realisasi | Dialog yang sama — konsekuensinya sekelas perubahan tanggal |

Eksekusi menunggu K-1 s/d K-6, ditambah K-8 s/d K-10 sebelum WP-T2 ditutup.
