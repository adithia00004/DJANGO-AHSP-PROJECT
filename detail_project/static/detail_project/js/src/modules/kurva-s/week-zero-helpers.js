/**
 * Helpers to ensure Kurva S datasets always start from Week 0 (0% progress).
 */

/**
 * Create zero-week metadata entry for cost datasets.
 * @returns {Object}
 */
export function createZeroWeekEntry() {
  return {
    week_number: 0,
    week_start: null,
    week_end: null,
    cost: 0,
    cumulative_cost: 0,
    cumulative_percent: 0,
    pekerjaan_breakdown: {},
  };
}

/**
 * Prepend zero-week detail information for tooltips / metadata.
 * @param {Array|Object} details
 * @param {string} zeroLabel
 * @param {boolean} isCostView
 * @returns {Array|Object}
 */
export function prependZeroDetails(details, zeroLabel, isCostView) {
  if (Array.isArray(details)) {
    return [
      {
        label: zeroLabel,
        planned: 0,
        actual: 0,
        variance: 0,
        start: null,
        end: null,
        tooltip: zeroLabel,
      },
      ...details,
    ];
  }

  if (isCostView && details && typeof details === 'object') {
    const zeroWeek = createZeroWeekEntry();
    return {
      ...details,
      weeks: Array.isArray(details.weeks) ? [zeroWeek, ...details.weeks] : details.weeks,
      actualWeeks: Array.isArray(details.actualWeeks) ? [zeroWeek, ...details.actualWeeks] : details.actualWeeks,
    };
  }

  return details;
}

/**
 * Ensure dataset starts with Week 0.
 * @param {Object} dataset
 * @returns {Object}
 */
export function ensureWeekZeroDataset(dataset) {
  if (!dataset || !Array.isArray(dataset.labels) || dataset.labels.length === 0) {
    return dataset;
  }

  const firstLabel = String(dataset.labels[0] || '').toLowerCase();
  if (firstLabel.includes('week 0') || firstLabel === 'w0') {
    return dataset;
  }

  const zeroLabel = dataset.viewMode === 'cost' ? 'W0' : 'Week 0';
  const plannedSeries = Array.isArray(dataset.planned) ? dataset.planned : [];
  const actualSeries = Array.isArray(dataset.actual) ? dataset.actual : [];

  const updated = {
    ...dataset,
    labels: [zeroLabel, ...dataset.labels],
    planned: [0, ...plannedSeries],
    actual: [0, ...actualSeries],
  };

  if (Array.isArray(dataset.acSeries)) {
    updated.acSeries = [0, ...dataset.acSeries];
  }

  updated.details = prependZeroDetails(dataset.details, zeroLabel, dataset.viewMode === 'cost');

  return updated;
}

export default {
  ensureWeekZeroDataset,
  prependZeroDetails,
  createZeroWeekEntry,
};
