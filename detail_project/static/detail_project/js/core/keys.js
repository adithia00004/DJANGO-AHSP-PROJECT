// /static/detail_project/js/core/keys.js
(() => {
  const DP = (window.DP = window.DP || {}); 
  DP.core = DP.core || {};
  if (DP.core.keys) return;

  // --- helpers dasar (kompat lama) ---
  function isMod(e) { return e.ctrlKey || e.metaKey; }

  // Abaikan shortcut saat user sedang mengetik di elemen yang seharusnya tidak diganggu.
  // Kecuali handler memang ingin override, ia bisa cek sendiri.
  function shouldIgnore(e) {
    const t = e.target;
    if (!t) return false;
    const tag = (t.tagName || '').toLowerCase();
    const isEditable = t.isContentEditable;
    const isInput = tag === 'input' || tag === 'textarea' || tag === 'select';
    // Jangan abaikan Enter khusus di tombol (button), tapi biarkan default-nya jalan.
    const isButton = tag === 'button';
    // Abaikan jika sedang komposisi IME
    if (e.isComposing) return true;
    // Abaikan jika dalam input/textarea/select atau contenteditable
    if (isEditable) return true;
    if (isInput && !isButton) return true;
    return false;
  }

  // Normalisasi string combo: "Ctrl+S", "Shift+Enter", "Ctrl+Space", "Esc"
  function matchCombo(e, combo) {
    const want = String(combo).toLowerCase().replace(/\s+/g, '');
    const key = (e.key || '').toLowerCase();
    const code = (e.code || '').toLowerCase();

    const needCtrl = /ctrl\+/.test(want) || /cmd\+/.test(want) || /meta\+/.test(want);
    const needShift = /shift\+/.test(want);
    const needAlt = /alt\+/.test(want);

    if (needCtrl && !(e.ctrlKey || e.metaKey)) return false;
    if (!needCtrl && (e.ctrlKey || e.metaKey)) return false;
    if (needShift && !e.shiftKey) return false;
    if (!needShift && e.shiftKey) {
      // kecuali tombolnya memang Shift+Enter yang diinginkan
      if (!(key === 'enter' && needShift)) return false;
    }
    if (needAlt && !e.altKey) return false;
    if (!needAlt && e.altKey) return false;

    // Key target
    if (/\besc(ape)?\b/.test(want)) return key === 'escape';
    if (/\benter\b/.test(want)) return key === 'enter';
    if (/\bspace\b/.test(want)) {
      // beberapa keyboard: key === ' ' / 'Spacebar', lebih stabil pakai code
      return code === 'space' || key === ' ' || key === 'spacebar';
    }
    // huruf/angka umum, contoh: "Ctrl+S", "Ctrl+K"
    const m = want.match(/\+?([a-z0-9])$/);
    if (m) return key === m[1];
    return false;
  }

  // Binding berbasis peta shortcut → handler, aman & scoped
  // options:
  // - scopeSelector: aktif hanya bila event.target berada di dalam elemen ini (default: null = di root)
  // - preventDefault: boolean atau array of combo (default: true untuk 'Ctrl+S' & 'Ctrl+Space')
  // - stopPropagation: boolean (default: false)
  function bindMap(root, map, options = {}) {
    if (!root) return () => {};
    const opts = {
      scopeSelector: options.scopeSelector || null,
      preventDefault: options.preventDefault,
      stopPropagation: !!options.stopPropagation,
    };

    // default PD untuk combo yang umumnya kita override
    const defaultPDCombos = new Set(['ctrl+s', 'cmd+s', 'meta+s', 'ctrl+space', 'cmd+space', 'meta+space']);

    const handler = (e) => {
      if (shouldIgnore(e)) return;
      // Scope check
      if (opts.scopeSelector) {
        const inScope = e.target && e.target.closest && e.target.closest(opts.scopeSelector);
        if (!inScope) return;
      }
      for (const combo in map) {
        if (!Object.prototype.hasOwnProperty.call(map, combo)) continue;
        if (matchCombo(e, combo)) {
          // preventDefault rules
          let doPD = false;
          if (typeof opts.preventDefault === 'boolean') {
            doPD = opts.preventDefault;
          } else if (Array.isArray(opts.preventDefault)) {
            doPD = opts.preventDefault.map(s => s.toLowerCase().replace(/\s+/g,'')).includes(combo.toLowerCase().replace(/\s+/g,''));
          } else {
            doPD = defaultPDCombos.has(combo.toLowerCase().replace(/\s+/g,''));
          }
          if (doPD) e.preventDefault();
          if (opts.stopPropagation) e.stopPropagation();

          try { map[combo](e); } catch (err) { /* swallow to avoid breaking UI */ }
          break;
        }
      }
    };

    root.addEventListener('keydown', handler, false);
    // return unbinder
    return () => root.removeEventListener('keydown', handler, false);
  }

  // API lama (dipertahankan)
  const keysAPI = {
    bindOnce(root, handler) {
      if (!root) return;
      if (root.dataset.dpKeysBound) return;
      root.dataset.dpKeysBound = '1';
      root.addEventListener('keydown', handler, false);
    },
    isSave(e) { return isMod(e) && (e.key || '').toLowerCase() === 's'; },
    isCommandSpace(e) { 
      const key = (e.key || '').toLowerCase();
      const code = (e.code || '').toLowerCase();
      return isMod(e) && (code === 'space' || key === ' ' || key === 'spacebar'); 
    },
    isEnter(e) { return (e.key === 'Enter' && !isMod(e) && !e.shiftKey); },
    isShiftEnter(e) { return (e.key === 'Enter' && e.shiftKey && !isMod(e)); },
    isEsc(e) { return (e.key === 'Escape'); },

    // API baru (opsional, non-breaking)
    bindMap,
    shouldIgnore,
    matchCombo
  };

  DP.core.keys = keysAPI;
})();
