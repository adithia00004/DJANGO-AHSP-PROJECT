# AHSP Workflow Data Flow Overview

Dokumen ini merangkum alur kerja end-to-end setelah implementasi Fase 0-4. Gunakan sebagai referensi cepat untuk memahami sumber input, proses yang terjadi, serta output/artefak yang dihasilkan.

## Diagram Alur Terpadu

Diagram berikut memetakan hubungan utama antar sumber input, layanan backend, penyimpanan data, serta artefak monitoring/audit. Setiap kotak hijau adalah titik interaksi UI/API, biru untuk layanan backend, abu-abu untuk storage/data tracker, dan oranye untuk artefak laporan.

```mermaid
flowchart LR
    subgraph Template_Workflow
        TUI([UI Template<br/>Grid Detail]):::ui --> TAPI([api_save_detail_ahsp_for_pekerjaan]):::svc
        TAPI --> S1[(Storage 1<br/>DetailAHSPProject)]:::data
        S1 --> S2[(Storage 2<br/>DetailAHSPExpanded)]:::data
        TAPI --> AUD[Audit Logger<br/>log_audit]:::svc
        TAPI --> CHG[ProjectChangeStatus<br/>touch_project_change]:::data
        S2 -->|Trigger bundle| CASCADE([cascade_bundle_re_expansion]):::svc --> S2
        CASCADE --> AUD
    end

    subgraph Harga_Workflow
        HUI([UI Harga Items]):::ui --> HAPI([api_save_harga_items]):::svc --> HP[(HargaItemProject + Markup)]:::data
        HAPI --> CHG
        HP --> ORPHAN([detect_orphaned_items]):::svc --> CLEAN([cleanup_orphans/api_cleanup]):::svc --> HP
        CLEAN --> CHG
    end

    subgraph Rincian_Workflow
        RUI([UI Rincian AHSP]):::ui --> RVIEW([views.rincian_ahsp_view]):::svc --> S2
        RUI --> SYNC([Sync Indicator JS]):::svc --> STATUSAPI([GET /api/project/<id>/change-status]):::svc --> CHG
    end

    subgraph Commands_Monitoring
        VALCMD([manage.py validate_ahsp_data]):::cli --> VALIDATE([services.validate_project_data]):::svc --> REPORT{{Laporan JSON/CLI}}:::out
        FIXCMD([manage.py fix_ahsp_data]):::cli --> FIX([services.fix_project_data]):::svc --> S2
        FIX --> CLEAN
        FIX --> CHG
    end

    AUD --> AUDIT[(DetailAHSPAudit)]:::data --> AUDAPI([GET /api/.../audit-trail]):::svc --> RUI

    classDef ui fill:#c6f6d5,stroke:#2f855a;
    classDef svc fill:#bee3f8,stroke:#2b6cb0;
    classDef data fill:#e2e8f0,stroke:#4a5568;
    classDef cli fill:#fefcbf,stroke:#b7791f;
    classDef out fill:#fed7d7,stroke:#c53030;

    class REPORT out;
```

## Diagram Interaksi Per Halaman

### Template AHSP Page

Template page menerima data struktur pekerjaan melalui `api_get_detail_ahsp`, menulis ulang storage via `api_save_detail_ahsp_for_pekerjaan`, dan (khusus REF_MOD) bisa melakukan reset ke referensi melalui `api_reset_detail_ahsp_to_ref`. Perubahan yang dilakukan menghasilkan sinyal ke halaman Harga maupun Rincian melalui Change Status API.

```mermaid
sequenceDiagram
    participant Template as Template AHSP UI
    participant DetailAPI as api_get/save/reset_detail_ahsp
    participant Raw as DetailAHSPProject
    participant Expanded as DetailAHSPExpanded
    participant Audit as DetailAHSPAudit
    participant Change as /api/project/<id>/change-status
    participant Harga as Harga Items UI
    participant Rincian as Rincian AHSP UI

    Template->>DetailAPI: GET api_get_detail_ahsp (prefill)
    DetailAPI-->>Template: rows[], bundles, locking token (Raw+Expanded)
    Template->>DetailAPI: POST api_save_detail_ahsp_for_pekerjaan
    DetailAPI->>Raw: Replace input rows
    DetailAPI->>Expanded: Rebuild expanded rows + cascade bundles
    DetailAPI->>Audit: log_audit(action=CREATE/UPDATE/DELETE/CASCADE)
    DetailAPI->>Change: touch_project_change(ahsp=True)
    Change-->>Harga: Flag AHSP changed (polled via GET change-status)
    Change-->>Rincian: Flag AHSP changed
    Template->>DetailAPI: POST api_reset_detail_ahsp_to_ref (REF_MOD only)
    DetailAPI-->>Template: Fresh rows cloned dari referensi
    Template->>Change: Poll GET change-status (mengetahui update harga)
```

### Harga Items Page

Harga page hanya menerima daftar item yang sudah diexpand oleh Template. Ia memuat data via `api_list_harga_items`, menyimpan nilai melalui `api_save_harga_items`, serta menangani orphan melalui `api_list_orphaned_harga_items` dan `api_cleanup_orphaned_harga_items`. Setiap penyimpanan atau cleanup memberi sinyal perubahan ke Template/Rincian agar mereka bisa me-refresh data harga.

```mermaid
sequenceDiagram
    participant Harga as Harga Items UI
    participant HargaAPI as api_list/save/cleanup_harga_items
    participant Expanded as DetailAHSPExpanded
    participant HargaStore as HargaItemProject
    participant OrphanSvc as detect_orphaned_items
    participant Change as /api/project/<id>/change-status
    participant Template as Template AHSP UI
    participant Rincian as Rincian AHSP UI

    Harga->>HargaAPI: GET api_list_harga_items
    HargaAPI->>Expanded: Baca daftar komponen aktif
    HargaAPI->>HargaStore: Join harga eksisting
    HargaAPI-->>Harga: Items[], markup, client_updated_at
    Harga->>HargaAPI: GET api_list_orphaned_harga_items
    HargaAPI->>OrphanSvc: detect_orphaned_items()
    HargaAPI-->>Harga: daftar orphan
    Harga->>HargaAPI: POST api_save_harga_items
    HargaAPI->>HargaStore: Upsert harga + markup/PPN
    HargaAPI->>Change: touch_project_change(harga=True)
    Change-->>Template: Flag harga berubah (badge sinkron)
    Change-->>Rincian: Flag harga berubah
    Harga->>HargaAPI: POST api_cleanup_orphaned_harga_items (opsional)
    HargaAPI->>HargaStore: Delete orphan + cascade marker
    HargaAPI->>Change: touch_project_change(harga=True)
```

### Rincian AHSP Page

Rincian page merangkum output Template + Harga. Ia memanggil `api_get_rincian_rab` untuk mengambil kombinasi koefisien & harga, menampilkan status sinkron lewat `api_get_change_status`, dan dapat membuka audit trail melalui `api_get_audit_trail`.

```mermaid
sequenceDiagram
    participant Rincian as Rincian AHSP UI
    participant RABAPI as api_get_rincian_rab
    participant Expanded as DetailAHSPExpanded
    participant HargaStore as HargaItemProject
    participant Change as /api/project/<id>/change-status
    participant AuditAPI as api_get_audit_trail
    participant Template as Template AHSP UI
    participant Harga as Harga Items UI

    Rincian->>RABAPI: GET api_get_rincian_rab
    RABAPI->>Expanded: Ambil koef & sumber bundle
    RABAPI->>HargaStore: Ambil harga, markup, BUK/PPN
    RABAPI-->>Rincian: payload rincian (per pekerjaan + total)
    Rincian-->>Template: Tandai sinkron (opsional) bila data sudah direview
    Rincian->>Change: Poll GET change-status untuk memantau update Template/Harga
    Change-->>Rincian: Timestamp last_ahsp_change + last_harga_change
    Rincian->>AuditAPI: GET api_get_audit_trail (lihat histori perubahan)
    AuditAPI-->>Rincian: daftar audit (CREATE/UPDATE/DELETE/CASCADE)
```
## 1. Template AHSP Workflow

| Tahap | Input | Proses | Output |
|-------|-------|--------|--------|
| 1. UI/API submit detail pekerjaan | Payload `rows[]` (kategori, kode, uraian, satuan, koef, ref_kind/ref_id) | `views_api.api_save_detail_ahsp_for_pekerjaan`
- Validasi kategori/duplikat, bundle ref
- Audit snapshot lama (`snapshot_pekerjaan_details`)
- Tulis Storage 1 (`DetailAHSPProject`)
- Populate Storage 2 (`DetailAHSPExpanded`)
- Cascade re-expansion jika bundle terkait
- Logging audit (`log_audit` action CREATE/UPDATE/DELETE)
- Update change tracker (`touch_project_change(ahsp=True)` + `detail_last_modified`) | - Storage 1 & 2 sinkron
- Audit entry per perubahan
- `ProjectChangeStatus.last_ahsp_change`
- Cascade results untuk pekerjaan lain |
| 2. Cascade (otomatis) | Trigger dari step 1 | `services.cascade_bundle_re_expansion`
- Re-expand pekerjaan yang mereferensi target
- Logging metrics & audit CASCADE
- Update `detail_last_modified` pekerjaan terdampak | - Storage 2 terbarui untuk chain bundle
- Audit action CASCADE |

## 2. Harga Items Workflow

| Tahap | Input | Proses | Output |
|-------|-------|--------|--------|
| 1. UI/API submit harga + markup | Payload `items[]`, `markup_percent`, `client_updated_at` | `views_api.api_save_harga_items`
- Validasi numeric/duplikat
- Update `HargaItemProject`
- Simpan markup/PPN
- Trigger change tracker (`touch_project_change(harga=True)`) | - Harga terkini
- Profit/Margin terkini
- `ProjectChangeStatus.last_harga_change` |
| 2. Orphan detection | - | `services.detect_orphaned_items()` (dipakai UI, command, validation) | Daftar orphan (id, kode, metadata) |
| 3. Orphan cleanup | Pilihan item (UI) atau parameter command | - UI `api_cleanup_orphaned_harga_items`
- Command `cleanup_orphans` (dry-run/limit)
- Fase 4 `fix_ahsp_data` dapat memanggil cleanup | - Item orphan dihapus
- `touch_project_change(harga=True)` bila ada yang hilang |

## 3. Rincian AHSP Workflow

| Tahap | Input | Proses | Output |
|-------|-------|--------|--------|
| 1. Rendering | Project ID | `views.rincian_ahsp_view`
- Menyediakan data Storage 2
- Menyertakan `ProjectChangeStatus` untuk badge sinkron | Halaman Rincian AHSP dengan data expand |
| 2. Sink indicator polling | - | Komponen `_sync_indicator.html` + `sync_indicator.js`
- Poll `GET /api/project/<id>/change-status/`
- Bandingkan timestamp AHSP/Harga/Pekerjaan
- Badge + tombol "Tandai sinkron"
- Opsional toggle auto refresh (Rincian) | Notifikasi perubahan lintas halaman; auto-reload jika diaktifkan |

## 4. Change Status API

`GET /api/project/<id>/change-status/`
- Query parameters (opsional): `since_ahsp`, `since_harga`, `pekerjaan_since`
- Response: `ahsp_changed_at`, `harga_changed_at`, `affected_pekerjaan_count`, `recent_pekerjaan[]`
- Di-backend memakai `ProjectChangeStatus` + `Pekerjaan.detail_last_modified`.

## 5. Audit Trail

| Sumber | Proses | Output |
|--------|--------|--------|
| Template save/reset | `log_audit` menulis `DetailAHSPAudit` (snapshot lama/baru, summary) | Riwayat CREATE/UPDATE/DELETE |
| Cascade re-expansion | `log_audit` action CASCADE (`triggered_by='cascade'`) | Entry CASCADE + ringkasan chain |
| UI audit trail | `GET /api/project/<id>/audit-trail/` + halaman `audit_trail.html` (filter, diff) | Timeline perubahan |

## 6. Validation & Migration Tools

| Command | Input | Proses | Output |
|---------|-------|--------|--------|
| `python manage.py validate_ahsp_data` | `--project-id` atau `--all-projects`, `--orphan-threshold`, `--output=report.json` | Memanggil `services.validate_project_data`
- Identifikasi bundle invalid, circular, mismatch expansion, orphan | Laporan per project (CLI + opsi JSON) |
| `python manage.py fix_ahsp_data` | `--project-id/--all-projects`, `--dry-run`, `--no-reexpand`, `--no-cleanup`, `--older-than-days`, `--limit` | Memanggil `services.fix_project_data`
- Re-expand Storage 2
- Cleanup orphans (reusing helper Fase?1)
- Update change tracker | Ringkasan aksi (CLI), Storage 2 kembali sinkron |

## 7. Referensi Dokumen

- `detail_project/WORKFLOW_3_PAGES.md` - narasi lengkap alur Template ? Harga ? Rincian.
- `docs/DUAL_STORAGE_ARCHITECTURE.md` - struktur storage ganda & dependensi.
- `detail_project/IMPLEMENTATION_ROADMAP.md` - status & catatan detail per fase.
- `detail_project/tests/test_*` - contoh penggunaan helper/command.

## Alur Per Jenis Sumber Pekerjaan (`source_type`)

### 1. Referensi (`source_type = ref`)

```mermaid
flowchart LR
    REF_START([Pilih pekerjaan Referensi]) --> REF_VIEW[GET api_get_detail_ahsp<br/>Mode: read-only]
    REF_VIEW --> REF_ROUTES{Aksi lanjut?}
    REF_ROUTES -->|Lihat harga / export| RINCIAN[Halaman Rincian (GET api_get_rincian_rab)]
    REF_ROUTES -->|Butuh modifikasi?| CLONE[Clone jadi REF_MOD melalui UI Rincian Gabungan]
    REF_ROUTES -->|Tetap referensi| DONE_REF([Tidak ada penulisan data])
```

Karena read-only, Template page hanya memuat data; perubahan dilakukan dengan menyalin ke jenis lain.

### 2. Referensi Modifikasi (`source_type = ref_modified`)

```mermaid
flowchart LR
    RM_START([Buka pekerjaan REF_MOD]) --> RM_GET[GET api_get_detail_ahsp<br/>segment A/B/C editable]
    RM_GET --> RM_EDIT[Edit TK/BHN/ALT, tanpa bundle]
    RM_EDIT --> RM_SAVE[POST api_save_detail_ahsp_for_pekerjaan<br/>Validasi + cascade expand]
    RM_SAVE --> RM_CHANGE[Change Status update: ahsp=True]
    RM_EDIT --> RM_RESET[Opsional: POST api_reset_detail_ahsp_to_ref]
    RM_RESET --> RM_GET
    RM_SAVE --> RINCIAN[Data baru dikonsumsi Harga/Rincian]
```

Fitur bundle dan segment D tetap terkunci; alur fokus pada menjaga kesesuaian dengan referensi sambil mencatat audit dan change tracker.

> Catatan: per 2025-11-14, saat pekerjaan berpindah dari REF ke REF_MODIFIED seluruh detail referensi dipindahkan ke pekerjaan lama dan storage expand (`DetailAHSPExpanded`) langsung dibangun ulang. Dengan begitu daftar Harga Items dan halaman Rincian tidak lagi kosong setelah pergantian sumber.

### 3. Custom (`source_type = custom`)

```mermaid
flowchart LR
    C_START([Buka pekerjaan CUSTOM]) --> C_GET[GET api_get_detail_ahsp<br/>Semua segment editable]
    C_GET --> C_EDIT[Tambah/edit TK/BHN/ALT/LAIN termasuk bundle]
    C_EDIT --> C_SAVE[POST api_save_detail_ahsp_for_pekerjaan]
    C_SAVE --> C_EXPAND[Rebuild DetailAHSPExpanded + cascade bundle]
    C_SAVE --> C_AUDIT[Audit log + Change Status ahsp=True]
    C_EXPAND --> HARGA[Harga Items GET api_list_harga_items (items baru?)]
    HARGA --> RINCIAN[Harga + koef digunakan di Rincian]
```

Jenis CUSTOM memiliki alur paling lengkap: bisa menjadi sumber bundle untuk pekerjaan lain, memicu penambahan item harga baru, dan seluruh perubahan tercermin di halaman Harga serta Rincian.

---
_Diperbarui: 2025-11-14_
