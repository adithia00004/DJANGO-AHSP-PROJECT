/**
 * Tooltip Manager for Kurva S
 * Manages tooltip creation, display, and positioning
 *
 * @module modules/kurva-s/tooltip-manager
 */

import { isDarkMode } from './canvas-utils.js';

/**
 * TooltipManager class
 * Handles tooltip lifecycle and display for curve points
 */
export class TooltipManager {
  /**
   * @param {Object} options - Configuration options
   * @param {number} [options.zIndex=50] - Z-index for tooltip
   */
  constructor(options = {}) {
    this.tooltip = null;
    this.zIndex = options.zIndex ?? 50;
  }

  /**
   * Ensures tooltip element exists and returns it
   * @returns {HTMLDivElement} Tooltip element
   */
  ensureTooltip() {
    if (this.tooltip) return this.tooltip;

    this.tooltip = document.createElement('div');
    this.tooltip.className = 'kurva-s-tooltip';
    this.tooltip.style.cssText = `
      position: fixed;
      padding: 8px 12px;
      background: rgba(17, 24, 39, 0.95);
      color: #f8fafc;
      border-radius: 6px;
      font-size: 12px;
      pointer-events: none;
      z-index: ${this.zIndex};
      display: none;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
      line-height: 1.5;
    `;
    document.body.appendChild(this.tooltip);
    return this.tooltip;
  }

  /**
   * Shows tooltip at specified position with point data
   * @param {number} clientX - Mouse X position (client coordinates)
   * @param {number} clientY - Mouse Y position (client coordinates)
   * @param {Object} point - Point data
   * @param {string} point.label - Point label (e.g., "Planned", "Actual")
   * @param {string} point.color - Point color
   * @param {number} [point.weekNumber] - Week number
   * @param {string} [point.columnId] - Column ID
   * @param {number} [point.progress] - Cumulative progress (%)
   * @param {number} [point.weekProgress] - Week progress (%)
   */
  show(clientX, clientY, point) {
    const tip = this.ensureTooltip();
    const weekLabel = point.weekNumber ? `Week ${point.weekNumber}` : point.columnId;
    const progressLabel = Number.isFinite(point.progress) ? `${point.progress.toFixed(1)}%` : '-';
    const weekProgressLabel = Number.isFinite(point.weekProgress) ? `${point.weekProgress.toFixed(1)}%` : '-';

    tip.innerHTML = `
      <div style="font-weight: 600; margin-bottom: 4px; color: ${point.color};">${point.label}</div>
      <div><strong>${weekLabel}</strong></div>
      <div>Cumulative: ${progressLabel}</div>
      <div>Week Progress: ${weekProgressLabel}</div>
    `;
    tip.style.left = `${clientX + 12}px`;
    tip.style.top = `${clientY + 12}px`;
    tip.style.display = 'block';
  }

  /**
   * Hides the tooltip
   */
  hide() {
    if (this.tooltip) {
      this.tooltip.style.display = 'none';
    }
  }

  /**
   * Destroys the tooltip element
   */
  destroy() {
    if (this.tooltip) {
      this.tooltip.remove();
      this.tooltip = null;
    }
  }
}

/**
 * Creates a legend element for the chart
 * @param {Object} options - Legend options
 * @param {string} options.plannedColor - Planned curve color
 * @param {string} options.actualColor - Actual curve color
 * @param {number} [options.zIndex=40] - Z-index for legend
 * @returns {HTMLDivElement} Legend element
 */
export function createLegend(options) {
  const { plannedColor, actualColor, zIndex = 40 } = options;
  const darkMode = isDarkMode();

  const legend = document.createElement('div');
  legend.className = 'kurva-s-legend';
  legend.style.cssText = `
    position: absolute;
    top: 10px;
    right: 10px;
    background: ${darkMode ? 'rgba(30, 30, 30, 0.95)' : 'rgba(255, 255, 255, 0.95)'};
    border: 1px solid ${darkMode ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)'};
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    box-shadow: 0 4px 12px rgba(0, 0, 0, ${darkMode ? '0.5' : '0.15'});
    z-index: ${zIndex};
    pointer-events: none;
    display: flex;
    gap: 16px;
    align-items: center;
  `;

  legend.innerHTML = `
    <div style="display: flex; align-items: center; gap: 6px;">
      <span style="display: inline-block; width: 24px; height: 3px; background: ${plannedColor}; border-radius: 2px;"></span>
      <span style="color: ${darkMode ? '#e2e8f0' : '#1e293b'};">Planned</span>
    </div>
    <div style="display: flex; align-items: center; gap: 6px;">
      <span style="display: inline-block; width: 24px; height: 3px; background: ${actualColor}; border-radius: 2px;"></span>
      <span style="color: ${darkMode ? '#e2e8f0' : '#1e293b'};">Actual</span>
    </div>
  `;

  return legend;
}

/**
 * Updates legend colors based on current theme
 * @param {HTMLDivElement} legend - Legend element
 * @param {string} plannedColor - Planned curve color
 * @param {string} actualColor - Actual curve color
 */
export function updateLegendColors(legend, plannedColor, actualColor) {
  if (!legend) return;

  const darkMode = isDarkMode();
  const textColor = darkMode ? '#e2e8f0' : '#1e293b';
  const bgColor = darkMode ? 'rgba(30, 30, 30, 0.95)' : 'rgba(255, 255, 255, 0.95)';
  const borderColor = darkMode ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)';

  // Update legend background and border
  legend.style.background = bgColor;
  legend.style.border = `1px solid ${borderColor}`;
  legend.style.boxShadow = `0 4px 12px rgba(0, 0, 0, ${darkMode ? '0.5' : '0.15'})`;

  // Update legend HTML with new colors
  legend.innerHTML = `
    <div style="display: flex; align-items: center; gap: 6px;">
      <span style="display: inline-block; width: 24px; height: 3px; background: ${plannedColor}; border-radius: 2px;"></span>
      <span style="color: ${textColor};">Planned</span>
    </div>
    <div style="display: flex; align-items: center; gap: 6px;">
      <span style="display: inline-block; width: 24px; height: 3px; background: ${actualColor}; border-radius: 2px;"></span>
      <span style="color: ${textColor};">Actual</span>
    </div>
  `;
}
