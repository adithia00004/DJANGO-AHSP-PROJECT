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
  const syncBannerEl = document.getElementById('hi-sync-banner');
  const syncTextEl = document.getElementById('hi-sync-text');
  const syncButtonEl = document.getElementById('hi-sync-open-template');
  const lockOverlayEl = document.getElementById('hi-lock-overlay');
  const lockButtonEl = document.getElementById('hi-lock-open-template');
  const templateUrl = ROOT.dataset.templateUrl || '';
  const sourceChange = window.DP?.sourceChange || null;
  const projectId = Number(ROOT.dataset.projectId || '0');

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

  syncButtonEl?.addEventListener('click', (event) => {
    event.preventDefault();
    openTemplatePage();
  });
  lockButtonEl?.addEventListener('click', (event) => {
    event.preventDefault();
    openTemplatePage();
  });

  // P0 FIX: Toast notification system (import from core)
  const toast = window.DP && window.DP.core && window.DP.core.toast
    ? (msg, variant='info', delay=3000) => window.DP.core.toast.show(msg, variant, delay)
    : (msg) => console.log('[TOAST]', msg);

  // State
  const katMap = { TK:'Tenaga', BHN:'Bahan', ALT:'Alat', LAIN:'Lainnya' };
  const Dim = { MASS:'mass', VOL:'volume', COUNT:'count', OTHER:'other' };
  let rows = [];
  let viewRows = [];
  let bukCanonLoaded = "";

  // P0 FIX: Dirty state tracking & optimistic locking
  let dirty = false;
  let projectUpdatedAt = null;  // Timestamp for optimistic locking
  let formLocked = false;
  let pendingTemplateReloadJobs = new Set(
    sourceChange && projectId ? sourceChange.listReloadJobs(projectId) : [],
  );
  let changeStatusPending = false;

  function setDirty(val) {
    dirty = !!val;
    if ($btnSave) {
      if (dirty) {
        $btnSave.classList.add('btn-warning');
        $btnSave.classList.remove('btn-success');
      } else {
        $btnSave.classList.remove('btn-warning');
        $btnSave.classList.add('btn-success');
      }
      $btnSave.disabled = formLocked || !dirty;
    }
  }

  function openTemplatePage() {
    if (templateUrl) {
      window.open(templateUrl, '_blank', 'noopener');
    } else if (TOAST) {
      TOAST.warn('Halaman Template AHSP tidak tersedia.');
    } else {
      alert('Halaman Template AHSP tidak tersedia.');
    }
  }

  function applyLockState(locked, reasonText) {
    formLocked = !!locked;
    if (syncBannerEl) syncBannerEl.classList.toggle('d-none', !formLocked);
    if (lockOverlayEl) lockOverlayEl.classList.toggle('d-none', !formLocked);
    if (syncTextEl && reasonText) {
      syncTextEl.textContent = reasonText;
    }
    if ($btnSave) {
      $btnSave.disabled = formLocked || !dirty;
    }
    const inputs = $tbody ? Array.from($tbody.querySelectorAll('.hi-input-price')) : [];
    inputs.forEach((input) => {
      input.disabled = formLocked;
    });
    if ($bukInput) {
      $bukInput.disabled = formLocked;
    }
  }

  function updateSyncLockState() {
    const templatePending = pendingTemplateReloadJobs.size;
    const locked = templatePending > 0 || changeStatusPending;
    let reason = '';
    if (templatePending > 0) {
      reason = `${templatePending} pekerjaan Template belum dimuat ulang setelah perubahan sumber.`;
    } else if (changeStatusPending) {
      reason = 'Template AHSP sedang disinkronkan. Tunggu hingga selesai sebelum mengubah harga.';
    }
    applyLockState(locked, reason);
  }

  updateSyncLockState();

  if (projectId && sourceChange) {
    window.addEventListener('dp:source-change', (event) => {
      const detail = event.detail || {};
      if (Number(detail.projectId) !== projectId) return;
      if (detail.state && detail.state.reload) {
        pendingTemplateReloadJobs = new Set(
          Object.keys(detail.state.reload)
            .map((key) => Number(key))
            .filter((id) => Number.isFinite(id)),
        );
        updateSyncLockState();
      }
    });
  }

  window.addEventListener('dp:change-status', (event) => {
    const detail = event.detail || {};
    if (Number(detail.projectId) !== projectId) return;
    if (detail.scope && detail.scope !== 'harga') return;
    if (typeof detail.hasChanges === 'undefined') return;
    changeStatusPending = !!detail.hasChanges;
    updateSyncLockState();
  });

  // ===== Helpers: numeric & format
  const toUI = (s)=> N ? N.formatForUI(N.enforceDp(s||'', DP)) : (s||'');
  // Locale-aware canonicalizer: prevents "100.000" (id-ID grouping) becoming 100.00
  function canonFromUI(raw, dp){
    const s0 = String(raw ?? '').trim();
    if (!s0) return '';
    const hasDot = s0.includes('.');
    const hasComma = s0.includes(',');
    if (hasDot && !hasComma){
      const dotGrouping = /^\d{1,3}(\.\d{3})+$/;
      if (dotGrouping.test(s0)){
        const noGroup = s0.replace(/\./g, '');
        return N ? (N.enforceDp(noGroup, dp) || '') : noGroup;
      }
    }
    if (hasComma && !hasDot){
      const commaGrouping = /^\d{1,3}(,\d{3})+$/;
      if (commaGrouping.test(s0)){
        const noGroup = s0.replace(/,/g, '');
        return N ? (N.enforceDp(noGroup, dp) || '') : noGroup;
      }
      const dec = s0.replace(/,/g, '.');
      const c = N ? N.canonicalizeForAPI(dec) : dec;
      return N ? (N.enforceDp(c || '', dp) || '') : (c || '');
    }
    const c = N ? N.canonicalizeForAPI(s0) : s0;
    return N ? (N.enforceDp(c || '', dp) || '') : (c || '');
  }
  const toCanon = (v)=> canonFromUI(v, DP);
  const toUI2 = (s)=> N ? N.formatForUI(N.enforceDp(s||'', 2)) : (s||'');
  const toCanon2 = (v)=> canonFromUI(v, 2);
  const toCanonFloat = (v, dp=6)=> canonFromUI(v, dp);
  const rupiah = (canon)=>{
    if (canon == null || canon === '') return '—';
    const n = Number(canon); if (!isFinite(n)) return '—';
    return fmtRp.format(n);
  };
  const decCountFromCanon = (canon)=>{
    const s = String(canon ?? '');
    if (!s) return 0;
    const i = s.lastIndexOf('.');
    return i === -1 ? 0 : (s.length - i - 1);
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

  // P0 FIX: Unsaved changes warning - prevent data loss on browser close/refresh
  window.addEventListener('beforeunload', (e) => {
    if (dirty) {
      const msg = 'Anda memiliki perubahan harga yang belum disimpan. Yakin ingin meninggalkan halaman?';
      e.preventDefault();
      e.returnValue = msg;
      return msg;
    }
  });

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

      // Profit/Margin
      if (j.meta && typeof j.meta.markup_percent !== 'undefined'){
        bukCanonLoaded = String(j.meta.markup_percent || '10.00');
        if ($bukInput) $bukInput.value = toUI2(bukCanonLoaded);
      }

      // P0 FIX: OPTIMISTIC LOCKING - Store timestamp when data is loaded
      if (j.meta && j.meta.project_updated_at) {
        projectUpdatedAt = j.meta.project_updated_at;
        console.log('[HARGA_ITEMS] Loaded timestamp:', projectUpdatedAt);
      }

      renderTable(rows);
      setDirty(false);  // Mark as clean after loading
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
      // simpan canon awal untuk deteksi edit/empty
      tr.dataset.origCanon = canonDisp;
      tr.dataset.manualEdited = '0';
      if (r.harga_canon === '' || r.harga_canon == null) {
        tr.classList.add('hi-row-empty');
        const inp = tr.querySelector('.hi-input-price');
        if (inp) inp.classList.add('vp-empty');
      } else {
        // Tandai nol sebagai perhatian (merah border kiri), tapi bukan invalid
        const isZero = (Number(canonDisp) === 0);
        if (isZero) tr.classList.add('hi-row-zero');
      }
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

  // ===== Input/Blur: validasi live + autofill 0
  function setRowDirtyVisual(tr, isDirty){
    if (!tr) return;
    tr.classList.toggle('hi-row-edited', !!isDirty);
    // Hindari background kuning Bootstrap di dark mode
    if (tr.classList.contains('table-warning')) tr.classList.remove('table-warning');
  }
  $tbody.addEventListener('input', (e)=>{
    const el = e.target;
    if (!(el instanceof HTMLInputElement) || !el.classList.contains('hi-input-price')) return;
    const tr = el.closest('tr');
    const canon = toCanon(el.value) || '';
    const num = Number(canon || 'NaN');
    const invalid = !isFinite(num) || num < 0 || num > MAX_PRICE;
    el.classList.toggle('ux-invalid', invalid);
    if (tr) tr.classList.toggle('hi-row-invalid', invalid);
    const prev = tr?.querySelector('.hi-price-preview');
    if (prev) prev.textContent = invalid ? '-' : rupiah(canon || '0.00');
    if (tr) tr.dataset.manualEdited = '1';
    // kosong? (harga asli null) -> hilangkan tanda empty saat user mengetik
    tr?.classList.remove('hi-row-empty');
    el.classList.remove('vp-empty');
    // nol? tandai/lepaskan sesuai nilai kanonik sekarang
    const isZero = (Number(canon) === 0);
    tr?.classList.toggle('hi-row-zero', isZero);
    // tandai dirty vs baseline
    const orig = tr?.dataset.origCanon || '';
    const isDirty = !!canon && canon !== orig;
    setRowDirtyVisual(tr, isDirty);

    // P0 FIX: Mark global dirty state when any input changes
    if (isDirty || $bukInput?.value !== toUI2(bukCanonLoaded)) {
      setDirty(true);
    }
  });

  // ===== Blur: normalisasi ke display format
  $tbody.addEventListener('blur', (e)=>{
    const el = e.target;
    if (!(el instanceof HTMLInputElement) || !el.classList.contains('hi-input-price')) return;

    let canon = toCanon(el.value);
    if (!canon) canon = '0.00'; // autofill 0
    const num = Number(canon);

    const invalid = !isFinite(num) || num < 0 || num > MAX_PRICE;
    el.value = toUI(canon);
    el.classList.toggle('ux-invalid', invalid);
    const tr = el.closest('tr');
    if (tr) tr.classList.toggle('hi-row-invalid', invalid);

    const prev = tr?.querySelector('.hi-price-preview');
    if (prev) prev.textContent = invalid ? '-' : rupiah(canon);
    if (tr){
      const orig = tr.dataset.origCanon || '';
      const isDirty = (orig && orig !== canon);
      tr.dataset.manualEdited = isDirty ? '1' : '0';
      setRowDirtyVisual(tr, isDirty);
      // Atur tanda nol setelah normalisasi
      tr.classList.toggle('hi-row-zero', Number(canon) === 0);
    }
  }, true);

  // ===== Profit/Margin: enforce 2dp pada blur
  // P0 FIX: Mark dirty when BUK/markup changes
  $bukInput?.addEventListener('input', ()=>{
    const canon = toCanon2($bukInput.value);
    if (canon && canon !== bukCanonLoaded) {
      setDirty(true);
    }
  });

  $bukInput?.addEventListener('blur', ()=>{
    const canon = toCanon2($bukInput.value);
    $bukInput.value = toUI2(canon || bukCanonLoaded);
  });

  // ===== SAVE
  $btnSave?.addEventListener('click', async ()=>{
    try{
      const payload = { items: [] };
      const mpCanon = toCanon2($bukInput?.value);

      // kumpulkan harga dengan validasi ketat (abort jika ada invalid)
      let invalidCount = 0;
      const idsSaving = [];
      viewRows.forEach(tr=>{
        const id = Number(tr.dataset.itemId);
        const input = tr.querySelector('.hi-input-price');
        if (!input) return;

        let canon = toCanon(input.value);
        if (!canon) canon = '0.00';
        const n = Number(canon);
        const invalid = !isFinite(n) || n < 0 || n > MAX_PRICE;
        input.classList.toggle('ux-invalid', invalid);
        if (invalid){ invalidCount++; return; }

        payload.items.push({ id, harga_satuan: canon });
        idsSaving.push({ id, canon });
      });

      if (invalidCount > 0){
        toast(`Terdapat ${invalidCount} input tidak valid. Perbaiki sebelum menyimpan.`, 'warning');
        return;
      }

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

      // P0 FIX: OPTIMISTIC LOCKING - Include timestamp in payload
      if (projectUpdatedAt) {
        payload.client_updated_at = projectUpdatedAt;
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

      // P0 FIX: OPTIMISTIC LOCKING - Handle conflict (409 status)
      if (!j.ok && j.conflict) {
        console.warn('[SAVE] Conflict detected - data modified by another user');

        const confirmMsg = (
          "⚠️ KONFLIK DATA TERDETEKSI!\n\n" +
          "Data harga telah diubah oleh pengguna lain sejak Anda membukanya.\n\n" +
          "Pilihan:\n" +
          "• OK = Muat Ulang (lihat perubahan terbaru, data Anda akan hilang)\n" +
          "• Cancel = Timpa (simpan data Anda, perubahan pengguna lain akan hilang)\n\n" +
          "⚠️ Timpa hanya jika Anda yakin perubahan Anda lebih penting!"
        );

        if (confirm(confirmMsg)) {
          // User chose to reload - refresh page
          console.log('[SAVE] User chose to reload');
          toast('🔄 Memuat ulang data terbaru...', 'info');
          setTimeout(() => window.location.reload(), 1000);
        } else {
          // User chose to force overwrite - retry without timestamp
          console.log('[SAVE] User chose to force overwrite');
          toast('⚠️ Menyimpan dengan mode timpa...', 'warning');

          const retryPayload = { ...payload };
          delete retryPayload.client_updated_at;

          const retryRes = await fetch(EP_SAVE, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
            credentials: 'same-origin',
            body: JSON.stringify(retryPayload)
          });
          const retryJ = await retryRes.json();

          if (retryJ.ok) {
            const userMsg = retryJ.user_message || '✅ Data berhasil disimpan (mode timpa)';
            toast(userMsg, 'success');
            setDirty(false);

            // Update stored timestamp
            if (retryJ.project_updated_at) {
              projectUpdatedAt = retryJ.project_updated_at;
            }

            // Visual feedback
            idsSaving.forEach(({id, canon})=>{
              const tr = $tbody.querySelector(`tr[data-item-id="${id}"]`);
              if (!tr) return;
              tr.classList.add('hi-row-saved');
              setTimeout(()=> tr.classList.remove('hi-row-saved'), 1200);
              tr.classList.remove('hi-row-empty');
              tr.classList.toggle('hi-row-zero', Number(canon) === 0);
              setRowDirtyVisual(tr, false);
              tr.dataset.origCanon = canon;
              const input = tr.querySelector('.hi-input-price');
              input?.classList.remove('ux-invalid');
            });

            setTimeout(()=> fetchList(), 900);
          } else {
            const errMsg = retryJ.user_message || 'Gagal menyimpan data.';
            toast(errMsg, 'error');
            console.error('[SAVE] Retry failed:', retryJ.errors);
          }
        }
        return; // Exit early - conflict handled
      }

      // P0 FIX: Use user_message from server
      if (!res.ok || !j.ok){
        const userMsg = j.user_message || 'Sebagian gagal disimpan. Silakan coba lagi.';
        toast(userMsg, 'warning');
        console.warn('[SAVE] Errors:', j.errors || []);
        fetchList(); // segarkan untuk sinkron
      } else {
        const userMsg = j.user_message || `✅ Berhasil menyimpan ${j.updated ?? payload.items.length} item.`;
        toast(userMsg, 'success');
        setDirty(false);  // Mark as clean after successful save

        // P0 FIX: Update stored timestamp after successful save
        if (j.project_updated_at) {
          projectUpdatedAt = j.project_updated_at;
          console.log('[SAVE] Updated timestamp:', projectUpdatedAt);
        }

        // Tandai baris-baris yang tersimpan dan bersihkan status dirty/empty
        idsSaving.forEach(({id, canon})=>{
          const tr = $tbody.querySelector(`tr[data-item-id="${id}"]`);
          if (!tr) return;
          tr.classList.add('hi-row-saved');
          setTimeout(()=> tr.classList.remove('hi-row-saved'), 1200);
          tr.classList.remove('hi-row-empty');
          tr.classList.toggle('hi-row-zero', Number(canon) === 0);
          setRowDirtyVisual(tr, false);
          tr.dataset.origCanon = canon;
          const input = tr.querySelector('.hi-input-price');
          input?.classList.remove('ux-invalid');
        });
        // Tunda refresh agar highlight terlihat
        setTimeout(()=> fetchList(), 900);
      }
    }catch(e){
      console.error(e);
      toast('❌ Gagal menyimpan. Periksa koneksi internet Anda.', 'error');
      fetchList();
    }finally{
      const spin = document.getElementById('hi-save-spin');
      $btnSave.disabled = false; spin?.setAttribute('hidden','');
      // fetchList dipanggil pada cabang di atas
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
    const rowsPaste = text.trim().split(/\r?\n/).map(line => line.split(/\t|;/));
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
      if (prof.factor_to_base) $convFactor.value = (N ? N.formatForUI(N.enforceDp(prof.factor_to_base, 6)) : (prof.factor_to_base||''));
      if (prof.capacity_m3){ $convCapM3Wrap.classList.remove('d-none'); $convCapM3.value = (N ? N.formatForUI(N.enforceDp(prof.capacity_m3, 6)) : (prof.capacity_m3||'')); }
      if (prof.capacity_ton){ $convCapTonWrap.classList.remove('d-none'); $convCapTon.value = (N ? N.formatForUI(N.enforceDp(prof.capacity_ton, 6)) : (prof.capacity_ton||'')); }
      if (prof.density){ $convDensityWrap.classList.remove('d-none'); $convDensity.value = (N ? N.formatForUI(N.enforceDp(prof.density, 6)) : (prof.density||'')); }
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
    // Jika user sudah edit manual dan nilai akan berbeda, minta konfirmasi
    if (convCtx.tr){
      const wasManual = convCtx.tr.dataset.manualEdited === '1';
      const curCanon = toCanon(input?.value);
      if (wasManual && curCanon && curCanon !== canon){
        const ok = window.confirm('Nilai harga pada baris ini telah diisi manual. Terapkan hasil konversi akan mengganti nilai tersebut. Lanjutkan?');
        if (!ok) return;
      }
    }
    if (input){ input.value = toUI(canon); input.classList.remove('ux-invalid'); }
    if (prev){ prev.textContent = rupiah(canon); }
    // Tampilkan indikator edited (kuning) untuk hasil konversi juga
    if (convCtx.tr){
      convCtx.tr.classList.remove('hi-row-empty');
      convCtx.tr.classList.toggle('hi-row-zero', Number(canon) === 0);
      const orig = convCtx.tr.dataset.origCanon || '';
      const isDirty = (orig && orig !== canon);
      setRowDirtyVisual(convCtx.tr, isDirty);
    }

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
    // Tandai baris sebagai tidak manual (diganti hasil konversi)
    if (convCtx.tr){ convCtx.tr.dataset.manualEdited = '0'; }
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
      $convFactor.value = N ? N.formatForUI(N.enforceDp(factor,6)) : factor;
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

  // ===== Init
  fetchList();

  // ===== Export buttons already initialized in initUnifiedExport() IIFE above =====
  // (Removed duplicate initExportButtons function - it was causing projectId undefined error)

})();
