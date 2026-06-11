(() => {
  const global = (window.DP = window.DP || {});
  const moduleName = 'sourceChange';
  if (global[moduleName]) {
    return;
  }

  const memStore = new Map();
  const PREFIX = 'dp.sourceChange.state.';

  function stateKey(projectId) {
    return `${PREFIX}${projectId}`;
  }

  function ensureState(raw) {
    if (!raw || typeof raw !== 'object') {
      return { reload: {}, volume: {} };
    }
    const cloneSection = (section) => {
      if (!section || typeof section !== 'object') {
        return {};
      }
      return Object.entries(section).reduce((acc, [key, value]) => {
        acc[key] = typeof value === 'object' ? { ...value } : { ts: value };
        if (!acc[key].ts) {
          acc[key].ts = new Date().toISOString();
        }
        return acc;
      }, {});
    };
    return {
      reload: cloneSection(raw.reload),
      volume: cloneSection(raw.volume),
    };
  }

  function cloneState(state) {
    return ensureState(state);
  }

  function readState(projectId) {
    const key = stateKey(projectId);
    try {
      const raw = localStorage.getItem(key);
      if (raw) {
        return ensureState(JSON.parse(raw));
      }
    } catch (error) {
      // LocalStorage unavailable; fall back to memory store
      console.warn('[SourceChangeState] localStorage read failed, using memory store', error);
    }
    const fallback = memStore.get(key);
    return ensureState(fallback);
  }

  function writeState(projectId, state) {
    const key = stateKey(projectId);
    try {
      localStorage.setItem(key, JSON.stringify(state));
      memStore.delete(key);
    } catch (error) {
      console.warn('[SourceChangeState] localStorage write failed, storing in memory', error);
      memStore.set(key, JSON.parse(JSON.stringify(state)));
    }
  }

  function sanitizeIds(ids) {
    if (!ids) return [];
    const list = Array.isArray(ids) ? ids : [ids];
    return list
      .map((value) => Number(value))
      .filter((value) => Number.isFinite(value) && value > 0);
  }

  function sameIdSet(a, b) {
    if (a.length !== b.length) return false;
    const set = new Set(a);
    return b.every((id) => set.has(id));
  }

  function getCsrfToken() {
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  async function ackServer(projectId, payload) {
    if (!projectId || !payload || typeof payload !== 'object') return null;
    try {
      const response = await fetch(`/detail_project/api/project/${projectId}/source-change/ack/`, {
        method: 'POST',
        credentials: 'same-origin',
        keepalive: true,
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return await response.json().catch(() => null);
    } catch (error) {
      console.warn('[SourceChangeState] ack to server failed', error);
      return null;
    }
  }

  function emit(action, detail) {
    const payload = { action, ...detail };
    window.dispatchEvent(
      new CustomEvent('dp:source-change', {
        detail: payload,
      }),
    );
  }

  function pushFlags(projectId, flags = {}) {
    if (!projectId) return;
    const state = readState(projectId);
    const now = new Date().toISOString();
    const addedReload = [];
    const addedVolume = [];

    sanitizeIds(flags.reload_job_ids).forEach((id) => {
      const key = String(id);
      if (!state.reload[key]) {
        state.reload[key] = { ts: now };
        addedReload.push(id);
      }
    });

    sanitizeIds(flags.volume_reset_job_ids).forEach((id) => {
      const key = String(id);
      if (!state.volume[key]) {
        state.volume[key] = { ts: now };
        addedVolume.push(id);
      }
    });

    if (!addedReload.length && !addedVolume.length) {
      return;
    }

    writeState(projectId, state);
    emit('push', {
      projectId,
      addedReloadIds: addedReload,
      addedVolumeIds: addedVolume,
      state: cloneState(state),
    });
  }

  function syncFlags(projectId, flags = {}) {
    if (!projectId) return;
    const nextReload = sanitizeIds(flags.reload_job_ids);
    const nextVolume = sanitizeIds(flags.volume_reset_job_ids);
    const state = readState(projectId);
    const currentReload = Object.keys(state.reload).map((key) => Number(key)).filter((id) => Number.isFinite(id));
    const currentVolume = Object.keys(state.volume).map((key) => Number(key)).filter((id) => Number.isFinite(id));

    if (sameIdSet(currentReload, nextReload) && sameIdSet(currentVolume, nextVolume)) {
      return;
    }

    const now = new Date().toISOString();
    const nextState = { reload: {}, volume: {} };
    nextReload.forEach((id) => {
      const key = String(id);
      nextState.reload[key] = state.reload[key] || { ts: now };
    });
    nextVolume.forEach((id) => {
      const key = String(id);
      nextState.volume[key] = state.volume[key] || { ts: now };
    });

    writeState(projectId, nextState);
    emit('sync', {
      projectId,
      syncedReloadIds: nextReload,
      syncedVolumeIds: nextVolume,
      state: cloneState(nextState),
    });
  }

  function markReloaded(projectId, jobIds) {
    if (!projectId) return;
    const ids = sanitizeIds(jobIds);
    if (!ids.length) return;
    const state = readState(projectId);
    const removed = [];
    ids.forEach((id) => {
      const key = String(id);
      if (state.reload[key]) {
        delete state.reload[key];
        removed.push(id);
      }
    });
    if (!removed.length) return;
    writeState(projectId, state);
    emit('resolve', {
      projectId,
      resolvedReloadIds: removed,
      resolvedVolumeIds: [],
      state: cloneState(state),
    });
    return ackServer(projectId, { reload_job_ids: removed }).then((serverState) => {
      if (serverState && Array.isArray(serverState.pending_reload_job_ids) && Array.isArray(serverState.pending_volume_reset_job_ids)) {
        syncFlags(projectId, {
          reload_job_ids: serverState.pending_reload_job_ids,
          volume_reset_job_ids: serverState.pending_volume_reset_job_ids,
        });
      }
      return serverState;
    });
  }

  function markVolumeResolved(projectId, jobIds) {
    if (!projectId) return;
    const ids = sanitizeIds(jobIds);
    if (!ids.length) return;
    const state = readState(projectId);
    const removed = [];
    ids.forEach((id) => {
      const key = String(id);
      if (state.volume[key]) {
        delete state.volume[key];
        removed.push(id);
      }
    });
    if (!removed.length) return;
    writeState(projectId, state);
    emit('resolve', {
      projectId,
      resolvedReloadIds: [],
      resolvedVolumeIds: removed,
      state: cloneState(state),
    });
    return ackServer(projectId, { volume_reset_job_ids: removed }).then((serverState) => {
      if (serverState && Array.isArray(serverState.pending_reload_job_ids) && Array.isArray(serverState.pending_volume_reset_job_ids)) {
        syncFlags(projectId, {
          reload_job_ids: serverState.pending_reload_job_ids,
          volume_reset_job_ids: serverState.pending_volume_reset_job_ids,
        });
      }
      return serverState;
    });
  }

  function listReloadJobs(projectId) {
    const state = readState(projectId);
    return Object.keys(state.reload).map((key) => Number(key));
  }

  function listVolumeJobs(projectId) {
    const state = readState(projectId);
    return Object.keys(state.volume).map((key) => Number(key));
  }

  function getState(projectId) {
    return cloneState(readState(projectId));
  }

  window.addEventListener('storage', (event) => {
    if (!event.key || !event.key.startsWith(PREFIX)) return;
    const projectId = Number(event.key.replace(PREFIX, ''));
    if (!Number.isFinite(projectId) || projectId <= 0) return;
    const state = readState(projectId);
    emit('storage', {
      projectId,
      state: cloneState(state),
    });
  });

  global[moduleName] = {
    pushFlags,
    syncFlags,
    markReloaded,
    markVolumeResolved,
    listReloadJobs,
    listVolumeJobs,
    getState,
  };
})();
