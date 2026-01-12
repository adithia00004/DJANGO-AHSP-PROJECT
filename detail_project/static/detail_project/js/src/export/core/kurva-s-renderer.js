/**
 * Kurva S Offscreen Renderer
 * Renders Kurva S charts (weekly/monthly) to offscreen canvas using uPlot
 *
 * @module export/core/kurva-s-renderer
 */

import uPlot from 'uplot';

/**
 * Preload fonts untuk consistent text metrics
 * @returns {Promise<void>}
 */
async function preloadFonts() {
  const fonts = [
    new FontFace('Arial', 'local(Arial)'),
    new FontFace('Arial', 'local(Arial Bold)', { weight: 'bold' })
  ];

  await Promise.all(fonts.map(f => f.load()));
  fonts.forEach(f => document.fonts.add(f));
  await document.fonts.ready;

  console.log('[KurvaSRenderer] Fonts preloaded');
}

/**
 * Generate month labels for monthly progressive mode
 * @param {number} totalWeeks - Total weeks in dataset
 * @param {number} weeksPerMonth - Weeks per month (default: 4)
 * @returns {Array<string>} Month labels ["M1", "M2", ...]
 */
function generateMonthLabels(totalWeeks, weeksPerMonth = 4) {
  const monthCount = Math.ceil(totalWeeks / weeksPerMonth);
  return Array.from({ length: monthCount }, (_, i) => `M${i + 1}`);
}

/**
 * Sample cumulative data untuk monthly progressive mode
 * M1 = cumulative sampai W4, M2 = cumulative sampai W8, dst
 *
 * @param {Array<Object>} weeklyData - Weekly data: [{ week, planned, actual }]
 * @param {number} weeksPerMonth - Weeks per month (default: 4)
 * @returns {Array<Object>} Monthly data: [{ month, planned, actual }]
 */
function sampleMonthlyProgressive(weeklyData, weeksPerMonth = 4) {
  const monthlyData = [];
  const totalWeeks = weeklyData.length;
  const monthCount = Math.ceil(totalWeeks / weeksPerMonth);

  for (let m = 1; m <= monthCount; m++) {
    // Ambil minggu terakhir dari bulan ini (kumulatif)
    const weekIndex = Math.min(m * weeksPerMonth - 1, totalWeeks - 1);
    const weekData = weeklyData[weekIndex];

    monthlyData.push({
      month: m,
      planned: weekData.planned,
      actual: weekData.actual
    });
  }

  return monthlyData;
}

/**
 * Render Kurva S chart to offscreen canvas
 *
 * @param {Object} config - Rendering configuration
 * @param {string} config.granularity - 'weekly' or 'monthly'
 * @param {number} [config.weeks_per_month=4] - Weeks per month (for monthly mode)
 * @param {Array<Object>} config.data - Chart data: [{ week, planned, actual }]
 * @param {number} [config.width=1200] - Canvas width in logical px
 * @param {number} [config.height=600] - Canvas height in logical px
 * @param {number} [config.dpi=300] - Target DPI (300 for PDF, 150 for Excel)
 * @param {string} [config.backgroundColor='#ffffff'] - Chart background color
 * @param {string} [config.timezone='Asia/Jakarta'] - Project timezone
 * @returns {Promise<string>} PNG dataURL (base64)
 */
export async function renderKurvaS(config) {
  const {
    granularity = 'weekly',
    weeks_per_month = 4,
    data = [],
    width = 1200,
    height = 600,
    dpi = 300,
    backgroundColor = '#ffffff',
    timezone = 'Asia/Jakarta'
  } = config;

  // Validasi data
  if (!data || data.length === 0) {
    throw new Error('[KurvaSRenderer] Data tidak boleh kosong');
  }

  console.log(`[KurvaSRenderer] Rendering Kurva S ${granularity} mode:`, {
    dataPoints: data.length,
    width,
    height,
    dpi
  });

  // Preload fonts
  await preloadFonts();

  // Prepare data berdasarkan granularity
  let chartData, labels;

  if (granularity === 'monthly') {
    const monthlyData = sampleMonthlyProgressive(data, weeks_per_month);
    labels = monthlyData.map(d => `M${d.month}`);
    chartData = [
      monthlyData.map((_, i) => i), // X-axis: indices
      monthlyData.map(d => d.planned), // Series 1: Planned
      monthlyData.map(d => d.actual)   // Series 2: Actual
    ];
  } else {
    // Weekly mode
    labels = data.map(d => `W${d.week}`);
    chartData = [
      data.map((_, i) => i), // X-axis: indices
      data.map(d => d.planned), // Series 1: Planned
      data.map(d => d.actual)   // Series 2: Actual
    ];
  }

  // DPI scaling
  const BASE_DPI = 96;
  const SCALE = dpi / BASE_DPI;
  const physicalWidth = Math.round(width * SCALE);
  const physicalHeight = Math.round(height * SCALE);

  // Create hidden container
  const hiddenContainer = document.createElement('div');
  hiddenContainer.style.cssText = `
    position: fixed;
    left: -99999px;
    top: -99999px;
    width: ${width}px;
    height: ${height}px;
    visibility: hidden;
    pointer-events: none;
    background-color: ${backgroundColor};
  `;
  document.body.appendChild(hiddenContainer);

  try {
    // uPlot options
    const opts = {
      width,
      height,
      title: granularity === 'monthly' ? 'Kurva S Monthly Progressive' : 'Kurva S Weekly',
      series: [
        {}, // X-axis (indices)
        {
          label: 'Planned',
          stroke: '#00CED1', // cyan
          width: 2,
          points: { show: true, size: 4, fill: '#00CED1' }
        },
        {
          label: 'Actual',
          stroke: '#FFD700', // yellow
          width: 2,
          points: { show: true, size: 4, fill: '#FFD700' }
        }
      ],
      axes: [
        {
          // X-axis
          values: (u, vals) => vals.map(v => labels[v] || ''),
          grid: { show: true },
          ticks: { show: true }
        },
        {
          // Y-axis (%)
          values: (u, vals) => vals.map(v => `${v.toFixed(1)}%`),
          grid: { show: true },
          ticks: { show: true }
        }
      ],
      legend: {
        show: true
      },
      cursor: {
        show: false // Disable cursor untuk export
      },
      scales: {
        x: {
          time: false // Bukan time series
        },
        y: {
          range: (u, dataMin, dataMax) => {
            // Auto range dengan buffer
            const buffer = (dataMax - dataMin) * 0.1;
            return [
              Math.max(0, dataMin - buffer),
              Math.min(100, dataMax + buffer)
            ];
          }
        }
      }
    };

    // Initialize uPlot
    const chart = new uPlot(opts, chartData, hiddenContainer);

    // Wait untuk render selesai
    await new Promise(resolve => setTimeout(resolve, 100));

    // Extract canvas
    const canvas = hiddenContainer.querySelector('canvas');
    if (!canvas) {
      throw new Error('[KurvaSRenderer] Canvas tidak ditemukan');
    }

    // Scale canvas untuk DPI
    const scaledCanvas = document.createElement('canvas');
    scaledCanvas.width = physicalWidth;
    scaledCanvas.height = physicalHeight;

    const ctx = scaledCanvas.getContext('2d');

    // Fill background
    ctx.fillStyle = backgroundColor;
    ctx.fillRect(0, 0, physicalWidth, physicalHeight);

    // Scale context
    ctx.scale(SCALE, SCALE);

    // Draw original canvas
    ctx.drawImage(canvas, 0, 0, width, height);

    // Convert to PNG dataURL
    const dataURL = scaledCanvas.toDataURL('image/png');

    // Cleanup
    chart.destroy();
    hiddenContainer.remove();

    console.log('[KurvaSRenderer] Rendering completed:', {
      outputSize: `${physicalWidth}x${physicalHeight}px`,
      dataURLLength: dataURL.length
    });

    return dataURL;

  } catch (error) {
    // Cleanup on error
    hiddenContainer.remove();
    console.error('[KurvaSRenderer] Rendering failed:', error);
    throw error;
  }
}

/**
 * Render multiple Kurva S charts (batch mode)
 * Useful untuk rendering beberapa chart dengan config berbeda
 *
 * @param {Array<Object>} configs - Array of config objects
 * @returns {Promise<Array<string>>} Array of PNG dataURLs
 */
export async function renderKurvaSBatch(configs) {
  console.log(`[KurvaSRenderer] Batch rendering ${configs.length} charts`);

  const results = [];
  for (let i = 0; i < configs.length; i++) {
    const config = configs[i];
    console.log(`[KurvaSRenderer] Rendering chart ${i + 1}/${configs.length}`);

    const dataURL = await renderKurvaS(config);
    results.push(dataURL);

    // GC hint setiap 5 charts
    if (i % 5 === 4) {
      await new Promise(resolve => setTimeout(resolve, 50));
    }
  }

  return results;
}
