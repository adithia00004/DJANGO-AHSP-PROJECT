# 36 — Audit & Implementation Plan: Over-Notifikasi Sinkronisasi Lintas Halaman

**Tanggal:** 2026-08-24
**Pemicu:** Keluhan owner — "setiap perubahan di List Pekerjaan / Volume Pekerjaan / Harga Items membuat Template AHSP meminta reload semua pekerjaan."
**Metode:** Pembacaan kode + sweep repo-wide produsen/konsumen sinyal sinkronisasi (bukan temuan per-halaman — mengikuti pelajaran UF-013/AT-01 dan checklist Cross-Cutting doc 26).
**Status dokumen:** **FASE 1 + FASE 4b SELESAI & HIJAU (2026-08-24), terverifikasi di Docker/PostgreSQL. Fase 2, 3, 4a, 4c belum dieksekusi.**
**Prioritas:** P0 untuk SYN-01; P1 untuk SYN-02/03/04; P2 untuk SYN-05/06.

---

## 1. Ringkasan Eksekutif

Template AHSP punya **dua jalur sinyal "data berubah" yang terpisah**, dan keduanya
tersulut jauh lebih luas daripada perubahan yang sebenarnya terjadi:

| Jalur | Wujud di UI | Sumber kebenaran |
|---|---|---|
| Flag `pending_reload_job_ids` | Badge per-baris "Detail perlu dimuat ulang" + banner "N pekerjaan memiliki perubahan sumber…" | `ProjectChangeStatus` (server) + mirror `localStorage` |
| Sync LED | Banner "Ada perubahan data terbaru dari halaman lain" + klik LED = reload | Endpoint `change-status` (polling 30 detik) |

**Akar masalah utama (SYN-01):** endpoint upsert List Pekerjaan menandai **setiap
pekerjaan yang ada di payload** sebagai "perlu reload", bukan hanya yang benar-benar
berganti sumber. Karena halaman List Pekerjaan selalu mengirim **seluruh pohon** setiap
kali Simpan, satu kali ganti nama klasifikasi = seluruh pekerjaan di proyek tertandai.

**Koreksi terhadap premis keluhan:** menyimpan **Volume Pekerjaan bukan pemicu langsung**.
Endpoint volume tidak menyentuh apa pun yang diawasi Template AHSP. Yang terjadi adalah
flag sisa dari save List Pekerjaan sebelumnya yang **tidak pernah bersih**, lalu
di-rehidrasi ke `localStorage` oleh polling LED yang berjalan di semua halaman (SYN-05).
Perbaikan SYN-01 + SYN-05 menutup gejala yang dirasakan di halaman Volume.

**Dampak yang mungkin belum disadari:** over-flag ini juga **mengunci form input Harga
Items** (`harga_items.js:151`), karena halaman itu menolak input selama masih ada
pekerjaan Template yang belum dimuat ulang.

---

## 2. Baseline Terverifikasi (sweep repo-wide, 2026-08-24)

### 2.1 Produsen flag `pending_reload_job_ids`

| Lokasi | Kondisi | Benar? |
|---|---|---|
| `views_api.py:1241` (`_adopt_tmp_into`) | Hanya jalur replace REF/REF_MOD | Ya |
| `views_api.py:1472` | **Tanpa syarat, semua pekerjaan existing di payload** | **TIDAK — SYN-01** |
| `views_api.py:1579` | Pekerjaan baru dibuat | Ya |

Titik persist tunggal: `views_api.py:1706` -> `register_source_change_flags()`.
**Tidak ada produsen lain di repo.** Volume, Harga, Rincian, Jadwal, Rekap tidak pernah
memproduksi flag ini.

### 2.2 Konsumen flag

| Halaman | File | Perilaku |
|---|---|---|
| Template AHSP | `template_ahsp.js:1675` | Badge + banner + target reload massal |
| Volume Pekerjaan | `volume_pekerjaan.js:815` | Hanya baca section `volume`, abaikan `reload` |
| Harga Items | `harga_items.js:164` | **Mengunci form harga** bila `reload` tidak kosong |
| Rincian AHSP | `rincian_ahsp.js:771` | Buang `cacheDetail` + toast "N pekerjaan terpengaruh" |

### 2.3 Pembersih flag

| Lokasi | Cakupan |
|---|---|
| `views_api.py:1985` (save Volume) | **Hanya** `volume_reset_job_ids` |
| `views_api.py:5313` (`api_ack_source_change_flags`) | Sesuai payload ack |
| `template_ahsp.js:1402` (`resolveReloadJob`) | Satu job, saat dibuka user |
| `template_ahsp.js:1303` / `rincian_ahsp.js:788` | Prune job yang tidak lagi dirender |

**Tidak ada jalur "bersihkan semua".** Flag hanya susut satu per satu.

### 2.4 Konfigurasi Sync LED (7 halaman)

| Halaman | `scope` | `watch` | Catatan |
|---|---|---|---|
| Template AHSP | `template` | `pekerjaan,harga` | **SYN-03** — halaman ini eksplisit *"tanpa kolom harga"* (`template_ahsp.html:770`) |
| Harga Items | `harga` | `ahsp` | wajar |
| Rincian AHSP | `rincian` | `ahsp,harga` | wajar |
| Volume Pekerjaan | `volume` | `pekerjaan` | wajar |
| Jadwal | `jadwal` | `pekerjaan,volume,jadwal` | wajar |
| Rekap RAB | `rekap_rab` | `pekerjaan,volume,ahsp,harga` | wajar (halaman turunan) |
| Rekap Kebutuhan | `rekap_kebutuhan` | `pekerjaan,volume,ahsp,harga` | wajar (halaman turunan) |

Ketujuh view mengirim `_get_sync_initial_timestamps()` (`views.py:42`) — tidak ada celah
initial-timestamp.

### 2.5 Basis timestamp `change-status`

| Sinyal | Basis | Ketepatan |
|---|---|---|
| `ahsp_changed_at` | `ProjectChangeStatus.last_ahsp_change` | tepat |
| `harga_changed_at` | `ProjectChangeStatus.last_harga_change` | tepat |
| `pekerjaan_changed_at` | `MAX(Pekerjaan.updated_at)` se-proyek (`views_api.py:5227`) | **TIDAK — SYN-02** |
| `volume_changed_at` | `MAX(VolumePekerjaan.updated_at)` | tepat |
| `jadwal_changed_at` | `MAX` atas Tahapan/PekerjaanTahapan/ProgressWeekly | tepat |

`Pekerjaan.updated_at` = `auto_now` (`models.py:31`). Sweep `.save()` atas instance
`Pekerjaan` menunjukkan **satu-satunya penulis adalah jalur upsert List Pekerjaan**
(baris 1125, 1197, 1229, 1442, 1468, 1530, 1557). Jalur Template/Harga/Volume memakai
`Pekerjaan.objects.filter(...).update(...)` yang **melewati** `auto_now` — jadi mereka
tidak mencemari sinyal ini. Masalahnya ada di dalam jalur List Pekerjaan sendiri.

---

## 3. Temuan

### SYN-01 — P0 — Flag reload dipasang untuk semua pekerjaan, bukan yang berubah sumber

**Bukti:** `detail_project/views_api.py:1472`

```python
                    else:
                        # Update biasa
                        pobj.ordering_index = final_order
                        pobj.sub_klasifikasi = s_obj
                        ...
                        pobj.save(update_fields=[...])

                    source_change_state["reload_jobs"].add(pobj.id)   # <- 20 spasi
```

Indentasi 20 spasi menempatkannya **sejajar dengan `if replace:` / `else:`**, bukan di
dalamnya. Akibatnya cabang "Update biasa" (murni reorder / rename / pindah sub) ikut
menandai baris tersebut.

Diperparah oleh `list_pekerjaan.js:1723` `collectTree()` yang mengirim seluruh pohon pada
setiap Simpan — tidak ada diffing sisi klien.

**Kontradiksi dengan UI-nya sendiri:** teks badge di `template_ahsp.js:1337` berbunyi
*"Sumber pekerjaan berubah di List Pekerjaan"*, padahal mayoritas baris yang ditandai
tidak mengalami perubahan sumber apa pun.

**Reproduksi:** buka List Pekerjaan -> ubah nama satu klasifikasi -> Simpan -> buka
Template AHSP. Banner melaporkan jumlah = seluruh pekerjaan proyek. Form Harga Items ikut
terkunci.

**SSOT keputusan sudah tersedia:** variabel `replace` (= `_is_reset_change()`,
`views_api.py:642`), dipakai bersama oleh upsert dan preview destructive-impact N2.

---

### SYN-02 — P1 — `pekerjaan_changed_at` naik walau tidak ada perubahan

Dua sumber bump palsu di jalur upsert:

1. **Two-phase reorder** (`views_api.py:1122-1125`): seluruh pekerjaan proyek digeser ke
   `ordering_index` sementara (1.000.001…) memakai `pobj.save()` — instance save,
   `auto_now` aktif. Tahap ini **wajib** karena `Pekerjaan` punya
   `unique_together = ("project", "ordering_index")` (`models.py:145`), tetapi
   bookkeeping transien ini tidak seharusnya terbaca sebagai "pekerjaan berubah".
2. **Cabang "Update biasa"** (`views_api.py:1468`): setiap baris di payload ditulis ulang
   tanpa dirty-check, termasuk saat seluruh nilainya identik.

Karena `pekerjaan_changed_at = MAX(Pekerjaan.updated_at)`, LED bertanda `pekerjaan`
(Template AHSP, Volume, Jadwal, Rekap RAB, Rekap Kebutuhan) **pasti** menyala setelah
save List Pekerjaan apa pun — termasuk save tanpa perubahan.

**Efek samping kedua:** `_detail_ahsp_version()` (`views_api.py:2055`) memakai
`detail_last_modified or updated_at`. Untuk pekerjaan yang belum pernah punya detail
tersimpan, versinya ikut bergeser -> prompt "Data pekerjaan ini telah berubah sejak
terakhir dimuat" (`template_ahsp.js:1965`) bisa muncul palsu.

---

### SYN-03 — P1 — Template AHSP mengawasi `harga` padahal tidak menampilkan harga

`template_ahsp.html:4` -> `watch="pekerjaan,harga"`.
`template_ahsp.html:770` -> *"Kelola komponen AHSP per pekerjaan **tanpa kolom harga**."*

Setiap simpan di Harga Items memanggil `touch_project_change(project, harga=True)`
(`views_api.py:3563`) -> LED Template menyala -> `changeStatusPending = true`
(`template_ahsp.js:1691`) -> banner muncul. Tidak ada satu pun data di layar Template AHSP
yang berubah karenanya.

---

### SYN-04 — P1 — Pemicu LED tidak berkorelasi dengan target reload

`template_ahsp.js:1705-1707`:

```js
const targets = pendingReloadJobs.size
  ? Array.from(pendingReloadJobs)
  : (activeJobId ? [activeJobId] : []);
```

Handler `dp:sync-refresh-request` mengabaikan **apa** yang berubah dan langsung me-reload
**seluruh** isi `pendingReloadJobs`. Jadi LED yang menyala karena perubahan *harga*
memicu reload massal berdasarkan flag yang berasal dari save *List Pekerjaan*.

**Catatan sejarah:** TA-17/CL-08 (doc 18 bagian 16, doc 25) sudah menghapus
`scheduleAutoReloadPendingJobs` (auto-reload massal saat page-open), dan UF-010/WP-P2d
memindahkan resolusi ke jalur lazy. Jalur `dp:sync-refresh-request` **terlewat** dari
pembersihan itu — reload massal masih hidup di sini, hanya berpindah pemicu dari
page-open ke klik LED.

---

### SYN-05 — P2 — Flag lengket dan terus dire-hidrasi

- Tidak ada jalur pembersihan massal (lihat bagian 2.3).
- `sync_led.js:214` memanggil `syncFlags()` pada **setiap** halaman, setiap 30 detik,
  menulis ulang `localStorage` dari state server.
- `template_ahsp.js:178` menginisialisasi `pendingReloadJobs` dari `localStorage` saat load.

Konsekuensi: flag yang salah dipasang (SYN-01) bertahan lintas sesi dan lintas halaman.
Inilah mengapa bekerja di halaman Volume terasa "menyebabkan" Template minta reload —
padahal halaman Volume hanya me-rehidrasi flag lama.

Selaras dengan prinsip **A-11** (doc 26): `localStorage` = draft cache, tidak boleh
memblok data server. Saat A-11 disusun, `source_change_state` dinilai *"flag awareness,
risiko rendah"* — penilaian itu benar untuk mekanismenya, tetapi tidak mengantisipasi
produsen flag yang over-broad.

---

### SYN-06 — P2 — Kebijakan kunci Harga Items terlalu keras

`harga_items.js:149-159`:

```js
const templatePending = pendingTemplateReloadJobs.size;
const locked = templatePending > 0 || changeStatusPending;
```

Seluruh input harga di-disable selama masih ada flag Template. Setelah SYN-01 diperbaiki
kondisi ini jarang terpicu, tetapi kebijakannya sendiri perlu ditinjau: memblokir
pengeditan harga karena komposisi AHSP pekerjaan lain berubah adalah coupling yang jauh
lebih ketat daripada yang dibutuhkan, dan bertentangan dengan semangat **B-1**
(last-write-wins, tanpa dialog konflik/locking).

---

## 4. Relasi dengan Keputusan yang Sudah Terkunci

| Referensi | Relevansi |
|---|---|
| **B-1** (doc 26) — last-write-wins, tanpa 409/locking | SYN-06 (kunci form) dan SYN-02 (versi palsu) berlawanan arah dengan ini |
| **A-11** (doc 26) — server-authoritative saat load | SYN-05 memperluas cakupan A-11 ke `source_change_state` |
| **TA-17 / CL-08** — hapus trigger reload massal | SYN-04 = sisa jalur yang terlewat |
| **UF-010 / WP-P2d** — lazy reload Template | Utuh dan benar; SYN-01 memasok input yang salah ke jalur yang benar |
| **LP-05 / CL-05** — pensiun legacy full-save List Pekerjaan | Bila full-tree save dipensiunkan, SYN-01 hilang sendirinya; namun jangan menunggu itu |

Tidak ada test yang mengunci perilaku over-flag saat ini
(`grep change_flags|reload_job_ids` pada `tests_*.py` -> hanya `tests_change_status_sync.py`
yang menguji prune-id-terhapus dan `tests_formula_ui_regressions.py` untuk bentuk payload).
**Perbaikan tidak akan menabrak test yang ada.**

---

## 5. Implementation Plan

### Prinsip

1. **Satu fase = satu commit = satu gate.** Jangan campur backend dan frontend.
2. **Perbaiki produsen sebelum konsumen.** SYN-01 memasok input ke semua gejala lain.
3. **Test-first pada setiap fase**; tidak lanjut bila gate merah.
4. Tidak ada migrasi skema, tidak ada perubahan data.

### Fase 1 — SYN-01: persempit flag ke perubahan sumber (P0) — **SELESAI 2026-08-24**

**Perubahan:** `detail_project/views_api.py:1472` — gate pada `replace`.

```python
                    if replace:
                        source_change_state["reload_jobs"].add(pobj.id)
```

Cakupan tetap benar untuk kedua sub-cabang replace:
- REF/REF_MOD -> `_adopt_tmp_into` sudah menambah flag (baris 1241); `set` membuat ini idempoten.
- -> CUSTOM (in-place) -> sebelumnya **tidak** ter-flag lewat jalur mana pun; gate ini menutup celah itu.

**Test baru:** `detail_project/tests_list_pekerjaan_reload_flag_scope.py`

| ID | Skenario | Ekspektasi |
|---|---|---|
| F1 | Save ulang pohon identik | `reload_job_ids == []` |
| F2 | Rename klasifikasi saja | `reload_job_ids == []` |
| F3 | Reorder pekerjaan saja | `reload_job_ids == []` |
| F4 | Pindah pekerjaan antar-sub | `reload_job_ids == []` |
| F5 | Ganti `ref_id` satu pekerjaan | hanya id itu |
| F6 | Ganti `source_type` ref->custom | hanya id itu |
| F7 | Tambah pekerjaan baru | hanya id baru |
| F8 | `ProjectChangeStatus.pending_reload_job_ids` setelah 3x save non-destruktif | tetap `[]` |

**Gate — HASIL EKSEKUSI 2026-08-24:**

| Suite | Hasil |
|---|---|
| `tests_list_pekerjaan_reload_flag_scope.py` (F1–F8 + F8b) | **9 passed** |
| 8 suite `tests_list_pekerjaan_*.py` + `tests_wp_p4_list_pekerjaan.py` + `tests_change_status_sync.py` | **47 passed** |
| Template AHSP + Harga + Volume + Rincian + WP-B7 (9 suite lintas-halaman) | **119 passed** |
| `manage.py check --settings=config.settings.test` | bersih (sisa 1 warning Silk/PgBouncer yang sudah ada sebelumnya) |

**Bukti test menjaga perbaikan:** patch dibalik sementara -> **9/9 merah**; dikembalikan
-> 9/9 hijau. Test benar-benar mengunci perilaku, bukan lolos karena kebetulan.

**Rollback:** revert satu commit; tidak ada state persisten yang berubah bentuk.

**Catatan operasional:** flag lama yang sudah telanjur tersimpan di
`ProjectChangeStatus.pending_reload_job_ids` **tidak** ikut bersih. Butuh Fase 4b atau
pembersihan manual satu kali.

**Temuan tambahan saat eksekusi (SYN-07, INFO):** field `change_flags` pada response
upsert melaporkan **set pending KUMULATIF** milik proyek (hasil merge di
`register_source_change_flags`, `services.py:1050`), bukan delta save tersebut. Jadi
`pushFlags` di klien selalu menerima seluruh set yang masih menggantung — konsisten dan
tidak salah, tetapi berarti response TIDAK bisa dibaca sebagai "apa yang berubah barusan".
Fase 4b menjadi lebih penting karenanya: selama flag warisan belum dibersihkan, response
save yang bersih pun tetap membawa set lama. Ini juga sebabnya test F1–F8 harus mengosongkan
tracker setelah seeding untuk bisa mengukur delta.

---

### Fase 2 — SYN-02: hentikan bump `updated_at` palsu (P1)

**2a. Two-phase reorder tanpa `auto_now`** — `views_api.py:1122-1125`:

```python
    for idx, pobj in enumerate(pekerjaan_queryset, start=1):
        pobj.ordering_index = temp_offset + idx          # tetap set di memori
        Pekerjaan.objects.filter(pk=pobj.pk).update(ordering_index=pobj.ordering_index)
```

Profil tabrakan `unique_together` **identik** dengan sekarang (nilai dan urutan penulisan
sama persis); satu-satunya perbedaan adalah `auto_now` tidak ikut.

**2b. Dirty-aware write pada cabang "Update biasa"** — `views_api.py:1455-1470`:

Tangkap state asli **sebelum** pergeseran temp:

```python
    original_state = {
        p.id: (p.ordering_index, p.sub_klasifikasi_id,
               p.snapshot_kode, p.snapshot_uraian, p.snapshot_satuan)
        for p in pekerjaan_queryset
    }
```

Lalu tulis lewat queryset `.update()` dan naikkan `updated_at` **hanya** bila ada beda
nyata terhadap `original_state[pobj.id]`. Penulisan tetap selalu terjadi (baris harus
keluar dari nilai temp) — yang dikendalikan adalah timestamp-nya.

**Test baru:** `detail_project/tests_list_pekerjaan_change_signal.py`

| ID | Skenario | Ekspektasi |
|---|---|---|
| C1 | Save pohon identik | `MAX(Pekerjaan.updated_at)` tidak berubah |
| C2 | Save pohon identik | `change-status.pekerjaan_changed_at` tidak berubah |
| C3 | Rename satu pekerjaan custom | hanya baris itu yang `updated_at`-nya naik |
| C4 | Reorder | hanya baris yang benar-benar berpindah yang naik |
| C5 | `ordering_index` final benar setelah reorder kompleks (tukar posisi, hapus di tengah) | tidak ada `IntegrityError`, urutan sesuai payload |

**Gate:** C1–C5 + seluruh `tests_list_pekerjaan_*.py` + `tests_wp_p4_list_pekerjaan.py`
(termasuk `tests_list_pekerjaan_upsert_drag_drop.py` dan `tests_list_pekerjaan_idmap_n3a.py`)
hijau. Fase ini menyentuh hot path — **wajib** dijalankan di PostgreSQL
(`config.settings.test_pg`), bukan hanya SQLite, karena perilaku unique constraint dan
urutan penulisan berbeda.

**Rollback:** revert commit. Risiko terbesar fase ini = regresi `ordering_index`;
karena itu C5 bersifat blocking.

---

### Fase 3 — SYN-03 + SYN-04: presisi sinyal di sisi klien (P1)

**3a.** `template_ahsp.html:4` -> `watch="pekerjaan"` (buang `harga`).

**3b.** `template_ahsp.js:1705` -> target reload dibatasi ke irisan flag dan baris yang
benar-benar dirender, dan bila tidak ada flag sama sekali cukup segarkan job aktif:

```js
const rendered = renderedJobIds();
const flagged = Array.from(pendingReloadJobs).filter((id) => rendered.has(id));
const targets = flagged.length ? flagged : (activeJobId ? [activeJobId] : []);
```

**Test:** `detail_project/static/detail_project/js/tests/template_ahsp_sync_scope.test.js`

| ID | Skenario | Ekspektasi |
|---|---|---|
| S1 | `dp:change-status` scope `template`, `hasChanges` dari harga | banner tidak muncul |
| S2 | `dp:sync-refresh-request` tanpa flag | hanya job aktif yang di-fetch |
| S3 | `dp:sync-refresh-request` dengan 2 flag dari 50 job | tepat 2 fetch |
| S4 | Flag menunjuk job yang sudah dihapus | tidak ada fetch; flag di-ack |

**Gate:** S1–S4 + `template_ahsp_race_guard.test.js` + `template_ahsp_lain.test.js` +
`tests_wp_p2_template_ahsp.py` + `tests_template_ahsp_ui_regressions.py`.

**Rollback:** revert; murni presentasi/klien.

---

### Fase 4 — SYN-05 + SYN-06: higiene flag & pelonggaran kunci (P2)

**4a.** Tombol "Tandai semua sudah dimuat" di banner Template AHSP -> `markReloaded` untuk
seluruh set (endpoint ack sudah mendukung batch).

**4b — SELESAI 2026-08-24.** Management command
`detail_project/management/commands/clear_stale_reload_flags.py`:

```
python manage.py clear_stale_reload_flags --all --dry-run
python manage.py clear_stale_reload_flags --project-id <id> --yes
```

Mengosongkan `pending_reload_job_ids`; mendukung `--project-id` / `--all`,
`--dry-run`, `--yes`, dan idempoten (run kedua melaporkan "tidak ada flag").

**Keputusan desain:** `pending_volume_reset_job_ids` **TIDAK** ikut dibersihkan kecuali
`--include-volume` diminta eksplisit. Flag volume menandai volume yang benar-benar
di-reset dan masih harus diisi ulang user — menghapusnya diam-diam akan menyembunyikan
pekerjaan bervolume kosong. Dikunci oleh test `test_volume_flags_survive_by_default`.

**Test:** `detail_project/tests_clear_stale_reload_flags.py` — **10 passed** (argumen,
dry-run tidak menulis, cakupan per-project vs `--all`, proteksi flag volume, idempotensi,
project tanpa tracker).

**Eksekusi nyata di DB Docker (PostgreSQL) 2026-08-24:**

```
 - project 195 (Rehabilitasi Screen House/Green House): 63 dari 83 pekerjaan ditandai (76%)
 - project 198 (Villa Batu):                            29 dari 29 pekerjaan ditandai (100%)
Selesai. 2 project dibersihkan; 92 flag reload dikosongkan.
```

Project 198 menandai **100% pekerjaannya** — konfirmasi SYN-01 pada data produksi-dev,
bukan hanya pada test sintetis. Pasca-eksekusi: `reload=[]` untuk keduanya, sementara
`volume` tetap utuh (`[1196, 1197]` dan `[1311, 1312]`).

**4c.** Tinjau `harga_items.js:151`: turunkan dari **lock** menjadi **peringatan
non-blocking**, selaras dengan B-1. *Butuh keputusan owner — bukan perbaikan bug murni.*

**Gate:** `tests_wp_p1_harga_items.py` + `tests_harga_items_save_api.py` + verifikasi
runtime di browser.

---

## 6. Urutan Eksekusi & Ketergantungan

```
Fase 1 (P0, backend)  ---> Fase 4b (bersihkan flag warisan)
   |
   +---> Fase 2 (P1, backend, butuh PG)
   |
   +---> Fase 3 (P1, frontend)   -- independen dari Fase 2
                                    |
                                    +---> Fase 4a / 4c (P2, 4c butuh keputusan owner)
```

Fase 1 sendirian sudah menutup mayoritas keluhan. Fase 3 menutup jalur harga -> Template.
Fase 2 adalah yang paling berisiko dan paling tidak mendesak dari ketiganya.

---

## 7. Risiko

| Risiko | Fase | Mitigasi |
|---|---|---|
| Perubahan sumber yang sah jadi **tidak** ter-flag (regresi diam-diam) | 1 | F5/F6/F7 menguji ketiga jalur flag; `replace` adalah SSOT yang sama dengan preview N2, jadi tidak ada drift |
| `IntegrityError` `unique_together` pada reorder | 2 | C5 blocking + wajib PostgreSQL |
| Harga stale di Template setelah `watch` dipersempit | 3 | Tidak berlaku — halaman ini tidak menampilkan harga (`template_ahsp.html:770`) |
| Flag warisan bertahan pasca-fix | 4b | Pembersihan satu kali; tanpa ini Fase 1 tidak terasa oleh proyek lama |
| Rincian AHSP kehilangan invalidasi cache yang sah | 1 | `rincian_ahsp.js:794` membuang cache untuk job ber-flag; setelah Fase 1 set-nya mengecil tapi tetap benar |

---

## 8. Definition of Done

- [x] Fase 1 F1–F8 hijau (9 passed; 47 + 119 regresi hijau) — **commit belum dibuat**
- [ ] Fase 2 commit + C1–C5 hijau di PostgreSQL
- [ ] Fase 3 commit + S1–S4 hijau
- [x] Fase 4b dijalankan di lingkungan yang punya flag warisan (Docker/PG, 92 flag di 2 project)
- [ ] Verifikasi runtime: rename klasifikasi -> Simpan -> Template AHSP **tanpa** banner
- [ ] Verifikasi runtime: simpan harga -> Template AHSP **tanpa** banner
- [ ] Verifikasi runtime: ganti `ref_id` satu pekerjaan -> **tepat satu** badge
- [ ] Verifikasi runtime: form Harga Items tidak terkunci setelah save List Pekerjaan biasa
- [ ] Keputusan owner untuk 4c dicatat di dokumen ini
