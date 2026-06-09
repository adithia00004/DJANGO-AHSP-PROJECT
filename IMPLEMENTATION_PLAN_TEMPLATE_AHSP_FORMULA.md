# Implementation Plan: Formula Koefisien Template AHSP (Lintas Page dengan Volume)

## 1. Latar Belakang

Parameter dan formula saat ini sudah dipakai pada halaman **Volume Pekerjaan** untuk kalkulasi `quantity`.
Kebutuhan pengembangan: memanfaatkan parameter yang sama untuk membantu kalkulasi `koefisien` pada **Template AHSP**.

## 2. Tujuan

1. Mengaktifkan formula pada kolom `koefisien` di Template AHSP.
2. Menjadikan parameter project (`bp_*`, `cp_*`) sebagai sumber variabel lintas page.
3. Menjaga kompatibilitas penuh dengan alur simpan existing (`koefisien` tetap angka canonical).
4. Menjaga aturan domain:
   - `REF` read-only.
   - `MOD` editable tanpa bundle AHSP.
   - `CUS` editable dengan bundle AHSP.

## 2.1 Tracking Eksekusi (Live)

Status legend:
1. `DONE` = sudah diimplementasi dan lolos verifikasi dasar.
2. `IN PROGRESS` = sudah mulai, belum memenuhi acceptance end-to-end.
3. `PENDING` = belum mulai.

Checklist progress:
1. `DONE` - Model sidecar `TemplateAhspKoefFormulaState` + migration.
2. `DONE` - Integrasi metadata formula di `api_get_detail_ahsp` dan `api_save_detail_ahsp_for_pekerjaan`.
3. `DONE` - Sync sidecar dalam `transaction.atomic` (replace-all detail + cleanup orphan + upsert active formula).
4. `DONE` - Guard `MOD` fail-fast jika payload bundle muncul.
5. `DONE` - Reset/replace flow membersihkan sidecar (`reset-to-ref`, save gabungan, reset data pekerjaan).
6. `DONE` - Secondary endpoint bulk GET `template-ahsp/formula`.
7. `DONE` - Export/import/copy project sudah menyertakan sidecar formula koefisien + validasi `row_key <-> kode`.
8. `DONE` - Fondasi shared module ditambahkan: `shared/param_store.js`, `shared/formula_adapter.js`.
9. `DONE` - Frontend Template AHSP pass-through metadata formula (load/save/clear saat edit angka) sudah aktif.
10. `DONE` - Port sidebar parameter read-only ke Template AHSP (search + refresh + grouping base/formula).
11. `DONE` - Mode formula koefisien final: refresh snapshot pada select/save, inline warning/error, dan badge `fx`.
12. `IN PROGRESS` - Test coverage: backend utama + UI regression guard baseline sudah ada; regression lintas page dan skenario formula lengkap belum selesai.
13. `DONE` - Hotfix reliability load detail: migration sidecar diterapkan, fallback backend saat tabel sidecar belum ada, dan frontend fetch-safe untuk response non-JSON (hindari `Unexpected token '<'`).

## 3. Keputusan Utama (Final)

1. `ProjectParameter` dan `ProjectComputedParameter` adalah **single source of truth (SSOT)** level project.
2. `Volume Pekerjaan` tetap menjadi editor utama parameter.
3. `Template AHSP` menjadi consumer parameter untuk formula koefisien.
4. Yang dicopy dari Volume adalah **sidebar parameter + mekanisme konsumsi parameter**, bukan seluruh workflow quantity.
5. Evaluator formula tetap tunggal: `vol_formula_engine.js`.
6. Formula koefisien disimpan sebagai state pendamping (sidecar), bukan menggantikan kolom numerik `koefisien`.
7. `row_key` sidecar difinalkan ke `kode` baris detail AHSP.
8. Flow API utama adalah **integrated payload** di endpoint detail existing; endpoint terpisah hanya sekunder (opsional).

## 4. Scope dan Non-Goals

### 4.1 In Scope

1. Port sidebar parameter ke Template AHSP.
2. Integrasi formula input untuk `koefisien`.
3. Penyimpanan formula raw per baris koefisien.
4. Integrasi lintas page parameter Volume -> Template AHSP.

### 4.2 Out of Scope

1. Tidak mengubah aturan bundle (tetap hanya `CUS`).
2. Tidak memindahkan evaluasi formula ke backend pada fase awal.
3. Tidak menyalin autosave/undo/stats/filter quantity dari Volume.
4. Tidak redesign total UI Template AHSP.
5. Tidak membuat storage parameter terpisah khusus Template AHSP.

## 5. Arsitektur Target

### 5.1 Definisi Sidecar

`Sidecar` adalah penyimpanan pendamping untuk metadata formula.

- Data utama tetap di `DetailAHSPProject.koefisien` (angka final).
- Sidecar menyimpan:
  - `raw` formula (contoh `=bp_1*2`).
  - `is_fx` (mode formula atau angka biasa).
  - identitas baris stabil untuk mapping.

Alasan:
1. Risiko regresi rendah.
2. Kompatibel dengan perhitungan existing.
3. Rollback fitur lebih mudah.

### 5.2 Identitas Baris Formula (Wajib)

Karena save Template AHSP bersifat replace-all, `detail_id` tidak stabil lintas save.
`row_key` sidecar difinalkan menjadi `kode` baris detail AHSP.

Aturan:
1. `row_key = kode` (natural key, unique per pekerjaan).
2. Sidecar key efektif: `(project, pekerjaan, row_key)`.
3. Frontend wajib selalu mengirim `kode` untuk setiap row.
4. Row baru memakai `kode` generated frontend (sementara) lalu ikut payload save.
5. Jika user mengubah `kode`, formula lama dianggap orphan dan akan dibersihkan saat save.

### 5.3 Opsi Model

#### Opsi A (Recommended): Model Sidecar Baru

Nama sementara: `TemplateAhspKoefFormulaState`

Field minimum:
1. `project` FK
2. `pekerjaan` FK
3. `row_key` string
4. `raw` text
5. `is_fx` bool
6. timestamp

Constraint:
1. unique `(project, pekerjaan, row_key)`
2. sidecar hanya di-upsert untuk row `is_fx=True` dengan `raw` tidak kosong.
3. jika mode row diubah dari formula ke angka biasa, entry sidecar row tersebut dihapus (bukan disimpan `is_fx=False`).

#### Opsi B: Tambah field formula ke `DetailAHSPProject`

Tidak dipilih pada fase ini karena impact migrasi/coupling lebih besar.

## 6. Rencana Perubahan Teknis

### 6.1 Perubahan Fondasi di Volume (Facade, bukan rombak internal)

Tujuan: menyiapkan komponen reusable lintas page tanpa mengganggu UX Volume.

Item:
1. Tambah `detail_project/static/detail_project/js/shared/param_store.js` untuk load/cache snapshot parameter project.
2. Tambah `detail_project/static/detail_project/js/shared/formula_adapter.js` sebagai wrapper evaluasi formula + mapping error + range check konteks koefisien.
3. Modul shared ini bersifat facade terhadap API/evaluator existing, bukan rewrite `volume_pekerjaan.js`.
4. `volume_pekerjaan.js` tetap memakai workflow quantity existing apa adanya.

### 6.2 Backend Template AHSP

Item:
1. Tambah model sidecar + migration.
2. **Primary flow:** integrasikan metadata formula ke endpoint detail existing.
3. `api_get_detail_ahsp` mengirim metadata per row: `koef_formula_raw`, `koef_is_fx`.
4. `api_save_detail_ahsp_for_pekerjaan` menerima metadata formula per row.
5. **Secondary flow (opsional, fase lanjutan):** `GET /api/project/<id>/template-ahsp/formula/` untuk bulk pre-load indikator formula lintas pekerjaan.
6. Sidecar sync wajib satu transaksi dengan replace-all detail (`transaction.atomic`).
7. Step transaksi: delete detail lama -> bulk_create detail baru -> cleanup orphan sidecar + cleanup row non-fx -> upsert sidecar aktif (`is_fx=True`) -> update expanded state.
8. Validasi backend.
9. `REF` tetap reject save.
10. `MOD` fail-fast jika payload bundle muncul.
11. Formula raw validasi whitelist/token.
12. Reset-to-ref dan delete pekerjaan wajib menghapus sidecar terkait.
13. Hardening runtime error: jika tabel sidecar belum tersedia (deployment drift), endpoint tetap graceful (tanpa metadata formula) alih-alih 500.

### 6.3 Frontend Template AHSP

File target utama: `detail_project/static/detail_project/js/template_ahsp.js` dan template HTML.

Item:
1. Port sidebar parameter dari Volume.
2. Load parameter shared project (read-only di Template).
3. Aktifkan mode formula pada input `koefisien` (`=` prefix).
4. Evaluate formula ke angka koefisien menggunakan `VolFormula.evaluate(...)`.
5. Terapkan rules numerik koefisien (min `0.000001`, max `999999.999999`).
6. Tampilkan preview/error inline per row.
7. Saat save, kirim `koefisien` numeric canonical.
8. Saat save, kirim metadata formula raw di payload detail (flow utama terintegrasi).
9. Hardening fetch detail: validasi `response.ok` dan content-type sebelum parse JSON, tampilkan pesan error server yang eksplisit, serta hindari unhandled promise pada trigger reload/select.

### 6.4 Export/Import/Copy Project

Item:
1. Tambahkan sidecar formula koefisien ke payload export backup.
2. Restore sidecar saat import/copy project.
3. Karena `row_key = kode`, remap harus menjaga konsistensi `kode` per pekerjaan.
4. Khusus import file: validasi setiap sidecar `row_key` harus match dengan `kode` detail yang ada; entry sidecar yang tidak match di-skip + dilog warning.

## 7. Fase Implementasi

### Fase 0 - Contract dan Guard

1. Finalisasi contract `row_key = kode`.
2. Kunci guard domain `REF/MOD/CUS` terkait formula/bundle.
3. Finalisasi keputusan edge case (range, parameter hilang, reset behavior).
4. Tambah logging diagnostik save/formula.

Acceptance:
1. Save `MOD` dengan payload bundle ditolak 400 dengan pesan jelas.
2. Seluruh endpoint detail/reset/delete punya contract sidecar yang eksplisit.

### Fase 1 - Foundation Refactor (Volume-safe)

1. Implementasi `shared/param_store.js`.
2. Implementasi `shared/formula_adapter.js`.
3. Tidak ubah perilaku quantity.

Acceptance:
1. Semua fitur Volume existing tetap berjalan.
2. Modul shared bisa dipakai oleh Template AHSP.

### Fase 2 - Data Layer Template AHSP

1. Tambah model sidecar + migration.
2. Integrasi metadata formula di endpoint detail existing (primary flow).
3. Integrasi read parameter lintas page (reuse endpoint existing parameter/computed).
4. Endpoint bulk formula-state (secondary flow) bersifat opsional.

Acceptance:
1. Formula state koefisien terbaca/tersimpan via GET/POST detail existing.
2. Template AHSP membaca parameter project yang sama dengan Volume.
3. Sidecar orphan ter-cleanup otomatis dalam transaksi save.

### Fase 3 - Integrasi UI Formula Koefisien

1. Port sidebar parameter ke Template AHSP.
   - Pola UI mengikuti Volume: overlay sidebar kanan, default hidden, muncul via tombol `Parameter` atau hover edge kanan.
2. Integrasi evaluator formula koefisien.
3. Integrasi save pipeline angka + formula state.

Acceptance:
1. `=bp_1 * 2` dihitung benar di koefisien.
2. Formula persist setelah reload job.
3. Tidak ada coupling ke flow quantity.

### Fase 4 - Hardening dan Stabilization

1. Konflik/freshness handling lintas page.
2. Optimasi performa evaluate/sync.
3. Dokumentasi user + runbook.

Acceptance:
1. Tidak ada regresi pada Template AHSP/Harga Items/Rincian/Rekap.

## 8. Checklist Implementasi Per File

### 8.1 Backend

1. `detail_project/models.py`
   - tambah model sidecar formula koefisien.
2. `detail_project/views_api.py`
   - integrasi GET/POST detail AHSP untuk metadata formula (primary flow).
   - optional endpoint bulk formula-state (secondary flow).
   - fail-fast validasi `MOD` vs bundle.
   - cleanup/upsert sidecar di dalam transaksi save.
   - reset-to-ref dan delete pekerjaan menghapus sidecar.
3. `detail_project/urls.py`
   - daftarkan route endpoint bulk formula-state bila diaktifkan.
4. Export/import handler di `detail_project/views_api.py`
   - sertakan sidecar formula koefisien.
   - validasi mapping `row_key <-> kode` saat import, skip entry sidecar invalid.

### 8.2 Frontend

1. `detail_project/templates/detail_project/template_ahsp.html`
   - inject data endpoint detail + optional bulk formula-state.
   - load `vol_formula_engine.js`.
   - mount slot sidebar parameter.
2. `detail_project/static/detail_project/js/template_ahsp.js`
   - konsumsi parameter shared.
   - evaluate formula koefisien.
   - map `row_key = kode` dan sync formula state.
3. `detail_project/static/detail_project/js/shared/param_store.js`
   - load/cache snapshot parameter project.
4. `detail_project/static/detail_project/js/shared/formula_adapter.js`
   - wrapper evaluator + mapping error + range guard.

### 8.3 Test

1. Tambah test backend formula-state koefisien.
2. Tambah test frontend/JS evaluasi koefisien.
3. Tambah regression lintas page (ubah param di Volume -> dipakai di Template).

## 9. Rencana Testing

### 9.1 Backend Tests

1. CRUD formula-state koefisien.
2. Validasi formula raw (token invalid, panjang berlebih, dsb).
3. Validasi mode:
   - `REF` tidak bisa save.
   - `MOD` bisa edit koef, tidak bisa bundle.
   - `CUS` bisa edit koef + bundle.
4. Cleanup orphan formula state saat replace-all.
5. Sidecar sync berada di transaksi yang sama dengan replace-all detail.
6. Reset-to-ref dan delete pekerjaan membersihkan sidecar.
7. Saat row berubah dari `is_fx=True` ke angka biasa, sidecar row tersebut terhapus.
8. Import skip sidecar dengan `row_key` yang tidak punya pasangan `kode` di detail payload.

### 9.2 Frontend Tests

1. Evaluasi formula operator dasar.
2. Evaluasi variabel `bp_*` dan `cp_*`.
3. Blok simpan bila hasil formula di luar range koefisien.
4. Referensi parameter hilang menampilkan warning dan memakai nilai numerik tersimpan terakhir.
5. Persist formula raw saat reload/select job.
6. Sinkronisasi nilai terbaru parameter dari Volume.
7. `row_key = kode` konsisten saat save/reload.

### 9.3 Regression Tests

1. Save detail tanpa formula tetap normal.
2. Export CSV/JSON Template AHSP tetap normal.
3. Integrasi Harga Items/Rekap tetap konsisten.
4. Volume workflow quantity tidak berubah.

## 10. Rollout Plan

1. Feature flag:
   - `TEMPLATE_AHSP_FORMULA_ENABLED` default `false`.
2. Tahap deploy:
   - staging internal
   - pilot user
   - gradual enable production
3. Monitoring:
   - save error rate Template AHSP
   - formula-state API error rate
   - conflict rate
   - partial save rate

## 11. Risiko dan Mitigasi

1. Formula pindah ke baris yang salah setelah save.
   - Mitigasi: `row_key = kode` + validasi unik + test replace-all.

2. Perubahan parameter di Volume tidak langsung tercermin.
   - Mitigasi: refresh snapshot parameter saat buka job dan sebelum save.

3. Regresi pada flow quantity Volume.
   - Mitigasi: refactor foundation bersifat additive, contract test Volume wajib hijau.

4. Ambiguitas MOD dan bundle.
   - Mitigasi: fail-fast backend + guard frontend eksplisit.

5. Performa menurun pada tabel besar.
   - Mitigasi: debounce evaluate/sync, lazy refresh per job aktif.

## 12. Edge Cases dan Keputusan

1. Hasil formula di luar range koefisien: **strict**, simpan diblok sampai valid.
2. Parameter yang direferensi hilang: tampilkan warning, simpan `raw` tetap, koefisien memakai nilai numerik valid terakhir.
3. Kontrak save untuk parameter hilang: frontend tetap mengirim `koefisien` numerik dari response detail terakhir (bukan `0`/`NaN`) sambil tetap mengirim `raw` formula di sidecar.
4. UI wajib menandai row parameter-hilang sebagai warning visual agar user sadar ada referensi putus.
5. Row kategori `LAIN` dengan bundle tetap boleh memakai formula koefisien (tidak mutual exclusive).
6. Reset-to-ref dan delete pekerjaan wajib clear seluruh sidecar formula terkait.
7. Edit `kode` dianggap ganti identitas row; sidecar lama dibersihkan sebagai orphan saat save.

## 13. Keputusan Review yang Perlu Disetujui

1. Nama final model/API sidecar.
2. Kebutuhan endpoint bulk formula-state pada fase awal atau fase lanjutan.
3. UX final untuk warning parameter hilang (warna/pesan/tombol simpan).

## 14. Definition of Done

1. Koefisien bisa diisi angka atau formula pada pekerjaan editable.
2. Formula tersimpan, termuat ulang, dan ter-map ke baris yang benar.
3. `koefisien` tetap tersimpan angka canonical sesuai spec.
4. Aturan domain `REF/MOD/CUS` dan bundle tetap terjaga.
5. Parameter lintas page konsisten antara Volume dan Template AHSP.
6. Tidak ada regresi pada workflow quantity Volume.
7. Seluruh test baru + regression utama lulus.

---

## 15. Checklist Tracking Progress

Legend: `[ ]` belum Â· `[~]` sedang dikerjakan Â· `[x]` selesai Â· `[-]` skip/tidak relevan

### 15.0 Hasil Verifikasi Final

| # | Klaim | Status Verifikasi | Catatan |
|---|---|---|---|
| 1 | DONE | VERIFIED | Model sidecar + migration aktif (`models.py` + `0042`) |
| 2 | DONE | VERIFIED | Integrasi GET/POST metadata formula di endpoint detail |
| 3 | DONE | VERIFIED | Cleanup + upsert sidecar di dalam `transaction.atomic` save detail |
| 4 | DONE | VERIFIED | Guard `MOD` fail-fast untuk payload bundle |
| 5 | DONE | VERIFIED | Cleanup sidecar pada reset-to-ref, delete pekerjaan, save gabungan |
| 6 | DONE | VERIFIED | Endpoint bulk formula-state Template AHSP tersedia |
| 7 | DONE | VERIFIED | Export/import/copy menyertakan sidecar + validasi `row_key <-> kode` |
| 8 | DONE | VERIFIED | Shared modules (`param_store.js`, `formula_adapter.js`) tersedia |
| 9 | DONE | VERIFIED | Frontend pass-through metadata formula aktif |
| 10 | DONE | VERIFIED | Sidebar parameter read-only (search + refresh + base/computed list) sudah dirender di Template AHSP |
| 11 | DONE | VERIFIED | Evaluasi `=` final dengan badge `fx`, warning/error inline, refresh snapshot select/save, dan re-evaluate on load |
| 12 | IN PROGRESS | CONFIRMED | Backend + frontend formula tests utama sudah ada; sisa validasi utama ada di hardening flag dan rollout pasca rilis |
| 13 | DONE | VERIFIED | Hotfix error load detail: migrasi `0042` diterapkan, fallback backend saat tabel sidecar belum ada, dan frontend parse response dibuat aman (tanpa crash `Unexpected token '<'`) |

Semua item `DONE` (1-11, 13) terverifikasi valid.

### 15.1 Progress Summary

| Fase | Total | Done | In Progress | Pending |
|---|---:|---:|---:|---:|
| Fase 0 | 8 | 8 | 0 | 0 |
| Fase 1 | 13 | 11 | 2 | 0 |
| Fase 2 | 27 | 23 | 4 | 0 |
| Fase 3 | 25 | 24 | 1 | 0 |
| Fase 4 | 17 | 17 | 0 | 0 |
| Post-Launch | 6 | 0 | 0 | 6 |
| **Total** | **96** | **83 (86%)** | **7 (7%)** | **6 (6%)** |

Catatan: ringkasan 96 item di 15.1 mengikuti checklist fase implementasi; baris audit hotfix pada 15.0 dicatat sebagai verifikasi tambahan dan tidak mengubah denominator.

### 15.2 Item `[~]` Perlu Perhatian

1. `1.3`, `1.A`: regression formal untuk memastikan zero impact ke Volume belum diverifikasi penuh.
2. `2.3`, `2.5d`: behavior feature flag belum tervalidasi end-to-end.
3. `2.T5` dan `2.T8` sudah ditutup; coverage backend yang masih perlu audit final ada di `2.T1`-`2.T4`, `2.T6`-`2.T7`.
4. Fokus tersisa pada rollout operasional: Post-Launch `P.1`-`P.6`.
5. Dokumentasi pengguna dan runbook formula sudah ditambahkan (`docs/PANDUAN_USER.md`, `docs/RUNBOOK_TEMPLATE_AHSP_FORMULA.md`), tinggal verifikasi adopsi di staging.

### 15.3 Update Implementasi Terbaru (Perbaikan Error)

1. Root cause error `500` saat load detail teridentifikasi: tabel sidecar formula belum tersedia pada environment aktif.
2. Perbaikan environment: migration `0042_templateahspkoefformulastate` diterapkan.
3. Hardening backend:
   - `api_get_detail_ahsp` fallback ke mode tanpa metadata formula jika tabel sidecar belum ada (graceful, bukan 500).
   - `api_save_detail_ahsp_for_pekerjaan` skip sync sidecar bila tabel sidecar tidak tersedia (dengan warning log).
   - endpoint bulk formula-state juga fallback empty state jika tabel sidecar belum ada.
4. Hardening frontend (`template_ahsp.js`):
   - parsing response dibuat safe (`response.ok` + cek content-type) sebelum `JSON.parse`.
   - pesan error load menampilkan konteks server yang lebih jelas.
   - trigger load/reload yang fire-and-forget dibungkus untuk mencegah unhandled promise rejection.
5. Dampak: kasus `Unexpected token '<'` tidak lagi memutus alur UI saat backend mengembalikan HTML error page.
6. Validasi pasca-fix:
   - `python manage.py check` lulus.
   - `python manage.py test detail_project.tests_template_ahsp_formula_state --keepdb -v 2` lulus (7 test termasuk skenario rollback transaksi dan toggle `is_fx` True->False).
7. Validasi lanjutan frontend formula:
   - `npm run test:frontend -- detail_project/static/detail_project/js/tests/formula_adapter.test.js detail_project/static/detail_project/js/tests/shared_param_store.test.js` lulus (6 test).
   - `python manage.py test detail_project.tests_template_ahsp_ui_regressions --keepdb -v 2` lulus (10 test guard UI).
8. Validasi hardening fase 4:
   - `python manage.py test detail_project.tests_template_ahsp_formula_state --keepdb -v 2` lulus (12 test, termasuk save tanpa formula, export/import sidecar invalid skip, query budget, dan integrasi rekap).
   - `python manage.py test detail_project.tests_volume_pekerjaan_save_api --keepdb -v 2` lulus (6 test, memastikan workflow quantity Volume tetap stabil).


### Fase 0 â€” Contract dan Guard

- [x] 0.1 Finalisasi contract `row_key = kode` (review di Section 5.2 dianggap final)
- [x] 0.2 Verifikasi guard `REF` reject save sudah ada di `api_save_detail_ahsp_for_pekerjaan`
- [x] 0.3 Verifikasi guard `MOD` fail-fast jika payload bundle muncul
- [x] 0.4 Tambah logging diagnostik pada save endpoint (formula metadata received/skipped)
- [x] 0.5 Verifikasi `api_reset_detail_ahsp_to_ref` siap untuk integrasi sidecar cleanup
- [x] 0.6 Verifikasi delete pekerjaan path siap untuk integrasi sidecar cleanup
- [x] **0.A** Acceptance: `MOD` + bundle â†’ 400 dengan pesan jelas
- [x] **0.B** Acceptance: Semua endpoint detail/reset/delete ter-audit untuk contract sidecar

### Fase 1 â€” Foundation Refactor (Volume-safe)

- [x] 1.1 Buat `detail_project/static/detail_project/js/shared/param_store.js`
  - [x] 1.1a `SharedParamStore.load(projectId)` â€” fetch bp + cp dari API
  - [x] 1.1b `SharedParamStore.getSnapshot()` â€” return flat object `{bp_1: val, ...}`
  - [x] 1.1c `SharedParamStore.refresh()` â€” re-fetch dari server
  - [x] 1.1d Cache di memory dengan invalidasi manual
- [x] 1.2 Buat `detail_project/static/detail_project/js/shared/formula_adapter.js`
  - [x] 1.2a `FormulaAdapter.evaluate(raw, snapshot, {min, max})` â€” wrapper `VolFormula.evaluate`
  - [x] 1.2b Return `{ok, value}` atau `{ok: false, error}` dengan pesan user-friendly
  - [x] 1.2c Range guard khusus koefisien (min `0.000001`, max `999999.999999`)
  - [x] 1.2d Handle parameter hilang â†’ return warning (bukan fatal error)
- [~] 1.3 Verifikasi `volume_pekerjaan.js` workflow quantity **tidak berubah**
- [~] **1.A** Acceptance: Volume existing tetap berjalan 100%
- [x] **1.B** Acceptance: Modul shared bisa di-import/dipakai oleh Template AHSP

### Fase 2 â€” Data Layer Template AHSP

**Backend Model:**
- [x] 2.1 Tambah model `TemplateAhspKoefFormulaState` di `models.py`
  - [x] 2.1a Fields: `project` FK, `pekerjaan` FK, `row_key` CharField, `raw` TextField, `is_fx` BooleanField
  - [x] 2.1b UniqueConstraint `(project, pekerjaan, row_key)`
  - [x] 2.1c Timestamps (`created_at`, `updated_at`)
- [x] 2.2 Generate + apply migration
- [~] 2.3 Feature flag `TEMPLATE_AHSP_FORMULA_ENABLED` di settings

**Backend API â€” Primary Flow (Integrated):**
- [x] 2.4 `api_get_detail_ahsp`: sertakan `koef_formula_raw` dan `koef_is_fx` per row di response
  - [x] 2.4a Query sidecar via `row_key = kode`, prefetch dalam satu query
  - [x] 2.4b Jika flag off atau sidecar tidak ada â†’ field null/false (backward compat)
- [x] 2.5 `api_save_detail_ahsp_for_pekerjaan`: terima metadata formula per row
  - [x] 2.5a Parse `koef_formula_raw` dan `koef_is_fx` dari setiap row di payload
  - [x] 2.5b Validasi formula raw via whitelist/token validator (reuse existing)
  - [x] 2.5c Dalam `transaction.atomic`:
    - [x] Step 1: delete detail lama (existing)
    - [x] Step 2: bulk_create detail baru (existing)
    - [x] Step 3: cleanup orphan sidecar (kode tidak ada di set baru)
    - [x] Step 4: cleanup sidecar row non-fx (mode berubah ke angka biasa)
    - [x] Step 5: upsert sidecar aktif (`is_fx=True`, `raw` tidak kosong)
    - [x] Step 6: update expanded state (existing)
  - [~] 2.5d Jika flag off â†’ skip sidecar steps, ignore metadata di payload

**Backend â€” Sidecar Cleanup:**
- [x] 2.6 `api_reset_detail_ahsp_to_ref`: tambah delete sidecar terkait
- [x] 2.7 Delete pekerjaan path: tambah delete sidecar terkait
- [x] 2.8 (Opsional) Endpoint bulk formula-state `GET .../template-ahsp/formula/`

**Backend Tests:**
- [~] 2.T1 Test CRUD formula-state via integrated endpoint
- [~] 2.T2 Test validasi formula raw (token invalid, panjang berlebih)
- [~] 2.T3 Test mode: `REF` reject, `MOD` edit koef tanpa bundle, `CUS` edit koef + bundle
- [~] 2.T4 Test orphan cleanup saat replace-all
- [x] 2.T5 Test sidecar sync dalam satu transaksi (rollback on error)
- [~] 2.T6 Test reset-to-ref menghapus sidecar
- [~] 2.T7 Test delete pekerjaan menghapus sidecar
- [x] 2.T8 Test toggle `is_fx` Trueâ†’False menghapus sidecar entry
- [x] **2.A** Acceptance: Formula state terbaca/tersimpan via GET/POST detail
- [x] **2.B** Acceptance: Parameter project terbaca lintas page
- [x] **2.C** Acceptance: Orphan sidecar ter-cleanup otomatis

### Fase 3 â€” Integrasi UI Formula Koefisien

**Frontend â€” Sidebar Parameter:**
- [x] 3.1 Port sidebar parameter ke `template_ahsp.html`
  - [x] 3.1a Load `vol_formula_engine.js` di template
  - [x] 3.1b Load `shared/param_store.js` dan `shared/formula_adapter.js`
  - [x] 3.1c Mount slot sidebar parameter (read-only display)
- [x] 3.2 Load parameter project via `SharedParamStore.load()` saat page init
- [x] 3.3 Refresh parameter snapshot saat select job / sebelum save

**Frontend â€” Formula Input Koefisien:**
- [x] 3.4 Deteksi mode formula pada input koefisien (`=` prefix)
- [x] 3.5 Evaluate formula via `FormulaAdapter.evaluate()` saat blur/input
- [x] 3.6 Tampilkan preview angka hasil evaluasi per row
- [x] 3.7 Tampilkan error/warning inline per row:
  - [x] 3.7a Hasil di luar range â†’ error merah, blok save
  - [x] 3.7b Parameter hilang â†’ warning kuning, save tetap diizinkan
  - [x] 3.7c Formula syntax invalid â†’ error merah, blok save
- [x] 3.8 Badge/indikator `fx` pada sel koefisien yang memakai formula

**Frontend â€” Save Pipeline:**
- [x] 3.9 `gatherRows()` menyertakan `koef_formula_raw` dan `koef_is_fx` per row
- [x] 3.10 Kirim `koefisien` numeric canonical (hasil evaluasi / nilai tersimpan terakhir)
- [x] 3.11 Kirim metadata formula di payload detail (integrated flow)
- [x] 3.12 Validasi pre-save: blok jika ada row dengan formula error (bukan warning)
- [x] 3.13 Handle parameter hilang saat save: kirim koefisien numerik dari response terakhir

**Frontend â€” Load/Reload:**
- [x] 3.14 Parse `koef_formula_raw` dan `koef_is_fx` dari response GET detail
- [x] 3.15 Restore mode formula di input saat load/select job
- [x] 3.16 Re-evaluate semua formula saat load (dengan parameter snapshot terbaru)

**Frontend Tests:**
- [x] 3.T1 Test evaluasi formula operator dasar (`+ - * / ^`)
- [x] 3.T2 Test evaluasi variabel `bp_*` dan `cp_*`
- [x] 3.T3 Test blok simpan saat hasil formula di luar range
- [x] 3.T4 Test parameter hilang â†’ warning + pakai nilai tersimpan
- [x] 3.T5 Test persist formula raw saat reload/select job
- [x] 3.T6 Test sinkronisasi parameter terbaru dari Volume
- [x] 3.T7 Test `row_key = kode` konsisten saat save/reload
- [x] **3.A** Acceptance: `=bp_1 * 2` dihitung benar di koefisien
- [x] **3.B** Acceptance: Formula persist setelah reload job
- [x] **3.C** Acceptance: Tidak ada coupling ke flow quantity

### Fase 4 â€” Hardening dan Stabilization

**Cross-page Freshness:**
- [x] 4.1 Refresh parameter snapshot saat buka job di Template AHSP
- [x] 4.2 Pre-save re-evaluate: deteksi perubahan nilai parameter sejak load
- [x] 4.3 Tampilkan diff/notifikasi jika parameter berubah menghasilkan nilai koefisien berbeda

**Export/Import/Copy:**
- [x] 4.4 Export backup menyertakan sidecar formula koefisien
- [x] 4.5 Import restore sidecar + validasi `row_key` match `kode`
- [x] 4.6 Import skip sidecar entry yang tidak match + log warning
- [x] 4.7 Copy project menyertakan sidecar formula

**Performance:**
- [x] 4.8 Audit jumlah query tambahan per load/save
- [x] 4.9 Debounce evaluate saat input cepat
- [x] 4.10 Lazy refresh: hanya evaluate formula saat job aktif

**Regression Tests:**
- [x] 4.T1 Save detail tanpa formula tetap normal
- [x] 4.T2 Export CSV/JSON Template AHSP tetap normal
- [x] 4.T3 Integrasi Harga Items/Rekap tetap konsisten
- [x] 4.T4 Volume workflow quantity tidak berubah
- [x] 4.T5 Import dengan sidecar invalid di-skip tanpa error

**Documentation:**
- [x] 4.11 Update panduan user (formula koefisien di Template AHSP)
- [x] 4.12 Runbook singkat (enable/disable flag, monitoring, troubleshoot)
- [x] **4.A** Acceptance: Tidak ada regresi pada Template AHSP/Harga Items/Rincian/Rekap

### Post-Launch

- [ ] P.1 Enable flag di staging â†’ smoke test
- [ ] P.2 Enable flag di pilot user â†’ collect feedback
- [ ] P.3 Monitor error rate 7 hari
- [ ] P.4 Gradual enable production
- [ ] P.5 Review: perlu endpoint bulk formula-state (secondary flow)?
- [ ] P.6 Review: perlu modal editor formula (UX enhancement)?
