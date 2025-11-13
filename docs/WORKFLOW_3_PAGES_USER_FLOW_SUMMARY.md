# WORKFLOW 3 PAGES - USER FLOW SUMMARY

## Ringkasan Cepat per Halaman
1. **Template AHSP** — Input komponen dan Segment D (LAIN) bundle creation.
2. **Harga Items** — Pricing terhadap hasil ekspansi DetailAHSPExpanded.
3. **Rincian AHSP** — Review + markup override + ekspor RAB.

## Guardrail Standar (Harus Sama dengan Dokumen Lain)
> **Guardrail — Source Types & Segment D (LAIN) Access**
> - **REFERENSI (REF)** — read-only di Template AHSP. Tab/Segment D (LAIN) disembunyikan; tidak bisa menambah bundle. Semua perubahan hanya boleh lewat import referensi atau workflow Rincian Gabungan.
> - **CUSTOM** — satu-satunya source_type yang fully editable di Template AHSP. Segment D (LAIN) selalu aktif, boleh referensi pekerjaan proyek (job) atau AHSP master, dan tunduk pada validasi empty-target + circular check.
> - **REFERENSI_MODIFIED (REF_MODIFIED)** — clone dari REF yang diedit di halaman "Rincian AHSP Gabungan". Di Template AHSP tampil sebagai read-only mirip REF dan Segment D tetap terkunci.
> - **Segment D Loop Limit** — Bundle hanya boleh nested maksimal 3 level (A→B→C). Level ke-4 otomatis di-block dengan error "Maksimum kedalaman bundle terlampaui".
> - **Cascade Enforcement** — Saat pekerjaan target diubah, sistem wajib menjalankan cascade re-expansion untuk semua pekerjaan yang mereferensikannya. User tidak bisa bypass guardrail ini karena edit manual di expanded rows memang tidak tersedia.

## User Flow Detail
### 1. Template AHSP
- **Input**: TK/BHN/ALT manual + LAIN (Segment D bundle) untuk CUSTOM.
- **Validasi**: empty component guardrail untuk ref_kind="job"; source_type gating.
- **Output**: DetailAHSPProject (raw), DetailAHSPExpanded (expanded), HargaItemProject (auto create, harga NULL).

### 2. Harga Items
- **Input**: List item dari DetailAHSPExpanded post cascade (REF & REF_MODIFIED ikut terbaca walau read-only di Template).
- **Aktivitas**: Set harga satuan, global markup, konversi satuan.
- **Guardrail**: Visual indicator "0.00" untuk harga NULL; optimistic locking.

### 3. Rincian AHSP
- **Input**: Join expanded components + harga + markup override.
- **Aktivitas**: Review totals, export RAB, override BUK per pekerjaan (kecuali REF/REF_MODIFIED).
- **Guardrail**: Source badge menandai items hasil Segment D + menegaskan limit nested 3 level.

## Catatan QA
- Jalankan test round-trip CUSTOM → REF → CUSTOM untuk memastikan cascade enforcement berjalan.
- Pastikan Segment D tab hidden untuk REF & REF_MODIFIED selama smoke test.
- Capture error screenshot ketika mencoba nested bundle 4 level sebagai bukti loop limit aktif.
