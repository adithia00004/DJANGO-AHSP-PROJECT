(function() {
  'use strict';

  const APP_GLOBAL = 'KelolaTahapanPageApp';
  const LEGACY_GLOBAL = 'JadwalPekerjaanApp';
  const LOG_PREFIX = '[KelolaTahapanPageApp]';

  if (window[APP_GLOBAL]) {
    return;
  }

  const modules = new Map();
  const events = new Map();

  const state = {
    createdAt: new Date().toISOString(),
    pageId: 'kelola_tahapan',
    pageName: 'Kelola Tahapan',
    shared: {},
    meta: {},
    flags: new Map(),
  };

  const EVENT_MAP = {
    MODULE_REGISTERED: 'module:registered',
    PAGE_DOM_READY: 'kelolaTahapan:dom-ready',
    PAGE_LOADING: 'kelolaTahapan:loading',
    PAGE_DATA_LOAD_START: 'kelolaTahapan:data-load:start',
    PAGE_DATA_LOAD_SUCCESS: 'kelolaTahapan:data-load:success',
    PAGE_DATA_LOAD_ERROR: 'kelolaTahapan:data-load:error',
    PAGE_MODULES_REGISTERED: 'kelolaTahapan:modules-registered',
  };

  const LEGACY_EVENT_ALIASES = {
    'kelolaTahapan:dom-ready': 'jadwal:dom-ready',
    'kelolaTahapan:loading': 'jadwal:loading',
    'kelolaTahapan:data-load:start': 'jadwal:data-load:start',
    'kelolaTahapan:data-load:success': 'jadwal:data-load:success',
    'kelolaTahapan:data-load:error': 'jadwal:data-load:error',
    'kelolaTahapan:modules-registered': 'jadwal:modules-registered',
  };

  function ensureEventBucket(eventName) {
    if (!events.has(eventName)) {
      events.set(eventName, new Set());
    }
    return events.get(eventName);
  }

  function emit(eventName, payload) {
    const deliver = (name) => {
      const bucket = events.get(name);
      if (!bucket) {
        return;
      }
      bucket.forEach((handler) => {
        try {
          handler(payload, api);
        } catch (error) {
          console.error(LOG_PREFIX, 'Event handler error for', name, error);
        }
      });
    };

    deliver(eventName);

    const aliasName = LEGACY_EVENT_ALIASES[eventName];
    if (aliasName) {
      deliver(aliasName);
    }
  }

  function on(eventName, handler) {
    if (typeof handler !== 'function') {
      console.warn(LOG_PREFIX, 'Tried to register non-function handler for', eventName);
      return () => {};
    }
    const bucket = ensureEventBucket(eventName);
    bucket.add(handler);
    return () => bucket.delete(handler);
  }

  function off(eventName, handler) {
    const bucket = events.get(eventName);
    if (!bucket) {
      return;
    }
    bucket.delete(handler);
  }

  function registerModule(name, definition) {
    if (!name) {
      throw new Error(`${LOG_PREFIX} Module name is required`);
    }
    if (modules.has(name)) {
      console.warn(`${LOG_PREFIX} Module "${name}" already registered.`, modules.get(name));
      return modules.get(name);
    }

    const moduleRecord = Object.assign({}, definition || {});
    modules.set(name, moduleRecord);

    emit('module:registered', { name, module: moduleRecord });
    if (typeof moduleRecord.onRegister === 'function') {
      try {
        moduleRecord.onRegister(api);
      } catch (error) {
        console.error(LOG_PREFIX, 'onRegister error for', name, error);
      }
    }

    return moduleRecord;
  }

  function getModule(name) {
    return modules.get(name);
  }

  function hasModule(name) {
    return modules.has(name);
  }

  const api = {
    version: '0.2.0',
    pageId: state.pageId,
    pageName: state.pageName,
    state,
    modules,
    registerModule,
    getModule,
    hasModule,
    on,
    off,
    emit,
    log: {
      info: (...args) => console.info(LOG_PREFIX, ...args),
      warn: (...args) => console.warn(LOG_PREFIX, ...args),
      error: (...args) => console.error(LOG_PREFIX, ...args),
    },
    constants: {
      events: Object.assign({}, EVENT_MAP, {
        LEGACY_ALIASES: Object.assign({}, LEGACY_EVENT_ALIASES),
      }),
    },
    legacy: {
      events: Object.assign({}, LEGACY_EVENT_ALIASES),
    },
  };

  window[APP_GLOBAL] = api;
  window[LEGACY_GLOBAL] = api;
  api.log.info('Kelola Tahapan page bootstrap initialized');
})();
