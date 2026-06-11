(function () {
  const G = (typeof window !== 'undefined') ? window : globalThis;

  function toCanonName(name) {
    return String(name || '').trim().toLowerCase();
  }

  function parseDecimal(raw) {
    if (raw == null) return null;
    const s = String(raw).trim();
    if (!s) return null;
    const normalized = s.replace(/\s+/g, '').replace(/,/g, '.');
    const num = Number(normalized);
    return Number.isFinite(num) ? num : null;
  }

  function buildSnapshot(parameters, computedParameters) {
    const out = {};

    (parameters || []).forEach((row) => {
      const name = toCanonName(row && row.name);
      if (!name) return;
      const v = parseDecimal(row && row.value);
      if (v == null) return;
      out[name] = v;
    });

    // Keep this tolerant: if backend later provides computed numeric value,
    // we can consume it directly without changing consumer code.
    (computedParameters || []).forEach((row) => {
      const name = toCanonName(row && row.name);
      if (!name) return;
      const hasValue = row && Object.prototype.hasOwnProperty.call(row, 'value');
      if (!hasValue) return;
      const v = parseDecimal(row && row.value);
      if (v == null) return;
      out[name] = v;
    });

    return out;
  }

  const state = {
    projectId: null,
    endpoints: null,
    snapshot: {},
    loadedAt: null,
    inflight: null,
  };

  async function fetchJson(url) {
    const res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) {
      throw new Error('HTTP ' + res.status + ' saat memuat parameter');
    }
    return res.json();
  }

  async function load(projectId, endpoints) {
    if (!projectId) throw new Error('projectId wajib');
    if (!endpoints || !endpoints.parameters || !endpoints.computedParameters) {
      throw new Error('endpoints parameter/computedParameters wajib');
    }

    if (
      state.inflight
      && state.projectId === projectId
      && state.endpoints
      && state.endpoints.parameters === endpoints.parameters
      && state.endpoints.computedParameters === endpoints.computedParameters
    ) {
      return state.inflight;
    }

    state.projectId = projectId;
    state.endpoints = {
      parameters: endpoints.parameters,
      computedParameters: endpoints.computedParameters,
    };

    state.inflight = Promise.all([
      fetchJson(state.endpoints.parameters),
      fetchJson(state.endpoints.computedParameters),
    ]).then(([baseRes, computedRes]) => {
      state.snapshot = buildSnapshot(baseRes.parameters || [], computedRes.computed_parameters || []);
      state.loadedAt = Date.now();
      return state.snapshot;
    }).finally(() => {
      state.inflight = null;
    });

    return state.inflight;
  }

  async function refresh() {
    if (!state.projectId || !state.endpoints) {
      return state.snapshot;
    }
    return load(state.projectId, state.endpoints);
  }

  function getSnapshot() {
    return { ...state.snapshot };
  }

  G.SharedParamStore = {
    load,
    refresh,
    getSnapshot,
    getMeta() {
      return {
        projectId: state.projectId,
        loadedAt: state.loadedAt,
      };
    },
  };
})();
