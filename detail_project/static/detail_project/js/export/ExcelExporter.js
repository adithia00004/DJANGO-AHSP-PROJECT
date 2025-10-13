/* =====================================================================
   FILE 1: ExcelExporter.js
   Path: detail_project/static/detail_project/js/ExcelExporter.js
   
   COMPLETE EXCEL EXPORT SOLUTION
   ===================================================================== */

class RekapRABExcelExporter {
  constructor(projectId) {
    this.projectId = projectId;
    this.workbook = null;
    this.worksheet = null;
  }

  log(message) {
    console.log(`[Excel Export] ${message}`);
  }

  /**
   * Main export function
   */
  async export() {
    try {
      this.log('Starting Excel export...');
      
      // Check if XLSX available
      if (typeof XLSX === 'undefined') {
        throw new Error('SheetJS library not loaded. Please refresh the page.');
      }

      // Collect data from page
      const data = this.collectData();
      
      if (!data.tableData || data.tableData.length === 0) {
        throw new Error('No data found to export');
      }
      
      // Create workbook
      this.createWorkbook(data);
      
      // Download file
      this.downloadFile();
      
      this.log('Export completed successfully');
      return true;
      
    } catch (error) {
      console.error('[Excel Export] Error:', error);
      alert('Gagal export Excel: ' + error.message);
      return false;
    }
  }

  /**
   * Collect all data from page
   */
  collectData() {
    this.log('Collecting data from page...');
    
    return {
      projectInfo: this.getProjectInfo(),
      tableData: this.getTableData(),
      summary: this.getSummaryData(),
      klasifikasi: this.getKlasifikasiSummary()
    };
  }

  /**
   * Get project info from data attributes and page
   */
  getProjectInfo() {
    const rekapApp = document.getElementById('rekap-app');
    
    const info = {
      projectName: rekapApp?.getAttribute('data-project-name') || 'Proyek',
      projectCode: rekapApp?.getAttribute('data-project-code') || '-',
      location: rekapApp?.getAttribute('data-project-location') || '-',
      year: rekapApp?.getAttribute('data-project-year') || new Date().getFullYear().toString(),
      owner: 'Dinas PUPR',
      sumberDana: 'APBD',
      tanggalCetak: this.formatDate(new Date())
    };

    // Try to get more info from page if available
    const titleEl = document.querySelector('h1, .ta-title, .project-title');
    if (titleEl && !info.projectName.includes('Proyek')) {
      info.projectName = titleEl.textContent.trim();
    }

    return info;
  }

  /**
   * Get table data rows
   */
  getTableData() {
    const table = document.getElementById('rekap-table');
    if (!table) {
      console.warn('Table #rekap-table not found');
      return [];
    }

    const rows = [];
    const tbody = table.querySelector('tbody');
    if (!tbody) return [];
    
    const trs = tbody.querySelectorAll('tr');
    
    trs.forEach(tr => {
      // Skip hidden rows
      const display = window.getComputedStyle(tr).display;
      if (display === 'none') return;
      
      const cells = tr.querySelectorAll('td');
      if (cells.length < 6) return;
      
      const level = tr.getAttribute('data-level') || '3';
      const nodeId = tr.getAttribute('data-node-id') || '';
      
      // Extract text, remove toggle icons
      const uraian = cells[0].textContent.trim().replace(/^[▼▶]\s*/, '');
      
      rows.push({
        level: parseInt(level),
        nodeId: nodeId,
        uraian: uraian,
        kode: cells[1].textContent.trim(),
        satuan: cells[2].textContent.trim(),
        volume: cells[3].textContent.trim(),
        harga: cells[4].textContent.trim(),
        total: cells[5].textContent.trim()
      });
    });
    
    this.log(`Collected ${rows.length} data rows`);
    return rows;
  }

  /**
   * Get summary data from tfoot
   */
  getSummaryData() {
    const tfoot = document.querySelector('#rekap-table tfoot');
    if (!tfoot) {
      console.warn('Table footer not found');
      return null;
    }

    // Get PPN input
    const ppnInput = tfoot.querySelector('#inp-ppn, input[type="number"]');
    const ppnPercent = ppnInput ? parseFloat(ppnInput.value) : 11;
    
    // Get rounding base
    const roundingSelect = tfoot.querySelector('#sel-rounding-base, select');
    const roundingBase = roundingSelect ? parseInt(roundingSelect.value) : 10000;
    
    // Extract total from tfoot cells
    const cells = Array.from(tfoot.querySelectorAll('th'));
    let totalD = 0;
    
    // Try to find the total cell (usually last cell or cell with 'text-end' class)
    const totalCell = cells.find(cell => 
      cell.classList.contains('text-end') ||
      cell.style.textAlign === 'right'
    ) || cells[cells.length - 1];
    
    if (totalCell) {
      const text = totalCell.textContent.replace(/[^0-9]/g, '');
      totalD = parseFloat(text) || 0;
    }
    
    // Calculate
    const ppn = totalD * (ppnPercent / 100);
    const grandTotal = totalD + ppn;
    const rounded = Math.round(grandTotal / roundingBase) * roundingBase;

    const summary = {
      totalD: Math.round(totalD),
      ppnPercent: ppnPercent,
      ppn: Math.round(ppn),
      grandTotal: Math.round(grandTotal),
      roundingBase: roundingBase,
      rounded: rounded
    };
    
    this.log(`Summary extracted: Total=${this.formatNumber(summary.totalD)}`);
    return summary;
  }

  /**
   * Get klasifikasi summary (level 1 only)
   */
  getKlasifikasiSummary() {
    const table = document.getElementById('rekap-table');
    if (!table) return [];

    const klasifikasi = [];
    const level1Rows = table.querySelectorAll('tbody tr[data-level="1"]');
    
    level1Rows.forEach((row, index) => {
      const cells = row.querySelectorAll('td');
      if (cells.length >= 6) {
        klasifikasi.push({
          no: index + 1,
          name: cells[0].textContent.trim().replace(/^[▼▶]\s*/, ''),
          total: cells[5].textContent.trim()
        });
      }
    });
    
    this.log(`Collected ${klasifikasi.length} klasifikasi items`);
    return klasifikasi;
  }

  /**
   * Create workbook with multiple sheets
   */
  createWorkbook(data) {
    this.log('Creating Excel workbook...');
    
    this.workbook = XLSX.utils.book_new();
    
    // Sheet 1: Main Report
    this.createMainSheet(data);
    
    // Sheet 2: Klasifikasi Summary
    if (data.klasifikasi && data.klasifikasi.length > 0) {
      this.createKlasifikasiSheet(data.klasifikasi);
    }
    
    // Sheet 3: Raw Data
    this.createRawDataSheet(data.tableData);
  }

  /**
   * Create main report sheet
   */
  createMainSheet(data) {
    const aoa = [];
    let row = 0;

    // TITLE SECTION
    aoa[row++] = ['REKAPITULASI'];
    aoa[row++] = ['RENCANA ANGGARAN BIAYA'];
    aoa[row++] = []; // Empty

    // PROJECT INFO
    aoa[row++] = ['Nama Proyek', ':', data.projectInfo.projectName];
    aoa[row++] = ['Kode Proyek', ':', data.projectInfo.projectCode];
    aoa[row++] = ['Pemilik Proyek', ':', data.projectInfo.owner];
    aoa[row++] = ['Lokasi', ':', data.projectInfo.location];
    aoa[row++] = ['Tahun Anggaran', ':', data.projectInfo.year];
    aoa[row++] = ['Sumber Dana', ':', data.projectInfo.sumberDana];
    aoa[row++] = ['Tanggal Cetak', ':', data.projectInfo.tanggalCetak];
    aoa[row++] = []; // Empty

    // TABLE HEADER
    const headerRow = row;
    aoa[row++] = ['Uraian', 'Kode AHSP', 'Satuan', 'Volume', 'Harga Satuan', 'Total Harga'];

    // TABLE DATA with indentation based on level
    data.tableData.forEach(item => {
      const uraian = this.getIndentedText(item.uraian, item.level);
      aoa[row++] = [
        uraian,
        item.kode,
        item.satuan,
        item.volume,
        item.harga,
        item.total
      ];
    });

    aoa[row++] = []; // Empty

    // SUMMARY
    if (data.summary) {
      aoa[row++] = ['Total Proyek (D)', '', '', '', '', this.formatNumber(data.summary.totalD)];
      aoa[row++] = [`PPN ${data.summary.ppnPercent}%`, '', '', '', '', this.formatNumber(data.summary.ppn)];
      aoa[row++] = ['Grand Total (D + PPN)', '', '', '', '', this.formatNumber(data.summary.grandTotal)];
      aoa[row++] = [`Pembulatan (${this.formatNumber(data.summary.roundingBase)})`, '', '', '', '', this.formatNumber(data.summary.rounded)];
    }

    // Create worksheet
    const ws = XLSX.utils.aoa_to_sheet(aoa);
    
    // Set column widths
    ws['!cols'] = [
      { wch: 45 },  // Uraian (wider for indentation)
      { wch: 12 },  // Kode
      { wch: 10 },  // Satuan
      { wch: 12 },  // Volume
      { wch: 18 },  // Harga Satuan
      { wch: 20 }   // Total
    ];
    
    // Add to workbook
    XLSX.utils.book_append_sheet(this.workbook, ws, 'Rekapitulasi RAB');
    this.log('Main sheet created');
  }

  /**
   * Create klasifikasi summary sheet
   */
  createKlasifikasiSheet(klasifikasi) {
    const aoa = [];
    
    // Title
    aoa[0] = ['RINGKASAN PER KLASIFIKASI'];
    aoa[1] = [];
    
    // Header
    aoa[2] = ['No', 'Klasifikasi', 'Total (Rp)'];
    
    // Data
    klasifikasi.forEach((item, index) => {
      aoa[3 + index] = [
        item.no,
        item.name,
        item.total
      ];
    });
    
    // Create worksheet
    const ws = XLSX.utils.aoa_to_sheet(aoa);
    
    // Set column widths
    ws['!cols'] = [
      { wch: 5 },   // No
      { wch: 50 },  // Klasifikasi
      { wch: 20 }   // Total
    ];
    
    XLSX.utils.book_append_sheet(this.workbook, ws, 'Ringkasan Klasifikasi');
    this.log('Klasifikasi sheet created');
  }

  /**
   * Create raw data sheet (CSV-like)
   */
  createRawDataSheet(tableData) {
    const aoa = [];
    
    // Header
    aoa[0] = ['Level', 'Uraian', 'Kode AHSP', 'Satuan', 'Volume', 'Harga Satuan', 'Total Harga'];
    
    // Data
    tableData.forEach((item, index) => {
      aoa[1 + index] = [
        item.level,
        item.uraian,
        item.kode,
        item.satuan,
        item.volume,
        item.harga,
        item.total
      ];
    });
    
    // Create worksheet
    const ws = XLSX.utils.aoa_to_sheet(aoa);
    
    // Set column widths
    ws['!cols'] = [
      { wch: 6 },   // Level
      { wch: 45 },  // Uraian
      { wch: 12 },  // Kode
      { wch: 10 },  // Satuan
      { wch: 12 },  // Volume
      { wch: 18 },  // Harga
      { wch: 20 }   // Total
    ];
    
    XLSX.utils.book_append_sheet(this.workbook, ws, 'Data Mentah');
    this.log('Raw data sheet created');
  }

  /**
   * Add indentation to text based on level
   */
  getIndentedText(text, level) {
    const indent = '  '.repeat(level - 1); // 2 spaces per level
    return indent + text;
  }

  /**
   * Format number with thousand separator
   */
  formatNumber(num) {
    if (!num && num !== 0) return '';
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, '.');
  }

  /**
   * Download the Excel file
   */
  downloadFile() {
    const filename = `Rekap_RAB_${this.projectId}_${this.formatDateFilename(new Date())}.xlsx`;
    
    XLSX.writeFile(this.workbook, filename);
    
    this.log(`File downloaded: ${filename}`);
  }

  /**
   * Format date for display
   */
  formatDate(date) {
    const months = [
      'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
      'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember'
    ];
    
    return `${date.getDate()} ${months[date.getMonth()]} ${date.getFullYear()}`;
  }

  /**
   * Format date for filename
   */
  formatDateFilename(date) {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}${m}${d}`;
  }
}

// Export to window for use in rekap_rab.js
window.RekapRABExcelExporter = RekapRABExcelExporter;

console.log('[Excel] RekapRABExcelExporter v1.0 loaded successfully');