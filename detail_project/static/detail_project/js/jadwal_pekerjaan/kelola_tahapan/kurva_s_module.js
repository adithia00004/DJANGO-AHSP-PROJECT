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

  function getDefaultOption(state, context) {
    if (context && typeof context.getDefaultOption === 'function') {
      return context.getDefaultOption(state);
    }
    return moduleStore.defaultOption || {
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
  }

  function init(context = {}) {
    if (!window.echarts) {
      return 'legacy';
    }
    const state = resolveState(context.state);
    if (!state) {
      return 'legacy';
    }

    const chartDom = resolveDom(state);
    if (!chartDom) {
      return 'legacy';
    }

    state.scurveChart = state.scurveChart || echarts.init(chartDom);
    const option = context.option || getDefaultOption(state, context);
    state.scurveChart.setOption(option);
    moduleStore.option = option;
    return state.scurveChart;
  }

  function resize(context = {}) {
    const state = resolveState(context.state);
    if (!state || !state.scurveChart) {
      return 'legacy';
    }
    state.scurveChart.resize();
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
    resize: (...args) => (moduleStore.resize || bridge().resize || noop)(...args),
    getChart: (...args) => (moduleStore.getChart || bridge().getChart || noop)(...args),
  });
})();
