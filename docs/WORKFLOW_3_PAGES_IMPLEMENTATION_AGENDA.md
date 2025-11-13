# WORKFLOW 3 PAGES IMPLEMENTATION AGENDA

_Referensi utama: `detail_project/WORKFLOW_3_PAGES.md` (Template AHSP → Harga Items → Rincian AHSP lifecycle)._ Agenda ini memecah dokumen referensi menjadi pekerjaan konkret, status tracking, dan kaitannya dengan script `run_validation_tests.sh` supaya setiap progres mudah diverifikasi.

---

## 1. Prinsip Arsitektur yang Harus Dipatuhi

| Area | Detail Implementasi | Referensi | Status |
| --- | --- | --- | --- |
| Dual Storage | Pertahankan pemisahan `DetailAHSPProject` (raw input), `DetailAHSPExpanded` (hasil ekspansi), dan `HargaItemProject` (master harga). | WORKFLOW_3_PAGES §Gambaran Umum. | ✅ Diterapkan (existing) |
| Manual Save + Optimistic Locking | Semua halaman wajib memakai tombol **Simpan** manual dan deteksi konflik simultan. | WORKFLOW_3_PAGES §Fase 1 & 2. | 🔄 Dijaga di regression plan |
| Bundle Cascade | Ekspansi LAIN wajib cascade dan invalidate pekerjaan yang bergantung. | WORKFLOW_3_PAGES §Segment D. | 🔄 Dalam pengawasan |
| Visual Null Harga | Harga NULL tampil sebagai "0.00" namun tetap tersimpan sebagai NULL di DB. | WORKFLOW_3_PAGES §Fase 2. | 🔄 Validasi ulang |

### 1.1 Source Type & Permission Matrix

| Source Type | Perilaku di Template AHSP | Segment yang Diizinkan | Respons Sistem Bila Melanggar |
| --- | --- | --- | --- |
| **REFERENSI** (read-only) | Data di-seed dari database referensi dan hanya bisa dilihat. | Tidak ada (view only). | Tombol edit/segment terkunci, tooltip menjelaskan bahwa pekerjaan referensi bersifat read-only. |
| **REFERENSI_MODIFIED** | User boleh menambah/menghapus/mengubah baris pada tiga segment dasar (TK/BHN/ALT) untuk menyesuaikan referensi. | Segment A–C saja; Segment D (LAIN/bundle) otomatis dinonaktifkan. | Bila user mencoba mengakses Segment D, sistem menolak dengan snackbar "Segment D khusus pekerjaan CUSTOM". |
| **CUSTOM** | User membangun komponen dari nol serta boleh menambahkan bundle dari pekerjaan lain/master. | Segment A–D aktif. Segment D menghormati batas 3 tingkat loop serta pengecekan circular. | Saat lebih dari 3 loop terdeteksi, save ditolak dengan error "Bundle depth limit (3) tercapai" sebelum data disimpan. |

_Catatan:_ Matrix ini menjadi acuan untuk semua halaman dalam workflow. Template AHSP menerapkan guard rail UI/API, Harga Items hanya memuat hasil ekspansi yang relevan, dan Rincian AHSP menampilkan status sesuai sumbernya.

---

## 2. Agenda Implementasi per Halaman

### 2.1 Template AHSP (Fase 1 – Input Komponen)

| Langkah | Deskripsi Teknis | Modul / Checklist | Status |
| --- | --- | --- | --- |
| Sidebar Filtering | Pastikan REFERENSI read-only, REFERENSI_MODIFIED hanya membuka segment A–C, dan CUSTOM membuka segment A–D. | `detail_project.views.TemplateAHSPView` filter logika. | ✅ Sudah ada, perlu regression test |
| Direct Item Input | Validasi kode unik per pekerjaan serta penyimpanan manual. | Forms/serializers + unit tests `test_create_custom_pekerjaan_appears_in_template_ahsp`. | 🔄 Perlu audit UX |
| Bundle Input | Autocomplete ref pekerjaan/ahsp + validasi target punya komponen. | API `validate_bundle_reference`, form JS. | 🔄 Perlu review API response |
| Save & Re-expand | Simpan raw → expand → cascade re-expand dependents. | Services `expand_bundle_recursive`. | 🔄 Tambahkan telemetry |

### 2.2 Harga Items (Fase 2 – Pricing)

| Langkah | Deskripsi Teknis | Modul / Checklist | Status |
| --- | --- | --- | --- |
| Item Filtering | Load dari `DetailAHSPExpanded` (TK/BHN/ALT). Pastikan bundle LAIN tersembunyi. | Queryset generator `detail_project.progress_utils`. | 🔄 Validasi ulang |
| Input Harga | Validasi non-negative, 2 desimal, auto 0 saat kosong tapi simpan NULL. | Forms/serializer + JS mask. | 🔄 Integrasi QA |
| Global Profit (BUK) | Edit `ProjectPricing.markup_percent` di layar yang sama. | Pricing API + form. | 🔄 Review UI |
| Save Flow | Optimistic locking + invalidasi cache rincian. | Pricing view/service. | 🔄 Tambahkan test coverage |

### 2.3 Rincian AHSP (Fase 3 – Review & Recap)

| Langkah | Deskripsi Teknis | Modul / Checklist | Status |
| --- | --- | --- | --- |
| Data Join | Join `DetailAHSPExpanded` dengan `HargaItemProject`. | Query helper `detail_project.views_api_tahapan_v2`. | ✅ Sudah tersedia |
| Total Kalkulasi | Terapkan formula subtotal → BUK → HSP → Volume → PPN. | `detail_project.progress_utils.compute_totals`. | 🔄 Review rounding |
| Override BUK | CRUD `Pekerjaan.markup_override_percent` (dialog). | API `/api/projects/{id}/pekerjaan/{id}/pricing/`. | 🔄 Pastikan UI/UX jelas |
| Export RAB | Konfirmasi rekap siap di-export. | Export pipeline. | ✅ Stabil |

### 2.4 Segment D (LAIN) Lifecycle

| Sub-agenda | Detail | Status |
| --- | --- | --- |
| Source Eligibility | Bundle hanya bisa di pekerjaan CUSTOM. Tambahkan guard rails di serializer & UI. | 🔄 Implementasi ulang notifikasi |
| Hierarchical Multiply | Koefisien bundle dikalikan multi-level, butuh test multi-depth. | 🔄 QA regression |
| Circular Detection | Gunakan `check_circular_dependency_pekerjaan` sebelum save. | ✅ Tersedia, perbarui test |
| Null Harga Handling | Harga auto-create sebagai NULL, UI menampilkan 0.00. | 🔄 Monitor DB konsistensi |

---

## 3. Data Sinkronisasi & Observability

1. **Invalidation Hooks** – Tiap perubahan Template/Harga wajib memicu re-expand/calc ulang dan invalidasi cache rekap.
2. **Audit Logging** – Tempelkan entry "workflow3" ke logger supaya history bundle/harga jelas.
3. **Telemetry** – Catat metric `workflow3.bundle_expansions/sec` dan `workflow3.pricing_saves` (TODO integrate ke monitoring dashboards).

---

## 4. Testing & Runbook Alignment

- Tambahan mode `workflow3` di `run_validation_tests.sh` menjalankan:
  1. `detail_project/tests/test_template_ahsp_bundle.py` (bundle lifecycle).
  2. `detail_project/tests/test_page_interactions_comprehensive.py` (Template ↔ Harga ↔ Rincian integrasi).
- Progress gating: tidak boleh deploy tanpa menjalankan `bash run_validation_tests.sh workflow3` dan melampirkan log.

---

## 5. Progress Tracker

| Tanggal | Pekerjaan | Status | Catatan |
| --- | --- | --- | --- |
| 2025-11-07 | Agenda awal disusun + run script disiapkan untuk Workflow 3 Pages. | ✅ Done | Dokumen ini + update script `workflow3` mode. |
| 2025-11-07 | Workflow3 tests dieksekusi → `test_empty_bundle_shows_error` masih gagal (status 400). | ⚠️ Known Issue | Dicatat pada status project; butuh fix di API save bundle. |

---

## 6. Agenda Synchronization Check

- **Roadmap ↔ Agenda** – `detail_project/WORKFLOW_3_PAGES.md` dan roadmap 3 halaman kini memakai matrix source type yang sama (REFERENSI read-only, REFERENSI_MODIFIED terbatas pada Segment A–C, CUSTOM penuh termasuk Segment D dengan limit loop tiga tingkat). Tidak ada konflik istilah maupun definisi segment setelah revisi terbaru.
- **Agenda ↔ User Flow** – `docs/WORKFLOW_3_PAGES_USER_FLOW_SUMMARY.md` mencerminkan checklist teknis di dokumen ini sehingga setiap opsi pengguna punya pasangan validasi & error handling pada agenda implementasi.
- **Agenda ↔ Runbook** – Mode `workflow3` di `run_validation_tests.sh` sudah terhubung langsung ke pekerjaan yang tercatat di atas; setiap progres wajib disertai log test terbaru agar status sinkron dengan eksekusi otomatis.
- **Outcome** – Dengan ketiga tautan silang tersebut, seluruh agenda sudah mengikuti alur kerja Template AHSP → Harga Items → Rincian AHSP dan menjaga tujuan akhir (bundle yang valid, harga konsisten, dan rincian siap ekspor) tanpa celah dokumentasi.

