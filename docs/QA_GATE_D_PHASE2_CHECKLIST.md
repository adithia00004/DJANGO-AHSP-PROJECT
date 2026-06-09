# QA Checklist: Label-Only Formula Input (Gate Eksekusi)

## Tujuan
Checklist manual terukur untuk memastikan implementasi label-only siap rilis.
Arsitektur: **Opsi C (Hybrid)** -- chip preview + label input masking.
Struktur checklist ini terdiri dari **6 gate** sesuai urutan eksekusi phase.

## Prasyarat
- `OPAQUE_ID_ENABLED=True`
- Migrasi opaque ID sudah selesai (`failed: 0`)
- Build frontend terbaru sudah terdeploy
- Feature flag `FORMULA_LABEL_ONLY_UI_ENABLED=True`

## Aturan Lulus
- Setiap butir mandatory harus `PASS`.
- Jika satu butir mandatory `FAIL`, gate dianggap gagal.

## Gate 1 - No Code Leak di UI (Mandatory)
1. Chip formula di modal editor.
Expected:
- Hanya label tampil.
- Tidak ada teks `bp_*`/`cp_*`.

2. Autocomplete/suggestion list.
Expected:
- Hanya label + nilai.
- Tidak ada format `Label (bp_*)`.

3. Dialog delete/resolver/error.
Expected:
- Tidak ada `(kode: bp_*)` atau token mentah sejenis.

4. Export user-facing.
Expected:
- Tidak ada kolom/teks kode internal.

5. Import error message.
Expected:
- Tidak ada token `bp_*`/`cp_*` di pesan error import.
- Error menampilkan label atau nomor baris.

6. Sync warning/toast.
Expected:
- UI tidak menampilkan field code raw dari warning payload.
- Summary warning tetap dapat dipahami user.

## Gate 2 - Core Editing Flow: Label Input Masking (Mandatory)
1. Buat formula baru via inline input.
Expected:
- User mengetik di input yang menampilkan **label** (bukan raw code).
- Autocomplete meng-insert label.
- Setelah blur, chip preview muncul menampilkan formula label.
- Save sukses, DB menyimpan raw code.

2. Buat formula baru via modal editor.
Expected:
- Textarea menampilkan **label** (bukan raw code).
- Autocomplete insert label.
- Chip preview area menampilkan visual chip.
- Save sukses.

3. Edit formula existing (legacy).
Expected:
- Formula lama terbaca sebagai label (bukan `bp_1 * bp_2`).
- Dapat diedit dan disimpan tanpa interaksi kode.

4. Reload consistency.
Expected:
- Setelah reload, formula tetap identik secara hasil hitung.
- Display menampilkan label yang sama.

5. Round-trip semantic identity.
Expected:
- `rawToDisplayText(raw)` menghasilkan label text.
- `displayToRaw(displayText)` menghasilkan raw yang **semantic-identical** dengan input awal (token stream ekuivalen, whitespace boleh beda).
- Tidak ada data drift setelah edit cycle.

6. Mode interaksi editor.
Expected:
- Hanya ada 2 mode: inline dan modal popup.
- Tidak ada tombol/fitur fullscreen terpisah di modal formula.

7. Keyboard UX native.
Expected:
- Copy/paste di input formula berfungsi natural.
- Undo/redo browser berfungsi.
- Arrow keys navigasi berfungsi normal.

8. Kedua kanal aktif (bukan dekorasi UI).
Expected:
- Inline bisa create/edit/save formula tanpa membuka modal.
- Modal bisa create/edit/save formula tanpa kembali ke inline.
- Hasil save dari kedua kanal identik (preview, nilai akhir, dan payload raw).

9. Matriks nilai diterima konsisten di kedua kanal.
Expected:
- Angka literal diterima: integer, desimal, format lokal (`1.000,25`) dan underscore (`1_000.25`).
- Operasi diterima: `+ - * / ^`, kurung `()`, fungsi `MIN/MAX/SUM/AVG/ABS/ROUND/CEIL/FLOOR/POW`.
- Referensi parameter diterima dari base (`bp_*`) dan computed (`cp_*`) via autocomplete/palette.
- Prefix `=` opsional, tetapi perilaku evaluasi sama pada inline dan modal.

10. Nilai invalid menghasilkan perilaku yang sama.
Expected:
- Kurung tidak seimbang, token tidak dikenal, operator tanpa operand, dan pembagian nol menghasilkan error konsisten.
- Unknown token memberi jalur resolver yang sama (CTA pilih parameter pengganti).

## Gate 3 - Recovery & Validation (Mandatory)
1. Unknown token resolver.
Expected:
- Error memberi CTA pengganti.
- User pilih parameter pengganti -> formula ter-update -> preview refresh.

2. Validasi sintaks dasar.
Expected:
- Formula kosong, kurung tidak seimbang, operator ganda terdeteksi sebelum apply.

3. Insert-only discipline (cursor map).
Expected:
- User tidak bisa mengetik label secara manual dan mendapat resolve.
- Insert parameter hanya via autocomplete/palette.
- Label dengan karakter spesial (`-`, `'`, `/`) aman karena posisi diketahui dari cursor map.

4. Label duplikat handling.
Expected:
- Buat 2 parameter dengan label identik (misal "Panjang").
- Insert keduanya ke formula via autocomplete (pilih masing-masing dari suggestion).
- Save dan reload.
- Formula tetap benar: kedua parameter resolve ke code berbeda (`bp_1`, `bp_2`).
- Cursor map membedakan keduanya meskipun display text sama.

## Gate 4 - Integritas Data & Sync (Mandatory)
1. Create/sync parameter base.
Expected:
- Data tersimpan benar.
- Name di DB tetap format `bp_*`.

2. Create/sync computed parameter.
Expected:
- Data tersimpan benar.
- Name di DB tetap format `cp_*`.

3. Multi-tab conflict (C2/C3).
Expected:
- Tab B mendapat konflik 409 + opsi `Reload` / `Tetap Lokal`.

4. Sync replace integrity.
Expected:
- Setelah reload, item yang dihapus tidak muncul kembali.

5. Label masking tidak korupsi raw data.
Expected:
- `rawInputById` selalu menyimpan raw code (bukan label text).
- Sync payload ke server selalu raw code.
- Tidak ada label text yang tersimpan ke DB.

## Gate 5 - Layout Stability (Mandatory)
1. Kontrol lebar kolom quantity (`vp-col-width-control`).
Expected:
- Tombol minus/plus/reset bekerja.
- Lebar kolom tidak "loncat" saat formula aktif/nonaktif.

2. Multi viewport.
Expected:
- Desktop besar, laptop, mobile landscape tetap terbaca dan usable.

3. Transisi chip/input.
Expected:
- Klik chip preview → input muncul dengan label text, tidak ada flicker.
- Blur input → chip preview refresh, tidak ada layout jump.

## Gate 6 - Simplifikasi Flow (Phase 4, Mandatory)
1. Formula mode explicit flow.
Expected:
- User dapat masuk/keluar mode formula secara jelas.
- Tidak tergantung pada pengetahuan awalan `=`.

2. Preview label+nilai konsisten.
Expected:
- Preview menampilkan `Label (nilai)` di semua area (inline dan modal).

## Evidensi Wajib Disimpan
- Screenshot/video:
  - inline input menampilkan label (bukan raw code),
  - modal editor menampilkan label (bukan raw code),
  - chip preview tampilan default,
  - autocomplete (tanpa code leak),
  - error import (tanpa code leak),
  - sync warning toast (tanpa code leak),
  - resolver unknown token,
  - modal konflik 409,
  - round-trip test evidence (raw→display→raw identity).
- Sampel export hasil.
- Catatan PASS/FAIL per butir mandatory.
- Catatan bug jika ada fail + reproduksi singkat.
