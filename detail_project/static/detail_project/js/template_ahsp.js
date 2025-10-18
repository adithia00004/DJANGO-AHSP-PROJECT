// Template AHSP – JS (selaras SSOT + gaya aksi seperti VP)
// - Hapus handler tombol toolbar “+ Tambah Baris” (sudah dihilangkan dari HTML)
// - Simpan: tombol success + neon + spinner (mirip VP) → #ta-btn-save & #ta-btn-save-spin
// - “+ Baris kosong” per-segmen tetap aktif dengan guard mode read-only & Select2 di LAIN

(function () {
  const $ = (sel, ctx=document) => ctx.querySelector(sel);
  const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));

  // ---------- STATE ----------
  const app = $('#ta-app');
  if (!app) return;

  const endpoints = {
    get: app.dataset.endpointGetPattern,       // .../<pid>/detail-ahsp/0/   -> replace 0
    save: app.dataset.endpointSavePattern,     // .../<pid>/detail-ahsp/0/save/
    reset: app.dataset.endpointResetPattern,   // .../<pid>/detail-ahsp/0/reset-to-ref/
    searchAhsp: app.dataset.endpointSearchAhsp,
  };
  const locale = app.dataset.locale || 'id-ID';

  let activeJobId = null;
  let activeSource = null;     // 'ref' | 'ref_modified' | 'custom'
  let readOnly = false;
  let dirty = false;
  let kategoriMeta = [];       // [{code,label}]
  const rowsByJob = {};        // { jobId: [{kategori,kode,uraian,satuan,koefisien}] }

  // === Koefisien numeric helpers (dp=6)
  const __NUM = window.Numeric || null;
  const __KOEF_DP = 6;
  function __koefToCanon(v){
    if (!__NUM) return (v ?? '').toString().trim();
    const s = __NUM.canonicalizeForAPI(v ?? '');
    return s ? __NUM.enforceDp(s, __KOEF_DP) : '';
  }
  function __koefToUI(canon){
    if (!__NUM) return canon ?? '';
    return __NUM.formatForUI(__NUM.enforceDp(canon ?? '', __KOEF_DP));
  }
  // Auto-format input koef saat blur
  document.addEventListener('blur', (e)=>{
    const el = e.target;
    if (!(el instanceof HTMLInputElement)) return;
    if (!el.classList.contains('num')) return;
    if (el.dataset.field !== 'koefisien') return;
    const canon = __koefToCanon(el.value);
    el.value = __koefToUI(canon);
  }, true);

  // --- CSRF helper ---
  function getCookie(name){
    return document.cookie.split('; ').find(r => r.startsWith(name+'='))?.split('=')[1] || '';
  }
  const CSRF = getCookie('csrftoken');

  // ---------- UTILS ----------
  function urlFor(pattern, id) {
    return pattern.replace(/\/0(\/|$)/, `/${id}$1`);
  }
  function setDirty(v) {
    dirty = !!v;
    $('#ta-dirty-dot').hidden = !dirty;
    $('#ta-dirty-text').hidden = !dirty;
    $('#ta-btn-save').disabled = dirty ? false : true;
  }
  function normKoefStrToSend(s) {
    if (s == null) return '';
    return String(s).trim();
  }
  function formatIndex() {
    $$('.ta-row').forEach((tr, i) => $('.row-index', tr).textContent = (i+1));
  }
  function clearTable(seg) {
    const body = $(`#seg-${seg}-body`);
    body.innerHTML = `<tr class="ta-empty"><td colspan="5">Belum ada item.</td></tr>`;
  }

  function renderRows(seg, rows) {
    const body = $(`#seg-${seg}-body`);
    body.innerHTML = '';
    const tpl = $('#ta-row-template');

    if (!rows.length) {
      body.innerHTML = `<tr class="ta-empty"><td colspan="5">Belum ada item.</td></tr>`;
      return;
    }

    rows.forEach(r => {
      const tr = tpl.content.firstElementChild.cloneNode(true);
      $('.cell-wrap', tr).textContent = r.uraian || '';
      $('input[data-field="kode"]', tr).value = r.kode || '';
      $('input[data-field="satuan"]', tr).value = r.satuan || '';
      // UI koef pakai locale
      $('input[data-field="koefisien"]', tr).value = __koefToUI(String(r.koefisien ?? ''));

      // Hidden ref_ahsp_id dari GET (kalau ada)
      const hid = $('input[data-field="ref_ahsp_id"]', tr);
      if (hid) hid.value = (r.ref_ahsp_id != null ? String(r.ref_ahsp_id) : '');
      // Tandai bundle di LAIN
      if (seg === 'LAIN') {
        const isBundle = !!(hid && hid.value);
        const kodeTd = $('input[data-field="kode"]', tr).closest('td');
        if (isBundle && kodeTd && !kodeTd.querySelector('.tag-bundle')) {
          kodeTd.insertAdjacentHTML('beforeend', ' <span class="tag-bundle">Bundle</span>');
        }
      }

      tr.dataset.kategori = r.kategori;
      // tambahkan checkbox seleksi di kolom nomor
      try { ensureSelectAffordance(tr); } catch(_){}
      body.appendChild(tr);
    });

    formatIndex();

    // Autocomplete khusus LAIN + sumber CUSTOM
    if (seg === 'LAIN' && activeSource === 'custom') {
      enhanceLAINAutocomplete(body);
    }
  }

  // Tambah checkbox seleksi di kolom nomor jika belum ada
  function ensureSelectAffordance(tr){
    const noCell = tr.querySelector('td.col-no');
    if (!noCell) return;
    if (noCell.querySelector('.ta-row-check')) return;
    const cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.className = 'form-check-input ta-row-check me-2';
    noCell.prepend(cb);
  }

  // Hitung & tampilkan jumlah baris terseleksi per segmen
  function updateDelState(seg){
    const body = $(`#seg-${seg}-body`);
    if (!body) return;
    const selected = body.querySelectorAll('.ta-row-check:checked').length;
    const cnt = document.querySelector(`.ta-del-count[data-for="${seg}"]`);
    if (cnt) cnt.textContent = String(selected);
    const btn = document.querySelector(`.ta-seg-del-selected[data-target-seg="${seg}"]`);
    if (btn) btn.disabled = selected === 0;
  }

  function gatherRows() {
    const segs = ['TK','BHN','ALT','LAIN'];
    const out = [];
    segs.forEach(seg => {
      $(`#seg-${seg}-body`)?.querySelectorAll('tr.ta-row')?.forEach(tr => {
        const base = {
          kategori: seg,
          uraian: $('.cell-wrap', tr).textContent.trim(),
          kode: $('input[data-field="kode"]', tr).value.trim(),
          satuan: $('input[data-field="satuan"]', tr).value.trim(),
          koefisien: normKoefStrToSend($('input[data-field="koefisien"]', tr).value),
        };
        if (seg === 'LAIN' && activeSource === 'custom') {
          const refId = $('input[data-field="ref_ahsp_id"]', tr).value.trim();
          if (refId) base.ref_ahsp_id = refId;
        }
        out.push(base);
      });
    });
    return out;
  }

  function validateClient(rows) {
    const errors = [];
    const seen = new Set();
    rows.forEach((r, i) => {
      if (!r.uraian) errors.push({path:`rows[${i}].uraian`, message:'Wajib'});
      if (!r.kode) errors.push({path:`rows[${i}].kode`, message:'Wajib'});
      const key = r.kode;
      if (key) {
        if (seen.has(key)) errors.push({path:`rows[${i}].kode`, message:'Kode duplikat'});
        seen.add(key);
      }
      if (r.koefisien === '' || r.koefisien == null) {
        errors.push({path:`rows[${i}].koefisien`, message:'Wajib'});
      }
    });
    return errors;
  }

  // Mode editor berdasarkan sumber row (lock/unlock)
  function setEditorModeBySource() {
    const canSave  = (activeSource === 'ref_modified' || activeSource === 'custom') && !readOnly;
    const canReset = (activeSource === 'ref_modified') && !readOnly;

    $('#ta-btn-save').hidden   = !canSave;
    $('#ta-btn-save').disabled = !canSave || !dirty;

    const resetBtnEl = $('#ta-btn-reset');
    if (resetBtnEl) resetBtnEl.hidden = !canReset;

    const editable = canSave;

    // Enable/disable input & contenteditable
    $$('.ta-row input, .ta-row .cell-wrap').forEach(el => {
      if (editable) {
        el.removeAttribute('disabled');
        if (el.tagName === 'DIV') el.setAttribute('contenteditable', 'true');
      } else {
        if (el.tagName === 'DIV') el.setAttribute('contenteditable', 'false');
        else el.setAttribute('disabled', 'true');
      }
    });

    // Kunci tombol penambah baris saat tidak editable
    const lockBtns = [
      ...$$('.ta-seg-add-catalog'),
      ...$$('.ta-seg-add-empty')
    ].filter(Boolean);
    lockBtns.forEach(btn => { btn.disabled = !editable; });

    document.body.classList.toggle('ta-readonly', !editable);

    // Sinkronkan Select2 (kalau ada)
    if (window.jQuery && jQuery.fn.select2) {
      $$('#seg-LAIN-body input[data-field="kode"]').forEach(inp => {
        const $inp = jQuery(inp);
        if ($inp.data('select2')) {
          $inp.prop('disabled', !editable);
          $inp.trigger('change.select2');
        }
      });
    }
  }

  function enhanceLAINAutocomplete(scopeEl) {
    if (!window.jQuery || !jQuery.fn.select2 || !endpoints.searchAhsp) return;
    const scope   = scopeEl || document;
    const selector = scopeEl
      ? '.ta-row input[data-field="kode"]'
      : '#seg-LAIN-body .ta-row input[data-field="kode"]';

    $$(selector, scope).forEach(input => {
      const tr = input.closest('tr.ta-row');
      const $input = jQuery(input);
      if ($input.data('hasSelect2')) return;

      $input.select2({
        ajax: {
          url: endpoints.searchAhsp,
          delay: 250,
          data: params => ({ q: params.term }),
          processResults: data => ({
            results: (data.results || []).map(x => ({
              id: x.id,
              text: `${x.kode_ahsp} — ${x.nama_ahsp}`,
              kode_ahsp: x.kode_ahsp,
              nama_ahsp: x.nama_ahsp,
              satuan: x.satuan || ''
            }))
          })
        },
        minimumInputLength: 1,
        width: 'resolve',
        placeholder: 'Cari AHSP…',
        dropdownAutoWidth: true
      });

      $input.on('select2:select', (e) => {
        const d = e.params.data || {};
        input.value = d.kode_ahsp || '';
        $('.cell-wrap', tr).textContent = d.nama_ahsp || '';
        $('input[data-field="satuan"]', tr).value = d.satuan || '';
        $('input[data-field="ref_ahsp_id"]', tr).value = d.id || '';
        const kodeTd = input.closest('td');
        if (kodeTd && !kodeTd.querySelector('.tag-bundle')) {
          kodeTd.insertAdjacentHTML('beforeend', ' <span class="tag-bundle">Bundle</span>');
        }
        setDirty(true);
      });

      // Edit manual kode → kosongkan ref id
      input.addEventListener('input', () => {
        $('input[data-field="ref_ahsp_id"]', tr).value = '';
        const b = tr.querySelector('.tag-bundle');
        if (b) b.remove();
      });

      $input.data('hasSelect2', true);
    });
  }

  // ---------- LOAD ----------
  function selectJob(li) {
    const id = +li.dataset.pekerjaanId;
    if (!id || id === activeJobId) return;
    activeJobId = id;
    activeSource = li.dataset.sourceType;
    $$('.ta-job-item').forEach(n => n.classList.toggle('is-active', n === li));
    $('#ta-active-kode').textContent = $('.kode', li)?.textContent?.trim() || '—';
    $('#ta-active-uraian').textContent = $('.uraian', li)?.textContent?.trim() || '—';
    $('#ta-active-satuan').textContent = $('.satuan', li)?.textContent?.trim() || '—';
    $('#ta-active-source').innerHTML = `<span class="badge">${activeSource}</span>`;
    setDirty(false);

    if (rowsByJob[id]) {
      paint(rowsByJob[id].items);
      kategoriMeta = rowsByJob[id].kategoriMeta || kategoriMeta;
      readOnly = rowsByJob[id].readOnly || false;
      setEditorModeBySource();
      return;
    }

    // fetch
    const url = urlFor(endpoints.get, id);
    fetch(url, {credentials:'same-origin'}).then(r => r.json()).then(js => {
      if (!js.ok) throw new Error('Gagal memuat');
      const items = js.items || [];
      kategoriMeta = js.meta?.kategori_opts || kategoriMeta;
      readOnly = !!js.meta?.read_only;
      rowsByJob[id] = {items, kategoriMeta, readOnly};
      paint(items);
      setEditorModeBySource();
    }).catch(() => {
      toast('Gagal memuat detail', 'error');
    });
  }

  function paint(items) {
    const by = {TK:[], BHN:[], ALT:[], LAIN:[]};
    (items||[]).forEach(r => {
      const seg = by[r.kategori] ? r.kategori : 'LAIN';
      by[seg].push(r);
    });
    ['TK','BHN','ALT','LAIN'].forEach(seg => renderRows(seg, by[seg]));
    updateStats();
  }

  function updateStats() {
    const n = $$('.ta-row').length;
    $('#ta-row-stats').textContent = `${n} baris`;
  }

  // ---------- EVENTS ----------
  // pilih pekerjaan
  $$('#ta-job-list .ta-job-item').forEach(li => {
    li.addEventListener('click', () => selectJob(li));
    li.addEventListener('keydown', (e) => { if (e.key==='Enter' || e.key===' ') { e.preventDefault(); selectJob(li);} });
  });

  // filter
  const jobFilterEl = $('#ta-job-search');
  if (jobFilterEl) {
    jobFilterEl.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      $$('#ta-job-list .ta-job-item').forEach(li => {
        const t = li.textContent.toLowerCase();
        li.hidden = !(t.includes(q));
      });
    });
  }

  // add empty row (per-segmen)
  $$('.ta-seg-add-empty').forEach(btn => {
    btn.addEventListener('click', () => {
      if (activeSource === 'ref') return; // read-only
      const seg = btn.dataset.targetSeg;
      const body = $(`#seg-${seg}-body`);
      const tpl = $('#ta-row-template');
      const tr = tpl.content.firstElementChild.cloneNode(true);
      tr.dataset.kategori = seg;
      if ($('.ta-empty', body)) body.innerHTML = '';
      try { ensureSelectAffordance(tr); } catch(_){}
      body.appendChild(tr);
      formatIndex();
      setDirty(true);
      setEditorModeBySource();
      if (seg === 'LAIN' && activeSource === 'custom') {
        enhanceLAINAutocomplete(body);
      }
      try { updateDelState(seg); } catch(_){}
    });
  });

  // input change -> dirty
  app.addEventListener('input', (e) => {
    if (!e.target.closest('.ta-row')) return;
    if (activeSource === 'ref') return;
    setDirty(true);
  });
  app.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      $('#ta-btn-save').click();
    }
  });

  // SAVE (replace-all) — spinner ala VP
  $('#ta-btn-save').addEventListener('click', () => {
    if (!activeJobId) return;
    const rows = gatherRows();
    const errs = validateClient(rows);
    if (errs.length) {
      toast('Periksa isian: ada error', 'warn');
      return;
    }

    const rowsCanon = rows.map(r => ({ ...r, koefisien: __koefToCanon(r.koefisien) }));
    const url = urlFor(endpoints.save, activeJobId);

    const btnSave = $('#ta-btn-save');
    const spin = $('#ta-btn-save-spin');
    if (spin) spin.hidden = false;
    if (btnSave) btnSave.disabled = true;

    fetch(url, {
      method:'POST',
      credentials:'same-origin',
      headers:{ 'Content-Type':'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({rows: rowsCanon})
    }).then(r=>r.json()).then(js=>{
      if (!js.ok && !js.saved_rows) throw new Error('Gagal simpan');
      setDirty(false);
      rowsByJob[activeJobId] = rowsByJob[activeJobId] || {};
      rowsByJob[activeJobId].items = rows; // cache tampilan
      toast('Tersimpan', 'success');
    }).catch(()=>{
      toast('Gagal menyimpan', 'error');
  }).finally(()=>{
      if (spin) spin.hidden = true;
      if (btnSave) btnSave.disabled = false;
    });
  });

  // Hapus baris terseleksi per segmen
  document.addEventListener('click', (e) => {
    const delBtn = e.target.closest('.ta-seg-del-selected');
    if (!delBtn) return;
    if (activeSource === 'ref') return;
    const seg = delBtn.dataset.targetSeg;
    const body = document.getElementById(`seg-${seg}-body`);
    if (!body) return;
    const checked = body.querySelectorAll('.ta-row-check:checked');
    if (!checked.length) return;
    checked.forEach(cb => cb.closest('tr.ta-row')?.remove());
    if (!body.querySelector('tr.ta-row')) {
      body.innerHTML = `<tr class=\"ta-empty\"><td colspan=\"5\">Belum ada item.</td></tr>`;
    }
    formatIndex();
    setDirty(true);
    updateDelState(seg);
  });

  // Update state tombol hapus saat ceklis berubah
  document.addEventListener('change', (e) => {
    const cb = e.target.closest('.ta-row-check');
    if (!cb) return;
    const tr = cb.closest('tr.ta-row');
    const seg = tr?.dataset?.kategori;
    if (seg) updateDelState(seg);
  });

  // RESET (ref_modified)
  const resetBtn = $('#ta-btn-reset');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      if (!activeJobId || activeSource !== 'ref_modified') return;
      if (!confirm('Reset rincian dari referensi? Perubahan lokal akan hilang.')) return;
      const url = urlFor(endpoints.reset, activeJobId);
      fetch(url, {
        method:'POST',
        credentials:'same-origin',
        headers:{ 'X-CSRFToken': CSRF }
      }).then(r=>r.json()).then(js=>{
        if (!js.ok) throw new Error('Gagal reset');
        // GET ulang
        fetch(urlFor(endpoints.get, activeJobId), {credentials:'same-origin'})
          .then(r=>r.json()).then(js=>{
            rowsByJob[activeJobId] = { items: js.items || [], kategoriMeta: js.meta?.kategori_opts || [], readOnly: !!js.meta?.read_only };
            paint(rowsByJob[activeJobId].items);
            setDirty(false);
            setEditorModeBySource();
            toast('Di-reset dari referensi', 'success');
          });
      }).catch(()=> toast('Gagal reset', 'error'));
    });
  }

  // EXPORT CSV (koefisien format kanonik titik)
  $('#ta-btn-export').addEventListener('click', () => {
    if (!activeJobId) return;
    const rows = gatherRows();
    const csv = ['kategori;kode;uraian;satuan;koefisien']
      .concat(rows.map(r => {
        const safeUraian = String(r.uraian || '').replace(/\r?\n/g,' ');
        const koefCanon = __koefToCanon(r.koefisien || '');
        return [r.kategori, r.kode, safeUraian, r.satuan, koefCanon]
          .map(v => String(v||'').replace(/;/g, ','))
          .join(';');
      }))
      .join('\n');
    const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `template_ahsp_${activeJobId}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  });

  // toast minimal (pakai console; bisa diganti DP.core.toast jika ada)
  function toast(msg, type='info') {
    console.log(`[${type}] ${msg}`);
  }

  // auto-select first job
  const first = $('#ta-job-list .ta-job-item:not([hidden])');
  if (first) selectJob(first);

  // =========================
  // Sidebar Resizer (vertical)
  // =========================
  (function installResizer(){
    const res = document.getElementById('ta-resizer');
    const side = document.querySelector('.ta-sidebar');
    if (!res || !side) return;

    const pid = app.dataset.projectId || '0';
    const KEY = `ta_sidebar_w:${pid}`;
    const MIN_W = 280; const MAX_W = 720;

    // restore saved width
    try {
      const saved = parseInt(localStorage.getItem(KEY)||'', 10);
      if (Number.isFinite(saved)) {
        const w = Math.min(MAX_W, Math.max(MIN_W, saved));
        // set both legacy and new tokens for compatibility
        document.body.style.setProperty('--ta-sidebar-w', `${w}px`);
        document.body.style.setProperty('--ta-left-w', `${w}px`);
      }
    } catch {}

    let dragging = false, startX = 0, startW = 0;
    const clamp = (w) => Math.min(MAX_W, Math.max(MIN_W, w));
    const onMove = (ev) => {
      if (!dragging) return;
      const x = ev.touches ? ev.touches[0].clientX : ev.clientX;
      const dx = x - startX; // drag right grows sidebar
      const w = clamp(startW + dx);
      const wpx = `${Math.round(w)}px`;
      // update both tokens so whichever CSS wins will reflect change
      document.body.style.setProperty('--ta-sidebar-w', wpx);
      document.body.style.setProperty('--ta-left-w',   wpx);
      try { localStorage.setItem(KEY, String(Math.round(w))); } catch {}
      ev.preventDefault();
    };
    const onUp = () => {
      if (!dragging) return;
      dragging = false;
      document.body.classList.remove('user-resizing');
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('touchend', onUp);
    };
    const onDown = (ev) => {
      dragging = true;
      startX = ev.touches ? ev.touches[0].clientX : ev.clientX;
      startW = side.getBoundingClientRect().width;
      document.body.classList.add('user-resizing');
      window.addEventListener('mousemove', onMove, { passive: false });
      window.addEventListener('touchmove', onMove, { passive: false });
      window.addEventListener('mouseup', onUp, { passive: true });
      window.addEventListener('touchend', onUp, { passive: true });
      ev.preventDefault();
    };
    res.addEventListener('mousedown', onDown);
    res.addEventListener('touchstart', onDown, { passive: false });
    // keyboard support
    res.addEventListener('keydown', (e) => {
      const step = (e.shiftKey ? 20 : 10);
      // prefer legacy token if present
      let cur = parseInt(getComputedStyle(document.body).getPropertyValue('--ta-left-w')||'0',10);
      if (!Number.isFinite(cur) || cur <= 0) {
        cur = parseInt(getComputedStyle(document.body).getPropertyValue('--ta-sidebar-w')||'360',10) || 360;
      }
      if (e.key === 'ArrowLeft' || e.key === 'Left') {
        const w = clamp(cur - step);
        const wpx = `${w}px`;
        document.body.style.setProperty('--ta-sidebar-w', wpx);
        document.body.style.setProperty('--ta-left-w',   wpx);
        try{localStorage.setItem(KEY,String(w));}catch{}
        e.preventDefault();
      } else if (e.key === 'ArrowRight' || e.key === 'Right') {
        const w = clamp(cur + step);
        const wpx = `${w}px`;
        document.body.style.setProperty('--ta-sidebar-w', wpx);
        document.body.style.setProperty('--ta-left-w',   wpx);
        try{localStorage.setItem(KEY,String(w));}catch{}
        e.preventDefault();
      }
    });
  })();
})();
