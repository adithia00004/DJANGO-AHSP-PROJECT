/**
 * Data Aggregator - Transform weekly data to monthly aggregates
 *
 * Provides utilities for aggregating weekly progress data into monthly
 * summaries for export and reporting purposes.
 *
 * @module DataAggregator
 */

import { createLogger } from './logger.js';

const logger = createLogger('DataAggregator');

/**
 * Aggregate weekly progress to monthly
 *
 * Groups weeks into months (default: 4 weeks = 1 month) and sums
 * the progress values for each month.
 *
 * @param {Array} weeklyData - Array of weekly progress objects
 *   [{week: 1, planned: 10, actual: 8}, ...]
 * @param {number} weeksPerMonth - Weeks per month (default: 4)
 * @returns {Array} Monthly aggregated data
 *
 * @example
 * const weekly = [
 *   {week: 1, planned: 10, actual: 8},
 *   {week: 2, planned: 15, actual: 12},
 *   {week: 3, planned: 12, actual: 10},
 *   {week: 4, planned: 13, actual: 15}
 * ];
 * const monthly = aggregateWeeklyToMonthly(weekly);
 * // Returns: [{month: 1, label: 'M1', weeks: 'W1-W4', planned: 50, actual: 45}]
 */
export function aggregateWeeklyToMonthly(weeklyData, weeksPerMonth = 4) {
  if (!Array.isArray(weeklyData) || weeklyData.length === 0) {
    logger.warn('Invalid or empty weekly data provided');
    return [];
  }

  const monthlyData = [];
  const totalWeeks = weeklyData.length;
  const totalMonths = Math.ceil(totalWeeks / weeksPerMonth);

  logger.debug(`Aggregating ${totalWeeks} weeks into ${totalMonths} months`);

  for (let m = 0; m < totalMonths; m++) {
    const weekStart = m * weeksPerMonth;
    const weekEnd = Math.min((m + 1) * weeksPerMonth, totalWeeks);
    const weeksInMonth = weekEnd - weekStart;

    const monthData = {
      month: m + 1,
      label: `M${m + 1}`,
      weeks: `W${weekStart + 1}-W${weekEnd}`,
      weekStart: weekStart + 1,
      weekEnd: weekEnd,
      weeksCount: weeksInMonth,
      planned: 0,
      actual: 0
    };

    // Sum progress for weeks in this month
    for (let w = weekStart; w < weekEnd; w++) {
      const weekData = weeklyData[w];
      if (weekData) {
        monthData.planned += Number(weekData.planned) || 0;
        monthData.actual += Number(weekData.actual) || 0;
      }
    }

    // Round to 2 decimal places
    monthData.planned = Math.round(monthData.planned * 100) / 100;
    monthData.actual = Math.round(monthData.actual * 100) / 100;

    monthlyData.push(monthData);
  }

  logger.info(`Aggregated ${totalWeeks} weeks into ${monthlyData.length} months`);

  return monthlyData;
}

/**
 * Sample weekly cumulative at month boundaries
 *
 * For Kurva S charts, we need cumulative progress at the END of each month
 * (week 4, 8, 12, etc.) rather than sum of weeks within month.
 *
 * @param {Array} weeklyCumulative - Weekly cumulative progress
 *   [{week: 1, planned: 10, actual: 8}, {week: 2, planned: 25, actual: 20}, ...]
 * @param {number} weeksPerMonth - Weeks per month (default: 4)
 * @returns {Array} Monthly cumulative data (sampled at month boundaries)
 *
 * @example
 * const weeklyCumulative = [
 *   {week: 1, planned: 10, actual: 8},
 *   {week: 2, planned: 25, actual: 20},
 *   {week: 3, planned: 37, actual: 30},
 *   {week: 4, planned: 50, actual: 45},
 *   {week: 5, planned: 60, actual: 55}
 * ];
 * const monthly = sampleMonthlyCumulative(weeklyCumulative);
 * // Returns: [
 * //   {month: 1, week: 4, planned: 50, actual: 45},
 * //   {month: 2, week: 5, planned: 60, actual: 55}  // Partial month
 * // ]
 */
export function sampleMonthlyCumulative(weeklyCumulative, weeksPerMonth = 4) {
  if (!Array.isArray(weeklyCumulative) || weeklyCumulative.length === 0) {
    logger.warn('Invalid or empty weekly cumulative data');
    return [];
  }

  const monthlyCumulative = [];
  const totalWeeks = weeklyCumulative.length;
  const totalMonths = Math.ceil(totalWeeks / weeksPerMonth);

  logger.debug(`Sampling ${totalWeeks} weeks at ${totalMonths} month boundaries`);

  for (let m = 1; m <= totalMonths; m++) {
    // Sample at end of month (week 4, 8, 12, ...)
    const weekIndex = Math.min(m * weeksPerMonth - 1, totalWeeks - 1);
    const weekData = weeklyCumulative[weekIndex];

    if (!weekData) {
      logger.warn(`No data at week ${weekIndex + 1} for month ${m}`);
      continue;
    }

    const monthData = {
      month: m,
      label: `M${m}`,
      week: weekIndex + 1,
      weekLabel: `W${weekIndex + 1}`,
      planned: Number(weekData.planned) || 0,
      actual: Number(weekData.actual) || 0
    };

    // Round to 2 decimal places
    monthData.planned = Math.round(monthData.planned * 100) / 100;
    monthData.actual = Math.round(monthData.actual * 100) / 100;

    monthlyCumulative.push(monthData);
  }

  logger.info(`Sampled ${monthlyCumulative.length} month boundary points`);

  return monthlyCumulative;
}

/**
 * Calculate cumulative progress from incremental values
 *
 * Converts incremental weekly progress to cumulative progress.
 *
 * @param {Array} incrementalData - Incremental progress data
 *   [{week: 1, planned: 10, actual: 8}, ...]
 * @returns {Array} Cumulative progress data
 *
 * @example
 * const incremental = [
 *   {week: 1, planned: 10, actual: 8},
 *   {week: 2, planned: 15, actual: 12},
 *   {week: 3, planned: 12, actual: 10}
 * ];
 * const cumulative = calculateCumulative(incremental);
 * // Returns: [
 * //   {week: 1, planned: 10, actual: 8},
 * //   {week: 2, planned: 25, actual: 20},
 * //   {week: 3, planned: 37, actual: 30}
 * // ]
 */
export function calculateCumulative(incrementalData) {
  if (!Array.isArray(incrementalData) || incrementalData.length === 0) {
    return [];
  }

  const cumulative = [];
  let cumulativePlanned = 0;
  let cumulativeActual = 0;

  for (const data of incrementalData) {
    cumulativePlanned += Number(data.planned) || 0;
    cumulativeActual += Number(data.actual) || 0;

    cumulative.push({
      ...data,
      planned: Math.round(cumulativePlanned * 100) / 100,
      actual: Math.round(cumulativeActual * 100) / 100
    });
  }

  return cumulative;
}

/**
 * Group data by period (weekly/monthly)
 *
 * Generic grouping function for any period-based data.
 *
 * @param {Array} data - Array of data objects
 * @param {string} groupBy - 'week' or 'month'
 * @returns {Object} Grouped data {period: [...items]}
 */
export function groupByPeriod(data, groupBy = 'week') {
  if (!Array.isArray(data)) {
    return {};
  }

  const grouped = {};

  for (const item of data) {
    const key = item[groupBy];
    if (key === undefined) continue;

    if (!grouped[key]) {
      grouped[key] = [];
    }
    grouped[key].push(item);
  }

  return grouped;
}

/**
 * Validate aggregation data
 *
 * Checks if aggregated data is valid and matches expected totals.
 *
 * @param {Array} weeklyData - Original weekly data
 * @param {Array} monthlyData - Aggregated monthly data
 * @returns {Object} {isValid: boolean, errors: string[]}
 */
export function validateAggregation(weeklyData, monthlyData) {
  const errors = [];

  // Check totals match
  const weeklyTotalPlanned = weeklyData.reduce((sum, w) => sum + (Number(w.planned) || 0), 0);
  const weeklyTotalActual = weeklyData.reduce((sum, w) => sum + (Number(w.actual) || 0), 0);

  const monthlyTotalPlanned = monthlyData.reduce((sum, m) => sum + (Number(m.planned) || 0), 0);
  const monthlyTotalActual = monthlyData.reduce((sum, m) => sum + (Number(m.actual) || 0), 0);

  const plannedDiff = Math.abs(weeklyTotalPlanned - monthlyTotalPlanned);
  const actualDiff = Math.abs(weeklyTotalActual - monthlyTotalActual);

  if (plannedDiff > 0.01) {
    errors.push(`Planned total mismatch: weekly=${weeklyTotalPlanned}, monthly=${monthlyTotalPlanned}`);
  }

  if (actualDiff > 0.01) {
    errors.push(`Actual total mismatch: weekly=${weeklyTotalActual}, monthly=${monthlyTotalActual}`);
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

export default {
  aggregateWeeklyToMonthly,
  sampleMonthlyCumulative,
  calculateCumulative,
  groupByPeriod,
  validateAggregation
};
