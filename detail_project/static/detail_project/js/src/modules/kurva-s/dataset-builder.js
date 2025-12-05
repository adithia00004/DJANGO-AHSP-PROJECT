import {
  getSortedColumns,
  buildVolumeLookup,
  buildHargaLookup,
  collectPekerjaanIds,
  getHargaForPekerjaan,
  getVolumeForPekerjaan,
  buildCellValueMap,
  formatRupiah,
  normalizeDate,
} from '../shared/chart-utils.js';
import { ensureWeekZeroDataset } from './week-zero-helpers.js';

const LOG_PREFIX = '[KurvaSDataset]';

export function buildProgressDataset(state) {
  const columns = getSortedColumns(state?.timeColumns);
  if (!columns || columns.length === 0) {
    console.warn(LOG_PREFIX, 'No time columns available');
    return null;
  }

  const volumeLookup = buildVolumeLookup(state);
  const hargaLookup = buildHargaLookup(state);
  const stateManager = state?.stateManager;

  let plannedCellValues;
  let actualCellValues;
  if (stateManager) {
    plannedCellValues = stateManager.getAllCellsForMode('planned') || new Map();
    actualCellValues = stateManager.getAllCellsForMode('actual') || new Map();
  } else {
    const plannedState = state?.plannedState || state;
    const actualState = state?.actualState || state;
    plannedCellValues = buildCellValueMap(plannedState);
    actualCellValues = buildCellValueMap(actualState);
  }

  if (!plannedCellValues || !(plannedCellValues instanceof Map)) {
    plannedCellValues = new Map();
  }
  if (!actualCellValues || !(actualCellValues instanceof Map)) {
    actualCellValues = new Map();
  }

  const pekerjaanIds = new Set([
    ...collectPekerjaanIds(state, plannedCellValues),
    ...collectPekerjaanIds(state, actualCellValues),
  ]);

  let totalBiaya = parseFloat(state?.totalBiayaProject || 0);
  if (!totalBiaya || totalBiaya <= 0) {
    pekerjaanIds.forEach((id) => {
      totalBiaya += getHargaForPekerjaan(hargaLookup, id, 0);
    });
  }
  const useHargaCalculation = totalBiaya > 0 && hargaLookup.size > 0;

  let totalVolume = 0;
  if (!useHargaCalculation) {
    pekerjaanIds.forEach((id) => {
      totalVolume += getVolumeForPekerjaan(volumeLookup, id, 1);
    });
    if (!Number.isFinite(totalVolume) || totalVolume <= 0) {
      totalVolume = pekerjaanIds.size || 1;
    }
  }

  const columnIndexById = new Map();
  columns.forEach((col, index) => {
    columnIndexById.set(String(col.id), index);
  });

  const labels = generateLabels(columns);
  const plannedSeries = calculatePlannedCurve(
    columns,
    volumeLookup,
    hargaLookup,
    plannedCellValues,
    useHargaCalculation ? totalBiaya : totalVolume,
    columnIndexById,
    useHargaCalculation
  );

  const actualColumnTotals = calculateColumnTotals(
    columns,
    actualCellValues,
    volumeLookup,
    hargaLookup,
    columnIndexById,
    useHargaCalculation
  );

  const actualSeries = calculateActualCurve(
    columns,
    actualColumnTotals,
    useHargaCalculation ? totalBiaya : totalVolume,
    useHargaCalculation
  );

  const details = buildDetailData(
    columns,
    labels,
    plannedSeries,
    actualSeries,
    useHargaCalculation ? totalBiaya : totalVolume,
    useHargaCalculation
  );

  return ensureWeekZeroDataset({
    labels,
    planned: plannedSeries,
    actual: actualSeries,
    details,
    totalVolume,
    totalBiaya,
    columnTotals: actualColumnTotals,
    useHargaCalculation,
    viewMode: 'progress',
  });
}

export function buildCostDataset(costData) {
  if (!costData) {
    console.error(LOG_PREFIX, 'No cost data available');
    return null;
  }

  const weeklyData = costData.weeklyData || {};
  const summary = costData.summary || {};
  const evm = costData.evm;

  if (evm && Array.isArray(evm.labels) && evm.labels.length > 0) {
    const totalCost = evm.summary?.bac || summary?.total_project_cost || 0;
    const weeklySummary = buildCostWeeklySummary(
      weeklyData?.planned || [],
      weeklyData?.actual || [],
      totalCost,
      evm.labels
    );
    const plannedSeries = evm.pv_percent || [];
    const actualSeries = evm.ev_percent || [];
    const acSeries = evm.ac_percent || actualSeries;
    const varianceSeries = plannedSeries.map((value, index) =>
      Number(((acSeries[index] || actualSeries[index] || 0) - (value || 0)).toFixed(2))
    );
    const varianceCostSeries = weeklySummary.map((entry) => entry.varianceCostValue || 0);
    return ensureWeekZeroDataset({
      labels: evm.labels,
      planned: plannedSeries,
      actual: actualSeries,
      acSeries,
      varianceSeries,
      varianceCostSeries,
      details: {
        totalCost,
        weeks: weeklyData?.planned || [],
        actualWeeks: weeklyData?.actual || [],
        weeklySummary,
        evmSummary: evm.summary,
        evm,
      },
      evm,
      totalBiaya: totalCost,
      useHargaCalculation: true,
      viewMode: 'cost',
    });
  }

  const labels = (weeklyData.planned || []).map((w) => `W${w.week_number}`);
  const plannedSeries = (weeklyData.planned || []).map((w) => w.cumulative_percent);
  const actualSeries = (weeklyData.actual || []).map((w) => w.cumulative_percent);
  const acSeries = actualSeries.length
    ? actualSeries
    : (weeklyData.earned || []).map((w) => w.cumulative_percent);
  const varianceSeries = plannedSeries.map((value, index) =>
    Number(((acSeries[index] || actualSeries[index] || 0) - (value || 0)).toFixed(2))
  );

  const details = {
    totalCost: summary?.total_project_cost || 0,
    plannedCost: summary?.planned_cost || 0,
    actualCost: summary?.actual_cost || 0,
    weeks: weeklyData.planned || [],
    actualWeeks: weeklyData.actual || [],
    viewMode: 'cost',
  };
  const weeklySummary = buildCostWeeklySummary(
    weeklyData.planned || [],
    weeklyData.actual || [],
    details.totalCost,
    labels
  );

  console.log(LOG_PREFIX, 'Cost dataset built:', {
    labels: labels.length,
    plannedPoints: plannedSeries.length,
    actualPoints: actualSeries.length,
    totalCost: formatRupiah(details.totalCost),
  });

  return ensureWeekZeroDataset({
    labels,
    planned: plannedSeries,
    actual: actualSeries,
    acSeries,
    varianceSeries,
    varianceCostSeries: weeklySummary.map((entry) => entry.varianceCostValue || 0),
    details: {
      ...details,
      weeklySummary,
    },
    totalBiaya: details.totalCost,
    useHargaCalculation: true,
    viewMode: 'cost',
  });
}

function generateLabels(columns) {
  return columns.map((col, index) => {
    const label =
      col?.label ||
      col?.displayLabel ||
      col?.display_name ||
      col?.name ||
      `Week ${index + 1}`;

    if (col?.start_date && col?.end_date) {
      return `${label} (${col.start_date} - ${col.end_date})`;
    }

    return label;
  });
}

function calculatePlannedCurve(
  columns,
  volumeLookup,
  hargaLookup,
  cellValues,
  totalValue,
  columnIndexById,
  useHargaCalculation
) {
  const plannedTotals = Array(columns.length).fill(0);

  cellValues.forEach((value, cellKey) => {
    const [pekerjaanId, columnId] = cellKey.split('-');
    if (!columnIndexById.has(columnId)) {
      return;
    }

    const columnIndex = columnIndexById.get(columnId);
    if (columnIndex === undefined) {
      return;
    }

    const numericValue = Number(value) || 0;

    if (useHargaCalculation) {
      const biaya = getHargaForPekerjaan(hargaLookup, pekerjaanId, 0);
      const kontribusi = (biaya * numericValue) / 100;
      plannedTotals[columnIndex] += kontribusi;
    } else {
      const volume = getVolumeForPekerjaan(volumeLookup, pekerjaanId, 1);
      const kontribusi = (volume * numericValue) / 100;
      plannedTotals[columnIndex] += kontribusi;
    }
  });

  let cumulative = 0;
  return plannedTotals.map((value) => {
    cumulative += value;
    if (!Number.isFinite(totalValue) || totalValue <= 0) {
      return 0;
    }
    return Number(((cumulative / totalValue) * 100).toFixed(2));
  });
}

function calculateColumnTotals(
  columns,
  cellValues,
  volumeLookup,
  hargaLookup,
  columnIndexById,
  useHargaCalculation
) {
  const totals = Array(columns.length).fill(0);

  cellValues.forEach((value, cellKey) => {
    const [pekerjaanId, columnId] = cellKey.split('-');
    const columnIndex = columnIndexById.get(columnId);
    if (typeof columnIndex === 'undefined') {
      return;
    }

    const numericValue = Number(value) || 0;

    if (useHargaCalculation) {
      const biaya = getHargaForPekerjaan(hargaLookup, pekerjaanId, 0);
      const kontribusi = (biaya * numericValue) / 100;
      totals[columnIndex] += kontribusi;
    } else {
      const volume = getVolumeForPekerjaan(volumeLookup, pekerjaanId, 1);
      const kontribusi = (volume * numericValue) / 100;
      totals[columnIndex] += kontribusi;
    }
  });

  return totals;
}

function calculateActualCurve(columns, columnTotals, totalValue, useHargaCalculation) {
  let cumulative = 0;
  return columns.map((_, index) => {
    cumulative += columnTotals[index] || 0;
    if (!Number.isFinite(totalValue) || totalValue <= 0) {
      return 0;
    }
    return Number(((cumulative / totalValue) * 100).toFixed(2));
  });
}

function buildDetailData(
  columns,
  labels,
  plannedSeries,
  actualSeries,
  totalValue = 0,
  useHargaCalculation = false
) {
  return columns.map((column, index) => {
    const label = labels[index] || `Week ${index + 1}`;
    const planned = plannedSeries[index] || 0;
    const actual = actualSeries[index] || 0;
    const variance = Number((actual - planned).toFixed(2));
    let plannedCostValue = null;
    let actualCostValue = null;
    let varianceCostValue = null;
    if (useHargaCalculation) {
      plannedCostValue = Number(((planned / 100) * (totalValue || 0)).toFixed(2));
      actualCostValue = Number(((actual / 100) * (totalValue || 0)).toFixed(2));
      varianceCostValue = Number(((actualCostValue - plannedCostValue)).toFixed(2));
    }

    return {
      label,
      planned,
      actual,
      variance,
      start: normalizeDate(column?.startDate || column?.start_date || column?.start),
      end: normalizeDate(column?.endDate || column?.end_date || column?.end),
      metadata: column,
      plannedCostValue,
      actualCostValue,
      varianceCostValue,
    };
  });
}

function buildCostWeeklySummary(plannedWeeks = [], actualWeeks = [], totalCost = 0, labels = []) {
  const maxLength = Math.max(plannedWeeks.length, actualWeeks.length, labels.length);
  const summary = [];
  for (let index = 0; index < maxLength; index += 1) {
    const plannedEntry = plannedWeeks[index] || {};
    const actualEntry = actualWeeks[index] || {};
    const label =
      labels[index] ||
      plannedEntry.label ||
      actualEntry.label ||
      `W${plannedEntry.week_number || actualEntry.week_number || index + 1}`;
    const plannedPercent = Number(
      plannedEntry.cumulative_percent ??
        plannedEntry.percent ??
        plannedEntry.value ??
        plannedEntry.cumulative ??
        0
    );
    const actualPercent = Number(
      actualEntry.cumulative_percent ??
        actualEntry.percent ??
        actualEntry.value ??
        actualEntry.cumulative ??
        0
    );
    const plannedCostValue = resolveCostValue(plannedEntry, plannedPercent, totalCost);
    const actualCostValue = resolveCostValue(actualEntry, actualPercent, totalCost);
    const variancePercent = Number(((actualPercent - plannedPercent)).toFixed(2));
    const varianceCostValue = Number((actualCostValue - plannedCostValue).toFixed(2));

    summary.push({
      label,
      weekNumber: plannedEntry.week_number ?? actualEntry.week_number ?? index + 1,
      plannedPercent: Number.isFinite(plannedPercent) ? plannedPercent : 0,
      actualPercent: Number.isFinite(actualPercent) ? actualPercent : 0,
      plannedCostValue,
      actualCostValue,
      variancePercent,
      varianceCostValue,
      range: {
        start: normalizeDate(
          plannedEntry.week_start ||
            plannedEntry.start_date ||
            actualEntry.week_start ||
            actualEntry.start_date
        ),
        end: normalizeDate(
          plannedEntry.week_end || plannedEntry.end_date || actualEntry.week_end || actualEntry.end_date
        ),
      },
    });
  }
  return summary;
}

function resolveCostValue(weekEntry, percent, totalCost) {
  const numericPercent = Number(
    percent ??
      weekEntry?.cumulative_percent ??
      weekEntry?.percent ??
      weekEntry?.value ??
      0
  );
  const cumulative = toNumber(
    weekEntry?.cumulative_cost ??
      weekEntry?.cumulative ??
      weekEntry?.accumulated_cost ??
      weekEntry?.acc_cost
  );
  if (Number.isFinite(cumulative) && cumulative > 0) {
    return cumulative;
  }
  const singleCost = toNumber(weekEntry?.cost);
  if (Number.isFinite(singleCost) && singleCost > 0 && !weekEntry?.cumulative_cost) {
    return singleCost;
  }
  if (!Number.isFinite(totalCost) || totalCost <= 0) {
    return 0;
  }
  return Number((((numericPercent || 0) / 100) * totalCost).toFixed(2));
}

function toNumber(value) {
  if (typeof value === 'number') {
    return value;
  }
  if (typeof value === 'string') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : NaN;
  }
  return NaN;
}
