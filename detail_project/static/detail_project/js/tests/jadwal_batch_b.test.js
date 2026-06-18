/**
 * WP-P7 Batch B guard — Vite source (jadwal). Source-grep: these modules are bundled
 * into dist/ (rebuilt by the owner); this guard locks the intent in the SOURCE so a
 * future edit/rebuild can't silently regress it.
 *
 *  - P7i (B6e/R2): no silent auto-regenerate on page-open; advisory notice instead.
 *  - P7j (JDW-04): loadAssignments propagates load errors (no empty-map masking).
 *  - P7k (KS-02/JDW-13D): Kurva S weight is harga-only; no silent volume/equal-weight fallback.
 */
import { describe, test, expect } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const SRC = resolve(__dirname, '..', 'src');
const read = (rel) => readFileSync(resolve(SRC, rel), 'utf-8');

const orchestrator = read('modules/app/DataOrchestrator.js');
const app = read('jadwal_kegiatan_app.js');
const dataLoader = read('modules/core/data-loader.js');
const datasetBuilder = read('modules/kurva-s/dataset-builder.js');

describe('WP-P7i — no silent auto-regenerate on page-open (B6e/R2)', () => {
  test('DataOrchestrator flags advisory instead of auto-regenerating', () => {
    expect(orchestrator).toContain('app.state.timelineNeedsRegen = true');
    expect(orchestrator).toContain('WP-P7i');
    // the auto-mutation (await regenerateTimeline immediately on incomplete weeks) is gone
    expect(orchestrator).not.toMatch(/shouldForceWeekly\)\s*\{[\s\S]*?await this\.regenerateTimeline/);
  });
  test('jadwal_kegiatan_app flags advisory instead of auto-regenerating', () => {
    expect(app).toContain('this.state.timelineNeedsRegen = true');
    expect(app).not.toMatch(/shouldForceWeekly\)\s*\{[\s\S]*?await this\._regenerateTimeline/);
  });
});

describe('WP-P7j — loadAssignments propagates errors (JDW-04)', () => {
  test('error sets a flag and re-throws (no empty-map masking)', () => {
    expect(dataLoader).toContain('this.state.assignmentsLoadError = error');
    expect(dataLoader).toMatch(/this\.state\.assignmentsLoadError = error;\s*\n\s*throw error;/);
  });
});

describe('WP-P7k — Kurva S harga-only weighting (KS-02/JDW-13D)', () => {
  test('no silent volume/equal-weight fallback; honest weightsReady flag', () => {
    expect(datasetBuilder).not.toContain('totalVolume = pekerjaanIds.size');
    expect(datasetBuilder).toContain('weightsReady: false');
    expect(datasetBuilder).toContain('JDW-13D');
  });
});
