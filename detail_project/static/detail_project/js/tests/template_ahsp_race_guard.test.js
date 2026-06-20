/**
 * TA-22 guard: stale async responses must not paint one job's rows over another.
 *
 * Both the job-fetch path (selectJobInternal) and the save success path (doSave)
 * key their cache/paint off the request's job id and refuse to repaint when the
 * user has switched to a different pekerjaan while the request was in flight —
 * otherwise a following save reads the visible table and writes the wrong job's
 * components to the active pekerjaan (silent cross-job corruption).
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const src = readFileSync(resolve(__dirname, '..', 'template_ahsp.js'), 'utf-8');

describe('TA-22 - stale-response guard', () => {
  test('job fetch caches by id then skips paint when the active job changed', () => {
    // cache is populated for the fetched id before the guard
    expect(src).toContain('rowsByJob[id] = {');
    // guard: do not paint a stale response over a different active job
    expect(src).toMatch(/if \(id !== activeJobId\) \{\s*return;\s*\}/);
  });

  test('save success keys cache/paint off the saved jobId, not activeJobId', () => {
    expect(src).toContain('const stillActive = (jobId === activeJobId);');
    expect(src).toContain('rowsByJob[jobId] = {');
    expect(src).toContain('if (stillActive) {');
    // the previous global-active bleed must be gone from the save success path
    expect(src).not.toContain('rowsByJob[activeJobId] = {');
  });
});
