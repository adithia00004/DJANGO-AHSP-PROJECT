/* =====================================================================
   REKAP_RAB.JS — Enhanced (Based on Your Working Original)
   
   ENHANCEMENTS ADDED:
   ✅ Search highlight dengan .rab-hit class
   ✅ Accessibility announcements
   ✅ Better error handling & loading states
   ✅ All original functionality preserved
   ===================================================================== */

(function () {
  'use strict';

  const root = document.getElementById('rekap-app');
  if (!root) return;

  const projectId = root.dataset.projectId || root.dataset.pid;
  const tbody = document.querySelector('#rekap-table tbody');
  const loadingRow = document.getElementById('rab-loading');
  const tableWrap = document.getElementById('rekap-table-wrap');

  // Footer refs
  const elD     = document.getElementById('ft-total-d');
  const elPPN   = document.getElementById('ft-ppn');
  const elGrand = document.getElementById('ft-grand');
  const elRound = document.getElementById('ft-rounded');
  const inpPPN  = document.getElementById('ppn-pct');
  const selBase = document.getElementById('round-base');

  // Toolbar refs
  const inpSearch   = document.getElementById('rab-search');
  const btnRefresh  = document.getElementById('btn-refresh');
  const btnExport   = document.getElementById('btn-export');
  const btnExpand   = document.getElementById('btn-expand');
  const btnCollapse = document.getElementById('btn-collapse');
  const btnPrint    = document.getElementById('btn-print');
  const btnSubtotal = document.getElementById('btn-subtotal');
  const btnDensity  = document.getElementById('btn-density');

  // ENHANCEMENT #2: Live region for accessibility
  const liveRegion = document.getElementById('rab-announce');

  // ========= Utils =========
  const nf = (dp=2) => new Intl.NumberFormat('id-ID', { maximumFractionDigits: dp });
  const fmt = (v, dp=2) => (v == null || v === '') ? '' : nf(dp).format(Number(v));
  const rupiah = v => (v == null || v === '') ? '-' : nf(0).format(Math.round(Number(v)));

  async function fetchJSON(url) {
    const res = await fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
    const data = await res.json().catch(() => ({ ok:false }));
    return { ok: res.ok && (data.ok ?? true), data };
  }

  // CSRF helpers for POST
  function getCookie(name) {
    const v = document.cookie ? document.cookie.split('; ') : [];
    for (let i=0;i<v.length;i++){ 
      const p=v[i].split('='); 
      if (p[0]===name) return decodeURIComponent(p[1]); 
    }
    return null;
  }

  function csrfHeaders(extra={}) {
    const token = getCookie('csrftoken');
    return Object.assign({
      'X-Requested-With': 'XMLHttpRequest',
      'Content-Type': 'application/json',
      ...(token ? {'X-CSRFToken': token} : {})
    }, extra);
  }

  // ENHANCEMENT #2: Announce helper for accessibility
  function announce(message) {
    if (!liveRegion) return;
    liveRegion.textContent = message;
    setTimeout(() => { liveRegion.textContent = ''; }, 3000);
  }

  // ENHANCEMENT #1: Highlight helper for search
  function highlightMatch(text, query) {
    if (!query || !text) return text;
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escaped})`, 'gi');
    return text.replace(regex, '<span class="rab-hit">$1</span>');
  }

  // ========= STATE =========
  let tree = [];
  let rekapRows = [];
  let fullModel = null;
  let subtotalOnly = false;
  let dense = false;

  // Expanded state per node (persist in localStorage)
  const exKey = (k)=>`rekap_rab:${projectId}:expanded:${k}`;
  const expanded = {
    get(id) {
      try { 
        const v = localStorage.getItem(exKey(id)); 
        return v === null ? true : v === '1'; 
      } catch(_) { return true; }
    },
    set(id, val) { 
      try { localStorage.setItem(exKey(id), val ? '1' : '0'); } 
      catch(_) {}
    },
    setMany(map) { 
      try { 
        for (const [id,val] of map) {
          localStorage.setItem(exKey(id), val ? '1' : '0');
        }
      } catch(_) {}
    }
  };

  // Local prefs
  const prefKey = (k)=>`rekap_rab:${projectId}:${k}`;
  
  const getBoolPref = (k, def=false) => {
    try { 
      const v = localStorage.getItem(prefKey(k)); 
      return v===null ? def : v==='1'; 
    } catch(_) { return def; }
  };
  
  const setBoolPref = (k, val) => { 
    try { localStorage.setItem(prefKey(k), val?'1':'0'); } 
    catch(_) {}
  };

  function savePrefs(){
    try {
      localStorage.setItem(prefKey('ppn_pct'),  String(inpPPN.value || ''));
      localStorage.setItem(prefKey('round_base'), String(selBase.value || ''));
    } catch(_) {}
  }

  function restorePrefs(){
    try {
      const savedPPN  = localStorage.getItem(prefKey('ppn_pct'));
      const savedBase = localStorage.getItem(prefKey('round_base'));
      if (savedPPN  !== null) inpPPN.value  = savedPPN;
      if (savedBase !== null) selBase.value = savedBase;
    } catch(_) {}
  }

  // ========= Normalization =========
  function normalize(tree, rekap) {
    const byPekerjaan = new Map();
    const byKode = new Map();
    for (const r of rekap) {
      if (r && r.pekerjaan_id != null) byPekerjaan.set(String(r.pekerjaan_id), r);
      if (r && r.kode) byKode.set(String(r.kode), r);
    }

    const Klist = [];
    for (const K of tree) {
      const Knode = { type:'klas', id:`k${K.id}`, name:K.name||'Klasifikasi', children:[], total:0 };
      for (const S of (K.sub || [])) {
        const Snode = { type:'sub', id:`s${S.id}`, name:S.name||'Sub-Klasifikasi', parent:Knode.id, children:[], total:0 };
        for (const P of (S.pekerjaan || [])) {
          let r = byPekerjaan.get(String(P.id));
          if (!r && P.snapshot_kode) r = byKode.get(String(P.snapshot_kode));

          const volume = (r && r.volume != null) ? Number(r.volume) : 0;
          const harga  = (r && (r.HSP != null || r.unit_price != null)) ? Number(r.HSP ?? r.unit_price) : 0;
          const total  = Number((volume || 0) * (harga || 0));

          Snode.children.push({
            type:'job',
            id:`p${P.id}`,
            parent:Snode.id,
            label:(r && r.uraian) ? r.uraian : (P.snapshot_uraian || 'Pekerjaan'),
            kode:(r && r.kode) ? r.kode : (P.snapshot_kode || ''),
            satuan:(r && r.satuan) ? r.satuan : (P.snapshot_satuan || ''),
            volume, harga, total
          });
        }
        Knode.children.push(Snode);
      }
      Klist.push(Knode);
    }
    return Klist;
  }

  function computeTotalsFiltered(model, predicate) {
    let totalD = 0;
    const rows = [];

    for (const K of model) {
      const indexK = rows.push({ level:1, node:K, total:0 }) - 1;
      let sumK = 0;

      for (const S of K.children) {
        let sumS = 0;
        const jobs = [];
        for (const J of S.children) {
          if (!predicate(J, S, K)) continue;
          jobs.push(J);
          sumS += Number(J.total || 0);
        }
        if (jobs.length > 0) {
          rows.push({ level:2, node:S, total:sumS });
          if (!subtotalOnly) {
            for (const J of jobs) rows.push({ level:3, node:J, total:J.total || 0 });
          }
          sumK += sumS;
        }
      }

      rows[indexK].total = sumK;
      totalD += sumK;
    }
    return { totalD, rows };
  }

  // ========= Rendering (ENHANCED with highlight) =========
  function buildRow(level, node, total, parentId, currentFilter='') {
    const tr = document.createElement('tr');
    tr.dataset.nodeId = node.id;
    if (parentId) tr.dataset.parentId = parentId;
    tr.dataset.level = String(level);

    const tdU  = document.createElement('td');
    const tdK  = document.createElement('td'); tdK.className = 'd-none d-md-table-cell';
    const tdS  = document.createElement('td'); tdS.className = 'd-none d-lg-table-cell';
    const tdV  = document.createElement('td'); tdV.className = 'text-end d-none d-sm-table-cell';
    const tdH  = document.createElement('td'); tdH.className = 'text-end d-none d-md-table-cell';
    const tdT  = document.createElement('td'); tdT.className = 'text-end fw-semibold';

    if (level === 1 || level === 2) {
      const isExpanded = expanded.get(node.id);
      const icon = isExpanded ? 'bi-caret-down-fill' : 'bi-caret-right-fill';
      
      // ENHANCEMENT #1: Apply highlight pada nama K/S
      const displayName = currentFilter 
        ? highlightMatch(node.name, currentFilter)
        : node.name;
      
      tdU.innerHTML = `<span class="toggle" role="button" tabindex="0" aria-expanded="${isExpanded}" aria-label="Toggle"><i class="bi ${icon} me-1"></i></span>${displayName}`;
      
      if (level === 1) tr.classList.add('table-primary');
      if (level === 2) tr.classList.add('table-light');
      tdT.textContent = fmt(total, 2);
    } else {
      // ENHANCEMENT #1: Apply highlight pada label & kode pekerjaan
      const displayLabel = currentFilter 
        ? highlightMatch(node.label, currentFilter)
        : node.label;
      const displayKode = currentFilter && node.kode
        ? highlightMatch(node.kode, currentFilter)
        : (node.kode || '');
      
      tdU.innerHTML = `<span class="text-muted small d-block">Pekerjaan</span><span>${displayLabel}</span>`;
      tdK.innerHTML = displayKode;
      tdS.textContent = node.satuan || '';
      tdV.textContent = fmt(node.volume ?? '', 3);
      tdH.textContent = fmt(node.harga ?? '', 2);
      tdT.textContent = fmt(node.total ?? '', 2);
    }

    tr.append(tdU, tdK, tdS, tdV, tdH, tdT);
    return tr;
  }

  function updateIconsFromState() {
    tbody.querySelectorAll('.toggle').forEach(t => {
      const tr = t.closest('tr');
      const id = tr?.dataset.nodeId;
      const ic = t.querySelector('i');
      const isEx = expanded.get(id);
      if (!ic) return;
      ic.classList.toggle('bi-caret-down-fill', isEx);
      ic.classList.toggle('bi-caret-right-fill', !isEx);
      t.setAttribute('aria-expanded', isEx ? 'true' : 'false');
      t.setAttribute('role', 'button');
      t.setAttribute('tabindex', '0');
    });
  }

  function applyVisibility({ filterActive=false } = {}) {
    const rowById = new Map();
    tbody.querySelectorAll('tr').forEach(r => {
      const id = r.dataset.nodeId;
      if (id) rowById.set(id, r);
    });

    function ancestorsExpanded(row) {
      if (filterActive) return true;
      let pid = row.dataset.parentId || '';
      while (pid) {
        if (expanded.get(pid) === false) return false;
        const pr = rowById.get(pid);
        pid = pr ? (pr.dataset.parentId || '') : '';
      }
      return true;
    }

    tbody.querySelectorAll('tr').forEach(r => {
      const pid = r.dataset.parentId;
      if (!pid) r.style.display = '';
      else r.style.display = ancestorsExpanded(r) ? '' : 'none';
    });
  }

  // ====== Toolbar guard ======
  function hasFilterText() {
    return !!(inpSearch?.value || '').trim();
  }

  function updateToolbarState() {
    const blocked = hasFilterText();
    if (btnExpand) {
      btnExpand.disabled = blocked;
      btnExpand.classList.toggle('disabled', blocked);
      btnExpand.title = blocked ? 'Nonaktif saat pencarian aktif' : '';
    }
    if (btnCollapse) {
      btnCollapse.disabled = blocked;
      btnCollapse.classList.toggle('disabled', blocked);
      btnCollapse.title = blocked ? 'Nonaktif saat pencarian aktif' : '';
    }
  }

  function recalcFooter(totalD) {
    const D = Number(totalD || 0);
    const pct = Number(inpPPN?.value || 0);
    const ppn = D * (pct / 100);
    const grand = D + ppn;
    const base = Number(selBase?.value || 10000);
    const rounded = Math.round(grand / base) * base;

    elD.textContent     = rupiah(D);
    elPPN.textContent   = rupiah(ppn);
    elGrand.textContent = rupiah(grand);
    elRound.textContent = rupiah(rounded);
  }

  function render(filterText='') {
    if (!fullModel) return;
    const q = (filterText || '').trim().toLowerCase();
    const match = (J, S, K) => {
      if (!q) return true;
      return (
        (J.label || '').toLowerCase().includes(q) ||
        (J.kode  || '').toLowerCase().includes(q) ||
        (S.name  || '').toLowerCase().includes(q) ||
        (K.name  || '').toLowerCase().includes(q)
      );
    };

    const { totalD, rows } = computeTotalsFiltered(fullModel, match);

    const frag = document.createDocumentFragment();
    let currentK = null, currentS = null;
    
    // ENHANCEMENT #1: Pass currentFilter ke buildRow untuk highlight
    for (const r of rows) {
      if (r.level === 1) {
        currentK = r.node;
        frag.appendChild(buildRow(1, r.node, r.total, null, q));
      } else if (r.level === 2) {
        currentS = r.node;
        frag.appendChild(buildRow(2, r.node, r.total, currentK?.id, q));
      } else {
        const trP = buildRow(3, r.node, r.total, currentS?.id, q);
        frag.appendChild(trP);
      }
    }

    tbody.innerHTML = '';
    if (rows.length === 0) {
      const tr = document.createElement('tr');
      const td = document.createElement('td');
      td.colSpan = 6;
      td.className = 'text-center text-muted py-4';
      td.textContent = q ? 'Tidak ada hasil yang cocok dengan pencarian' : 'Tidak ada data';
      tr.appendChild(td);
      tbody.appendChild(tr);
      
      // ENHANCEMENT #2: Announce no results
      if (q) announce('Tidak ada hasil yang cocok dengan pencarian');
    } else {
      tbody.appendChild(frag);
      updateIconsFromState();
      applyVisibility({ filterActive: !!q });
      
      // ENHANCEMENT #2: Announce search results
      if (q) {
        const visibleJobs = rows.filter(r => r.level === 3).length;
        announce(`Menampilkan ${visibleJobs} pekerjaan dari hasil pencarian "${q}"`);
      }
    }
    
    recalcFooter(totalD);
    recalcTableHeight();
    updateToolbarState();
  }

  // ENHANCEMENT #3: Better error handling
  async function loadData() {
    try {
      loadingRow && (loadingRow.style.display = '');
      
      // CORRECT URL PREFIX: /detail_project/api/project/...
      const [tRes, rRes, pRes] = await Promise.all([
        fetchJSON(`/detail_project/api/project/${projectId}/list-pekerjaan/tree/`),
        fetchJSON(`/detail_project/api/project/${projectId}/rekap/`),
        fetchJSON(`/detail_project/api/project/${projectId}/pricing/`)
      ]);
      
      if (!tRes.ok || !rRes.ok || !Array.isArray(tRes.data.klasifikasi) || !Array.isArray(rRes.data.rows)) {
        throw new Error('Gagal memuat data dari server');
      }
      
      tree = tRes.data.klasifikasi;
      rekapRows = rRes.data.rows;
      fullModel = normalize(tree, rekapRows);

      // Prefill PPN & rounding
      if (pRes && pRes.ok) {
        setPPNValue(pRes.data.ppn_percent);
        setRoundBase(pRes.data.rounding_base);
      } else if (rRes.data.meta) {
        const m = rRes.data.meta || {};
        setPPNValue(m.ppn_percent);
        setRoundBase(m.rounding_base);
      } else {
        restorePrefs();
      }

      render('');
      
      // ENHANCEMENT #2: Announce success
      announce('Data RAB berhasil dimuat');
      
    } catch (e) {
      console.error('[RAB] Load error:', e);
      tbody.innerHTML = `
        <tr>
          <td colspan="6" class="text-center text-danger py-4">
            <i class="bi bi-exclamation-triangle-fill mb-2" style="font-size: 2rem; display: block;"></i>
            <strong>Gagal memuat data</strong>
            <p class="mb-2 small">${e.message}</p>
            <button class="btn btn-sm btn-outline-primary" onclick="location.reload()">
              <i class="bi bi-arrow-clockwise"></i> Muat Ulang
            </button>
          </td>
        </tr>
      `;
      // ENHANCEMENT #2: Announce error
      announce(`Error: ${e.message}`);
    } finally {
      loadingRow && loadingRow.remove();
    }
  }

  function setPPNValue(v) {
    if (v == null) return;
    const num = Number(v);
    if (!Number.isNaN(num)) inpPPN.value = String(num);
  }

  function setRoundBase(v) {
    if (v == null) return;
    const ival = Number(v);
    if (!Number.isFinite(ival) || ival <= 0) return;
    if (selBase && !Array.from(selBase.options).some(o => Number(o.value) === ival)) {
      const opt = document.createElement('option');
      opt.value = String(ival);
      opt.textContent = nf(0).format(ival);
      selBase.appendChild(opt);
    }
    selBase.value = String(ival);
  }

  // ========= Tinggi Tabel adaptif =========
  function recalcTableHeight() {
    if (!tableWrap) return;
    const topbar  = document.getElementById('dp-topbar');
    const toolbar = root.querySelector('.rekap-toolbar');

    const vh = window.innerHeight || document.documentElement.clientHeight;
    const topH = topbar ? Math.ceil(topbar.getBoundingClientRect().height) : 64;
    const tbH  = toolbar ? Math.ceil(toolbar.getBoundingClientRect().height) : 0;

    const gaps = 12;
    const h = Math.max(320, vh - topH - tbH - gaps);

    tableWrap.style.maxHeight = h + 'px';
    tableWrap.style.height    = h + 'px';
  }

  const recalcHeightDebounced = (()=>{ 
    let t; 
    return ()=>{ clearTimeout(t); t=setTimeout(recalcTableHeight, 60); }; 
  })();
  
  window.addEventListener('resize', recalcHeightDebounced);
  window.addEventListener('load', recalcTableHeight);

  // ========= Expand/Collapse handlers =========
  tbody.addEventListener('click', (ev) => {
    const btn = ev.target.closest('.toggle');
    if (!btn) return;
    const tr = btn.closest('tr');
    if (!tr) return;
    const id = tr.dataset.nodeId;
    const willExpand = !(expanded.get(id) === false);
    expanded.set(id, !willExpand);
    updateIconsFromState();
    applyVisibility({ filterActive: hasFilterText() });
    
    // ENHANCEMENT #2: Announce toggle
    announce(willExpand ? 'Baris di-collapse' : 'Baris di-expand');
  });

  // Keyboard support
  tbody.addEventListener('keydown', (ev) => {
    if (ev.key !== 'Enter' && ev.key !== ' ') return;
    const btn = ev.target.closest('.toggle');
    if (!btn) return;
    ev.preventDefault();
    const tr = btn.closest('tr');
    if (!tr) return;
    const id = tr.dataset.nodeId;
    const willExpand = !(expanded.get(id) === false);
    expanded.set(id, !willExpand);
    updateIconsFromState();
    applyVisibility({ filterActive: hasFilterText() });
  });

  // ==== Expand/Collapse All ====
  function expandAll() {
    const pairs = [];
    if (Array.isArray(fullModel)) {
      for (const K of fullModel) {
        pairs.push([K.id, true]);
        for (const S of K.children) pairs.push([S.id, true]);
      }
    } else {
      tbody.querySelectorAll('tr').forEach(r => {
        if (r.querySelector('.toggle')) pairs.push([r.dataset.nodeId, true]);
      });
    }
    expanded.setMany(pairs);
    updateIconsFromState();
    applyVisibility({ filterActive: hasFilterText() });
    
    // ENHANCEMENT #2: Announce
    announce('Semua baris telah di-expand');
  }

  function collapseAll() {
    const pairs = [];
    if (Array.isArray(fullModel)) {
      for (const K of fullModel) {
        pairs.push([K.id, false]);
        for (const S of K.children) pairs.push([S.id, false]);
      }
    } else {
      tbody.querySelectorAll('tr[data-level="1"]').forEach(r => pairs.push([r.dataset.nodeId, false]));
      tbody.querySelectorAll('tr[data-level="2"]').forEach(r => pairs.push([r.dataset.nodeId, false]));
    }
    expanded.setMany(pairs);
    updateIconsFromState();
    applyVisibility({ filterActive: hasFilterText() });
    
    // ENHANCEMENT #2: Announce
    announce('Semua baris telah di-collapse');
  }

  // ========= Export CSV =========
  function exportCSV() {
    if (!fullModel) return;
    const lines = [];
    lines.push(['Klasifikasi','Sub-Klasifikasi','Pekerjaan','Kode AHSP','Satuan','Volume','Harga Satuan','Total Harga'].join(';'));
    
    for (const K of fullModel) {
      for (const S of K.children) {
        for (const J of S.children) {
          lines.push([
            (K.name||'').replace(/;/g,','), 
            (S.name||'').replace(/;/g,','), 
            (J.label||'').replace(/;/g,','), 
            (J.kode||'').replace(/;/g,','), 
            (J.satuan||'').replace(/;/g,','), 
            String(J.volume ?? ''), 
            String(J.harga ?? ''), 
            String(J.total ?? '')
          ].join(';'));
        }
      }
    }
    
    // Summary
    const { totalD } = computeTotalsFiltered(fullModel, () => true);
    const D = Number(totalD || 0);
    const pct = Number(inpPPN?.value || 0);
    const ppn = D * (pct / 100);
    const grand = D + ppn;
    const base = Number(selBase?.value || 10000);
    const rounded = Math.round(grand / base) * base;
    
    lines.push('');
    lines.push(['', '', '', '', 'Total Proyek (D)', String(Math.round(D))].join(';'));
    lines.push(['', '', '', '', `PPN ${pct}%`, String(Math.round(ppn))].join(';'));
    lines.push(['', '', '', '', 'Grand Total (D+PPN)', String(Math.round(grand))].join(';'));
    lines.push(['', '', '', '', `Pembulatan ke ${base}`, String(Math.round(rounded))].join(';'));

    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = `rekap_rab_${projectId}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(()=>URL.revokeObjectURL(a.href), 1000);
    
    // ENHANCEMENT #2: Announce export
    announce('File CSV berhasil di-download');
  }

  // ========= Server-save prefs =========
  const postPricingDebounced = (() => {
    let t; 
    return (payload) => {
      clearTimeout(t);
      t = setTimeout(async () => {
        try {
          await fetch(`/detail_project/api/project/${projectId}/pricing/`, {
            method: 'POST',
            headers: csrfHeaders(),
            body: JSON.stringify(payload)
          });
        } catch(e) { console.error('[RAB] Pricing error:', e); }
      }, 250);
    };
  })();

  // ========= Density UI =========
  function applyDenseUI() {
    root.classList.toggle('rab-dense', dense);
    btnDensity?.classList.toggle('active', dense);
    recalcTableHeight();
  }

  // ========= Events =========
  function debounce(fn, ms) { 
    let t=0; 
    return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn(...args), ms); }; 
  }

  inpSearch?.addEventListener('input', debounce(e => {
    render(e.target.value || '');
    updateToolbarState();
  }, 180));

  btnRefresh?.addEventListener('click', () => {
    tbody.innerHTML=''; 
    const tr=document.createElement('tr'); 
    tr.innerHTML='<td colspan="6" class="text-center text-muted py-4"><div class="spinner-border spinner-border-sm"></div><span class="ms-2">Memuat ulang…</span></td>'; 
    tbody.appendChild(tr); 
    loadData();
  });

  btnExport?.addEventListener('click', exportCSV);
  btnExpand?.addEventListener('click', (e) => { e.preventDefault(); if (!hasFilterText()) expandAll(); });
  btnCollapse?.addEventListener('click', (e) => { 
    e.preventDefault(); 
    if (!hasFilterText()) collapseAll(); 
  });

  btnPrint?.addEventListener('click', ()=>window.print());

  btnSubtotal?.addEventListener('click', () => {
    subtotalOnly = !subtotalOnly;
    setBoolPref('subtotal_only', subtotalOnly);
    btnSubtotal.classList.toggle('active', subtotalOnly);
    render(inpSearch?.value || '');
    announce(subtotalOnly ? 'Mode subtotal aktif' : 'Mode detail aktif');
  });

  btnDensity?.addEventListener('click', () => {
    dense = !dense;
    setBoolPref('dense', dense);
    applyDenseUI();
    announce(dense ? 'Mode compact aktif' : 'Mode normal aktif');
  });

  inpPPN?.addEventListener('input', () => {
    savePrefs();
    postPricingDebounced({ ppn_percent: inpPPN.value });
    render(inpSearch?.value || '');
  });

  selBase?.addEventListener('change', () => {
    savePrefs();
    postPricingDebounced({ rounding_base: selBase.value });
    render(inpSearch?.value || '');
  });

  // ========= Init =========
  restorePrefs();
  subtotalOnly = getBoolPref('subtotal_only', false);
  btnSubtotal?.classList.toggle('active', subtotalOnly);
  dense = getBoolPref('dense', false);
  applyDenseUI();
  updateToolbarState();
  loadData();

})();