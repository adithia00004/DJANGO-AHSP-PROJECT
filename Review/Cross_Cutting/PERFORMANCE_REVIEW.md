# Cross-Cutting: Performance Review

**Status:** `[~]` BASELINE TERIMPORT, REVALIDASI SSOT BERJALAN
**Terakhir diperbarui:** 2026-02-16

---

## Scope

Review performa seluruh aspek aplikasi: database queries, API response time,
frontend loading, bundle size, dan caching strategy.

---

## Baseline Terimport (Referensi 2026-02-08)

Baseline berikut diambil dari audit sebelumnya dan akan divalidasi ulang di SSOT ini:

- Optimasi hotspot N+1 pada dashboard list sudah diterapkan.
- Optimasi hotspot export dashboard sudah diterapkan.
- Optimasi builder export di `detail_project/views_api.py` sudah diterapkan.

Sumber referensi:
- `AUDIT_PRE_LAUNCH.md`

---

## 1. Database Performance

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| P-1 | N+1 query pada list pekerjaan | `views_api.py` (tree endpoint) | `[ ]` | - |
| P-2 | N+1 query pada rekap RAB | `views_api.py` (rekap) | `[ ]` | - |
| P-3 | N+1 query pada rekap kebutuhan | `views_api.py` | `[ ]` | - |
| P-4 | select_related / prefetch_related usage | All querysets | `[ ]` | - |
| P-5 | Database indexes on FK/search fields | All models | `[ ]` | - |
| P-6 | PostgreSQL full-text search index | `AHSPReferensi` | `[ ]` | - |
| P-7 | Materialized view refresh strategy | `AHSPStats` | `[ ]` | - |
| P-8 | ParameterSequence SELECT FOR UPDATE | Lock contention | `[ ]` | - |
| P-9 | Bulk operations use bulk_create/update | Import/copy views | `[ ]` | - |
| P-10 | Query count per page load | All pages (target < 20) | `[ ]` | - |

## 2. API Response Time

| # | Endpoint Category | Target | Status | Actual |
|---|------------------|--------|--------|--------|
| P-11 | List pekerjaan tree | < 500ms | `[ ]` | - |
| P-12 | Volume pekerjaan list | < 300ms | `[ ]` | - |
| P-13 | Harga items list | < 300ms | `[ ]` | - |
| P-14 | Rekap RAB | < 1000ms | `[ ]` | - |
| P-15 | Rekap kebutuhan | < 1000ms | `[ ]` | - |
| P-16 | AHSP search (autocomplete) | < 200ms | `[ ]` | - |
| P-17 | Deep copy project | < 5000ms | `[ ]` | - |
| P-18 | Chart data (unified) | < 1000ms | `[ ]` | - |
| P-19 | Parameter sync | < 300ms | `[ ]` | - |
| P-20 | Export generation | < 10000ms | `[ ]` | - |

## 3. Frontend Performance

| # | Check Item | Target | Status | Actual |
|---|-----------|--------|--------|--------|
| P-21 | First Contentful Paint (landing) | < 2s | `[ ]` | - |
| P-22 | Time to Interactive (dashboard) | < 3s | `[ ]` | - |
| P-23 | JS bundle total size | < 1MB gzipped | `[ ]` | - |
| P-24 | CSS total size | < 200KB gzipped | `[ ]` | - |
| P-25 | Image optimization | WebP / compressed | `[ ]` | - |
| P-26 | Lazy loading for heavy modules | Gantt, Charts | `[ ]` | - |
| P-27 | Code splitting (Vite) | Per-page bundles | `[ ]` | - |
| P-28 | Vendor bundle (ECharts, etc) | Separate chunk | `[ ]` | - |
| P-29 | DOM node count (volume page) | < 3000 nodes | `[ ]` | - |
| P-30 | Memory leaks (long sessions) | No growth over time | `[ ]` | - |

## 4. Caching Strategy

| # | Check Item | Lokasi | Status | Temuan |
|---|-----------|--------|--------|--------|
| P-31 | Static file caching headers | Nginx/Django settings | `[ ]` | - |
| P-32 | Static file hashing (cache bust) | Vite build config | `[ ]` | - |
| P-33 | API response caching | Where applicable | `[ ]` | - |
| P-34 | Search cache (referensi) | `referensi/search_cache.py` | `[ ]` | - |
| P-35 | Session backend efficiency | Settings | `[ ]` | - |
| P-36 | Database connection pooling | PgBouncer config | `[ ]` | - |

## 5. Scalability

| # | Check Item | Status | Temuan |
|---|-----------|--------|--------|
| P-37 | Large project (100+ pekerjaan) | `[ ]` | - |
| P-38 | Many projects per user (50+) | `[ ]` | - |
| P-39 | Concurrent users (10+) | `[ ]` | - |
| P-40 | Export large dataset (500+ rows) | `[ ]` | - |
| P-41 | Import large Excel (1000+ rows) | `[ ]` | - |

---

## Ringkasan Temuan

| Severity | Jumlah | Items |
|----------|--------|-------|
| CRITICAL | 0 | - |
| HIGH | 0 | - |
| MEDIUM | 0 | - |
| LOW | 0 | - |

---

## Rekomendasi & Perbaikan

| # | Rekomendasi | Severity | Status |
|---|-------------|----------|--------|
| - | Belum ada | - | - |

---

## Checklist Sign-off

- [ ] Database queries optimized
- [ ] API response times acceptable
- [ ] Frontend performance acceptable
- [ ] Caching configured
- [ ] Scalability tested
- [ ] Reviewer sign-off
