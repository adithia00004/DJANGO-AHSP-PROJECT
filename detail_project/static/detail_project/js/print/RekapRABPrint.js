/* =====================================================================
   REKAP-RAB-PRINT.JS - v5 (Final Corrections)
   
   CHANGELOG v5:
   B.1: Fix column alignment - show all values correctly
   B.2: Hierarchical border styling (thick for klasifikasi, medium for sub)
   C.1: Move "LEMBAR PENGESAHAN" title up for more table space
   C.3: Reduce signature space to prevent page break
   C.4: Keep signatures together using page-break-inside: avoid
   ===================================================================== */

import { PrintComponents, PrintUtils } from './PrintComponents.js';

export function initRekapRABPrint(rabModule) {
  if (!rabModule || !rabModule.btnPrint) {
    PrintUtils.log('Warning: RABModule or print button not found');
    return;
  }
  
  PrintUtils.log('Initializing Rekap RAB Print v5...');
  
  const printHandler = new RekapRABPrintHandler(rabModule);
  
  rabModule.btnPrint.replaceWith(rabModule.btnPrint.cloneNode(true));
  const newBtn = document.getElementById(rabModule.btnPrint.id) || rabModule.btnPrint;
  
  newBtn.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    printHandler.execute();
  }, { once: false });
  
  PrintUtils.log('Rekap RAB Print v5 initialized successfully');
}

class RekapRABPrintHandler {
  constructor(rabModule) {
    this.rabModule = rabModule;
    this.injectedElements = [];
    this.printInProgress = false;
    this.originalStyles = {};
  }

  log(message) {
    console.log(`[Rekap RAB Print v5] ${message}`);
  }

  async execute() {
    if (this.printInProgress) {
      this.log('Print already in progress, skipping...');
      return;
    }
    
    try {
      this.printInProgress = true;
      this.log('Starting print execution...');
      
      this.storeOriginalStyles();
      await this.prepare();
      await this.expandAllRows();
      await this.moveTfootToEnd();
      await this.injectComponents();
      this.applyPrintStyles();
      await this.sleep(300);
      
      this.log('Triggering print dialog...');
      window.print();
      
      setTimeout(() => {
        this.cleanup();
        this.printInProgress = false;
      }, 1000);
      
    } catch (error) {
      this.handleError(error);
      this.printInProgress = false;
    }
  }

  storeOriginalStyles() {
    this.log('Storing original styles...');
    
    const body = document.body;
    this.originalStyles.bodyClass = body.className;
    this.originalStyles.bodyDataTheme = body.getAttribute('data-theme');
    
    const mainContent = document.querySelector('#main-content > div.container-fluid.mt-2');
    if (mainContent) {
      this.originalStyles.mainContentMaxWidth = mainContent.style.maxWidth;
      this.originalStyles.mainContentWidth = mainContent.style.width;
    }
    
    const tfoot = document.querySelector('#rekap-table tfoot');
    if (tfoot) {
      this.originalStyles.tfootParent = tfoot.parentNode;
      this.originalStyles.tfootNextSibling = tfoot.nextSibling;
    }
  }

  async prepare() {
    this.log('Preparing for print...');
    
    const body = document.body;
    body.classList.remove('dark-mode', 'theme-dark');
    body.classList.add('light-mode', 'theme-light', 'print-mode');
    body.setAttribute('data-theme', 'light');
    
    const mainContent = document.querySelector('#main-content > div.container-fluid.mt-2');
    if (mainContent) {
      mainContent.style.maxWidth = '100%';
      mainContent.style.width = '100%';
    }
    
    const toolbar = document.getElementById('rab-toolbar');
    if (toolbar) {
      toolbar.style.display = 'none';
    }

    const table = document.getElementById('rekap-table');
    if (table) {
      const thead = table.querySelector('thead');
      if (thead) {
        thead.style.position = 'static';
      }
    }
  }

  async expandAllRows() {
    this.log('Expanding all rows...');
    
    const expandBtn = document.getElementById('btn-expand-all');
    if (expandBtn) {
      expandBtn.click();
      await this.sleep(500);
    }
  }

  async moveTfootToEnd() {
    this.log('Moving tfoot to end...');
    
    const table = document.getElementById('rekap-table');
    const tfoot = table?.querySelector('tfoot');
    
    if (!tfoot) {
      this.log('No tfoot found, skipping...');
      return;
    }
    
    const summaryData = this.extractSummaryFromTfoot(tfoot);
    
    const summaryDiv = document.createElement('div');
    summaryDiv.className = 'print-summary-section';
    summaryDiv.id = 'print-summary-replacement';
    
    summaryDiv.innerHTML = `
      <div class="print-summary-content">
        <table class="print-summary-table">
          <tr>
            <td class="summary-label">Total Proyek (D)</td>
            <td class="summary-separator">:</td>
            <td class="summary-value">${summaryData.totalD}</td>
          </tr>
          <tr>
            <td class="summary-label">PPN ${summaryData.ppnPercent}%</td>
            <td class="summary-separator">:</td>
            <td class="summary-value">${summaryData.ppnValue}</td>
          </tr>
          <tr>
            <td class="summary-label">Grand Total (Total Biaya Langsung + PPN)</td>
            <td class="summary-separator">:</td>
            <td class="summary-value">${summaryData.grandTotal}</td>
          </tr>
          <tr>
            <td class="summary-label">Pembulatan (${summaryData.roundingBase})</td>
            <td class="summary-separator">:</td>
            <td class="summary-value">${summaryData.rounded}</td>
          </tr>
        </table>
      </div>
    `;
    
    tfoot.style.display = 'none';
    
    const tableWrap = document.getElementById('rekap-table-wrap');
    if (tableWrap && tableWrap.parentNode) {
      tableWrap.parentNode.appendChild(summaryDiv);
      this.injectedElements.push(summaryDiv);
    }
  }

  extractSummaryFromTfoot(tfoot) {
    const ppnInput = tfoot.querySelector('#inp-ppn, input[type="number"]');
    const ppnPercent = ppnInput ? ppnInput.value : '11';
    
    const roundingSelect = tfoot.querySelector('#sel-rounding-base, select');
    const roundingBase = roundingSelect ? roundingSelect.value : '10000';
    
    const tfootCells = Array.from(tfoot.querySelectorAll('th'));
    
    let totalD = 0;
    
    const totalCell = tfootCells.find(cell => 
      cell.textContent.includes('Rp') || 
      cell.classList.contains('text-end') ||
      cell.style.textAlign === 'right'
    );
    
    if (totalCell) {
      const text = totalCell.textContent.replace(/[^0-9]/g, '');
      totalD = parseFloat(text) || 0;
    }
    
    if (totalD === 0 && tfootCells.length > 0) {
      const lastCell = tfootCells[tfootCells.length - 1];
      const text = lastCell.textContent.replace(/[^0-9]/g, '');
      totalD = parseFloat(text) || 0;
    }
    
    const ppn = totalD * (parseFloat(ppnPercent) / 100);
    const grandTotal = totalD + ppn;
    const base = parseInt(roundingBase);
    const rounded = Math.round(grandTotal / base) * base;
    
    return {
      totalD: this.formatNumber(Math.round(totalD)),
      ppnPercent: ppnPercent,
      ppnValue: this.formatNumber(Math.round(ppn)),
      grandTotal: this.formatNumber(Math.round(grandTotal)),
      roundingBase: this.formatNumber(base),
      rounded: this.formatNumber(rounded)
    };
  }

  formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  async injectComponents() {
    this.log('Injecting print components...');
    
    try {
      const rekapApp = document.getElementById('rekap-app');
      if (!rekapApp) throw new Error('Rekap app container not found');

      const table = document.getElementById('rekap-table');
      if (!table) throw new Error('Rekap table not found');

      const projectInfo = this.getProjectInfo();

      const printHeader = this.createPrintHeader(projectInfo);
      
      const tableWrap = document.getElementById('rekap-table-wrap');
      if (tableWrap && tableWrap.parentNode) {
        tableWrap.parentNode.insertBefore(printHeader, tableWrap);
        this.injectedElements.push(printHeader);
      } else if (table.parentNode) {
        table.parentNode.insertBefore(printHeader, table);
        this.injectedElements.push(printHeader);
      }

      const printFooter = this.createPrintFooter(projectInfo);
      
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
              <td class="info-label">Sumber Dana</td>
              <td class="info-separator">:</td>
              <td class="info-value">${info.sumberDana || '-'}</td>
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

  createPrintFooter(info) {
    const klasifikasiData = this.extractKlasifikasiTotals();
    
    const footer = document.createElement('div');
    footer.className = 'print-footer-signatures';
    footer.innerHTML = `
      <div class="print-signatures-wrapper">
        <!-- FIX C.1: Title moved up, less margin -->
        <h3 class="signatures-title">LEMBAR PENGESAHAN</h3>
        
        <!-- FIX C.4: Klasifikasi table can break, signatures cannot -->
        <div class="klasifikasi-summary">
          <table class="klasifikasi-table">
            <thead>
              <tr>
                <th style="width: 10%;">No</th>
                <th style="width: 60%;">Klasifikasi</th>
                <th style="width: 30%;">Total (Rp)</th>
              </tr>
            </thead>
            <tbody>
              ${klasifikasiData.map((item, idx) => `
                <tr>
                  <td style="text-align: center;">${idx + 1}</td>
                  <td>${item.name}</td>
                  <td style="text-align: right;">${item.total}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        </div>
        
        <!-- FIX C.3 & C.4: Signatures together, reduced space -->
        <div class="signatures-section">
          <div class="signatures-grid-two">
            <div class="signature-box">
              <p class="sig-role">Disetujui Oleh,</p>
              <p class="sig-position">Pemilik Proyek</p>
              <div class="sig-space"></div>
              <div class="sig-underline"></div>
              <p class="sig-name">( _________________________________ )</p>
              <p class="sig-nip">NIP/NIK: __________________________</p>
            </div>
            
            <div class="signature-box">
              <p class="sig-role">Dibuat Oleh,</p>
              <p class="sig-position">Konsultan Perencana</p>
              <div class="sig-space"></div>
              <div class="sig-underline"></div>
              <p class="sig-name">( _________________________________ )</p>
              <p class="sig-nip">NIP/NIK: __________________________</p>
            </div>
          </div>
        </div>
      </div>
    `;
    return footer;
  }

  extractKlasifikasiTotals() {
    const table = document.getElementById('rekap-table');
    if (!table) return [];
    
    const klasifikasiRows = table.querySelectorAll('tbody tr[data-level="1"]');
    const klasifikasiData = [];
    
    klasifikasiRows.forEach(row => {
      const cells = row.querySelectorAll('td');
      if (cells.length >= 6) {
        const name = cells[0].textContent.trim().replace(/^[▼▶]\s*/, '');
        const totalText = cells[5].textContent.trim();
        
        klasifikasiData.push({
          name: name,
          total: totalText
        });
      }
    });
    
    return klasifikasiData;
  }

  applyPrintStyles() {
    this.log('Applying print styles v5...');
    
    let styleEl = document.getElementById('rekap-print-styles');
    if (!styleEl) {
      styleEl = document.createElement('style');
      styleEl.id = 'rekap-print-styles';
      document.head.appendChild(styleEl);
    }

    styleEl.textContent = `
      @media print {
        @page {
          size: A4 landscape;
          margin: 15mm 10mm 15mm 10mm;
        }
        
        * {
          -webkit-print-color-adjust: exact !important;
          print-color-adjust: exact !important;
          color-adjust: exact !important;
        }

        /* Force light mode */
        body,
        body.dark-mode,
        body[data-theme="dark"] {
          background: #ffffff !important;
          color: #000000 !important;
        }

        *,
        *::before,
        *::after {
          background-color: transparent !important;
          color: #000000 !important;
        }

        /* Container width */
        #main-content,
        #main-content > div.container-fluid.mt-2,
        .container-fluid {
          max-width: 100% !important;
          width: 100% !important;
          margin: 0 !important;
          padding: 0 !important;
        }

        /* Hide non-printable */
        #rab-toolbar,
        #dp-topbar,
        #dp-sidebar,
        .btn,
        button,
        nav,
        .card:not(.print-keep),
        input,
        select {
          display: none !important;
        }

        body {
          margin: 0 !important;
          padding: 0 !important;
          background: white !important;
          color: #000 !important;
          font-family: 'Arial', sans-serif !important;
        }

        #rekap-app {
          max-width: none !important;
          padding: 0 !important;
          margin: 0 !important;
        }

        #rekap-table-wrap {
          max-height: none !important;
          height: auto !important;
          overflow: visible !important;
        }

        /* Header */
        .print-header {
          width: 100%;
          margin-bottom: 20px;
          page-break-inside: avoid;
          border-bottom: 3px solid #000;
          padding-bottom: 15px;
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

        .print-info-table {
          width: 100%;
          max-width: 650px;
          margin: 0 auto;
          border-collapse: collapse;
        }

        .print-info-table tr {
          height: 26px;
        }

        .print-info-table td {
          padding: 4px 10px;
          font-size: 10pt;
          color: #000 !important;
        }

        .info-label {
          width: 150px;
          font-weight: 600;
        }

        .info-separator {
          width: 20px;
          text-align: center;
        }

        /* FIX B.1: Table - ensure all columns visible with correct values */
        #rekap-table {
          width: 100% !important;
          border-collapse: collapse !important;
          font-size: 8pt !important;
          page-break-inside: auto !important;
          table-layout: fixed !important;
          margin-top: 15px;
        }

        /* Proper column widths */
        #rekap-table col:nth-child(1) { width: 35%; }  /* Uraian */
        #rekap-table col:nth-child(2) { width: 12%; }  /* Kode AHSP */
        #rekap-table col:nth-child(3) { width: 8%; }   /* Satuan */
        #rekap-table col:nth-child(4) { width: 10%; }  /* Volume */
        #rekap-table col:nth-child(5) { width: 15%; }  /* Harga Satuan */
        #rekap-table col:nth-child(6) { width: 20%; }  /* Total */

        /* Table head */
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
          font-size: 9pt !important;
        }

        /* Table body */
        #rekap-table tbody {
          display: table-row-group !important;
        }

        #rekap-table tbody tr {
          page-break-inside: avoid !important;
          display: table-row !important;
        }

        /* FIX B.1: Ensure all cells display with correct alignment */
        #rekap-table tbody td {
          border: 1px solid #666 !important;
          padding: 5px 4px !important;
          color: #000 !important;
          background: #fff !important;
          font-size: 8pt !important;
          display: table-cell !important;
          visibility: visible !important;
          overflow: visible !important;
          white-space: normal !important;
          word-wrap: break-word !important;
        }

        /* Column-specific alignment - FIX B.1 */
        #rekap-table tbody td:nth-child(1) { 
          text-align: left !important;
        }
        #rekap-table tbody td:nth-child(2) { 
          text-align: center !important;  /* Kode AHSP - center */
        }
        #rekap-table tbody td:nth-child(3) { 
          text-align: center !important;  /* Satuan - center */
        }
        #rekap-table tbody td:nth-child(4) { 
          text-align: right !important;   /* Volume - right */
        }
        #rekap-table tbody td:nth-child(5) { 
          text-align: right !important;   /* Harga - right */
        }
        #rekap-table tbody td:nth-child(6) { 
          text-align: right !important;   /* Total - right */
        }

        /* FIX B.2: Hierarchical border styling */
        
        /* Level 1 - Klasifikasi: Thick border (1 px), wraps around its children */
        #rekap-table tbody tr[data-level="1"] td {
          font-weight: bold !important;
          background-color: #d9d9d9 !important;
          color: #000 !important;
          font-size: 9pt !important;
          border: 1px solid #000 !important;  /* Thick border */
        }

        #rekap-table tbody tr[data-level="1"] td:first-child {
          padding-left: 8px !important;
        }

        /* First klasifikasi row - top border only */
        #rekap-table tbody tr[data-level="1"]:first-of-type td {
          border-top: 1px solid #000 !important;
          border-left: 1px solid #000 !important;
          border-right: 1px solid #000 !important;
          border-bottom: 1px solid #666 !important;
        }

        /* Subsequent klasifikasi rows */
        #rekap-table tbody tr[data-level="1"] + tr[data-level="2"] td,
        #rekap-table tbody tr[data-level="1"] + tr[data-level="3"] td {
          border-left: 1px solid #000 !important;  /* Inherit thick left border */
          border-right: 1px solid #000 !important; /* Inherit thick right border */
        }

        /* Level 2 - Sub-klasifikasi: Medium border (1px), wraps around itself */
        #rekap-table tbody tr[data-level="2"] td {
          font-weight: 600 !important;
          background-color: #efefef !important;
          color: #000 !important;
          border: 1px solid #333 !important;  /* Medium border */
        }

        #rekap-table tbody tr[data-level="2"] td:first-child {
          padding-left: 20px !important;
        }

        /* Level 3 - Pekerjaan: Normal border (1px) */
        #rekap-table tbody tr[data-level="3"] td {
          font-weight: normal !important;
          background-color: #fff !important;
          color: #000 !important;
          border: 1px solid #666 !important;  /* Normal border */
        }

        #rekap-table tbody tr[data-level="3"] td:first-child {
          padding-left: 35px !important;
        }

        /* Last row of klasifikasi group - bottom border thick */
        #rekap-table tbody tr[data-level="1"] + tr:not([data-level="1"]):last-of-type td,
        #rekap-table tbody tr[data-level="3"]:last-child td {
          border-bottom: 2.5px solid #000 !important;
        }

        /* Hide toggle */
        .toggle,
        .toggle-icon {
          display: none !important;
        }

        /* Hide tfoot */
        #rekap-table tfoot {
          display: none !important;
        }

        /* Summary section */
        .print-summary-section {
          width: 100%;
          margin: 25px 0;
          padding: 15px 0;
          border-top: 2px solid #000;
          border-bottom: 2px solid #000;
          page-break-inside: avoid;
        }

        .print-summary-table {
          width: 100%;
          max-width: 500px;
          margin: 0 auto;
          border-collapse: collapse;
        }

        .print-summary-table tr {
          height: 30px;
        }

        .print-summary-table td {
          padding: 5px 10px;
          font-size: 11pt;
          font-weight: 600;
          color: #000 !important;
        }

        .summary-label {
          width: 220px;
        }

        .summary-value {
          text-align: right;
          font-weight: bold;
        }

        /* FIX C: Signature section improvements */
        .print-footer-signatures {
          page-break-before: always !important;
          margin-top: 30px;
          width: 100%;
        }

        .print-signatures-wrapper {
          width: 100%;
          padding: 20px 20px;  /* Reduced from 30px */
        }

        /* FIX C.1: Title with less margin */
        .signatures-title {
          text-align: center;
          font-size: 14pt;
          font-weight: bold;
          margin: 0 0 20px 0;  /* Reduced from 30px */
          letter-spacing: 2px;
          text-decoration: underline;
          color: #000 !important;
        }

        /* FIX C.4: Klasifikasi table can break across pages */
        .klasifikasi-summary {
          width: 100%;
          margin-bottom: 30px;
          page-break-inside: auto;  /* Allow breaking */
        }

        .klasifikasi-table {
          width: 100%;
          border-collapse: collapse;
        }

        .klasifikasi-table thead {
          display: table-header-group;  /* Repeat header if breaks */
        }

        .klasifikasi-table thead th {
          background-color: #4a4a4a !important;
          color: #ffffff !important;
          border: 1.5px solid #000 !important;
          padding: 8px 6px !important;
          font-weight: bold !important;
          text-align: center !important;
          font-size: 10pt !important;
        }

        .klasifikasi-table tbody {
          page-break-inside: auto;  /* Allow breaking within table */
        }

        .klasifikasi-table tbody tr {
          page-break-inside: avoid;  /* But not within a row */
        }

        .klasifikasi-table tbody td {
          border: 1px solid #333 !important;
          padding: 6px 8px !important;
          color: #000 !important;
          background: #fff !important;
          font-size: 9pt !important;
        }

        /* FIX C.3 & C.4: Signatures stay together, reduced space */
        .signatures-section {
          page-break-inside: avoid !important;  /* CRITICAL: Keep together */
          page-break-before: avoid !important;
          margin-top: 20px;
        }

        .signatures-grid-two {
          display: flex;
          justify-content: space-around;
          align-items: flex-start;
          gap: 60px;
          margin: 0 60px;
        }

        .signature-box {
          flex: 1;
          text-align: center;
          min-width: 250px;
        }

        .sig-role {
          font-size: 11pt;
          margin: 0 0 5px 0;  /* Reduced from 8px */
          color: #000 !important;
        }

        .sig-position {
          font-size: 11pt;
          font-weight: bold;
          margin: 0 0 10px 0;  /* Reduced from 15px */
          color: #000 !important;
        }

        /* FIX C.3: Reduced signature space from 60mm to 45mm */
        .sig-space {
          height: 45mm;  /* Was 60mm */
          margin: 10px 0;  /* Reduced from 15px */
        }

        .sig-underline {
          width: 80%;
          margin: 0 auto 5px;  /* Reduced bottom margin */
          border-bottom: 1px solid #000;
        }

        .sig-name {
          font-size: 10pt;
          font-weight: bold;
          margin: 5px 0 3px 0;  /* Reduced margins */
          color: #000 !important;
        }

        .sig-nip {
          font-size: 9pt;
          margin: 2px 0 0 0;  /* Reduced from 3px */
          color: #000 !important;
        }

        /* Ensure visibility */
        #rekap-table,
        #rekap-table *,
        .print-header,
        .print-summary-section,
        .print-footer-signatures {
          visibility: visible !important;
          opacity: 1 !important;
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

        #rekap-table tr {
          display: table-row !important;
        }

        #rekap-table td,
        #rekap-table th {
          display: table-cell !important;
        }
      }
    `;
  }

  cleanup() {
    this.log('Cleaning up...');
    
    this.injectedElements.forEach(el => {
      if (el && el.parentNode) {
        el.parentNode.removeChild(el);
      }
    });
    this.injectedElements = [];

    const body = document.body;
    body.className = this.originalStyles.bodyClass || '';
    if (this.originalStyles.bodyDataTheme) {
      body.setAttribute('data-theme', this.originalStyles.bodyDataTheme);
    }
    body.classList.remove('print-mode');

    const mainContent = document.querySelector('#main-content > div.container-fluid.mt-2');
    if (mainContent && this.originalStyles.mainContentMaxWidth !== undefined) {
      mainContent.style.maxWidth = this.originalStyles.mainContentMaxWidth;
      mainContent.style.width = this.originalStyles.mainContentWidth;
    }

    const toolbar = document.getElementById('rab-toolbar');
    if (toolbar) {
      toolbar.style.display = '';
    }

    const table = document.getElementById('rekap-table');
    if (table) {
      const thead = table.querySelector('thead');
      if (thead) {
        thead.style.position = '';
      }
    }

    const tfoot = document.querySelector('#rekap-table tfoot');
    if (tfoot) {
      tfoot.style.display = '';
    }
  }

  getProjectInfo() {
    const titleSelectors = ['h1', 'h2', '.project-title'];
    let titleEl = null;
    for (const selector of titleSelectors) {
      titleEl = document.querySelector(selector);
      if (titleEl) break;
    }
    
    const info = {
      projectName: titleEl ? titleEl.textContent.trim() : 'Pembangunan Gedung Serbaguna',
      owner: 'Dinas PUPR (Pemprov DKI Jakarta)',
      location: 'Jakarta',
      year: new Date().getFullYear().toString(),
      sumberDana: 'APBD'
    };

    const metaEls = document.querySelectorAll('.project-meta dt, .project-meta dd, .card-body p');
    metaEls.forEach(el => {
      const text = el.textContent.toLowerCase();
      const value = el.textContent.trim();
      
      if (text.includes('pemilik')) info.owner = value.replace(/pemilik\s*:\s*/i, '');
      if (text.includes('lokasi')) info.location = value.replace(/lokasi\s*:\s*/i, '');
      if (text.includes('tahun')) info.year = value.replace(/tahun\s*:\s*/i, '');
      if (text.includes('sumber dana')) info.sumberDana = value.replace(/sumber dana\s*:\s*/i, '');
    });

    return info;
  }

  formatDate(date) {
    const months = [
      'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
      'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ];
    
    return `${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()}`;
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  handleError(error) {
    console.error('[Rekap RAB Print v5] Error:', error);
    alert('Terjadi kesalahan saat mencetak. Silakan coba lagi.');
    this.cleanup();
    this.printInProgress = false;
  }
}

// Export
export { RekapRABPrintHandler };
export default { initRekapRABPrint, RekapRABPrintHandler };

window.RekapRABPrintHandler = RekapRABPrintHandler;
console.log('[RAB] RekapRABPrint v5 handler loaded successfully');