# REKAP KEBUTUHAN – LIVING ROADMAP & PAGE DOCUMENTATION

Last updated: 2025-12-03

---

## 1. Living Roadmap (review anytime)

This roadmap stays in sync with our iterative delivery. Each phase is scoped to 1–2 weeks and can be re‑prioritized without rewriting the entire plan.

### Phase 0 – Stabilization & Observability (Done)
| Track | Goals | Key Tasks | Exit Criteria | Status |
| --- | --- | --- | --- | --- |
| Data Integrity | Ensure `compute_kebutuhan_items()` output is canonical across web/export consumers | - Normalize filter inputs<br>- Cache rows per signature<br>- Expose `summarize_kebutuhan_rows()` for meta reuse | ✅ API returns consistent results for page + exports under multiple filters | ✅ Done (cache + filter plumbing shipped) |
| Error Recovery | Remove JS load failures that blank the page | - Fix `rekap_kebutuhan.js` encoding/regression issues<br>- Harden `ExportManager` logging<br>- Add smoke check to CI manual list | ✅ Page renders default view without console errors | ✅ Fixed (JS rebuilt, API smoke + pytest pass) |
| Documentation | Establish shareable source-of-truth for this feature | - Create this living roadmap + page doc<br>- Reference it from `ACTIVE_ROADMAPS_AUDIT.md` | ✅ Stakeholders know where to look for plans/status | ✅ Done (cross-link added) |

### Phase 1 – Advanced Filters & Pricing Context
| Track | Goals | Key Tasks | Exit Criteria | Status |
| --- | --- | --- | --- | --- |
| UX Filters | Let users slice kebutuhan by klasifikasi/sub/pekerjaan + time scopes | - Build multi-select UI for hierarchy<br>- Implement weekly/monthly selectors (hook into Tahapan/Jadwal data)<br>- Debounce search & show active chips | ✅ Filters dropdown + time range allow targeted snapshots without reloads | ✅ Done (dropdown-based filter hub + synced chips live in production) |
| Pricing Columns | Surface harga satuan & total per item | - Extend service layer to hydrate price & computed total<br>- Update table columns + exports<br>- Footer totals per kategori + overall | ✅ Users see quantity * harga = total with same numbers in export | ✅ Done (Phase 0 added harga columns + stats) |
| Performance | Keep interaction <500 ms despite new filters | - Precompute volume per time bucket<br>- Reuse cache entry for identical query<br>- Profiling & cleanup | ✅ Chrome DevTools shows <500 ms render for default project | 🟡 In Progress (cache keys expanded for filters; profiling queued) |

### Phase 2 – Timeline Intelligence (Completed ✅ 2025-12-03)
| Track | Goals | Key Tasks | Exit Criteria | Status |
| --- | --- | --- | --- | --- |
| Weekly/Monthly View | Let user pick "all project", "week X", "week X–Y", "month X–Y" | - ✅ Map jadwal/tahapan to calendar buckets<br>- ✅ API accepts range & returns split rows<br>- ✅ UI toggles between absolute & per-range totals | ✅ Visual indicator of selected period + numbers reconcile with Jadwal grid | ✅ Done |
| Timeline Polish & UX | Enhanced visual indicators, tooltips, animations for timeline view | - ✅ Enhanced period card design with badges & stats<br>- ✅ Bootstrap tooltips for item details<br>- ✅ Smooth fade/slide animations between views<br>- ✅ Responsive design (mobile/tablet/desktop)<br>- ✅ Dark mode support | ✅ Timeline view provides polished, professional UX with smooth interactions | ✅ Done |
| Notifications/Insights | Provide "what changed?" cues | - Compare current vs previous snapshot<br>- Show delta badges per item<br>- Optional export of change log | ✅ Users can export or view diff w/out manual spreadsheets | 💤 Future |
| Automation Hooks | Allow downstream systems to subscribe | - Webhook/export job definitions<br>- API tokens/permissions audit specific to Rekap Kebutuhan | ✅ Documented endpoints + sample payload | 💤 Future |

**Implementation Summary:**
- **CSS:** Added 528 lines of enhanced timeline styles in `rekap_kebutuhan_enhancements.css`
  - Period cards with slide-in animations (.rk-timeline-period)
  - Enhanced headers with badges, dates, stats (.rk-timeline-period__header)
  - Status-based color coding (active/past/future)
  - Responsive breakpoints for mobile/tablet/desktop
  - Dark mode support
- **JavaScript:** Enhanced timeline rendering in `rekap_kebutuhan.js` (120 lines)
  - Enhanced renderTimeline() with table layout and tooltips
  - initTimelineTooltips() for Bootstrap tooltip initialization
  - Smooth view transitions in setViewMode() with fade/slide effects
- **Documentation:**
  - Created `docs/PHASE_2_TIMELINE_POLISH_PLAN.md` - Complete planning document (559 lines)
  - Created `docs/PHASE_2_COMPLETION_SUMMARY.md` - Implementation summary
- **Total Implementation:** 648 lines of code + comprehensive documentation

### Phase 3 – Intelligence & Self-Serve Analytics (In Progress)
* ✅ Embedded charts (material mix + top-cost bar chart) langsung di halaman Rekap Kebutuhan
* 🔄 Dynamic grouping (by supplier, cost bucket)
* 🔄 Scenario simulation (adjust markup or price multiplier)

### Phase 4 – UI/UX Optimization & Toolbar Redesign (Completed ✅ 2025-12-03)
| Track | Goals | Key Tasks | Exit Criteria | Status |
| --- | --- | --- | --- | --- |
| Toolbar Redesign | Meningkatkan usability dan visual hierarchy toolbar tanpa menghilangkan fungsi inti | - ✅ Audit current toolbar components (export, search, stats badges)<br>- ✅ Redesign layout with improved spacing & grouping (3-section layout)<br>- ✅ Implement responsive behavior for smaller screens<br>- ✅ Add visual separators & icon improvements<br>- ✅ Enhance accessibility (keyboard nav, ARIA labels) | ✅ Toolbar lebih intuitif, compact, dan responsive dengan semua fitur tetap accessible | ✅ Done |
| Action Buttons UX | Optimize placement dan visual feedback untuk actions | - ✅ Group related actions (export + NEW refresh button)<br>- ✅ Add loading states (spinning animation) & tooltips<br>- ✅ Improve button hierarchy (primary/secondary styling)<br>- ✅ Implement keyboard shortcuts (Ctrl+R, Ctrl+F, Esc) | ✅ Users dapat mengakses actions dengan lebih efisien | ✅ Done |
| Stats Display | Enhance visibility informasi statistik real-time | - ✅ Redesign stats badges menjadi card-based dengan color-coded icons<br>- ✅ Add micro-animations for value updates (pulse effect)<br>- ✅ Implement collapsible detail view (mobile/tablet)<br>- 🔄 Show historical comparison (deferred to Phase 5) | ✅ Stats lebih prominent dan informatif dengan visual hierarchy jelas | ✅ Done |
| Search & Filter Integration | Seamless integration search dengan filter panel | - ✅ Add search clear button (X)<br>- ✅ Visual indicator untuk active filters (existing)<br>- ✅ Quick clear functionality with keyboard shortcut<br>- 🔄 Search suggestions/autocomplete (deferred - requires backend) | ✅ Users dapat clear search dengan mudah, keyboard accessible | ✅ Done |
| Mobile Responsiveness | Ensure toolbar tetap fungsional di semua screen sizes | - ✅ Implement progressive layout (desktop: 3-col, tablet: stacked, mobile: compact)<br>- ✅ Stats collapse with toggle button<br>- ✅ Touch-friendly button sizes (44px minimum)<br>- ✅ Responsive breakpoints (1200px, 992px, 768px, 576px) | ✅ Toolbar fully functional pada viewport <768px dengan proper touch targets | ✅ Done |

**Implementation Summary:**
- **HTML:** Restructured toolbar into 3 semantic sections (Actions, Search & View, Stats)
- **CSS:** New card-based stats design with color-coded icons, responsive breakpoints, animations
- **JavaScript:** New `rekap_kebutuhan_toolbar.js` handles refresh, search clear, keyboard shortcuts, stat animations
- **Accessibility:** ARIA labels, keyboard navigation, focus indicators, screen reader announcements
- **Files Modified:**
  - `templates/detail_project/rekap_kebutuhan.html` - New toolbar HTML structure
  - `static/detail_project/css/rekap_kebutuhan.css` - Toolbar V2 styles + responsive
  - `static/detail_project/js/rekap_kebutuhan_toolbar.js` - NEW enhancement script
- **Documentation:** Created `docs/TOOLBAR_REDESIGN_ANALYSIS.md` for detailed analysis and specs

---

## 2. Page Documentation

### 2.1 Purpose & Audience
Rekap Kebutuhan aggregates **resource items (TK/BHN/ALT/LAIN)** across all pekerjaan in a project. It multiplies each item’s koefisien by pekerjaan volume, applies optional markup overrides, and produces a consumable table with quantities, price references, and totals. Users rely on it to answer:
- “Berapa total pasir/m3 untuk minggu ini?”
- “Item X dari klasifikasi Y butuh berapa biaya?”
- “Apakah kebutuhan alat naik ketika jadwal digeser?”

### 2.2 Data Pipeline
1. **Source tables**: `DetailAHSPExpanded` (fully expanded komponen), `VolumePekerjaan`, `HargaItemProject`, `PekerjaanTahapan`.
2. **Service**: `services.compute_kebutuhan_items(project, mode, tahapan_id, filters)`  
   *Builds pekerjaan scope, scales komponen koefisien × bundle multiplier × volume, aggregates per unique item.*
3. **Cache**: keyed by `(project_id, signature, mode, tahapan_id, filter hash)` for 5 minutes to balance freshness/perf.
4. **Meta**: `summarize_kebutuhan_rows()` attaches `counts_per_kategori`, `quantity_totals`, `generated_at`.

### 2.3 API Endpoints
| Endpoint | Method | Description | Params |
| --- | --- | --- | --- |
| `/rekap-kebutuhan/` | GET (HTML) | Page shell | – |
| `/api/project/<pid>/rekap-kebutuhan-enhanced/` | GET | Main data feed | `mode=all/tahapan`, `tahapan_id`, `klasifikasi`, `sub_klasifikasi`, `pekerjaan` (future), `kategori`, `search`, `week_range`, `month_range` (Phase 2) |
| `/api/project/<pid>/rekap-kebutuhan/filters/` | GET | Supplies klasifikasi/sub metadata & counts | – |
| `/api/project/<pid>/export/rekap-kebutuhan/{csv|pdf|word}/` | GET | Filter-aware exports | same params as data endpoint |

### 2.4 Frontend Components
* **Filter panel**: scope buttons, klasifikasi/sub multi-select, kategori chips, time-range controls (Phase 2), search box.
  
  Collapse toggle now lets users hide/show the entire filter cluster so the table/timeline can take more vertical space.
* **Toolbar**: Export dropdown, search input, stats badges (counts + quantity totals + timestamp).
* **Table**: columns `Kategori | Kode | Uraian | Satuan | Kuantitas | Harga Satuan | Total Harga` (Phase 0 patch — cost context now visible).
* **Empty/loading states** consistent with DP design system.
* **Insight cards**: “Distribusi Kategori” pie chart + “Top Item berdasarkan biaya” bar chart (collapsible) update live for snapshot/timeline.
* **Exports**: `ExportManager` now accepts query parameters so UI state == exported file.

### 2.5 Testing Checklist
1. API hit without filters (default).
2. Filter combinations: single klasifikasi, multi-sub, tahapan scope.
3. Time range once implemented.
4. Search keyword with diacritics.
5. Exports for each format (CSV/PDF/Word) with filters applied.
6. Performance sample (devtools capture).

### 2.6 Dependencies & Riskiest Areas
- Bundle expansion math (shared with Rincian AHSP & Rekap RAB).
- Tahapan assignments for weekly distribution.
- Pricing overrides (project vs pekerjaan-level) – ensure we never double-markup.

### 2.7 References
- `detail_project/services.py` (functions: `compute_kebutuhan_items`, `summarize_kebutuhan_rows`)
- `detail_project/static/detail_project/js/rekap_kebutuhan.js`
- `detail_project/exports/rekap_kebutuhan_adapter.py`
- `docs/ACTIVE_ROADMAPS_AUDIT.md` (Week 3 focus)

---

**Usage:** keep this file updated at the end of each sprint. Link new tickets/decisions back here so the roadmap + documentation stays living and trustworthy.
