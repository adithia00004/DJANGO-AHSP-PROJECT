# Runbook: Formula Koefisien Template AHSP

## 1. Tujuan

Dokumen operasional untuk monitoring, troubleshooting, dan rollback fitur formula koefisien pada Template AHSP.

## 2. Scope

- Endpoint detail Template AHSP (`GET/POST`)
- Sidecar state formula koefisien (`TemplateAhspKoefFormulaState`)
- Konsumsi parameter project (`bp_*`, `cp_*`)
- UI evaluasi formula pada `template_ahsp.js`

## 3. Prasyarat Deploy

1. Migration `0042_templateahspkoefformulastate` sudah terpasang.
2. Asset frontend terbaru sudah ter-build/deploy.
3. Endpoint parameter/computed parameter aktif.

Command verifikasi:

```bash
python manage.py showmigrations detail_project
python manage.py check
```

## 4. Health Checks

### 4.1 Backend

1. Buka endpoint detail AHSP untuk satu pekerjaan, pastikan response `200`.
2. Simpan detail AHSP dengan satu row formula (`koef_is_fx=true`), pastikan response `ok=true`.
3. Reset-to-ref untuk pekerjaan MOD, pastikan sidecar terhapus.

### 4.2 Frontend

1. Ketik formula `=bp_1*2` pada koefisien, pastikan nilai dihitung.
2. Pastikan badge `fx` muncul.
3. Ubah parameter di Volume, lalu save di Template AHSP:
   - sistem re-evaluate formula,
   - menampilkan notifikasi jika nilai koefisien berubah.

## 5. Monitoring Sinyal Risiko

Pantau log untuk:

- `Koef sidecar table missing`
- `Skipping formula metadata sync`
- `Fetch failed` pada load detail AHSP
- lonjakan warning `missing_identifier` (indikasi parameter putus)

## 6. Incident Playbook

### 6.1 Error 500 saat load detail AHSP

Gejala:
- Endpoint detail AHSP mengembalikan 500.
- UI bisa menampilkan error parse JSON (`Unexpected token '<'`).

Langkah:

1. Cek migration:
   - `python manage.py showmigrations detail_project`
2. Jika `0042` belum apply:
   - `python manage.py migrate detail_project 0042`
3. Restart app worker/web.
4. Hard refresh browser.

### 6.2 Formula tidak tersimpan

Langkah:

1. Cek payload save apakah memuat `koef_formula_raw` dan `koef_is_fx`.
2. Cek validasi formula raw (token/sintaks).
3. Cek log warning sync sidecar.
4. Verifikasi row key (`kode`) tidak kosong dan konsisten.

### 6.3 Parameter hilang

Gejala:
- Row kuning, warning `missing_identifier`.

Langkah:

1. Cek parameter pada halaman Volume.
2. Recreate parameter yang hilang atau edit formula.
3. Simpan ulang Template AHSP.

## 7. Rollback

Jika perlu rollback fitur:

1. Pertahankan data numerik `koefisien` sebagai source aman.
2. Nonaktifkan konsumsi metadata formula di frontend (hide formula behavior).
3. Endpoint backend tetap aman karena fallback graceful jika sidecar tidak tersedia.
4. Jangan hapus tabel sidecar tanpa backup data.

## 8. Verifikasi Pasca-Perbaikan

Command test minimum:

```bash
python manage.py test detail_project.tests_template_ahsp_formula_state --keepdb -v 2
python manage.py test detail_project.tests_template_ahsp_ui_regressions --keepdb -v 2
npm run test:frontend -- detail_project/static/detail_project/js/tests/formula_adapter.test.js detail_project/static/detail_project/js/tests/shared_param_store.test.js
python manage.py test detail_project.tests_volume_pekerjaan_save_api --keepdb -v 2
```
