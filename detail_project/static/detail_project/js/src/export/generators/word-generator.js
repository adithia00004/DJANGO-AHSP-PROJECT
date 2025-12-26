/**
 * Word Generator
 * Frontend coordinator untuk Word generation (actual generation di backend)
 *
 * @module export/generators/word-generator
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

  const pages = normalizeAttachmentsToPages(attachments);

  console.log('[WordGenerator] Requesting Word generation from backend:', {
    reportType,
    attachmentsCount: attachments.length,
    pagesCount: pages.length
  });

  if (pages.length === 0) {
    throw new Error('[WordGenerator] No valid attachments to generate Word document');
  }

  const { projectName = '' } = options || {};

  // Always use session-based API (init/upload-pages/finalize) since backend does not expose /api/export/generate
  const BATCH_SIZE = 10;

  // Step 1: Initialize export session
  const initRes = await fetch('/detail_project/api/export/init', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCsrfToken()
    },
    body: JSON.stringify({
      reportType,
      format: 'word',
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

  console.log(`[WordGenerator] Export session initialized: ${exportId}`);

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

    console.log(`[WordGenerator] Uploaded batch ${batchIndex + 1}/${Math.ceil(pages.length / BATCH_SIZE)}`);
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
  const wordRes = await fetch(`/detail_project/api/export/download/${exportId}`);
  if (!wordRes.ok) {
    const text = await wordRes.text().catch(() => '');
    throw new Error(`Export download failed: ${wordRes.status} ${wordRes.statusText}\n${text}`);
  }
  const blob = await wordRes.blob();

  return {
    blob,
    metadata: {
      reportType,
      format: 'word',
      pageCount: pages.length,
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
