/* =====================================================================
   REKAP-RAB-PRINT.JS - Rekap RAB Print Adapter (v2 - All Issues Fixed)
   File: detail_project/static/detail_project/js/print/RekapRABPrint.js
   
   CHANGELOG v2:
   - Fixed project identity layout (not cramped)
   - Consistent table styling (borders, colors, fonts)
   - Single print process (no double print)
   - Signature only on last page
   - Fixed header/column width alignment
   - Fixed missing data/values
   ===================================================================== */

import { PrintComponents, PrintUtils } from './PrintComponents.js';

/**
 * Initialize Rekap RAB Print functionality
 */
export function initRekapRABPrint(rabModule) {
  if (!rabModule || !rabModule.btnPrint) {
    PrintUtils.log('Warning: RABModule or print button not found');
    return;
  }
  
  PrintUtils.log('Initializing Rekap RAB Print v2...');
  
  const printHandler = new RekapRABPrintHandler(rabModule);
  
  // FIXED: Remove any existing listeners to prevent double print
  rabModule.btnPrint.replaceWith(rabModule.btnPrint.cloneNode(true));
  const newBtn = document.getElementById(rabModule.btnPrint.id) || rabModule.btnPrint;
  
  newBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    printHandler.execute();
  }, { once: false });
  
  PrintUtils.log('Rekap RAB Print v2 initialized successfully');
}

/**
 * Rekap RAB Print Handler Class
 */
class RekapRABPrintHandler {
  constructor(rabModule) {
    this.rabModule = rabModule;
    this.injectedElements = [];
    this.printInProgress = false; // Prevent double print
  }

  log(message) {
    console.log(`[Rekap RAB Print v2] ${message}`);
  }

  /**
   * Main execution method
   */
  async execute() {
    // FIXED: Prevent double print
    if (this.printInProgress) {
      this.log('Print already in progress, skipping...');
      return;
    }
    
    try {
      this.printInProgress = true;
      this.log('Starting print execution...');
      
      // 1. Prepare for print
      await this.prepare();
      
      // 2. Expand all rows
      await this.expandAllRows();
      
      // 3. Inject print components
      await this.injectComponents();
      
      // 4. Apply print styles
      this.applyPrintStyles();
      
      // 5. Wait for DOM updates
      await this.sleep(300);
      
      // 6. Trigger print
      this.log('Triggering print dialog...');
      window.print();
      
      // 7. Cleanup after print (with delay)
      setTimeout(() => {
        this.cleanup();
        this.printInProgress = false;
      }, 1000);
      
    } catch (error) {
      this.handleError(error);
      this.printInProgress = false;
    }
  }

  /**
   * Prepare for print
   */
  async prepare() {
    this.log('Preparing for print...');
    
    // Hide toolbar
    const toolbar = document.getElementById('rab-toolbar');
    if (toolbar) {
      toolbar.style.display = 'none';
    }

    // Remove fixed positioning from table elements
    const table = document.getElementById('rekap-table');
    if (table) {
      const thead = table.querySelector('thead');
      const tfoot = table.querySelector('tfoot');
      
      if (thead) {
        thead.style.position = 'static';
      }
      if (tfoot) {
        tfoot.style.position = 'static';
      }
    }
  }

  /**
   * Expand all rows
   */
  async expandAllRows() {
    this.log('Expanding all rows...');
    
    const expandBtn = document.getElementById('btn-expand-all');
    if (expandBtn) {
      expandBtn.click();
      await this.sleep(500);
    }
  }

  /**
   * Inject print-specific components
   */
  async injectComponents() {
    this.log('Injecting print components...');
    
    try {
      const rekapApp = document.getElementById('rekap-app');
      if (!rekapApp) {
        throw new Error('Rekap app container not found');
      }

      const table = document.getElementById('rekap-table');
      if (!table) {
        throw new Error('Rekap table not found');
      }

      // Get project info
      const projectInfo = this.getProjectInfo();

      // Create print header
      const printHeader = this.createPrintHeader(projectInfo);
      
      // Insert header
      const tableWrap = document.getElementById('rekap-table-wrap');
      if (tableWrap && tableWrap.parentNode) {
        tableWrap.parentNode.insertBefore(printHeader, tableWrap);
        this.injectedElements.push(printHeader);
      } else if (table.parentNode) {
        table.parentNode.insertBefore(printHeader, table);
        this.injectedElements.push(printHeader);
      }

      // Create print footer (signature - only on last page)
      const printFooter = this.createPrintFooter(projectInfo);
      
      // Insert footer AFTER table wrap
      if (tableWrap && tableWrap.parentNode) {
        tableWrap.parentNode.appendChild(printFooter);
        this.injectedElements.push(printFooter);
      } else if (table.parentNode) {
        table.parentNode.appendChild(printFooter);
        this.injectedElements.push(printFooter);
      }

      this.log('Components injected successfully');
      
    } catch (error) {
      this.log(`Error in injectComponents: ${error.message}`);
      throw error;
    }
  }

  /**
   * Create print header - FIXED: Better layout, not cramped
   */
  createPrintHeader(info) {
    const header = document.createElement('div');
    header.className = 'print-header';
    header.innerHTML = `
      <div class="print-header-wrapper">
        <div class="print-title-section">
          <h1 class="print-main-title">REKAPITULASI</h1>
          <h2 class="print-sub-title">RENCANA ANGGARAN BIAYA</h2>
        </div>
        
        <div class="print-info-section">
          <table class="print-info-table">
            <tr>
              <td class="info-label">Nama Proyek</td>
              <td class="info-separator">:</td>
              <td class="info-value">${info.projectName || '-'}</td>
            </tr>
            <tr>
              <td class="info-label">Pemilik Proyek</td>
              <td class="info-separator">:</td>
              <td class="info-value">${info.owner || '-'}</td>
            </tr>
            <tr>
              <td class="info-label">Lokasi</td>
              <td class="info-separator">:</td>
              <td class="info-value">${info.location || '-'}</td>
            </tr>
            <tr>
              <td class="info-label">Tahun Anggaran</td>
              <td class="info-separator">:</td>
              <td class="info-value">${info.year || new Date().getFullYear()}</td>
            </tr>
            <tr>
              <td class="info-label">Tanggal Cetak</td>
              <td class="info-separator">:</td>
              <td class="info-value">${this.formatDate(new Date())}</td>
            </tr>
          </table>
        </div>
      </div>
    `;
    return header;
  }

  /**
   * Create print footer - FIXED: Only on last page
   */
  createPrintFooter(info) {
    const footer = document.createElement('div');
    footer.className = 'print-footer-signatures';
    footer.innerHTML = `
      <div class="print-signatures-wrapper">
        <h3 class="signatures-title">PENGESAHAN</h3>
        <div class="signatures-grid">
          <div class="signature-box">
            <p class="sig-role">Menyetujui,</p>
            <p class="sig-position">Pemilik Proyek</p>
            <div class="sig-line"></div>
            <p class="sig-name">( _________________________ )</p>
            <p class="sig-subtitle">NIP/NIK: </p>
          </div>
          
          <div class="signature-box">
            <p class="sig-role">Mengetahui,</p>
            <p class="sig-position">Konsultan Perencana</p>
            <div class="sig-line"></div>
            <p class="sig-name">( _________________________ )</p>
            <p class="sig-subtitle">NIP/NIK: </p>
          </div>
          
          <div class="signature-box">
            <p class="sig-role">Menyusun,</p>
            <p class="sig-position">Pelaksana Pekerjaan</p>
            <div class="sig-line"></div>
            <p class="sig-name">( _________________________ )</p>
            <p class="sig-subtitle">NIP/NIK: </p>
          </div>
        </div>
      </div>
    `;
    return footer;
  }

  /**
   * Apply print styles - FIXED: All styling issues
   */
  applyPrintStyles() {
    this.log('Applying print styles v2...');
    
    let styleEl = document.getElementById('rekap-print-styles');
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = 'rekap-print-styles';
      document.head.appendChild(styleEl);
    }

    styleEl.textContent = `
      /* ============================================================
         PRINT STYLES v2 - Fixed All Issues
         ============================================================ */
      
      @media print {
        /* ===== PAGE SETUP ===== */
        @page {
          size: A4 landscape;
          margin: 15mm 10mm 15mm 10mm;
        }
        
        * {
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
          color-adjust: exact !important;
        }

        /* ===== HIDE NON-PRINTABLE ===== */
        #rab-toolbar,
        .rekap-toolbar,
        #dp-topbar,
        #dp-sidebar,
        .btn,
        button:not(.print-keep),
        .no-print,
        nav,
        .breadcrumb,
        .alert {
          display: none !important;
        }

        /* ===== BODY & CONTAINER ===== */
        body {
          margin: 0 !important;
          padding: 0 !important;
          background: white !important;
          color: #000 !important;
          font-family: 'Arial', 'Helvetica', sans-serif !important;
        }

        #rekap-app {
          max-width: none !important;
          padding: 0 !important;
          margin: 0 !important;
          width: 100% !important;
        }

        #rekap-table-wrap {
          max-height: none !important;
          height: auto !important;
          overflow: visible !important;
        }

        /* ===== PRINT HEADER - FIXED: Not cramped ===== */
        .print-header {
          width: 100%;
          margin-bottom: 20px;
          page-break-inside: avoid;
          border-bottom: 3px solid #000;
          padding-bottom: 15px;
        }

        .print-header-wrapper {
          width: 100%;
        }

        .print-title-section {
          text-align: center;
          margin-bottom: 20px;
        }

        .print-main-title {
          font-size: 18pt;
          font-weight: bold;
          margin: 0 0 5px 0;
          letter-spacing: 2px;
          color: #000 !important;
        }

        .print-sub-title {
          font-size: 16pt;
          font-weight: bold;
          margin: 0;
          letter-spacing: 1px;
          color: #000 !important;
        }

        .print-info-section {
          margin-top: 15px;
        }

        .print-info-table {
          width: 100%;
          max-width: 600px;
          margin: 0 auto;
          border-collapse: collapse;
        }

        .print-info-table tr {
          height: 24px;
        }

        .print-info-table td {
          padding: 3px 8px;
          vertical-align: top;
          font-size: 10pt;
          color: #000 !important;
        }

        .info-label {
          width: 150px;
          font-weight: 600;
          text-align: left;
        }

        .info-separator {
          width: 15px;
          text-align: center;
          font-weight: bold;
        }

        .info-value {
          font-weight: normal;
          text-align: left;
        }

        /* ===== TABLE STYLES - FIXED: Consistent styling ===== */
        #rekap-table {
          width: 100% !important;
          border-collapse: collapse !important;
          font-size: 8pt !important;
          page-break-inside: auto !important;
          table-layout: fixed !important;
          margin-top: 15px;
        }

        /* FIXED: Column widths to match header */
        #rekap-table col:nth-child(1) { width: 35%; }  /* Uraian */
        #rekap-table col:nth-child(2) { width: 12%; }  /* Kode */
        #rekap-table col:nth-child(3) { width: 8%; }   /* Satuan */
        #rekap-table col:nth-child(4) { width: 10%; }  /* Volume */
        #rekap-table col:nth-child(5) { width: 15%; }  /* Harga Satuan */
        #rekap-table col:nth-child(6) { width: 20%; }  /* Total */

        /* ===== THEAD - FIXED: Consistent borders and colors ===== */
        #rekap-table thead {
          position: static !important;
          display: table-header-group !important;
        }

        #rekap-table thead th {
          background-color: #4a4a4a !important;
          color: #ffffff !important;
          border: 1.5px solid #000 !important;
          padding: 8px 6px !important;
          font-weight: bold !important;
          text-align: center !important;
          vertical-align: middle !important;
          font-size: 9pt !important;
          position: static !important;
        }

        /* ===== TBODY - FIXED: No missing data ===== */
        #rekap-table tbody {
          display: table-row-group !important;
        }

        #rekap-table tbody tr {
          page-break-inside: avoid !important;
          page-break-after: auto !important;
          display: table-row !important;
        }

        #rekap-table tbody td {
          border: 1px solid #333 !important;
          padding: 5px 4px !important;
          color: #000 !important;
          background: #fff !important;
          vertical-align: middle !important;
          font-size: 8pt !important;
          overflow: visible !important;
          text-overflow: clip !important;
          white-space: normal !important;
          word-wrap: break-word !important;
        }

        /* Level 1 - Klasifikasi (Bold + Gray background) */
        #rekap-table tbody tr[data-level="1"] td {
          font-weight: bold !important;
          background-color: #d9d9d9 !important;
          color: #000 !important;
        }

        #rekap-table tbody tr[data-level="1"] td:first-child {
          padding-left: 6px !important;
        }

        /* Level 2 - Sub (Bold + Light gray) */
        #rekap-table tbody tr[data-level="2"] td {
          font-weight: 600 !important;
          background-color: #efefef !important;
          color: #000 !important;
        }

        #rekap-table tbody tr[data-level="2"] td:first-child {
          padding-left: 18px !important;
        }

        /* Level 3 - Pekerjaan (Normal + White) */
        #rekap-table tbody tr[data-level="3"] td {
          font-weight: normal !important;
          background-color: #fff !important;
          color: #000 !important;
        }

        #rekap-table tbody tr[data-level="3"] td:first-child {
          padding-left: 32px !important;
        }

        /* Text alignment per column */
        #rekap-table tbody td:nth-child(1) { text-align: left !important; }    /* Uraian */
        #rekap-table tbody td:nth-child(2) { text-align: center !important; }  /* Kode */
        #rekap-table tbody td:nth-child(3) { text-align: center !important; }  /* Satuan */
        #rekap-table tbody td:nth-child(4) { text-align: right !important; }   /* Volume */
        #rekap-table tbody td:nth-child(5) { text-align: right !important; }   /* Harga */
        #rekap-table tbody td:nth-child(6) { text-align: right !important; }   /* Total */

        /* Hide toggle buttons */
        .toggle,
        .toggle-icon {
          display: none !important;
        }

        /* ===== TFOOT - FIXED: Consistent with thead ===== */
        #rekap-table tfoot {
          position: static !important;
          display: table-footer-group !important;
        }

        #rekap-table tfoot th {
          background-color: #4a4a4a !important;
          color: #ffffff !important;
          border: 1.5px solid #000 !important;
          padding: 8px 6px !important;
          font-weight: bold !important;
          font-size: 9pt !important;
          text-align: right !important;
        }

        #rekap-table tfoot th:first-child {
          text-align: left !important;
        }

        /* FIXED: Ensure tfoot inputs/selects are hidden or styled */
        #rekap-table tfoot input,
        #rekap-table tfoot select {
          border: none !important;
          background: transparent !important;
          color: #fff !important;
          font-weight: bold !important;
          text-align: right !important;
          padding: 0 !important;
        }

        /* ===== PRINT FOOTER - FIXED: Only on last page ===== */
        .print-footer-signatures {
          page-break-before: always !important;
          page-break-inside: avoid !important;
          margin-top: 40px;
          width: 100%;
        }

        .print-signatures-wrapper {
          width: 100%;
          padding: 20px 0;
        }

        .signatures-title {
          text-align: center;
          font-size: 14pt;
          font-weight: bold;
          margin: 0 0 30px 0;
          letter-spacing: 1px;
          text-decoration: underline;
          color: #000 !important;
        }

        .signatures-grid {
          display: flex;
          justify-content: space-around;
          align-items: flex-start;
          gap: 30px;
          margin: 0 40px;
        }

        .signature-box {
          flex: 1;
          text-align: center;
          min-width: 200px;
        }

        .sig-role {
          font-size: 10pt;
          font-weight: normal;
          margin: 0 0 60px 0;
          color: #000 !important;
        }

        .sig-line {
          height: 50px;
          margin: 10px 0;
        }

        .sig-name {
          font-size: 10pt;
          font-weight: bold;
          margin: 5px 0;
          color: #000 !important;
        }

        .sig-position {
          font-size: 10pt;
          font-weight: bold;
          margin: 5px 0 0 0;
          color: #000 !important;
        }

        .sig-subtitle {
          font-size: 9pt;
          margin: 3px 0 0 0;
          color: #000 !important;
        }

        /* ===== ENSURE VISIBILITY ===== */
        #rekap-table,
        #rekap-table *,
        .print-header,
        .print-header *,
        .print-footer-signatures,
        .print-footer-signatures * {
          visibility: visible !important;
          opacity: 1 !important;
          display: table-cell !important;
        }

        #rekap-table {
          display: table !important;
        }

        #rekap-table thead {
          display: table-header-group !important;
        }

        #rekap-table tbody {
          display: table-row-group !important;
        }

        #rekap-table tfoot {
          display: table-footer-group !important;
        }

        #rekap-table tr {
          display: table-row !important;
        }

        .print-header,
        .print-footer-signatures {
          display: block !important;
        }

        /* Remove hover effects */
        #rekap-table tbody tr:hover {
          background: inherit !important;
        }

        /* FIXED: Prevent text from being cut off */
        * {
          box-sizing: border-box !important;
        }
      }
    `;
  }

  /**
   * Cleanup after print
   */
  cleanup() {
    this.log('Cleaning up...');
    
    // Remove injected elements
    this.injectedElements.forEach(el => {
      if (el && el.parentNode) {
        el.parentNode.removeChild(el);
      }
    });
    this.injectedElements = [];

    // Restore toolbar
    const toolbar = document.getElementById('rab-toolbar');
    if (toolbar) {
      toolbar.style.display = '';
    }

    // Restore table positioning
    const table = document.getElementById('rekap-table');
    if (table) {
      const thead = table.querySelector('thead');
      const tfoot = table.querySelector('tfoot');
      
      if (thead) {
        thead.style.position = '';
      }
      if (tfoot) {
        tfoot.style.position = '';
      }
    }
  }

  /**
   * Get project information from page
   */
  getProjectInfo() {
    // Try multiple selectors for project info
    const titleSelectors = [
      'h1.project-title',
      'h2.project-title', 
      '.project-header h1',
      '.project-header h2',
      '#project-title',
      'h1',
      'h2'
    ];
    
    let titleEl = null;
    for (const selector of titleSelectors) {
      titleEl = document.querySelector(selector);
      if (titleEl) break;
    }
    
    const info = {
      title: 'REKAPITULASI RENCANA ANGGARAN BIAYA',
      projectName: titleEl ? titleEl.textContent.trim() : 'Pembangunan Gedung Serbaguna',
      owner: 'Dinas PUPR (Pemprov DKI Jakarta)',
      location: 'Jakarta',
      year: new Date().getFullYear().toString()
    };

    // Try to extract from meta elements
    const metaEls = document.querySelectorAll('.project-meta dt, .project-meta dd');
    for (let i = 0; i < metaEls.length; i += 2) {
      const key = metaEls[i]?.textContent?.toLowerCase() || '';
      const value = metaEls[i + 1]?.textContent?.trim() || '';
      
      if (key.includes('pemilik') || key.includes('owner')) info.owner = value;
      if (key.includes('lokasi') || key.includes('location')) info.location = value;
      if (key.includes('tahun') || key.includes('year')) info.year = value;
      if (key.includes('nama') || key.includes('proyek') || key.includes('project')) {
        info.projectName = value;
      }
    }

    return info;
  }

  /**
   * Format date to Indonesian format
   */
  formatDate(date) {
    const months = [
      'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
      'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ];
    
    const day = date.getDate();
    const month = months[date.getMonth()];
    const year = date.getFullYear();
    
    return `${day} ${month} ${year}`;
  }

  /**
   * Sleep helper
   */
  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * Error handler
   */
  handleError(error) {
    console.error('[Rekap RAB Print v2] Error:', error);
    alert('Terjadi kesalahan saat mencetak. Silakan coba lagi.');
    this.cleanup();
    this.printInProgress = false;
  }
}

// Export
export { RekapRABPrintHandler };
export default { initRekapRABPrint, RekapRABPrintHandler };

window.RekapRABPrintHandler = RekapRABPrintHandler;
console.log('[RAB] RekapRABPrint v2 handler loaded successfully');