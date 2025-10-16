// harga_items.js — Drop-in full version (formal terms + robust conversion)
// - Patuh SSOT (tidak menulis --dp-*), hanya menulis var halaman (--hi-toolbar-h)
// - Fitur: autofill 0, validasi angka (negatif/>2dp/out-of-range), bulk paste, konversi satuan
(function(){
  const ROOT = document.getElementById('hi-app');
  if (!ROOT) return;

  const N = window.Numeric || null;
  const DP = 2;
  const MAX_PRICE = 1e12; // batas aman
  const locale = ROOT.dataset.locale || 'id-ID';
  const fmtRp = new Intl.NumberFormat(locale, {
    style: 'currency', currency: 'IDR',
    minimumFractionDigits: 2, maximumFractionDigits: 2
  });

  // Endpoints
  const EP_LIST = (ROOT.dataset.endpointList || '') + '?canon=1';
  const EP_SAVE = ROOT.dataset.endpointSave || '';

  // DOM
  const $tbody = document.getElementById('hi-tbody');
  const $filter = document.getElementById('hi-filter');
  const $btnSave = document.getElementById('hi-btn-save');
  // Unified export (dropdown like Rekap RAB)
  const btnExportCSV  = document.getElementById('btn-export-csv');
  const btnExportPDF  = document.getElementById('btn-export-pdf');
  const btnExportWord = document.getElementById('btn-export-word');
  const $stats = document.getElementById('hi-stats');
  const $bukInput = document.getElementById('hi-buk-input');

  // Sinkron tinggi toolbar (var halaman, bukan global)
  const rootEl = document.querySelector(':root[data-page="harga_items"]') || document.documentElement;
  const toolbar = document.getElementById('hi-toolbar');
  const debounce = (fn, ms=120)=>{ let t; return (...a)=>{ clearTimeout(t); t=setTimeout(()=>fn(...a), ms); }; };
  function syncToolbarH(){
    if (!rootEl || !toolbar) return;
    rootEl.style.setProperty('--hi-toolbar-h', Math.ceil(toolbar.getBoundingClientRect().height) + 'px');
  }
  window.addEventListener('resize', debounce(syncToolbarH, 120));
  syncToolbarH();

  // State
  const katMap = { TK:'Tenaga', BHN:'Bahan', ALT:'Alat', LAIN:'Lainnya' };
  const Dim = { MASS:'mass', VOL:'volume', COUNT:'count', OTHER:'other' };
  let rows = [];
  let viewRows = [];
  let bukCanonLoaded = "";

  // ===== Helpers: numeric & format
  const toUI = (s)=> N ? N.formatForUI(N.enforceDp(s||'', DP)) : (s||'');
  const toCanon = (v)=> N ? (N.enforceDp(N.canonicalizeForAPI(v||''), DP) || '') : String(v||'');
  const toUI2 = (s)=> N ? N.formatForUI(N.enforceDp(s||'', 2)) : (s||'');
  const toCanon2 = (v)=> N ? (N.enforceDp(N.canonicalizeForAPI(v||''), 2) || '') : String(v||'');
  const toCanonFloat = (v, dp=6)=> N ? (N.enforceDp(N.canonicalizeForAPI(v||''), dp) || '') : String(v||'');
  const rupiah = (canon)=>{
    if (canon == null || canon === '') return '—';
    const n = Number(canon); if (!isFinite(n)) return '—';
    return fmtRp.format(n);
  };
  const decCountRaw = (raw)=>{
    const str = String(raw ?? '');
    if (!str) return 0;
    const i = Math.max(str.lastIndexOf('.'), str.lastIndexOf(','));
    return i === -1 ? 0 : (str.length - i - 1);
  };
  const csrfToken = ()=>{
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  };
  function inferDim(u){
    const s = (u||'').toLowerCase().trim();
    if (['kg','g','gram','ons','ton','mg'].includes(s)) return Dim.MASS;
    if (['m3','m³','l','lt','liter','ml'].includes(s)) return Dim.VOL;
    if (['zak','pcs','buah','unit','bh'].includes(s)) return Dim.COUNT;
    return Dim.OTHER;
  }

  // ===== Konversi: in-memory + localStorage per Kode
  const convStore = new Map(); // key: item.id -> profile
  const lsk = (kode)=> 'hiConv:' + kode;

  // ===== Fetch list
  async function fetchList(){
    setEmpty('Memuat data…');
    try{
      const res = await fetch(EP_LIST, { credentials:'same-origin' });
      const j = await res.json();
      if (!j.ok) throw new Error('Gagal memuat.');
      rows = (j.items || []).map((it,i)=>({
        idx: i+1,
        id: it.id,
        kode: it.kode_item,
        uraian: it.uraian,
        satuan: it.satuan || '',
        kategori: it.kategori,
        harga_canon: it.harga_satuan == null ? '' : String(it.harga_satuan),
        conv: it.conv || null // opsional dari server
      }));

      // Prefill konversi dari server atau localStorage
      rows.forEach(r=>{
        if (r.conv) convStore.set(r.id, r.conv);
        else {
          try{
            const raw = localStorage.getItem(lsk(r.kode));
            if (raw) convStore.set(r.id, JSON.parse(raw));
          }catch{}
        }
      });

      // BUK
      if (j.meta && typeof j.meta.markup_percent !== 'undefined'){
        bukCanonLoaded = String(j.meta.markup_percent || '10.00');
        if ($bukInput) $bukInput.value = toUI2(bukCanonLoaded);
      }
      renderTable(rows);
    }catch(e){
      setEmpty('Gagal memuat data.');
      console.error(e);
    }
  }

  function setEmpty(text){
    $tbody.innerHTML = `<tr class="hi-empty"><td colspan="7">${text}</td></tr>`;
    $stats.textContent = '0 item';
  }

  // ===== Render table
  function renderTable(data){
    if (!data || data.length === 0){ setEmpty('Tidak ada item harga yang digunakan di Detail AHSP.'); return; }
    const fr = document.createDocumentFragment();
    viewRows = [];
    data.forEach((r,i)=>{
      const tr = document.createElement('tr');
      tr.dataset.itemId = r.id;
      tr.dataset.kode = (r.kode||'').toLowerCase();
      tr.dataset.uraian = (r.uraian||'').toLowerCase();
      tr.dataset.kategori = r.kategori || '';
      tr.dataset.satuan = r.satuan || '';
      const canonDisp = (r.harga_canon === '' ? '0.00' : r.harga_canon);

      tr.innerHTML = `
        <td class="mono text-center">${i+1}</td>
        <td>${escapeHtml(katMap[r.kategori] || r.kategori || '')}</td>
        <td class="mono">${escapeHtml(r.kode)}</td>
        <td>${escapeHtml(r.uraian)}</td>
        <td>${escapeHtml(r.satuan)}</td>
        <td>
          <div class="d-flex align-items-center gap-2">
            <input type="text" inputmode="decimal"
                   class="form-control form-control-sm ux-focusable hi-input-price text-end ux-tabular"
                   value="${escapeAttr(toUI(canonDisp))}"
                   aria-label="Harga satuan untuk ${escapeAttr(r.kode)}">
            <button type="button"
                    class="btn btn-sm btn-outline-secondary hi-conv-open"
                    title="Konversi satuan (bantu hitung)"
                    data-bs-toggle="modal" data-bs-target="#hiConvModal">
              <i class="bi bi-arrow-left-right" aria-hidden="true"></i>
              <span class="only-desktop">Konversi</span>
            </button>
          </div>
        </td>
        <td class="mono hi-price-preview">${escapeHtml(rupiah(canonDisp))}</td>
      `;
      fr.appendChild(tr);
      viewRows.push(tr);
    });
    $tbody.innerHTML = '';
    $tbody.appendChild(fr);
    $stats.textContent = `${data.length} item`;
  }

  const escapeHtml = (s)=> (s??'').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  const escapeAttr = (s)=> escapeHtml(s);

  // ===== Filter
  $filter?.addEventListener('input', ()=>{
    const q = ($filter.value||'').trim().toLowerCase();
    if (!q){ viewRows.forEach(tr=> tr.hidden=false); $stats.textContent = `${viewRows.length} item`; return; }
    let show=0;
    viewRows.forEach(tr=>{
      const hit = tr.dataset.kode.includes(q)
        || tr.dataset.uraian.includes(q)
        || (katMap[tr.dataset.kategori]||'').toLowerCase().includes(q);
      tr.hidden = !hit; if (hit) show++;
    });
    $stats.textContent = `${show} / ${viewRows.length} item`;
  });

  // ===== Blur: validasi + autofill 0
  $tbody.addEventListener('blur', (e)=>{
    const el = e.target;
    if (!(el instanceof HTMLInputElement) || !el.classList.contains('hi-input-price')) return;

    const raw = el.value;
    const dec = decCountRaw(raw);
    let canon = toCanon(raw);
    if (!canon) canon = '0.00'; // autofill 0
    const num = Number(canon);

    const invalid = !isFinite(num) || dec > DP || num < 0 || num > MAX_PRICE;
    el.value = toUI(canon);
    el.classList.toggle('ux-invalid', invalid);

    const prev = el.closest('tr')?.querySelector('.hi-price-preview');
    if (prev) prev.textContent = invalid ? '—' : rupiah(canon);
  }, true);

  // ===== BUK: enforce 2dp pada blur
  $bukInput?.addEventListener('blur', ()=>{
    const canon = toCanon2($bukInput.value);
    $bukInput.value = toUI2(canon || bukCanonLoaded);
  });

  // ===== SAVE
  $btnSave?.addEventListener('click', async ()=>{
    try{
      const payload = { items: [] };
      const mpCanon = toCanon2($bukInput?.value);

      // kumpulkan harga
      viewRows.forEach(tr=>{
        const id = Number(tr.dataset.itemId);
        const input = tr.querySelector('.hi-input-price');
        if (!input) return;

        let canon = toCanon(input.value);
        if (!canon) canon = '0.00';
        const n = Number(canon);
        const invalid = !isFinite(n) || n < 0 || n > MAX_PRICE;
        input.classList.toggle('ux-invalid', invalid);
        if (invalid) return;

        payload.items.push({ id, harga_satuan: canon });
      });

      // konversi → jika user minta simpan ke server
      const conversions = [];
      convStore.forEach((p, id)=>{
        if (p && p.rememberServer){
          conversions.push({ id, ...p });
        }
      });
      if (conversions.length) payload.conversions = conversions;
      if (mpCanon) payload.markup_percent = mpCanon;

      if (payload.items.length === 0 && !payload.conversions && (!mpCanon || mpCanon === bukCanonLoaded)){
        toast('Tidak ada perubahan valid untuk disimpan.', 'info');
        return;
      }

      const spin = document.getElementById('hi-save-spin');
      $btnSave.disabled = true; spin?.removeAttribute('hidden');

      const res = await fetch(EP_SAVE, {
        method:'POST',
        headers:{ 'Content-Type':'application/json', 'X-CSRFToken': csrfToken() },
        credentials:'same-origin',
        body: JSON.stringify(payload),
      });
      const j = await res.json();
      if (!res.ok || !j.ok){
        console.warn(j);
        toast('Sebagian gagal disimpan. Cek log.', 'warn');
      } else {
        toast(`Berhasil menyimpan ${j.updated ?? payload.items.length} item.`, 'success');
      }
    }catch(e){
      console.error(e); toast('Gagal menyimpan.', 'error');
    }finally{
      const spin = document.getElementById('hi-save-spin');
      $btnSave.disabled = false; spin?.setAttribute('hidden','');
      fetchList(); // segarkan tampilan
    }
  });

  // ===== EXPORT CSV
  // Export CSV (fallback local), or unified via ExportManager if available
  function exportCSVLocal(){
    const headers = ['No','Kategori','Kode','Uraian','Satuan','Harga','Nominal'];
    const lines = [headers.join(';')];
    let idx=0;
    viewRows.forEach(tr=>{
      if (tr.hidden) return;
      const kategori = tr.children[1].textContent.trim();
      const kode = tr.children[2].textContent.trim();
      const uraian = tr.children[3].textContent.trim().replace(/;/g, ',');
      const satuan = tr.children[4].textContent.trim();
      const input = tr.querySelector('.hi-input-price');
      let canon = toCanon(input.value); if (!canon) canon='0.00';
      const nominal = rupiah(canon).replace(/^Rp\s?/, 'Rp ');
      lines.push([++idx, kategori, kode, uraian, satuan, canon, nominal].join(';'));
    });
    const blob = new Blob([lines.join('\n')], { type:'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = `harga_items_${(new Date()).toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  (function initUnifiedExport(){
    const projectId = ROOT?.dataset?.projectId;
    if (!projectId){
      // bind CSV local only
      btnExportCSV?.addEventListener('click', exportCSVLocal);
      btnExportPDF?.addEventListener('click', ()=> toast && toast('Export PDF belum tersedia', 'info'));
      btnExportWord?.addEventListener('click', ()=> toast && toast('Export Word belum tersedia', 'info'));
      return;
    }
    if (typeof ExportManager === 'undefined'){
      btnExportCSV?.addEventListener('click', exportCSVLocal);
      btnExportPDF?.addEventListener('click', ()=> toast && toast('Export PDF belum tersedia', 'info'));
      btnExportWord?.addEventListener('click', ()=> toast && toast('Export Word belum tersedia', 'info'));
      return;
    }
    try{
      // Page type for backend endpoints (to be provided server-side)
      const exporter = new ExportManager(projectId, 'harga-items');
      btnExportCSV?.addEventListener('click', (e)=>{ e.preventDefault(); exporter.exportAs('csv'); });
      btnExportPDF?.addEventListener('click', (e)=>{ e.preventDefault(); exporter.exportAs('pdf'); });
      btnExportWord?.addEventListener('click', (e)=>{ e.preventDefault(); exporter.exportAs('word'); });
    }catch(err){
      console.warn('[HI] ExportManager init failed, fallback to local CSV', err);
      btnExportCSV?.addEventListener('click', exportCSVLocal);
      btnExportPDF?.addEventListener('click', ()=> toast && toast('Export PDF belum tersedia', 'info'));
      btnExportWord?.addEventListener('click', ()=> toast && toast('Export Word belum tersedia', 'info'));
    }
  })();

  // ===== BULK PASTE (Kode;[Unit];Harga;[Factor];[Density])
  document.addEventListener('paste', (e)=>{
    if (!e.clipboardData) return;
    const text = e.clipboardData.getData('text');
    if (!text || !text.includes('\n')) return; // bukan tabel
    const rowsPaste = text.trim().split(/\r?\n/).map(line => line.split(/\t|;|,/));
    let hit=0, invalid=0;
    const byKode = new Map();

    rowsPaste.forEach(cols=>{
      const [kode, unit, harga, factor, density] = cols;
      const k = String(kode||'').trim().toLowerCase(); if (!k) return;
      const canonHarga = toCanon(harga||'0') || '0.00';
      const factorCanon = toCanonFloat(factor||'', 6);
      const densityCanon = toCanonFloat(density||'', 6);
      byKode.set(k, { unit, harga: canonHarga, factor: factorCanon, density: densityCanon });
    });

    viewRows.forEach(tr=>{
      const k = (tr.dataset.kode||'').toLowerCase();
      if (!byKode.has(k)) return;
      const { harga, factor, unit, density } = byKode.get(k);

      const input = tr.querySelector('.hi-input-price');
      const prev = tr.querySelector('.hi-price-preview');
      if (!input || !prev) return;

      const n = Number(harga);
      const isInv = !isFinite(n) || n < 0 || n > MAX_PRICE;

      input.value = toUI(harga);
      input.classList.toggle('ux-invalid', isInv);
      prev.textContent = isInv ? '—' : rupiah(harga);
      if (isInv) invalid++; else hit++;

      // simpan profil konversi jika ada factor (tanpa push ke server)
      if (factor){
        convStore.set(Number(tr.dataset.itemId), {
          unit: (unit || '').toString(),
          price_market: toCanon2(harga) || '',
          factor_to_base: factor,
          density: density || '',
          capacity_m3: '',
          capacity_ton: '',
          method: 'direct',
          base_unit: tr.dataset.satuan || tr.children[4].textContent.trim(),
          updated_at: (new Date()).toISOString(),
          remember: true,
          rememberServer: false
        });
      }
    });

    toast(`Paste massal: ${hit} baris${invalid?`, ${invalid} tidak valid`:''}.`, invalid ? 'warn' : 'success');
  });

  // ===== Modal Konversi: setup
  let convCtx = { tr:null, id:null, kode:'', base:'', baseDim:Dim.OTHER };

  const $convModal = document.getElementById('hiConvModal');
  const $convItem = document.getElementById('hi-conv-item');
  const $convUnit = document.getElementById('hi-conv-unit');
  const $convUnitCustom = document.getElementById('hi-conv-unit-custom');
  const $convPrice = document.getElementById('hi-conv-price');
  const $convCapM3Wrap = document.getElementById('hi-capacity-m3-wrap');
  const $convCapTonWrap = document.getElementById('hi-capacity-ton-wrap');
  const $convCapM3 = document.getElementById('hi-conv-cap-m3');
  const $convCapTon = document.getElementById('hi-conv-cap-ton');
  const $convDensityWrap = document.getElementById('hi-density-wrap');
  const $convDensity = document.getElementById('hi-conv-density');
  const $convFactor = document.getElementById('hi-conv-factor');
  const $convBase = document.getElementById('hi-conv-base');
  const $convToBase = document.getElementById('hi-conv-to-base');
  const $convUnitLabel = document.getElementById('hi-conv-unit-label');
  const $convResult = document.getElementById('hi-conv-result');
  const $convHint = document.getElementById('hi-conv-hint');
  const $convApply = document.getElementById('hi-conv-apply');
  const $convError = document.getElementById('hi-conv-error');

  function setUnitLabel(lbl){ $convUnitLabel.textContent = lbl; }
  function resetModal(){
    [$convPrice,$convCapM3,$convCapTon,$convDensity,$convFactor].forEach(i=>{ if(i){ i.value=''; }});
    $convResult.textContent = '—'; $convHint.textContent = '';
    $convApply.disabled = true; $convError?.classList.add('d-none');
    $convCapM3Wrap.classList.add('d-none'); $convCapTonWrap.classList.add('d-none'); $convDensityWrap.classList.add('d-none');
    const formula = document.getElementById('hi-conv-formula');
    if (formula) formula.textContent = 'Rumus: Harga per satuan pembelian dari Supplier ÷ Konstanta konversi';
  }

  // buka modal dari baris
  $tbody.addEventListener('click', (e)=>{
    const btn = e.target.closest('.hi-conv-open'); if (!btn) return;
    const tr = btn.closest('tr'); if (!tr) return;

    convCtx.tr = tr;
    convCtx.id = Number(tr.dataset.itemId);
    convCtx.kode = tr.children[2]?.textContent?.trim() || '';
    convCtx.base = tr.dataset.satuan || tr.children[4]?.textContent?.trim() || '';
    convCtx.baseDim = inferDim(convCtx.base);

    resetModal();

    // header item & label base
    $convItem.textContent = `${tr.children[3]?.textContent?.trim() || '(Tanpa uraian)'} — ${convCtx.kode}`;
    $convBase.textContent = convCtx.base || '-';
    $convToBase.textContent = convCtx.base || '-';

    // unit default
    $convUnit.value = 'dump_truck';
    $convUnitCustom.classList.add('d-none');
    setUnitLabel('satuan pembelian dari Supplier');

    // restore profil (server/local)
    const prof = convStore.get(convCtx.id) || null;
    if (prof){
      const unitOpt = ['dump_truck','m3','ton','zak','custom'].includes(prof.unit) ? prof.unit : 'custom';
      $convUnit.value = unitOpt;
      if (unitOpt==='custom'){
        $convUnitCustom.classList.remove('d-none');
        $convUnitCustom.value = prof.unit || 'satuan pembelian dari Supplier';
        setUnitLabel($convUnitCustom.value || 'satuan pembelian dari Supplier');
      } else {
        setUnitLabel(unitOpt);
      }
      if (prof.price_market) $convPrice.value = toUI2(prof.price_market);
      if (prof.factor_to_base) $convFactor.value = toUI2(prof.factor_to_base);
      if (prof.capacity_m3){ $convCapM3Wrap.classList.remove('d-none'); $convCapM3.value = toUI2(prof.capacity_m3); }
      if (prof.capacity_ton){ $convCapTonWrap.classList.remove('d-none'); $convCapTon.value = toUI2(prof.capacity_ton); }
      if (prof.density){ $convDensityWrap.classList.remove('d-none'); $convDensity.value = toUI2(prof.density); }
    }

    updateHelperVisibility();
    recalcConv();
  });

  // perubahan unit
  $convUnit?.addEventListener('change', ()=>{
    const v = $convUnit.value;
    if (v === 'custom'){
      $convUnitCustom.classList.remove('d-none');
      setUnitLabel($convUnitCustom.value || 'satuan pembelian dari Supplier');
    }else{
      $convUnitCustom.classList.add('d-none');
      setUnitLabel(v);
    }
    updateHelperVisibility();
    recalcConv();
  });

  $convUnitCustom?.addEventListener('input', ()=>{
    if ($convUnit.value==='custom'){
      setUnitLabel($convUnitCustom.value || 'satuan pembelian dari Supplier');
      recalcConv();
    }
  });

  // input → hitung ulang
  [$convPrice,$convCapM3,$convCapTon,$convDensity,$convFactor].forEach(el=>{
    el?.addEventListener('input', ()=>{
      if (el=== $convCapM3 || el === $convCapTon || el === $convDensity) autoFillFactor();
      recalcConv();
    });
  });

  // apply konversi
  $convApply?.addEventListener('click', ()=>{
    const canon = recalcConv(true);
    if (!canon){ $convError?.classList.remove('d-none'); return; }

    const input = convCtx.tr?.querySelector('.hi-input-price');
    const prev = convCtx.tr?.querySelector('.hi-price-preview');
    if (input){ input.value = toUI(canon); input.classList.remove('ux-invalid'); }
    if (prev){ prev.textContent = rupiah(canon); }

    // simpan profil
    const unitName = ($convUnit.value==='custom') ? ($convUnitCustom.value || 'satuan pembelian dari Supplier') : $convUnit.value;
    const prof = {
      unit: unitName,
      price_market: toCanon2($convPrice.value) || '',
      factor_to_base: toCanonFloat($convFactor.value,6) || '',
      density: toCanonFloat($convDensity.value,6) || '',
      capacity_m3: toCanonFloat($convCapM3.value,6) || '',
      capacity_ton: toCanonFloat($convCapTon.value,6) || '',
      method: deriveMethod(),
      base_unit: convCtx.base,
      updated_at: (new Date()).toISOString(),
      remember: !!document.getElementById('hi-conv-remember')?.checked,
      rememberServer: !!document.getElementById('hi-conv-remember-server')?.checked
    };
    convStore.set(convCtx.id, prof);

    try{
      if (prof.remember){ localStorage.setItem(lsk(convCtx.kode), JSON.stringify(prof)); }
      else { localStorage.removeItem(lsk(convCtx.kode)); }
    }catch{}

    if (window.bootstrap && $convModal){
      window.bootstrap.Modal.getOrCreateInstance($convModal).hide();
    }
  });

  $convModal?.addEventListener('hidden.bs.modal', resetModal);

  function deriveMethod(){
    if ($convFactor.value && ($convCapM3.value || $convCapTon.value || $convDensity.value)) return 'hybrid';
    if ($convFactor.value) return 'direct';
    if ($convCapM3.value || $convCapTon.value || $convDensity.value) return 'calc';
    return 'unknown';
  }

  function updateHelperVisibility(){
    const unit = $convUnit.value;
    $convCapM3Wrap.classList.add('d-none');
    $convCapTonWrap.classList.add('d-none');
    $convDensityWrap.classList.add('d-none');

    // tampilkan helper sesuai unit
    if (unit === 'dump_truck' || unit === 'm3') $convCapM3Wrap.classList.remove('d-none');
    if (unit === 'ton') $convCapTonWrap.classList.remove('d-none');

    // density hanya bila konversi volume -> massa
    const unitDim = (unit==='m3' || unit==='dump_truck') ? Dim.VOL : (unit==='ton' ? Dim.MASS : Dim.OTHER);
    if (unitDim === Dim.VOL && convCtx.baseDim === Dim.MASS) $convDensityWrap.classList.remove('d-none');

    // label unit
    setUnitLabel(unit==='custom' ? ($convUnitCustom.value || 'satuan pembelian dari Supplier') : unit);
  }

  function autoFillFactor(){
    // hitung faktor dari parameter (jika masuk akal)
    const unit = $convUnit.value;
    let factor = '';

    if ((unit==='dump_truck' || unit==='m3') && convCtx.baseDim === Dim.MASS){
      const cap = Number(toCanonFloat($convCapM3.value,6) || 'NaN'); // m3
      const dens = Number(toCanonFloat($convDensity.value,6) || 'NaN'); // kg/m3
      if (isFinite(cap) && cap>0 && isFinite(dens) && dens>0){
        factor = String(cap * dens); // m3 * (kg/m3) = kg
      }
    }else if ((unit==='dump_truck' || unit==='m3') && convCtx.baseDim === Dim.VOL){
      const cap = Number(toCanonFloat($convCapM3.value,6) || 'NaN'); // m3
      if (isFinite(cap) && cap>0){ factor = String(cap); } // m3 -> m3
    }else if (unit==='ton' && convCtx.baseDim === Dim.MASS){
      const capTon = Number(toCanonFloat($convCapTon.value,6) || 'NaN'); // ton
      if (isFinite(capTon) && capTon>0){
        const base = (convCtx.base||'').toLowerCase();
        const toKg = base === 'kg' ? 1000 : 1; // asumsi: jika base kg, 1 ton = 1000 kg
        factor = String(capTon * toKg);
      }
    }
    if (factor){
      $convFactor.value = toUI2(N ? N.enforceDp(factor,6) : factor);
    }
  }

  function recalcConv(strict=false){
    const price = toCanon2($convPrice.value);
    const factor = toCanonFloat($convFactor.value, 6);

    const pn = Number(price), fn = Number(factor);
    const invalid = !isFinite(pn) || pn < 0 || pn > MAX_PRICE || !isFinite(fn) || fn <= 0;
    $convApply.disabled = invalid;
    $convError?.classList.toggle('d-none', !invalid);

    if (invalid){
      $convResult.textContent = '—';
      $convHint.textContent = '';
      return strict ? '' : '';
    }

    // harga per satuan dasar = harga per satuan pembelian ÷ konstanta konversi
    const result = pn / fn;
    const outCanon = N ? N.enforceDp(String(result), DP) : result.toFixed(DP);
    $convResult.textContent = rupiah(outCanon);

    // ringkasan audit
    const bits = [];
    const unitName = ($convUnit.value==='custom') ? ($convUnitCustom.value || 'satuan pembelian dari Supplier') : $convUnit.value;
    if ($convCapM3.value) bits.push(`${toUI2(toCanonFloat($convCapM3.value,2))} m³`);
    if ($convCapTon.value) bits.push(`${toUI2(toCanonFloat($convCapTon.value,2))} ton`);
    if ($convDensity.value) bits.push(`${toUI2(toCanonFloat($convDensity.value,2))} kg/m³`);
    const factorPretty = toUI2(factor);
    const arrow = factorPretty ? ` → ${factorPretty} ${convCtx.base}` : '';
    $convHint.textContent = bits.length
      ? `Ringkasan perhitungan: ${unitName}${bits.length?`, `:''}${bits.join(', ')}${arrow}`
      : '';

    return outCanon;
  }

  // ===== Toast minimal (pakai komponen SSOT)
  function toast(msg, level){
    let wrap = document.getElementById('dp-toast-wrap');
    if (!wrap){
      wrap = document.createElement('div');
      wrap.id = 'dp-toast-wrap';
      wrap.className = 'dp-layer-toast';
      Object.assign(wrap.style,{
        position:'fixed', right:'16px', bottom:'16px',
        display:'flex', flexDirection:'column', gap:'8px'
      });
      document.body.appendChild(wrap);
    }
    const card = document.createElement('div');
    card.className = 'dp-card dp-border dp-surface ux-text-sm';
    card.style.padding = '8px 12px';
    card.innerHTML = `<strong>${(level||'info').toUpperCase()}:</strong> <span>${msg}</span>`;
    wrap.appendChild(card);
    setTimeout(()=>{ card.remove(); if (!wrap.childElementCount) wrap.remove(); }, 2200);
  }

  // ===== Init
  fetchList();
})();
