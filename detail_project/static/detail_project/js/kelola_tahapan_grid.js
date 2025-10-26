// static/detail_project/js/kelola_tahapan_grid.js
// Excel-like Grid View for Project Scheduling with Gantt & S-Curve

(function() {
  'use strict';

  // =========================================================================
  // CONFIGURATION & STATE
  // =========================================================================

  const app = document.getElementById('tahapan-grid-app');
  if (!app) return;

  const projectId = parseInt(app.dataset.projectId);
  const apiBase = app.dataset.apiBase;

  // State Management
  const state = {
    tahapanList: [],           // List of tahapan with dates
    pekerjaanTree: [],         // Hierarchical tree: Klasifikasi > Sub > Pekerjaan
    flatPekerjaan: [],         // Flattened list for easy access
    volumeMap: new Map(),      // pekerjaan_id -> volume
    assignmentMap: new Map(),  // pekerjaan_id -> { tahapan_id: percentage }

    timeScale: 'weekly',       // 'daily', 'weekly', 'monthly', 'custom'
    displayMode: 'percentage', // 'percentage' or 'volume'
    timeColumns: [],           // Array of time period objects

    expandedNodes: new Set(),  // Set of expanded node IDs
    modifiedCells: new Map(),  // Track changes: "pekerjaanId-timeId" -> value
    currentCell: null,         // Currently focused cell

    ganttInstance: null,       // Frappe Gantt instance
    scurveChart: null,         // ECharts instance
  };

  // DOM Elements
  const $leftTable = document.getElementById('left-table');
  const $rightTable = document.getElementById('right-table');
  const $leftTbody = document.getElementById('left-tbody');
  const $rightTbody = document.getElementById('right-tbody');
  const $timeHeaderRow = document.getElementById('time-header-row');
  const $leftPanelScroll = document.querySelector('.left-panel-scroll');
  const $rightPanelScroll = document.querySelector('.right-panel-scroll');
  const $itemCount = document.getElementById('item-count');
  const $modifiedCount = document.getElementById('modified-count');
  const $totalProgress = document.getElementById('total-progress');
  const $statusMessage = document.getElementById('status-message');
  const $loadingOverlay = document.getElementById('loading-overlay');

  // =========================================================================
  // UTILITY FUNCTIONS
  // =========================================================================

  function showLoading(show = true) {
    if ($loadingOverlay) {
      $loadingOverlay.classList.toggle('d-none', !show);
    }
  }

  function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    const toastBody = document.getElementById('toast-body');
    if (!toast || !toastBody) return;

    toast.classList.remove('text-bg-success', 'text-bg-danger', 'text-bg-warning');
    toast.classList.add(`text-bg-${type}`);
    toastBody.textContent = message;

    const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
    bsToast.show();
  }

  async function apiCall(url, options = {}) {
    // Add CSRF token for POST/PUT/DELETE/PATCH requests
    const method = (options.method || 'GET').toUpperCase();
    const needsCSRF = ['POST', 'PUT', 'DELETE', 'PATCH'].includes(method);

    if (needsCSRF) {
      options.headers = options.headers || {};
      options.headers['X-CSRFToken'] = getCookie('csrftoken');
    }

    const response = await fetch(url, {
      credentials: 'same-origin',
      ...options
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.error || `HTTP ${response.status}`);
    }

    return response.json();
  }

  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  function formatNumber(num, decimals = 2) {
    if (num === null || num === undefined || num === '') return '-';
    const n = parseFloat(num);
    if (isNaN(n)) return '-';
    return n.toLocaleString('id-ID', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  }

  // =========================================================================
  // DATE UTILITY FUNCTIONS (for time scale modes)
  // =========================================================================

  function getProjectTimeline() {
    // Get from app context or use defaults
    const today = new Date();

    // Try to get from project data passed via context
    const projectData = window.projectData || {};

    const start = projectData.tanggal_mulai
      ? new Date(projectData.tanggal_mulai)
      : today;

    const end = projectData.tanggal_selesai
      ? new Date(projectData.tanggal_selesai)
      : new Date(start.getFullYear(), 11, 31); // Dec 31

    return { start, end };
  }

  function addDays(date, days) {
    const result = new Date(date);
    result.setDate(result.getDate() + days);
    return result;
  }

  function formatDate(date, format = 'short') {
    if (format === 'short') {
      const day = date.getDate().toString().padStart(2, '0');
      const month = date.toLocaleString('id-ID', { month: 'short' });
      return `${day} ${month}`;
    } else if (format === 'iso') {
      return date.toISOString().split('T')[0];
    }
    return date.toLocaleDateString('id-ID');
  }

  function getWeekNumber(date, startDate) {
    const diff = date - startDate;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    return Math.floor(days / 7) + 1;
  }

  function getMonthName(date) {
    return date.toLocaleString('id-ID', { month: 'long', year: 'numeric' });
  }

  // =========================================================================
  // DATA LOADING
  // =========================================================================

  async function loadAllData() {
    showLoading(true);
    try {
      // Load base data first
      await Promise.all([
        loadTahapan(),
        loadPekerjaan(),
        loadVolumes()
      ]);

      // Generate time columns (needed for assignment mapping)
      generateTimeColumns();

      // Load assignments after time columns are ready
      await loadAssignments();

      // Render grid with all data
      renderGrid();
      updateStatusBar();

      showToast('Data loaded successfully', 'success');
    } catch (error) {
      console.error('Load data failed:', error);
      showToast('Failed to load data: ' + error.message, 'danger');
    } finally {
      showLoading(false);
    }
  }

  async function loadTahapan() {
    try {
      const data = await apiCall(apiBase);
      state.tahapanList = (data.tahapan || []).sort((a, b) => a.urutan - b.urutan);
      return state.tahapanList;
    } catch (error) {
      console.error('Failed to load tahapan:', error);
      throw error;
    }
  }

  async function loadPekerjaan() {
    try {
      const response = await apiCall(`/detail_project/api/project/${projectId}/list-pekerjaan/tree/`);

      // Build hierarchical tree
      const tree = buildPekerjaanTree(response);
      state.pekerjaanTree = tree;

      // Flatten for easy access
      state.flatPekerjaan = flattenTree(tree);

      return state.pekerjaanTree;
    } catch (error) {
      console.error('Failed to load pekerjaan:', error);
      throw error;
    }
  }

  function buildPekerjaanTree(response) {
    const tree = [];
    const data = response.klasifikasi || response;

    if (!Array.isArray(data)) return tree;

    data.forEach(klas => {
      const klasNode = {
        id: `klas-${klas.id || klas.nama}`,
        type: 'klasifikasi',
        nama: klas.name || klas.nama || 'Klasifikasi',
        children: [],
        level: 0,
        expanded: true
      };

      if (klas.sub && Array.isArray(klas.sub)) {
        klas.sub.forEach(sub => {
          const subNode = {
            id: `sub-${sub.id || sub.nama}`,
            type: 'sub-klasifikasi',
            nama: sub.name || sub.nama || 'Sub-Klasifikasi',
            children: [],
            level: 1,
            expanded: true
          };

          if (sub.pekerjaan && Array.isArray(sub.pekerjaan)) {
            sub.pekerjaan.forEach(pkj => {
              const pkjNode = {
                id: pkj.id || pkj.pekerjaan_id,
                type: 'pekerjaan',
                kode: pkj.snapshot_kode || pkj.kode || '',
                nama: pkj.snapshot_uraian || pkj.uraian || '',
                volume: pkj.volume || 0,
                satuan: pkj.snapshot_satuan || pkj.satuan || '-',
                level: 2
              };
              subNode.children.push(pkjNode);
            });
          }

          klasNode.children.push(subNode);
        });
      }

      tree.push(klasNode);
    });

    return tree;
  }

  function flattenTree(tree, result = []) {
    tree.forEach(node => {
      result.push(node);
      if (node.children && node.children.length > 0) {
        flattenTree(node.children, result);
      }
    });
    return result;
  }

  async function loadVolumes() {
    try {
      const data = await apiCall(`/detail_project/api/project/${projectId}/volume-pekerjaan/list/`);
      state.volumeMap.clear();

      const volumes = data.items || data.volumes || data.data || [];
      if (Array.isArray(volumes)) {
        volumes.forEach(v => {
          const pkjId = v.pekerjaan_id || v.id;
          const qty = parseFloat(v.quantity || v.volume || v.qty) || 0;
          if (pkjId) {
            state.volumeMap.set(pkjId, qty);
          }
        });
      }

      return state.volumeMap;
    } catch (error) {
      console.error('Failed to load volumes:', error);
      return state.volumeMap;
    }
  }

  async function loadAssignments() {
    try {
      state.assignmentMap.clear();
      console.log('Loading assignments for pekerjaan...');

      // Load assignments for all pekerjaan
      const promises = state.flatPekerjaan
        .filter(node => node.type === 'pekerjaan')
        .map(async (node) => {
          try {
            const data = await apiCall(`/detail_project/api/project/${projectId}/pekerjaan/${node.id}/assignments/`);

            if (data.assignments && Array.isArray(data.assignments)) {
              console.log(`  Pekerjaan ${node.id} has ${data.assignments.length} assignments:`, data.assignments);
              data.assignments.forEach(a => {
                const tahapanId = a.tahapan_id;
                const proporsi = parseFloat(a.proporsi) || 0;

                // Map tahapanId to corresponding timeColumns
                state.timeColumns.forEach(col => {
                  if (col.tahapanId === tahapanId) {
                    // Use cellKey format: "pekerjaanId-colId"
                    const cellKey = `${node.id}-${col.id}`;
                    console.log(`    Mapped: ${cellKey} = ${proporsi}`);
                    state.assignmentMap.set(cellKey, proporsi);
                  }
                });
              });
            }
          } catch (error) {
            console.warn(`Failed to load assignments for pekerjaan ${node.id}:`, error);
          }
        });

      await Promise.all(promises);
      console.log(`Total assignments loaded: ${state.assignmentMap.size}`);
      console.log('Assignment map:', Array.from(state.assignmentMap.entries()));
      return state.assignmentMap;
    } catch (error) {
      console.error('Failed to load assignments:', error);
      return state.assignmentMap;
    }
  }

  // =========================================================================
  // TIME COLUMNS GENERATION
  // =========================================================================

  function generateTimeColumns() {
    state.timeColumns = [];

    // Check current time scale mode
    const timeScale = state.timeScale || 'custom';
    console.log(`Generating time columns for mode: ${timeScale}`);

    // ALL modes now pull from database tahapan (loaded in state.tahapanList)
    // Backend has already created the appropriate tahapan for each mode
    // We just map tahapan to time columns with proper tahapanId

    if (timeScale === 'custom') {
      console.log(`  Custom mode: Using all ${state.tahapanList.length} tahapan`);
    } else {
      console.log(`  ${timeScale} mode: Filtering tahapan by generation_mode="${timeScale}"`);
    }

    state.tahapanList.forEach((tahap, index) => {
      // For daily/weekly/monthly modes, only include tahapan with matching generation_mode
      // For custom mode, include all tahapan
      const shouldInclude = timeScale === 'custom' || tahap.generation_mode === timeScale;

      if (shouldInclude) {
        const column = {
          id: `tahap-${tahap.tahapan_id}`,
          tahapanId: tahap.tahapan_id,  // ✅ CRITICAL: Link to database tahapan!
          label: tahap.nama || `Tahap ${index + 1}`,
          type: tahap.generation_mode || 'custom',
          isAutoGenerated: tahap.is_auto_generated || false,
          generationMode: tahap.generation_mode || 'custom',
          index: state.timeColumns.length,
          startDate: tahap.tanggal_mulai ? new Date(tahap.tanggal_mulai) : null,
          endDate: tahap.tanggal_selesai ? new Date(tahap.tanggal_selesai) : null,
          urutan: tahap.urutan || index
        };

        state.timeColumns.push(column);
      }
    });

    console.log(`Generated ${state.timeColumns.length} time columns with tahapanId`);
  }

  function generateDailyColumns() {
    const { start, end } = getProjectTimeline();
    console.log(`  Daily mode: ${formatDate(start, 'iso')} to ${formatDate(end, 'iso')}`);

    let currentDate = new Date(start);
    let dayNum = 1;

    while (currentDate <= end) {
      const column = {
        id: `day-${dayNum}`,
        tahapanId: null, // Will be mapped to actual tahapan
        label: `Day ${dayNum}`,
        sublabel: formatDate(currentDate, 'short'),
        type: 'daily',
        index: dayNum - 1,
        startDate: new Date(currentDate),
        endDate: new Date(currentDate),
        dateKey: formatDate(currentDate, 'iso')
      };

      state.timeColumns.push(column);
      currentDate = addDays(currentDate, 1);
      dayNum++;
    }
  }

  function generateWeeklyColumns() {
    const { start, end } = getProjectTimeline();
    const weekEndDay = state.weekEndDay || 0; // 0 = Sunday (default)

    console.log(`  Weekly mode: ${formatDate(start, 'iso')} to ${formatDate(end, 'iso')}`);

    let currentStart = new Date(start);
    let weekNum = 1;

    while (currentStart <= end) {
      // Find end of week (next occurrence of weekEndDay)
      let currentEnd = new Date(currentStart);
      const daysUntilWeekEnd = (weekEndDay - currentStart.getDay() + 7) % 7;

      if (daysUntilWeekEnd === 0 && currentStart.getDay() === weekEndDay) {
        // Already on week end day - this is a 1-day week
        currentEnd = new Date(currentStart);
      } else {
        currentEnd = addDays(currentStart, daysUntilWeekEnd);
      }

      // Don't exceed project end
      if (currentEnd > end) {
        currentEnd = new Date(end);
      }

      const startDay = currentStart.getDate().toString().padStart(2, '0');
      const endDay = currentEnd.getDate().toString().padStart(2, '0');
      const startMonth = currentStart.toLocaleString('id-ID', { month: 'short' });
      const endMonth = currentEnd.toLocaleString('id-ID', { month: 'short' });

      let label;
      if (startMonth === endMonth && currentStart.getDate() === currentEnd.getDate()) {
        label = `W${weekNum} (${startDay} ${startMonth})`;
      } else if (startMonth === endMonth) {
        label = `W${weekNum} (${startDay}-${endDay} ${startMonth})`;
      } else {
        label = `W${weekNum} (${startDay} ${startMonth}-${endDay} ${endMonth})`;
      }

      const column = {
        id: `week-${weekNum}`,
        tahapanId: null,
        label: label,
        type: 'weekly',
        index: weekNum - 1,
        startDate: new Date(currentStart),
        endDate: new Date(currentEnd),
        weekNumber: weekNum
      };

      state.timeColumns.push(column);

      // Move to day after week end
      currentStart = addDays(currentEnd, 1);
      weekNum++;

      // Safety check
      if (weekNum > 100) break; // Prevent infinite loop
    }
  }

  function generateMonthlyColumns() {
    const { start, end } = getProjectTimeline();
    console.log(`  Monthly mode: ${formatDate(start, 'iso')} to ${formatDate(end, 'iso')}`);

    let currentDate = new Date(start);
    let monthNum = 1;

    while (currentDate <= end) {
      // Start of month (or project start if mid-month)
      const monthStart = new Date(currentDate);

      // End of month
      const monthEnd = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 0);

      // Don't exceed project end
      const actualEnd = monthEnd > end ? new Date(end) : monthEnd;

      const monthName = currentDate.toLocaleString('id-ID', { month: 'long' });
      const year = currentDate.getFullYear();

      const column = {
        id: `month-${monthNum}`,
        tahapanId: null,
        label: `${monthName} ${year}`,
        type: 'monthly',
        index: monthNum - 1,
        startDate: new Date(monthStart),
        endDate: new Date(actualEnd),
        monthNumber: monthNum
      };

      state.timeColumns.push(column);

      // Move to first day of next month
      currentDate = new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1);
      monthNum++;

      // Safety check
      if (monthNum > 24) break; // Max 2 years
    }
  }

  function generateCustomColumns() {
    // Generate from user-defined tahapan
    console.log(`  Custom mode: Generating from ${state.tahapanList.length} tahapan`);

    state.tahapanList.forEach((tahap, index) => {
      const column = {
        id: `tahap-${tahap.tahapan_id}`,
        tahapanId: tahap.tahapan_id,  // ✅ Link to tahapan
        label: tahap.nama || `Tahap ${index + 1}`,
        type: 'custom',
        isAutoGenerated: tahap.is_auto_generated || false,
        generationMode: tahap.generation_mode || 'custom',
        index: index,
        startDate: tahap.tanggal_mulai ? new Date(tahap.tanggal_mulai) : null,
        endDate: tahap.tanggal_selesai ? new Date(tahap.tanggal_selesai) : null,
        urutan: tahap.urutan || index
      };

      console.log(`  Column ${index}: ${column.id} (tahapanId=${column.tahapanId}, label="${column.label}")`);
      state.timeColumns.push(column);
    });
  }

  function generateWeeklyColumns() {
    // Generate 52 weeks starting from project start date or current date
    const startDate = getProjectStartDate();
    const weeksToGenerate = 52; // 1 year

    for (let i = 0; i < weeksToGenerate; i++) {
      const weekStart = new Date(startDate);
      weekStart.setDate(weekStart.getDate() + (i * 7));

      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekEnd.getDate() + 6);

      // Format: "W1 (01-07 Jan)"
      const weekNum = i + 1;
      const startDay = weekStart.getDate().toString().padStart(2, '0');
      const endDay = weekEnd.getDate().toString().padStart(2, '0');
      const startMonth = weekStart.toLocaleString('id-ID', { month: 'short' });
      const endMonth = weekEnd.toLocaleString('id-ID', { month: 'short' });

      let label;
      if (startMonth === endMonth) {
        label = `W${weekNum} (${startDay}-${endDay} ${startMonth})`;
      } else {
        label = `W${weekNum} (${startDay} ${startMonth}-${endDay} ${endMonth})`;
      }

      state.timeColumns.push({
        id: `week-${weekNum}`,
        label: label,
        type: 'week',
        index: i,
        startDate: new Date(weekStart),
        endDate: new Date(weekEnd)
      });
    }
  }

  function getProjectStartDate() {
    // Try to get from first tahapan
    if (state.tahapanList.length > 0 && state.tahapanList[0].tanggal_mulai) {
      return new Date(state.tahapanList[0].tanggal_mulai);
    }

    // Default to start of current year
    const now = new Date();
    return new Date(now.getFullYear(), 0, 1); // Jan 1st
  }

  function generateDailyColumns() {
    // TODO: Implement daily view
    generateWeeklyColumns(); // Fallback for now
  }

  function generateMonthlyColumns() {
    const startDate = getProjectStartDate();
    const monthsToGenerate = 12; // 1 year

    for (let i = 0; i < monthsToGenerate; i++) {
      const monthStart = new Date(startDate.getFullYear(), startDate.getMonth() + i, 1);
      const monthEnd = new Date(startDate.getFullYear(), startDate.getMonth() + i + 1, 0);

      const monthName = monthStart.toLocaleString('id-ID', { month: 'long' });
      const year = monthStart.getFullYear();

      state.timeColumns.push({
        id: `month-${i}`,
        label: `${monthName} ${year}`,
        type: 'month',
        index: i,
        startDate: new Date(monthStart),
        endDate: new Date(monthEnd)
      });
    }
  }

  function generateCustomColumns() {
    // TODO: Implement custom date range
    generateWeeklyColumns(); // Fallback for now
  }

  // =========================================================================
  // GRID RENDERING
  // =========================================================================

  function renderGrid() {
    if (!$leftTbody || !$rightTbody || !$timeHeaderRow) return;

    // Render time column headers
    renderTimeHeaders();

    // Render both tables
    renderLeftTable();
    renderRightTable();

    // CRITICAL: Sync row heights after render
    syncRowHeights();

    // Setup scroll sync
    setupScrollSync();

    // Attach events
    attachGridEvents();
  }

  function syncRowHeights() {
    // Get all rows from both tables
    const leftRows = $leftTbody.querySelectorAll('tr');
    const rightRows = $rightTbody.querySelectorAll('tr');

    // Sync each row height
    leftRows.forEach((leftRow, index) => {
      const rightRow = rightRows[index];
      if (!rightRow) return;

      // Clear any previous inline height
      leftRow.style.height = '';
      rightRow.style.height = '';

      // Force browser to calculate natural height
      const leftHeight = leftRow.offsetHeight;
      const rightHeight = rightRow.offsetHeight;

      // Use the maximum height of both
      const maxHeight = Math.max(leftHeight, rightHeight);

      // Apply to both rows for perfect alignment
      leftRow.style.height = `${maxHeight}px`;
      rightRow.style.height = `${maxHeight}px`;
    });
  }

  function renderTimeHeaders() {
    // Clear existing headers
    $timeHeaderRow.innerHTML = '';

    // Add time columns
    const fragment = document.createDocumentFragment();
    state.timeColumns.forEach(col => {
      const th = document.createElement('th');
      th.dataset.colId = col.id;
      th.textContent = col.label;
      th.title = col.label; // Tooltip for long labels
      fragment.appendChild(th);
    });

    $timeHeaderRow.appendChild(fragment);
  }

  function renderLeftTable() {
    const rows = [];
    state.pekerjaanTree.forEach(node => {
      renderLeftRow(node, rows);
    });

    $leftTbody.innerHTML = rows.join('');
  }

  function renderRightTable() {
    const rows = [];
    state.pekerjaanTree.forEach(node => {
      renderRightRow(node, rows);
    });

    $rightTbody.innerHTML = rows.join('');
  }

  function renderLeftRow(node, rows, parentExpanded = true) {
    const isExpanded = state.expandedNodes.has(node.id) !== false;
    const isVisible = parentExpanded;
    const rowClass = `row-${node.type} ${isVisible ? '' : 'row-hidden'}`;
    const levelClass = `level-${node.level}`;

    let toggleIcon = '';
    if (node.children && node.children.length > 0) {
      toggleIcon = `<span class="tree-toggle ${isExpanded ? '' : 'collapsed'}" data-node-id="${node.id}">
        <i class="bi bi-caret-down-fill"></i>
      </span>`;
    }

    const volume = node.type === 'pekerjaan' ? formatNumber(state.volumeMap.get(node.id) || 0) : '';
    const satuan = node.type === 'pekerjaan' ? escapeHtml(node.satuan) : '';

    rows.push(`
      <tr class="${rowClass}" data-node-id="${node.id}" data-row-index="${rows.length}">
        <td class="col-tree">
          ${toggleIcon}
        </td>
        <td class="col-uraian ${levelClass}">
          <div class="tree-node">
            ${escapeHtml(node.nama)}
          </div>
        </td>
        <td class="col-volume text-right">${volume}</td>
        <td class="col-satuan">${satuan}</td>
      </tr>
    `);

    // Render children
    if (node.children && node.children.length > 0) {
      node.children.forEach(child => {
        renderLeftRow(child, rows, isExpanded && isVisible);
      });
    }
  }

  function renderRightRow(node, rows, parentExpanded = true) {
    const isExpanded = state.expandedNodes.has(node.id) !== false;
    const isVisible = parentExpanded;
    const rowClass = `row-${node.type} ${isVisible ? '' : 'row-hidden'}`;

    // Time cells
    const timeCells = state.timeColumns.map(col => renderTimeCell(node, col)).join('');

    rows.push(`
      <tr class="${rowClass}" data-node-id="${node.id}" data-row-index="${rows.length}">
        ${timeCells}
      </tr>
    `);

    // Render children
    if (node.children && node.children.length > 0) {
      node.children.forEach(child => {
        renderRightRow(child, rows, isExpanded && isVisible);
      });
    }
  }

  function renderTimeCell(node, column) {
    if (node.type !== 'pekerjaan') {
      // Readonly for klasifikasi/sub-klasifikasi
      return `<td class="time-cell readonly" data-node-id="${node.id}" data-col-id="${column.id}"></td>`;
    }

    const cellKey = `${node.id}-${column.id}`;

    // Get saved value from assignmentMap (from database)
    const savedValue = state.assignmentMap.get(cellKey) || 0;

    // Get modified value (pending changes)
    const modifiedValue = state.modifiedCells.get(cellKey);

    // Current value to display: modified if exists, otherwise saved
    const currentValue = modifiedValue !== undefined ? modifiedValue : savedValue;

    // Determine cell state classes
    let cellClasses = 'time-cell editable';

    // State 3: Saved (nilai > 0 di database)
    if (savedValue > 0) {
      cellClasses += ' saved';
    }

    // State 2: Modified (ada perubahan pending)
    if (modifiedValue !== undefined && modifiedValue !== savedValue) {
      cellClasses += ' modified';
    }

    // State 1: Default (empty) - no additional class needed

    // Calculate display value
    let displayValue = '';
    if (currentValue > 0) {
      if (state.displayMode === 'percentage') {
        displayValue = `<span class="cell-value percentage">${currentValue.toFixed(1)}</span>`;
      } else {
        const volume = state.volumeMap.get(node.id) || 0;
        const volValue = (volume * currentValue / 100).toFixed(2);
        displayValue = `<span class="cell-value volume">${volValue}</span>`;
      }
    }

    return `<td class="${cellClasses}"
                data-node-id="${node.id}"
                data-col-id="${column.id}"
                data-value="${currentValue}"
                data-saved-value="${savedValue}"
                tabindex="0">
              ${displayValue}
            </td>`;
  }

  // =========================================================================
  // EVENT HANDLERS
  // =========================================================================

  function attachGridEvents() {
    // Tree toggle
    document.querySelectorAll('.tree-toggle').forEach(toggle => {
      toggle.addEventListener('click', handleTreeToggle);
    });

    // Cell editing
    document.querySelectorAll('.time-cell.editable').forEach(cell => {
      cell.addEventListener('click', handleCellClick);
      cell.addEventListener('dblclick', handleCellDoubleClick);
      cell.addEventListener('keydown', handleCellKeydown);
    });
  }

  function handleTreeToggle(e) {
    e.stopPropagation();
    const nodeId = this.dataset.nodeId;
    const isExpanded = !this.classList.contains('collapsed');

    if (isExpanded) {
      state.expandedNodes.delete(nodeId);
      this.classList.add('collapsed');
    } else {
      state.expandedNodes.add(nodeId);
      this.classList.remove('collapsed');
    }

    // Toggle children visibility
    toggleNodeChildren(nodeId, !isExpanded);

    // CRITICAL: Re-sync row heights after toggle
    // Use setTimeout to ensure DOM has updated
    setTimeout(() => syncRowHeights(), 10);
  }

  function toggleNodeChildren(nodeId, show) {
    // Find all children rows in both tables
    const leftRows = $leftTbody.querySelectorAll(`tr[data-node-id]`);
    const rightRows = $rightTbody.querySelectorAll(`tr[data-node-id]`);

    let foundParent = false;
    let parentLevel = -1;

    leftRows.forEach((row, index) => {
      if (row.dataset.nodeId === nodeId) {
        foundParent = true;
        const levelClass = row.querySelector('.col-uraian').className.match(/level-(\d+)/);
        parentLevel = levelClass ? parseInt(levelClass[1]) : -1;
        return;
      }

      if (foundParent) {
        const rowLevelClass = row.querySelector('.col-uraian')?.className.match(/level-(\d+)/);
        const rowLevel = rowLevelClass ? parseInt(rowLevelClass[1]) : -1;

        if (rowLevel > parentLevel) {
          // This is a child - toggle both left and right rows
          if (show) {
            row.classList.remove('row-hidden');
            rightRows[index]?.classList.remove('row-hidden');
          } else {
            row.classList.add('row-hidden');
            rightRows[index]?.classList.add('row-hidden');
          }
        } else {
          // No longer a child
          foundParent = false;
        }
      }
    });
  }

  function setupScrollSync() {
    if (!$leftPanelScroll || !$rightPanelScroll) return;

    // Sync vertical scrolling from right to left
    $rightPanelScroll.addEventListener('scroll', () => {
      $leftPanelScroll.scrollTop = $rightPanelScroll.scrollTop;
    });

    // Sync vertical scrolling from left to right (if user scrolls left via keyboard/touch)
    $leftPanelScroll.addEventListener('scroll', () => {
      $rightPanelScroll.scrollTop = $leftPanelScroll.scrollTop;
    });
  }

  function handleCellClick(e) {
    // Select cell
    document.querySelectorAll('.time-cell.selected').forEach(c => c.classList.remove('selected'));
    this.classList.add('selected');
    state.currentCell = this;
  }

  function handleCellDoubleClick(e) {
    // Enter edit mode
    enterEditMode(this);
  }

  function handleCellKeydown(e) {
    if (!this.classList.contains('editing')) {
      // Navigation mode
      switch(e.key) {
        case 'Enter':
          enterEditMode(this);
          e.preventDefault();
          break;
        case 'Tab':
          navigateCell(e.shiftKey ? 'left' : 'right');
          e.preventDefault();
          break;
        case 'ArrowUp':
          navigateCell('up');
          e.preventDefault();
          break;
        case 'ArrowDown':
          navigateCell('down');
          e.preventDefault();
          break;
        case 'ArrowLeft':
          if (!e.shiftKey) {
            navigateCell('left');
            e.preventDefault();
          }
          break;
        case 'ArrowRight':
          if (!e.shiftKey) {
            navigateCell('right');
            e.preventDefault();
          }
          break;
        default:
          // Start typing
          if (e.key.length === 1 && /[0-9]/.test(e.key)) {
            enterEditMode(this, e.key);
            e.preventDefault();
          }
      }
    }
  }

  function enterEditMode(cell, initialValue = '') {
    if (cell.classList.contains('readonly')) return;

    cell.classList.add('editing');
    const currentValue = initialValue || cell.dataset.value || '';

    const input = document.createElement('input');
    input.type = 'number';
    input.step = '0.01';
    input.min = '0';
    input.max = '100';
    input.value = initialValue || currentValue;
    input.className = 'cell-input';

    input.addEventListener('blur', () => {
      // Only exit if not already exiting (prevent race condition)
      if (!cell._isExiting) {
        exitEditMode(cell, input);
      }
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        cell._isExiting = true; // Prevent blur from calling exitEditMode again
        exitEditMode(cell, input);
        navigateCell('down');
        e.preventDefault();
      } else if (e.key === 'Escape') {
        cell._isExiting = true; // Prevent blur from calling exitEditMode again
        cell.classList.remove('editing');
        cell.innerHTML = cell._originalContent;
        cell.focus();
      } else if (e.key === 'Tab') {
        cell._isExiting = true; // Prevent blur from calling exitEditMode again
        exitEditMode(cell, input);
        navigateCell(e.shiftKey ? 'left' : 'right');
        e.preventDefault();
      }
    });

    cell._originalContent = cell.innerHTML;
    cell.innerHTML = '';
    cell.appendChild(input);
    input.focus();
    input.select();
  }

  function exitEditMode(cell, input) {
    const newValue = parseFloat(input.value) || 0;
    const savedValue = parseFloat(cell.dataset.savedValue) || 0;
    const cellKey = `${cell.dataset.nodeId}-${cell.dataset.colId}`;

    console.log(`exitEditMode: cellKey=${cellKey}, newValue=${newValue}, savedValue=${savedValue}`);

    cell.classList.remove('editing');

    // Validate range
    if (newValue < 0 || newValue > 100) {
      showToast('Value must be between 0-100', 'danger');
      cell.innerHTML = cell._originalContent;
      cell._isExiting = false; // Reset flag
      cell.focus();
      return;
    }

    // Determine if value changed from saved value
    const hasChanged = newValue !== savedValue;
    console.log(`  hasChanged=${hasChanged}`);

    if (hasChanged) {
      // Update modifiedCells Map
      if (newValue === 0 && savedValue === 0) {
        // Both zero - remove from modified
        console.log(`  Both zero - removing from modifiedCells`);
        state.modifiedCells.delete(cellKey);
      } else {
        console.log(`  Adding to modifiedCells: ${cellKey} = ${newValue}`);
        state.modifiedCells.set(cellKey, newValue);
      }

      // Update cell classes based on 3-state system
      cell.classList.remove('saved', 'modified');

      // State 3: Saved
      if (savedValue > 0) {
        cell.classList.add('saved');
      }

      // State 2: Modified
      if (newValue !== savedValue) {
        cell.classList.add('modified');
      }

      // Update data attribute
      cell.dataset.value = newValue;

      // Calculate and update display
      let displayValue = '';
      if (newValue > 0) {
        if (state.displayMode === 'percentage') {
          displayValue = `<span class="cell-value percentage">${newValue.toFixed(1)}</span>`;
        } else {
          const node = state.flatPekerjaan.find(n => n.id == cell.dataset.nodeId);
          const volume = state.volumeMap.get(node?.id) || 0;
          const volValue = (volume * newValue / 100).toFixed(2);
          displayValue = `<span class="cell-value volume">${volValue}</span>`;
        }
      }
      cell.innerHTML = displayValue;

      updateStatusBar();
    } else {
      // No change - restore original
      cell.innerHTML = cell._originalContent;
    }

    // Reset flag for next edit
    cell._isExiting = false;
    cell.focus();
  }

  function navigateCell(direction) {
    if (!state.currentCell) return;

    const currentRow = state.currentCell.closest('tr');
    const currentIndex = Array.from(currentRow.children).indexOf(state.currentCell);
    let nextCell = null;

    switch(direction) {
      case 'up': {
        const prevRow = currentRow.previousElementSibling;
        if (prevRow && !prevRow.classList.contains('row-hidden')) {
          nextCell = prevRow.children[currentIndex];
        }
        break;
      }
      case 'down': {
        const nextRow = currentRow.nextElementSibling;
        if (nextRow && !nextRow.classList.contains('row-hidden')) {
          nextCell = nextRow.children[currentIndex];
        }
        break;
      }
      case 'left': {
        nextCell = state.currentCell.previousElementSibling;
        break;
      }
      case 'right': {
        nextCell = state.currentCell.nextElementSibling;
        break;
      }
    }

    if (nextCell && nextCell.classList.contains('time-cell')) {
      nextCell.focus();
      nextCell.click();
    }
  }

  function syncScrolling() {
    // Sync vertical scrolling between frozen and time tables
    if ($frozenTbody && $timeTbody) {
      const frozenPanel = document.querySelector('.left-panel');
      const timePanel = document.querySelector('.right-panel');

      // Not needed if tables are in same container with overflow
      // For now, tables are separate, we need manual sync
    }
  }

  // =========================================================================
  // STATUS BAR & STATISTICS
  // =========================================================================

  function updateStatusBar() {
    if ($itemCount) {
      const pekerjaanCount = state.flatPekerjaan.filter(n => n.type === 'pekerjaan').length;
      $itemCount.textContent = pekerjaanCount;
    }

    if ($modifiedCount) {
      $modifiedCount.textContent = state.modifiedCells.size;
    }

    if ($totalProgress) {
      // Calculate overall progress
      let totalPercent = 0;
      let count = 0;

      state.flatPekerjaan.filter(n => n.type === 'pekerjaan').forEach(node => {
        const assignments = state.assignmentMap.get(node.id) || {};
        const sum = Object.values(assignments).reduce((a, b) => a + b, 0);
        totalPercent += sum;
        count++;
      });

      const avgProgress = count > 0 ? (totalPercent / count).toFixed(1) : 0;
      $totalProgress.textContent = `${avgProgress}%`;
    }
  }

  // =========================================================================
  // SAVE FUNCTIONALITY
  // =========================================================================

  async function saveAllChanges() {
    console.log('Save All clicked. Modified cells:', state.modifiedCells.size);
    console.log('Modified cells map:', Array.from(state.modifiedCells.entries()));

    if (state.modifiedCells.size === 0) {
      showToast('No changes to save', 'warning');
      return;
    }

    showLoading(true);

    try {
      // Group changes by pekerjaan
      const changesByPekerjaan = new Map();

      state.modifiedCells.forEach((value, key) => {
        const [pekerjaanId, colId] = key.split('-');
        if (!changesByPekerjaan.has(pekerjaanId)) {
          changesByPekerjaan.set(pekerjaanId, {});
        }

        // Find tahapan ID from column
        const column = state.timeColumns.find(c => c.id === colId);
        if (column && column.tahapanId) {
          changesByPekerjaan.get(pekerjaanId)[column.tahapanId] = value;
        }
      });

      console.log('Changes grouped by pekerjaan:', Array.from(changesByPekerjaan.entries()));

      // Save each pekerjaan
      let successCount = 0;
      for (const [pekerjaanId, assignments] of changesByPekerjaan.entries()) {
        console.log(`Saving pekerjaan ${pekerjaanId}:`, assignments);
        await savePekerjaanAssignments(pekerjaanId, assignments);
        successCount++;
      }

      console.log(`Successfully saved ${successCount} pekerjaan assignments`);

      // SUCCESS: Move modified values to assignmentMap
      state.modifiedCells.forEach((value, key) => {
        state.assignmentMap.set(key, value);

        // Update cell data-saved-value attribute
        const [pekerjaanId, colId] = key.split('-');
        const cell = document.querySelector(
          `.time-cell[data-node-id="${pekerjaanId}"][data-col-id="${colId}"]`
        );
        if (cell) {
          cell.dataset.savedValue = value;

          // Update classes: remove modified, add saved if value > 0
          cell.classList.remove('modified');
          if (value > 0) {
            cell.classList.add('saved');
          } else {
            cell.classList.remove('saved');
          }
        }
      });

      // Clear modified cells after successful save
      state.modifiedCells.clear();

      showToast(`All changes saved successfully (${successCount} pekerjaan)`, 'success');
      updateStatusBar();

    } catch (error) {
      console.error('Save failed:', error);
      showToast('Failed to save: ' + error.message, 'danger');
    } finally {
      showLoading(false);
    }
  }

  async function savePekerjaanAssignments(pekerjaanId, assignments) {
    // Separate assignments into two groups: assign (proporsi > 0) and unassign (proporsi = 0)
    const toAssign = [];
    const toUnassign = [];

    for (const [tahapanId, proporsi] of Object.entries(assignments)) {
      if (parseFloat(proporsi) > 0) {
        toAssign.push({ tahapanId, proporsi: parseFloat(proporsi) });
      } else {
        toUnassign.push(tahapanId);
      }
    }

    console.log(`  - To assign (${toAssign.length}):`, toAssign);
    console.log(`  - To unassign (${toUnassign.length}):`, toUnassign);

    // Handle assignments (proporsi > 0)
    for (const { tahapanId, proporsi } of toAssign) {
      const url = `${apiBase}${tahapanId}/assign/`;
      const payload = {
        assignments: [{
          pekerjaan_id: parseInt(pekerjaanId),
          proporsi: proporsi
        }]
      };
      console.log(`  - POST ${url}`, payload);

      const response = await apiCall(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(payload)
      });
      console.log(`  - Response:`, response);
    }

    // Handle unassignments (proporsi = 0)
    for (const tahapanId of toUnassign) {
      const url = `${apiBase}${tahapanId}/unassign/`;
      const payload = {
        pekerjaan_ids: [parseInt(pekerjaanId)]
      };
      console.log(`  - POST ${url}`, payload);

      const response = await apiCall(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCookie('csrftoken')
        },
        body: JSON.stringify(payload)
      });
      console.log(`  - Response:`, response);
    }
  }

  // =========================================================================
  // GANTT CHART
  // =========================================================================

  function initGanttChart() {
    const ganttData = state.tahapanList.map(tahap => ({
      id: `tahap-${tahap.tahapan_id}`,
      name: tahap.nama,
      start: tahap.tanggal_mulai || new Date().toISOString().split('T')[0],
      end: tahap.tanggal_selesai || new Date(Date.now() + 30*24*60*60*1000).toISOString().split('T')[0],
      progress: 50 // Calculate from assignments
    }));

    if (ganttData.length > 0 && window.Gantt) {
      state.ganttInstance = new Gantt('#gantt-chart', ganttData, {
        view_mode: 'Week',
        language: 'id'
      });
    }
  }

  // =========================================================================
  // KURVA S CHART
  // =========================================================================

  function initScurveChart() {
    if (!window.echarts) return;

    const chartDom = document.getElementById('scurve-chart');
    if (!chartDom) return;

    state.scurveChart = echarts.init(chartDom);

    // Sample data - replace with real calculations
    const option = {
      title: {
        text: 'Kurva S - Progress Project'
      },
      tooltip: {
        trigger: 'axis'
      },
      legend: {
        data: ['Planned', 'Actual']
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'Week 5', 'Week 6']
      },
      yAxis: {
        type: 'value',
        max: 100,
        axisLabel: {
          formatter: '{value}%'
        }
      },
      series: [
        {
          name: 'Planned',
          type: 'line',
          smooth: true,
          data: [0, 15, 35, 55, 75, 100],
          lineStyle: { color: '#0d6efd', width: 2, type: 'dashed' }
        },
        {
          name: 'Actual',
          type: 'line',
          smooth: true,
          data: [0, 10, 30, 50, 68, 85],
          lineStyle: { color: '#198754', width: 3 },
          areaStyle: { color: 'rgba(25, 135, 84, 0.1)' }
        }
      ]
    };

    state.scurveChart.setOption(option);
  }

  // =========================================================================
  // TIME SCALE MODE SWITCHING (with backend regeneration)
  // =========================================================================

  async function switchTimeScaleMode(newMode) {
    console.log(`Switching time scale mode to: ${newMode}`);

    // Show loading state
    const gridContainer = document.getElementById('grid-container');
    if (gridContainer) {
      gridContainer.style.opacity = '0.5';
      gridContainer.style.pointerEvents = 'none';
    }

    try {
      // Call backend API to regenerate tahapan
      const response = await apiCall(`/detail_project/api/project/${projectId}/regenerate-tahapan/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          mode: newMode,
          week_end_day: state.weekEndDay || 0,
          convert_assignments: true  // Phase 3.3: Enable assignment conversion
        })
      });

      console.log(`Regenerate response:`, response);

      if (response.ok) {
        // Update state
        state.timeScale = newMode;

        // Reload tahapan list from backend
        await loadTahapan();

        // Regenerate time columns from new tahapan
        generateTimeColumns();

        // Reload assignments
        await loadAssignments();

        // Re-render grid
        renderGrid();

        // Show success message
        alert(`Mode switched to ${newMode}. ${response.message || ''}`);
      } else {
        console.error('Failed to regenerate tahapan:', response.error);
        alert(`Error: ${response.error || 'Failed to switch mode'}`);
      }

    } catch (error) {
      console.error('Error switching mode:', error);
      alert(`Error switching mode: ${error.message}`);
    } finally {
      // Remove loading state
      if (gridContainer) {
        gridContainer.style.opacity = '1';
        gridContainer.style.pointerEvents = 'auto';
      }
    }
  }

  // =========================================================================
  // EVENT BINDINGS
  // =========================================================================

  // Time scale toggle
  document.querySelectorAll('input[name="timeScale"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      const newMode = e.target.value;

      // Confirm mode switch (since it will regenerate tahapan)
      const confirmMsg = `Switch to ${newMode} mode? This will regenerate tahapan.`;
      if (confirm(confirmMsg)) {
        switchTimeScaleMode(newMode);
      } else {
        // Revert radio selection
        document.querySelector(`input[name="timeScale"][value="${state.timeScale}"]`).checked = true;
      }
    });
  });

  // Display mode toggle
  document.querySelectorAll('input[name="displayMode"]').forEach(radio => {
    radio.addEventListener('change', (e) => {
      state.displayMode = e.target.value;
      renderGrid();
    });
  });

  // Collapse/Expand all
  document.getElementById('btn-collapse-all')?.addEventListener('click', () => {
    state.expandedNodes.clear();
    renderGrid();
  });

  document.getElementById('btn-expand-all')?.addEventListener('click', () => {
    state.flatPekerjaan.forEach(node => {
      if (node.children && node.children.length > 0) {
        state.expandedNodes.add(node.id);
      }
    });
    renderGrid();
  });

  // Save button
  document.getElementById('btn-save-all')?.addEventListener('click', saveAllChanges);

  // Tab switch events
  document.getElementById('gantt-tab')?.addEventListener('shown.bs.tab', () => {
    if (!state.ganttInstance) {
      initGanttChart();
    }
  });

  document.getElementById('scurve-tab')?.addEventListener('shown.bs.tab', () => {
    if (!state.scurveChart) {
      initScurveChart();
    } else {
      state.scurveChart.resize();
    }
  });

  // =========================================================================
  // PANEL SCROLL SHADOW EFFECT
  // =========================================================================

  const $leftThead = document.getElementById('left-thead');
  const $rightThead = document.getElementById('right-thead');

  /**
   * Handle shadow effect when content scrolls under table headers
   * Headers are sticky to panel top (not viewport)
   * Toolbar sticky handled by dp-sticky-topbar class (pure CSS)
   */
  function handlePanelScrollShadow() {
    if ($leftPanelScroll && $leftThead) {
      const scrollTop = $leftPanelScroll.scrollTop;
      $leftThead.classList.toggle('scrolled', scrollTop > 0);
    }

    if ($rightPanelScroll && $rightThead) {
      const scrollTop = $rightPanelScroll.scrollTop;
      $rightThead.classList.toggle('scrolled', scrollTop > 0);
    }
  }

  // Attach panel scroll listeners for shadow effect
  if ($leftPanelScroll) {
    $leftPanelScroll.addEventListener('scroll', handlePanelScrollShadow, { passive: true });
  }
  if ($rightPanelScroll) {
    $rightPanelScroll.addEventListener('scroll', handlePanelScrollShadow, { passive: true });
  }

  // =========================================================================
  // INITIALIZATION
  // =========================================================================

  loadAllData();

})();
