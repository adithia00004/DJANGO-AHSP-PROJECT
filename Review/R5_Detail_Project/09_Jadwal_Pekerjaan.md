# R5.9 - Review Jadwal Pekerjaan (Gantt + Kurva-S)

**Status:** `[ ]` BELUM DIREVIEW
**Terakhir diperbarui:** -

---

## Informasi Umum

| Atribut | Detail |
|---------|--------|
| URL | `/detail_project/<project_id>/jadwal-pekerjaan/` |
| View | `detail_project.views.jadwal_pekerjaan_view` |
| Template | `detail_project/templates/detail_project/jadwal_pekerjaan.html` |
| Sub-templates | `_gantt_tab.html`, `_grid_tab.html`, `_kurva_s_tab.html` |
| JS (Core) | `src/jadwal_kegiatan_app.js` |
| JS (Gantt) | `src/modules/gantt/gantt-chart-redesign.js`, `GanttCanvasOverlay.js` |
| JS (Grid) | `src/modules/grid/tanstack-grid-manager.js` |
| JS (Kurva-S) | `src/modules/kurva-s/uplot-chart.js` |
| CSS | `gantt-chart-redesign.css`, `kelola_tahapan_grid.css` |

### API Endpoints (v2 - Weekly Canonical)

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| GET | `api/v2/project/<id>/tahapan/` | Get tahapan |
| POST | `api/v2/project/<id>/tahapan/save/` | Save tahapan |
| GET | `api/v2/project/<id>/pekerjaan/<pid>/assignments/` | Get assignments |
| POST | `api/v2/project/<id>/regenerate-tahapan/` | Regenerate |
| POST | `api/v2/project/<id>/week-boundary/` | Update weeks |
| POST | `api/v2/project/<id>/reset-progress/` | Reset progress |
| GET | `api/v2/project/<id>/chart-data/` | Chart data |
| GET | `api/v2/project/<id>/kurva-s-data/` | S-curve volume |
| GET | `api/v2/project/<id>/kurva-s-harga/` | S-curve cost |

---

## Audit Fungsional

### Tab Grid (Kelola Tahapan)

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-1 | Grid tampil dengan data | Weekly progress grid | `[ ]` |
| TC-2 | Input progress per minggu | Value tersimpan | `[ ]` |
| TC-3 | Total progress = 100% max | Validation enforced | `[ ]` |
| TC-4 | Week boundaries config | Start/end day configurable | `[ ]` |
| TC-5 | Save progress | API save works | `[ ]` |
| TC-6 | Regenerate dari canonical | Data regenerated | `[ ]` |
| TC-7 | Reset all progress | Data cleared with confirm | `[ ]` |

### Tab Gantt Chart

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-8 | Gantt bars render | Bars sesuai durasi | `[ ]` |
| TC-9 | Gantt scroll horizontal | Smooth scroll | `[ ]` |
| TC-10 | Gantt zoom levels | Zoom in/out works | `[ ]` |
| TC-11 | Gantt overlay canvas | Canvas synced with data | `[ ]` |
| TC-12 | Tooltip on hover | Info pekerjaan tampil | `[ ]` |

### Tab Kurva-S

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-13 | S-curve volume render | Chart line correct | `[ ]` |
| TC-14 | S-curve harga render | Cost curve correct | `[ ]` |
| TC-15 | Planned vs Actual lines | Both lines visible | `[ ]` |
| TC-16 | Chart tooltip | Data point info | `[ ]` |
| TC-17 | Canvas overlay sync | Overlay accurate | `[ ]` |

### General

| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| TC-18 | Tab switching | State preserved | `[ ]` |
| TC-19 | Empty project (no schedule) | Empty state UI | `[ ]` |
| TC-20 | Large project performance | Render < 3 sec | `[ ]` |
| TC-21 | Fullscreen mode | Toggle works | `[ ]` |
| TC-22 | Export chart | Export functionality | `[ ]` |
| TC-23 | IDOR protection | Owner check | `[ ]` |

---

## Temuan (Findings)

| # | Severity | Deskripsi | Langkah Reproduksi | Evidence |
|---|----------|-----------|---------------------|----------|
| - | - | Belum ada temuan | - | - |

---

## Rekomendasi

| # | Rekomendasi | Prioritas | Effort |
|---|-------------|-----------|--------|
| - | Belum ada rekomendasi | - | - |

---

## Aktivitas Perbaikan

| # | Tanggal | Deskripsi Perbaikan | Commit/PR | Status |
|---|---------|---------------------|-----------|--------|
| - | - | Belum ada perbaikan | - | - |

---

## Checklist Sign-off

- [ ] Grid tab OK
- [ ] Gantt tab OK
- [ ] Kurva-S tab OK
- [ ] Data accuracy
- [ ] Performance OK
- [ ] Security OK
- [ ] Reviewer sign-off
