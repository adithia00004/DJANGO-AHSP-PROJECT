# IMPLEMENTATION ROADMAP
## Template AHSP, Harga Items, dan Rincian AHSP Enhancement

**Document Version:** 1.1
**Last Updated:** 2025-11-13
**Status:** In Progress - FASE 0

---

## 📊 IMPLEMENTATION PROGRESS

| Phase | Status | Start Date | End Date | Progress |
|-------|--------|------------|----------|----------|
| **FASE 0: Preparation** | ✅ Completed | 2025-11-13 | 2025-11-13 | 100% (3/3) |
| FASE 1: Orphan Cleanup | ⚪ Not Started | - | - | 0% |
| FASE 2: Audit Trail | ⚪ Not Started | - | - | 0% |
| FASE 3: Sync Indicators | ⚪ Not Started | - | - | 0% |
| FASE 4: Migration Tools | ⚪ Not Started | - | - | 0% |

**Overall Progress:** 20% (3 of 15 tasks completed)

**Legend:**
- ✅ Completed
- 🟡 In Progress
- ⚪ Not Started
- ❌ Blocked

---

## EXECUTIVE SUMMARY

Dokumen ini menyusun **agenda bertahap** untuk implementasi enhancement berdasarkan:
- WORKFLOW_3_PAGES.md (completed documentation)
- 8 critical feedback points dari user
- TODO items yang teridentifikasi

**Prinsip Implementasi:**
1. **Incremental**: Implementasi bertahap, setiap fase bisa di-deploy independent
2. **Backward Compatible**: Tidak break existing functionality
3. **Tested**: Setiap fase harus punya test coverage
4. **Documented**: Update dokumentasi setelah implementasi

---

## CURRENT STATUS

### ✅ COMPLETED (Production Ready)
- [x] Dual storage architecture (DetailAHSPProject + DetailAHSPExpanded + HargaItemProject)
- [x] Bundle expansion mechanism (ref_kind='job' dan 'ahsp')
- [x] Cascade re-expansion (cascade_bundle_re_expansion)
- [x] Empty bundle validation
- [x] Circular dependency protection
- [x] Max depth validation (3 levels)
- [x] Optimistic locking (conflict resolution)
- [x] Manual save workflow
- [x] Override markup/BUK per-pekerjaan
- [x] Source type handling (REF/REF_MODIFIED/CUSTOM)

### ⚠️ TODO (Enhancement Needed)
- [ ] Orphan cleanup mechanism
- [ ] Cross-page sync indicators
- [ ] Audit trail system
- [ ] Migration/validation strategy for legacy data
- [ ] Observability & monitoring improvements
- [ ] Bundle complexity isolation (optional refactoring)

---

## ROADMAP PHASES

Implementasi dibagi menjadi **4 fase utama**, setiap fase memiliki deliverable yang jelas dan dapat di-deploy independent.

---

## FASE 0: PREPARATION & VALIDATION (Week 1)

**Status:** ✅ COMPLETED (100% - 3/3 tasks completed)
**Duration:** 2025-11-13 (1 day)
**Tujuan:** Validasi current state dan persiapan infrastructure untuk enhancement

### Tasks:

#### 0.1 Data Audit & Validation ✅
**Priority:** CRITICAL
**Effort:** 2-3 days
**Status:** ✅ COMPLETED (2025-11-13)
**Commit:** a932a44

**Deliverables:**
1. ✅ **Script: audit_current_data.py** (620 lines)
   - Check for orphaned HargaItemProject
   - Check for circular dependencies in existing bundles (DFS algorithm)
   - Check for stale expanded data (timestamp comparison)
   - Check for empty bundles (LAIN → empty pekerjaan)
   - Check for max depth violations (>3 levels)
   - Check for expansion integrity (raw vs expanded)
   - CLI options: --project-id, --all-projects, --detailed, --output
   - Markdown report generation

   **Location:** `detail_project/management/commands/audit_current_data.py`

2. ✅ **Documentation: FASE_0_AUDIT_GUIDE.md** (700+ lines)
   - Usage guide with examples
   - Output interpretation (clean vs problematic projects)
   - Success criteria thresholds
   - Action plans for each issue type
   - Troubleshooting guide
   - Maintenance schedule recommendations

   **Location:** `detail_project/FASE_0_AUDIT_GUIDE.md`

**Success Criteria:**
- ✅ Know exact count of orphaned items (6 checks implemented)
- ✅ Know if any circular dependencies exist (DFS cycle detection)
- ✅ Know if cascade re-expansion working correctly (timestamp validation)
- ✅ Comprehensive documentation for operators

---

#### 0.2 Test Coverage Baseline ✅
**Priority:** HIGH
**Effort:** 2-3 days
**Status:** ✅ COMPLETED (2025-11-13)
**Commit:** a932a44

**Deliverables:**
1. ✅ **Test Suite: test_workflow_baseline.py** (850+ lines)
   - ✅ Test bundle creation (ref_kind='job')
   - ✅ Test cascade re-expansion (NEW! Previously untested)
   - ✅ Test empty bundle validation
   - ✅ Test circular dependency protection (self-ref, 2-level, 3-level)
   - ✅ Test optimistic locking (client_updated_at conflicts)
   - ✅ Test source_type restrictions (REF/REF_MODIFIED/CUSTOM)
   - ✅ Test max depth validation (3 levels)
   - ✅ Test dual storage integrity (raw ↔ expanded)

   **7 Test Classes, 14+ Test Methods**
   **Location:** `detail_project/tests/test_workflow_baseline.py`

2. ✅ **Documentation: FASE_0_TESTING_GUIDE.md** (800+ lines)
   - Test structure breakdown
   - Running tests guide (pytest commands)
   - Coverage measurement instructions (pytest-cov)
   - Integration with existing test suite
   - Gap analysis documentation
   - CI/CD setup example (GitHub Actions)
   - Troubleshooting guide

   **Location:** `detail_project/FASE_0_TESTING_GUIDE.md`

**Success Criteria:**
- ✅ All current functionality has test coverage (7 test classes)
- ✅ Baseline established for regression testing
- ⚠️ Coverage measurement pending (requires pytest-cov in production)
- ✅ **KEY ACHIEVEMENT:** cascade_bundle_re_expansion() now has comprehensive tests!

---

#### 0.3 Monitoring Setup ✅
**Priority:** MEDIUM
**Effort:** 1-2 days
**Status:** ✅ COMPLETED (2025-11-13)
**Commit:** (pending)

**Deliverables:**
1. ✅ **monitoring_helpers.py** (680 lines)
   - ✅ Structured logging functions (log_operation, log_error)
   - ✅ Performance monitoring decorator (@monitor)
   - ✅ Metrics collector class (MetricsCollector)
   - ✅ Operation-specific helpers:
     - log_bundle_expansion()
     - log_cascade_operation()
     - log_circular_dependency_check()
     - log_optimistic_lock_conflict()
     - log_orphan_detection()

   **Location:** `detail_project/monitoring_helpers.py`

2. ✅ **Integration in services.py**
   - ✅ cascade_bundle_re_expansion() - timing, depth, re-expanded count
   - ✅ check_circular_dependency_pekerjaan() - circular detection logging
   - ✅ Imports: log_operation, log_cascade_operation, log_circular_dependency_check

3. ✅ **Integration in views_api.py**
   - ✅ api_save_detail_ahsp_for_pekerjaan() - optimistic lock conflict logging
   - ✅ Imports: log_optimistic_lock_conflict, collect_metric

4. ✅ **Documentation: FASE_0_MONITORING_GUIDE.md** (800+ lines)
   - Structured logging format specification
   - Metrics collection guide
   - Usage examples for all operation types
   - Monitoring dashboard queries
   - Alerting rules (cascade depth, conflicts, circular deps)
   - Log analysis examples (grep, Python)
   - Production integration (Prometheus, CloudWatch)
   - Troubleshooting guide

   **Location:** `detail_project/FASE_0_MONITORING_GUIDE.md`

**Success Criteria:**
- ✅ Can monitor bundle usage via structured logs
- ✅ Can track cascade operations with depth and duration
- ✅ Can detect circular dependencies proactively
- ✅ Can track optimistic lock conflicts
- ✅ Metrics collection available for aggregation
- ✅ Performance metrics tracked (duration_ms for operations)
- ✅ Production-ready with external monitoring integration examples

---

## FASE 1: ORPHAN CLEANUP MECHANISM (Week 2-3)

**Tujuan:** Implement automated cleanup untuk orphaned HargaItemProject

**Rationale:** Ini adalah TODO item yang paling sering mentioned di dokumentasi dan paling impact ke data quality.

### Tasks:

#### 1.1 Orphan Detection API
**Priority:** HIGH
**Effort:** 2 days

**Deliverables:**
1. **API Endpoint:** `GET /api/projects/{id}/orphaned-items/`
   ```json
   Response:
   {
     "ok": true,
     "orphaned_count": 15,
     "orphaned_items": [
       {
         "id": 123,
         "kode": "L.99",
         "uraian": "Item Lama",
         "kategori": "TK",
         "harga_satuan": 150000,
         "last_used": "2024-12-01",
         "can_delete": true,
         "safety_note": "Item ini tidak digunakan di DetailAHSPExpanded manapun"
       }
     ],
     "total_value": 2500000
   }
   ```

2. **Service Function:** `detect_orphaned_items(project)`
   - Query: HargaItemProject NOT IN (SELECT DISTINCT kode FROM DetailAHSPExpanded)
   - Return: list of orphaned items with metadata

**Success Criteria:**
- ✓ Can detect orphaned items accurately
- ✓ No false positives (items still in use not flagged)

---

#### 1.2 Manual Cleanup UI
**Priority:** HIGH
**Effort:** 2 days

**Deliverables:**
1. **UI: Orphan Cleanup Page** (detail_project/orphan_cleanup.html)
   - Show list of orphaned items
   - Checkboxes untuk select items to delete
   - "Select All" functionality
   - Preview total value being deleted
   - Confirmation dialog before delete

2. **API Endpoint:** `POST /api/projects/{id}/orphaned-items/cleanup/`
   ```json
   Request:
   {
     "item_ids": [123, 456, 789],
     "confirm": true
   }

   Response:
   {
     "ok": true,
     "deleted_count": 3,
     "total_value_deleted": 450000,
     "message": "3 orphaned items berhasil dihapus"
   }
   ```

**Success Criteria:**
- ✓ User dapat melihat dan delete orphaned items via UI
- ✓ Confirmation dialog prevents accidental deletion

---

#### 1.3 Automated Cleanup (Optional)
**Priority:** LOW
**Effort:** 1 day

**Deliverables:**
1. **Management Command:** `python manage.py cleanup_orphans`
   - Find orphans older than X days (configurable)
   - Dry-run mode (--dry-run flag)
   - Delete with logging

2. **Cron Job Setup** (optional)
   - Run weekly/monthly
   - Email report to admin

**Success Criteria:**
- ✓ Can run automated cleanup via cron
- ✓ Dry-run works correctly (no deletion, only report)

---

## FASE 2: AUDIT TRAIL SYSTEM (Week 4-5)

**Tujuan:** Implement audit trail untuk tracking changes dan debugging

### Tasks:

#### 2.1 Audit Model & Infrastructure
**Priority:** HIGH
**Effort:** 2 days

**Deliverables:**
1. **Model: DetailAHSPAudit**
   ```python
   class DetailAHSPAudit(TimeStampedModel):
       project = ForeignKey(Project)
       pekerjaan = ForeignKey(Pekerjaan)
       action = CharField(choices=[
           ('CREATE', 'Create'),
           ('UPDATE', 'Update'),
           ('DELETE', 'Delete'),
           ('CASCADE', 'Cascade Re-expansion'),
       ])

       # Snapshot data
       old_data = JSONField(null=True, blank=True)
       new_data = JSONField(null=True, blank=True)

       # Metadata
       triggered_by = CharField(max_length=20)  # 'user' or 'cascade'
       user = ForeignKey(User, null=True, blank=True)
       change_summary = TextField()  # Human readable summary

       class Meta:
           ordering = ['-created_at']
           indexes = [
               models.Index(fields=['project', '-created_at']),
               models.Index(fields=['pekerjaan', '-created_at']),
           ]
   ```

2. **Migration:** `0XXX_add_audit_trail.py`

**Success Criteria:**
- ✓ Model dapat store audit data
- ✓ Indexes untuk fast query

---

#### 2.2 Audit Logging Integration
**Priority:** HIGH
**Effort:** 3 days

**Deliverables:**
1. **Audit Helper:** `services.py::log_audit()`
   ```python
   def log_audit(
       project, pekerjaan, action,
       old_data=None, new_data=None,
       triggered_by='user', user=None
   ):
       # Create audit entry
       # Generate change_summary (e.g., "Added 3 TK items, deleted 1 BHN")
       pass
   ```

2. **Integration Points:**
   - `api_save_detail_ahsp_for_pekerjaan()`: log CREATE/UPDATE/DELETE
   - `cascade_bundle_re_expansion()`: log CASCADE
   - Track: item kode, koefisien changes, bundle additions/removals

**Success Criteria:**
- ✓ All CRUD operations logged
- ✓ Cascade operations logged with triggered_by='cascade'

---

#### 2.3 Audit Trail UI
**Priority:** MEDIUM
**Effort:** 2 days

**Deliverables:**
1. **UI: Audit History Page** (detail_project/audit_trail.html)
   - Timeline view of changes
   - Filter by: pekerjaan, action type, date range
   - Show: who, when, what changed
   - Diff view (old vs new data)

2. **API Endpoint:** `GET /api/projects/{id}/audit-trail/`
   - Pagination support
   - Filter support

**Success Criteria:**
- ✓ User dapat melihat history lengkap
- ✓ Easy to debug "kenapa total berubah?"

---

## FASE 3: CROSS-PAGE SYNC INDICATORS (Week 6)

**Tujuan:** Implement visual indicators untuk notify user tentang changes di page lain

### Tasks:

#### 3.1 Change Detection Mechanism
**Priority:** MEDIUM
**Effort:** 2 days

**Deliverables:**
1. **Timestamp Tracking:**
   - Project.last_ahsp_change (DetailAHSPProject/Expanded modified)
   - Project.last_harga_change (HargaItemProject modified)
   - Pekerjaan.last_modified

2. **API: Change Status**
   ```python
   GET /api/projects/{id}/change-status/
   Response:
   {
     "ahsp_changed_since": "2024-01-15T10:30:00Z",
     "harga_changed_since": "2024-01-15T11:00:00Z",
     "affected_pekerjaan_count": 5
   }
   ```

**Success Criteria:**
- ✓ Can detect if data changed since page load

---

#### 3.2 UI Indicators
**Priority:** MEDIUM
**Effort:** 2 days

**Deliverables:**
1. **Template AHSP Page:**
   - Badge di sidebar: "✓ Data tersinkron" atau "⚠️ Ada perubahan di Harga Items"
   - Polling every 30s (optional)

2. **Harga Items Page:**
   - Badge: "⚠️ Ada komponen baru dari Template AHSP"
   - Suggest refresh button

3. **Rincian AHSP Page:**
   - Badge: "⚠️ Harga atau komponen berubah"
   - Auto-refresh option

**Success Criteria:**
- ✓ User aware of changes in other pages
- ✓ No automatic refresh (user control)

---

## FASE 4: MIGRATION & VALIDATION TOOLS (Week 7)

**Tujuan:** Tools untuk validate & fix legacy data

### Tasks:

#### 4.1 Data Validation Script
**Priority:** MEDIUM
**Effort:** 2 days

**Deliverables:**
1. **Management Command:** `python manage.py validate_ahsp_data`
   - Check: all bundles have valid targets
   - Check: no circular dependencies
   - Check: expanded data matches raw input
   - Check: orphan count acceptable
   - Generate report

**Success Criteria:**
- ✓ Can validate data integrity
- ✓ Report actionable issues

---

#### 4.2 Migration/Fix Tools
**Priority:** LOW
**Effort:** 2 days

**Deliverables:**
1. **Management Command:** `python manage.py fix_ahsp_data`
   - Fix: re-expand all bundles
   - Fix: cleanup orphans older than X days
   - Fix: recalculate all DetailAHSPExpanded
   - Dry-run mode

**Success Criteria:**
- ✓ Can fix common data issues
- ✓ Dry-run safe

---

## OPTIONAL ENHANCEMENTS

### A. Bundle Complexity Isolation (Optional Refactoring)

**Priority:** LOW
**Effort:** 5 days

**Deliverables:**
1. **Class: BundleProcessor**
   - Isolate bundle logic from views_api.py
   - Methods: expand(), validate(), cascade_update()
   - Easier to test & maintain

**When to do:** If bundle logic becomes too complex or hard to maintain

---

### B. WebSocket for Real-Time Sync

**Priority:** LOW
**Effort:** 3 days

**Deliverables:**
1. **WebSocket Channel:** project_changes
   - Push notification when data changes
   - Client auto-refresh or show notification

**When to do:** If polling is too heavy or UX needs real-time updates

---

## TESTING STRATEGY

### Per Fase Testing:

**FASE 0 (Preparation):**
- Unit tests for audit script
- Integration tests for baseline workflow

**FASE 1 (Orphan Cleanup):**
- Unit tests: detect_orphaned_items()
- Integration tests: cleanup API
- E2E tests: UI workflow

**FASE 2 (Audit Trail):**
- Unit tests: log_audit()
- Integration tests: audit creation
- E2E tests: audit timeline UI

**FASE 3 (Sync Indicators):**
- Unit tests: change detection
- Integration tests: polling mechanism
- E2E tests: UI indicators

**FASE 4 (Migration):**
- Unit tests: validation logic
- Integration tests: fix scripts
- E2E tests: dry-run vs real run

---

## DEPLOYMENT STRATEGY

### Per Fase Deployment:

**Checklist per fase:**
1. ✓ Code review passed
2. ✓ Tests passed (>80% coverage)
3. ✓ Documentation updated
4. ✓ Staging tested
5. ✓ Migration script ready (if needed)
6. ✓ Rollback plan documented

**Deployment Order:**
1. Deploy to staging
2. Run migration (if needed)
3. Manual QA testing
4. Deploy to production (off-peak hours)
5. Monitor for 24h
6. Rollback if issues

---

## MONITORING & SUCCESS METRICS

### Metrics to Track:

**FASE 1 (Orphan Cleanup):**
- Orphan count before/after: expect decrease
- Manual cleanup usage: track adoption
- Storage saved: track disk space

**FASE 2 (Audit Trail):**
- Audit entries created per day
- Disk usage (audit table size)
- Query performance (audit queries)

**FASE 3 (Sync Indicators):**
- Polling frequency
- User engagement (click refresh rate)
- Server load (polling overhead)

**FASE 4 (Migration):**
- Data validation pass rate
- Issues fixed count
- Time to run full validation

---

## RISK MITIGATION

### Identified Risks:

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Orphan cleanup deletes active items | HIGH | LOW | Double validation, confirmation dialog, dry-run |
| Audit trail bloats database | MEDIUM | HIGH | Partitioning, archiving old entries |
| Polling causes server load | MEDIUM | MEDIUM | Configurable interval, disable option |
| Migration script breaks data | HIGH | LOW | Dry-run first, backup before run |

---

## TIMELINE SUMMARY

| Fase | Duration | Deliverables | Priority |
|------|----------|--------------|----------|
| **FASE 0** | Week 1 | Audit, baseline tests, monitoring | CRITICAL |
| **FASE 1** | Week 2-3 | Orphan cleanup mechanism | HIGH |
| **FASE 2** | Week 4-5 | Audit trail system | HIGH |
| **FASE 3** | Week 6 | Cross-page sync indicators | MEDIUM |
| **FASE 4** | Week 7 | Migration & validation tools | MEDIUM |
| **Total** | **7 weeks** | All enhancements | - |

---

## DECISION LOG

### Why This Order?

1. **FASE 0 first:** Need baseline before enhancement
2. **FASE 1 (Orphan) before FASE 2 (Audit):** Orphan is data quality issue, audit is observability
3. **FASE 3 (Sync) after FASE 2 (Audit):** Audit trail can help debug sync issues
4. **FASE 4 (Migration) last:** After all features stable, then fix legacy data

### What Can Be Parallelized?

- FASE 1 & FASE 2 can run parallel (different codepaths)
- FASE 3 independent, can start anytime after FASE 0

### What Can Be Skipped?

- FASE 4 can be skipped if no legacy data issues
- Optional enhancements can be deferred indefinitely

---

## NEXT STEPS

**To Start Implementation:**

1. **Review & Approve Roadmap:**
   - Stakeholder review
   - Priority adjustment if needed
   - Resource allocation

2. **Setup Development Environment:**
   - Create feature branch: `feature/ahsp-enhancement-phase-0`
   - Setup staging environment
   - Configure CI/CD for testing

3. **Begin FASE 0:**
   - Start with data audit script
   - Establish test baseline
   - Setup monitoring

4. **Weekly Check-ins:**
   - Progress review
   - Blocker discussion
   - Timeline adjustment

---

## CONTACT & OWNERSHIP

**Document Owner:** [Your Name]
**Technical Lead:** [TBD]
**QA Lead:** [TBD]
**Timeline:** 7 weeks (can be adjusted)

---

**Last Updated:** 2025-01-XX
**Version:** 1.0
**Status:** Ready for Review & Implementation
