(function() {
  'use strict';

  const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
  const manifest = window.KelolaTahapanModuleManifest;
  if (!bootstrap || !manifest || !manifest.modules || !manifest.modules.kurvaS) {
    return;
  }

  const meta = manifest.modules.kurvaS;
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
    if (!facade || !facade.kurvaS) {
      return {};
    }
    return facade.kurvaS;
  };

  const globalModules = window.KelolaTahapanPageModules = window.KelolaTahapanPageModules || {};
  const moduleStore = globalModules.kurvaS = Object.assign({}, globalModules.kurvaS || {});

  const ONE_DAY_MS = 24 * 60 * 60 * 1000;

  function resolveState(stateOverride) {
    const state = stateOverride || window.kelolaTahapanPageState || (bootstrap && bootstrap.state) || null;
    if (!state) return null;
    if (!state.domRefs || typeof state.domRefs !== 'object') {
      state.domRefs = {};
    }
    return state;
  }

  function resolveDom(state) {
    const domRefs = state.domRefs || {};
    const chartDom = domRefs.scurveChart || document.getElementById('scurve-chart');
    if (!domRefs.scurveChart && chartDom) {
      domRefs.scurveChart = chartDom;
    }
    return chartDom;
  }

  function getThemeColors() {
    const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';
    if (theme === 'dark') {
      return {
        text: '#f8fafc',
        axis: '#cbd5f5',
        plannedLine: '#60a5fa',
        plannedArea: 'rgba(96, 165, 250, 0.15)',
        actualLine: '#34d399',
        actualArea: 'rgba(52, 211, 153, 0.18)',
        gridLine: '#334155',
      };
    }
    return {
      text: '#1f2937',
      axis: '#374151',
      plannedLine: '#0d6efd',
      plannedArea: 'rgba(13, 110, 253, 0.12)',
      actualLine: '#198754',
      actualArea: 'rgba(25, 135, 84, 0.12)',
      gridLine: '#e5e7eb',
    };
  }

  function getColumns(state) {
    const columns = Array.isArray(state.timeColumns) ? state.timeColumns.slice() : [];
    columns.sort((a, b) => {
      const aStart = a.startDate instanceof Date ? a.startDate : (a.startDate ? new Date(a.startDate) : null);
      const bStart = b.startDate instanceof Date ? b.startDate : (b.startDate ? new Date(b.startDate) : null);
      if (aStart && bStart) return aStart.getTime() - bStart.getTime();
      return (a.index || 0) - (b.index || 0);
    });
    return columns;
  }

  function buildVolumeLookup(state) {
    const lookup = new Map();
    const setVolume = (key, value) => {
      const numericKey = Number(key);
      const volume = Number.isFinite(value) && value > 0 ? value : null;
      if (volume === null) return;
      lookup.set(String(key), volume);
      if (!Number.isNaN(numericKey)) {
        lookup.set(String(numericKey), volume);
      }
    };

    if (state.volumeMap instanceof Map) {
      state.volumeMap.forEach((value, key) => {
        const vol = parseFloat(value);
        setVolume(key, vol);
      });
    } else if (state.volumeMap && typeof state.volumeMap === 'object') {
      Object.entries(state.volumeMap).forEach(([key, value]) => {
        const vol = parseFloat(value);
        setVolume(key, vol);
      });
    }

    return lookup;
  }

  function getVolumeForPekerjaan(volumeLookup, pekerjaanId, fallback = 1) {
    const idVariants = [
      String(pekerjaanId),
      String(Number(pekerjaanId)),
    ];
    for (const variant of idVariants) {
      if (volumeLookup.has(variant)) {
        return volumeLookup.get(variant);
      }
    }
    return fallback;
  }

  function buildCellValueMap(state) {
    const map = new Map();

    const assignValue = (key, value) => {
      const numeric = parseFloat(value);
      map.set(String(key), Number.isFinite(numeric) ? numeric : 0);
    };

    if (state.assignmentMap instanceof Map) {
      state.assignmentMap.forEach((value, key) => assignValue(key, value));
    } else if (state.assignmentMap && typeof state.assignmentMap === 'object') {
      Object.entries(state.assignmentMap).forEach(([key, value]) => assignValue(key, value));
    }

    if (state.modifiedCells instanceof Map) {
      state.modifiedCells.forEach((value, key) => assignValue(key, value));
    } else if (state.modifiedCells && typeof state.modifiedCells === 'object') {
      Object.entries(state.modifiedCells).forEach(([key, value]) => assignValue(key, value));
    }

    return map;
  }

  function collectPekerjaanIds(state, cellValues) {
    const ids = new Set();

    if (Array.isArray(state.flatPekerjaan)) {
      state.flatPekerjaan.forEach((node) => {
        if (node && (node.type === 'pekerjaan' || typeof node.type === 'undefined')) {
          ids.add(String(node.id));
        }
      });
    }

    cellValues.forEach((_, key) => {
      const [pekerjaanId] = String(key).split('-');
      if (pekerjaanId) {
        ids.add(pekerjaanId);
      }
    });

    return ids;
  }

  function buildDataset(state, context = {}) {
    const columns = getColumns(state);
    if (!columns.length) {
      return null;
    }

    const volumeLookup = buildVolumeLookup(state);
    const cellValues = buildCellValueMap(state);
    const pekerjaanIds = collectPekerjaanIds(state, cellValues);

    let totalVolume = 0;
    pekerjaanIds.forEach((id) => {
      totalVolume += getVolumeForPekerjaan(volumeLookup, id, 1);
    });
    if (!Number.isFinite(totalVolume) || totalVolume <= 0) {
      totalVolume = pekerjaanIds.size || 1;
    }

    const columnIndexById = new Map();
    columns.forEach((col, index) => {
      columnIndexById.set(String(col.id), index);
    });

    const columnTotals = new Array(columns.length).fill(0);
    cellValues.forEach((value, key) => {
      const [pekerjaanId, columnId] = String(key).split('-');
      const columnIndex = columnIndexById.get(columnId);
      if (columnIndex === undefined) {
        return;
      }
      const percent = parseFloat(value);
      if (!Number.isFinite(percent) || percent <= 0) {
        return;
      }
      const pekerjaanVolume = getVolumeForPekerjaan(volumeLookup, pekerjaanId, 1);
      columnTotals[columnIndex] += pekerjaanVolume * (percent / 100);
    });

    const labels = columns.map((col, index) => {
      if (col.label) return col.label;
      if (col.rangeLabel) return `${col.label || ''} ${col.rangeLabel}`.trim();
      return `Week ${index + 1}`;
    });

    const plannedSeries = [];
    const actualSeries = [];
    const details = [];

    let cumulativeActualVolume = 0;
    const plannedStep = columns.length > 0 ? 100 / columns.length : 0;

    columns.forEach((col, index) => {
      cumulativeActualVolume += columnTotals[index] || 0;
      const actualPercent = totalVolume > 0
        ? Math.min(100, Math.max(0, (cumulativeActualVolume / totalVolume) * 100))
        : 0;
      const plannedPercent = Math.min(100, Math.max(0, plannedStep * (index + 1)));

      plannedSeries.push(Number(plannedPercent.toFixed(2)));
      actualSeries.push(Number(actualPercent.toFixed(2)));

      details.push({
        label: labels[index],
        planned: plannedSeries[index],
        actual: actualSeries[index],
        start: col.startDate instanceof Date ? col.startDate : (col.startDate ? new Date(col.startDate) : null),
        end: col.endDate instanceof Date ? col.endDate : (col.endDate ? new Date(col.endDate) : null),
        tooltip: col.tooltip || labels[index],
      });
    });

    return {
      labels,
      planned: plannedSeries,
      actual: actualSeries,
      details,
      totalVolume,
      columnTotals,
    };
  }

  function buildFallbackDataset() {
    return {
      labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
      planned: [0, 33, 66, 100],
      actual: [0, 20, 45, 70],
      details: [],
      totalVolume: 1,
      columnTotals: [],
    };
  }

  function formatDateLabel(date) {
    if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
      return '';
    }
    return date.toLocaleDateString('id-ID', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  }

  function createChartOption(dataset) {
    const colors = getThemeColors();
    const data = dataset || buildFallbackDataset();

    return {
      backgroundColor: 'transparent',
      color: [colors.plannedLine, colors.actualLine],
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          if (!params || !params.length) return '';
          const index = params[0].dataIndex;
          const detail = data.details[index] || {};
          const label = detail.label || data.labels[index];
          const planned = data.planned[index] ?? 0;
          const actual = data.actual[index] ?? 0;
          const start = formatDateLabel(detail.start);
          const end = formatDateLabel(detail.end);

          return [
            `<strong>${label}</strong>`,
            start && end ? `<div>Periode: ${start} - ${end}</div>` : '',
            `<div>Planned: ${planned.toFixed(1)}%</div>`,
            `<div>Actual: ${actual.toFixed(1)}%</div>`,
          ].filter(Boolean).join('');
        },
      },
      legend: {
        data: ['Planned', 'Actual'],
        textStyle: {
          color: colors.text,
        },
      },
      grid: {
        left: '4%',
        right: '4%',
        top: '12%',
        bottom: '6%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        boundaryGap: false,
        data: data.labels,
        axisLabel: {
          color: colors.axis,
        },
        axisLine: {
          lineStyle: {
            color: colors.gridLine,
          },
        },
      },
      yAxis: {
        type: 'value',
        min: 0,
        max: 100,
        axisLabel: {
          formatter: '{value}%',
          color: colors.axis,
        },
        splitLine: {
          lineStyle: {
            color: colors.gridLine,
            type: 'dashed',
          },
        },
      },
      series: [
        {
          name: 'Planned',
          type: 'line',
          smooth: true,
          data: data.planned,
          lineStyle: {
            color: colors.plannedLine,
            width: 2,
            type: 'dashed',
          },
          areaStyle: {
            color: colors.plannedArea,
          },
          symbolSize: 6,
        },
        {
          name: 'Actual',
          type: 'line',
          smooth: true,
          data: data.actual,
          lineStyle: {
            color: colors.actualLine,
            width: 3,
          },
          areaStyle: {
            color: colors.actualArea,
          },
          symbolSize: 7,
        },
      ],
    };
  }

  function ensureChartInstance(state) {
    if (!window.echarts) {
      return 'legacy';
    }
    const chartDom = resolveDom(state);
    if (!chartDom) {
      return 'legacy';
    }

    if (!state.scurveChart) {
      state.scurveChart = echarts.init(chartDom);
    }
    return state.scurveChart;
  }

  function refresh(context = {}) {
    const state = resolveState(context.state);
    if (!state) {
      return 'legacy';
    }

    const chart = ensureChartInstance(state);
    if (chart === 'legacy') {
      return 'legacy';
    }

    const dataset = buildDataset(state, context) || buildFallbackDataset();
    const option = createChartOption(dataset);

    chart.setOption(option, true);
    moduleStore.dataset = dataset;
    moduleStore.option = option;

    return chart;
  }

  function init(context = {}) {
    return refresh(context);
  }

  function resize(context = {}) {
    const state = resolveState(context.state);
    if (!state || !state.scurveChart) {
      return 'legacy';
    }
    try {
      state.scurveChart.resize();
    } catch (error) {
      bootstrap.log.warn('Kelola Tahapan Kurva S: resize failed', error);
    }
    return state.scurveChart;
  }

  function getChart(context = {}) {
    const state = resolveState(context.state);
    if (!state) return null;
    return state.scurveChart || null;
  }

  Object.assign(moduleStore, {
    resolveState,
    resolveDom,
    buildDataset,
    refresh,
    init,
    resize,
    getChart,
  });

  bootstrap.registerModule(meta.id, {
    namespace: meta.namespace,
    pageId: manifest.pageId,
    description: meta.description,
    onRegister(context) {
      bootstrap.log.info('Kelola Tahapan Kurva-S module registered.');
      if (context && context.emit) {
        context.emit('kelola_tahapan.kurva_s:registered', { manifest, meta });
      }
    },
    init: (...args) => (moduleStore.init || bridge().init || noop)(...args),
    refresh: (...args) => (moduleStore.refresh || bridge().refresh || noop)(...args),
    resize: (...args) => (moduleStore.resize || bridge().resize || noop)(...args),
    getChart: (...args) => (moduleStore.getChart || bridge().getChart || noop)(...args),
  });
})();
