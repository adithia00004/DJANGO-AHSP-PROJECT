/**
 * Excel Generator - Native Excel Export
 * Generate Excel (.xlsx) files dengan ExcelJS
 * 3 Sheets: Cover, Kurva S (data table with formulas), Input Progress-Gantt (SSOT for input values)
 *
 * NOTE: ExcelJS does not support native Excel charts. Data is provided in summary rows
 * (Kumulatif Rencana, Kumulatif Realisasi) so users can create charts manually in Excel.
 *
 * @module export/generators/excel-generator
 */

import ExcelJS from 'exceljs';

// ============================================================================
// STYLE CONSTANTS
// ============================================================================

const COLORS = {
  PLANNED_BG: 'FF00CED1',    // Cyan/Turquoise for Planned
  ACTUAL_BG: 'FF34A853',     // Green for Actual
  HEADER_BG: 'FF2D5A8E',     // Dark blue for headers
  HEADER_TEXT: 'FFFFFFFF',   // White text
  SUBHEADER_BG: 'FFE8F0FE',  // Light blue for sub-headers
  KLASIFIKASI_BG: 'FFD9E8FB', // Light blue for klasifikasi
  SUB_KLASIFIKASI_BG: 'FFF0F4F8', // Light gray for sub-klasifikasi
  WHITE: 'FFFFFFFF',
  BLACK: 'FF000000',
  BORDER: 'FF999999',
  PRIMARY: 'FF2D5A8E',
  POSITIVE: 'FF22C55E',      // Green for positive deviation
  NEGATIVE: 'FFEF4444',      // Red for negative deviation
  NEUTRAL: 'FFEAB308',       // Yellow for zero deviation
  TOTAL_BG: 'FFFCE7F3'       // Light pink for total row
};

const FONTS = {
  TITLE: { size: 18, bold: true, name: 'Arial', color: { argb: COLORS.PRIMARY } },
  SUBTITLE: { size: 14, bold: true, name: 'Arial', color: { argb: COLORS.PRIMARY } },
  HEADER: { size: 9, bold: true, name: 'Arial', color: { argb: COLORS.HEADER_TEXT } },
  NORMAL: { size: 9, name: 'Arial' },
  SMALL: { size: 8, name: 'Arial' },
  LABEL: { size: 9, bold: true, name: 'Arial' }
};

/**
 * Get thin border style
 */
function getThinBorder() {
  const thin = { style: 'thin', color: { argb: COLORS.BORDER } };
  return { top: thin, left: thin, bottom: thin, right: thin };
}

/**
 * Format number as Indonesian Rupiah
 */
function formatRupiah(value) {
  if (!value || isNaN(value)) return 'Rp 0';
  return `Rp ${Number(value).toLocaleString('id-ID')}`;
}

/**
 * Get column letter from index (1-based)
 */
function getColLetter(colIndex) {
  let letter = '';
  while (colIndex > 0) {
    const remainder = (colIndex - 1) % 26;
    letter = String.fromCharCode(65 + remainder) + letter;
    colIndex = Math.floor((colIndex - 1) / 26);
  }
  return letter;
}

// ============================================================================
// MAIN EXPORT FUNCTION
// ============================================================================

/**
 * Generate Native Excel file with 3 sheets
 */
export async function generateExcel(config) {
  const {
    reportType = 'rekap',
    rows = [],
    timeColumns = [],
    planned = null,
    actual = null,
    projectName = 'Laporan',
    projectInfo = {}
  } = config;

  console.log('[ExcelGenerator] Generating Native Excel:', {
    reportType,
    rowsCount: rows.length,
    weeksCount: timeColumns.length,
    sampleRow: rows[0] ? {
      type: rows[0].type,
      volume: rows[0].volume,
      hargaSatuan: rows[0].hargaSatuan,
      totalHarga: rows[0].totalHarga
    } : null
  });

  // Create workbook
  const workbook = new ExcelJS.Workbook();
  workbook.creator = 'AHSP Export System';
  workbook.created = new Date();

  // Calculate total harga for bobot calculation
  let totalHargaProject = 0;

  rows.forEach(item => {
    if (item.type === 'pekerjaan') {
      const harga = item.totalHarga || item.total_harga || item.harga ||
        (item.volume && item.hargaSatuan ? item.volume * item.hargaSatuan : 0);
      totalHargaProject += harga;
    }
  });

  console.log('[ExcelGenerator] Total Harga Project:', totalHargaProject);

  // Build sheets in order:
  // 1. Input Progress-Gantt FIRST (SSOT for input progress values)
  const ganttRanges = buildGridGanttSheet(workbook, rows, timeColumns, planned, actual, totalHargaProject);

  // 2. Kurva S (references Input Progress-Gantt for week cells)
  const kurvaSRanges = buildKurvaSSheet(workbook, rows, timeColumns, planned, actual, totalHargaProject, ganttRanges);

  // 3. Cover sheet (references Kurva S for summary)
  buildCoverSheet(workbook, config, kurvaSRanges, totalHargaProject);

  // Reorder sheets: Cover should be first
  const coverSheet = workbook.getWorksheet('Cover');
  const kurvaSSheet = workbook.getWorksheet('Kurva S');
  const gridSheet = workbook.getWorksheet('Input Progress-Gantt');

  if (coverSheet) coverSheet.orderNo = 0;
  if (kurvaSSheet) kurvaSSheet.orderNo = 1;
  if (gridSheet) gridSheet.orderNo = 2;

  // Generate Excel buffer
  const buffer = await workbook.xlsx.writeBuffer();

  // Convert to Blob
  const blob = new Blob([buffer], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  });

  console.log('[ExcelGenerator] Excel file generated:', {
    size: blob.size,
    sheetCount: workbook.worksheets.length
  });

  return {
    blob,
    metadata: {
      reportType,
      format: 'xlsx',
      sheetCount: workbook.worksheets.length,
      size: blob.size,
      generatedAt: new Date().toISOString()
    }
  };
}

// ============================================================================
// SHEET 3: INPUT PROGRESS-GANTT (Built FIRST - SSOT for input progress)
// ============================================================================

function buildGridGanttSheet(workbook, rows, timeColumns, planned, actual, totalHargaProject) {
  const ws = workbook.addWorksheet('Input Progress-Gantt');

  const ganttRanges = {
    pekerjaanRows: [],
    weekStartCol: 4,
    headerRow: 1
  };

  if (!rows || rows.length === 0) {
    ws.getCell('A1').value = 'Tidak ada data pekerjaan';
    return ganttRanges;
  }

  const fixedCols = 3;
  const weekStartCol = fixedCols + 1;
  const weekCount = timeColumns.length;
  const totalCol = weekStartCol + weekCount;

  ganttRanges.weekStartCol = weekStartCol;

  ws.getColumn(1).width = 8;
  ws.getColumn(2).width = 40;
  ws.getColumn(3).width = 10;
  for (let i = weekStartCol; i <= totalCol; i++) {
    ws.getColumn(i).width = 8;
  }

  const headerRow = 1;
  ganttRanges.headerRow = headerRow;

  const headerData = ['No', 'Uraian Pekerjaan', 'Bobot'];
  timeColumns.forEach(col => {
    headerData.push(col.label || `W${col.week}`);
  });
  headerData.push('Total');

  headerData.forEach((header, idx) => {
    const cell = ws.getCell(headerRow, idx + 1);
    cell.value = header;
    cell.font = FONTS.HEADER;
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_BG } };
    cell.border = getThinBorder();
    cell.alignment = { horizontal: 'center', vertical: 'middle' };
  });

  ws.views = [{ state: 'frozen', xSplit: fixedCols, ySplit: 1 }];

  let currentRow = 2;
  let pekerjaanCounter = 0;

  rows.forEach((item) => {
    const isPekerjaan = item.type === 'pekerjaan';
    const isKlasifikasi = item.type === 'klasifikasi';
    const isSubKlasifikasi = item.type === 'sub-klasifikasi' || item.type === 'sub_klasifikasi';

    if (isPekerjaan) {
      pekerjaanCounter++;
      const plannedRowNum = currentRow;
      const actualRowNum = currentRow + 1;

      ganttRanges.pekerjaanRows.push({
        id: item.id,
        plannedRow: plannedRowNum,
        actualRow: actualRowNum
      });

      ws.mergeCells(plannedRowNum, 1, actualRowNum, 1);
      ws.mergeCells(plannedRowNum, 2, actualRowNum, 2);
      ws.mergeCells(plannedRowNum, 3, actualRowNum, 3);

      ws.getCell(plannedRowNum, 1).value = item.code || item.kode || pekerjaanCounter;
      ws.getCell(plannedRowNum, 1).alignment = { horizontal: 'center', vertical: 'middle' };
      ws.getCell(plannedRowNum, 1).border = getThinBorder();

      ws.getCell(plannedRowNum, 2).value = item.name || item.uraian || '';
      ws.getCell(plannedRowNum, 2).alignment = { vertical: 'middle', wrapText: true };
      ws.getCell(plannedRowNum, 2).border = getThinBorder();

      const totalHarga = item.totalHarga || item.total_harga || (item.volume * (item.hargaSatuan || 0)) || 0;
      const bobot = totalHargaProject > 0 ? totalHarga / totalHargaProject : 0;
      ws.getCell(plannedRowNum, 3).value = bobot;
      ws.getCell(plannedRowNum, 3).numFmt = '0.00%';
      ws.getCell(plannedRowNum, 3).alignment = { horizontal: 'center', vertical: 'middle' };
      ws.getCell(plannedRowNum, 3).border = getThinBorder();

      timeColumns.forEach((col, weekIdx) => {
        const colNum = weekStartCol + weekIdx;
        const weekKey = col.week || col.fieldId || weekIdx + 1;
        const plannedValue = planned?.[item.id]?.[weekKey] || 0;

        const cell = ws.getCell(plannedRowNum, colNum);
        cell.value = plannedValue > 0 ? plannedValue / 100 : 0;
        cell.numFmt = '0.0%';
        if (plannedValue > 0) {
          cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.PLANNED_BG } };
        }
        cell.border = getThinBorder();
        cell.alignment = { horizontal: 'center' };
        cell.font = FONTS.SMALL;
      });

      timeColumns.forEach((col, weekIdx) => {
        const colNum = weekStartCol + weekIdx;
        const weekKey = col.week || col.fieldId || weekIdx + 1;
        const actualValue = actual?.[item.id]?.[weekKey] || 0;

        const cell = ws.getCell(actualRowNum, colNum);
        cell.value = actualValue > 0 ? actualValue / 100 : 0;
        cell.numFmt = '0.0%';
        if (actualValue > 0) {
          cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ACTUAL_BG } };
        }
        cell.border = getThinBorder();
        cell.alignment = { horizontal: 'center' };
        cell.font = FONTS.SMALL;
      });

      ws.mergeCells(plannedRowNum, totalCol, actualRowNum, totalCol);
      const firstWeekLetter = getColLetter(weekStartCol);
      const lastWeekLetter = getColLetter(weekStartCol + weekCount - 1);
      ws.getCell(plannedRowNum, totalCol).value = {
        formula: `SUM(${firstWeekLetter}${plannedRowNum}:${lastWeekLetter}${plannedRowNum})+SUM(${firstWeekLetter}${actualRowNum}:${lastWeekLetter}${actualRowNum})`
      };
      ws.getCell(plannedRowNum, totalCol).numFmt = '0.0%';
      ws.getCell(plannedRowNum, totalCol).alignment = { horizontal: 'center', vertical: 'middle' };
      ws.getCell(plannedRowNum, totalCol).border = getThinBorder();

      ws.getCell(actualRowNum, 1).border = getThinBorder();
      ws.getCell(actualRowNum, 2).border = getThinBorder();
      ws.getCell(actualRowNum, 3).border = getThinBorder();
      ws.getCell(actualRowNum, totalCol).border = getThinBorder();

      currentRow += 2;

    } else {
      ws.mergeCells(currentRow, 2, currentRow, totalCol);

      ws.getCell(currentRow, 2).value = item.name || item.uraian || '';
      ws.getCell(currentRow, 2).font = { ...FONTS.NORMAL, bold: true };
      ws.getCell(currentRow, 2).border = getThinBorder();

      if (isKlasifikasi) {
        ws.getCell(currentRow, 2).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.KLASIFIKASI_BG } };
      } else if (isSubKlasifikasi) {
        ws.getCell(currentRow, 2).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUB_KLASIFIKASI_BG } };
        ws.getCell(currentRow, 2).alignment = { indent: 2 };
      }

      ws.getCell(currentRow, 1).border = getThinBorder();

      currentRow++;
    }
  });

  console.log('[ExcelGenerator] Grid-Gantt sheet created with', ganttRanges.pekerjaanRows.length, 'pekerjaan');
  return ganttRanges;
}

// ============================================================================
// SHEET 1: COVER
// ============================================================================

function buildCoverSheet(workbook, config, kurvaSRanges, totalHargaProject) {
  const ws = workbook.addWorksheet('Cover');
  const { projectName = 'Nama Proyek', projectInfo = {}, rows = [] } = config;

  const lokasi = projectInfo.lokasi || projectInfo.projectLocation || '-';
  const pemilik = projectInfo.nama_client || projectInfo.pemilik || projectInfo.projectOwner || '-';
  const sumberDana = projectInfo.sumber_dana || '-';
  const anggaran = totalHargaProject || projectInfo.anggaran || 0;

  ws.getColumn('A').width = 8;
  ws.getColumn('B').width = 25;
  ws.getColumn('C').width = 5;
  ws.getColumn('D').width = 45;
  ws.getColumn('E').width = 8;

  const titleRow = 6;
  ws.mergeCells(`B${titleRow}:D${titleRow}`);
  ws.getCell(`B${titleRow}`).value = 'LAPORAN REKAPITULASI';
  ws.getCell(`B${titleRow}`).font = FONTS.TITLE;
  ws.getCell(`B${titleRow}`).alignment = { horizontal: 'center', vertical: 'middle' };

  ws.mergeCells(`B${titleRow + 1}:D${titleRow + 1}`);
  ws.getCell(`B${titleRow + 1}`).value = 'JADWAL PEKERJAAN';
  ws.getCell(`B${titleRow + 1}`).font = { ...FONTS.SUBTITLE, size: 14 };
  ws.getCell(`B${titleRow + 1}`).alignment = { horizontal: 'center', vertical: 'middle' };

  ws.mergeCells(`B${titleRow + 3}:D${titleRow + 3}`);
  ws.getCell(`B${titleRow + 3}`).value = '────────────────────────────────────';
  ws.getCell(`B${titleRow + 3}`).font = { size: 8, color: { argb: COLORS.PRIMARY } };
  ws.getCell(`B${titleRow + 3}`).alignment = { horizontal: 'center' };

  ws.mergeCells(`B${titleRow + 5}:D${titleRow + 5}`);
  ws.getCell(`B${titleRow + 5}`).value = projectName;
  ws.getCell(`B${titleRow + 5}`).font = { size: 16, bold: true, name: 'Arial' };
  ws.getCell(`B${titleRow + 5}`).alignment = { horizontal: 'center', vertical: 'middle' };

  const detailsStartRow = titleRow + 8;
  const details = [
    ['Lokasi', lokasi],
    ['Pemilik', pemilik],
    ['Sumber Dana', sumberDana],
    ['Anggaran', formatRupiah(anggaran)],
    ['Tanggal Export', new Date().toLocaleDateString('id-ID')],
    ['Jumlah Pekerjaan', `${rows.filter(r => r.type === 'pekerjaan').length} item`]
  ];

  details.forEach((item, idx) => {
    const row = detailsStartRow + idx;
    ws.getCell(`B${row}`).value = item[0];
    ws.getCell(`B${row}`).font = FONTS.LABEL;
    ws.getCell(`B${row}`).alignment = { horizontal: 'right' };

    ws.getCell(`C${row}`).value = ':';
    ws.getCell(`C${row}`).alignment = { horizontal: 'center' };

    ws.getCell(`D${row}`).value = item[1];
    ws.getCell(`D${row}`).font = FONTS.NORMAL;
  });

  const summaryStartRow = detailsStartRow + 8;
  ws.mergeCells(`B${summaryStartRow}:D${summaryStartRow}`);
  ws.getCell(`B${summaryStartRow}`).value = 'RINGKASAN PROGRESS';
  ws.getCell(`B${summaryStartRow}`).font = FONTS.SUBTITLE;
  ws.getCell(`B${summaryStartRow}`).alignment = { horizontal: 'center' };
  ws.getCell(`B${summaryStartRow}`).fill = {
    type: 'pattern',
    pattern: 'solid',
    fgColor: { argb: COLORS.SUBHEADER_BG }
  };

  const summaryData = [
    ['Progress Rencana', kurvaSRanges.finalPlannedFormula],
    ['Progress Realisasi', kurvaSRanges.finalActualFormula],
    ['Deviasi', kurvaSRanges.deviationFormula]
  ];

  summaryData.forEach((item, idx) => {
    const row = summaryStartRow + 2 + idx;
    ws.getCell(`B${row}`).value = item[0];
    ws.getCell(`B${row}`).font = FONTS.LABEL;
    ws.getCell(`B${row}`).alignment = { horizontal: 'right' };
    ws.getCell(`B${row}`).border = getThinBorder();

    ws.getCell(`C${row}`).value = ':';
    ws.getCell(`C${row}`).alignment = { horizontal: 'center' };
    ws.getCell(`C${row}`).border = getThinBorder();

    ws.getCell(`D${row}`).value = { formula: item[1] };
    ws.getCell(`D${row}`).numFmt = '0.00%';
    ws.getCell(`D${row}`).border = getThinBorder();
    ws.getCell(`D${row}`).font = FONTS.NORMAL;
  });

  // Note about chart
  const noteRow = summaryStartRow + 7;
  ws.mergeCells(`B${noteRow}:D${noteRow}`);
  ws.getCell(`B${noteRow}`).value = 'Catatan: Untuk membuat grafik Kurva S, gunakan data "Kumulatif Rencana" dan "Kumulatif Realisasi" pada sheet "Kurva S"';
  ws.getCell(`B${noteRow}`).font = { ...FONTS.SMALL, italic: true };
  ws.getCell(`B${noteRow}`).alignment = { horizontal: 'center', wrapText: true };

  console.log('[ExcelGenerator] Cover sheet created');
  return ws;
}

// ============================================================================
// SHEET 2: KURVA S (Data table with formulas - no chart)
// ============================================================================

function buildKurvaSSheet(workbook, rows, timeColumns, planned, actual, totalHargaProject, ganttRanges) {
  const ws = workbook.addWorksheet('Kurva S');

  if (!rows || rows.length === 0 || !timeColumns || timeColumns.length === 0) {
    ws.getCell('A1').value = 'Tidak ada data';
    return {
      finalPlannedFormula: '"0%"',
      finalActualFormula: '"0%"',
      deviationFormula: '"0%"'
    };
  }

  const fixedColCount = 7;
  const weekStartCol = fixedColCount + 1;
  const weekCount = timeColumns.length;
  const totalCol = weekStartCol + weekCount;

  ws.getColumn(1).width = 8;
  ws.getColumn(2).width = 35;
  ws.getColumn(3).width = 10;
  ws.getColumn(4).width = 10;
  ws.getColumn(5).width = 14;
  ws.getColumn(6).width = 14;
  ws.getColumn(7).width = 8;
  for (let i = weekStartCol; i <= totalCol; i++) {
    ws.getColumn(i).width = 7;
  }

  ws.mergeCells('A1:' + getColLetter(totalCol) + '1');
  ws.getCell('A1').value = 'KURVA S - RINCIAN PROGRESS';
  ws.getCell('A1').font = FONTS.SUBTITLE;
  ws.getCell('A1').alignment = { horizontal: 'center' };

  const headerRow = 3;
  const headers = ['No', 'Uraian Pekerjaan', 'Volume', 'Satuan', 'Harga Satuan', 'Total Harga', 'Bobot'];
  timeColumns.forEach(col => {
    headers.push(col.label || `W${col.week}`);
  });
  headers.push('Total');

  headers.forEach((header, idx) => {
    const cell = ws.getCell(headerRow, idx + 1);
    cell.value = header;
    cell.font = FONTS.HEADER;
    cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.HEADER_BG } };
    cell.border = getThinBorder();
    cell.alignment = { horizontal: 'center', vertical: 'middle', wrapText: true };
  });
  ws.getRow(headerRow).height = 30;

  ws.views = [{ state: 'frozen', xSplit: 2, ySplit: headerRow }];

  let currentRow = headerRow + 1;
  let pekerjaanCounter = 0;
  const pekerjaanRowData = [];
  const totalHargaColLetter = getColLetter(6);

  const ganttRowMap = {};
  ganttRanges.pekerjaanRows.forEach(r => {
    ganttRowMap[r.id] = r;
  });

  rows.forEach((item) => {
    const isPekerjaan = item.type === 'pekerjaan';
    const isKlasifikasi = item.type === 'klasifikasi';
    const isSubKlasifikasi = item.type === 'sub-klasifikasi' || item.type === 'sub_klasifikasi';

    if (isPekerjaan) {
      pekerjaanCounter++;
      const plannedRowNum = currentRow;
      const actualRowNum = currentRow + 1;

      pekerjaanRowData.push({
        planned: plannedRowNum,
        actual: actualRowNum,
        id: item.id
      });

      for (let c = 1; c <= fixedColCount; c++) {
        ws.mergeCells(plannedRowNum, c, actualRowNum, c);
      }

      ws.getCell(plannedRowNum, 1).value = item.code || item.kode || pekerjaanCounter;
      ws.getCell(plannedRowNum, 1).alignment = { horizontal: 'center', vertical: 'middle' };
      ws.getCell(plannedRowNum, 1).border = getThinBorder();
      ws.getCell(plannedRowNum, 1).font = FONTS.SMALL;

      ws.getCell(plannedRowNum, 2).value = item.name || item.uraian || '';
      ws.getCell(plannedRowNum, 2).alignment = { vertical: 'middle', wrapText: true };
      ws.getCell(plannedRowNum, 2).border = getThinBorder();
      ws.getCell(plannedRowNum, 2).font = FONTS.SMALL;

      const volume = item.volume || 0;
      ws.getCell(plannedRowNum, 3).value = volume;
      ws.getCell(plannedRowNum, 3).numFmt = '#,##0.00';
      ws.getCell(plannedRowNum, 3).alignment = { horizontal: 'right', vertical: 'middle' };
      ws.getCell(plannedRowNum, 3).border = getThinBorder();
      ws.getCell(plannedRowNum, 3).font = FONTS.SMALL;

      ws.getCell(plannedRowNum, 4).value = item.satuan || '-';
      ws.getCell(plannedRowNum, 4).alignment = { horizontal: 'center', vertical: 'middle' };
      ws.getCell(plannedRowNum, 4).border = getThinBorder();
      ws.getCell(plannedRowNum, 4).font = FONTS.SMALL;

      const hargaSatuan = item.hargaSatuan || item.harga_satuan || 0;
      ws.getCell(plannedRowNum, 5).value = hargaSatuan;
      ws.getCell(plannedRowNum, 5).numFmt = '#,##0';
      ws.getCell(plannedRowNum, 5).alignment = { horizontal: 'right', vertical: 'middle' };
      ws.getCell(plannedRowNum, 5).border = getThinBorder();
      ws.getCell(plannedRowNum, 5).font = FONTS.SMALL;

      const volCellRef = getColLetter(3) + plannedRowNum;
      const hargaCellRef = getColLetter(5) + plannedRowNum;

      ws.getCell(plannedRowNum, 6).value = { formula: `${volCellRef}*${hargaCellRef}` };
      ws.getCell(plannedRowNum, 6).numFmt = '#,##0';
      ws.getCell(plannedRowNum, 6).alignment = { horizontal: 'right', vertical: 'middle' };
      ws.getCell(plannedRowNum, 6).border = getThinBorder();
      ws.getCell(plannedRowNum, 6).font = FONTS.SMALL;

      ws.getCell(plannedRowNum, 7).value = 0;
      ws.getCell(plannedRowNum, 7).numFmt = '0.00%';
      ws.getCell(plannedRowNum, 7).alignment = { horizontal: 'center', vertical: 'middle' };
      ws.getCell(plannedRowNum, 7).border = getThinBorder();
      ws.getCell(plannedRowNum, 7).font = FONTS.SMALL;

      const ganttRow = ganttRowMap[item.id];
      const bobotCellRef = '$' + getColLetter(7) + '$' + plannedRowNum;

      timeColumns.forEach((col, weekIdx) => {
        const colNum = weekStartCol + weekIdx;
        const ganttWeekCol = ganttRanges.weekStartCol + weekIdx;
        const ganttColLetter = getColLetter(ganttWeekCol);

        const cell = ws.getCell(plannedRowNum, colNum);

        if (ganttRow) {
          const ganttCellRef = `'Input Progress-Gantt'!${ganttColLetter}${ganttRow.plannedRow}`;
          cell.value = { formula: `${bobotCellRef}*${ganttCellRef}` };
          cell.numFmt = '0.00%';

          const weekKey = col.week || col.fieldId || weekIdx + 1;
          const plannedValue = planned?.[item.id]?.[weekKey] || 0;
          if (plannedValue > 0) {
            cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.PLANNED_BG } };
          }
        }
        cell.border = getThinBorder();
        cell.alignment = { horizontal: 'center' };
        cell.font = FONTS.SMALL;
      });

      timeColumns.forEach((col, weekIdx) => {
        const colNum = weekStartCol + weekIdx;
        const ganttWeekCol = ganttRanges.weekStartCol + weekIdx;
        const ganttColLetter = getColLetter(ganttWeekCol);

        const cell = ws.getCell(actualRowNum, colNum);

        if (ganttRow) {
          const ganttCellRef = `'Input Progress-Gantt'!${ganttColLetter}${ganttRow.actualRow}`;
          cell.value = { formula: `${bobotCellRef}*${ganttCellRef}` };
          cell.numFmt = '0.00%';

          const weekKey = col.week || col.fieldId || weekIdx + 1;
          const actualValue = actual?.[item.id]?.[weekKey] || 0;
          if (actualValue > 0) {
            cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ACTUAL_BG } };
          }
        }
        cell.border = getThinBorder();
        cell.alignment = { horizontal: 'center' };
        cell.font = FONTS.SMALL;
      });

      ws.mergeCells(plannedRowNum, totalCol, actualRowNum, totalCol);
      const firstWeekLetter = getColLetter(weekStartCol);
      const lastWeekLetter = getColLetter(weekStartCol + weekCount - 1);
      ws.getCell(plannedRowNum, totalCol).value = {
        formula: `SUM(${firstWeekLetter}${plannedRowNum}:${lastWeekLetter}${plannedRowNum})+SUM(${firstWeekLetter}${actualRowNum}:${lastWeekLetter}${actualRowNum})`
      };
      ws.getCell(plannedRowNum, totalCol).numFmt = '0.00%';
      ws.getCell(plannedRowNum, totalCol).alignment = { horizontal: 'center', vertical: 'middle' };
      ws.getCell(plannedRowNum, totalCol).border = getThinBorder();
      ws.getCell(plannedRowNum, totalCol).font = FONTS.SMALL;

      for (let c = 1; c <= 7; c++) {
        ws.getCell(actualRowNum, c).border = getThinBorder();
      }

      currentRow += 2;

    } else {
      ws.mergeCells(currentRow, 2, currentRow, totalCol);

      ws.getCell(currentRow, 2).value = item.name || item.uraian || '';
      ws.getCell(currentRow, 2).font = { ...FONTS.NORMAL, bold: true };
      ws.getCell(currentRow, 2).border = getThinBorder();

      if (isKlasifikasi) {
        ws.getCell(currentRow, 2).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.KLASIFIKASI_BG } };
      } else if (isSubKlasifikasi) {
        ws.getCell(currentRow, 2).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.SUB_KLASIFIKASI_BG } };
        ws.getCell(currentRow, 2).alignment = { indent: 2 };
      }

      ws.getCell(currentRow, 1).border = getThinBorder();

      currentRow++;
    }
  });

  // TOTAL ROW
  const totalRowNum = currentRow + 1;

  ws.getCell(totalRowNum, 2).value = 'TOTAL';
  ws.getCell(totalRowNum, 2).font = { ...FONTS.NORMAL, bold: true };
  ws.getCell(totalRowNum, 2).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_BG } };
  ws.getCell(totalRowNum, 2).border = getThinBorder();

  const totalHargaSumFormulas = pekerjaanRowData.map(p => `${totalHargaColLetter}${p.planned}`).join('+');
  ws.getCell(totalRowNum, 6).value = { formula: totalHargaSumFormulas || '0' };
  ws.getCell(totalRowNum, 6).numFmt = '#,##0';
  ws.getCell(totalRowNum, 6).font = { ...FONTS.NORMAL, bold: true };
  ws.getCell(totalRowNum, 6).border = getThinBorder();

  const bobotColLetter = getColLetter(7);
  const bobotSumFormula = pekerjaanRowData.map(p => `${bobotColLetter}${p.planned}`).join('+');
  ws.getCell(totalRowNum, 7).value = { formula: bobotSumFormula || '0' };
  ws.getCell(totalRowNum, 7).numFmt = '0.00%';
  ws.getCell(totalRowNum, 7).font = { ...FONTS.NORMAL, bold: true };
  ws.getCell(totalRowNum, 7).border = getThinBorder();

  for (let c = 1; c <= totalCol; c++) {
    ws.getCell(totalRowNum, c).border = getThinBorder();
    if (c >= weekStartCol && c < totalCol) {
      ws.getCell(totalRowNum, c).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.TOTAL_BG } };
    }
  }

  // Update Bobot formulas
  const totalHargaSumRef = '$' + totalHargaColLetter + '$' + totalRowNum;
  pekerjaanRowData.forEach(p => {
    const bobotCell = ws.getCell(p.planned, 7);
    const thisHargaRef = totalHargaColLetter + p.planned;
    bobotCell.value = { formula: `IF(${totalHargaSumRef}=0,0,${thisHargaRef}/${totalHargaSumRef})` };
  });

  // SUMMARY ROWS (data source for manual chart creation)
  const summaryStartRow = totalRowNum + 2;

  // Note about chart data
  ws.mergeCells(`A${summaryStartRow}:${getColLetter(fixedColCount)}${summaryStartRow}`);
  ws.getCell(`A${summaryStartRow}`).value = 'DATA UNTUK GRAFIK KURVA S (buat chart manual dari data di bawah):';
  ws.getCell(`A${summaryStartRow}`).font = { ...FONTS.NORMAL, bold: true, italic: true };

  const dataStartRow = summaryStartRow + 1;

  ws.getCell(dataStartRow, 2).value = 'Progress Mingguan Rencana';
  ws.getCell(dataStartRow, 2).font = { ...FONTS.NORMAL, bold: true };
  ws.getCell(dataStartRow, 2).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.PLANNED_BG } };
  ws.getCell(dataStartRow, 2).border = getThinBorder();

  timeColumns.forEach((col, weekIdx) => {
    const colNum = weekStartCol + weekIdx;
    const colLetter = getColLetter(colNum);
    const cellRefs = pekerjaanRowData.map(p => `${colLetter}${p.planned}`).join('+');
    ws.getCell(dataStartRow, colNum).value = { formula: cellRefs || '0' };
    ws.getCell(dataStartRow, colNum).numFmt = '0.00%';
    ws.getCell(dataStartRow, colNum).border = getThinBorder();
    ws.getCell(dataStartRow, colNum).font = FONTS.SMALL;
  });

  ws.getCell(dataStartRow + 1, 2).value = 'Progress Mingguan Realisasi';
  ws.getCell(dataStartRow + 1, 2).font = { ...FONTS.NORMAL, bold: true };
  ws.getCell(dataStartRow + 1, 2).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ACTUAL_BG } };
  ws.getCell(dataStartRow + 1, 2).border = getThinBorder();

  timeColumns.forEach((col, weekIdx) => {
    const colNum = weekStartCol + weekIdx;
    const colLetter = getColLetter(colNum);
    const cellRefs = pekerjaanRowData.map(p => `${colLetter}${p.actual}`).join('+');
    ws.getCell(dataStartRow + 1, colNum).value = { formula: cellRefs || '0' };
    ws.getCell(dataStartRow + 1, colNum).numFmt = '0.00%';
    ws.getCell(dataStartRow + 1, colNum).border = getThinBorder();
    ws.getCell(dataStartRow + 1, colNum).font = FONTS.SMALL;
  });

  ws.getCell(dataStartRow + 2, 2).value = 'Kumulatif Rencana';
  ws.getCell(dataStartRow + 2, 2).font = { ...FONTS.NORMAL, bold: true };
  ws.getCell(dataStartRow + 2, 2).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.PLANNED_BG } };
  ws.getCell(dataStartRow + 2, 2).border = getThinBorder();

  timeColumns.forEach((col, weekIdx) => {
    const colNum = weekStartCol + weekIdx;
    const colLetter = getColLetter(colNum);

    if (weekIdx === 0) {
      ws.getCell(dataStartRow + 2, colNum).value = { formula: `${colLetter}${dataStartRow}` };
    } else {
      const prevColLetter = getColLetter(colNum - 1);
      ws.getCell(dataStartRow + 2, colNum).value = {
        formula: `${prevColLetter}${dataStartRow + 2}+${colLetter}${dataStartRow}`
      };
    }
    ws.getCell(dataStartRow + 2, colNum).numFmt = '0.00%';
    ws.getCell(dataStartRow + 2, colNum).border = getThinBorder();
    ws.getCell(dataStartRow + 2, colNum).font = FONTS.SMALL;
  });

  ws.getCell(dataStartRow + 3, 2).value = 'Kumulatif Realisasi';
  ws.getCell(dataStartRow + 3, 2).font = { ...FONTS.NORMAL, bold: true };
  ws.getCell(dataStartRow + 3, 2).fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: COLORS.ACTUAL_BG } };
  ws.getCell(dataStartRow + 3, 2).border = getThinBorder();

  timeColumns.forEach((col, weekIdx) => {
    const colNum = weekStartCol + weekIdx;
    const colLetter = getColLetter(colNum);

    if (weekIdx === 0) {
      ws.getCell(dataStartRow + 3, colNum).value = { formula: `${colLetter}${dataStartRow + 1}` };
    } else {
      const prevColLetter = getColLetter(colNum - 1);
      ws.getCell(dataStartRow + 3, colNum).value = {
        formula: `${prevColLetter}${dataStartRow + 3}+${colLetter}${dataStartRow + 1}`
      };
    }
    ws.getCell(dataStartRow + 3, colNum).numFmt = '0.00%';
    ws.getCell(dataStartRow + 3, colNum).border = getThinBorder();
    ws.getCell(dataStartRow + 3, colNum).font = FONTS.SMALL;
  });

  // Calculate final cumulative cell addresses
  const lastWeekColLetter = getColLetter(weekStartCol + weekCount - 1);
  const finalPlannedCell = `${lastWeekColLetter}${dataStartRow + 2}`;
  const finalActualCell = `${lastWeekColLetter}${dataStartRow + 3}`;

  console.log('[ExcelGenerator] Kurva S sheet created with', pekerjaanRowData.length, 'pekerjaan items');

  return {
    finalPlannedFormula: `'Kurva S'!${finalPlannedCell}`,
    finalActualFormula: `'Kurva S'!${finalActualCell}`,
    deviationFormula: `'Kurva S'!${finalActualCell}-'Kurva S'!${finalPlannedCell}`,
    dataStartRow,
    totalCol,
    totalRowNum
  };
}

// ============================================================================
// DOWNLOAD HELPER
// ============================================================================

export function downloadExcel(blob, filename = 'export') {
  if (!blob || !(blob instanceof Blob)) {
    console.error('[ExcelGenerator] Invalid blob:', blob);
    throw new Error('Invalid blob provided to downloadExcel');
  }

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `${filename}.xlsx`;
  document.body.appendChild(a);
  a.click();

  setTimeout(() => {
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    console.log('[ExcelGenerator] File downloaded:', `${filename}.xlsx`);
  }, 100);
}
