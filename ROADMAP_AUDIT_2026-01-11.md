# Roadmap Audit 2026-01-11

Scope: Audit the optimization roadmap and confirm which checkpoints are valid
based on existing evidence. Provide a minimal, reliable plan forward.

Evidence sources reviewed:
- MASTER_EXECUTION_TRACKER.md
- Locust CSVs referenced in the tracker (v18, v19, v20, v21, v23, v24, v24b)
- load_testing/locustfile.py tag behavior (export/admin leakage)

Key findings (evidence-based)
1) Auth-only baseline is solid when rate limits are disabled and pool is sized
   Evidence: hasil_test_auth_only_50u_multi_nolimit_v3_pool100_stats.csv
   - Aggregated: 100 requests, 0 failures
   - Login POST: 50 requests, 0 failures
2) Full mixed-load baseline is NOT solid because the workload was inconsistent
   Evidence: v23/v24/v24b tests still included export/admin endpoints due to tag
   leakage and incorrect tag syntax (comma-separated tags are treated as one tag).
3) Error spikes in the last tests correlate with export-heavy endpoints being
   unintentionally included. These endpoints hold DB connections for 60-120s,
   causing PgBouncer queue wait timeouts and cascading 500s (including login).

Root cause of branching and "noisy results"
- The test workload changed across runs due to tag leakage, so the data is not
  apple-to-apple. Optimizations were evaluated under different loads.

Audit verdict
- Infrastructure baseline for auth-only is OK.
- Core workload baseline is NOT yet validated. We must establish a clean core
  test (no export/admin) before continuing optimization work.

Checkpoints to stabilize the plan
Checkpoint A: Test hygiene (must pass before optimization)
- Run core-only test with correct tag filtering:
  locust ... --tags api page phase1 --exclude-tags export admin
- Verification: stats CSV must NOT contain "/export/" or "/admin/" or
  "/detail_project/[id]/export-test/".

Checkpoint B: Auth-only baseline (quick health check)
- 50 users, 180s, rate limits disabled, pool >= 100/20
- Pass criteria: >99% success, P95 < 2s for login POST

Checkpoint C: Core-only baseline (the real gate)
- 100 users, 300s, rate limits disabled, core-only tags as in A
- Pass criteria: <1.5% failures, P95 < 2s on core endpoints

Checkpoint D: Mixed workload (separate from core-only)
- Run export/admin in a separate test track to avoid contaminating core metrics
- Pass criteria: define acceptable P95 per export class (likely 10-30s)

Updated plan (minimal and reliable)
1) Establish clean core-only baseline (Checkpoint A + C).
2) Identify top 2-3 failing endpoints from that clean baseline.
3) Optimize only those endpoints, then rerun the same core-only test.
4) Only after core is stable, run mixed workload tests (Checkpoint D).

Why this plan reduces wasted time
- It prevents us from chasing false regressions caused by inconsistent load.
- Each optimization has a single, reliable test gate.

