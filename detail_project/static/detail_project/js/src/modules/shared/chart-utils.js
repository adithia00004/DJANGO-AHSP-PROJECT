/**
 * Chart Utilities Module
 * Shared utilities for Kurva-S and Gantt charts
 *
 * Migrated from legacy chart modules
 * Date: 2025-11-20
 */

// =========================================================================
// CONSTANTS
// =========================================================================

export const ONE_DAY_MS = 24 * 60 * 60 * 1000;

// =========================================================================
// THEME UTILITIES
// =========================================================================

/**
 * Get theme-specific colors for charts
 * Supports Bootstrap dark/light theme
 *
 * @returns {Object} Theme colors
 */
export function getThemeColors() {
  const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';

  if (theme === 'dark') {
    return {
      text: '#f8fafc',
      axis: '#cbd5e1',
      plannedLine: '#60a5fa',
      plannedArea: 'rgba(96, 165, 250, 0.15)',
      actualLine: '#34d399',
      actualArea: 'rgba(52, 211, 153, 0.18)',
      gridLine: '#334155',
      background: '#1e293b',
    };
  }

  return {
    text: '#1f2937',
    axis: '#374151',
    plannedLine: '#0d6efd',
    plannedArea: 'rgba(13, 110, 253, 0.12)',
    actualLine: '#198754',
    actualArea: 'rgba(25, 135, 84, 0.12)',
    gridLine: '#e5e7eb',
    background: '#ffffff',
  };
}

/**
 * Setup theme observer for chart updates
 * Watches for data-bs-theme attribute changes
 *
 * @param {Function} callback - Called when theme changes
 * @returns {MutationObserver} Observer instance
 */
export function setupThemeObserver(callback) {
  const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
      if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
        const theme = document.documentElement.getAttribute('data-bs-theme');
        console.log('[ChartUtils] Theme changed to:', theme);
        callback(theme);
      }
    });
  });

  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ['data-bs-theme']
  });

  return observer;
}

// =========================================================================
// DATE UTILITIES
// =========================================================================

/**
 * Normalize date to Date object
 * Handles multiple input formats: Date, ISO string, timestamp
 *
 * @param {Date|string|number} input - Date input
 * @returns {Date|null} Normalized date or null if invalid
 */
export function normalizeDate(input) {
  if (!input) return null;

  // Already a Date object
  if (input instanceof Date) {
    return Number.isNaN(input.getTime()) ? null : input;
  }

  // ISO string or other string format
  if (typeof input === 'string') {
    const date = new Date(input);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  // Timestamp
  if (typeof input === 'number' && Number.isFinite(input)) {
    const date = new Date(input);
    return Number.isNaN(date.getTime()) ? null : date;
  }

  return null;
}

/**
 * Format date to YYYY-MM-DD string
 *
 * @param {Date} date - Date to format
 * @returns {string} Formatted date string
 */
export function formatDate(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return '';
  }

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');

  return `${year}-${month}-${day}`;
}

/**
 * Calculate date range from time columns
 *
 * @param {Array} columns - Array of time column objects
 * @returns {Object} {startDate, endDate}
 */
export function calculateDateRange(columns) {
  if (!Array.isArray(columns) || columns.length === 0) {
    return { startDate: null, endDate: null };
  }

  let minDate = null;
  let maxDate = null;

  columns.forEach(col => {
    const start = normalizeDate(col.startDate);
    const end = normalizeDate(col.endDate);

    if (start && (!minDate || start < minDate)) {
      minDate = start;
    }

    if (end && (!maxDate || end > maxDate)) {
      maxDate = end;
    }
  });

  return { startDate: minDate, endDate: maxDate };
}

/**
 * Get sorted time columns
 * Sorts by startDate, then by index
 *
 * @param {Array} columns - Time columns
 * @returns {Array} Sorted columns
 */
export function getSortedColumns(columns) {
  if (!Array.isArray(columns)) return [];

  return columns.slice().sort((a, b) => {
    const aStart = normalizeDate(a.startDate);
    const bStart = normalizeDate(b.startDate);

    if (aStart && bStart) {
      return aStart.getTime() - bStart.getTime();
    }

    return (a.index || 0) - (b.index || 0);
  });
}

// =========================================================================
// VOLUME UTILITIES
// =========================================================================

/**
 * Build volume lookup map from state
 * Handles both Map and Object formats
 *
 * @param {Object} state - Application state
 * @returns {Map} Volume lookup (pekerjaanId → volume)
 */
export function buildVolumeLookup(state) {
  const lookup = new Map();

  const setVolume = (key, value) => {
    const numericKey = Number(key);
    const volume = Number.isFinite(value) && value > 0 ? value : null;

    if (volume === null) return;

    // Store both string and numeric keys for flexible lookup
    lookup.set(String(key), volume);
    if (!Number.isNaN(numericKey)) {
      lookup.set(String(numericKey), volume);
    }
  };

  // Handle Map format
  if (state.volumeMap instanceof Map) {
    state.volumeMap.forEach((value, key) => {
      const vol = parseFloat(value);
      setVolume(key, vol);
    });
  }
  // Handle Object format
  else if (state.volumeMap && typeof state.volumeMap === 'object') {
    Object.entries(state.volumeMap).forEach(([key, value]) => {
      const vol = parseFloat(value);
      setVolume(key, vol);
    });
  }

  return lookup;
}

/**
 * Get volume for a specific pekerjaan
 *
 * @param {Map} volumeLookup - Volume lookup map
 * @param {string|number} pekerjaanId - Pekerjaan ID
 * @param {number} fallback - Fallback value if not found
 * @returns {number} Volume value
 */
export function getVolumeForPekerjaan(volumeLookup, pekerjaanId, fallback = 1) {
  const idVariants = [
    String(pekerjaanId),
    String(Number(pekerjaanId)),
  ];

  for (const variant of idVariants) {
    if (volumeLookup.has(variant)) {
      return volumeLookup.get(variant);
    }
  }

  return fallback;
}

/**
 * Build harga (cost) lookup map from state
 * Phase 2F.0: Kurva S should use HARGA (Rupiah) instead of volume
 *
 * @param {Object} state - Application state
 * @returns {Map} Harga lookup map (pekerjaanId → total harga in Rp)
 */
export function buildHargaLookup(state) {
  const lookup = new Map();

  const setHarga = (key, value) => {
    const numericKey = Number(key);
    const harga = Number.isFinite(value) && value >= 0 ? value : null;

    if (harga === null) return;

    // Store both string and numeric keys for flexible lookup
    lookup.set(String(key), harga);
    if (!Number.isNaN(numericKey)) {
      lookup.set(String(numericKey), harga);
    }
  };

  // Handle Map format
  if (state.hargaMap instanceof Map) {
    state.hargaMap.forEach((value, key) => {
      const harga = parseFloat(value);
      setHarga(key, harga);
    });
  }
  // Handle Object format
  else if (state.hargaMap && typeof state.hargaMap === 'object') {
    Object.entries(state.hargaMap).forEach(([key, value]) => {
      const harga = parseFloat(value);
      setHarga(key, harga);
    });
  }

  return lookup;
}

/**
 * Get harga for a specific pekerjaan
 * Phase 2F.0: Used for harga-weighted Kurva S calculation
 *
 * @param {Map} hargaLookup - Harga lookup map
 * @param {string|number} pekerjaanId - Pekerjaan ID
 * @param {number} fallback - Fallback value if not found (default: 0)
 * @returns {number} Total harga (Rp) for the pekerjaan
 */
export function getHargaForPekerjaan(hargaLookup, pekerjaanId, fallback = 0) {
  const idVariants = [
    String(pekerjaanId),
    String(Number(pekerjaanId)),
  ];

  for (const variant of idVariants) {
    if (hargaLookup.has(variant)) {
      return hargaLookup.get(variant);
    }
  }

  return fallback;
}

// =========================================================================
// DATA UTILITIES
// =========================================================================

/**
 * Build cell value map from assignmentMap and modifiedCells
 * Modified cells override assignment values
 *
 * @param {Object} state - Application state
 * @returns {Map} Cell value map (cellKey → percentage)
 */
export function buildCellValueMap(state) {
  const map = new Map();

  const assignValue = (key, value) => {
    const numeric = parseFloat(value);
    map.set(String(key), Number.isFinite(numeric) ? numeric : 0);
  };

  // First, load saved assignment values
  if (state.assignmentMap instanceof Map) {
    state.assignmentMap.forEach((value, key) => assignValue(key, value));
  } else if (state.assignmentMap && typeof state.assignmentMap === 'object') {
    Object.entries(state.assignmentMap).forEach(([key, value]) => assignValue(key, value));
  }

  // Then, override with modified cells (unsaved changes)
  if (state.modifiedCells instanceof Map) {
    state.modifiedCells.forEach((value, key) => assignValue(key, value));
  } else if (state.modifiedCells && typeof state.modifiedCells === 'object') {
    Object.entries(state.modifiedCells).forEach(([key, value]) => assignValue(key, value));
  }

  return map;
}

/**
 * Collect all pekerjaan IDs from state and cell values
 *
 * @param {Object} state - Application state
 * @param {Map} cellValues - Cell value map
 * @returns {Set} Set of pekerjaan IDs
 */
export function collectPekerjaanIds(state, cellValues) {
  const ids = new Set();

  // From flatPekerjaan array
  if (Array.isArray(state.flatPekerjaan)) {
    state.flatPekerjaan.forEach((node) => {
      if (node && (node.type === 'pekerjaan' || typeof node.type === 'undefined')) {
        ids.add(String(node.id));
      }
    });
  }

  // From cell keys (format: "pekerjaanId-tahapanId")
  cellValues.forEach((_, key) => {
    const [pekerjaanId] = String(key).split('-');
    if (pekerjaanId) {
      ids.add(pekerjaanId);
    }
  });

  return ids;
}

// =========================================================================
// NUMBER UTILITIES
// =========================================================================

/**
 * Format percentage for display
 *
 * @param {number} value - Percentage value (0-100)
 * @param {number} decimals - Number of decimal places
 * @returns {string} Formatted percentage
 */
export function formatPercentage(value, decimals = 1) {
  if (!Number.isFinite(value)) return '0%';

  const rounded = decimals === 0
    ? Math.round(value)
    : parseFloat(value.toFixed(decimals));

  return `${rounded}%`;
}

/**
 * Format number as Indonesian Rupiah
 * Phase 2F.0: Display currency in Kurva S tooltips
 *
 * @param {number} amount - Amount in Rupiah
 * @returns {string} Formatted currency string (e.g., "Rp 1.234.567")
 */
export function formatRupiah(amount) {
  if (!Number.isFinite(amount)) return 'Rp 0';

  // Format with thousand separators (Indonesian style)
  const formatted = Math.round(amount).toLocaleString('id-ID');
  return `Rp ${formatted}`;
}

/**
 * Clamp number between min and max
 *
 * @param {number} value - Value to clamp
 * @param {number} min - Minimum value
 * @param {number} max - Maximum value
 * @returns {number} Clamped value
 */
export function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

// =========================================================================
// RESIZE UTILITIES
// =========================================================================

/**
 * Create debounced resize handler
 *
 * @param {Function} callback - Function to call on resize
 * @param {number} delay - Debounce delay in ms
 * @returns {Function} Debounced handler
 */
export function createResizeHandler(callback, delay = 150) {
  let timeoutId = null;

  return function debouncedResize() {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      callback();
      timeoutId = null;
    }, delay);
  };
}

/**
 * Setup resize observer for chart container
 *
 * @param {HTMLElement} container - Container element
 * @param {Function} callback - Called when container resizes
 * @returns {ResizeObserver} Observer instance
 */
export function setupResizeObserver(container, callback) {
  if (!container || typeof ResizeObserver === 'undefined') {
    return null;
  }

  const observer = new ResizeObserver((entries) => {
    for (const entry of entries) {
      if (entry.target === container) {
        callback(entry.contentRect);
      }
    }
  });

  observer.observe(container);

  return observer;
}

// =========================================================================
// VALIDATION UTILITIES
// =========================================================================

/**
 * Validate chart data
 *
 * @param {Object} data - Chart data
 * @returns {Object} {isValid, errors}
 */
export function validateChartData(data) {
  const errors = [];

  if (!data || typeof data !== 'object') {
    errors.push('Chart data must be an object');
    return { isValid: false, errors };
  }

  if (!Array.isArray(data.xAxis)) {
    errors.push('xAxis must be an array');
  }

  if (!Array.isArray(data.series)) {
    errors.push('series must be an array');
  }

  if (data.xAxis && data.series) {
    data.series.forEach((serie, index) => {
      if (!Array.isArray(serie.data)) {
        errors.push(`Series ${index} data must be an array`);
      } else if (serie.data.length !== data.xAxis.length) {
        errors.push(`Series ${index} length (${serie.data.length}) doesn't match xAxis (${data.xAxis.length})`);
      }
    });
  }

  return {
    isValid: errors.length === 0,
    errors
  };
}

// =========================================================================
// EXPORT ALL
// =========================================================================

export default {
  // Constants
  ONE_DAY_MS,

  // Theme
  getThemeColors,
  setupThemeObserver,

  // Date
  normalizeDate,
  formatDate,
  calculateDateRange,
  getSortedColumns,

  // Volume
  buildVolumeLookup,
  getVolumeForPekerjaan,

  // Harga (Phase 2F.0)
  buildHargaLookup,
  getHargaForPekerjaan,

  // Data
  buildCellValueMap,
  collectPekerjaanIds,

  // Number
  formatPercentage,
  formatRupiah,
  clamp,

  // Resize
  createResizeHandler,
  setupResizeObserver,

  // Validation
  validateChartData,
};
