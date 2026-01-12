/**
 * Export Coordinator - Orchestrates export process for different report types
 *
 * Manages the complete export flow:
 * 1. Capture charts (Gantt, Kurva S)
 * 2. Aggregate data (weekly → monthly if needed)
 * 3. Build payload with attachments
 * 4. Send to backend
 * 5. Download file
 *
 * @module ExportCoordinator
 */

import { ChartExporter } from './chart-exporter.js';
import { aggregateWeeklyToMonthly, sampleMonthlyCumulative } from './data-aggregator.js';
import { createLogger } from './logger.js';

const logger = createLogger('ExportCoordinator');

/**
 * Export Coordinator class
 */
export class ExportCoordinator {
  /**
   * Create export coordinator
   * @param {Object} app - JadwalKegiatanApp instance
   */
  constructor(app) {
    this.app = app;
    this._savedKurvaSData = null;
  }

  /**
   * Switch to a tab and wait for render
   * @private
   * @param {string} tabId - Tab button ID ('gantt-tab' or 'scurve-tab')
   * @returns {Promise<void>}
   */
  async _switchToTab(tabId) {
    const tabButton = document.getElementById(tabId);
    if (!tabButton) {
      throw new Error(`Tab button #${tabId} not found`);
    }

    // Click the tab
    tabButton.click();

    // Wait for tab to render
    await this._wait(500);
  }

  /**
   * Get current active tab ID
   * @private
   * @returns {string|null}
   */
  _getCurrentTab() {
    const activeTab = document.querySelector('#viewTabs .nav-link.active');
    return activeTab ? activeTab.id : null;
  }

  /**
   * Capture canvas from DOM selector
   * @private
   * @param {string} selector - CSS selector for canvas element
   * @param {Object} options - Export options
   * @returns {Promise<string|null>} Data URL or null if not found
   */
  async _captureCanvasFromDOM(selector, options = {}) {
    const canvas = document.querySelector(selector);

    if (!canvas || !(canvas instanceof HTMLCanvasElement)) {
      logger.warn(`Canvas not found: ${selector}`);
      return null;
    }

    logger.debug(`Capturing canvas: ${selector}`);
    return await ChartExporter.exportCanvasToPNG(canvas, {
      scale: options.scale || 2,
      backgroundColor: options.backgroundColor || '#ffffff'
    });
  }

  /**
   * Capture FULL view (Grid + Chart Overlay) as composite image
   *
   * This captures the entire view including:
   * - Grid table with pekerjaan rows
   * - Chart overlay (Gantt bars or Kurva S lines)
   * - Proper alignment between chart and rows
   *
   * @private
   * @param {string} containerSelector - Container to capture
   * @param {Object} options - Export options
   * @returns {Promise<string|null>} Data URL or null if failed
   */
  async _captureFullView(containerSelector, options = {}) {
    const container = document.querySelector(containerSelector);

    if (!container) {
      logger.warn(`Container not found: ${containerSelector}`);
      return null;
    }

    logger.debug(`Capturing full view: ${containerSelector}`);

    try {
      // Use html2canvas to capture entire container (grid + overlay)
      if (typeof html2canvas === 'undefined') {
        logger.error('html2canvas library not loaded');
        return null;
      }

      const canvas = await html2canvas(container, {
        scale: options.scale || 2,
        backgroundColor: options.backgroundColor || '#ffffff',
        logging: false,
        useCORS: true,
        allowTaint: false,
        scrollX: 0,
        scrollY: -window.scrollY, // Adjust for page scroll
        windowWidth: container.scrollWidth,
        windowHeight: container.scrollHeight
      });

      const dataURL = canvas.toDataURL('image/png');
      logger.info(`Full view captured: ${(dataURL.length / 1024).toFixed(2)} KB`);

      return dataURL;
    } catch (error) {
      logger.error('Failed to capture full view', error);
      return null;
    }
  }

  /**
   * Capture chart with multiple fallback strategies
   * @private
   * @param {string} type - 'gantt' or 'kurvaS'
   * @param {Object} options - Export options
   * @returns {Promise<string|null>} Data URL or null if not found
   */
  async _captureChartWithFallback(type, options = {}) {
    if (type === 'gantt') {
      // Strategy 1: Capture FULL view (Grid + Gantt overlay)
      // This is the primary method to ensure bars align with pekerjaan rows
      const ganttContainer = document.querySelector('#gantt-view');
      if (ganttContainer && ganttContainer.classList.contains('active')) {
        logger.debug('Capturing Gantt FULL view (Grid + Overlay)');
        const fullViewURL = await this._captureFullView('#gantt-redesign-container', options);
        if (fullViewURL) return fullViewURL;
      }

      // Strategy 2: Try canvas overlay only (fallback)
      let canvas = document.querySelector('.gantt-canvas-overlay');
      if (canvas) {
        logger.debug('Capturing Gantt from canvas overlay only');
        return await ChartExporter.exportCanvasToPNG(canvas, options);
      }

      // Strategy 3: Instance fallback
      const ganttInstance = this.app.ganttChart || this.app.ganttFrozenGrid;
      if (ganttInstance?.overlay?.canvas) {
        logger.debug('Capturing Gantt from instance overlay');
        return await ChartExporter.exportGanttChart(ganttInstance, options);
      }

      logger.warn('Gantt chart not available for capture');
      return null;
    }

    if (type === 'kurvaS') {
      // Strategy 1: Capture FULL view (Grid + Kurva S overlay)
      const scurveTab = document.querySelector('#scurve-view');
      if (scurveTab && scurveTab.classList.contains('active')) {
        logger.debug('Capturing Kurva S FULL view (Grid + Overlay)');
        const fullViewURL = await this._captureFullView('#scurve-container', options);
        if (fullViewURL) return fullViewURL;
      }

      // Strategy 2: Canvas overlay (UnifiedTableManager on Grid View)
      let canvas = document.querySelector('.kurva-s-canvas-overlay');
      if (canvas) {
        logger.debug('Capturing Kurva S from canvas overlay');

        // For overlay on grid, capture grid container + overlay together
        const gridContainer = document.querySelector('#tanstack-grid-container');
        if (gridContainer) {
          logger.debug('Capturing Grid + Kurva S overlay composite');
          return await this._captureFullView('#tanstack-grid-section', options);
        }

        return await ChartExporter.exportCanvasToPNG(canvas, options);
      }

      // Strategy 3: uPlot canvas (standalone chart in S-Curve tab)
      const uplotCanvas = document.querySelector('#scurve-chart canvas');
      if (uplotCanvas) {
        logger.debug('Capturing Kurva S from uPlot canvas');
        return await ChartExporter.exportCanvasToPNG(uplotCanvas, options);
      }

      // Strategy 4: Instance fallback
      if (this.app.kurvaSChart?.chartInstance?.ctx?.canvas) {
        logger.debug('Capturing Kurva S from uPlot instance');
        return await ChartExporter.exportKurvaSChart(this.app.kurvaSChart, options);
      }

      logger.warn('Kurva S chart not available for capture');
      return null;
    }

    return null;
  }

  /**
   * Export based on report type
   *
   * Main export entry point. Routes to appropriate handler based on report type.
   *
   * @param {string} reportType - 'full', 'monthly', or 'weekly'
   * @param {string} format - 'pdf', 'word', 'xlsx', or 'csv'
   * @param {Object} options - Additional options
   *   {includeGantt: boolean, includeKurvaS: boolean}
   * @returns {Promise<Blob>} Downloaded file blob
   */
  async export(reportType, format, options = {}) {
    logger.info(`Starting export: ${reportType} (${format})`, options);

    try {
      switch (reportType) {
        case 'full':
          return await this.exportFullReport(format, options);
        case 'monthly':
          return await this.exportMonthlyReport(format, options);
        case 'weekly':
          return await this.exportWeeklyReport(format, options);
        default:
          throw new Error(`Unknown report type: ${reportType}`);
      }
    } catch (error) {
      logger.error(`Export failed: ${reportType} (${format})`, error);
      throw error;
    }
  }

  /**
   * Export A: Rekap Laporan (Full Report)
   *
   * Includes:
   * - A.1: Grid Views Full (Weekly mode, all weeks)
   * - A.2: Gantt Chart Full
   * - A.3: Kurva S Full (Weekly granularity)
   *
   * @param {string} format - Export format
   * @param {Object} options - Export options
   * @returns {Promise<Blob>} File blob
   */
  async exportFullReport(format, options) {
    logger.info('Exporting Full Report (Rekap Laporan)');

    // Remember current tab to restore later
    const originalTab = this._getCurrentTab();
    const attachments = [];

    try {
      // A.2: Gantt Chart Full (Grid + Bars)
      if (options.includeGantt !== false) {
        try {
          logger.debug('Switching to Gantt tab for full capture');
          await this._switchToTab('gantt-tab');

          // Wait longer for full rendering (grid + overlay + data binding)
          await this._wait(1500);

          // Capture FULL Gantt (Grid + Overlay)
          const ganttURL = await this._captureChartWithFallback('gantt', {
            scale: 2,
            backgroundColor: '#ffffff'
          });

          if (ganttURL) {
            attachments.push({
              title: 'A.2 - Gantt Chart Full (Grid + Bars)',
              data_url: ganttURL
            });
            logger.info('✅ Gantt Chart FULL captured successfully (Grid + Bars)');
          } else {
            logger.warn('⚠️ Gantt chart capture failed - chart may not be rendered');
          }
        } catch (error) {
          logger.warn('❌ Failed to capture Gantt Chart', error);
        }
      }

      // A.3: Kurva S Full (Grid + S-Curve)
      if (options.includeKurvaS !== false) {
        try {
          logger.debug('Switching to S-Curve tab for full capture');
          await this._switchToTab('scurve-tab');

          // Wait longer for full rendering (grid + chart + data)
          await this._wait(1500);

          // Capture FULL Kurva S (Grid + Chart)
          const kurvaSURL = await this._captureChartWithFallback('kurvaS', {
            scale: 2,
            backgroundColor: '#ffffff'
          });

          if (kurvaSURL) {
            attachments.push({
              title: 'A.3 - Kurva S Full (Grid + Weekly)',
              data_url: kurvaSURL
            });
            logger.info('✅ Kurva S FULL captured successfully (Grid + Chart)');
          } else {
            logger.warn('⚠️ Kurva S chart capture failed - chart may not be rendered');
          }
        } catch (error) {
          logger.warn('❌ Failed to capture Kurva S', error);
        }
      }

      // Restore original tab
      if (originalTab) {
        logger.debug(`Restoring original tab: ${originalTab}`);
        await this._switchToTab(originalTab);
      }

      // Send to backend
      return await this._sendExportRequest(format, {
        report_type: 'full',
        mode: 'weekly',  // Grid in weekly mode
        include_dates: false,
        attachments
      });

    } catch (error) {
      // Ensure we restore tab even if export fails
      if (originalTab) {
        await this._switchToTab(originalTab).catch(e => {
          logger.error('Failed to restore original tab', e);
        });
      }
      throw error;
    }
  }

  /**
   * Export B: Laporan Bulanan (Monthly Report)
   *
   * Includes:
   * - B.1: Grid Bulanan (4-week aggregation)
   * - B.2: Kurva S Bulanan (Monthly granularity)
   *
   * @param {string} format - Export format
   * @param {Object} options - Export options
   * @returns {Promise<Blob>} File blob
   */
  async exportMonthlyReport(format, options) {
    logger.info('Exporting Monthly Report (Laporan Bulanan)');

    // Remember current tab to restore later
    const originalTab = this._getCurrentTab();
    const attachments = [];

    try {
      // B.1: Grid Bulanan (handled by backend with mode='monthly')
      // Backend will aggregate 4 weeks into 1 month

      // B.2: Kurva S Bulanan
      if (options.includeKurvaS !== false) {
        try {
          // Switch to S-Curve tab to ensure chart is loaded
          logger.debug('Switching to S-Curve tab for monthly capture');
          await this._switchToTab('scurve-tab');
          await this._wait(800);

          // Get weekly cumulative data from app state
          const weeklyCumulative = this.app.state?.kurvaSData || [];

          if (weeklyCumulative.length === 0) {
            logger.warn('No Kurva S data available in app state');
          } else {
            logger.debug(`Converting ${weeklyCumulative.length} weeks to monthly`);

            // Sample at month boundaries (week 4, 8, 12...)
            const monthlyCumulative = sampleMonthlyCumulative(weeklyCumulative, 4);
            logger.debug(`Sampled ${monthlyCumulative.length} monthly data points`);

            // Check if Kurva S chart instance is now available
            if (!this.app.kurvaSChart) {
              logger.warn('Kurva S Chart instance still not available after tab switch');
            } else {
              // Temporarily switch chart to monthly mode
              await this._renderKurvaSMonthly(monthlyCumulative);

              // Capture monthly chart with fallback strategies
              const kurvaSURL = await this._captureChartWithFallback('kurvaS', {
                scale: 2,
                backgroundColor: '#ffffff'
              });

              if (kurvaSURL) {
                attachments.push({
                  title: 'B.2 - Kurva S Bulanan (Monthly)',
                  data_url: kurvaSURL
                });
                logger.info('Kurva S Bulanan captured successfully');
              } else {
                logger.warn('Kurva S chart capture failed - chart may not be rendered');
              }

              // Restore original weekly chart
              await this._restoreKurvaSWeekly();
            }
          }
        } catch (error) {
          logger.error('Failed to capture Kurva S Bulanan', error);
          // Try to restore weekly mode even if capture failed
          await this._restoreKurvaSWeekly().catch(e => {
            logger.error('Failed to restore weekly mode', e);
          });
        }
      }

      // Restore original tab
      if (originalTab) {
        logger.debug(`Restoring original tab: ${originalTab}`);
        await this._switchToTab(originalTab);
      }

      return await this._sendExportRequest(format, {
        report_type: 'monthly',
        mode: 'monthly',  // Grid in monthly mode
        weeks_per_month: 4,
        include_dates: false,
        attachments
      });

    } catch (error) {
      // Ensure we restore tab even if export fails
      if (originalTab) {
        await this._switchToTab(originalTab).catch(e => {
          logger.error('Failed to restore original tab', e);
        });
      }
      throw error;
    }
  }

  /**
   * Export C: Laporan Mingguan (Weekly Report)
   *
   * Includes:
   * - C.1: Grid Mingguan (Weekly mode with date ranges)
   * - C.2: Kurva S Mingguan (Weekly granularity)
   *
   * @param {string} format - Export format
   * @param {Object} options - Export options
   * @returns {Promise<Blob>} File blob
   */
  async exportWeeklyReport(format, options) {
    logger.info('Exporting Weekly Report (Laporan Mingguan)');

    // Remember current tab to restore later
    const originalTab = this._getCurrentTab();
    const attachments = [];

    try {
      // C.1: Grid Mingguan (same as Full but with date ranges)
      // Backend handles with mode='weekly' + include_dates=true

      // C.2: Kurva S Mingguan (Grid + S-Curve Weekly)
      if (options.includeKurvaS !== false) {
        try {
          logger.debug('Switching to S-Curve tab for full weekly capture');
          await this._switchToTab('scurve-tab');

          // Wait longer for full rendering
          await this._wait(1500);

          // Capture FULL Kurva S (Grid + Chart)
          const kurvaSURL = await this._captureChartWithFallback('kurvaS', {
            scale: 2,
            backgroundColor: '#ffffff'
          });

          if (kurvaSURL) {
            attachments.push({
              title: 'C.2 - Kurva S Mingguan (Grid + Weekly)',
              data_url: kurvaSURL
            });
            logger.info('✅ Kurva S Mingguan FULL captured successfully (Grid + Chart)');
          } else {
            logger.warn('⚠️ Kurva S chart capture failed - chart may not be rendered');
          }
        } catch (error) {
          logger.warn('❌ Failed to capture Kurva S Mingguan', error);
        }
      }

      // Restore original tab
      if (originalTab) {
        logger.debug(`Restoring original tab: ${originalTab}`);
        await this._switchToTab(originalTab);
      }

      return await this._sendExportRequest(format, {
        report_type: 'weekly',
        mode: 'weekly',
        include_dates: true,  // Include date ranges for each week
        attachments
      });

    } catch (error) {
      // Ensure we restore tab even if export fails
      if (originalTab) {
        await this._switchToTab(originalTab).catch(e => {
          logger.error('Failed to restore original tab', e);
        });
      }
      throw error;
    }
  }

  /**
   * Send export request to backend
   * @private
   * @param {string} format - Export format
   * @param {Object} payload - Request payload
   * @returns {Promise<Blob>} Response blob
   */
  async _sendExportRequest(format, payload) {
    logger.debug('Sending export request', { format, payload: { ...payload, attachments: `${payload.attachments?.length || 0} items` } });

    const projectId = this.app.state?.projectId;
    if (!projectId) {
      throw new Error('Project ID not found in app state');
    }

    const url = `/detail_project/api/project/${projectId}/export/jadwal-pekerjaan/${format}/`;

    logger.time('export-request');

    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': this.app.getCsrfToken?.() || this._getCsrfToken()
      },
      body: JSON.stringify(payload)
    });

    logger.timeEnd('export-request');

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Export request failed: ${response.statusText}\n${errorText}`);
    }

    const blob = await response.blob();
    logger.info(`Export successful: ${(blob.size / 1024).toFixed(2)} KB`);

    return blob;
  }

  /**
   * Get CSRF token from cookie
   * @private
   * @returns {string} CSRF token
   */
  _getCsrfToken() {
    const name = 'csrftoken';
    const cookies = document.cookie.split(';');

    for (let cookie of cookies) {
      cookie = cookie.trim();
      if (cookie.startsWith(name + '=')) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }

    return '';
  }

  /**
   * Temporarily render Kurva S in monthly mode
   * @private
   * @param {Array} monthlyData - Monthly cumulative data
   */
  async _renderKurvaSMonthly(monthlyData) {
    if (!this.app.kurvaSChart) {
      return;
    }

    logger.debug('Rendering Kurva S in monthly mode');

    // Save current state for restoration
    this._savedKurvaSData = this.app.state?.kurvaSData;

    // Render monthly
    this.app.kurvaSChart.renderMonthlyMode(monthlyData);

    // Wait for render to complete
    await this._wait(200);
  }

  /**
   * Restore Kurva S to weekly mode
   * @private
   */
  async _restoreKurvaSWeekly() {
    if (!this.app.kurvaSChart) {
      return;
    }

    logger.debug('Restoring Kurva S to weekly mode');

    // Restore weekly mode
    this.app.kurvaSChart.renderWeeklyMode(this._savedKurvaSData);

    // Wait for render
    await this._wait(200);

    // Clear saved data
    this._savedKurvaSData = null;
  }

  /**
   * Wait for specified milliseconds
   * @private
   * @param {number} ms - Milliseconds to wait
   * @returns {Promise<void>}
   */
  _wait(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Trigger file download from blob
   *
   * @param {Blob} blob - File blob
   * @param {string} filename - Download filename
   */
  downloadBlob(blob, filename) {
    logger.info(`Downloading: ${filename}`);

    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

    logger.info('Download triggered');
  }

  /**
   * Generate filename for export
   *
   * @param {string} reportType - Report type
   * @param {string} format - Export format
   * @returns {string} Filename
   *
   * @example
   * generateFilename('full', 'pdf')
   * // Returns: "Rekap_Laporan_ProjectName_2025-01-15.pdf"
   */
  generateFilename(reportType, format) {
    const reportNames = {
      'full': 'Rekap_Laporan',
      'monthly': 'Laporan_Bulanan',
      'weekly': 'Laporan_Mingguan'
    };

    const extensions = {
      'pdf': 'pdf',
      'word': 'docx',
      'xlsx': 'xlsx',
      'csv': 'csv'
    };

    const projectName = (this.app.state?.projectName || 'Project')
      .replace(/[^a-zA-Z0-9]/g, '_');
    const date = new Date().toISOString().split('T')[0];
    const reportName = reportNames[reportType] || 'Jadwal_Pekerjaan';
    const ext = extensions[format] || format;

    return `${reportName}_${projectName}_${date}.${ext}`;
  }
}

export default ExportCoordinator;
