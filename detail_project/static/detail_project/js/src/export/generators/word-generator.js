/**
 * Word Generator
 * Frontend coordinator untuk Word generation (actual generation di backend)
 *
 * @module export/generators/word-generator
 */

/**
 * Get CSRF token from cookie
 * @returns {string} CSRF token
 */
function getCsrfToken() {
  const name = 'csrftoken';
  const cookies = document.cookie.split(';');
  for (let cookie of cookies) {
    const [key, value] = cookie.trim().split('=');
    if (key === name) {
      return decodeURIComponent(value);
    }
  }
  return '';
}

/**
 * Generate Word document via backend
 * Sends attachments[] + metadata to backend → backend generates Word
 *
 * @param {Object} config - Configuration
 * @param {Array<Object>} config.attachments - Chart attachments: [{ title, data_url, format }]
 * @param {Object} [config.gridData] - Grid data (optional)
 * @param {string} config.reportType - 'rekap', 'monthly', 'weekly'
 * @param {Object} [config.options={}] - Additional options
 * @returns {Promise<{blob: Blob, metadata: Object}>} Word blob + metadata
 */
export async function generateWord(config) {
  const {
    attachments = [],
    gridData = null,
    reportType = 'rekap',
    options = {}
  } = config;

  console.log('[WordGenerator] Requesting Word generation from backend:', {
    reportType,
    attachmentsCount: attachments.length
  });

  // Determine strategy: batch upload atau single upload
  const useBatching = attachments.length > 50;

  try {
    if (useBatching) {
      // Batch upload mode
      return await generateWordBatched(config);
    } else {
      // Single upload mode
      return await generateWordSingle(config);
    }
  } catch (error) {
    console.error('[WordGenerator] Word generation failed:', error);
    throw error;
  }
}

/**
 * Generate Word dengan single upload (< 50 pages)
 */
async function generateWordSingle(config) {
  const { attachments, gridData, reportType, options } = config;

  const response = await fetch('/api/export/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({
      reportType,
      format: 'word',
      attachments,
      gridData,
      options
    })
  });

  if (!response.ok) {
    throw new Error(`Backend returned ${response.status}: ${response.statusText}`);
  }

  const blob = await response.blob();

  return {
    blob,
    metadata: {
      reportType,
      format: 'word',
      pageCount: attachments.length,
      generatedAt: new Date().toISOString()
    }
  };
}

/**
 * Generate Word dengan batch upload (>= 50 pages)
 */
async function generateWordBatched(config) {
  const { attachments, gridData, reportType, options } = config;
  const BATCH_SIZE = 10;

  // Step 1: Initialize export session
  const initRes = await fetch('/api/export/init', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({
      reportType,
      format: 'word',
      estimatedPages: attachments.length
    })
  });

  if (!initRes.ok) {
    throw new Error(`Export init failed: ${initRes.status}`);
  }

  const { exportId } = await initRes.json();

  console.log(`[WordGenerator] Export session initialized: ${exportId}`);

  // Step 2: Upload attachments dalam batch
  for (let i = 0; i < attachments.length; i += BATCH_SIZE) {
    const batch = attachments.slice(i, i + BATCH_SIZE);
    const batchIndex = Math.floor(i / BATCH_SIZE);

    await fetch('/api/export/upload-pages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken()
      },
      body: JSON.stringify({
        exportId,
        batchIndex,
        pages: batch
      })
    });

    console.log(`[WordGenerator] Uploaded batch ${batchIndex + 1}/${Math.ceil(attachments.length / BATCH_SIZE)}`);
  }

  // Step 3: Finalize & get download URL
  const finalRes = await fetch('/api/export/finalize', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({ exportId })
  });

  if (!finalRes.ok) {
    throw new Error(`Export finalize failed: ${finalRes.status}`);
  }

  const { downloadUrl } = await finalRes.json();

  // Download Word document
  const wordRes = await fetch(downloadUrl);
  const blob = await wordRes.blob();

  return {
    blob,
    metadata: {
      reportType,
      format: 'word',
      pageCount: attachments.length,
      exportId,
      generatedAt: new Date().toISOString()
    }
  };
}

/**
 * Download Word file to user's computer
 * @param {Blob} blob - Word file blob
 * @param {string} filename - Filename (without extension)
 */
export function downloadWord(blob, filename = 'export') {
  const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
  const fullFilename = `Laporan_${filename}_${timestamp}.docx`;

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fullFilename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  console.log('[WordGenerator] File downloaded:', fullFilename);
}
