/**
 * PDF Generator
 * Frontend coordinator untuk PDF generation (actual generation di backend)
 *
 * @module export/generators/pdf-generator
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
 * Generate PDF via backend
 * Sends attachments[] + metadata to backend → backend generates PDF
 *
 * @param {Object} config - Configuration
 * @param {Array<Object>} config.attachments - Chart attachments: [{ title, data_url, format }]
 * @param {Object} [config.gridData] - Grid data (optional)
 * @param {string} config.reportType - 'rekap', 'monthly', 'weekly'
 * @param {Object} [config.options={}] - Additional options
 * @returns {Promise<{blob: Blob, metadata: Object}>} PDF blob + metadata
 */
export async function generatePDF(config) {
  const {
    attachments = [],
    gridData = null,
    reportType = 'rekap',
    options = {}
  } = config;

  console.log('[PDFGenerator] Requesting PDF generation from backend:', {
    reportType,
    attachmentsCount: attachments.length
  });

  // Determine strategy: batch upload atau single upload
  const useBatching = attachments.length > 50;

  try {
    if (useBatching) {
      // Batch upload mode
      return await generatePDFBatched(config);
    } else {
      // Single upload mode
      return await generatePDFSingle(config);
    }
  } catch (error) {
    console.error('[PDFGenerator] PDF generation failed:', error);
    throw error;
  }
}

/**
 * Generate PDF dengan single upload (< 50 pages)
 */
async function generatePDFSingle(config) {
  const { attachments, gridData, reportType, options } = config;

  const response = await fetch('/api/export/generate', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({
      reportType,
      format: 'pdf',
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
      format: 'pdf',
      pageCount: attachments.length,
      generatedAt: new Date().toISOString()
    }
  };
}

/**
 * Generate PDF dengan batch upload (>= 50 pages)
 */
async function generatePDFBatched(config) {
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
      format: 'pdf',
      estimatedPages: attachments.length
    })
  });

  if (!initRes.ok) {
    throw new Error(`Export init failed: ${initRes.status}`);
  }

  const { exportId } = await initRes.json();

  console.log(`[PDFGenerator] Export session initialized: ${exportId}`);

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

    console.log(`[PDFGenerator] Uploaded batch ${batchIndex + 1}/${Math.ceil(attachments.length / BATCH_SIZE)}`);
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

  // Download PDF
  const pdfRes = await fetch(downloadUrl);
  const blob = await pdfRes.blob();

  return {
    blob,
    metadata: {
      reportType,
      format: 'pdf',
      pageCount: attachments.length,
      exportId,
      generatedAt: new Date().toISOString()
    }
  };
}

/**
 * Download PDF file to user's computer
 * @param {Blob} blob - PDF file blob
 * @param {string} filename - Filename (without extension)
 */
export function downloadPDF(blob, filename = 'export') {
  const timestamp = new Date().toISOString().replace(/[-:T]/g, '').slice(0, 14);
  const fullFilename = `Laporan_${filename}_${timestamp}.pdf`;

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fullFilename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  console.log('[PDFGenerator] File downloaded:', fullFilename);
}
