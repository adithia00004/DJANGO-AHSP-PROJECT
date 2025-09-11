/* volume_pekerjaan.js — Page logic (FE-only)
 * Fitur:
 * - Prefill volume via GET /detail_project/api/project/<id>/rekap/
 * - Input angka biasa & formula (= …) dengan variabel global
 * - Variabel global disimpan di localStorage per proyek (offcanvas UI)
 * - Dirty-submit (kirim delta saja) ke endpoint lama: /volume-pekerjaan/save/
 * - Format tampilan angka Indonesia: 1.000,33 (2 desimal, HALF_UP)
 * - Autocomplete variabel saat mengetik di mode formula (dropdown saran)
 * - Keyboard UX: Enter/Shift+Enter navigasi; Ctrl/⌘+S untuk simpan
 * - Unsaved changes guard (peringatan saat meninggalkan halaman jika ada perubahan)
 *
 * Catatan:
 * - Tidak mengubah endpoint/kontrak API.
 * - Mengandalkan VolFormula.evaluate(expr, variables, opts) dari vol_formula_engine.js
 */
(function () {
  const root = document.getElementById('vol-app');
  if (!root) return;

  // --- Konteks dasar
  const projectId = root.dataset.projectId || root.dataset.pid;
  const qtyPlaces = 2; // tampilkan & bulatkan UI ke 2 desimal; DB tetap 3dp (schema lama)
  const qtyStep = qtyPlaces === 0 ? '1' : ('0.' + '0'.repeat(qtyPlaces - 1) + '1');

  // --- State in-memory
  const rows = Array.from(root.querySelectorAll('#vp-table tbody tr[data-pekerjaan-id]'));
  const originalValueById = {};  // baseline dari prefill (number)
  const rawInputById = {};       // string yang user ketik (bisa '= …')
  const currentValueById = {};   // nilai numerik terkini (hasil normalisasi/evaluasi)
  const fxModeById = {};         // boolean: toggle formula per baris
  const dirtySet = new Set();    // id yang berubah dari original
  let variables = {};            // variabel global proyek {name: number}

  // --- Elemen UI
  const btnSave = document.getElementById('btn-save-vol');
  const totalEl = document.getElementById('vp-total'); // boleh null (tfoot dihapus)

  // Offcanvas Variabel
  const varTable = document.getElementById('vp-var-table');
  const btnVarAdd = document.getElementById('vp-var-add');
  const btnVarInsert = document.getElementById('vp-var-insert');
  const offcanvasEl = document.getElementById('vpVarOffcanvas');

  // --- Util umum
  function getCsrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }
  function roundHalfUp(x, places) {
    const p = Math.max(0, Math.min(20, places | 0));
    const factor = Math.pow(10, p);
    return (x >= 0)
      ? Math.floor(x * factor + 0.5) / factor
      : Math.ceil(x * factor - 0.5) / factor;
  }
  // Format angka Indonesia (ribuan '.', desimal ',')
  function formatId(num, places) {
    try {
      return new Intl.NumberFormat('id-ID', {
        minimumFractionDigits: places,
        maximumFractionDigits: places
      }).format(num);
    } catch {
      // fallback
      return Number(num).toFixed(places);
    }
  }
  // Normalisasi string angka lokal → “dot-decimal” agar bisa diparse Number/Decimal
  function normalizeLocaleNumericString(input) {
    let s = String(input ?? '').trim();
    if (!s) return s;
    s = s.replace(/\s+/g, '').replace(/_/g, ''); // hapus spasi/underscore
    const hasComma = s.includes(',');
    const hasDot = s.includes('.');
    if (hasComma && hasDot) {
      // Asumsi id-ID: '.' ribuan, ',' desimal
      s = s.replace(/\./g, '');
      s = s.replace(',', '.');
    } else if (hasComma) {
      s = s.replace(',', '.');
    }
    return s;
  }
  function normQty(val) {
    if (val === '' || val === null || typeof val === 'undefined') return '';
    const s = normalizeLocaleNumericString(val);
    let num = Number(s);
    if (!Number.isFinite(num)) return '';
    if (num < 0) num = 0;
    const rounded = roundHalfUp(num, qtyPlaces);
    return formatId(rounded, qtyPlaces); // tampil sebagai id-ID
  }
  function parseNumberOrEmpty(val) {
    const s = normalizeLocaleNumericString(val);
    if (!s) return '';
    const n = Number(s);
    return Number.isFinite(n) ? n : '';
  }
  function setBtnSaveEnabled() {
    const dirty = dirtySet.size !== 0;
    if (btnSave) btnSave.disabled = !dirty;
    // NEW: tandai halaman kotor untuk beforeunload guard
    window.__vpDirty = dirty;
  }
  function recalcTotal() {
    let sum = 0;
    rows.forEach(tr => {
      const id = parseInt(tr.dataset.pekerjaanId, 10);
      const v = currentValueById[id] ?? 0;
      if (Number.isFinite(v)) sum += v;
    });
    const rounded = roundHalfUp(sum, qtyPlaces);
    if (totalEl) totalEl.textContent = formatId(rounded, qtyPlaces);
  }
  function storageKeyVars() { return `volvars:${projectId}`; }
  function storageKeyForms() { return `volform:${projectId}`; }
  function loadVars() {
    try {
      const raw = localStorage.getItem(storageKeyVars());
      variables = raw ? JSON.parse(raw) : {};
      if (typeof variables !== 'object' || !variables) variables = {};
    } catch { variables = {}; }
  }
  function saveVars() {
    localStorage.setItem(storageKeyVars(), JSON.stringify(variables));
  }
  function loadFormulas() {
    try {
      const raw = localStorage.getItem(storageKeyForms());
      const obj = raw ? JSON.parse(raw) : {};
      if (!obj || typeof obj !== 'object') return {};
      return obj;
    } catch { return {}; }
  }
  function saveFormulas(map) {
    localStorage.setItem(storageKeyForms(), JSON.stringify(map));
  }
  // --- NEW: angkat offcanvas ke <body> agar lepas dari stacking context kontainer
  (function liftOffcanvasToBody() {
    try {
      if (offcanvasEl && offcanvasEl.parentElement !== document.body) {
        document.body.appendChild(offcanvasEl);
      }
    } catch (_) { /* no-op */ }
  })();

  // --- Panel Variabel Proyek (CRUD FE-only)
  function renderVarTable() {
    const tbody = varTable.querySelector('tbody');
    tbody.innerHTML = '';
    const names = Object.keys(variables);
    if (names.length === 0) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td colspan="3" class="text-muted">Belum ada variabel.</td>`;
      tbody.appendChild(tr);
      return;
    }
    names.sort().forEach(name => {
      const val = variables[name];
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><input type="text" class="form-control form-control-sm var-name" value="${name}" aria-label="Nama variabel"></td>
        <td><input type="text" class="form-control form-control-sm var-value" value="${val}" aria-label="Nilai variabel"></td>
        <td class="text-end">
          <button type="button" class="btn btn-sm btn-outline-danger var-del">Hapus</button>
        </td>`;
      // Klik baris → pilih variabel (untuk tombol "Sisipkan")
      tr.addEventListener('click', () => {
        tbody.querySelectorAll('tr').forEach(r => r.classList.remove('table-primary'));
        tr.classList.add('table-primary');
        tr.dataset.selected = '1';
      });
      // events
      tr.querySelector('.var-name').addEventListener('change', e => {
        const newName = String(e.target.value || '').trim();
        if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(newName)) {
          alert('Nama variabel harus berupa identifier (huruf/underscore, lalu huruf/angka/underscore).');
          e.target.value = name;
          return;
        }
        if (newName !== name) {
          if (variables[newName] != null) {
            alert('Nama variabel sudah ada.');
            e.target.value = name;
            return;
          }
          const v = variables[name];
          delete variables[name];
          variables[newName] = Number(v) || 0;
          saveVars();
          // re-evaluate semua formula
          reevaluateAllFormulas();
          renderVarTable();
        }
      });
      tr.querySelector('.var-value').addEventListener('change', e => {
        const n = parseNumberOrEmpty(e.target.value);
        if (n === '') {
          alert('Nilai variabel harus berupa angka.');
          e.target.value = val;
          return;
        }
        variables[name] = n;
        saveVars();
        reevaluateAllFormulas();
      });
      tr.querySelector('.var-del').addEventListener('click', () => {
        if (!confirm(`Hapus variabel "${name}"?`)) return;
        delete variables[name];
        saveVars();
        reevaluateAllFormulas();
        renderVarTable();
      });
      tbody.appendChild(tr);
    });
  }
  if (btnVarAdd) {
    btnVarAdd.addEventListener('click', () => {
      const name = prompt('Nama variabel (mis. panjang, lebar, tinggi):');
      if (!name) return;
      const trimmed = name.trim();
      if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(trimmed)) {
        alert('Nama variabel tidak valid. Gunakan huruf/underscore, lalu huruf/angka/underscore.');
        return;
      }
      if (variables[trimmed] != null) {
        alert('Nama variabel sudah ada.');
        return;
      }
      const valStr = prompt(`Nilai untuk ${trimmed}:`, '0');
      const n = parseNumberOrEmpty(valStr);
      if (n === '') {
        alert('Nilai variabel harus berupa angka.');
        return;
      }
      variables[trimmed] = n;
      saveVars();
      renderVarTable();
      reevaluateAllFormulas();
    });
  }

  // Tombol SISIPKAN → sisipkan nama variabel terpilih ke input aktif (caret)
  if (btnVarInsert) {
    btnVarInsert.addEventListener('click', () => {
      const tbody = varTable.querySelector('tbody');
      const selected = Array.from(tbody.querySelectorAll('tr')).find(tr => tr.classList.contains('table-primary'));
      if (!selected) {
        alert('Pilih variabel dulu (klik salah satu baris).');
        return;
      }
      const nameInput = selected.querySelector('.var-name');
      const varName = nameInput ? String(nameInput.value || '').trim() : '';
      if (!varName) return;
      // target = input qty yang sedang fokus
      const active = document.activeElement;
      if (!active || !active.classList || !active.classList.contains('qty-input')) {
        alert('Fokuskan kursor di kolom Quantity terlebih dahulu.');
        return;
      }
      // Pastikan mode formula; jika tidak, otomatis aktifkan
      if (!String(active.value || '').trim().startsWith('=')) {
        active.value = '=' + (active.value || '');
      }
      // sisipkan pada caret
      const start = active.selectionStart ?? active.value.length;
      const end = active.selectionEnd ?? active.value.length;
      const before = active.value.slice(0, start);
      const after = active.value.slice(end);
      active.value = before + varName + after;
      // pindahkan caret ke belakang variabel
      const pos = before.length + varName.length;
      active.setSelectionRange(pos, pos);
      // trigger evaluasi
      const tr = active.closest('tr');
      const id = parseInt(tr.dataset.pekerjaanId, 10);
      const preview = tr.querySelector('.fx-preview');
      handleInputChange(id, active, preview, false);
    });
  }

  // --- SUGGESTIONS (autocomplete variabel di input formula)
  const suggestState = new WeakMap(); // inputEl -> {box, ul, items, activeIdx}

  function getCaretIdentifier(inputEl) {
    const value = String(inputEl.value || '');
    const pos = inputEl.selectionStart ?? value.length;
    // Harus dalam mode formula
    if (!value.trim().startsWith('=')) return null;
    // Cari batas kiri/kanan untuk token identifier (A-Za-z0-9_)
    let start = pos, end = pos;
    const isPart = c => /[A-Za-z0-9_]/.test(c);
    while (start > 0 && isPart(value[start - 1])) start--;
    while (end < value.length && isPart(value[end])) end++;
    // Validasi huruf pertama
    const word = value.slice(start, end);
    if (!word) return null;
    if (!/^[A-Za-z_][A-Za-z0-9_]*$/.test(word)) return null;
    return { word, start, end };
  }

  function ensureSuggestBox(inputEl) {
    let state = suggestState.get(inputEl);
    if (state && state.box && state.ul) return state;
    // anchor = wrapper flex-grow-1 (fallback ke parent)
    const wrap = inputEl.closest('.flex-grow-1') || inputEl.parentElement;
    const box = document.createElement('div');
    box.className = 'vp-suggest';
    box.style.display = 'none';
    const ul = document.createElement('ul');
    box.appendChild(ul);
    wrap.appendChild(box);
    state = { box, ul, items: [], activeIdx: -1 };
    suggestState.set(inputEl, state);
    return state;
  }

  function hideSuggest(inputEl) {
    const state = suggestState.get(inputEl);
    if (!state) return;
    state.box.style.display = 'none';
    state.items = [];
    state.activeIdx = -1;
    state.ul.innerHTML = '';
  }

  function showSuggest(inputEl, items) {
    const state = ensureSuggestBox(inputEl);
    state.items = items.slice(0, 8); // batasi 8
    state.activeIdx = state.items.length ? 0 : -1;
    state.ul.innerHTML = '';
    if (!state.items.length) {
      state.box.style.display = 'none';
      return;
    }
    state.items.forEach((it, idx) => {
      const li = document.createElement('li');
      li.className = idx === state.activeIdx ? 'active' : '';
      li.innerHTML = `<span class="s-name">${it.name}</span><span class="s-value">${formatId(it.value, qtyPlaces)}</span>`;
      li.addEventListener('mousedown', (ev) => {
        ev.preventDefault(); // jangan hilang fokus
        applySuggestion(inputEl, it.name);
      });
      state.ul.appendChild(li);
    });
    state.box.style.display = 'block';
  }

  function moveActive(inputEl, delta) {
    const state = suggestState.get(inputEl);
    if (!state || !state.items.length) return;
    state.activeIdx = (state.activeIdx + delta + state.items.length) % state.items.length;
    // refresh active class
    const lis = state.ul.querySelectorAll('li');
    lis.forEach((li, i) => li.classList.toggle('active', i === state.activeIdx));
  }

  function applyActiveSuggestion(inputEl) {
    const state = suggestState.get(inputEl);
    if (!state || state.activeIdx < 0) return false;
    const it = state.items[state.activeIdx];
    if (!it) return false;
    applySuggestion(inputEl, it.name);
    return true;
  }

  function applySuggestion(inputEl, varName) {
    const value = String(inputEl.value || '');
    const caret = inputEl.selectionStart ?? value.length;
    // Cari identifier di caret; kalau tidak ada, tinggal sisipkan
    const idf = getCaretIdentifier(inputEl);
    let before, after;
    if (idf) {
      before = value.slice(0, idf.start);
      after = value.slice(idf.end);
    } else {
      before = value.slice(0, caret);
      after = value.slice(caret);
    }
    // Pastikan ada '=' di awal
    const ensureEq = value.trim().startsWith('=') ? '' : '=';
    inputEl.value = ensureEq + before + varName + after;
    const pos = (ensureEq ? 1 : 0) + before.length + varName.length;
    inputEl.setSelectionRange(pos, pos);
    // Trigger evaluasi
    const tr = inputEl.closest('tr');
    const id = parseInt(tr.dataset.pekerjaanId, 10);
    const preview = tr.querySelector('.fx-preview');
    handleInputChange(id, inputEl, preview, false);
    hideSuggest(inputEl);
  }

  function updateSuggestions(inputEl, id) {
    const raw = String(inputEl.value || '');
    if (!isFormulaMode(id, raw)) { hideSuggest(inputEl); return; }
    const names = Object.keys(variables || {});
    if (!names.length) { hideSuggest(inputEl); return; }
    const idf = getCaretIdentifier(inputEl);
    // 🔁 Perbaikan UX: jika baru ketik "=" (belum ada identifier), tampilkan SEMUA variabel
    if (!idf) {
      const allItems = names
        .sort((a, b) => a.localeCompare(b, 'id'))
        .map(n => ({ name: n, value: Number(variables[n] || 0) }));
      showSuggest(inputEl, allItems);
      return;
    }
    const prefix = idf.word.toLowerCase();
    const items = names
      .filter(n => n.toLowerCase().startsWith(prefix))
      .sort((a, b) => a.localeCompare(b, 'id'))
      .map(n => ({ name: n, value: Number(variables[n] || 0) }));
    if (!items.length) { hideSuggest(inputEl); return; }
    showSuggest(inputEl, items);
  }

  // --- Wiring baris pekerjaan
  const formulaState = loadFormulas(); // { [pekerjaanId]: { raw: string, fx: boolean } }

  // Helper navigasi keyboard antar input
  function collectQtyInputs() {
    return Array.from(document.querySelectorAll('#vp-table .qty-input'));
  }
  function focusNextFrom(currentEl, delta) {
    const inputs = collectQtyInputs();
    const idx = inputs.indexOf(currentEl);
    if (idx === -1) return;
    let next = idx + delta;
    if (next < 0) next = 0;
    if (next >= inputs.length) next = inputs.length - 1;
    const tgt = inputs[next];
    if (tgt) {
      tgt.focus();
      try { tgt.select(); } catch (_) {}
    }
  }

  function bindRow(tr) {
    const id = parseInt(tr.dataset.pekerjaanId, 10);
    const input = tr.querySelector('.qty-input');
    const fxBtn = tr.querySelector('.fx-toggle');
    const preview = tr.querySelector('.fx-preview');

    // Set atribut & default
    input.setAttribute('step', qtyStep);
    input.setAttribute('min', '0');

    // Restore formula state (localStorage)
    const f = formulaState[id] || {};
    if (typeof f.fx === 'boolean') {
      fxModeById[id] = !!f.fx;
      fxBtn.setAttribute('aria-pressed', String(!!f.fx));
      if (f.fx) fxBtn.classList.add('active');
    } else {
      fxModeById[id] = false;
    }
    if (typeof f.raw === 'string' && f.raw.trim()) {
      rawInputById[id] = f.raw;
      input.value = f.raw; // tampilkan raw formula agar user tahu dia di mode formula
    }

    // Toggle handler
    fxBtn.addEventListener('click', () => {
      const newState = !(fxModeById[id]);
      fxModeById[id] = newState;
      fxBtn.setAttribute('aria-pressed', String(newState));
      fxBtn.classList.toggle('active', newState);
      // Jika baru ON dan input tidak diawali '=', tambahkan '=' agar UX jelas
      if (newState && input.value.trim() && !String(input.value).trim().startsWith('=')) {
        input.value = '=' + input.value.trim();
      }
      handleInputChange(id, input, preview, /*fromToggle*/true);
      // Simpan ke localStorage
      persistRowFormula(id);
      // Perbarui suggestions
      updateSuggestions(input, id);
    });

    // Input & blur
    let debTimer = null;
    input.addEventListener('input', () => {
      clearTimeout(debTimer);
      // update suggestions segera (tanpa delay) agar terasa responsif
      updateSuggestions(input, id);
      debTimer = setTimeout(() => handleInputChange(id, input, preview, false), 120);
    });
    input.addEventListener('blur', () => {
      // normalisasi tampilan angka biasa di blur
      if (!isFormulaMode(id, input.value)) {
        const normalized = normQty(input.value);
        if (normalized !== '') input.value = normalized;
      }
      // sembunyikan suggestions sedikit terlambat agar klik item tetap tertangkap
      setTimeout(() => hideSuggest(input), 120);
    });
    input.addEventListener('focus', () => {
      // saat fokus kembali, tampilkan lagi jika relevan
      updateSuggestions(input, id);
    });

    // Keyboard UX (suggestion + navigasi + quick save)
    input.addEventListener('keydown', (ev) => {
      // Ctrl/⌘ + S => Simpan
      if ((ev.ctrlKey || ev.metaKey) && (ev.key === 's' || ev.key === 'S')) {
        ev.preventDefault();
        if (btnSave && !btnSave.disabled) btnSave.click();
        return;
      }

      const state = suggestState.get(input);
      const suggestVisible = state && state.box && state.box.style.display !== 'none' && state.items.length > 0;

      // Navigasi di popup suggest
      if (suggestVisible) {
        if (ev.key === 'ArrowDown') { ev.preventDefault(); moveActive(input, +1); return; }
        if (ev.key === 'ArrowUp')   { ev.preventDefault(); moveActive(input, -1); return; }
        if (ev.key === 'Enter') {
          // bila ada pilihan aktif, pakai dulu; jika tidak ada, lanjut ke navigasi baris
          const applied = applyActiveSuggestion(input);
          if (applied) { ev.preventDefault(); return; }
          // jatuh ke navigasi baris (di bawah)
        }
        if (ev.key === 'Escape') { hideSuggest(input); return; }
      }

      // Enter => pindah baris; Shift+Enter => baris sebelumnya
      if (ev.key === 'Enter') {
        ev.preventDefault();
        focusNextFrom(input, ev.shiftKey ? -1 : +1);
      }
    });
  }
  rows.forEach(bindRow);

  function isFormulaMode(id, rawStr) {
    const explicitFx = !!fxModeById[id];
    const startsEq = String(rawStr || '').trim().startsWith('=');
    return explicitFx || startsEq;
  }

  function persistRowFormula(id) {
    const map = loadFormulas();
    map[id] = {
      raw: rawInputById[id] || '',
      fx: !!fxModeById[id]
    };
    saveFormulas(map);
  }

  function handleInputChange(id, inputEl, previewEl, fromToggle) {
    const raw = String(inputEl.value || '');
    rawInputById[id] = raw;

    // Bersihkan status visual
    inputEl.classList.remove('is-invalid', 'is-valid');
    inputEl.removeAttribute('title');
    if (previewEl) previewEl.textContent = '';

    if (isFormulaMode(id, raw)) {
      // pastikan ada '=' di awal agar konsisten UX
      const expr = raw.startsWith('=') ? raw : ('=' + raw);
      try {
        // Evaluasi aman via engine
        if (typeof VolFormula === 'undefined' || !VolFormula.evaluate) {
          throw new Error('Formula engine tidak tersedia');
        }
        let val = VolFormula.evaluate(expr, variables, { clampMinZero: true });
        if (!Number.isFinite(val) || val < 0) val = 0;
        const rounded = roundHalfUp(val, qtyPlaces);
        currentValueById[id] = rounded;

        // Preview & visual
        if (previewEl) {
          previewEl.textContent = `${expr}  →  ${formatId(rounded, qtyPlaces)}`;
        }
        inputEl.classList.add('is-valid');

        // Dirty tracking
        updateDirty(id);
      } catch (e) {
        inputEl.classList.add('is-invalid');
        const msg = (e && e.message) ? e.message : 'Formula error';
        inputEl.setAttribute('title', msg);
        // Jangan ubah currentValue jika gagal; hanya preview error
      }
      // Persist state formula
      persistRowFormula(id);
    } else {
      // Mode angka biasa
      const n = parseNumberOrEmpty(raw);
      if (n === '') {
        // kosong → tidak update currentValue; biarkan user mengetik
        if (previewEl) previewEl.textContent = '';
      } else {
        const clamped = n < 0 ? 0 : n;
        const rounded = roundHalfUp(clamped, qtyPlaces);
        currentValueById[id] = rounded;
        inputEl.classList.add('is-valid');
      }
      updateDirty(id);
      persistRowFormula(id); // simpan raw kosong juga, agar toggle state tetap
    }
    recalcTotal();
    setBtnSaveEnabled();
  }

  function updateDirty(id) {
    const cur = currentValueById[id];
    const base = originalValueById[id] ?? 0;
    // compare in fixed dp to avoid float noise
    const a = Number.isFinite(cur) ? roundHalfUp(cur, qtyPlaces) : 0;
    const b = Number.isFinite(base) ? roundHalfUp(base, qtyPlaces) : 0;
    if (a !== b) dirtySet.add(id); else dirtySet.delete(id);
  }

  function reevaluateAllFormulas() {
    rows.forEach(tr => {
      const id = parseInt(tr.dataset.pekerjaanId, 10);
      const input = tr.querySelector('.qty-input');
      const preview = tr.querySelector('.fx-preview');
      const raw = String(rawInputById[id] || input.value || '');
      if (!raw.trim()) return;
      if (isFormulaMode(id, raw)) {
        handleInputChange(id, input, preview, false);
      }
    });
    recalcTotal();
    setBtnSaveEnabled();
  }

  // helper: rebuild tbody with groups (Klasifikasi/Sub) dari tree endpoint
  async function enhanceWithGroups() {
    try {
      const res = await fetch(`/detail_project/api/project/${projectId}/list-pekerjaan/tree/`, { credentials: 'same-origin' });
      const json = await res.json().catch(() => ({}));
      if (!json || !json.ok || !Array.isArray(json.klasifikasi)) return; // fallback flat
      const tbody = document.querySelector('#vp-table tbody');
      tbody.innerHTML = '';
      let counter = 0;
      json.klasifikasi.forEach(k => {
        // header klasifikasi
        const trK = document.createElement('tr');
        trK.className = 'vp-klass';
        trK.innerHTML = `<td colspan="5">${k.name || '(Tanpa Klasifikasi)'}</td>`;
        tbody.appendChild(trK);
        (k.sub || []).forEach(s => {
          // header sub
          const trS = document.createElement('tr');
          trS.className = 'vp-sub';
          trS.innerHTML = `<td colspan="5">${s.name || '(Tanpa Sub)'}</td>`;
          tbody.appendChild(trS);
          // pekerjaan
          (s.pekerjaan || []).forEach(p => {
            counter += 1;
            const tr = document.createElement('tr');
            tr.dataset.pekerjaanId = p.id;
            tr.innerHTML = `
              <td>${counter}</td>
              <td class="text-monospace">${p.snapshot_kode || ''}</td>
              <td class="text-wrap">${p.snapshot_uraian || ''}</td>
              <td>${p.snapshot_satuan || ''}</td>
              <td>
                <div class="d-flex align-items-start gap-2 vp-cell">
                  <button type="button" class="btn btn-outline-secondary btn-sm fx-toggle"
                          title="Mode formula (gunakan awalan =)" aria-pressed="false">fx</button>
                  <div class="flex-grow-1">
                    <input type="text" inputmode="decimal" class="form-control form-control-sm qty-input" aria-label="Quantity">
                    <div class="form-text fx-preview text-muted small" style="min-height:1rem;"></div>
                  </div>
                </div>
              </td>`;
            tbody.appendChild(tr);
            bindRow(tr);
          });
        });
      });
      // update rows reference
      while (rows.length) rows.pop();
      document.querySelectorAll('#vp-table tbody tr[data-pekerjaan-id]').forEach(tr => rows.push(tr));
    } catch (e) {
      console.warn('Enhance groups gagal', e);
    }
  }

  // --- Prefill nilai dari rekap (tanpa ubah BE)
  (async function prefill() {
    try {
      const res = await fetch(`/detail_project/api/project/${projectId}/rekap/`, { credentials: 'same-origin' });
      const json = await res.json().catch(() => ({}));
      const volMap = {};
      if (json && json.rows && Array.isArray(json.rows)) {
        json.rows.forEach(r => {
          if (r && typeof r.pekerjaan_id === 'number') {
            const v = Number(r.volume || 0);
            volMap[r.pekerjaan_id] = Number.isFinite(v) ? v : 0;
          }
        });
      }
      // Bangun ulang tabel berkelompok (tidak wajib; aman bila gagal)
      await enhanceWithGroups();
      // Isi ke UI
      rows.forEach(tr => {
        const id = parseInt(tr.dataset.pekerjaanId, 10);
        const input = tr.querySelector('.qty-input');
        const preview = tr.querySelector('.fx-preview');
        const base = Number(volMap[id] || 0);
        originalValueById[id] = base;
        currentValueById[id] = base;
        // Tampilkan base dengan format Indonesia (kosongkan jika 0 untuk tampilan ringkas)
        input.value = base ? formatId(base, qtyPlaces) : (base === 0 ? '' : '');
        // Jika ada raw formula tersimpan, tampilkan & evaluasi
        const f = formulaState[id];
        if (f && typeof f.raw === 'string' && f.raw.trim()) {
          input.value = f.raw;
          handleInputChange(id, input, preview, false);
        }
      });
      recalcTotal();
      setBtnSaveEnabled();
    } catch (e) {
      console.warn('Prefill rekap gagal', e);
      // fallback: tampilkan kosong, original dianggap 0
      rows.forEach(tr => {
        const id = parseInt(tr.dataset.pekerjaanId, 10);
        originalValueById[id] = 0;
        currentValueById[id] = 0;
      });
      recalcTotal();
      setBtnSaveEnabled();
    }
  })();

  // --- Submit
  btnSave && btnSave.addEventListener('click', async function () {
    if (dirtySet.size === 0) {
      alert('Tidak ada perubahan untuk disimpan.');
      return;
    }

    // Kumpulkan delta
    const postingIds = Array.from(dirtySet.values());
    const items = postingIds.map(id => {
      // Jika input kosong tapi dirty (misalnya formula sebelumnya dihapus), kirim 0
      let q = currentValueById[id];
      if (!Number.isFinite(q)) q = 0;
      // kirim sebagai number (bukan string terformat)
      const rounded = roundHalfUp(q, qtyPlaces);
      return { pekerjaan_id: id, quantity: rounded };
    });

    btnSave.disabled = true;
    try {
      const res = await fetch(`/detail_project/api/project/${projectId}/volume-pekerjaan/save/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        credentials: 'same-origin',
        body: JSON.stringify({ items })
      });
      const json = await res.json().catch(() => ({}));

      // Mark per-baris error berdasarkan indeks items[...] dari payload kita
      const markErrors = () => {
        if (!json || !Array.isArray(json.errors)) return;
        const re = /items\[(\d+)\]\.(quantity|pekerjaan_id)/;
        json.errors.forEach(e => {
          const m = e && e.path ? re.exec(e.path) : null;
          if (!m) return;
          const idx = parseInt(m[1], 10);
          const id = postingIds[idx];
          const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
          if (!tr) return;
          const input = tr.querySelector('.qty-input');
          if (!input) return;
          input.classList.add('is-invalid');
          if (e.message) input.setAttribute('title', e.message);
        });
      };

      if (!res.ok || json.ok === false) {
        markErrors();
        alert(`⚠️ Sebagian/semua gagal disimpan.\nTersimpan: ${json && typeof json.saved === 'number' ? json.saved : 0}\n${
          json && json.errors ? JSON.stringify(json.errors, null, 2) : 'Server error'
        }`);
        return;
      }

      // Sukses penuh
      postingIds.forEach(id => {
        originalValueById[id] = currentValueById[id] ?? 0;
        // Flash hijau singkat
        const tr = rows.find(r => parseInt(r.dataset.pekerjaanId, 10) === id);
        if (tr) {
          const input = tr.querySelector('.qty-input');
          if (input) {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
            setTimeout(() => input.classList.remove('is-valid'), 1200);
          }
        }
        dirtySet.delete(id);
      });
      setBtnSaveEnabled();
      recalcTotal();
      alert(`✅ Disimpan: ${json && typeof json.saved === 'number' ? json.saved : postingIds.length}`);
    } catch (e) {
      console.error(e);
      alert('❌ Gagal simpan (network/server error).');
    } finally {
      btnSave.disabled = false;
    }
  });

  // --- Unsaved changes guard
  window.addEventListener('beforeunload', (e) => {
    if (window.__vpDirty) {
      e.preventDefault();
      e.returnValue = '';
      return '';
    }
  });

  // --- Init variables-panel (load & render)
  loadVars();
  renderVarTable();
})();
