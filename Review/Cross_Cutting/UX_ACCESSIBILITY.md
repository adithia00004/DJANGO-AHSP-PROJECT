# Cross-Cutting: UX & Accessibility Review

**Status:** `[ ]` BELUM DIREVIEW (BASELINE TERSEDIA, BELUM DI-MIGRATE)
**Terakhir diperbarui:** 2026-02-16

---

## Scope

Review User Experience dan aksesibilitas (WCAG 2.1 AA) lintas seluruh pages.

---

## Baseline Tersedia

Audit UX/A11y detail untuk halaman volume sudah tersedia di:

- `AUDIT_VOLUME_PEKERJAAN.md`

Baseline ini belum di-migrate penuh ke checklist lintas halaman (R1-R6), sehingga status dokumen tetap `[ ]`.

---

## 1. Konsistensi UI

| # | Check Item | Status | Temuan |
|---|-----------|--------|--------|
| U-1 | Color scheme konsisten antar page | `[ ]` | - |
| U-2 | Typography (font family, sizes) konsisten | `[ ]` | - |
| U-3 | Button styles konsisten | `[ ]` | - |
| U-4 | Form input styles konsisten | `[ ]` | - |
| U-5 | Spacing & padding konsisten | `[ ]` | - |
| U-6 | Icon usage konsisten | `[ ]` | - |
| U-7 | Loading states konsisten | `[ ]` | - |
| U-8 | Error message format konsisten | `[ ]` | - |
| U-9 | Toast/notification style konsisten | `[ ]` | - |
| U-10 | Empty state design konsisten | `[ ]` | - |
| U-11 | Modal dialog style konsisten | `[ ]` | - |
| U-12 | Navigation sidebar konsisten | `[ ]` | - |

## 2. Mobile Responsiveness

| # | Page | Breakpoint | Status | Temuan |
|---|------|-----------|--------|--------|
| U-13 | Landing Page | < 768px | `[ ]` | - |
| U-14 | Login/Signup | < 768px | `[ ]` | - |
| U-15 | Dashboard | < 768px | `[ ]` | - |
| U-16 | Project Form | < 768px | `[ ]` | - |
| U-17 | List Pekerjaan | < 768px | `[ ]` | - |
| U-18 | Volume Pekerjaan | < 768px | `[ ]` | - |
| U-19 | Harga Items | < 768px | `[ ]` | - |
| U-20 | Rekap RAB | < 768px | `[ ]` | - |
| U-21 | Jadwal Pekerjaan | < 768px | `[ ]` | - |
| U-22 | Checkout Page | < 768px | `[ ]` | - |
| U-23 | Referensi Database | < 768px | `[ ]` | - |
| U-24 | All pages tablet | 768-1024px | `[ ]` | - |

## 3. WCAG 2.1 AA Compliance

### Perceivable

| # | Criterion | Check | Status | Temuan |
|---|-----------|-------|--------|--------|
| U-25 | 1.1.1 Non-text Content | Alt text on images | `[ ]` | - |
| U-26 | 1.3.1 Info & Relationships | Semantic HTML (headings, lists, tables) | `[ ]` | - |
| U-27 | 1.4.1 Use of Color | Info not conveyed by color alone | `[ ]` | - |
| U-28 | 1.4.3 Contrast (Minimum) | 4.5:1 for text, 3:1 for large | `[ ]` | - |
| U-29 | 1.4.4 Resize Text | Content readable at 200% zoom | `[ ]` | - |
| U-30 | 1.4.11 Non-text Contrast | UI components 3:1 contrast | `[ ]` | - |

### Operable

| # | Criterion | Check | Status | Temuan |
|---|-----------|-------|--------|--------|
| U-31 | 2.1.1 Keyboard | All functionality via keyboard | `[ ]` | - |
| U-32 | 2.1.2 No Keyboard Trap | Focus can move away | `[ ]` | - |
| U-33 | 2.4.1 Skip Navigation | Skip-to-content link | `[ ]` | - |
| U-34 | 2.4.2 Page Titled | Descriptive page titles | `[ ]` | - |
| U-35 | 2.4.3 Focus Order | Logical tab order | `[ ]` | - |
| U-36 | 2.4.7 Focus Visible | Visible focus indicator | `[ ]` | - |

### Understandable

| # | Criterion | Check | Status | Temuan |
|---|-----------|-------|--------|--------|
| U-37 | 3.1.1 Language of Page | `lang="id"` on html | `[ ]` | - |
| U-38 | 3.2.1 On Focus | No unexpected changes | `[ ]` | - |
| U-39 | 3.3.1 Error Identification | Errors clearly identified | `[ ]` | - |
| U-40 | 3.3.2 Labels & Instructions | Form fields labeled | `[ ]` | - |
| U-41 | 3.3.3 Error Suggestion | Helpful error messages | `[ ]` | - |

### Robust

| # | Criterion | Check | Status | Temuan |
|---|-----------|-------|--------|--------|
| U-42 | 4.1.1 Parsing | Valid HTML | `[ ]` | - |
| U-43 | 4.1.2 Name, Role, Value | ARIA labels on custom controls | `[ ]` | - |

## 4. User Flows

| # | Flow | Steps | Status | Temuan |
|---|------|-------|--------|--------|
| U-44 | Signup → Trial → First Project | 5 steps | `[ ]` | - |
| U-45 | Create Project → Add Pekerjaan → Set Volume | 4 steps | `[ ]` | - |
| U-46 | Set Harga → View Rekap RAB → Export | 3 steps | `[ ]` | - |
| U-47 | Subscribe PRO → Payment → Activated | 3 steps | `[ ]` | - |
| U-48 | Import AHSP → Validate → Commit | 4 steps | `[ ]` | - |

---

## Ringkasan Temuan

| Severity | Jumlah |
|----------|--------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | 0 |
| LOW | 0 |

---

## Rekomendasi & Perbaikan

| # | Rekomendasi | Status |
|---|-------------|--------|
| - | Belum ada | - |

---

## Checklist Sign-off

- [ ] UI consistency reviewed
- [ ] Mobile responsiveness tested
- [ ] WCAG 2.1 AA compliance checked
- [ ] Key user flows validated
- [ ] Reviewer sign-off
