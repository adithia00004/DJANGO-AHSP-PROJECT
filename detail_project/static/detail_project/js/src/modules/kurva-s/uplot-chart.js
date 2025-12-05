import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';

import {
  getThemeColors,
  setupThemeObserver,
  createResizeHandler,
  setupResizeObserver,
  formatPercentage,
  formatRupiah,
} from '../shared/chart-utils.js';
import { buildProgressDataset, buildCostDataset } from './dataset-builder.js';

const LOG_PREFIX = '[KurvaSUPlot]';
const DEFAULT_OPTIONS = {
  height: 520,
  enableCostView: true,
};

export class KurvaSUPlotChart {
  constructor(state, options = {}) {
    this.state = state;
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.viewMode = 'progress';
    this.chartInstance = null;
    this.container = null;
    this.tooltipEl = null;
    this.resizeHandler = null;
    this.resizeObserver = null;
    this.themeObserver = null;
    this.currentDataset = null;
    this.costData = null;
    this.isLoadingCostData = false;

    // Interaction helpers
    this._interactionAttached = false;
    this._wheelHandler = null;
    this._interactionTarget = null;
    this._scaleBounds = null;
    this._dateFormatter = null;
  }

  initialize(container) {
    if (!container) {
      console.error(LOG_PREFIX, 'Container element is required');
      return false;
    }

    this.container = container;
    if (getComputedStyle(container).position === 'static') {
      this.container.style.position = 'relative';
    }

    this._createTooltip();

    this.themeObserver = setupThemeObserver(() => this._rebuild());
    this.resizeHandler = createResizeHandler(() => this.resize());
    window.addEventListener('resize', this.resizeHandler);
    this.resizeObserver = setupResizeObserver(container, () => this.resize());

    const success = this.update();
    if (!success) {
      console.warn(LOG_PREFIX, 'Unable to render Kurva-S chart (no dataset)');
    }
    return true;
  }

  update(dataset) {
    const resolvedDataset = dataset || buildProgressDataset(this.state);
    if (!resolvedDataset) {
      return false;
    }
    this.currentDataset = resolvedDataset;
    this.viewMode = resolvedDataset.viewMode || this.viewMode || 'progress';

    const transformedData = this._transformDataset(resolvedDataset);
    const colors = getThemeColors();

    if (!this.chartInstance) {
      const options = this._buildChartOptions(resolvedDataset, colors);
      this.chartInstance = new uPlot(options, transformedData, this.container);
      this._updateScaleBounds();
      this._attachInteractions();
    } else {
      this.chartInstance.setData(transformedData);
      this._updateScaleBounds();
    }

    this._updateTooltipPosition();
    return true;
  }

  resize() {
    if (!this.chartInstance || !this.container) {
      return;
    }
    this.chartInstance.setSize({
      width: this.container.clientWidth || 800,
      height: this.options.height,
    });
  }

  async toggleView(mode) {
    const nextMode = (mode || (this.viewMode === 'progress' ? 'cost' : 'progress')).toLowerCase();
    if (nextMode === this.viewMode) {
      return true;
    }

    if (nextMode === 'cost') {
      if (!this.options.enableCostView) {
        console.warn(LOG_PREFIX, 'Cost view disabled on uPlot chart');
        return false;
      }
      if (!this.costData) {
        const data = await this.fetchCostData();
        if (!data) {
          return false;
        }
      }
      const costDataset = buildCostDataset(this.costData);
      if (!costDataset) {
        console.warn(LOG_PREFIX, 'Cost dataset not available');
        return false;
      }
      this.viewMode = 'cost';
      this.update(costDataset);
      return true;
    }

    this.viewMode = 'progress';
    this.update();
    return true;
  }

  dispose() {
    this._detachInteractions();
    if (this.chartInstance) {
      this.chartInstance.destroy();
      this.chartInstance = null;
    }
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler);
      this.resizeHandler = null;
    }
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
    if (this.themeObserver) {
      this.themeObserver.disconnect();
      this.themeObserver = null;
    }
    if (this.tooltipEl) {
      this.tooltipEl.remove();
      this.tooltipEl = null;
    }
  }

  // ---------------------------------------------------------------------------
  // Internal helpers
  // ---------------------------------------------------------------------------

  _rebuild() {
    if (!this.container) {
      return;
    }
    if (this.chartInstance) {
      this.chartInstance.destroy();
      this.chartInstance = null;
    }
    this.update(this.currentDataset);
  }

  async fetchCostData() {
    if (!this.options.enableCostView) {
      console.log(LOG_PREFIX, 'Cost view disabled');
      return null;
    }

    const projectId = this.state?.projectId;
    if (!projectId) {
      console.warn(LOG_PREFIX, 'Cannot load cost data without project ID');
      return null;
    }

    if (this.isLoadingCostData) {
      return null;
    }

    try {
      this.isLoadingCostData = true;
      const url = `/detail_project/api/v2/project/${projectId}/kurva-s-harga/`;
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Content-Type': 'application/json' },
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      const data = await response.json();
      if (data?.error) {
        throw new Error(data.error);
      }
      this.costData = data;
      console.log(LOG_PREFIX, 'Cost data loaded for uPlot chart');
      return data;
    } catch (error) {
      console.error(LOG_PREFIX, 'Failed to load cost data:', error);
      return null;
    } finally {
      this.isLoadingCostData = false;
    }
  }

  _transformDataset(dataset) {
    const xValues = dataset.labels.map((_, idx) => idx);
    const planned = dataset.planned.map((value) => Number(value) || 0);

    if (dataset.viewMode === 'cost' && Array.isArray(dataset.acSeries)) {
      const actualCost = dataset.acSeries.map((value) => Number(value) || 0);
      return [xValues, planned, actualCost];
    }

    const actual = dataset.actual.map((value) => Number(value) || 0);
    return [xValues, planned, actual];
  }

  _buildChartOptions(dataset, colors) {
    const isCostView = dataset.viewMode === 'cost' && Array.isArray(dataset.acSeries);
    return {
      width: this.container?.clientWidth || 800,
      height: this.options.height,
      scales: {
        x: { time: false },
        y: { auto: true },
      },
      axes: [
        {
          stroke: colors.axis,
          grid: { stroke: colors.gridLine },
          values: (u, vals) =>
            vals.map((v) => {
              if (!Number.isFinite(v)) {
                return '';
              }
              const nearestIndex = Math.round(v);
              if (Math.abs(v - nearestIndex) > 0.01) {
                return '';
              }
              if (nearestIndex < 0 || nearestIndex >= dataset.labels.length) {
                return '';
              }
              return dataset.labels[nearestIndex] || `Week ${nearestIndex + 1}`;
            }),
        },
        {
          stroke: colors.axis,
          grid: { stroke: colors.gridLine },
          label: isCostView ? '% of Total Cost' : 'Progress %',
          values: (u, vals) => vals.map((v) => `${Math.round(v)}%`),
        },
      ],
      legend: {
        show: true,
      },
      series: [
        {},
        {
          label: isCostView ? 'Rencana (PV)' : 'Rencana',
          stroke: colors.plannedLine,
          width: 2,
          fill: colors.plannedArea,
        },
        isCostView
          ? {
              label: 'Realisasi (AC)',
              stroke: colors.costActualLine || colors.actualLine,
              width: 3,
              fill: colors.costActualArea || colors.actualArea,
            }
          : {
              label: 'Realisasi',
              stroke: colors.actualLine,
              width: 2,
              fill: colors.actualArea,
            },
      ],
      cursor: {
        drag: { x: true, y: false },
        focus: { prox: 32 },
      },
      select: {
        show: true,
      },
      hooks: {
        ready: [
          () => {
            this._updateScaleBounds();
            this._attachInteractions();
          },
        ],
        setCursor: [
          (u) => this._updateTooltip(u),
        ],
        setScale: [
          () => this._updateTooltipPosition(),
        ],
        dblclick: [
          (u) => {
            const first = u.data[0][0];
            const last = u.data[0][u.data[0].length - 1];
            u.setScale('x', { min: first, max: last });
          },
        ],
      },
    };
  }

  _attachInteractions() {
    if (this._interactionAttached || !this.chartInstance) {
      return;
    }
    const target = this.chartInstance.over || this.container;
    if (!target) {
      return;
    }
    this._interactionTarget = target;
    this._wheelHandler = (event) => this._handleWheelInteraction(event);
    target.addEventListener('wheel', this._wheelHandler, { passive: false });
    this._interactionAttached = true;
  }

  _detachInteractions() {
    if (this._interactionAttached && this._interactionTarget && this._wheelHandler) {
      this._interactionTarget.removeEventListener('wheel', this._wheelHandler);
    }
    this._interactionAttached = false;
    this._wheelHandler = null;
    this._interactionTarget = null;
  }

  _handleWheelInteraction(event) {
    if (!this.chartInstance || !this._scaleBounds) {
      return;
    }

    const isZoomGesture = event.ctrlKey || event.metaKey;
    const isPanGesture = !isZoomGesture && event.shiftKey;
    if (!isZoomGesture && !isPanGesture) {
      return;
    }

    event.preventDefault();

    const bounds = this._scaleBounds;
    const scale = this.chartInstance.scales?.x || {};
    const currentMin = Number.isFinite(scale.min) ? scale.min : bounds.min;
    const currentMax = Number.isFinite(scale.max) ? scale.max : bounds.max;

    if (isZoomGesture) {
      const zoomIntensity = 0.12;
      const direction = event.deltaY > 0 ? 1 : -1;
      const factor = Math.max(0.2, 1 + zoomIntensity * direction);

      const overRect = (this.chartInstance.over || this.container).getBoundingClientRect();
      const cursorX = event.clientX - overRect.left;
      const cursorVal = this.chartInstance.posToVal(cursorX, 'x');
      const resolvedCursor = Number.isFinite(cursorVal) ? cursorVal : (currentMin + currentMax) / 2;

      const newMin = resolvedCursor - (resolvedCursor - currentMin) * factor;
      const newMax = resolvedCursor + (currentMax - resolvedCursor) * factor;
      this._setScaleBounded(newMin, newMax);
      return;
    }

    const range = currentMax - currentMin;
    const panStep = Math.max(1, range * 0.15);
    const delta = event.deltaY > 0 ? panStep : -panStep;
    this._setScaleBounded(currentMin + delta, currentMax + delta);
  }

  _setScaleBounded(targetMin, targetMax) {
    if (!this.chartInstance || !this._scaleBounds) {
      return;
    }

    const bounds = this._scaleBounds;
    const boundsSpan = bounds.max - bounds.min;
    if (boundsSpan <= 0) {
      return;
    }

    const minWindow = 1;
    let minVal = Math.min(targetMin, targetMax);
    let maxVal = Math.max(targetMin, targetMax);
    let windowSize = Math.max(minWindow, maxVal - minVal);

    if (windowSize > boundsSpan) {
      windowSize = boundsSpan;
    }

    minVal = Math.max(bounds.min, Math.min(minVal, bounds.max - windowSize));
    maxVal = minVal + windowSize;
    if (maxVal > bounds.max) {
      maxVal = bounds.max;
      minVal = maxVal - windowSize;
    }

    this.chartInstance.setScale('x', { min: minVal, max: maxVal });
  }

  _updateScaleBounds() {
    if (!this.chartInstance || !Array.isArray(this.chartInstance.data?.[0])) {
      return;
    }
    const xValues = this.chartInstance.data[0];
    if (!xValues.length) {
      return;
    }
    this._scaleBounds = {
      min: xValues[0],
      max: xValues[xValues.length - 1],
    };
  }

  _createTooltip() {
    const tooltip = document.createElement('div');
    tooltip.className = 'kurva-s-tooltip';
    tooltip.style.position = 'absolute';
    tooltip.style.pointerEvents = 'none';
    tooltip.style.padding = '8px 10px';
    tooltip.style.borderRadius = '6px';
    tooltip.style.background = 'rgba(15, 23, 42, 0.85)';
    tooltip.style.color = '#fff';
    tooltip.style.fontSize = '12px';
    tooltip.style.transform = 'translate(-50%, -100%)';
    tooltip.style.opacity = '0';
    tooltip.style.transition = 'opacity 0.15s ease';

    this.tooltipEl = tooltip;
    this.container.appendChild(tooltip);
  }

  _updateTooltip(u) {
    if (!this.tooltipEl || !this.currentDataset) {
      return;
    }

    const idx = u.cursor.idx;
    if (idx == null || idx < 0 || idx >= this.currentDataset.labels.length) {
      this.tooltipEl.style.opacity = '0';
      return;
    }

    const labels = this.currentDataset.labels || [];
    const label = labels[idx] || `Week ${idx + 1}`;
    const planned = this.currentDataset.planned[idx] ?? 0;
    const detailArray = Array.isArray(this.currentDataset.details) ? this.currentDataset.details : null;
    const detailObject = !detailArray && this.currentDataset.details ? this.currentDataset.details : {};
    const totalCost = Number(detailObject.totalCost || this.currentDataset.totalBiaya || 0) || 0;
    const weeklyCostSummary = Array.isArray(detailObject.weeklySummary) ? detailObject.weeklySummary : null;
    const summaryEntry = weeklyCostSummary ? weeklyCostSummary[idx] : null;
    const isCostView = (this.viewMode || this.currentDataset.viewMode) === 'cost';

    const htmlParts = [
      `<div style="font-weight:600;margin-bottom:4px;">${label}</div>`,
    ];

    if (isCostView) {
      const acSeries = Array.isArray(this.currentDataset.acSeries)
        ? this.currentDataset.acSeries
        : this.currentDataset.actual || [];
      const actual = acSeries[idx] ?? 0;
      const variance = summaryEntry?.variancePercent ?? Number((actual - planned).toFixed(2));
      const plannedWeek = Array.isArray(detailObject.weeks) ? detailObject.weeks[idx] : null;
      const actualWeek = Array.isArray(detailObject.actualWeeks) ? detailObject.actualWeeks[idx] : null;
      const rangeText = this._formatWeekRange(plannedWeek, actualWeek);
      const plannedAmount =
        typeof summaryEntry?.plannedCostValue === 'number'
          ? formatRupiah(summaryEntry.plannedCostValue)
          : this._resolveCostAmount(plannedWeek, planned, totalCost);
      const actualAmount =
        typeof summaryEntry?.actualCostValue === 'number'
          ? formatRupiah(summaryEntry.actualCostValue)
          : this._resolveCostAmount(actualWeek, actual, totalCost);
      const varianceAmount =
        typeof summaryEntry?.varianceCostValue === 'number'
          ? formatRupiah(summaryEntry.varianceCostValue)
          : '';
      const varianceColor = this._getVarianceColor(variance);

      if (rangeText) {
        htmlParts.push(`<div style="font-size:0.85em;color:#cbd5e1;margin-bottom:4px;">Periode: ${rangeText}</div>`);
      }
      htmlParts.push(
        `<div>Rencana (PV): <strong>${formatPercentage(planned)}</strong> <span style="color:#cbd5e1;font-size:0.85em;">(${plannedAmount})</span></div>`,
        `<div>Realisasi (AC): <strong>${formatPercentage(actual)}</strong> <span style="color:#cbd5e1;font-size:0.85em;">(${actualAmount})</span></div>`,
        `<div>Variance: <strong style="color:${varianceColor};">${variance >= 0 ? '+' : ''}${variance.toFixed(1)}%</strong>${varianceAmount ? ` <span style="color:${varianceColor};font-size:0.85em;">(${varianceAmount})</span>` : ''}</div>`,
      );
    } else {
      const actual = this.currentDataset.actual[idx] ?? 0;
      const variance = Number((actual - planned).toFixed(2));
      const detail = detailArray ? detailArray[idx] : null;
      const startLabel = detail?.start ? this._formatDateLabel(detail.start) : '';
      const endLabel = detail?.end ? this._formatDateLabel(detail.end) : '';
      const rangeText = this._composeRangeText(startLabel, endLabel);
      const useHarga = Boolean(this.currentDataset.useHargaCalculation && totalCost > 0);
      const plannedAmountValue =
        typeof detail?.plannedCostValue === 'number' ? detail.plannedCostValue : (totalCost * planned) / 100;
      const actualAmountValue =
        typeof detail?.actualCostValue === 'number' ? detail.actualCostValue : (totalCost * actual) / 100;
      const plannedAmount = useHarga ? formatRupiah(plannedAmountValue || 0) : '';
      const actualAmount = useHarga ? formatRupiah(actualAmountValue || 0) : '';
      const varianceAmount =
        useHarga && typeof detail?.varianceCostValue === 'number'
          ? formatRupiah(detail.varianceCostValue)
          : useHarga
          ? formatRupiah((actualAmountValue || 0) - (plannedAmountValue || 0))
          : '';
      const varianceColor = this._getVarianceColor(variance);

      if (rangeText) {
        htmlParts.push(`<div style="font-size:0.85em;color:#cbd5e1;margin-bottom:4px;">Periode: ${rangeText}</div>`);
      }

      htmlParts.push(`<div>Rencana: <strong>${formatPercentage(planned)}</strong>${useHarga ? ` <span style="color:#cbd5e1;font-size:0.85em;">(${plannedAmount})</span>` : ''}</div>`);
      htmlParts.push(`<div>Realisasi: <strong>${formatPercentage(actual)}</strong>${useHarga ? ` <span style="color:#cbd5e1;font-size:0.85em;">(${actualAmount})</span>` : ''}</div>`);
      htmlParts.push(`<div>Variance: <strong style="color:${varianceColor};">${variance >= 0 ? '+' : ''}${variance.toFixed(1)}%</strong>${useHarga ? ` <span style="color:${varianceColor};font-size:0.85em;">(${varianceAmount})</span>` : ''}</div>`);
    }

    this.tooltipEl.innerHTML = htmlParts.join('');

    const xValue = u.data[0][idx];
    const left = u.valToPos(xValue, 'x');
    const seriesIndex = Math.min(2, u.data.length - 1);
    let seriesValue = u.data[seriesIndex]?.[idx];
    if (!Number.isFinite(seriesValue)) {
      seriesValue = u.data[1]?.[idx] ?? 0;
    }
    const top = u.valToPos(seriesValue, 'y');
    this.tooltipEl.style.left = `${left}px`;
    this.tooltipEl.style.top = `${top}px`;
    this.tooltipEl.style.opacity = '1';
  }

  _updateTooltipPosition() {
    if (!this.chartInstance || !this.tooltipEl) {
      return;
    }
    const { idx } = this.chartInstance.cursor;
    if (idx != null) {
      this._updateTooltip(this.chartInstance);
    }
  }

  _formatDateLabel(input) {
    if (!input) {
      return '';
    }
    let date = input;
    if (!(input instanceof Date)) {
      date = new Date(input);
    }
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
      return '';
    }
    if (!this._dateFormatter && typeof Intl !== 'undefined' && typeof Intl.DateTimeFormat === 'function') {
      try {
        this._dateFormatter = new Intl.DateTimeFormat('id-ID', {
          day: '2-digit',
          month: 'short',
          year: 'numeric',
        });
      } catch (error) {
        console.warn(LOG_PREFIX, 'Intl.DateTimeFormat unavailable, falling back to basic formatter:', error);
        this._dateFormatter = null;
      }
    }
    if (this._dateFormatter) {
      return this._dateFormatter.format(date);
    }
    const day = String(date.getDate()).padStart(2, '0');
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const year = date.getFullYear();
    return `${day}/${month}/${year}`;
  }

  _formatWeekRange(plannedWeek, actualWeek) {
    const startRaw = plannedWeek?.week_start || actualWeek?.week_start;
    const endRaw = plannedWeek?.week_end || actualWeek?.week_end;
    const startLabel = startRaw ? this._formatDateLabel(new Date(startRaw)) : '';
    const endLabel = endRaw ? this._formatDateLabel(new Date(endRaw)) : '';
    return this._composeRangeText(startLabel, endLabel);
  }

  _composeRangeText(startLabel, endLabel) {
    if (startLabel && endLabel) {
      return `${startLabel} - ${endLabel}`;
    }
    return startLabel || endLabel || '';
  }

  _getVarianceColor(value) {
    if (value > 0.1) {
      return '#f87171';
    }
    if (value < -0.1) {
      return '#22c55e';
    }
    return '#cbd5e1';
  }

  _resolveCostAmount(weekEntry, percent, totalCost) {
    if (weekEntry) {
      const cumulative = this._parseNumber(weekEntry.cumulative_cost);
      if (Number.isFinite(cumulative) && cumulative > 0) {
        return formatRupiah(cumulative);
      }
      const singleCost = this._parseNumber(weekEntry.cost);
      if (Number.isFinite(singleCost) && singleCost > 0) {
        return formatRupiah(singleCost);
      }
    }

    if (!Number.isFinite(totalCost) || totalCost <= 0) {
      return formatRupiah(0);
    }
    return formatRupiah((totalCost * percent) / 100);
  }

  _parseNumber(value) {
    if (typeof value === 'number') {
      return value;
    }
    if (typeof value === 'string') {
      const parsed = Number(value);
      return Number.isFinite(parsed) ? parsed : NaN;
    }
    return NaN;
  }
}

export default KurvaSUPlotChart;
