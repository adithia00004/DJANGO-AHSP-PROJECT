// rincian_ahsp.js — layout 2 panel: list kiri, detail satu pekerjaan kanan
(function(){
  const ROOT = document.getElementById('rekap-app');
  if (!ROOT) return;

  // ====== Intl & endpoints ======
  const locale = ROOT.dataset.locale || 'id-ID';
  const fmtRp = new Intl.NumberFormat(locale, {
    style: 'currency', currency: 'IDR',
    minimumFractionDigits: 2, maximumFractionDigits: 2
  });

  const EP_REKAP    = ROOT.dataset.epRekap;
  const EP_PRICING  = ROOT.dataset.epPricing;
  const EP_DET_PREF = ROOT.dataset.epDetailPrefix;      // ex: ".../detail-ahsp/0/"
  const EP_POV_PREF = ROOT.dataset.epPricingItemPrefix; // ex: ".../pekerjaan/0/pricing/"

  // ====== URL helpers ======
  function substId(url, id) {
    const n = Number(id);
    if (!n || n <= 0) throw new Error('invalid pekerjaan id');
    const clean = String(url || '').trim();
    return clean.replace(/\/0(?=\/|$)/, `/${n}`);
  }
  const urlDetail      = (id) => substId(EP_DET_PREF, id);
  const urlPricingItem = (id) => substId(EP_POV_PREF, id);

  // ====== DOM refs ======
  const $grid     = ROOT.querySelector('.hi-body'); // grid container
  // Kiri
  const $badgeBUK = ROOT.querySelector('#rk-badge-buk');
  const $search   = ROOT.querySelector('#rk-search');
  const $list     = ROOT.querySelector('#rk-list');
  const $grand    = ROOT.querySelector('#rk-grand');
  // Kanan (header)
  const $kode     = ROOT.querySelector('#rk-pkj-kode');
  const $uraian   = ROOT.querySelector('#rk-pkj-uraian');
  const $sat      = ROOT.querySelector('#rk-pkj-sat');
  const $src      = ROOT.querySelector('#rk-pkj-source');
  const $ovrChip  = ROOT.querySelector('#rk-pkj-ovr-chip');
  const $eff      = ROOT.querySelector('#rk-eff');
  const $ovrInput = ROOT.querySelector('#rk-ovr-input');
  const $ovrApply = ROOT.querySelector('#rk-ovr-apply');
  const $ovrClear = ROOT.querySelector('#rk-ovr-clear');
  // Kanan (tabel)
  const $tbody    = ROOT.querySelector('#rk-tbody-detail');
  // Resizer
  const $resizer  = ROOT.querySelector('.rk-resizer');
  const $leftPane = ROOT.querySelector('.rk-left');
  // Toast
  const $toast    = ROOT.querySelector('#rk-toast');


  // ====== state ======
  let ctrlDetail = null, ctrlPricing = null; // AbortControllers
  let rows = [];
  let filtered = [];
  let selectedId = null;
  let projectBUK = 10.00;
  const cacheDetail = new Map();
  let selectToken = 0;

  // ====== utils ======
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, m => ({
    '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'
  }[m]));
  // Parser angka robust (mirip backend parse_any): dukung ","/"." dan ribuan
  function parseNum(x){
    if (x == null) return 0;
    let s = String(x).trim();
    if (!s) return 0;
    s = s.replace(/_/g,'');
    const hasComma = s.includes(',');
    const hasDot   = s.includes('.');
    if (hasComma && hasDot){
      const lastComma = s.lastIndexOf(',');
      const lastDot   = s.lastIndexOf('.');
      if (lastComma > lastDot){
        const fracLen = s.length - lastComma - 1;
        if (fracLen === 3){ s = s.replace(/,/g,''); }
        else { s = s.replace(/\./g,'').replace(',', '.'); }
      } else {
        const fracLen = s.length - lastDot - 1;
        if (fracLen === 3){ s = s.replace(/\./g,'').replace(',', '.'); }
        else { s = s.replace(/,/g,''); }
      }
    } else {
      if (!hasDot && (s.match(/,/g)||[]).length === 1){ s = s.replace(',', '.'); }
      else if (!hasComma && (s.match(/\./g)||[]).length === 1){ /* ok */ }
      else { s = s.replace(/\./g,'').replace(',', '.'); }
    }
    const n = Number(s);
    return Number.isFinite(n) && n >= 0 ? n : 0;
  }
  const num = parseNum;
  const fmt = (x) => fmtRp.format(num(x));
  const csrf = () => (document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)?.[1] || '');

  // ====== UI polish: icons/classes/placeholder alignment ======
  function applyIconAndUIFixes(){
    // Ensure chips use consistent styles
    const srcChip = ROOT.querySelector('#rk-pkj-source');
    srcChip?.classList.add('ux-chip','ux-mono','mono');
    // Update icons to consistent variants
    const effIcon = ROOT.querySelector('#rk-eff i');
    if (effIcon && effIcon.classList.contains('bi-lightning-charge')){
      effIcon.classList.remove('bi-lightning-charge');
      effIcon.classList.add('bi-lightning-charge-fill');
    }
    const ovrIcon = ROOT.querySelector('#rk-pkj-ovr-chip i');
    if (ovrIcon && ovrIcon.classList.contains('bi-sliders')){
      ovrIcon.classList.remove('bi-sliders');
      ovrIcon.classList.add('bi-sliders2');
    }
    // Table header style
    ROOT.querySelector('#ra-table')?.classList.add('ux-thead');
    // Initial placeholders clean
    if ($kode)   $kode.textContent = $kode.textContent && $kode.textContent.trim() ? $kode.textContent : '-';
    if ($sat)    $sat.textContent  = $sat.textContent  && $sat.textContent.trim()  ? $sat.textContent  : '-';
    if ($src)    $src.textContent  = $src.textContent  && $src.textContent.trim()  ? $src.textContent  : '-';
    if ($eff && !$eff.textContent.includes('%')) $eff.textContent = 'Efektif: -%';
    // Loading note punctuation
    const rowNote = ROOT.querySelector('.ta-job-list .row-note');
    if (rowNote && /Memuat/.test(rowNote.textContent||'')) rowNote.textContent = 'Memuat…';
  }

  function parsePctUI(s){
    if (s == null) return null;
    s = String(s).trim().replace(/\s+/g,'');
    s = s.replace(/%+$/,'');
    if (s === '') return null;
    s = s.replace(/\./g,'').replace(',', '.'); // "12.500,5" -> "12500.5"
    const v = Number(s);
    return Number.isFinite(v) ? v : null;
  }

  function setOverrideUIEnabled(enabled){
    [$ovrInput, $ovrApply, $ovrClear].forEach(el => { if (el) el.disabled = !enabled; });
    if (!enabled && $ovrChip) $ovrChip.hidden = true;
    if ($ovrInput) $ovrInput.placeholder = enabled ? "Override %" : "Override tidak tersedia";
  }

  function showToast(msg, type = 'info') {
    if (!$toast) { console.log(`[${type}]`, msg); return; }
    const div = document.createElement('div');
    div.className = `rk-toast rk-toast-${type}`;
    div.textContent = msg;
    $toast.appendChild(div);
    setTimeout(() => {
      div.classList.add('out');
      setTimeout(() => div.remove(), 250);
    }, 1600);
  }

  function setLoading(on){ ROOT.classList.toggle('is-loading', !!on); }

  async function safeJson(r) {
    const ct = (r.headers.get('content-type') || '').toLowerCase();
    if (!ct.includes('application/json')) {
      const text = await r.text().catch(()=> '');
      throw new Error(`Non-JSON response (${r.status}): ${text.slice(0,120)}`);
    }
    return r.json();
  }

  // ====== server calls ======
  async function loadProjectBUK(){
    const r = await fetch(EP_PRICING, { credentials:'same-origin' });
    const j = await safeJson(r);
    if (!r.ok || !j.ok) throw new Error('pricing fail');
    projectBUK = Number(j.markup_percent);
    if ($badgeBUK) $badgeBUK.textContent = `BUK: ${j.markup_percent}%`;
  }

  async function loadRekap(){
    setLoading(true);
    try{
      if ($list) $list.innerHTML = `<li class="rk-item"><div class="row-note">Memuat…</div></li>`;
      const r = await fetch(EP_REKAP, { credentials:'same-origin' });
      const j = await safeJson(r);
      if (!r.ok || !j.ok) throw new Error('rekap fail');
      rows = j.rows || [];
      renderList();

      const last = localStorage.getItem('rk-last-pkj-id');
      const firstId = filtered[0]?.pekerjaan_id;
      const target = (last && rows.some(x => String(x.pekerjaan_id)===last)) ? Number(last) : firstId;
      if (selectedId == null && target) selectItem(target);
    } finally {
      setLoading(false);
    }
  }

  async function fetchDetail(id){
    ctrlDetail?.abort();
    ctrlDetail = new AbortController();
    const r = await fetch(urlDetail(id), { credentials:'same-origin', signal: ctrlDetail.signal });
    const j = await safeJson(r);
    if (!r.ok || !j.ok) throw new Error('detail fail');
    cacheDetail.set(id, j);
    return j;
  }

  async function getPricingItem(id){
    if (!EP_POV_PREF) throw new Error('pricing item endpoint not provided');
    ctrlPricing?.abort();
    ctrlPricing = new AbortController();
    const r = await fetch(urlPricingItem(id), { credentials:'same-origin', signal: ctrlPricing.signal });
    const j = await safeJson(r);
    if (!r.ok || !j.ok) throw new Error('pricing item fail');
    return j;
  }

  async function saveOverride(id, rawOrNull){
    if (!EP_POV_PREF) throw new Error('pricing item endpoint not provided');
    const payload = (rawOrNull==null || rawOrNull==='') ? { override_markup: null }
                                                        : { override_markup: String(rawOrNull).replace('.',',') };
    const r = await fetch(urlPricingItem(id), {
      method:'POST', credentials:'same-origin',
      headers:{'Content-Type':'application/json','X-CSRFToken': csrf()},
      body: JSON.stringify(payload)
    });
    const j = await safeJson(r);
    if (!r.ok || !j.ok) throw new Error('save override fail');
    return j;
  }

  // ====== kiri: list pekerjaan ======
  function renderList(){
    const q = ($search?.value || '').toLowerCase().trim();
    filtered = !q ? rows.slice() : rows.filter(r =>
      (r.kode || '').toLowerCase().includes(q) ||
      (r.uraian || '').toLowerCase().includes(q)
    );

    if (!filtered.length){
      if ($list) $list.innerHTML = `<li class="rk-item"><div class="row-note">Tidak ada hasil.</div></li>`;
      if ($grand) $grand.textContent = `Grand Total: ${fmt(0)}`;
      return;
    }

    let grand = 0;
    const fr = document.createDocumentFragment();
    filtered.forEach(r => {
      const A = num(r.A), B = num(r.B), C = num(r.C), L = num(r.LAIN || 0);
      const E = A + B + C + L;
      const bukEff = (r.markup_eff != null ? Number(r.markup_eff) : projectBUK);
      const F = E * (bukEff/100);
      const G = E + F;
      const total = G * num(r.volume);
      grand += total;

      const li = document.createElement('li');
      li.className = 'rk-item';
      li.dataset.id = r.pekerjaan_id;
      li.innerHTML = `
        <div class="rk-item-title">${esc(r.uraian || '')}</div>
        <div class="rk-item-meta">
          <span class="mono">${esc(r.kode || '')}</span>
          ${Math.abs(bukEff - projectBUK) > 1e-6 ? `<span class="rk-chip rk-chip-warn mono">${bukEff.toFixed(2)}%</span>` : ''}
          <span class="rk-chip mono">${esc(r.satuan || '')}</span>
          <span class="row-note">Total:</span><span class="mono">${fmt(total)}</span>
        </div>
      `;
      li.addEventListener('click', () => selectItem(r.pekerjaan_id));
      fr.appendChild(li);
    });

    if ($list){
      $list.innerHTML = '';
      $list.appendChild(fr);
    }
    if ($grand) $grand.textContent = `Grand Total: ${fmt(grand)}`;

    highlightActive();
  }

  function highlightActive(){
    if (!$list) return;
    const items = $list.querySelectorAll('.rk-item');
    items.forEach(el => el.classList.toggle('active', String(el.dataset.id) === String(selectedId)));
  }

  // ====== kanan: detail satu pekerjaan ======
  async function selectItem(id){
    if (!id || Number(id) <= 0) { console.warn('skip selectItem invalid id:', id); return; }
    selectedId = id;
    localStorage.setItem('rk-last-pkj-id', String(id));
    highlightActive();
    const myToken = ++selectToken;

    setLoading(true);
    try{
      // header awal dari rows
      const r = rows.find(x => x.pekerjaan_id === id);
      if ($kode)   $kode.textContent   = r?.kode   || '—';
      if ($uraian) $uraian.textContent = r?.uraian || '—';
      if ($sat)    $sat.textContent    = r?.satuan || '—';

      // pricing item (optional)
      let effPct = projectBUK;
      if (!EP_POV_PREF) {
        setOverrideUIEnabled(false);
        if ($eff) $eff.textContent = `Efektif: ${projectBUK.toFixed(2)}%`;
      } else {
        setOverrideUIEnabled(true);
        try{
          const pp = await getPricingItem(id);
          if (myToken !== selectToken) return;
          effPct = Number(pp.effective_markup);
          if ($ovrInput) $ovrInput.value = (pp.override_markup ?? '');
          if ($ovrChip)  $ovrChip.hidden = !(pp.override_markup != null);
          if ($eff)      $eff.textContent = `Efektif: ${pp.effective_markup}%`;
        }catch{
          if (myToken !== selectToken) return;
          if ($ovrInput) $ovrInput.value = '';
          if ($ovrChip)  $ovrChip.hidden = true;
          if ($eff)      $eff.textContent = `Efektif: ${projectBUK.toFixed(2)}%`;
        }
      }

      // detail
      let detail = cacheDetail.get(id);
      if (!detail){
        detail = await fetchDetail(id);
      }
      if (myToken !== selectToken) return;

      const items = detail.items || [];
      renderDetailTable(items, effPct);
      if ($src) $src.textContent = (detail.pekerjaan?.source_type || '—').toUpperCase();
    } finally {
      setLoading(false);
    }
  }

  function renderDetailTable(items, effPct){
    if (!$tbody) return;
    const group = {TK:[],BHN:[],ALT:[],LAIN:[]};
    for (const it of items){
      const k = (it.kategori || '').toUpperCase();
      if (group[k]) group[k].push(it);
    }

    const fr = document.createDocumentFragment();
    let no = 1;

    function addSec(title, arr){
      const trh = document.createElement('tr');
      trh.className='sec-head';
      trh.innerHTML = `<td colspan="7">${esc(title)}</td>`;
      fr.appendChild(trh);

      let subtotal = 0;
      arr.forEach((it) => {
        const kf = num(it.koefisien);
        const hr = num(it.harga_satuan);
        const jm = kf * hr;
        subtotal += jm;
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td class="mono">${no++}</td>
          <td>${esc(it.uraian || '')}</td>
          <td class="mono">${esc(it.kode || '')}</td>
          <td class="mono">${esc(it.satuan || '')}</td>
          <td class="mono">${kf.toLocaleString(locale,{minimumFractionDigits:6, maximumFractionDigits:6})}</td>
          <td class="mono">${fmt(hr)}</td>
          <td class="mono">${fmt(jm)}</td>
        `;
        fr.appendChild(tr);
      });

      const trs = document.createElement('tr');
      trs.className='sec-sum';
      trs.innerHTML = `<td colspan="6">Subtotal ${esc(title.split('—')[0].trim())}</td><td class="mono">${fmt(subtotal)}</td>`;
      fr.appendChild(trs);
      return subtotal;
    }

    $tbody.innerHTML = '';
    const sA = addSec('A — Tenaga Kerja', group.TK);
    const sB = addSec('B — Bahan',        group.BHN);
    const sC = addSec('C — Peralatan',    group.ALT);
    const sD = addSec('D — Lainnya',      group.LAIN);

    const E = sA+sB+sC+sD;
    const F = E * (num(effPct)/100);
    const G = E + F;

    const tre = document.createElement('tr');
    tre.className='tot-row';
    tre.innerHTML = `<td colspan="6">E — Jumlah (A+B+C+D)</td><td class="mono">${fmt(E)}</td>`;
    const trf = document.createElement('tr');
    trf.className='tot-row';
    trf.innerHTML = `<td colspan="6">F — BUK × E</td><td class="mono">${fmt(F)}</td>`;
    const trg = document.createElement('tr');
    trg.className='tot-row';
    trg.innerHTML = `<td colspan="6">G — HSP = E + F</td><td class="mono">${fmt(G)}</td>`;

    fr.appendChild(tre); fr.appendChild(trf); fr.appendChild(trg);
    $tbody.appendChild(fr);
  }

  // ====== events ======
  function debounce(fn, ms){ let t; return (...args)=>{ clearTimeout(t); t=setTimeout(()=>fn(...args), ms); }; }
  if ($search) {
    $search.addEventListener('input', debounce(() => {
      renderList();
      highlightActive();
    }, 120));
  }

  if ($ovrApply) {
    $ovrApply.addEventListener('click', async () => {
      if (selectedId == null) return;
      const v = parsePctUI($ovrInput?.value);
      if (v==null || v<0 || v>100){ showToast('Override BUK harus 0..100', 'warn'); return; }
      $ovrApply.disabled = true;
      try{
        await saveOverride(selectedId, v);
        const pp = await getPricingItem(selectedId);
        if ($eff) $eff.textContent = `Efektif: ${pp.effective_markup}%`;
        if ($ovrChip) $ovrChip.hidden = !(pp.override_markup != null);

        const idx = rows.findIndex(r => r.pekerjaan_id === selectedId);
        if (idx >= 0) rows[idx].markup_eff = Number(pp.effective_markup);
        renderList();

        const det = cacheDetail.get(selectedId);
        renderDetailTable(det?.items || [], Number(pp.effective_markup));

        showToast('Override BUK tersimpan', 'success');
      }catch(e){
        console.error(e); showToast('Gagal menerapkan override', 'error');
      }finally{ $ovrApply.disabled = false; }
    });
  }

  if ($ovrInput) {
    $ovrInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !$ovrApply?.disabled) {
        e.preventDefault();
        $ovrApply?.click();
      }
    });
  }

  if ($ovrClear) {
    $ovrClear.addEventListener('click', async () => {
      if (selectedId == null) return;
      $ovrClear.disabled = true;
      try{
        await saveOverride(selectedId, null);
        const pp = await getPricingItem(selectedId);
        if ($ovrInput) $ovrInput.value = '';
        if ($eff)      $eff.textContent = `Efektif: ${pp.effective_markup}%`;
        if ($ovrChip)  $ovrChip.hidden = true;

        const idx = rows.findIndex(r => r.pekerjaan_id === selectedId);
        if (idx >= 0) rows[idx].markup_eff = Number(pp.effective_markup);
        renderList();

        const det = cacheDetail.get(selectedId);
        renderDetailTable(det?.items || [], Number(pp.effective_markup));

        showToast('Override dihapus', 'info');
      }catch(e){
        console.error(e); showToast('Gagal menghapus override', 'error');
      }finally{ $ovrClear.disabled = false; }
    });
  }

  document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      $search?.focus();
      $search?.select();
    }
  });

  // ====== init ======
  (async () => {
    try{
      applyIconAndUIFixes();
      if (!EP_POV_PREF) setOverrideUIEnabled(false);
      await loadProjectBUK();
      await loadRekap();
    }catch(e){
      console.error(e);
      if ($list) $list.innerHTML = `<li class="rk-item"><div class="row-note">Gagal memuat.</div></li>`;
    }
  })();

  // ====== Resizer: drag/keyboard untuk ubah lebar panel kiri ======
  (function initResizer(){
    if (!$resizer || !$leftPane || !$grid) return;

    const setLeftW = (px) => { ROOT.style.setProperty('--rk-left-w', `${px}px`); };
    const getLeftW = () => {
      const v = getComputedStyle(ROOT).getPropertyValue('--rk-left-w').trim();
      const n = parseInt(v, 10);
      return Number.isFinite(n) ? n : 360;
    };

    // restore
    const saved = parseInt(localStorage.getItem('rk-left-w') || '', 10);
    if (saved) setLeftW(saved);

    let startX = 0, startW = 0;
    const MIN = 240, MAX = 640;

    let raf = null;
    const onMove = (e) => {
      const dx = e.clientX - startX;
      const w = Math.max(MIN, Math.min(MAX, startW + dx));
      if (raf) return;
      raf = requestAnimationFrame(() => {
        setLeftW(w);
        raf = null;
      });
    };

    const onUp = () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      document.body.style.userSelect = '';
      const cur = getLeftW();
      if (!Number.isNaN(cur)) localStorage.setItem('rk-left-w', String(cur));
    };

    $resizer.addEventListener('mousedown', (e) => {
      e.preventDefault();
      startX = e.clientX;
      startW = getLeftW();
      document.body.style.userSelect = 'none';
      window.addEventListener('mousemove', onMove);
      window.addEventListener('mouseup', onUp);
    });

    // keyboard support
    $resizer.addEventListener('keydown', (e) => {
      const step = (e.shiftKey ? 20 : 10);
      if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        e.preventDefault();
        const cur = getLeftW();
        const next = Math.max(MIN, Math.min(MAX, cur + (e.key === 'ArrowRight' ? step : -step)));
        setLeftW(next);
        localStorage.setItem('rk-left-w', String(next));
      }
      if (e.key.toLowerCase() === 'r') { // reset
        setLeftW(360);
        localStorage.setItem('rk-left-w', '360');
      }
    });

    // double-click resizer => reset
    $resizer.addEventListener('dblclick', () => {
      setLeftW(360);
      localStorage.setItem('rk-left-w', '360');
    });
  })();

})();
