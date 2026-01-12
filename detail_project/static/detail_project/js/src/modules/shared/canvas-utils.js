/**
 * Canvas Utilities for Kurva S
 * Shared canvas creation and configuration utilities
 *
 * @module modules/kurva-s/canvas-utils
 */

/**
 * Creates a canvas element with standard configuration
 * @param {string} className - CSS class name for the canvas
 * @returns {HTMLCanvasElement} Configured canvas element
 */
export function createCanvas(className = 'kurva-s-canvas') {
  const canvas = document.createElement('canvas');
  canvas.className = className;
  canvas.style.cssText = `
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: auto;
    background: transparent;
  `;
  return canvas;
}

/**
 * Creates a clip viewport wrapper for canvas
 * ClipViewport is a fixed overlay that clips canvas to visible area
 *
 * @param {string} className - CSS class name for the viewport
 * @param {number} zIndex - Z-index for stacking (default: 10)
 * @returns {HTMLDivElement} Configured clip viewport element
 */
export function createClipViewport(className = 'kurva-s-clip-viewport', zIndex = 10) {
  const clipViewport = document.createElement('div');
  clipViewport.className = className;
  clipViewport.style.cssText = `
    position: absolute;
    overflow: hidden;
    pointer-events: auto;
    z-index: ${zIndex};
  `;
  return clipViewport;
}

/**
 * Gets 2D rendering context from canvas
 * @param {HTMLCanvasElement} canvas - Canvas element
 * @returns {CanvasRenderingContext2D} 2D rendering context
 */
export function getContext2D(canvas) {
  return canvas.getContext('2d');
}

/**
 * Hit test to find closest point within radius
 * @param {Array<{x, y}>} points - Array of points with x,y coordinates
 * @param {number} x - Test X coordinate
 * @param {number} y - Test Y coordinate
 * @param {number} radius - Hit test radius in pixels
 * @returns {Object|null} Closest point within radius, or null
 */
export function hitTestPoint(points, x, y, radius) {
  if (!points || points.length === 0) return null;

  for (const point of points) {
    const dx = point.x - x;
    const dy = point.y - y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    if (distance <= radius) {
      return point;
    }
  }
  return null;
}

/**
 * Detects if dark mode is active
 * Checks both data-bs-theme attribute and prefers-color-scheme
 *
 * @returns {boolean} True if dark mode is active
 */
export function isDarkMode() {
  const htmlTheme = document.documentElement.getAttribute('data-bs-theme');
  if (htmlTheme) {
    return htmlTheme === 'dark';
  }
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
}

/**
 * Get CSS variable value from document root
 * @param {string} name - CSS variable name (e.g., '--bs-primary')
 * @returns {string|null} Trimmed value or null if not found
 */
export function getCssVar(name) {
  try {
    const root = document.documentElement;
    const value = getComputedStyle(root).getPropertyValue(name);
    return value && value.trim().length ? value.trim() : null;
  } catch (e) {
    return null;
  }
}

/**
 * Get color from a button element by selector
 * @param {string} selector - CSS selector for button element
 * @returns {string|null} Color value or null if not found
 */
export function getBtnColor(selector) {
  try {
    const el = document.querySelector(selector);
    if (!el) return null;
    const style = getComputedStyle(el);
    return style.getPropertyValue('background-color')?.trim() ||
      style.getPropertyValue('border-color')?.trim() ||
      style.getPropertyValue('color')?.trim() ||
      null;
  } catch (e) {
    return null;
  }
}

