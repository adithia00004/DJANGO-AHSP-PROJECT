/**
 * Chart Exporter - Export charts as high-resolution images
 *
 * Provides utilities for capturing HTML5 canvas charts and converting
 * them to PNG data URLs for export and embedding in documents.
 *
 * @module ChartExporter
 */

import { createLogger } from './logger.js';

const logger = createLogger('ChartExporter');

/**
 * ChartExporter class
 */
export class ChartExporter {
  /**
   * Export canvas element to PNG data URL
   *
   * Creates a high-resolution copy of the canvas for print quality.
   *
   * @param {HTMLCanvasElement} canvas - Source canvas element
   * @param {Object} options - Export options
   * @param {number} [options.scale=2] - DPI scale (2x for high-res, 300 DPI equivalent)
   * @param {string} [options.backgroundColor='#ffffff'] - Background color
   * @param {number} [options.width] - Override width (uses canvas width if not specified)
   * @param {number} [options.height] - Override height (uses canvas height if not specified)
   * @returns {Promise<string>} Data URL (data:image/png;base64,...)
   *
   * @example
   * const canvas = document.getElementById('myChart');
   * const dataURL = await ChartExporter.exportCanvasToPNG(canvas, {scale: 2});
   * // dataURL: "data:image/png;base64,iVBORw0KGgo..."
   */
  static async exportCanvasToPNG(canvas, options = {}) {
    const {
      scale = 2,
      backgroundColor = '#ffffff',
      width = null,
      height = null
    } = options;

    if (!canvas || !(canvas instanceof HTMLCanvasElement)) {
      throw new Error('Invalid canvas element');
    }

    logger.time('canvas-export');

    try {
      // Create temporary canvas with higher resolution
      const tempCanvas = document.createElement('canvas');
      const ctx = tempCanvas.getContext('2d');

      // Calculate dimensions
      const sourceWidth = width || canvas.width;
      const sourceHeight = height || canvas.height;

      tempCanvas.width = sourceWidth * scale;
      tempCanvas.height = sourceHeight * scale;

      logger.debug(`Exporting canvas: ${tempCanvas.width}x${tempCanvas.height}px (${scale}x scale)`);

      // Fill background
      ctx.fillStyle = backgroundColor;
      ctx.fillRect(0, 0, tempCanvas.width, tempCanvas.height);

      // Enable high-quality rendering
      ctx.imageSmoothingEnabled = true;
      ctx.imageSmoothingQuality = 'high';

      // Scale context
      ctx.scale(scale, scale);

      // Draw source canvas
      ctx.drawImage(canvas, 0, 0, sourceWidth, sourceHeight);

      // Convert to data URL
      const dataURL = tempCanvas.toDataURL('image/png');

      logger.timeEnd('canvas-export');
      logger.info(`Canvas exported: ${(dataURL.length / 1024).toFixed(2)} KB`);

      return dataURL;

    } catch (error) {
      logger.error('Failed to export canvas', error);
      throw error;
    }
  }

  /**
   * Export Gantt chart to PNG
   *
   * Captures the Gantt chart canvas with bar overlays.
   *
   * @param {Object} ganttChart - GanttChartRedesign instance
   * @param {Object} options - Export options
   * @returns {Promise<string>} Data URL
   *
   * @example
   * const ganttChart = app.ganttChart;
   * const dataURL = await ChartExporter.exportGanttChart(ganttChart);
   */
  static async exportGanttChart(ganttChart, options = {}) {
    if (!ganttChart) {
      throw new Error('Gantt chart instance not provided');
    }

    // Get canvas from Gantt overlay
    const canvas = ganttChart.overlay?.canvas;

    if (!canvas) {
      throw new Error('Gantt chart canvas not found. Is the chart rendered?');
    }

    logger.info('Exporting Gantt chart');

    return this.exportCanvasToPNG(canvas, {
      ...options,
      backgroundColor: options.backgroundColor || '#ffffff'
    });
  }

  /**
   * Export Kurva S chart to PNG
   *
   * Captures the Kurva S (S-Curve) chart canvas from uPlot.
   *
   * @param {Object} kurvaSChart - KurvaSUPlotChart instance
   * @param {Object} options - Export options
   * @returns {Promise<string>} Data URL
   *
   * @example
   * const kurvaSChart = app.kurvaSChart;
   * const dataURL = await ChartExporter.exportKurvaSChart(kurvaSChart);
   */
  static async exportKurvaSChart(kurvaSChart, options = {}) {
    if (!kurvaSChart) {
      throw new Error('Kurva S chart instance not provided');
    }

    // uPlot stores canvas in chartInstance.ctx.canvas
    const canvas = kurvaSChart.chartInstance?.ctx?.canvas ||
                   kurvaSChart.chartInstance?.root?.querySelector('canvas');

    if (!canvas) {
      throw new Error('Kurva S chart canvas not found. Is the chart rendered?');
    }

    logger.info('Exporting Kurva S chart');

    return this.exportCanvasToPNG(canvas, {
      ...options,
      backgroundColor: options.backgroundColor || '#ffffff'
    });
  }

  /**
   * Export DOM element to PNG using html2canvas
   *
   * For non-canvas elements (SVG, DOM), use html2canvas library.
   * Note: html2canvas must be loaded separately.
   *
   * @param {HTMLElement} element - DOM element to capture
   * @param {Object} options - Export options
   * @returns {Promise<string>} Data URL
   *
   * @example
   * const chartContainer = document.getElementById('chartDiv');
   * const dataURL = await ChartExporter.exportDOMToPNG(chartContainer);
   */
  static async exportDOMToPNG(element, options = {}) {
    if (!element || !(element instanceof HTMLElement)) {
      throw new Error('Invalid DOM element');
    }

    // Check if html2canvas is available
    if (typeof html2canvas === 'undefined') {
      throw new Error('html2canvas library not loaded. Include it in your HTML.');
    }

    logger.time('dom-export');
    logger.info('Exporting DOM element to PNG');

    try {
      const canvas = await html2canvas(element, {
        scale: options.scale || 2,
        backgroundColor: options.backgroundColor || '#ffffff',
        logging: false,
        useCORS: true,
        allowTaint: false
      });

      const dataURL = canvas.toDataURL('image/png');

      logger.timeEnd('dom-export');
      logger.info(`DOM exported: ${(dataURL.length / 1024).toFixed(2)} KB`);

      return dataURL;

    } catch (error) {
      logger.error('Failed to export DOM element', error);
      throw error;
    }
  }

  /**
   * Download data URL as file
   *
   * Triggers browser download for a data URL.
   *
   * @param {string} dataURL - Data URL (e.g., from exportCanvasToPNG)
   * @param {string} filename - Download filename
   *
   * @example
   * const dataURL = await ChartExporter.exportGanttChart(ganttChart);
   * ChartExporter.downloadDataURL(dataURL, 'gantt-chart.png');
   */
  static downloadDataURL(dataURL, filename = 'chart.png') {
    const link = document.createElement('a');
    link.href = dataURL;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    logger.info(`Downloaded: ${filename}`);
  }

  /**
   * Convert data URL to Blob
   *
   * Useful for sending via fetch/xhr.
   *
   * @param {string} dataURL - Data URL
   * @returns {Blob} Blob object
   *
   * @example
   * const dataURL = await ChartExporter.exportGanttChart(ganttChart);
   * const blob = ChartExporter.dataURLToBlob(dataURL);
   * // Upload blob to server
   */
  static dataURLToBlob(dataURL) {
    const parts = dataURL.split(';base64,');
    const contentType = parts[0].split(':')[1];
    const base64 = parts[1];

    const binary = atob(base64);
    const array = [];

    for (let i = 0; i < binary.length; i++) {
      array.push(binary.charCodeAt(i));
    }

    return new Blob([new Uint8Array(array)], { type: contentType });
  }

  /**
   * Get image dimensions from data URL
   *
   * Returns the actual pixel dimensions of the exported image.
   *
   * @param {string} dataURL - Data URL
   * @returns {Promise<Object>} {width, height}
   *
   * @example
   * const dataURL = await ChartExporter.exportGanttChart(ganttChart);
   * const {width, height} = await ChartExporter.getImageDimensions(dataURL);
   * console.log(`Exported image: ${width}x${height}px`);
   */
  static async getImageDimensions(dataURL) {
    return new Promise((resolve, reject) => {
      const img = new Image();

      img.onload = () => {
        resolve({
          width: img.width,
          height: img.height
        });
      };

      img.onerror = () => {
        reject(new Error('Failed to load image from data URL'));
      };

      img.src = dataURL;
    });
  }

  /**
   * Estimate file size from data URL
   *
   * Returns estimated file size in bytes.
   *
   * @param {string} dataURL - Data URL
   * @returns {number} File size in bytes
   *
   * @example
   * const dataURL = await ChartExporter.exportGanttChart(ganttChart);
   * const sizeKB = ChartExporter.estimateFileSize(dataURL) / 1024;
   * console.log(`File size: ${sizeKB.toFixed(2)} KB`);
   */
  static estimateFileSize(dataURL) {
    // Base64 encoding adds ~33% overhead
    // data:image/png;base64, is ~22 chars
    const base64Length = dataURL.split(',')[1].length;
    return Math.ceil(base64Length * 0.75); // Approximate actual bytes
  }
}

/**
 * Export multiple charts in batch
 *
 * Convenience function to export multiple charts at once.
 *
 * @param {Object} charts - Object with chart instances
 *   {gantt: ganttChart, kurvaS: kurvaSChart}
 * @param {Object} options - Export options
 * @returns {Promise<Object>} Object with data URLs
 *   {gantt: dataURL, kurvaS: dataURL}
 *
 * @example
 * const exported = await exportMultipleCharts({
 *   gantt: app.ganttChart,
 *   kurvaS: app.kurvaSChart
 * });
 * console.log(exported.gantt); // data URL for Gantt
 * console.log(exported.kurvaS); // data URL for Kurva S
 */
export async function exportMultipleCharts(charts, options = {}) {
  const exported = {};

  logger.info('Exporting multiple charts', Object.keys(charts));

  if (charts.gantt) {
    try {
      exported.gantt = await ChartExporter.exportGanttChart(charts.gantt, options);
    } catch (error) {
      logger.error('Failed to export Gantt chart', error);
      exported.gantt = null;
    }
  }

  if (charts.kurvaS) {
    try {
      exported.kurvaS = await ChartExporter.exportKurvaSChart(charts.kurvaS, options);
    } catch (error) {
      logger.error('Failed to export Kurva S chart', error);
      exported.kurvaS = null;
    }
  }

  return exported;
}

export default ChartExporter;
