// static/detail_project/js/detail_ahsp.js
(function () {
  const $ = (sel, ctx=document) => ctx.querySelector(sel);
  const $$ = (sel, ctx=document) => Array.from(ctx.querySelectorAll(sel));

  // ---------- STATE ----------
  const app = $('#da-app');
  if (!app) return;

  const endpoints = {
    get: app.dataset.endpointGetPattern,       // .../<pid>/detail-ahsp/0/   -> replace 0
    save: app.dataset.endpointSavePattern,     // .../<pid>/detail-ahsp/0/save/
    reset: app.dataset.endpointResetPattern,   // .../<pid>/detail-ahsp/0/reset-to-ref/
    searchAhsp: app.dataset.endpointSearchAhsp,   // NEW Fase 5
  };
  const locale = app.dataset.locale || 'id-ID';

  let activeJobId = null;
  let activeSource = null;     // 'ref' | 'ref_modified' | 'custom'
  let readOnly = false;
  let dirty = false;
  let kategoriMeta = [];       // [{code,label}]
  const rowsByJob = {};        // { jobId: [{kategori,kode,uraian,satuan,koefisien}] }

  // === Koefisien numeric helpers (dp=6) ===
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
  // Auto-format setiap input koef saat blur
  document.addEventListener('blur', (e)=>{
    const el = e.target;
    if (!(el instanceof HTMLInputElement)) return;
    if (!el.classList.contains('num')) return;
    if (el.dataset.field !== 'koefisien') return;
    const canon = __koefToCanon(el.value);
    el.value = __koefToUI(canon);
  }, true);

  // --- CSRF helper (dipakai semua POST) ---
  function getCookie(name){
    return document.cookie.split('; ').find(r => r.startsWith(name+'='))?.split('=')[1] || '';
  }
  const CSRF = getCookie('csrftoken');
  
  // ---------- UTILS ----------
  function urlFor(pattern, id) {
    // Ganti segmen "/0/" (atau "/0" di akhir) menjadi "/<id>/"
    return pattern.replace(/\/0(\/|$)/, `/${id}$1`);
  }
  function setDirty(v) {
    dirty = !!v;
    $('#da-dirty-dot').hidden = !dirty;
    $('#da-dirty-text').hidden = !dirty;
    $('#da-btn-save').disabled = dirty ? false : true;
  }
  function normKoefStrToSend(s) {
    if (s == null) return '';
    return String(s).trim();
  }
  function formatIndex() {
    $$('.da-row').forEach((tr, i) => $('.row-index', tr).textContent = (i+1));
  }
  function clearTable(seg) {
    const body = $(`#seg-${seg}-body`);
    body.innerHTML = `<tr class="da-empty"><td colspan="5">Belum ada item.</td></tr>`;
  }

  function renderRows(seg, rows) {
    const body = $(`#seg-${seg}-body`);
    body.innerHTML = '';
    const tpl = $('#da-row-template');

    if (!rows.length) {
      body.innerHTML = `<tr class="da-empty"><td colspan="5">Belum ada item.</td></tr>`;
      return;
    }

    rows.forEach(r => {
      const tr = tpl.content.firstElementChild.cloneNode(true);
      $('.cell-wrap', tr).textContent = r.uraian || '';
      $('input[data-field="kode"]', tr).value = r.kode || '';
      $('input[data-field="satuan"]', tr).value = r.satuan || '';
      // TAMPILKAN KOEF DI UI (locale) — bukan raw string
      $('input[data-field="koefisien"]', tr).value = __koefToUI(String(r.koefisien ?? ''));

      // Hidden ref_ahsp_id dari GET (kalau ada)
      const hid = $('input[data-field="ref_ahsp_id"]', tr);
      if (hid) hid.value = (r.ref_ahsp_id != null ? String(r.ref_ahsp_id) : '');
      // Tambah lencana kecil saat LAIN + ada ref_ahsp_id
      if (seg === 'LAIN') {
        const isBundle = !!(hid && hid.value);
        const kodeTd = $('input[data-field="kode"]', tr).closest('td');
        if (isBundle && kodeTd && !kodeTd.querySelector('.tag-bundle')) {
          kodeTd.insertAdjacentHTML('beforeend', ' <span class="tag-bundle">Bundle</span>');
        }
      }

      tr.dataset.kategori = r.kategori;
      body.appendChild(tr);
    });

    formatIndex();

    // Pasang Select2 hanya utk LAIN & job CUSTOM
    if (seg === 'LAIN' && activeSource === 'custom') {
      enhanceLAINAutocomplete(body);
    }
  }

  function gatherRows() {
  const segs = ['TK','BHN','ALT','LAIN'];
  const out = [];
  segs.forEach(seg => {
    $(`#seg-${seg}-body`)?.querySelectorAll('tr.da-row')?.forEach(tr => {
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

  // >>> PATCH: perluas guard agar juga mematikan tombol tambah & katalog

  function setEditorModeBySource() {
    const canSave  = (activeSource === 'ref_modified' || activeSource === 'custom') && !readOnly;
    const canReset = (activeSource === 'ref_modified') && !readOnly;

    $('#da-btn-save').hidden   = !canSave;
    $('#da-btn-save').disabled = !canSave || !dirty;

    const resetBtnEl = $('#da-btn-reset');
    if (resetBtnEl) resetBtnEl.hidden = !canReset;

    const editable = canSave;

    // Enable/disable input & contenteditable
    $$('.da-row input, .da-row .cell-wrap').forEach(el => {
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
      ...$$('.da-seg-add-catalog'),
      ...$$('.da-seg-add-empty'),
      $('#da-btn-add-empty'),
      $('#da-btn-add-component'),
    ].filter(Boolean);
    lockBtns.forEach(btn => { btn.disabled = !editable; });

    document.body.classList.toggle('da-readonly', !editable);

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

    // Jika diberi scopeEl (tbody LAIN), cari input di dalamnya.
    // Kalau tidak, fallback ke seluruh dokumen.
    const scope   = scopeEl || document;
    const selector = scopeEl
      ? '.da-row input[data-field="kode"]'
      : '#seg-LAIN-body .da-row input[data-field="kode"]';

    $$(selector, scope).forEach(input => {
      const tr = input.closest('tr.da-row');
      const $input = jQuery(input);

      // Hindari double-init
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
        // >>> tambahkan ini:
        const kodeTd = input.closest('td');
        if (kodeTd && !kodeTd.querySelector('.tag-bundle')) {
          kodeTd.insertAdjacentHTML('beforeend', ' <span class="tag-bundle">Bundle</span>');
        }
        setDirty(true);
      });

      // Kalau user edit manual kode → kosongkan ref id
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
    $$('.da-job-item').forEach(n => n.classList.toggle('is-active', n === li));
    $('#da-active-kode').textContent = $('.kode', li)?.textContent?.trim() || '—';
    $('#da-active-uraian').textContent = $('.uraian', li)?.textContent?.trim() || '—';
    $('#da-active-satuan').textContent = $('.satuan', li)?.textContent?.trim() || '—';
    $('#da-active-source').innerHTML = `<span class="badge">${activeSource}</span>`;
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
    const n = $$('.da-row').length;
    $('#da-row-stats').textContent = `${n} baris`;
  }

  // ---------- EVENTS ----------
  // pilih pekerjaan
  $$('#da-job-list .da-job-item').forEach(li => {
    li.addEventListener('click', () => selectJob(li));
    li.addEventListener('keydown', (e) => { if (e.key==='Enter' || e.key===' ') { e.preventDefault(); selectJob(li);} });
  });

  // filter (fallback dua id supaya aman)
  const jobFilterEl = $('#da-job-filter') || $('#da-job-search');
  if (jobFilterEl) {
    jobFilterEl.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      $$('#da-job-list .da-job-item').forEach(li => {
        const t = li.textContent.toLowerCase();
        li.hidden = !(t.includes(q));
      });
    });
  }

  // add empty row
  $$('.da-seg-add-empty').forEach(btn => {
    btn.addEventListener('click', () => {
      if (activeSource === 'ref') return; // read-only
      const seg = btn.dataset.targetSeg;
      const body = $(`#seg-${seg}-body`);
      const tpl = $('#da-row-template');
      const tr = tpl.content.firstElementChild.cloneNode(true);
      tr.dataset.kategori = seg;
      if ($('.da-empty', body)) body.innerHTML = '';
      body.appendChild(tr);
      formatIndex();
      setDirty(true);
      setEditorModeBySource();
      if (seg === 'LAIN' && activeSource === 'custom') {
        enhanceLAINAutocomplete(body); // NEW
      }
    });
  });

  // input change -> dirty
  app.addEventListener('input', (e) => {
    if (!e.target.closest('.da-row')) return;
    if (activeSource === 'ref') return;
    setDirty(true);
  });
  app.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
      e.preventDefault();
      $('#da-btn-save').click();
    }
  });

  // SAVE (replace-all) —>>> PATCH: kanonisasi sebelum POST
  $('#da-btn-save').addEventListener('click', () => {
    if (!activeJobId) return;
    const rows = gatherRows();
    const errs = validateClient(rows);
    if (errs.length) {
      toast('Periksa isian: ada error', 'warn');
      return;
    }
    // >>> PATCH: normalisasi koef ke string kanonik (dp=6) sebelum POST
    const rowsCanon = rows.map(r => ({ ...r, koefisien: __koefToCanon(r.koefisien) }));

    const url = urlFor(endpoints.save, activeJobId);
    fetch(url, {
      method:'POST',
      credentials:'same-origin',
      headers:{ 'Content-Type':'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({rows: rowsCanon})
    }).then(r=>r.json()).then(js=>{
      if (!js.ok && !js.saved_rows) throw new Error('Gagal simpan');
      setDirty(false);
      rowsByJob[activeJobId] = rowsByJob[activeJobId] || {};
      rowsByJob[activeJobId].items = rows; // cache apa adanya (UI tetap seperti yang terlihat)
      toast('Tersimpan', 'success');
    }).catch(()=>{
      toast('Gagal menyimpan', 'error');
    });
  });

  // RESET (ref_modified)
  const resetBtn = $('#da-btn-reset');
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

  // EXPORT CSV —>>> PATCH: tulis koefisien dalam format kanonik (titik)
  $('#da-btn-export').addEventListener('click', () => {
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
    a.download = `detail_ahsp_${activeJobId}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  });

  // toast minimal
  function toast(msg, type='info') {
    console.log(`[${type}] ${msg}`);
    // bisa diganti komponen toast kamu
  }

  // auto-select first job
  const first = $('#da-job-list .da-job-item:not([hidden])');
  if (first) selectJob(first);
})();
