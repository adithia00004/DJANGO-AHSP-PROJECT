(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;
  if (!bootstrap || !manifest || !manifest.modules || !manifest.modules.gantt) {
    return;
  }

  const meta = manifest.modules.gantt;
  const noop = () => undefined;
  const hasModule = typeof bootstrap.hasModule === 'function'
    ? (id) => bootstrap.hasModule(id)
    : (id) => bootstrap.modules && bootstrap.modules.has
      ? bootstrap.modules.has(id)
      : false;

  if (hasModule(meta.id)) {
    return;
  }

  const bridge = () => {
    const facade = window[manifest.globals.facade];
    if (!facade || !facade.gantt) {
      return {};
    }
    return facade.gantt;
  };

  const globalModules = window.KelolaTahapanPageModules = window.KelolaTahapanPageModules || {};
  const moduleStore = globalModules.gantt = Object.assign({}, globalModules.gantt || {});
  const ONE_DAY_MS = 24 * 60 * 60 * 1000;

  function resolveState(stateOverride) {
    let target = stateOverride || window.kelolaTahapanPageState || (bootstrap && bootstrap.state) || null;
    if (!target || typeof target !== 'object') {
      return null;
    }

    if (!(target.assignmentMap instanceof Map)) target.assignmentMap = new Map(target.assignmentMap || []);
    if (!(target.modifiedCells instanceof Map)) target.modifiedCells = new Map(target.modifiedCells || []);
    if (!(target.expandedNodes instanceof Set)) target.expandedNodes = new Set(Array.from(target.expandedNodes || []));
    if (!(target.tahapanProgressMap instanceof Map)) target.tahapanProgressMap = new Map();
    if (!Array.isArray(target.timeColumns)) target.timeColumns = [];
    if (!Array.isArray(target.tahapanList)) target.tahapanList = [];
    if (!target.domRefs || typeof target.domRefs !== 'object') target.domRefs = {};

    return target;
  }

  function resolveDom(state) {
    const domRefs = state.domRefs || {};

    const chart = domRefs.ganttChart || document.getElementById('gantt-chart');

    if (!domRefs.ganttChart && chart) {
      domRefs.ganttChart = chart;
      if (!chart.style.height) {
        chart.style.height = '500px';
      }
      if (!chart.style.width) {
        chart.style.width = '100%';
      }
    }

    return { chart };
  }

  function defaultEscapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
  }

  function defaultNormalizeToISODate(value, fallbackISO) {
    if (!value) {
      return fallbackISO || null;
    }
    if (value instanceof Date) {
      if (Number.isNaN(value.getTime())) {
        return fallbackISO || null;
      }
      return value.toISOString().split('T')[0];
    }
    if (typeof value === 'string') {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return fallbackISO || null;
      }
      return date.toISOString().split('T')[0];
    }
    if (typeof value === 'number') {
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) {
        return fallbackISO || null;
      }
      return date.toISOString().split('T')[0];
    }
    return fallbackISO || null;
  }

  function defaultGetProjectStartDate(state) {
    if (state.tahapanList.length > 0 && state.tahapanList[0].tanggal_mulai) {
      return new Date(state.tahapanList[0].tanggal_mulai);
    }
    if (state.projectStart) {
      const date = new Date(state.projectStart);
      if (!Number.isNaN(date.getTime())) {
        return date;
      }
    }
    return new Date();
  }

  function prepareUtils(contextUtils) {
    const utils = Object.assign(
      {
        escapeHtml: defaultEscapeHtml,
        normalizeToISODate: defaultNormalizeToISODate,
        getProjectStartDate: defaultGetProjectStartDate,
      },
      moduleStore.utils || {},
      contextUtils || {},
    );

    moduleStore.utils = utils;
    return utils;
  }

  function buildPekerjaanPathMaps(state) {
    const nodeMap = new Map();
    const pathMap = new Map();

    const traverse = (nodes, prefix = []) => {
      if (!Array.isArray(nodes)) return;
      nodes.forEach(node => {
        const label = node.nama || node.name || node.kode || `Node ${node.id}`;
        const nextPrefix = prefix.concat(label);

        if (node.type === 'pekerjaan') {
          const key = String(node.id);
          nodeMap.set(key, node);
          pathMap.set(key, nextPrefix);
        }

        if (node.children && node.children.length > 0) {
          traverse(node.children, nextPrefix);
        }
      });
    };

    traverse(state.pekerjaanTree || []);
    return { nodeMap, pathMap };
  }

  function calculateProgress(context = {}) {
    const state = resolveState(context.state);
    if (!state) return new Map();

    const columnLookup = new Map();
    (state.timeColumns || []).forEach(col => {
      if (col && col.tahapanId) {
        columnLookup.set(col.id, col);
      }
    });

    const { nodeMap, pathMap } = buildPekerjaanPathMaps(state);
    const weightedByTahapan = new Map();
    const volumeByTahapan = new Map();
    const percentSumByTahapan = new Map();
    const countByTahapan = new Map();
    const pekerjaanDetailsByTahapan = new Map();

    const assignmentsEntries = state.assignmentMap instanceof Map
      ? state.assignmentMap.entries()
      : Object.entries(state.assignmentMap || {});

    for (const [key, value] of assignmentsEntries) {
      const [pekerjaanId, colId] = key.split('-');
      const column = columnLookup.get(colId);
      if (!column || !column.tahapanId) {
        continue;
      }
      const tahapanId = column.tahapanId;
      const percent = parseFloat(value) || 0;

      if (!Number.isFinite(percent) || percent <= 0) {
        continue;
      }

      if (!weightedByTahapan.has(tahapanId)) {
        weightedByTahapan.set(tahapanId, 0);
      }
      if (!volumeByTahapan.has(tahapanId)) {
        volumeByTahapan.set(tahapanId, 0);
      }

      const pekerjaanVolume = state.volumeMap instanceof Map
        ? (state.volumeMap.get(Number(pekerjaanId)) || state.volumeMap.get(pekerjaanId) || 0)
        : 0;

      if (pekerjaanVolume > 0) {
        const currentWeighted = weightedByTahapan.get(tahapanId) || 0;
        weightedByTahapan.set(tahapanId, currentWeighted + pekerjaanVolume * percent);

        const currentVolume = volumeByTahapan.get(tahapanId) || 0;
        volumeByTahapan.set(tahapanId, currentVolume + pekerjaanVolume);
      }

      const percentSum = percentSumByTahapan.get(tahapanId) || 0;
      percentSumByTahapan.set(tahapanId, percentSum + percent);

      const count = countByTahapan.get(tahapanId) || 0;
      countByTahapan.set(tahapanId, count + 1);

      if (!pekerjaanDetailsByTahapan.has(tahapanId)) {
        pekerjaanDetailsByTahapan.set(tahapanId, new Map());
      }
      const pekerjaanMap = pekerjaanDetailsByTahapan.get(tahapanId);
      const pekerjaanKey = String(pekerjaanId);
      if (!pekerjaanMap.has(pekerjaanKey)) {
        const node = nodeMap.get(pekerjaanKey) || {};
        const pathParts = pathMap.get(pekerjaanKey) || [node.nama || node.name || pekerjaanKey];
        pekerjaanMap.set(pekerjaanKey, {
          pekerjaanId: pekerjaanKey,
          nama: node.nama || node.name || node.kode || `Pekerjaan ${pekerjaanKey}`,
          path: pathParts.join(' / '),
          percent: 0
        });
      }
      const detail = pekerjaanMap.get(pekerjaanKey);
      detail.percent += percent;
    }

    const progressMap = new Map();

    (state.tahapanList || []).forEach(tahap => {
      const tahapanId = tahap.tahapan_id;
      const weighted = weightedByTahapan.get(tahapanId) || 0;
      const totalVolume = volumeByTahapan.get(tahapanId) || 0;
      const percentSum = percentSumByTahapan.get(tahapanId) || 0;
      const count = countByTahapan.get(tahapanId) || 0;

      let progress = 0;
      if (totalVolume > 0) {
        progress = weighted / totalVolume;
      } else if (count > 0) {
        progress = percentSum / count;
      }

      if (!Number.isFinite(progress)) {
        progress = 0;
      }

      progress = Math.max(0, Math.min(100, Math.round(progress * 100) / 100));

      const pekerjaanMap = pekerjaanDetailsByTahapan.get(tahapanId);
      const pekerjaanDetails = pekerjaanMap
        ? Array.from(pekerjaanMap.values()).map(detail => ({
            pekerjaanId: detail.pekerjaanId,
            nama: detail.nama,
            path: detail.path,
            percent: Math.round(detail.percent * 100) / 100
          }))
        : [];

      progressMap.set(tahapanId, {
        progress,
        totalVolume,
        sampleCount: count,
        pekerjaan: pekerjaanDetails
      });
    });

    state.tahapanProgressMap = progressMap;
    moduleStore.progressMap = progressMap;
    return progressMap;
  }

  function buildTasks(context = {}) {
    const state = resolveState(context.state);
    if (!state) return [];

    const utils = prepareUtils(context.utils);
    moduleStore.calculateProgress(Object.assign({}, context, { state, utils }));
    const pekerjaanList = buildPekerjaanHierarchy(state);
    const tasks = buildPekerjaanTasks(state, utils, pekerjaanList);

    state.ganttTasks = tasks;
    moduleStore.tasks = tasks;
    return tasks;
  }

  function buildPekerjaanHierarchy(state) {
    const result = [];

    const walk = (nodes, level = 0, ancestors = []) => {
      if (!Array.isArray(nodes)) return;
      nodes.forEach((node) => {
        const label = node.nama || node.name || node.kode || `Node ${node.id}`;
        const pathParts = ancestors.concat(label);
        if (node.type === 'pekerjaan') {
          result.push({
            id: String(node.id),
            level,
            pathParts,
          });
        }
        if (node.children && node.children.length > 0) {
          walk(node.children, level + 1, pathParts);
        }
      });
    };

    walk(state.pekerjaanTree || [], 0, []);
    return result;
  }

  function buildPekerjaanTasks(state, utils, pekerjaanList) {
    const { nodeMap, pathMap } = buildPekerjaanPathMaps(state);
    const columnLookup = new Map();

    state.timeColumns.forEach((col) => {
      if (!col || !col.id) return;
      const rawStart = col.startDate instanceof Date ? col.startDate : (col.startDate ? new Date(col.startDate) : null);
      if (!(rawStart instanceof Date) || Number.isNaN(rawStart.getTime())) {
        return;
      }
      let rawEnd = col.endDate instanceof Date ? col.endDate : (col.endDate ? new Date(col.endDate) : null);
      if (!(rawEnd instanceof Date) || Number.isNaN(rawEnd.getTime()) || rawEnd.getTime() <= rawStart.getTime()) {
        rawEnd = new Date(rawStart.getTime() + ONE_DAY_MS);
      }
      columnLookup.set(String(col.id), {
        column: col,
        startDate: rawStart,
        endDate: rawEnd,
        label: col.label || '',
        rangeLabel: col.rangeLabel || col.subLabel || '',
      });
    });

    const buckets = new Map();
    const entries = state.assignmentMap instanceof Map
      ? Array.from(state.assignmentMap.entries())
      : Object.entries(state.assignmentMap || {});

    entries.forEach(([rawKey, rawValue]) => {
      const key = String(rawKey);
      const separatorIndex = key.indexOf('-');
      if (separatorIndex === -1) return;
      const pekerjaanId = key.slice(0, separatorIndex);
      const colId = key.slice(separatorIndex + 1);
      if (!pekerjaanId || !colId) return;

      const columnInfo = columnLookup.get(colId);
      if (!columnInfo) return;

      const percent = parseFloat(rawValue);
      if (!Number.isFinite(percent) || percent <= 0) return;

      const bucket = buckets.get(pekerjaanId) || {
        totalPercent: 0,
        start: null,
        end: null,
        segments: [],
      };

      bucket.totalPercent += percent;
      if (!bucket.start || columnInfo.startDate < bucket.start) {
        bucket.start = columnInfo.startDate;
      }
      if (!bucket.end || columnInfo.endDate > bucket.end) {
        bucket.end = columnInfo.endDate;
      }
      bucket.segments.push({
        label: columnInfo.label || columnInfo.rangeLabel || '',
        rangeLabel: columnInfo.rangeLabel || '',
        start: columnInfo.startDate,
        end: columnInfo.endDate,
        percent,
      });

      buckets.set(pekerjaanId, bucket);
    });

    const tasks = [];
    const projectRange = computeProjectRange(state);
    const projectStartSafe = new Date(projectRange.min);
    const projectEndSafe = new Date(projectRange.max);

    pekerjaanList.forEach((pekerjaan, index) => {
      const pekerjaanId = pekerjaan.id;
      const bucket = buckets.get(pekerjaanId);
      const node = nodeMap.get(pekerjaanId);
      const pathParts = pekerjaan.pathParts.length > 0
        ? pekerjaan.pathParts
        : (pathMap.get(pekerjaanId) || [node ? (node.nama || node.name || `Pekerjaan ${pekerjaanId}`) : `Pekerjaan ${pekerjaanId}`]);
      const displayLabel = pathParts.join(' / ') || `Pekerjaan ${pekerjaanId}`;
      const indentPrefix = '\u00A0\u00A0'.repeat(Math.max(0, pekerjaan.level - 2));
      const name = indentPrefix + (pathParts[pathParts.length - 1] || displayLabel);

      let startDate = projectStartSafe;
      let endDate = projectEndSafe;
      let progress = 0;
      let segments = [];

      if (bucket && bucket.start && bucket.end) {
        startDate = bucket.start;
        endDate = bucket.end;
        progress = Math.max(0, Math.min(100, bucket.totalPercent));
        segments = bucket.segments
          .sort((a, b) => a.start - b.start)
          .map((segment) => ({
            label: segment.label || segment.rangeLabel || displayLabel,
            start: utils.normalizeToISODate(segment.start, null) || segment.start.toISOString().split('T')[0],
            end: utils.normalizeToISODate(segment.end, null) || segment.end.toISOString().split('T')[0],
            percent: Math.max(0, Math.min(100, segment.percent)),
          }));
      }

      const startValue = startDate.getTime();
      const endValue = Math.max(endDate.getTime(), startValue + ONE_DAY_MS);
      const startISO = utils.normalizeToISODate(startDate, null) || new Date(startValue).toISOString().split('T')[0];
      const endISO = utils.normalizeToISODate(endDate, startISO) || new Date(endValue).toISOString().split('T')[0];

      tasks.push({
        id: `pekerjaan-${pekerjaanId}`,
        name,
        start: startISO,
        end: endISO,
        startValue,
        endValue,
        progress,
        metadata: {
          pekerjaanId,
          label: displayLabel,
          start: startISO,
          end: endISO,
          pathParts,
          segments,
        },
      });
    });

    return tasks;
  }

  function buildChartDataset(tasks, state) {
    const categories = [];
    const data = [];
    let minStart = Number.POSITIVE_INFINITY;
    let maxEnd = Number.NEGATIVE_INFINITY;

    tasks.forEach((task, index) => {
      const label = task.metadata && task.metadata.label
        ? task.metadata.label
        : task.name || `Pekerjaan ${index + 1}`;

      categories.push(label);

      const startValue = Number.isFinite(task.startValue) ? task.startValue : Date.parse(task.start);
      const endValueRaw = Number.isFinite(task.endValue) ? task.endValue : Date.parse(task.end);
      const endValue = Number.isFinite(endValueRaw) && endValueRaw > startValue
        ? endValueRaw
        : startValue + ONE_DAY_MS;

      data.push({
        value: [startValue, endValue, index],
        task,
      });

      if (startValue < minStart) minStart = startValue;
      if (endValue > maxEnd) maxEnd = endValue;
    });

    if (!Number.isFinite(minStart) || !Number.isFinite(maxEnd)) {
      const projectStart = state && state.projectStart ? new Date(state.projectStart) : null;
      const projectEnd = state && state.projectEnd ? new Date(state.projectEnd) : null;
      if (projectStart instanceof Date && !Number.isNaN(projectStart.getTime())) {
        minStart = projectStart.getTime();
      }
      if (projectEnd instanceof Date && !Number.isNaN(projectEnd.getTime())) {
        maxEnd = projectEnd.getTime();
      }
    }

    if ((!Number.isFinite(minStart) || !Number.isFinite(maxEnd)) || maxEnd <= minStart) {
      const stateRange = computeProjectRange(state);
      minStart = stateRange.min;
      maxEnd = stateRange.max;
    }

    if (!categories.length) {
      categories.push('Belum ada pekerjaan');
      data.push({
        value: [minStart, minStart + ONE_DAY_MS, 0],
        task: {
          progress: 0,
          metadata: {
            label: 'Belum ada pekerjaan',
            pathParts: [],
            segments: [],
            start: new Date(minStart).toISOString().split('T')[0],
            end: new Date(minStart + ONE_DAY_MS).toISOString().split('T')[0],
          },
        },
        placeholder: true,
      });
    }

    return { categories, data, range: { min: minStart, max: maxEnd } };
  }

  function computeProjectRange(state) {
    const start = state && state.projectStart ? new Date(state.projectStart) : null;
    const end = state && state.projectEnd ? new Date(state.projectEnd) : null;
    const startSafe = (start instanceof Date && !Number.isNaN(start.getTime()))
      ? start.getTime()
      : Date.now();
    const endSafe = (end instanceof Date && !Number.isNaN(end.getTime()) && end.getTime() > startSafe)
      ? end.getTime()
      : startSafe + 30 * ONE_DAY_MS;
    return { min: startSafe, max: endSafe };
  }

  function renderGanttItem(params, api) {
    const categoryIndex = api.value(2);
    const startCoord = api.coord([api.value(0), categoryIndex]);
    const endCoord = api.coord([api.value(1), categoryIndex]);
    const barHeight = Math.max(api.size([0, 1])[1] * 0.6, 6);

    const x = startCoord[0];
    const y = startCoord[1] - barHeight / 2;
    const totalWidth = Math.max(endCoord[0] - startCoord[0], 3);

    const dataItem = params && params.data ? params.data : null;
    if (!dataItem || !dataItem.task) {
      return {
        type: 'group',
        children: [],
      };
    }

    const task = dataItem.task || {};
    const progressRaw = Number(task.progress);
    const progress = Number.isFinite(progressRaw) ? Math.min(Math.max(progressRaw, 0), 100) : 0;
    const progressWidth = Math.max(totalWidth * (progress / 100), 0);

    const isComplete = progress >= 100;
    const fillColor = isComplete ? '#198754' : '#0d6efd';
    const borderColor = isComplete ? '#146c43' : '#0a58ca';

    const children = [
      {
        type: 'rect',
        shape: { x, y, width: totalWidth, height: barHeight },
        style: {
          fill: '#e9ecef',
          stroke: '#ced4da',
        },
      },
      {
        type: 'rect',
        shape: { x, y, width: progressWidth, height: barHeight },
        style: {
          fill: fillColor,
          stroke: borderColor,
        },
      },
    ];

    const progressLabel = progress.toFixed(progress % 1 === 0 ? 0 : 1);
    if (totalWidth > 60) {
      children.push({
        type: 'text',
        style: {
          text: `${progressLabel}%`,
          fill: '#ffffff',
          fontWeight: 'bold',
          fontSize: 12,
          align: 'center',
          verticalAlign: 'middle',
          x: x + totalWidth / 2,
          y: startCoord[1],
        },
      });
    } else {
      children.push({
        type: 'text',
        style: {
          text: `${progressLabel}%`,
          fill: '#6c757d',
          fontSize: 12,
          align: 'left',
          verticalAlign: 'middle',
          x: x + totalWidth + 6,
          y: startCoord[1],
        },
      });
    }

    return {
      type: 'group',
      children,
    };
  }

  function safeHtml(text, utils) {
    const value = text || '';
    return utils && typeof utils.escapeHtml === 'function'
      ? utils.escapeHtml(value)
      : String(value);
  }

  function createChartOption({ utils, dataset, range }) {
    const todayValue = Date.now();
    const minAxis = range && Number.isFinite(range.min) ? range.min : undefined;
    const maxAxis = range && Number.isFinite(range.max) ? range.max : undefined;

    return {
      animation: false,
      tooltip: {
        enterable: true,
        confine: true,
        backgroundColor: '#ffffff',
        borderColor: '#ced4da',
        borderWidth: 1,
        textStyle: {
          color: '#212529',
        },
        formatter: (params) => {
          const task = (params && params.data && params.data.task) || {};
          const meta = task.metadata || {};
          const segments = Array.isArray(meta.segments) ? meta.segments : [];

          const segmentsHtml = segments.length
            ? `<ul class="gantt-tooltip-jobs">${segments.map((detail) => {
                const percentLabel = Number.isFinite(detail.percent)
                  ? `${detail.percent.toFixed(1).replace(/\\.0$/, '')}%`
                  : '';
                const label = detail.label || `${detail.start} - ${detail.end}`;
                return `<li><span class="gantt-tooltip-job">${safeHtml(label, utils)}</span>${percentLabel ? `<span class="gantt-tooltip-percent">${percentLabel}</span>` : ''}</li>`;
              }).join('')}</ul>`
            : '<p class="mb-0"><em>Belum ada distribusi progres</em></p>';

          const progressValue = Number(task.progress) || 0;
          const progressLabel = `${progressValue.toFixed(progressValue % 1 === 0 ? 0 : 1)}%`;

          const startLabel = safeHtml(meta.start || task.start || '', utils);
          const endLabel = safeHtml(meta.end || task.end || '', utils);
          const title = safeHtml(meta.label || task.name || 'Pekerjaan', utils);

          return `
            <div class="gantt-tooltip">
              <div class="gantt-tooltip-title">${title}</div>
              <div><strong>Periode:</strong> ${startLabel} s/d ${endLabel}</div>
              <div><strong>Progress:</strong> ${progressLabel}</div>
              <div class="gantt-tooltip-section">
                <strong>Distribusi:</strong>
                ${segmentsHtml}
              </div>
            </div>
          `;
        },
      },
      dataZoom: [
        {
          type: 'slider',
          xAxisIndex: 0,
          height: 20,
          bottom: 12,
        },
        {
          type: 'inside',
          xAxisIndex: 0,
        },
      ],
      grid: {
        left: 220,
        right: 32,
        top: 32,
        bottom: 60,
        containLabel: true,
      },
      xAxis: {
        type: 'time',
        min: minAxis,
        max: maxAxis,
        axisLine: { lineStyle: { color: '#dee2e6' } },
        splitLine: { lineStyle: { color: '#f1f3f5' } },
        axisLabel: {
          formatter: (value) => {
            const date = new Date(value);
            if (Number.isNaN(date.getTime())) return '';
            return date.toLocaleDateString('id-ID', {
              day: '2-digit',
              month: 'short',
              year: 'numeric',
            });
          },
        },
      },
      yAxis: {
        type: 'category',
        inverse: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: {
          align: 'left',
          margin: 12,
          formatter: (value) => value,
        },
        data: dataset.categories,
      },
      series: [
        {
          name: 'Pekerjaan',
          type: 'custom',
          renderItem: renderGanttItem,
          encode: { x: [0, 1], y: 2 },
          data: dataset.data,
          itemStyle: {
            opacity: 1,
          },
          emphasis: {
            focus: 'series',
          },
          markLine: {
            symbol: ['none', 'none'],
            lineStyle: {
              color: '#dc3545',
              width: 1.5,
              type: 'dashed',
            },
            data: [
              [
                { coord: [todayValue, -0.5] },
                { coord: [todayValue, dataset.categories.length - 0.5] },
              ],
            ],
          },
        },
      ],
    };
  }

  function ensureChart(state) {
    const dom = resolveDom(state);
    if (!dom.chart) {
      return null;
    }

    if (!window.echarts || typeof window.echarts.init !== 'function') {
      console.warn('Kelola Tahapan Gantt: ECharts is not available.');
      return null;
    }

    if (state.ganttInstance && typeof state.ganttInstance.getOption !== 'function') {
      try {
        if (typeof state.ganttInstance.destroy === 'function') {
          state.ganttInstance.destroy();
        }
      } catch (err) {
        console.warn('Kelola Tahapan Gantt: failed to cleanup legacy gantt instance.', err);
      }
      state.ganttInstance = null;
    }

    let chart = window.echarts.getInstanceByDom(dom.chart);
    if (chart && chart.isDisposed?.()) {
      chart = null;
    }

    if (!chart) {
      dom.chart.innerHTML = '';
      chart = window.echarts.init(dom.chart);
    }

    state.ganttInstance = chart;

    registerChartInteractions(chart, state);

    if (!moduleStore.resizeHandler) {
      moduleStore.resizeHandler = () => {
        if (state.ganttInstance && !state.ganttInstance.isDisposed?.()) {
          state.ganttInstance.resize();
        }
      };
      window.addEventListener('resize', moduleStore.resizeHandler);
    }

    return chart;
  }

  function registerChartInteractions(chart, state) {
    if (!chart || chart.__kelolaTahapanBound) {
      return;
    }

    chart.on('click', (params) => {
      const dataItem = params && params.data ? params.data : null;
      if (!dataItem || dataItem.placeholder) {
        return;
      }
      const task = dataItem.task;
      if (!task) return;
      let pekerjaanId = null;
      if (task.id) {
        const match = String(task.id).match(/^pekerjaan-(.+)$/);
        if (match) {
          pekerjaanId = match[1];
        }
      }
      if (window.KelolaTahapanPage && window.KelolaTahapanPage.events && typeof window.KelolaTahapanPage.events.emit === 'function') {
        window.KelolaTahapanPage.events.emit('gantt:select', {
          pekerjaanId,
          task,
          state,
        });
      }
    });

    chart.__kelolaTahapanBound = true;
  }

  function refresh(context = {}) {
    const state = resolveState(context.state);
    if (!state) return 'legacy';

    const utils = prepareUtils(context.utils);

    const tasks = Array.isArray(context.tasks) && context.tasks.length > 0
      ? context.tasks
      : moduleStore.buildTasks(Object.assign({}, context, { state, utils }));

    state.ganttTasks = tasks;
    if (!window.echarts || typeof window.echarts.init !== 'function') {
      console.warn('Kelola Tahapan Gantt: ECharts tidak tersedia. Pastikan script ECharts sudah dimuat.');
      return 'legacy';
    }

    if (!tasks || tasks.length === 0) {
      if (state.ganttInstance && typeof state.ganttInstance.clear === 'function') {
        state.ganttInstance.clear();
      }
      return [];
    }

    const chart = ensureChart(state);
    if (!chart) {
      return 'legacy';
    }

    const dataset = buildChartDataset(tasks, state);
    const option = createChartOption({
      utils,
      dataset,
      range: dataset.range,
    });

    chart.setOption(option, true);
    try {
      chart.resize();
    } catch (resizeError) {
      console.warn('Kelola Tahapan Gantt: resize failed', resizeError);
    }
    moduleStore.chartOption = option;

    return chart;
  }

  function init(context = {}) {
    const state = resolveState(context.state);
    if (!state) return 'legacy';
    moduleStore.buildTasks(Object.assign({}, context, { state }));
    return moduleStore.refresh(Object.assign({}, context, { state }));
  }

  function getSidebarElement() {
    return null;
  }

  Object.assign(moduleStore, {
    resolveState,
    resolveDom,
    calculateProgress,
    buildTasks,
    refresh,
    init,
  });

  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister(context) {
      bootstrap.log.info('Kelola Tahapan Gantt module registered.');
      if (context) {
        context.state = context.state || {};
        context.state.shared = context.state.shared || {};
        context.state.shared.ganttModuleRegisteredAt = Date.now();
      }
      if (context && context.emit) {
        context.emit('kelola_tahapan.gantt:registered', { manifest, meta });
      }
    },
    init: (...args) => (moduleStore.init || bridge().init || noop)(...args),
    refresh: (...args) => (moduleStore.refresh || bridge().refresh || noop)(...args),
    buildTasks: (...args) => (moduleStore.buildTasks || bridge().buildTasks || noop)(...args),
    calculateProgress: (...args) => (moduleStore.calculateProgress || bridge().calculateProgress || noop)(...args),
    getTasks: (...args) => (moduleStore.buildTasks || bridge().getTasks || bridge().buildTasks || noop)(...args),
    getProgressMap: (...args) => (moduleStore.calculateProgress || bridge().getProgressMap || bridge().calculateProgress || noop)(...args),
  });
})();
