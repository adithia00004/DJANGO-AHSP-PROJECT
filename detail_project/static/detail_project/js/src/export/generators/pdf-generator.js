/**
 * PDF Generator
 * Frontend coordinator untuk PDF generation (actual generation di backend)
 *
 * @module export/generators/pdf-generator
 */

/**
 * Normalize attachments[] (snake_case/camelCase) to backend page schema
 * Backend expects: { pageNumber, title, dataUrl, format }
 *
 * @param {Array<Object>} attachments
 * @returns {Array<Object>} pages
 */
function normalizeAttachmentsToPages(attachments = []) {
  const pages = [];

  for (const attachment of attachments) {
    if (!attachment) continue;

    const dataUrl = attachment.dataUrl || attachment.data_url || attachment.dataURL;
    if (!dataUrl) continue;

    pages.push({
      pageNumber: pages.length + 1,
      title: attachment.title || `Page ${pages.length + 1}`,
      dataUrl,
      format: attachment.format || 'png'
    });
  }

  return pages;
}

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

  const pages = normalizeAttachmentsToPages(attachments);

  console.log('[PDFGenerator] Requesting PDF generation from backend:', {
    reportType,
    attachmentsCount: attachments.length,
    pagesCount: pages.length
  });

  if (pages.length === 0) {
    throw new Error('[PDFGenerator] No valid attachments to generate PDF');
  }

  const { projectName = '' } = options || {};

  // Always use session-based API (init/upload-pages/finalize) since backend does not expose /api/export/generate
  const BATCH_SIZE = 10;

  // Get format from options (allows xlsx reuse of this function)
  const format = options.format || 'pdf';

  // Step 1: Initialize export session
  const initRes = await fetch('/detail_project/api/export/init', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({
      reportType,
      format: format,  // Use dynamic format
      estimatedPages: pages.length,
      projectName,
      metadata: {
        options,
        hasGridData: Boolean(gridData)
      }
    })
  });

  if (!initRes.ok) {
    throw new Error(`Export init failed: ${initRes.status}`);
  }

  const { exportId } = await initRes.json();

  console.log(`[PDFGenerator] Export session initialized: ${exportId}`);

  // Step 2: Upload attachments dalam batch
  for (let i = 0; i < pages.length; i += BATCH_SIZE) {
    const batch = pages.slice(i, i + BATCH_SIZE);
    const batchIndex = Math.floor(i / BATCH_SIZE);

    const uploadRes = await fetch('/detail_project/api/export/upload-pages', {
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

    if (!uploadRes.ok) {
      const text = await uploadRes.text().catch(() => '');
      throw new Error(`Export upload-pages failed: ${uploadRes.status} ${uploadRes.statusText}\n${text}`);
    }

    console.log(`[PDFGenerator] Uploaded batch ${batchIndex + 1}/${Math.ceil(pages.length / BATCH_SIZE)}`);
  }

  // Step 3: Finalize & get download URL
  const finalRes = await fetch('/detail_project/api/export/finalize', {
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

  await finalRes.json().catch(() => ({}));

  // Always download via authenticated endpoint
  const pdfRes = await fetch(`/detail_project/api/export/download/${exportId}`);
  if (!pdfRes.ok) {
    const text = await pdfRes.text().catch(() => '');
    throw new Error(`Export download failed: ${pdfRes.status} ${pdfRes.statusText}\n${text}`);
  }
  const blob = await pdfRes.blob();

  return {
    blob,
    metadata: {
      reportType,
      format: format,
      pageCount: pages.length,
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
