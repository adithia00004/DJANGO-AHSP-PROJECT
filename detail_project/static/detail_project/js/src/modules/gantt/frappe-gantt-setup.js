/**
 * Frappe Gantt Setup Module
 * Modern ES6 implementation of Gantt chart using Frappe Gantt library
 *
 * Migrated from legacy gantt_module.js
 * Date: 2025-11-20
 */

// Import required utilities from chart-utils
import {
  normalizeDate,
  formatDate,
  calculateDateRange,
  getSortedColumns,
  buildVolumeLookup,
  getVolumeForPekerjaan,
  // buildCellValueMap, // Phase 0.5: Removed (unused, deprecated)
  setupThemeObserver,
  ONE_DAY_MS,
} from '../shared/chart-utils.js';

// =========================================================================
// CONSTANTS
// =========================================================================

const LOG_PREFIX = '[GanttChart]';

const VIEW_MODES = {
  DAY: 'Day',
  WEEK: 'Week',
  MONTH: 'Month',
};

const DEFAULT_VIEW_MODE = VIEW_MODES.WEEK;

const TASK_CLASSES = {
  COMPLETE: 'gantt-task-complete',
  IN_PROGRESS: 'gantt-task-in-progress',
  NOT_STARTED: 'gantt-task-not-started',
  MILESTONE: 'bar-milestone',
  PEKERJAAN: 'bar-pekerjaan',
};

const CHART_DEFAULTS = {
  height: '520px',
  width: '100%',
};

const SUMMARY_DATE_FORMAT_OPTIONS = {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
};

const STATUS_KEYS = {
  COMPLETE: 'complete',
  IN_PROGRESS: 'inProgress',
  NOT_STARTED: 'notStarted',
};

const STATUS_LABELS = {
  [STATUS_KEYS.COMPLETE]: 'Selesai',
  [STATUS_KEYS.IN_PROGRESS]: 'Sedang berjalan',
  [STATUS_KEYS.NOT_STARTED]: 'Belum mulai',
};

const UNIT_IN_MS = {
  hour: 60 * 60 * 1000,
  day: 24 * 60 * 60 * 1000,
  week: 7 * 24 * 60 * 60 * 1000,
  month: 30 * 24 * 60 * 60 * 1000,
  year: 365 * 24 * 60 * 60 * 1000,
};

// =========================================================================
// UTILITY FUNCTIONS
// =========================================================================

/**
 * Escape HTML to prevent XSS
 *
 * @param {string} text - Text to escape
 * @returns {string} Escaped HTML
 */
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text || '';
  return div.innerHTML;
}

/**
 * Normalize view mode to valid Frappe Gantt mode
 *
 * @param {string} mode - View mode input
 * @returns {string} Normalized view mode
 */
function normalizeViewMode(mode) {
  if (!mode) return DEFAULT_VIEW_MODE;

  const value = String(mode).trim().toLowerCase();
  if (value === 'day') return VIEW_MODES.DAY;
  if (value === 'month') return VIEW_MODES.MONTH;
  return VIEW_MODES.WEEK;
}

/**
 * Categorize progress into summary status buckets
 *
 * @param {number} progress - Progress percentage
 * @returns {string} Status key
 */
function getStatusKeyFromProgress(progress) {
  const value = Number.isFinite(progress) ? progress : 0;
  if (value >= 100) return STATUS_KEYS.COMPLETE;
  if (value > 0) return STATUS_KEYS.IN_PROGRESS;
  return STATUS_KEYS.NOT_STARTED;
}

/**
 * Format progress value for display
 *
 * @param {number} progress - Progress percentage
 * @returns {string} Formatted label (e.g. "45%")
 */
function formatProgressLabel(progress) {
  const value = Math.max(0, Math.min(100, Number(progress) || 0));
  return `${value.toFixed(value % 1 === 0 ? 0 : 1)}%`;
}

function formatDeltaLabel(value) {
  const numeric = Number(value) || 0;
  const formatted = numeric.toFixed(Math.abs(numeric) % 1 === 0 ? 0 : 1);
  if (numeric === 0) {
    return '0%';
  }
  return `${numeric > 0 ? '+' : ''}${formatted}%`;
}

/**
 * Create Intl formatter for summary dates with graceful fallback
 *
 * @param {Array<string>} localeCandidates - Ordered locale list
 * @returns {Intl.DateTimeFormat|{format: Function}} Formatter instance
 */
function createDateFormatter(localeCandidates = []) {
  for (const locale of localeCandidates) {
    if (!locale) continue;
    try {
      return new Intl.DateTimeFormat(locale, SUMMARY_DATE_FORMAT_OPTIONS);
    } catch (error) {
      console.warn(`${LOG_PREFIX} Failed to create Intl formatter (${locale}):`, error);
    }
  }

  try {
    return new Intl.DateTimeFormat('en-US', SUMMARY_DATE_FORMAT_OPTIONS);
  } catch (error) {
    console.warn(`${LOG_PREFIX} Intl fallback failed, using ISO formatter`, error);
    return {
      format: (date) => formatDate(date) || '',
    };
  }
}

/**
 * Build hierarchical path for pekerjaan
 * Traverses pekerjaanTree to build path from root to node
 *
 * @param {Object} state - Application state
 * @returns {Object} {nodeMap, pathMap}
 */
function buildPekerjaanPathMaps(state) {
  const nodeMap = new Map();
  const pathMap = new Map();

  const traverse = (nodes, prefix = []) => {
    if (!Array.isArray(nodes)) return;

    nodes.forEach(node => {
      const label = node.nama || node.name || node.kode || `Node ${node.id}`;
      const nextPrefix = prefix.concat(label);

      // Map pekerjaan nodes
      if (node.type === 'pekerjaan') {
        const key = String(node.id);
        nodeMap.set(key, node);
        pathMap.set(key, nextPrefix);
      }

      // Recursively traverse children
      if (node.children && node.children.length > 0) {
        traverse(node.children, nextPrefix);
      }
    });
  };

  traverse(state.pekerjaanTree || []);
  return { nodeMap, pathMap };
}

/**
 * Build pekerjaan hierarchy with levels
 * Flattens tree structure with level information
 *
 * @param {Object} state - Application state
 * @returns {Array} Flattened pekerjaan list with levels
 */
function buildPekerjaanHierarchy(state) {
  const result = [];

  const walk = (nodes, level = 0, ancestors = []) => {
    if (!Array.isArray(nodes)) return;

    nodes.forEach((node) => {
      const label = node.nama || node.name || node.kode || `Node ${node.id}`;
      const pathParts = ancestors.concat(label);

      if (node.type === 'pekerjaan') {
        result.push({
          id: String(node.id),
          level,
          pathParts,
        });
      }

      if (node.children && node.children.length > 0) {
        walk(node.children, level + 1, pathParts);
      }
    });
  };

  walk(state.pekerjaanTree || [], 0, []);
  return result;
}

/**
 * Calculate project date range from state
 *
 * @param {Object} state - Application state
 * @returns {Object} {min, max} timestamps
 */
function computeProjectRange(state) {
  const start = state && state.projectStart ? new Date(state.projectStart) : null;
  const end = state && state.projectEnd ? new Date(state.projectEnd) : null;

  const startSafe = (start instanceof Date && !Number.isNaN(start.getTime()))
    ? start.getTime()
    : Date.now();

  const endSafe = (end instanceof Date && !Number.isNaN(end.getTime()) && end.getTime() > startSafe)
    ? end.getTime()
    : startSafe + 30 * ONE_DAY_MS;

  return { min: startSafe, max: endSafe };
}

// =========================================================================
// GANTT CHART CLASS
// =========================================================================

/**
 * GanttChart - Modern ES6 wrapper for Frappe Gantt
 *
 * Features:
 * - Hierarchical task display with indentation
 * - Progress bars from volume-weighted assignments
 * - Multiple view modes (Day/Week/Month)
 * - Theme-aware styling
 * - Automatic updates on state changes
 *
 * @class
 */
export class GanttChart {
  /**
   * Create a new GanttChart instance
   *
   * @param {Object} state - Application state
   * @param {Object} options - Configuration options
   */
  constructor(state, options = {}) {
    console.log(`${LOG_PREFIX} Creating new instance`);

    this.state = state;
    this.options = {
      viewMode: DEFAULT_VIEW_MODE,
      enableThemeObserver: true,
      enableResizeHandler: true,
      language: 'id-ID',
      barHeight: options?.barHeight || 32,
      barPadding: options?.barPadding || 18,
      summaryLocale: options.summaryLocale || options.language || 'id-ID',
      ...options,
    };

    this.ganttInstance = null;
    this.container = null;
    this.themeObserver = null;
    this.resizeHandler = null;

    this.tasks = [];
    this.columnLookup = new Map();
    this.volumeLookup = new Map();
    this.summaryRows = [];
    this.lastHierarchy = [];
    this.rowVisualHeight = 0;
    this._actualOverlayRefs = [];

    console.log(`${LOG_PREFIX} Instance created with view mode: ${this.options.viewMode}`);
  }

  /**
   * Initialize Gantt chart in container
   *
   * @param {HTMLElement|string} container - Container element or ID
   * @returns {boolean} Success status
   */
  initialize(container) {
    console.log(`${LOG_PREFIX} Initializing...`);

    // Resolve container
    if (typeof container === 'string') {
      this.container = document.getElementById(container);
    } else if (container instanceof HTMLElement) {
      this.container = container;
    } else {
      console.error(`${LOG_PREFIX} Invalid container:`, container);
      return false;
    }

    if (!this.container) {
      console.error(`${LOG_PREFIX} Container not found`);
      return false;
    }

    // Set default container styles
    if (!this.container.style.height) {
      this.container.style.height = CHART_DEFAULTS.height;
    }
    if (!this.container.style.width) {
      this.container.style.width = CHART_DEFAULTS.width;
    }

    // Check Frappe Gantt availability
    if (typeof window.Gantt !== 'function') {
      console.error(`${LOG_PREFIX} Frappe Gantt library not found. Make sure it's loaded before initializing.`);
      return false;
    }

    // Build initial tasks
    this._buildLookups();
    this.tasks = this._buildTasks();

    // Create Gantt instance
    this._createGanttInstance();

    // Setup observers
    if (this.options.enableThemeObserver) {
      this._setupThemeObserver();
    }

    if (this.options.enableResizeHandler) {
      this._setupResizeHandler();
    }

    console.log(`${LOG_PREFIX} Initialized successfully with ${this.tasks.length} tasks`);
    return true;
  }

  /**
   * Update Gantt chart with new data
   *
   * @param {Object} data - New state data (optional, uses this.state if not provided)
   * @param {string} viewMode - View mode override (optional)
   * @returns {boolean} Success status
   */
  update(data = null, viewMode = null) {
    console.log(`${LOG_PREFIX} Updating chart...`);

    if (!this.ganttInstance) {
      console.warn(`${LOG_PREFIX} Cannot update: not initialized`);
      return false;
    }

    // Update state if provided
    if (data) {
      Object.assign(this.state, data);
    }

    // Rebuild tasks
    this._buildLookups();
    this.tasks = this._buildTasks();

    try {
      // Refresh Gantt with new tasks
      this.ganttInstance.refresh(this.tasks);

      // Change view mode if specified
      if (viewMode) {
        this.changeViewMode(viewMode);
      } else {
        // Reapply current view mode to ensure proper rendering
        this.ganttInstance.change_view_mode(this.options.viewMode);
      }
      this._afterRender();

      console.log(`${LOG_PREFIX} Updated successfully with ${this.tasks.length} tasks`);
      return true;
    } catch (error) {
      console.error(`${LOG_PREFIX} Update failed:`, error);
      return false;
    }
  }

  /**
   * Change Gantt view mode
   *
   * @param {string} mode - View mode: 'Day', 'Week', 'Month'
   * @returns {boolean} Success status
   */
  changeViewMode(mode) {
    const normalized = normalizeViewMode(mode);

    if (!this.ganttInstance) {
      console.warn(`${LOG_PREFIX} Cannot change view mode: not initialized`);
      this.options.viewMode = normalized;
      return false;
    }

    try {
      this.ganttInstance.change_view_mode(normalized);
      this.options.viewMode = normalized;

      // Update state cache if available
      if (this.state) {
        this.state.cache = this.state.cache || {};
        this.state.cache.ganttViewMode = normalized;
      }

      console.log(`${LOG_PREFIX} View mode changed to: ${normalized}`);
      return true;
    } catch (error) {
      console.error(`${LOG_PREFIX} Failed to change view mode:`, error);
      return false;
    }
  }

  /**
   * Dispose Gantt chart and cleanup
   */
  dispose() {
    console.log(`${LOG_PREFIX} Disposing...`);

    // Destroy Gantt instance
    if (this.ganttInstance && typeof this.ganttInstance.destroy === 'function') {
      try {
        this.ganttInstance.destroy();
      } catch (error) {
        console.warn(`${LOG_PREFIX} Error destroying Gantt instance:`, error);
      }
    }

    // Cleanup theme observer
    if (this.themeObserver) {
      this.themeObserver.disconnect();
      this.themeObserver = null;
    }

    // Cleanup resize handler
    if (this.resizeHandler) {
      window.removeEventListener('resize', this.resizeHandler);
      this.resizeHandler = null;
    }

    // Clear references
    this.ganttInstance = null;
    this.container = null;
    this.tasks = [];
    this.columnLookup.clear();
    this.volumeLookup.clear();
    this.summaryRows = [];

    console.log(`${LOG_PREFIX} Disposed successfully`);
  }

  // =========================================================================
  // PRIVATE METHODS - Data Building
  // =========================================================================

  /**
   * Build lookup maps for columns and volumes
   * @private
   */
  _buildLookups() {
    // Build column lookup
    this.columnLookup.clear();
    (this.state.timeColumns || []).forEach((col) => {
      if (!col || !col.id) return;

      const rawStart = col.startDate instanceof Date ? col.startDate : (col.startDate ? new Date(col.startDate) : null);
      if (!(rawStart instanceof Date) || Number.isNaN(rawStart.getTime())) {
        return;
      }

      let rawEnd = col.endDate instanceof Date ? col.endDate : (col.endDate ? new Date(col.endDate) : null);
      if (!(rawEnd instanceof Date) || Number.isNaN(rawEnd.getTime()) || rawEnd.getTime() <= rawStart.getTime()) {
        rawEnd = new Date(rawStart.getTime() + ONE_DAY_MS);
      }

      this.columnLookup.set(String(col.id), {
        column: col,
        startDate: rawStart,
        endDate: rawEnd,
        label: col.label || '',
        rangeLabel: col.rangeLabel || col.subLabel || '',
      });
    });

    // Build volume lookup
    this.volumeLookup = buildVolumeLookup(this.state);
  }

  /**
   * Build tasks array from state
   * @private
   * @returns {Array} Frappe Gantt tasks
   */
  _buildTasks() {
    const { nodeMap, pathMap } = buildPekerjaanPathMaps(this.state);
    const pekerjaanList = buildPekerjaanHierarchy(this.state);

    // Build assignment buckets per mode
    const modeBuckets = this._buildModeBuckets();
    const plannedBuckets = modeBuckets.planned;
    const actualBuckets = modeBuckets.actual;

    // Get project date range
    const projectRange = computeProjectRange(this.state);
    const projectStartSafe = new Date(projectRange.min);
    const projectEndSafe = new Date(projectRange.max);

    const tasks = [];
    const summarySeed = [];
    const hierarchySeed = [];

    pekerjaanList.forEach((pekerjaan) => {
      const pekerjaanId = pekerjaan.id;
      const plannedBucket = plannedBuckets.get(pekerjaanId) || null;
      const actualBucket = actualBuckets.get(pekerjaanId) || null;
      const node = nodeMap.get(pekerjaanId);
      const pathParts = pekerjaan.pathParts.length > 0
        ? pekerjaan.pathParts
        : (pathMap.get(pekerjaanId) || [node ? (node.nama || node.name || `Pekerjaan ${pekerjaanId}`) : `Pekerjaan ${pekerjaanId}`]);

      const displayLabel = pathParts.join(' / ') || `Pekerjaan ${pekerjaanId}`;

      // Create indentation prefix (2 non-breaking spaces per level, starting from level 2)
      const indentPrefix = '\u00A0\u00A0'.repeat(Math.max(0, pekerjaan.level - 2));
      const name = indentPrefix + (pathParts[pathParts.length - 1] || displayLabel);

      const plannedRange = this._resolveRangeFromBucket(plannedBucket, projectStartSafe, projectEndSafe, displayLabel);
      const actualRange = this._resolveRangeFromBucket(actualBucket, projectStartSafe, projectEndSafe, displayLabel);

      // Determine task class based on planned progress
      let customClass = TASK_CLASSES.PEKERJAAN;
      if (plannedRange.progress >= 100) {
        customClass = TASK_CLASSES.COMPLETE;
      } else if (plannedRange.progress > 0) {
        customClass = TASK_CLASSES.IN_PROGRESS;
      } else {
        customClass = TASK_CLASSES.NOT_STARTED;
      }

      tasks.push({
        id: `pekerjaan-${pekerjaanId}`,
        name,
        start: plannedRange.startISO,
        end: plannedRange.endISO,
        progress: plannedRange.progress,
        custom_class: customClass,
        dependencies: '', // Can be populated if dependency data exists
        metadata: {
          pekerjaanId,
          label: displayLabel,
          start: plannedRange.startISO,
          end: plannedRange.endISO,
          pathParts,
          plannedRange,
          actualRange,
          hasPlanData: plannedRange.hasData,
          hasActualData: actualRange.hasData,
        },
      });

      summarySeed.push({
        pekerjaanId,
        label: displayLabel,
        shortLabel: pathParts[pathParts.length - 1] || displayLabel,
        pathLabel: displayLabel,
        planned: plannedRange,
        actual: actualRange,
      });

      hierarchySeed.push({
        id: pekerjaanId,
        level: pekerjaan.level,
        label: pathParts[pathParts.length - 1] || displayLabel,
        pathParts,
        kode: node?.kode || null,
      });
    });

    this.summaryRows = this._buildSummaryRows(summarySeed);
    this.lastHierarchy = hierarchySeed;
    console.log(`${LOG_PREFIX} Built ${tasks.length} tasks`);
    return tasks;
  }

  _resolveRangeFromBucket(bucket, defaultStart, defaultEnd, fallbackLabel) {
    if (!bucket || !bucket.start || !bucket.end) {
      const defaultStartISO = formatDate(defaultStart) || defaultStart.toISOString().split('T')[0];
      const defaultEndISO = formatDate(defaultEnd) || defaultEnd.toISOString().split('T')[0];

      return {
        startDate: defaultStart,
        endDate: defaultEnd,
        startISO: defaultStartISO,
        endISO: defaultEndISO,
        startValue: defaultStart.getTime(),
        endValue: defaultEnd.getTime(),
        segments: [],
        progress: 0,
        hasData: false,
      };
    }

    const startDate = bucket.start;
    const endDate = bucket.end;
    const startValue = startDate.getTime();
    const endValue = Math.max(endDate.getTime(), startValue + ONE_DAY_MS);
    const startISO = formatDate(startDate) || new Date(startValue).toISOString().split('T')[0];
    const endISO = formatDate(new Date(endValue)) || new Date(endValue).toISOString().split('T')[0];

    const segments = bucket.segments
      .sort((a, b) => a.start - b.start)
      .map((segment) => ({
        label: segment.label || segment.rangeLabel || fallbackLabel,
        start: formatDate(segment.start) || segment.start.toISOString().split('T')[0],
        end: formatDate(segment.end) || segment.end.toISOString().split('T')[0],
        percent: Math.max(0, Math.min(100, segment.percent)),
      }));

    return {
      startDate,
      endDate: new Date(endValue),
      startISO,
      endISO,
      startValue,
      endValue,
      segments,
      progress: Math.max(0, Math.min(100, bucket.totalPercent)),
      hasData: bucket.hasData,
    };
  }

  /**
   * Build summary rows for external UI (e.g., table beside chart)
   * @private
   * @param {Array} seedRows - Raw pekerjaan info
   * @returns {Array} Summary rows sorted by start date
   */
  _buildSummaryRows(seedRows = []) {
    if (!Array.isArray(seedRows) || seedRows.length === 0) {
      return [];
    }

    const browserLocale = typeof navigator !== 'undefined' ? navigator.language : null;
    const formatter = createDateFormatter([
      this.options.summaryLocale,
      this.options.language,
      browserLocale,
      'id-ID',
      'en-US',
    ]);

    const rows = seedRows
      .map((row) => {
        const plannedStart = row.planned?.startDate instanceof Date ? row.planned.startDate : null;
        const plannedEnd = row.planned?.endDate instanceof Date ? row.planned.endDate : null;
        const actualStart = row.actual?.startDate instanceof Date ? row.actual.startDate : null;
        const actualEnd = row.actual?.endDate instanceof Date ? row.actual.endDate : null;

        const plannedStartLabel = plannedStart && !Number.isNaN(plannedStart.getTime())
          ? formatter.format(plannedStart)
          : '-';
        const plannedEndLabel = plannedEnd && !Number.isNaN(plannedEnd.getTime())
          ? formatter.format(plannedEnd)
          : '-';

        const actualStartLabel = actualStart && !Number.isNaN(actualStart.getTime())
          ? formatter.format(actualStart)
          : '-';
        const actualEndLabel = actualEnd && !Number.isNaN(actualEnd.getTime())
          ? formatter.format(actualEnd)
          : '-';

        const plannedProgress = Math.max(0, Math.min(100, Number(row.planned?.progress) || 0));
        const actualProgress = Math.max(0, Math.min(100, Number(row.actual?.progress) || 0));
        const status = getStatusKeyFromProgress(actualProgress || plannedProgress);

        return {
          pekerjaanId: row.pekerjaanId,
          label: row.label,
          shortLabel: row.shortLabel || row.label,
          pathLabel: row.pathLabel || row.label,
          planned: {
            startLabel: plannedStartLabel,
            endLabel: plannedEndLabel,
            progress: plannedProgress,
            progressLabel: formatProgressLabel(plannedProgress),
            hasData: row.planned?.hasData,
            startValue: row.planned?.startValue || null,
            endValue: row.planned?.endValue || null,
          },
          actual: {
            startLabel: actualStartLabel,
            endLabel: actualEndLabel,
            progress: actualProgress,
            progressLabel: formatProgressLabel(actualProgress),
            hasData: row.actual?.hasData,
            startValue: row.actual?.startValue || null,
            endValue: row.actual?.endValue || null,
          },
          delta: actualProgress - plannedProgress,
          deltaLabel: formatDeltaLabel(actualProgress - plannedProgress),
          status,
          statusLabel: STATUS_LABELS[status],
        };
      })
      .sort((a, b) => {
        const aStart = Number.isFinite(a.planned?.startValue) ? a.planned.startValue : Number.POSITIVE_INFINITY;
        const bStart = Number.isFinite(b.planned?.startValue) ? b.planned.startValue : Number.POSITIVE_INFINITY;

        if (aStart === bStart) {
          return (a.planned?.endValue || 0) - (b.planned?.endValue || 0);
        }

        return aStart - bStart;
      })
      .map((row, index) => ({
        ...row,
        index: index + 1,
      }));

    return rows;
  }

  _afterRender() {
    if (!this.ganttInstance || !Array.isArray(this.ganttInstance.bars)) {
      return;
    }

    this._applyDualLaneLayout();
    this._renderActualOverlays();

    if (this.ganttInstance.options) {
      this.rowVisualHeight = (this.ganttInstance.options.bar_height || 30) + (this.ganttInstance.options.padding || 18);
    }
  }

  _applyDualLaneLayout() {
    const bars = this.ganttInstance?.bars || [];
    const totalHeight = this.ganttInstance?.options?.bar_height || 30;
    const laneGap = Math.max(3, Math.round(totalHeight * 0.2));
    const laneHeight = Math.max(6, Math.floor((totalHeight - laneGap) / 2));

    bars.forEach((bar) => {
      if (!bar.$bar) return;

      const baseY = bar.$bar.getY();
      bar.$bar.setAttribute('height', laneHeight);
      bar.$bar.setAttribute('y', baseY);

      if (bar.$bar_progress) {
        bar.$bar_progress.remove();
        bar.$bar_progress = null;
      }

      bar.__dualLane = {
        plannedY: baseY,
        actualY: baseY + laneHeight + laneGap,
        laneHeight,
      };
    });
  }

  _clearActualOverlays() {
    if (Array.isArray(this._actualOverlayRefs)) {
      this._actualOverlayRefs.forEach((node) => {
        if (node && typeof node.remove === 'function') {
          node.remove();
        }
      });
    }
    this._actualOverlayRefs = [];
  }

  _renderActualOverlays() {
    if (!this.ganttInstance || !Array.isArray(this.ganttInstance.bars)) {
      return;
    }

    this._clearActualOverlays();

    const namespace = 'http://www.w3.org/2000/svg';
    this.ganttInstance.bars.forEach((bar) => {
      const actualRange = bar.task?.metadata?.actualRange;
      const lane = bar.__dualLane;
      if (!actualRange || !lane || !actualRange.hasData) {
        return;
      }

      const { x, width } = this._computeRangePosition(actualRange.startDate, actualRange.endDate);
      const rect = document.createElementNS(namespace, 'rect');
      rect.setAttribute('x', x);
      rect.setAttribute('y', lane.actualY);
      rect.setAttribute('width', Math.max(width, 2));
      rect.setAttribute('height', lane.laneHeight);
      rect.setAttribute('rx', this.ganttInstance.options.bar_corner_radius);
      rect.setAttribute('ry', this.ganttInstance.options.bar_corner_radius);
      rect.setAttribute('class', `bar-actual-overlay${actualRange.hasData ? '' : ' has-no-data'}`);
      bar.bar_group.appendChild(rect);
      this._actualOverlayRefs.push(rect);
    });
  }

  _computeRangePosition(startDate, endDate) {
    if (!this.ganttInstance || !this.ganttInstance.config || !this.ganttInstance.gantt_start) {
      return { x: 0, width: 0 };
    }

    const config = this.ganttInstance.config;
    const start = startDate instanceof Date ? startDate : (startDate ? new Date(startDate) : new Date(this.ganttInstance.gantt_start));
    const end = endDate instanceof Date ? endDate : (endDate ? new Date(endDate) : new Date(start.getTime() + ONE_DAY_MS));
    const safeStart = Number.isNaN(start.getTime()) ? new Date(this.ganttInstance.gantt_start) : start;
    const safeEndRaw = Number.isNaN(end.getTime()) ? new Date(safeStart.getTime() + ONE_DAY_MS) : end;
    const safeEnd = safeEndRaw.getTime() <= safeStart.getTime()
      ? new Date(safeStart.getTime() + ONE_DAY_MS)
      : safeEndRaw;

    const unit = config.unit || 'day';
    const unitMs = UNIT_IN_MS[unit] || UNIT_IN_MS.day;
    const step = config.step || 1;
    const columnWidth = config.column_width || this.ganttInstance.options?.column_width || 40;
    const diffStartUnits = (safeStart.getTime() - this.ganttInstance.gantt_start.getTime()) / unitMs;
    const durationUnits = Math.max(0.1, (safeEnd.getTime() - safeStart.getTime()) / unitMs);

    const x = (diffStartUnits / step) * columnWidth;
    const width = (durationUnits / step) * columnWidth;

    return {
      x: Math.max(0, x),
      width,
    };
  }

  /**
   * Build assignment buckets from assignmentMap
   * Groups assignments by pekerjaan with date ranges and percentages
   * @private
   * @returns {Map} Bucket map (pekerjaanId → bucket)
   */
  _buildModeBuckets() {
    return {
      planned: this._buildAssignmentBucketsFromMap(this._getCellsForMode('planned')),
      actual: this._buildAssignmentBucketsFromMap(this._getCellsForMode('actual')),
    };
  }

  _getCellsForMode(mode) {
    const manager = this.state?.stateManager;
    if (manager && typeof manager.getAllCellsForMode === 'function') {
      try {
        const merged = manager.getAllCellsForMode(mode);
        return merged instanceof Map ? merged : new Map(merged || []);
      } catch (error) {
        console.warn(`${LOG_PREFIX} Failed to read cells for mode ${mode}:`, error);
      }
    }

    if (mode === (this.state.progressMode || 'planned')) {
      if (this.state.assignmentMap instanceof Map) {
        return this.state.assignmentMap;
      }
      return new Map(Object.entries(this.state.assignmentMap || {}));
    }

    return new Map();
  }

  _buildAssignmentBucketsFromMap(sourceMap) {
    const buckets = new Map();
    const entries = sourceMap instanceof Map ? Array.from(sourceMap.entries()) : Object.entries(sourceMap || {});

    entries.forEach(([rawKey, rawValue]) => {
      const key = String(rawKey);
      const separatorIndex = key.indexOf('-');
      if (separatorIndex === -1) return;

      const pekerjaanId = key.slice(0, separatorIndex);
      const colId = key.slice(separatorIndex + 1);
      if (!pekerjaanId || !colId) return;

      const columnInfo = this.columnLookup.get(colId);
      if (!columnInfo) return;

      const percent = parseFloat(rawValue);
      if (!Number.isFinite(percent) || percent <= 0) return;

      const bucket = buckets.get(pekerjaanId) || {
        totalPercent: 0,
        start: null,
        end: null,
        segments: [],
        hasData: false,
      };

      bucket.hasData = true;
      bucket.totalPercent += percent;
      if (!bucket.start || columnInfo.startDate < bucket.start) {
        bucket.start = columnInfo.startDate;
      }
      if (!bucket.end || columnInfo.endDate > bucket.end) {
        bucket.end = columnInfo.endDate;
      }
      bucket.segments.push({
        label: columnInfo.label || columnInfo.rangeLabel || '',
        rangeLabel: columnInfo.rangeLabel || '',
        start: columnInfo.startDate,
        end: columnInfo.endDate,
        percent,
      });

      buckets.set(pekerjaanId, bucket);
    });

    return buckets;
  }

  // =========================================================================
  // PRIVATE METHODS - Gantt Setup
  // =========================================================================

  /**
   * Create Frappe Gantt instance
   * @private
   */
  _createGanttInstance() {
    if (!this.container) {
      console.error(`${LOG_PREFIX} Cannot create Gantt: no container`);
      return;
    }

    if (this.tasks.length === 0) {
      console.warn(`${LOG_PREFIX} No tasks to display`);
      this.container.innerHTML = '<div class="text-center text-muted p-4">Tidak ada data untuk ditampilkan</div>';
      return;
    }

    // Clear container
    this.container.innerHTML = '';

    const baseOptions = {
      view_mode: this.options.viewMode,
      date_format: 'YYYY-MM-DD',
      bar_height: this.options.barHeight,
      padding: this.options.barPadding,
      readonly: true,
      show_expected_progress: false,
      custom_popup_html: (task) => this._buildPopupHtml(task),
      on_click: (task) => this._handleTaskClick(task),
      on_date_change: (task, start, end) => this._handleDateChange(task, start, end),
      on_progress_change: (task, progress) => this._handleProgressChange(task, progress),
      on_view_change: (mode) => this._handleViewChange(mode),
    };

    const languagesToTry = Array.from(new Set([
      this.options.language || 'id-ID',
      'en',
    ]));

    let created = false;
    let lastError = null;

    for (const lang of languagesToTry) {
      try {
        const options = { ...baseOptions, language: lang };
        this.ganttInstance = new window.Gantt(this.container, this.tasks, options);
        this.options.language = lang;
        this._afterRender();
        console.log(`${LOG_PREFIX} Gantt instance created (language=${lang})`);
        created = true;
        break;
      } catch (error) {
        lastError = error;
        console.error(`${LOG_PREFIX} Failed to create Gantt instance (language=${lang}):`, error);
      }
    }

    if (!created && lastError) {
      console.error(`${LOG_PREFIX} Unable to create Gantt after trying fallback languages`, lastError);
      this.container.innerHTML = '<div class="text-center text-danger p-4">Gagal memuat Gantt chart</div>';
    }
  }

  /**
   * Build custom popup HTML for task
   * @private
   * @param {Object} task - Frappe Gantt task
   * @returns {string} HTML string
   */
  _buildPopupHtml(task) {
    const meta = task.metadata || {};
    const title = escapeHtml(meta.label || task.name || 'Pekerjaan');
    const progressValue = Number(task.progress) || 0;
    const progressLabel = `${progressValue.toFixed(progressValue % 1 === 0 ? 0 : 1)}%`;
    const startLabel = escapeHtml(meta.start || task.start || '');
    const endLabel = escapeHtml(meta.end || task.end || '');
    const actualRange = meta.actualRange || null;
    const actualStartLabel = actualRange?.startISO ? escapeHtml(actualRange.startISO) : null;
    const actualEndLabel = actualRange?.endISO ? escapeHtml(actualRange.endISO) : null;

    const segments = Array.isArray(meta.segments) ? meta.segments : [];
    const segmentsHtml = segments.length
      ? `<ul class="gantt-popup-segments">${segments.map((detail) => {
          const percentLabel = Number.isFinite(detail.percent)
            ? `${detail.percent.toFixed(detail.percent % 1 === 0 ? 0 : 1)}%`
            : '';
          const label = detail.label || `${detail.start} - ${detail.end}`;
          return `<li><span class="gantt-popup-segment-label">${escapeHtml(label)}</span>${percentLabel ? `<span class="gantt-popup-segment-percent">${percentLabel}</span>` : ''}</li>`;
        }).join('')}</ul>`
      : '<p class="mb-0 text-muted"><em>Belum ada distribusi progres</em></p>';

    return `
      <div class="gantt-popup">
        <h5>${title}</h5>
        <div class="gantt-popup-section">
          <strong>Periode:</strong> ${startLabel} s/d ${endLabel}
        </div>
        ${actualRange ? `
        <div class="gantt-popup-section">
          <strong>Realisasi:</strong> ${actualStartLabel || '-'} s/d ${actualEndLabel || '-'}
        </div>` : ''}
        <div class="gantt-popup-section">
          <strong>Progress:</strong> ${progressLabel}
        </div>
        <div class="gantt-popup-section">
          <strong>Distribusi:</strong>
          ${segmentsHtml}
        </div>
      </div>
    `;
  }

  // =========================================================================
  // PRIVATE METHODS - Event Handlers
  // =========================================================================

  /**
   * Handle task click event
   * @private
   * @param {Object} task - Clicked task
   */
  _handleTaskClick(task) {
    console.log(`${LOG_PREFIX} Task clicked:`, task.id);

    // Extract pekerjaan ID
    let pekerjaanId = null;
    if (task.id) {
      const match = String(task.id).match(/^pekerjaan-(.+)$/);
      if (match) {
        pekerjaanId = match[1];
      }
    }

    // Emit event if event system exists
    if (window.KelolaTahapanPage && window.KelolaTahapanPage.events && typeof window.KelolaTahapanPage.events.emit === 'function') {
      window.KelolaTahapanPage.events.emit('gantt:select', {
        pekerjaanId,
        task,
        state: this.state,
      });
    }

    // Call custom click handler if provided
    if (typeof this.options.onClick === 'function') {
      this.options.onClick(task, pekerjaanId);
    }
  }

  /**
   * Handle date change event (drag task)
   * @private
   * @param {Object} task - Changed task
   * @param {Date} start - New start date
   * @param {Date} end - New end date
   */
  _handleDateChange(task, start, end) {
    console.log(`${LOG_PREFIX} Date changed for task ${task.id}:`, { start, end });

    // Call custom handler if provided
    if (typeof this.options.onDateChange === 'function') {
      this.options.onDateChange(task, start, end);
    }
  }

  /**
   * Handle progress change event (drag progress bar)
   * @private
   * @param {Object} task - Changed task
   * @param {number} progress - New progress value
   */
  _handleProgressChange(task, progress) {
    console.log(`${LOG_PREFIX} Progress changed for task ${task.id}:`, progress);

    // Call custom handler if provided
    if (typeof this.options.onProgressChange === 'function') {
      this.options.onProgressChange(task, progress);
    }
  }

  /**
   * Handle view mode change event
   * @private
   * @param {string} mode - New view mode
   */
  _handleViewChange(mode) {
    const normalized = normalizeViewMode(mode);
    this.options.viewMode = normalized;

    // Update state cache
    if (this.state) {
      this.state.cache = this.state.cache || {};
      this.state.cache.ganttViewMode = normalized;
    }

    console.log(`${LOG_PREFIX} View changed to: ${normalized}`);

    // Call custom handler if provided
    if (typeof this.options.onViewChange === 'function') {
      this.options.onViewChange(normalized);
    }
  }

  // =========================================================================
  // PRIVATE METHODS - Observers
  // =========================================================================

  /**
   * Setup theme observer for auto-refresh on theme change
   * @private
   */
  _setupThemeObserver() {
    this.themeObserver = setupThemeObserver((theme) => {
      console.log(`${LOG_PREFIX} Theme changed to ${theme}, refreshing chart...`);

      // Refresh chart with current tasks
      if (this.ganttInstance && typeof this.ganttInstance.refresh === 'function') {
        try {
          this.ganttInstance.refresh(this.tasks);
          this.ganttInstance.change_view_mode(this.options.viewMode);
        } catch (error) {
          console.warn(`${LOG_PREFIX} Failed to refresh on theme change:`, error);
        }
      }
    });
  }

  /**
   * Setup resize handler for responsive updates
   * @private
   */
  _setupResizeHandler() {
    let resizeTimeout = null;

    this.resizeHandler = () => {
      if (resizeTimeout) {
        clearTimeout(resizeTimeout);
      }

      resizeTimeout = setTimeout(() => {
        console.log(`${LOG_PREFIX} Window resized, refreshing chart...`);

        if (this.ganttInstance && typeof this.ganttInstance.refresh === 'function') {
          try {
            this.ganttInstance.refresh(this.tasks);
            this.ganttInstance.change_view_mode(this.options.viewMode);
          } catch (error) {
            console.warn(`${LOG_PREFIX} Failed to refresh on resize:`, error);
          }
        }

        resizeTimeout = null;
      }, 150); // 150ms debounce
    };

    window.addEventListener('resize', this.resizeHandler);
  }

  // =========================================================================
  // PUBLIC GETTERS
  // =========================================================================

  /**
   * Get current tasks
   * @returns {Array} Current tasks array
   */
  getTasks() {
    return this.tasks;
  }

  /**
   * Get current view mode
   * @returns {string} Current view mode
   */
  getViewMode() {
    return this.options.viewMode;
  }

  /**
   * Check if Gantt is initialized
   * @returns {boolean} Initialization status
   */
  isInitialized() {
    return this.ganttInstance !== null;
  }

  /**
   * Get flattened hierarchy for tree panel
   * @returns {Array}
   */
  getHierarchy() {
    if (!Array.isArray(this.lastHierarchy)) {
      return [];
    }
    return this.lastHierarchy.map((row) => ({
      ...row,
      pathParts: Array.isArray(row.pathParts) ? [...row.pathParts] : [],
    }));
  }

  /**
   * Get summary rows (planned vs actual)
   * @returns {Array}
   */
  getSummaryRows() {
    if (!Array.isArray(this.summaryRows)) {
      return [];
    }
    return this.summaryRows.map((row) => ({
      ...row,
      planned: { ...row.planned },
      actual: { ...row.actual },
    }));
  }

  /**
   * Get visual row height for syncing tree panel
   * @returns {number}
   */
  getRowHeight() {
    if (this.rowVisualHeight) {
      return this.rowVisualHeight;
    }
    if (this.ganttInstance?.options) {
      return (this.ganttInstance.options.bar_height || 30) + (this.ganttInstance.options.padding || 18);
    }
    return 46;
  }

  /**
   * Get summary rows for external UI rendering
   * @param {number|null} limit - Optional limit (null means all)
   * @returns {Array} Summary rows (cloned)
   */
  getSummaryRows(limit = null) {
    if (!Array.isArray(this.summaryRows) || this.summaryRows.length === 0) {
      return [];
    }

    const rows = Number.isFinite(limit) && limit > 0
      ? this.summaryRows.slice(0, limit)
      : this.summaryRows.slice();

    return rows.map((row) => ({ ...row }));
  }

  /**
   * Get aggregate stats for summary rows
   * @returns {Object} {total, complete, inProgress, notStarted}
   */
  getSummaryStats() {
    const stats = {
      total: 0,
      complete: 0,
      inProgress: 0,
      notStarted: 0,
    };

    if (!Array.isArray(this.summaryRows)) {
      return stats;
    }

    stats.total = this.summaryRows.length;
    this.summaryRows.forEach((row) => {
      if (!row || !row.status) return;
      if (row.status === STATUS_KEYS.COMPLETE) {
        stats.complete += 1;
      } else if (row.status === STATUS_KEYS.IN_PROGRESS) {
        stats.inProgress += 1;
      } else {
        stats.notStarted += 1;
      }
    });

    return stats;
  }

  /**
   * Get metadata for summary (counts)
   * @returns {Object}
   */
  getSummaryOverview() {
    return this.getSummaryStats();
  }
}

// =========================================================================
// FACTORY FUNCTION
// =========================================================================

/**
 * Create and initialize a GanttChart instance
 *
 * @param {Object} state - Application state
 * @param {HTMLElement|string} container - Container element or ID
 * @param {Object} options - Configuration options
 * @returns {GanttChart|null} GanttChart instance or null on error
 */
export function createGanttChart(state, container, options = {}) {
  if (!state || typeof state !== 'object') {
    console.error(`${LOG_PREFIX} Invalid state object`);
    return null;
  }

  const chart = new GanttChart(state, options);
  const success = chart.initialize(container);

  if (!success) {
    console.error(`${LOG_PREFIX} Failed to initialize chart`);
    return null;
  }

  return chart;
}

// =========================================================================
// EXPORTS
// =========================================================================

export default {
  GanttChart,
  createGanttChart,
  VIEW_MODES,
  DEFAULT_VIEW_MODE,
  TASK_CLASSES,
};
