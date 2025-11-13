# WORKFLOW 3 PAGES - IMPLEMENTATION AGENDA

## Tujuan
- Menyelesaikan integrasi 3 halaman utama (Template AHSP, Harga Items, Rincian AHSP) sesuai roadmap terbaru.
- Memastikan akses Segment D (LAIN) mengikuti guardrail yang sama dengan dokumentasi detail_project.
- Menetapkan referensi tunggal untuk batasan REFERENSI / REFERENSI_MODIFIED / CUSTOM.

## Guardrail Standar (Harus Dipakai di Semua Dokumen)
> **Guardrail — Source Types & Segment D (LAIN) Access**
> - **REFERENSI (REF)** — read-only di Template AHSP. Tab/Segment D (LAIN) disembunyikan; tidak bisa menambah bundle. Semua perubahan hanya boleh lewat import referensi atau workflow Rincian Gabungan.
> - **CUSTOM** — satu-satunya source_type yang fully editable di Template AHSP. Segment D (LAIN) selalu aktif, boleh referensi pekerjaan proyek (job) atau AHSP master, dan tunduk pada validasi empty-target + circular check.
> - **REFERENSI_MODIFIED (REF_MODIFIED)** — clone dari REF yang diedit di halaman "Rincian AHSP Gabungan". Di Template AHSP tampil sebagai read-only mirip REF dan Segment D tetap terkunci.
> - **Segment D Loop Limit** — Bundle hanya boleh nested maksimal 3 level (A→B→C). Level ke-4 otomatis di-block dengan error "Maksimum kedalaman bundle terlampaui".
> - **Cascade Enforcement** — Saat pekerjaan target diubah, sistem wajib menjalankan cascade re-expansion untuk semua pekerjaan yang mereferensikannya. User tidak bisa bypass guardrail ini karena edit manual di expanded rows memang tidak tersedia.

## Agenda Implementasi
1. **Template AHSP**
   - Audit form binding untuk memastikan state source_type menentukan enable/disable Segment D.
   - Terapkan validator baru "target must have components" untuk LAIN ref_kind="job" dan bubble error hingga toast.
   - Logging cascade trigger agar QA bisa memverifikasi guardrail Cascade Enforcement berjalan.
2. **Harga Items**
   - Pastikan list hanya mengambil DetailAHSPExpanded (post cascade) sehingga REF/REF_MODIFIED yang read-only tetap ter-cover.
   - Tambah badge "Guardrail Applied" ketika harga berasal dari expanded bundle sebagai indikator QA.
3. **Rincian AHSP**
   - Render source badge `[Bundle_B]` + state highlight sesuai Segment D guardrail.
   - Pastikan override markup tidak bisa mengedit pekerjaan REF/REF_MODIFIED.
4. **QA Checklist**
   - Simulasikan 3 user flow (REF, CUSTOM, REF_MODIFIED) dan capture bukti guardrail aktif.
   - Uji nested bundle 4 level dan pastikan error keluar di level ke-4.

## Deliverables
- Patch di `detail_project/views` untuk validator bundle + cascade log.
- Update dokumentasi (file ini + user flow summary) menggunakan guardrail standar.
- Bukti QA (screen/video) menunjukkan guardrail Segment D dan limit loop.
