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
  moduleStore.viewMode = moduleStore.viewMode || 'Week';

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
        chart.style.height = '520px';
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

  function normalizeViewMode(mode) {
    if (!mode) return 'Week';
    const value = String(mode).trim().toLowerCase();
    if (value === 'day') return 'Day';
    if (value === 'month') return 'Month';
    return 'Week';
  }

  function getViewMode() {
    return normalizeViewMode(moduleStore.viewMode);
  }

  function setViewMode(mode, context = {}) {
    const normalized = normalizeViewMode(mode);
    moduleStore.viewMode = normalized;

    const state = resolveState(context.state);
    if (state) {
      state.cache = state.cache || {};
      state.cache.ganttViewMode = normalized;
    }

    if (moduleStore.ganttInstance && typeof moduleStore.ganttInstance.change_view_mode === 'function') {
      try {
        moduleStore.ganttInstance.change_view_mode(normalized);
      } catch (error) {
        console.warn('Kelola Tahapan Gantt: change_view_mode failed', error);
      }
    }

    if (context.refresh !== false) {
      return moduleStore.refresh(Object.assign({}, context, { state }));
    }
    return normalized;
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

      const node = nodeMap.get(pekerjaanId);
      const path = pathMap.get(pekerjaanId) || [];
      const totalVolume = state.volumeMap instanceof Map
        ? state.volumeMap.get(Number(pekerjaanId)) || 0
        : 0;

      weightedByTahapan.set(tahapanId, (weightedByTahapan.get(tahapanId) || 0) + (totalVolume * percent));
      volumeByTahapan.set(tahapanId, (volumeByTahapan.get(tahapanId) || 0) + totalVolume);
      percentSumByTahapan.set(tahapanId, (percentSumByTahapan.get(tahapanId) || 0) + percent);
      countByTahapan.set(tahapanId, (countByTahapan.get(tahapanId) || 0) + 1);

      const pekerjaanMap = pekerjaanDetailsByTahapan.get(tahapanId) || new Map();
      pekerjaanMap.set(pekerjaanId, {
        pekerjaanId,
        nama: node ? (node.nama || node.name || node.kode || pekerjaanId) : pekerjaanId,
        path,
        percent,
      });
      pekerjaanDetailsByTahapan.set(tahapanId, pekerjaanMap);
    }

    const progressMap = new Map();

    const tahapanList = state.tahapanList || [];
    tahapanList.forEach((tahap) => {
      const tahapanId = tahap.id || tahap.tahapan_id || tahap.uuid || tahap.pk;
      if (!tahapanId) return;

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
            percent: Math.round(detail.percent * 100) / 100,
          }))
        : [];

      progressMap.set(tahapanId, {
        progress,
        totalVolume,
        sampleCount: count,
        pekerjaan: pekerjaanDetails,
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
    calculateProgress(Object.assign({}, context, { state, utils }));
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

    pekerjaanList.forEach((pekerjaan) => {
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
        progress,
        custom_class: progress >= 100 ? 'gantt-task-complete' : '',
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

  function safeHtml(text, utils) {
    const value = text || '';
    return utils && typeof utils.escapeHtml === 'function'
      ? utils.escapeHtml(value)
      : String(value);
  }

  function buildPopupHtml(task, utils) {
    const meta = task.metadata || {};
    const title = safeHtml(meta.label || task.name || 'Pekerjaan', utils);
    const progressValue = Number(task.progress) || 0;
    const progressLabel = `${progressValue.toFixed(progressValue % 1 === 0 ? 0 : 1)}%`;
    const startLabel = safeHtml(meta.start || task.start || '', utils);
    const endLabel = safeHtml(meta.end || task.end || '', utils);

    const segments = Array.isArray(meta.segments) ? meta.segments : [];
    const segmentsHtml = segments.length
      ? `<ul class="gantt-popup-segments">${segments.map((detail) => {
          const percentLabel = Number.isFinite(detail.percent)
            ? `${detail.percent.toFixed(detail.percent % 1 === 0 ? 0 : 1)}%`
            : '';
          const label = detail.label || `${detail.start} - ${detail.end}`;
          return `<li><span class="gantt-popup-segment-label">${safeHtml(label, utils)}</span>${percentLabel ? `<span class="gantt-popup-segment-percent">${percentLabel}</span>` : ''}</li>`;
        }).join('')}</ul>`
      : '<p class="mb-0 text-muted"><em>Belum ada distribusi progres</em></p>';

    return `
      <div class="gantt-popup">
        <h5>${title}</h5>
        <div class="gantt-popup-section">
          <strong>Periode:</strong> ${startLabel} s/d ${endLabel}
        </div>
        <div class="gantt-popup-section">
          <strong>Progress:</strong> ${progressLabel}
        </div>
        <div class="gantt-popup-section">
          <strong>Distribusi:</strong>
          ${segmentsHtml}
        </div>
      </div>
    `;
  }

  function emitSelectionEvent(task, state) {
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
  }

  function buildGanttOptions(state, utils) {
    const viewMode = getViewMode();

    return {
      view_mode: viewMode,
      date_format: 'YYYY-MM-DD',
      custom_popup_html: (task) => buildPopupHtml(task, utils),
      on_click(task) {
        emitSelectionEvent(task, state);
      },
      on_view_change(mode) {
        const normalized = normalizeViewMode(mode);
        moduleStore.viewMode = normalized;
        if (state) {
          state.cache = state.cache || {};
          state.cache.ganttViewMode = normalized;
        }
        moduleStore.emitViewChange?.(normalized);
      },
    };
  }

  function bindResizeHandler(state, utils) {
    if (moduleStore.resizeHandler) {
      return;
    }
    moduleStore.resizeHandler = () => {
      if (moduleStore.ganttInstance && typeof moduleStore.ganttInstance.refresh === 'function') {
        try {
          moduleStore.ganttInstance.refresh(state.ganttTasks || []);
          moduleStore.ganttInstance.change_view_mode(getViewMode());
        } catch (error) {
          console.warn('Kelola Tahapan Gantt: resize refresh failed', error);
        }
      }
    };
    window.addEventListener('resize', moduleStore.resizeHandler);
  }

  function ensureGantt(state, tasks, utils, options = {}) {
    const dom = resolveDom(state);
    if (!dom.chart) {
      return null;
    }

    if (typeof window.Gantt !== 'function') {
      console.warn('Kelola Tahapan Gantt: Frappe Gantt tidak tersedia. Pastikan script Frappe Gantt sudah dimuat.');
      return 'legacy';
    }

    const viewMode = getViewMode();
    if (moduleStore.ganttInstance && typeof moduleStore.ganttInstance.refresh === 'function') {
      try {
        moduleStore.ganttInstance.refresh(tasks);
        moduleStore.ganttInstance.change_view_mode(viewMode);
        moduleStore.ganttInstance.options.custom_popup_html = (task) => buildPopupHtml(task, utils);
        return moduleStore.ganttInstance;
      } catch (error) {
        console.warn('Kelola Tahapan Gantt: gagal me-refresh instance Frappe, membuat ulang.', error);
        moduleStore.ganttInstance = null;
        state.ganttInstance = null;
      }
    }

    dom.chart.innerHTML = '';
    const gantt = new Gantt(dom.chart, tasks, Object.assign({}, buildGanttOptions(state, utils), options));
    moduleStore.ganttInstance = gantt;
    state.ganttInstance = gantt;
    bindResizeHandler(state, utils);
    return gantt;
  }

  function refresh(context = {}) {
    const state = resolveState(context.state);
    if (!state) return 'legacy';

    const utils = prepareUtils(context.utils);

    const tasks = Array.isArray(context.tasks) && context.tasks.length > 0
      ? context.tasks
      : moduleStore.buildTasks(Object.assign({}, context, { state, utils }));

    state.ganttTasks = tasks;

    if (!tasks || tasks.length === 0) {
      if (state.ganttInstance && typeof state.ganttInstance.refresh === 'function') {
        try {
          state.ganttInstance.refresh([]);
        } catch (error) {
          console.warn('Kelola Tahapan Gantt: gagal membersihkan gantt kosong', error);
        }
      }
      return [];
    }

    const gantt = ensureGantt(state, tasks, utils, context.options);
    if (gantt && gantt !== 'legacy') {
      moduleStore.tasks = tasks;
      bootstrap.log.info('Kelola Tahapan Gantt: render completed', {
        taskCount: tasks.length,
        viewMode: getViewMode(),
      });
    }
    return gantt;
  }

  function init(context = {}) {
    const state = resolveState(context.state);
    if (!state) return 'legacy';
    moduleStore.buildTasks(Object.assign({}, context, { state }));
    return moduleStore.refresh(Object.assign({}, context, { state }));
  }

  function destroy() {
    if (moduleStore.ganttInstance) {
      try {
        if (typeof moduleStore.ganttInstance.destroy === 'function') {
          moduleStore.ganttInstance.destroy();
        }
      } catch (error) {
        console.warn('Kelola Tahapan Gantt: destroy failed', error);
      }
    }
    moduleStore.ganttInstance = null;
    if (moduleStore.resizeHandler) {
      window.removeEventListener('resize', moduleStore.resizeHandler);
      moduleStore.resizeHandler = null;
    }
  }

  Object.assign(moduleStore, {
    resolveState,
    resolveDom,
    calculateProgress,
    buildTasks,
    refresh,
    init,
    destroy,
    setViewMode,
    getViewMode,
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
    setViewMode: (...args) => (moduleStore.setViewMode || bridge().setViewMode || noop)(...args),
    getViewMode: (...args) => (moduleStore.getViewMode || bridge().getViewMode || noop)(...args),
    destroy: (...args) => (moduleStore.destroy || bridge().destroy || noop)(...args),
  });
})();
