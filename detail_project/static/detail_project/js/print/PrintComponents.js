/* =====================================================================
   PRINT-COMPONENTS.JS - Reusable Print Components (Shared)
   File: detail_project/static/detail_project/js/print/PrintComponents.js
   
   Usage: Import in page-specific print adapters
   
   Example:
   import { PrintComponents } from './PrintComponents.js';
   const header = PrintComponents.createHeader(data);
   ===================================================================== */

export const PrintComponents = {
  
  /**
   * Create print document header
   * @param {Object} data - Header data
   * @param {string} data.title - Document title
   * @param {string} data.projectName - Project name
   * @param {string} data.projectCode - Project code
   * @param {string} data.projectLocation - Project location
   * @param {string} data.year - Year
   * @param {string} data.printDate - Print date
   * @param {string} data.printTime - Print time
   * @param {string} [data.logoUrl] - Optional logo URL
   * @returns {HTMLElement} Header element
   */
  createHeader(data) {
    const header = document.createElement('div');
    header.className = 'print-header d-print-block';
    
    const logoHtml = data.logoUrl 
      ? `<img src="${data.logoUrl}" alt="Logo" width="60" height="60">`
      : this._getDefaultLogo();
    
    header.innerHTML = `
      <div class="print-header-top">
        <div class="print-header-logo">
          ${logoHtml}
        </div>
        
        <div class="print-header-title">
          <h1>${this._escape(data.title)}</h1>
          <h2>${this._escape(data.projectName)}</h2>
          <p>Tahun Anggaran ${data.year}</p>
        </div>
        
        <div class="print-header-info">
          <div><strong>Kode:</strong> ${data.projectCode}</div>
          <div><strong>Lokasi:</strong> ${this._escape(data.projectLocation)}</div>
          <div style="margin-top: 5mm;">
            <small>Dicetak: ${data.printDate}</small><br>
            <small>Pukul: ${data.printTime}</small>
          </div>
        </div>
      </div>
      
      <div class="print-header-meta">
        <div class="print-header-meta-item">
          <span class="print-header-meta-label">Nama Kegiatan:</span>
          <span class="print-header-meta-value">${this._escape(data.projectName)}</span>
        </div>
        <div class="print-header-meta-item">
          <span class="print-header-meta-label">Lokasi Pekerjaan:</span>
          <span class="print-header-meta-value">${this._escape(data.projectLocation)}</span>
        </div>
        <div class="print-header-meta-item">
          <span class="print-header-meta-label">Tahun Anggaran:</span>
          <span class="print-header-meta-value">${data.year}</span>
        </div>
      </div>
    `;
    
    return header;
  },
  
  /**
   * Create signatures section
   * @param {Object} data - Signature data
   * @param {string} data.projectName - Project name
   * @param {string} data.grandTotal - Grand total (optional)
   * @param {string} data.printDate - Print date
   * @param {string} data.printTime - Print time
   * @param {Array} [data.signatories] - Custom signatories (optional)
   * @returns {HTMLElement} Signatures section
   */
  createSignatures(data) {
    const section = document.createElement('div');
    section.className = 'print-signatures d-print-block';
    
    const description = data.grandTotal
      ? `Dokumen <strong>${this._escape(data.projectName)}</strong> dengan nilai total <strong>${data.grandTotal}</strong> telah diperiksa dan disetujui untuk dilaksanakan sesuai dengan ketentuan yang berlaku.`
      : `Dokumen <strong>${this._escape(data.projectName)}</strong> telah diperiksa dan disetujui untuk dilaksanakan sesuai dengan ketentuan yang berlaku.`;
    
    const signatories = data.signatories || [
      { title: 'Mengetahui,<br>Kepala Dinas', name: '', nip: '' },
      { title: 'Menyetujui,<br>Pejabat Pembuat Komitmen', name: '', nip: '' },
      { title: 'Dibuat Oleh,<br>Tim Penyusun', name: '', nip: '' }
    ];
    
    const signatureBoxes = signatories.map(sig => this._createSignatureBox(sig)).join('');
    
    section.innerHTML = `
      <div class="print-signatures-container">
        <p class="print-signatures-title">PENGESAHAN</p>
        <p class="print-signatures-desc">${description}</p>
        
        <div class="print-signatures-row">
          ${signatureBoxes}
        </div>
        
        <div style="margin-top: 8mm; font-size: 8pt; color: #666; text-align: center;">
          <p>Dokumen ini dicetak pada ${data.printDate} pukul ${data.printTime}</p>
        </div>
      </div>
    `;
    
    return section;
  },
  
  /**
   * Create single signature box
   * @private
   */
  _createSignatureBox(data) {
    const name = data.name || '_________________________';
    const nip = data.nip || '_______________________';
    
    return `
      <div class="print-signature-box">
        <div class="print-signature-title">${data.title}</div>
        <div class="print-signature-name">( ${name} )</div>
        <div class="print-signature-nip">NIP. ${nip}</div>
      </div>
    `;
  },
  
  /**
   * Show PDF save instruction popup
   * @param {number} [duration=30000] - Duration in ms before auto-hide
   */
  showPDFInstruction(duration = 30000) {
    // Remove existing instruction if any
    const existing = document.getElementById('print-pdf-instruction');
    if (existing) existing.remove();
    
    const popup = document.createElement('div');
    popup.id = 'print-pdf-instruction';
    popup.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 18px 24px;
      border-radius: 12px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
      z-index: 100000;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
      font-size: 14px;
      max-width: 340px;
      animation: slideInRight 0.3s ease-out;
    `;
    
    popup.innerHTML = `
      <div style="display: flex; align-items: start; gap: 12px;">
        <div style="font-size: 28px;">💾</div>
        <div>
          <strong style="font-size: 15px; display: block; margin-bottom: 8px;">
            Simpan sebagai PDF
          </strong>
          <ol style="margin: 0; padding-left: 20px; line-height: 1.6;">
            <li>Pilih <strong>"Save as PDF"</strong> atau <strong>"Microsoft Print to PDF"</strong></li>
            <li>Orientasi: <strong>Landscape</strong></li>
            <li>Klik tombol <strong>Save/Print</strong></li>
            <li>Pilih lokasi penyimpanan file</li>
          </ol>
          <div style="margin-top: 10px; padding-top: 10px; border-top: 1px solid rgba(255,255,255,0.3); font-size: 12px;">
            💡 Pastikan <strong>"Background graphics"</strong> aktif
          </div>
        </div>
      </div>
    `;
    
    // Add animation
    if (!document.getElementById('print-popup-style')) {
      const style = document.createElement('style');
      style.id = 'print-popup-style';
      style.textContent = `
        @keyframes slideInRight {
          from {
            transform: translateX(100%);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }
      `;
      document.head.appendChild(style);
    }
    
    document.body.appendChild(popup);
    
    // Remove after print dialog
    const removePopup = () => {
      if (popup.parentNode) popup.remove();
      window.removeEventListener('afterprint', removePopup);
    };
    
    window.addEventListener('afterprint', removePopup, { once: true });
    
    // Also remove on timeout
    setTimeout(removePopup, duration);
  },
  
  /**
   * Create cover page
   * @param {Object} data - Cover page data
   * @returns {HTMLElement} Cover page element
   */
  createCoverPage(data) {
    const cover = document.createElement('div');
    cover.className = 'print-cover d-print-block';
    
    const logoHtml = data.logoUrl
      ? `<img src="${data.logoUrl}" alt="Logo">`
      : this._getDefaultLogo();
    
    cover.innerHTML = `
      <div class="print-cover-logo">
        ${logoHtml}
      </div>
      <h1>${this._escape(data.title)}</h1>
      <h2>${this._escape(data.projectName)}</h2>
      <p>Kode: ${data.projectCode}</p>
      <p>Lokasi: ${this._escape(data.projectLocation)}</p>
      <div class="print-cover-meta">
        <p>Tahun Anggaran ${data.year}</p>
        <p style="margin-top: 30mm;">${data.organization || ''}</p>
        <p>${data.department || ''}</p>
      </div>
    `;
    
    return cover;
  },
  
  /**
   * Get default SVG logo
   * @private
   */
  _getDefaultLogo() {
    return `
      <svg width="60" height="60" viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect width="60" height="60" rx="8" fill="#2c3e50"/>
        <path d="M15 25 L30 15 L45 25 M18 27 V42 H25 V35 H35 V42 H42 V27" 
              stroke="white" stroke-width="2.5" fill="none"/>
        <text x="30" y="53" text-anchor="middle" fill="white" 
              font-size="10" font-weight="bold">RAB</text>
      </svg>
    `;
  },
  
  /**
   * Escape HTML to prevent XSS
   * @private
   */
  _escape(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  },
  
  /**
   * Create info box
   * @param {string} title - Box title
   * @param {string} content - Box content
   * @returns {HTMLElement}
   */
  createInfoBox(title, content) {
    const box = document.createElement('div');
    box.className = 'print-info-box';
    box.innerHTML = `
      <div class="print-info-box-title">${this._escape(title)}</div>
      <div>${content}</div>
    `;
    return box;
  },
  
  /**
   * Create section divider
   * @returns {HTMLElement}
   */
  createDivider() {
    const divider = document.createElement('div');
    divider.className = 'print-section-divider';
    return divider;
  }
};

/**
 * Utility functions for print operations
 */
export const PrintUtils = {
  
  /**
   * Sleep/delay function
   * @param {number} ms - Milliseconds
   * @returns {Promise}
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  },
  
  /**
   * Get current date/time in Indonesian format
   * @returns {Object} Date and time strings
   */
  getCurrentDateTime() {
    const now = new Date();
    return {
      date: now.toLocaleDateString('id-ID', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      }),
      time: now.toLocaleTimeString('id-ID', {
        hour: '2-digit',
        minute: '2-digit'
      }),
      dateShort: now.toLocaleDateString('id-ID'),
      timeShort: now.toLocaleTimeString('id-ID', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      })
    };
  },
  
  /**
   * Format number to Indonesian Rupiah
   * @param {number} value - Number value
   * @param {boolean} [withCurrency=false] - Include "Rp" prefix
   * @returns {string}
   */
  formatRupiah(value, withCurrency = false) {
    if (value == null || value === '') return '-';
    const formatted = new Intl.NumberFormat('id-ID', {
      maximumFractionDigits: 0
    }).format(Math.round(Number(value)));
    return withCurrency ? `Rp ${formatted}` : formatted;
  },
  
  /**
   * Format number with decimals
   * @param {number} value - Number value
   * @param {number} [decimals=2] - Decimal places
   * @returns {string}
   */
  formatNumber(value, decimals = 2) {
    if (value == null || value === '') return '';
    return new Intl.NumberFormat('id-ID', {
      maximumFractionDigits: decimals,
      minimumFractionDigits: decimals
    }).format(Number(value));
  },
  
  /**
   * Extract project data from DOM
   * @param {HTMLElement} container - Container element with data attributes
   * @returns {Object} Project data
   */
  extractProjectData(container) {
    if (!container) return {};
    
    const dateTime = this.getCurrentDateTime();
    
    return {
      projectId: container.dataset.projectId || '',
      projectName: container.dataset.projectName || 'Nama Proyek',
      projectCode: container.dataset.projectCode || '-',
      projectLocation: container.dataset.projectLocation || '-',
      year: container.dataset.projectYear || new Date().getFullYear(),
      printDate: dateTime.date,
      printTime: dateTime.time,
      printDateShort: dateTime.dateShort,
      printTimeShort: dateTime.timeShort
    };
  },
  
  /**
   * Clean element content (remove inputs, buttons, etc)
   * @param {HTMLElement} element - Element to clean
   * @returns {HTMLElement} Cleaned element
   */
  cleanElementForPrint(element) {
    const clone = element.cloneNode(true);
    
    // Remove interactive elements
    const selectors = [
      'input:not(.print-keep)',
      'select:not(.print-keep)',
      'textarea:not(.print-keep)',
      'button',
      '.btn',
      '.input-group',
      '.form-control',
      '.form-select'
    ];
    
    clone.querySelectorAll(selectors.join(',')).forEach(el => el.remove());
    
    return clone;
  },
  
  /**
   * Show loading state on button
   * @param {HTMLElement} button - Button element
   * @param {boolean} loading - Loading state
   */
  setButtonLoading(button, loading) {
    if (!button) return;
    
    if (loading) {
      button.disabled = true;
      button.classList.add('printing');
      button.dataset.originalText = button.innerHTML;
      
      const spinner = '<span class="spinner-border spinner-border-sm me-2"></span>';
      button.innerHTML = spinner + 'Menyiapkan...';
    } else {
      button.disabled = false;
      button.classList.remove('printing');
      
      if (button.dataset.originalText) {
        button.innerHTML = button.dataset.originalText;
        delete button.dataset.originalText;
      }
    }
  },
  
  /**
   * Log print operation
   * @param {string} message - Log message
   * @param {any} [data] - Additional data
   */
  log(message, data) {
    const timestamp = new Date().toISOString();
    console.log(`[PrintComponents ${timestamp}] ${message}`, data || '');
  },
  
  /**
   * Handle print error
   * @param {Error} error - Error object
   * @param {string} [context] - Error context
   */
  handleError(error, context = 'Print') {
    console.error(`[${context}] Error:`, error);
    alert(`Terjadi kesalahan saat menyiapkan ${context.toLowerCase()}. Silakan coba lagi.\n\nDetail: ${error.message}`);
  }
};

// Export default
export default {
  PrintComponents,
  PrintUtils
};