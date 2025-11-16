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

  // P1 FIX: Cache TTL to prevent stale data
  const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes - balance between performance and freshness

  let activeJobId = null;
  let activeSource = null;     // 'ref' | 'ref_modified' | 'custom'
  let readOnly = false;
  let dirty = false;
  let kategoriMeta = [];       // [{code,label}]
  const rowsByJob = {};        // { jobId: [{kategori,kode,uraian,satuan,koefisien}] }
  const projectId = Number(app.dataset.projectId);
  const sourceChange = window.DP?.sourceChange || null;
  const bannerEl = $('#ta-sync-banner');
  const bannerTextEl = $('#ta-sync-banner-text');
  const bannerReloadBtn = $('#ta-banner-reload');
  const editorBlocker = $('#ta-editor-blocker');
  const editorReloadBtn = $('#ta-editor-reload');
  const conflictModalEl = $('#taConflictModal');
  const conflictModal = (conflictModalEl && window.bootstrap && window.bootstrap.Modal)
    ? new bootstrap.Modal(conflictModalEl, { backdrop: 'static', keyboard: false })
    : null;
  const CONFLICT_MESSAGE = [
    'KONFLIK DATA TERDETEKSI!',
    'Data pekerjaan ini telah diubah oleh pengguna lain sejak Anda membukanya.',
    'Pilih tindakan: Muat ulang data terbaru atau timpa perubahan terbaru mereka.'
  ].join('\n\n');
  let pendingReloadJobs = new Set(
    sourceChange && projectId ? sourceChange.listReloadJobs(projectId) : [],
  );
  let changeStatusPending = false;
  let reloadInFlight = false;
  let reloadQueue = Promise.resolve();

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
  // P2.1 FIX: Auto-format + constraint validation on blur
  document.addEventListener('blur', (e)=>{
    const el = e.target;
    if (!(el instanceof HTMLInputElement)) return;
    if (!el.classList.contains('num')) return;
    if (el.dataset.field !== 'koefisien') return;

    const canon = __koefToCanon(el.value);
    const num = parseFloat(canon);

    // Constraint validation (matches P1.1 validation)
    const MIN_KOEF = 0.000001;
    const MAX_KOEF = 999999.999999;

    if (isNaN(num) || num < MIN_KOEF) {
      toast(`⚠️ Koefisien harus ≥ ${MIN_KOEF} (positif)`, 'warning');
      el.value = __koefToUI('1.000000'); // Reset to default
      setDirty(true);
    } else if (num > MAX_KOEF) {
      toast(`⚠️ Koefisien maksimal ${MAX_KOEF}`, 'warning');
      el.value = __koefToUI(String(MAX_KOEF)); // Cap to max
      setDirty(true);
    } else {
      el.value = __koefToUI(canon); // Format normally
    }
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
          const rk = $('input[data-field="ref_kind"]', tr).value.trim();
          const rid = $('input[data-field="ref_id"]', tr).value.trim();
          if (rk && rid) { base.ref_kind = rk; base.ref_id = rid; }
          else {
            const refId = $('input[data-field="ref_ahsp_id"]', tr).value.trim();
            if (refId) base.ref_ahsp_id = refId;
          }
        }
        out.push(base);
      });
    });
    return out;
  }

  // P1.1 FIX: Strengthened client validation
  function validateClient(rows) {
    const errors = [];
    const seen = new Set();
    const MAX_URAIAN_LEN = 500;
    const MAX_KODE_LEN = 100;
    const MAX_SATUAN_LEN = 50;
    const MIN_KOEF = 0.000001;  // Based on user: positive only
    const MAX_KOEF = 999999.999999;

    rows.forEach((r, i) => {
      // Uraian validation
      if (!r.uraian || !r.uraian.trim()) {
        errors.push({path:`rows[${i}].uraian`, message:'Uraian wajib diisi'});
      } else if (r.uraian.length > MAX_URAIAN_LEN) {
        errors.push({path:`rows[${i}].uraian`, message:`Maksimal ${MAX_URAIAN_LEN} karakter`});
      }

      // Kode validation
      if (!r.kode || !r.kode.trim()) {
        errors.push({path:`rows[${i}].kode`, message:'Kode wajib diisi'});
      } else {
        if (r.kode.length > MAX_KODE_LEN) {
          errors.push({path:`rows[${i}].kode`, message:`Maksimal ${MAX_KODE_LEN} karakter`});
        }
        // Check duplicate
        const key = r.kode.trim();
        if (seen.has(key)) {
          errors.push({path:`rows[${i}].kode`, message:'Kode duplikat'});
        }
        seen.add(key);
      }

      // Satuan validation
      if (!r.satuan || !r.satuan.trim()) {
        errors.push({path:`rows[${i}].satuan`, message:'Satuan wajib diisi'});
      } else if (r.satuan.length > MAX_SATUAN_LEN) {
        errors.push({path:`rows[${i}].satuan`, message:`Maksimal ${MAX_SATUAN_LEN} karakter`});
      }

      // Koefisien validation - enhanced numeric check
      if (r.koefisien === '' || r.koefisien == null) {
        errors.push({path:`rows[${i}].koefisien`, message:'Koefisien wajib diisi'});
      } else {
        const koefStr = String(r.koefisien).trim();
        const koefNum = parseFloat(__koefToCanon(koefStr));

        if (isNaN(koefNum)) {
          errors.push({path:`rows[${i}].koefisien`, message:'Koefisien harus berupa angka'});
        } else if (koefNum < MIN_KOEF) {
          errors.push({path:`rows[${i}].koefisien`, message:`Koefisien minimal ${MIN_KOEF} (harus positif)`});
        } else if (koefNum > MAX_KOEF) {
          errors.push({path:`rows[${i}].koefisien`, message:`Koefisien maksimal ${MAX_KOEF}`});
        }
      }

      // Kategori validation
      if (!r.kategori || !['TK', 'BHN', 'ALT', 'LAIN'].includes(r.kategori)) {
        errors.push({path:`rows[${i}].kategori`, message:'Kategori tidak valid'});
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

    // CACHE FIX: Enable reload button whenever a job is active
    const reloadBtnEl = $('#ta-btn-reload');
    if (reloadBtnEl) {
      reloadBtnEl.disabled = !activeJobId; // Enable if job selected
    }

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

      function localProjectOptions(term) {
        const q = String(term || '').toLowerCase();
        const items = [];
        document.querySelectorAll('#ta-job-list .ta-job-item').forEach(li => {
          const id = parseInt(li.getAttribute('data-pekerjaan-id')||'0',10);
          const kode = (li.querySelector('.kode')?.textContent || '').trim();
          const uraian = (li.querySelector('.uraian')?.textContent || '').trim();
          const satuan = (li.querySelector('.satuan')?.textContent || '').trim();
          if (!id) return;
          const hay = `${kode} ${uraian}`.toLowerCase();
          if (q && !hay.includes(q)) return;
          const badge = (li.getAttribute('data-source-type')||'').toUpperCase();
          items.push({
            id: `job:${id}`,
            text: `[${badge||'JOB'}] ${kode} — ${uraian}`,
            kode_job: kode,
            nama_job: uraian,
            satuan: satuan || ''
          });
        });
        return items.slice(0, 20);
      }

      $input.select2({
        ajax: {
          url: endpoints.searchAhsp,
          delay: 250,
          data: params => ({ q: params.term }),
          processResults: (data, params) => {
            const remote = (data.results || []).map(x => ({
              id: `ahsp:${x.id}`,
              text: `${x.kode_ahsp} — ${x.nama_ahsp}`,
              kode_ahsp: x.kode_ahsp,
              nama_ahsp: x.nama_ahsp,
              satuan: x.satuan || ''
            }));
            const local = localProjectOptions(params?.term);
            const groups = [];
            if (local.length) groups.push({ text: 'Pekerjaan Proyek', children: local });
            if (remote.length) groups.push({ text: 'Master AHSP', children: remote });
            return { results: groups.length ? groups : [] };
          }
        },
        minimumInputLength: 1,
        width: 'resolve',
        placeholder: 'Cari AHSP atau Pekerjaan…',
        dropdownAutoWidth: true
      });

      $input.on('select2:select', async (e) => {
        const d = e.params.data || {};
        let kind = 'ahsp';
        let refId = '';
        let kode = '';
        let nama = '';
        let sat  = d.satuan || '';
        const sid = String(d.id||'');
        if (sid.startsWith('job:')) {
          kind = 'job';
          refId = sid.split(':')[1] || '';
          kode = d.kode_job || '';
          nama = d.nama_job || '';
        } else {
          kind = 'ahsp';
          refId = sid.split(':')[1] || sid;
          kode = d.kode_ahsp || '';
          nama = d.nama_ahsp || '';
        }

        // P1.2 FIX: Add loading state during bundle validation
        if (kind === 'job' && refId) {
          // Show loading toast
          const loadingMsg = `🔍 Memeriksa bundle "${kode}"...`;
          toast(loadingMsg, 'info', 0); // No auto-dismiss during loading

          try {
            // Fetch job details to validate it has components with timeout
            const validateUrl = urlFor(endpoints.get, parseInt(refId));
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 5000); // 5 sec timeout

            const resp = await fetch(validateUrl, {
              credentials:'same-origin',
              signal: controller.signal
            });
            clearTimeout(timeoutId);

            const data = await resp.json();

            if (data.ok && (!data.items || data.items.length === 0)) {
              // Bundle is empty - show warning and prevent selection
              toast(`⚠️ Bundle Kosong: "${nama}" belum memiliki komponen AHSP.\n\nSilakan isi detail AHSP untuk pekerjaan tersebut terlebih dahulu sebelum menggunakan sebagai bundle.`, 'warning', 5000);
              console.warn('[BUNDLE_VALIDATION] Empty bundle detected:', kode, nama);

              // Clear the selection
              $input.val(null).trigger('change');
              return; // Don't proceed with selection
            }

            console.log('[BUNDLE_VALIDATION] Bundle valid:', kode, 'has', data.items?.length || 0, 'components');
            toast(`✅ Bundle "${kode}" valid (${data.items?.length || 0} komponen)`, 'success', 2000);

          } catch (err) {
            if (err.name === 'AbortError') {
              console.error('[BUNDLE_VALIDATION] Timeout validating bundle:', kode);
              toast('⏱️ Timeout saat validasi bundle. Lanjutkan dengan hati-hati.', 'warning', 4000);
            } else {
              console.error('[BUNDLE_VALIDATION] Error validating bundle:', err);
              toast('⚠️ Tidak dapat validasi bundle. Lanjutkan dengan hati-hati.', 'warning', 4000);
            }
            // Don't block - let backend handle validation
          }
        }

        // AHSP bundles are now supported! Backend will expand them recursively

        input.value = kode;
        $('.cell-wrap', tr).textContent = nama;
        $('input[data-field="satuan"]', tr).value = sat;
        $('input[data-field="ref_kind"]', tr).value = kind;
        $('input[data-field="ref_id"]', tr).value = String(refId || '');
        $('input[data-field="ref_ahsp_id"]', tr).value = (kind === 'ahsp' ? String(refId||'') : '');
        // FIX: Set default koefisien = 1 jika kosong (prevent validation error)
        const koefInput = $('input[data-field="koefisien"]', tr);
        if (!koefInput.value.trim()) {
          koefInput.value = __koefToUI('1.000000');
        }
        const kodeTd = input.closest('td');
        if (kodeTd && !kodeTd.querySelector('.tag-bundle')) {
          kodeTd.insertAdjacentHTML('beforeend', ' <span class="tag-bundle">Bundle</span>');
        }
        setDirty(true);
      });

      // Edit manual kode → kosongkan ref id
      input.addEventListener('input', () => {
        $('input[data-field="ref_ahsp_id"]', tr).value = '';
        $('input[data-field="ref_kind"]', tr).value = '';
        $('input[data-field="ref_id"]', tr).value = '';
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

    // P0.1 FIX: Promise-based auto-save - no more race condition!
    if (dirty && activeJobId) {
      const currentJobEl = $(`.ta-job-item[data-pekerjaan-id="${activeJobId}"]`);
      const currentKode = currentJobEl?.querySelector('.kode')?.textContent?.trim() || 'pekerjaan ini';
      const targetKode = li.querySelector('.kode')?.textContent?.trim() || 'pekerjaan lain';

      const confirmMsg = `⚠️ PERUBAHAN BELUM TERSIMPAN!\n\nAnda memiliki perubahan yang belum disimpan pada "${currentKode}".\n\nPilih tindakan:\n• OK = Simpan dulu, lalu pindah ke "${targetKode}"\n• Cancel = Tetap di "${currentKode}"`;

      if (!confirm(confirmMsg)) {
        console.log('[SELECT_JOB] User cancelled job switch due to unsaved changes');
        return; // Stay on current job
      }

      // User chose to save first - use Promise to wait for completion
      console.log('[SELECT_JOB] Auto-saving before job switch...');
      toast('💾 Menyimpan perubahan...', 'info', 2000);

      doSave(activeJobId).then(() => {
        console.log('[SELECT_JOB] Save completed successfully, switching job...');
        toast('✅ Tersimpan! Beralih ke pekerjaan lain...', 'success', 1500);
        // Wait a bit for user to see success message
        setTimeout(() => selectJobInternal(li, id), 500);
      }).catch((err) => {
        console.error('[SELECT_JOB] Save failed:', err);
        toast('❌ Gagal menyimpan. Tetap di pekerjaan ini.', 'error');
        // Stay on current job if save fails
      });
      return;
    }

    // P2 FIX: Auto-reload stale jobs silently in background
    // No more invasive blocker - just seamless refresh
    const requiresReload = jobNeedsReload(id);
    if (requiresReload) {
      console.log('[SELECT_JOB] Job requires reload - auto-reloading silently');
      toast('🔄 Memuat data terbaru...', 'info', 2000);
    }

    // Proceed with job selection - forceRefresh will be handled by selectJobInternal
    selectJobInternal(li, id, requiresReload);
  }

  // Internal function to actually perform job selection (without checks)
  // forceRefresh: if true, bypass cache and fetch fresh data from server
  function selectJobInternal(li, id, forceRefresh = false) {
    activeJobId = id;
    activeSource = li.dataset.sourceType;
    $$('.ta-job-item').forEach(n => n.classList.toggle('is-active', n === li));
    $('#ta-active-kode').textContent = $('.kode', li)?.textContent?.trim() || '—';
    $('#ta-active-uraian').textContent = $('.uraian', li)?.textContent?.trim() || '—';
    $('#ta-active-satuan').textContent = $('.satuan', li)?.textContent?.trim() || '—';
    $('#ta-active-source').innerHTML = `<span class="badge">${activeSource}</span>`;
    setDirty(false);
    const flaggedBefore = jobNeedsReload(id);
    const requiresReload = forceRefresh || flaggedBefore;
    const hasCache = !!rowsByJob[id];

    // P1 FIX: Check cache expiry - prevent stale data
    const cache = rowsByJob[id];
    const cacheExpired = cache && cache.cachedAt
      ? (Date.now() - cache.cachedAt > CACHE_TTL_MS)
      : false;

    if (cacheExpired) {
      console.log('[CACHE] Cache expired for job', id, '- age:', Math.round((Date.now() - cache.cachedAt) / 1000), 'seconds');
    }

    const needsFetch = requiresReload || !hasCache || cacheExpired;

    // Use cache only when fresh and no reload requested
    if (!needsFetch && hasCache) {
      console.log('[CACHE] Using fresh cache for job', id, '- age:', Math.round((Date.now() - cache.cachedAt) / 1000), 'seconds');
      paint(rowsByJob[id].items);
      kategoriMeta = rowsByJob[id].kategoriMeta || kategoriMeta;
      readOnly = rowsByJob[id].readOnly || false;
      setEditorModeBySource();
      toggleEditorBlocker(false);
      return Promise.resolve();
    }

    // P2 FIX: Show loading placeholder, but NO invasive blocker
    if (!hasCache || requiresReload) {
      showLoadingPlaceholder();
    }

    // fetch
    const url = urlFor(endpoints.get, id);
    return fetch(url, {credentials:'same-origin'}).then(r => r.json()).then(js => {
      if (!js.ok) throw new Error('Gagal memuat');
      const items = js.items || [];
      kategoriMeta = js.meta?.kategori_opts || kategoriMeta;
      readOnly = !!js.meta?.read_only;

      // OPTIMISTIC LOCKING: Store timestamp when data is loaded
      const updatedAt = js.pekerjaan?.updated_at || null;

      // P1 FIX: Store cache timestamp for TTL check
      rowsByJob[id] = {
        items,
        kategoriMeta,
        readOnly,
        updatedAt,
        cachedAt: Date.now() // Track when cache was created
      };
      paint(items);
      setEditorModeBySource();
      if (flaggedBefore) {
        resolveReloadJob(id);
      }
    }).catch((err) => {
      // P2.2 FIX: Offer retry on network error
      console.error('[LOAD] Fetch failed:', err);
      const retry = confirm('❌ Gagal memuat data pekerjaan.\n\nCoba lagi?');
      if (retry) {
        console.log('[LOAD] User requested retry');
        return selectJobInternal(li, id, true); // Force refresh retry
      }
      toast('Gagal memuat detail. Silakan coba lagi.', 'error');
      throw err;
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

  function showLoadingPlaceholder() {
    ['TK','BHN','ALT','LAIN'].forEach((seg) => {
      const body = $(`#seg-${seg}-body`);
      if (!body) return;
      body.innerHTML = `<tr class="ta-empty"><td colspan="5">Memuat data...</td></tr>`;
    });
  }

  function jobNeedsReload(id) {
    return pendingReloadJobs.has(Number(id));
  }

  function syncPendingState(state) {
    if (!state || !state.reload) {
      pendingReloadJobs = new Set();
      return;
    }
    pendingReloadJobs = new Set(
      Object.keys(state.reload).map((key) => Number(key)).filter((id) => Number.isFinite(id)),
    );
  }

  function updateJobBadges() {
    const items = $$('#ta-job-list .ta-job-item');
    items.forEach((li) => {
      const id = Number(li.dataset.pekerjaanId);
      const needsReload = jobNeedsReload(id);
      li.classList.toggle('ta-job-item--stale', needsReload);
      const meta = li.querySelector('.meta');
      if (!meta) return;
      let pill = meta.querySelector('.ta-job-pill');
      if (needsReload) {
        if (!pill) {
          pill = document.createElement('span');
          pill.className = 'ta-job-pill';
          pill.textContent = 'Perlu reload';
          meta.appendChild(pill);
        }
      } else if (pill) {
        pill.remove();
      }
    });
  }

  function updateBanner() {
    if (!bannerEl) return;
    const pendingCount = pendingReloadJobs.size;
    const shouldShow = pendingCount > 0 || changeStatusPending;
    bannerEl.classList.toggle('d-none', !shouldShow);
    if (!shouldShow) return;

    // P2 FIX: Friendlier banner messages - emphasize auto-reload
    const messages = [];
    if (pendingCount > 0) {
      messages.push(`${pendingCount} pekerjaan memiliki pembaruan. Data akan dimuat otomatis saat dibuka.`);
    }
    if (changeStatusPending) {
      messages.push('Ada perubahan terbaru pada Template AHSP.');
    }
    if (bannerTextEl) {
      bannerTextEl.textContent = messages.join(' ');
    }
  }

  function toggleEditorBlocker(show) {
    // P2 FIX: Blocker disabled - auto-reload is seamless now
    // Keep function for backward compatibility but don't actually block
    if (!editorBlocker) return;
    // Always keep it hidden
    editorBlocker.classList.add('d-none');
    console.log('[BLOCKER] Blocker toggle disabled - seamless reload enabled');
  }

  function setReloadButtonsState(isLoading) {
    [bannerReloadBtn, editorReloadBtn].forEach((btn) => {
      if (!btn) return;
      btn.classList.toggle('is-loading', !!isLoading);
      if (isLoading) {
        btn.setAttribute('disabled', 'disabled');
      } else {
        btn.removeAttribute('disabled');
      }
    });
  }

  function resolveReloadJob(jobId) {
    if (!jobNeedsReload(jobId)) return;
    pendingReloadJobs.delete(Number(jobId));
    try {
      sourceChange?.markReloaded(projectId, [jobId]);
    } catch (err) {
      console.warn('[TA] Failed to mark reload job resolved', err);
    }
    updateJobBadges();
    updateBanner();
    // P2 FIX: No more blocker toggle - auto-reload is seamless
  }

  async function reloadJobs(jobIds, options = {}) {
    const rawIds = Array.isArray(jobIds) ? jobIds : [];
    const uniqueIds = Array.from(new Set(rawIds.map((id) => Number(id)))).filter((id) => Number.isFinite(id));
    const isSilent = !!options.silent;
    const queueMode = !!options.queue || isSilent;
    if (!uniqueIds.length) {
      if (!isSilent) {
        toast('Tidak ada pekerjaan yang dipilih untuk dimuat ulang.', 'info');
      }
      return Promise.resolve();
    }
    if (reloadInFlight && !queueMode) {
      if (!isSilent) {
        toast('Proses muat ulang masih berjalan. Tunggu sebentar.', 'info');
      }
      return Promise.resolve();
    }

    const run = async () => {
      reloadInFlight = true;
      const manageButtons = !isSilent;
      if (manageButtons) {
        setReloadButtonsState(true);
      }
      const preserveSelection = options?.preserveSelection !== false;
      const originalJobId = preserveSelection ? activeJobId : null;
      const originalJobEl = originalJobId ? $(`.ta-job-item[data-pekerjaan-id="${originalJobId}"]`) : null;
      let successCount = 0;
      let failure = null;
      try {
        for (const id of uniqueIds) {
          const li = $(`.ta-job-item[data-pekerjaan-id="${id}"]`);
          if (!li) {
            console.warn('[TA] Tidak menemukan elemen pekerjaan untuk reload massal', id);
            continue;
          }
          try {
            await selectJobInternal(li, id, true);
            successCount += 1;
          } catch (err) {
            failure = err;
            break;
          }
        }
      } finally {
        reloadInFlight = false;
        if (manageButtons) {
          setReloadButtonsState(false);
        }
      }

      if (preserveSelection && originalJobEl && activeJobId !== originalJobId) {
        await selectJobInternal(originalJobEl, originalJobId, jobNeedsReload(originalJobId));
      }

      if (failure) {
        console.error('[TA] Reload jobs halted', failure);
        toast('Sebagian pekerjaan gagal dimuat ulang. Coba lagi.', 'error');
        throw failure;
      }
      if (!successCount) {
        if (!isSilent) {
          toast('Tidak ada pekerjaan yang perlu dimuat ulang.', 'info');
        }
        return;
      }
      if (!isSilent) {
        const msg = successCount === 1
          ? 'Pekerjaan berhasil dimuat ulang.'
          : `${successCount} pekerjaan berhasil dimuat ulang.`;
        toast(msg, 'success');
      }
    };

    if (queueMode) {
      const nextTask = reloadQueue.catch(() => {}).then(() => run());
      reloadQueue = nextTask.catch(() => {});
      return nextTask;
    }
    return run();
  }

  function forceReloadActiveJob() {
    if (!activeJobId) {
      toast('Pilih pekerjaan yang ingin dimuat ulang.', 'warning');
      return Promise.resolve();
    }
    const currentJobEl = $(`.ta-job-item[data-pekerjaan-id="${activeJobId}"]`);
    if (!currentJobEl) {
      toast('Pekerjaan tidak ditemukan.', 'error');
      return Promise.resolve();
    }
    return reloadJobs([activeJobId], { preserveSelection: true });
  }

  function promptConflictResolution() {
    if (!conflictModal) {
      const fallback = window.confirm(CONFLICT_MESSAGE);
      return Promise.resolve(fallback ? 'reload' : 'overwrite');
    }
    return new Promise((resolve) => {
      let resolved = false;
      const handleClick = (event) => {
        const btn = event.target.closest('[data-choice]');
        if (!btn) return;
        event.preventDefault();
        resolved = true;
        const choice = btn.getAttribute('data-choice') === 'overwrite' ? 'overwrite' : 'reload';
        conflictModalEl.removeEventListener('click', handleClick);
        conflictModalEl.removeEventListener('hidden.bs.modal', handleHidden);
        conflictModal.hide();
        resolve(choice);
      };
      const handleHidden = () => {
        conflictModalEl.removeEventListener('click', handleClick);
        conflictModalEl.removeEventListener('hidden.bs.modal', handleHidden);
        if (!resolved) {
          resolve('reload');
        }
      };
      conflictModalEl.addEventListener('click', handleClick);
      conflictModalEl.addEventListener('hidden.bs.modal', handleHidden);
      conflictModal.show();
    });
  }

  function updateStats() {
    const n = $$('.ta-row').length;
    $('#ta-row-stats').textContent = `${n} baris`;
  }

  updateJobBadges();
  updateBanner();

  // ---------- EVENTS ----------
  // pilih pekerjaan
  $$('#ta-job-list .ta-job-item').forEach(li => {
    li.addEventListener('click', () => selectJob(li));
    li.addEventListener('keydown', (e) => { if (e.key==='Enter' || e.key===' ') { e.preventDefault(); selectJob(li);} });
  });

  if (projectId && sourceChange) {
    window.addEventListener('dp:source-change', (event) => {
      const detail = event.detail || {};
      if (Number(detail.projectId) !== projectId) return;
      if (detail.state) {
        syncPendingState(detail.state);
        updateJobBadges();
        updateBanner();
      }
    });
  }

  if (projectId) {
    window.addEventListener('dp:change-status', (event) => {
      const detail = event.detail || {};
      if (Number(detail.projectId) !== projectId) return;
      if (detail.scope && detail.scope !== 'template') return;
      if (typeof detail.hasChanges === 'undefined') return;
      changeStatusPending = !!detail.hasChanges;
      updateBanner();
    });
  }

  bannerReloadBtn?.addEventListener('click', (event) => {
    event.preventDefault();
    if (!pendingReloadJobs.size) {
      toast('Semua pekerjaan sudah terbaru.', 'info');
      return;
    }
    reloadJobs(Array.from(pendingReloadJobs), { preserveSelection: !!activeJobId }).catch(() => {});
  });
  editorReloadBtn?.addEventListener('click', (event) => {
    event.preventDefault();
    forceReloadActiveJob().catch(() => {});
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
      // FIX: Set default koefisien = 1 untuk row baru (prevent validation error)
      const koefInput = $('input[data-field="koefisien"]', tr);
      if (koefInput) koefInput.value = __koefToUI('1.000000');
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

  // P0.1: Refactor save logic into reusable function
  async function doSave(jobId) {
    if (!jobId) return Promise.reject(new Error('No job selected'));

    const rows = gatherRows();
    const errs = validateClient(rows);
    if (errs.length) {
      const firstErr = errs[0];
      const errMsg = `Periksa isian: ${firstErr.path} - ${firstErr.message}`;
      toast(errMsg, 'warn');
      console.warn('Validation errors:', errs);
      return Promise.reject(new Error('Validation failed'));
    }

    const rowsCanon = rows.map(r => ({ ...r, koefisien: __koefToCanon(r.koefisien) }));
    const url = urlFor(endpoints.save, jobId);

    // P0.2 FIX: Freshness check before save to prevent stale cache conflict
    const currentCache = rowsByJob[jobId];
    if (currentCache && currentCache.updatedAt) {
      console.log('[SAVE] Checking cache freshness before save...');
      try {
        const freshCheckUrl = urlFor(endpoints.get, jobId);
        const freshResp = await fetch(freshCheckUrl, {credentials:'same-origin', timeout: 5000});
        const freshData = await freshResp.json();

        if (freshData.ok && freshData.pekerjaan?.updated_at) {
          if (freshData.pekerjaan.updated_at !== currentCache.updatedAt) {
            console.warn('[SAVE] Data changed since cache loaded!', {
              cached: currentCache.updatedAt,
              fresh: freshData.pekerjaan.updated_at
            });
            toast('⚠️ Data telah diubah sejak terakhir dimuat. Muat ulang dulu!', 'warning', 5000);

            // Offer to reload
            const reload = confirm('Data pekerjaan ini telah diubah oleh user lain.\n\nMuat ulang data terbaru? (perubahan Anda akan hilang)');
            if (reload) {
              const jobEl = $(`.ta-job-item[data-pekerjaan-id="${jobId}"]`);
              if (jobEl) selectJobInternal(jobEl, jobId, true); // Force refresh
            }
            return Promise.reject(new Error('Stale cache - data changed'));
          }
          console.log('[SAVE] Cache is fresh - proceeding with save');
        }
      } catch (err) {
        console.warn('[SAVE] Freshness check failed - proceeding anyway:', err);
        // Don't block save if check fails (network issue etc)
      }
    }

    // OPTIMISTIC LOCKING: Include timestamp from when data was loaded
    const clientUpdatedAt = currentCache?.updatedAt || null;
    const payload = {
      rows: rowsCanon,
      client_updated_at: clientUpdatedAt
    };

    const btnSave = $('#ta-btn-save');
    const spin = $('#ta-btn-save-spin');
    if (spin) spin.hidden = false;
    if (btnSave) btnSave.disabled = true;

    return fetch(url, {
      method:'POST',
      credentials:'same-origin',
      headers:{ 'Content-Type':'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify(payload)
    }).then(r => {
      // DEBUG: Log response status
      console.log('[SAVE] HTTP Status:', r.status);
      if (!r.ok) {
        console.error('[SAVE] HTTP Error:', r.status, r.statusText);
      }
      return r.json();
    }).then(js => {
      // DEBUG: Log full response
      console.log('[SAVE] Response:', js);

      // OPTIMISTIC LOCKING: Handle conflict (409 status)
      if (!js.ok && js.conflict) {
        console.warn('[SAVE] Conflict detected - data modified by another user');
        return promptConflictResolution().then((choice) => {
          if (choice === 'overwrite') {
            console.log('[SAVE] Force overwrite selected');
            toast('Menimpa perubahan terbaru...', 'warning');
            const retryPayload = { rows: rowsCanon };
            return fetch(url, {
              method: 'POST',
              credentials: 'same-origin',
              headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
              body: JSON.stringify(retryPayload),
            }).then((retryRes) => retryRes.json()).then((retryJs) => {
              if (retryJs.ok) {
                toast('Data berhasil disimpan (mode timpa)', 'success');
                setDirty(false);
                if (retryJs.pekerjaan?.updated_at) {
                  rowsByJob[activeJobId] = rowsByJob[activeJobId] || {};
                  rowsByJob[activeJobId].updatedAt = retryJs.pekerjaan.updated_at;
                }
              } else {
                const errMsg = retryJs.user_message || 'Gagal menyimpan data. Silakan coba lagi.';
                toast(errMsg, 'error');
              }
            }).catch((err) => {
              console.error('[SAVE] Retry failed:', err);
              toast('Gagal menyimpan. Periksa koneksi internet Anda.', 'error');
            });
          }
          console.log('[SAVE] Reload selected to resolve conflict');
          toast('Memuat ulang data terbaru...', 'info');
          setTimeout(() => window.location.reload(), 1000);
          return null;
        });
      }


      // IMPROVED: Use user_message from server for better UX
      if (!js.ok) {
        // Server returned error with user-friendly message
        const userMsg = js.user_message || 'Gagal menyimpan data. Silakan coba lagi.';
        toast(userMsg, 'error');
        console.error('[SAVE] Server errors:', js.errors || []);
        return; // Don't throw, just return
      }

      // Partial success (status 207) - some errors but data saved
      if (js.errors && js.errors.length > 0) {
        let userMsg = js.user_message || `⚠️ Data tersimpan sebagian. ${js.errors.length} kesalahan ditemukan.`;

        // BUNDLE ERROR FIX: Show details for bundle errors to help user understand issue
        const bundleErrors = js.errors.filter(e => e.field && e.field.startsWith('bundle.'));
        if (bundleErrors.length > 0) {
          const bundleDetails = bundleErrors.map(e => `• ${e.message}`).slice(0, 3).join('\n');
          userMsg += '\n\nDetail:\n' + bundleDetails;
          if (bundleErrors.length > 3) {
            userMsg += `\n... dan ${bundleErrors.length - 3} error lainnya.`;
          }
        }

        toast(userMsg, 'warning', 5000); // Longer duration for error messages
        console.warn('[SAVE] Partial success with errors:', js.errors);
      } else {
        // Full success - use server's success message with expansion feedback
        let userMsg = js.user_message || '✅ Data berhasil disimpan!';

        // ENHANCED: Show bundle expansion feedback
        const rawRows = js.saved_raw_rows || 0;
        const expandedRows = js.saved_expanded_rows || 0;

        if (expandedRows > rawRows) {
          // Bundles were expanded
          const bundleCount = rawRows - (rows.filter(r => r.kategori !== 'LAIN').length);
          const expandedCount = expandedRows - rawRows;
          if (bundleCount > 0) {
            userMsg += `\n\n📦 ${bundleCount} bundle di-expand menjadi ${expandedCount} komponen tambahan.`;
          }
        }

        toast(userMsg, 'success');
        console.log('[SAVE] Success - Raw:', rawRows, 'Expanded:', expandedRows, 'Expansion:', expandedRows - rawRows);
      }

      // Update state
      setDirty(false);

      // P0 FIX: Use response data directly instead of double fetch
      // Server already sends fresh data in save response - no need to fetch again!
      const hasExpansion = (js.saved_expanded_rows || 0) > (js.saved_raw_rows || 0);

      if (hasExpansion) {
        // Bundle expansion occurred - reload to get expanded components
        console.log('[SAVE] Bundle expansion detected - reloading to fetch expanded components');
        delete rowsByJob[activeJobId];
        reloadJobs([activeJobId], { preserveSelection: true, silent: true, queue: true }).catch(() => {});
      } else {
        // Simple save without expansion - update cache directly from response
        console.log('[SAVE] Updating cache directly from response (no expansion)');

        if (js.items && Array.isArray(js.items)) {
          // Server returned updated items - use them
          rowsByJob[activeJobId] = {
            items: js.items,
            kategoriMeta: rowsByJob[activeJobId]?.kategoriMeta || kategoriMeta,
            readOnly: rowsByJob[activeJobId]?.readOnly || readOnly,
            updatedAt: js.pekerjaan?.updated_at || null,
            cachedAt: Date.now()
          };
          paint(js.items);
          console.log('[SAVE] Cache updated with', js.items.length, 'items from response');
        } else {
          // Fallback: Server didn't return items - use what we sent
          rowsByJob[activeJobId] = {
            items: rowsCanon,
            kategoriMeta: rowsByJob[activeJobId]?.kategoriMeta || kategoriMeta,
            readOnly: rowsByJob[activeJobId]?.readOnly || readOnly,
            updatedAt: js.pekerjaan?.updated_at || null,
            cachedAt: Date.now()
          };
          paint(rowsCanon);
          console.log('[SAVE] Cache updated with sent data (server response had no items)');
        }
      }
    }).catch((err) => {
      // Network error or unexpected error
      console.error('[SAVE] Catch error:', err);
      console.error('[SAVE] Error stack:', err.stack);
      toast('❌ Gagal menyimpan. Periksa koneksi internet Anda dan coba lagi.', 'error');
    }).finally(() => {
      if (spin) spin.hidden = true;
      if (btnSave) btnSave.disabled = false;
    });
  }

  // SAVE button handler - use refactored doSave function
  $('#ta-btn-save').addEventListener('click', () => {
    if (!activeJobId) return;
    doSave(activeJobId).catch(() => {
      // Error already handled in doSave
    });
  });

  // Hapus baris terseleksi per segmen (ENHANCED: with confirmation)
  document.addEventListener('click', (e) => {
    const delBtn = e.target.closest('.ta-seg-del-selected');
    if (!delBtn) return;
    if (activeSource === 'ref') return;
    const seg = delBtn.dataset.targetSeg;
    const body = document.getElementById(`seg-${seg}-body`);
    if (!body) return;
    const checked = body.querySelectorAll('.ta-row-check:checked');
    if (!checked.length) return;

    // CRITICAL IMPROVEMENT: Show confirmation with preview
    const count = checked.length;
    const items = Array.from(checked).map(cb => {
      const row = cb.closest('tr.ta-row');
      const kode = row?.querySelector('input[data-field="kode"]')?.value || '?';
      const uraian = row?.querySelector('.cell-wrap')?.textContent?.trim() || '?';
      return { kode, uraian };
    }).slice(0, 5); // Show max 5 items in preview

    const preview = items.map(item => `• ${item.kode}: ${item.uraian}`).join('\n');
    const moreText = count > 5 ? `\n... dan ${count - 5} baris lainnya` : '';

    const confirmMsg = `⚠️ HAPUS ${count} BARIS TERPILIH?\n\n${preview}${moreText}\n\nTindakan ini tidak bisa dibatalkan (belum ada undo).`;

    if (!confirm(confirmMsg)) {
      console.log('[DELETE] User cancelled deletion');
      return; // User cancelled
    }

    // Proceed with deletion
    console.log(`[DELETE] Deleting ${count} rows from segment ${seg}`);
    checked.forEach(cb => cb.closest('tr.ta-row')?.remove());
    if (!body.querySelector('tr.ta-row')) {
      body.innerHTML = `<tr class=\"ta-empty\"><td colspan=\"5\">Belum ada item.</td></tr>`;
    }
    formatIndex();
    setDirty(true);
    updateDelState(seg);

    // Show feedback toast
    toast(`🗑️ ${count} baris berhasil dihapus dari ${seg}`, 'info');
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
    resetBtn.addEventListener('click', async () => {
      if (!activeJobId || activeSource !== 'ref_modified') return;
      if (!confirm('Reset rincian dari referensi? Perubahan lokal akan hilang.')) return;

      const url = urlFor(endpoints.reset, activeJobId);

      try {
        // Fetch with HTTP error checking
        const response = await fetch(url, {
          method:'POST',
          credentials:'same-origin',
          headers:{ 'X-CSRFToken': CSRF }
        });

        // Check HTTP status first
        if (!response.ok) {
          const text = await response.text();
          let errorMsg = 'Gagal reset. Silakan coba lagi.';

          if (response.status === 403) {
            errorMsg = '⛔ Anda tidak memiliki akses untuk reset pekerjaan ini.';
          } else if (response.status === 404) {
            errorMsg = '❌ Pekerjaan atau referensi tidak ditemukan.';
          } else if (response.status === 500) {
            errorMsg = '⚠️ Server error. Hubungi administrator.';
          } else if (text) {
            errorMsg = `HTTP ${response.status}: ${text}`;
          }

          throw new Error(errorMsg);
        }

        const js = await response.json();

        // Check API response status
        if (!js.ok) {
          // Extract specific error from server
          const errorMsg = js.errors && js.errors.length > 0
            ? js.errors.map(e => e.message).join('; ')
            : js.user_message || 'Gagal reset. Silakan coba lagi.';
          throw new Error(errorMsg);
        }

        // Success: reload data
        const getResponse = await fetch(urlFor(endpoints.get, activeJobId), {credentials:'same-origin'});
        const getData = await getResponse.json();

        // P1 FIX: Add cache timestamp
        rowsByJob[activeJobId] = {
          items: getData.items || [],
          kategoriMeta: getData.meta?.kategori_opts || [],
          readOnly: !!getData.meta?.read_only,
          updatedAt: getData.pekerjaan?.updated_at || null,
          cachedAt: Date.now()
        };

        paint(rowsByJob[activeJobId].items);
        setDirty(false);
        setEditorModeBySource();

        // Show success with item count
        const count = getData.items?.length || 0;
        toast(`✅ Berhasil reset ${count} item dari referensi`, 'success');

      } catch(err) {
        // Comprehensive error handling
        console.error('[RESET ERROR]', err);

        let errorMsg = 'Gagal reset. Silakan coba lagi.';

        if (err.message) {
          if (err.message.includes('timeout') || err.message.includes('Failed to fetch')) {
            errorMsg = '⏱️ Koneksi timeout. Periksa internet dan coba lagi.';
          } else if (err.message.includes('NetworkError') || err.message.includes('Network request failed')) {
            errorMsg = '🌐 Tidak ada koneksi internet. Periksa koneksi Anda.';
          } else {
            errorMsg = err.message; // Use specific error from server
          }
        }

        toast(errorMsg, 'error');
      }
    });
  }

  // RELOAD - Force refresh data dari server (CACHE FIX)
  const reloadBtn = $('#ta-btn-reload');
  if (reloadBtn) {
    reloadBtn.addEventListener('click', () => {
      if (!activeJobId) {
        toast('⚠️ Tidak ada pekerjaan yang dipilih', 'warning');
        return;
      }

      // Konfirmasi jika ada perubahan yang belum disimpan
      if (dirty) {
        const confirmMsg = (
          "⚠️ PERUBAHAN BELUM TERSIMPAN!\n\n" +
          "Anda memiliki perubahan yang belum disimpan.\n\n" +
          "Pilihan:\n" +
          "• OK = Buang perubahan dan muat ulang data terbaru dari server\n" +
          "• Cancel = Batalkan reload dan simpan dulu\n\n" +
          "⚠️ Perubahan yang belum disimpan akan hilang!"
        );

        if (!confirm(confirmMsg)) {
          console.log('[RELOAD] User cancelled reload - has unsaved changes');
          return;
        }
      }

      // Clear cache dan force refresh
      console.log('[RELOAD] Force refreshing data for pekerjaan:', activeJobId);
      delete rowsByJob[activeJobId]; // Clear cache

      // Re-fetch dari server dengan forceRefresh = true
      const currentJobEl = $(`.ta-job-item[data-pekerjaan-id="${activeJobId}"]`);
      if (currentJobEl) {
        toast('🔄 Memuat ulang data terbaru...', 'info');
        selectJobInternal(currentJobEl, activeJobId, true); // forceRefresh = true
      } else {
        toast('❌ Pekerjaan tidak ditemukan', 'error');
      }
    });
  }

  // P3.1 FIX: Proper CSV export with escaping
  function escapeCSV(value) {
    const str = String(value || '');
    // If contains delimiter, quote, or newline, wrap in quotes and escape quotes
    if (str.includes(';') || str.includes('"') || str.includes('\n') || str.includes('\r')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  }

  // EXPORT CSV (koefisien format kanonik titik)
  $('#ta-btn-export').addEventListener('click', () => {
    if (!activeJobId) return;
    const rows = gatherRows();

    // UTF-8 BOM for Excel compatibility
    const BOM = '\uFEFF';
    const header = 'kategori;kode;uraian;satuan;koefisien';

    const csvRows = rows.map(r => {
      const koefCanon = __koefToCanon(r.koefisien || '');
      return [
        escapeCSV(r.kategori),
        escapeCSV(r.kode),
        escapeCSV(r.uraian),
        escapeCSV(r.satuan),
        escapeCSV(koefCanon)
      ].join(';');
    });

    const csv = BOM + [header, ...csvRows].join('\n');
    const blob = new Blob([csv], {type:'text/csv;charset=utf-8;'});
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);

    // Better filename with timestamp
    const timestamp = new Date().toISOString().slice(0,19).replace(/[: ]/g, '-');
    const jobKode = $('#ta-active-kode').textContent.trim() || activeJobId;
    a.download = `template_ahsp_${jobKode}_${timestamp}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
    toast('✅ CSV berhasil di-export', 'success');
  });

  // toast notification - use global DP.core.toast if available
  /**
   * Show toast notification with auto-dismiss
   * @param {string} msg - Message to display
   * @param {string} type - Type: 'success', 'error', 'warning', 'info'
   * @param {number} delay - Auto-dismiss delay in ms (default: 3000)
   */
  function toast(msg, type='info', delay=3000) {
    console.log(`[TOAST ${type.toUpperCase()}] ${msg}`);

    // Use global DP.core.toast if available (with correct z-index)
    if (window.DP && window.DP.core && window.DP.core.toast) {
      window.DP.core.toast.show(msg, type, delay);
      return;
    }

    // Fallback to inline implementation
    // P3.2 FIX: Toast stacking with max limit
    let container = document.getElementById('ta-toast-container');
    if (!container) {
      container = document.createElement('div');
      container.id = 'ta-toast-container';
      container.style.cssText = `
        position: fixed;
        top: 80px;
        right: 20px;
        z-index: 13100;
        display: flex;
        flex-direction: column;
        gap: 10px;
        max-width: 400px;
      `;
      document.body.appendChild(container);
    }

    // Remove oldest toasts if more than 5
    const existingToasts = container.querySelectorAll('.ta-toast');
    if (existingToasts.length >= 5) {
      existingToasts[0].remove(); // Remove oldest (first)
    }

    // Icon and color mapping
    const config = {
      success: { icon: 'bi-check-circle-fill', bg: '#28a745', color: '#fff' },
      error: { icon: 'bi-x-circle-fill', bg: '#dc3545', color: '#fff' },
      warning: { icon: 'bi-exclamation-triangle-fill', bg: '#ffc107', color: '#000' },
      info: { icon: 'bi-info-circle-fill', bg: '#17a2b8', color: '#fff' }
    };
    const cfg = config[type] || config.info;

    // Create toast element
    const toastEl = document.createElement('div');
    toastEl.className = 'ta-toast';
    toastEl.style.cssText = `
      background: ${cfg.bg};
      color: ${cfg.color};
      padding: 12px 16px;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      display: flex;
      align-items: center;
      gap: 12px;
      min-width: 300px;
      animation: slideInRight 0.3s ease-out;
      font-size: 14px;
      line-height: 1.4;
    `;

    toastEl.innerHTML = `
      <i class="bi ${cfg.icon}" style="font-size: 20px; flex-shrink: 0;"></i>
      <span style="flex: 1;">${escapeHtml(msg)}</span>
      <button type="button" style="
        background: none;
        border: none;
        color: ${cfg.color};
        font-size: 20px;
        line-height: 1;
        cursor: pointer;
        padding: 0;
        opacity: 0.7;
        flex-shrink: 0;
      " aria-label="Close">&times;</button>
    `;

    // Close button
    const closeBtn = toastEl.querySelector('button');
    closeBtn.addEventListener('click', () => {
      toastEl.style.animation = 'slideOutRight 0.3s ease-in';
      setTimeout(() => toastEl.remove(), 300);
    });

    // Auto-dismiss after 5 seconds (error stays longer)
    const duration = type === 'error' ? 8000 : 5000;
    setTimeout(() => {
      if (toastEl.parentNode) {
        toastEl.style.animation = 'slideOutRight 0.3s ease-in';
        setTimeout(() => toastEl.remove(), 300);
      }
    }, duration);

    container.appendChild(toastEl);
  }

  // Helper: Escape HTML to prevent XSS
  function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  // Add animations via <style>
  if (!document.getElementById('ta-toast-animations')) {
    const style = document.createElement('style');
    style.id = 'ta-toast-animations';
    style.textContent = `
      @keyframes slideInRight {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes slideOutRight {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
      }
    `;
    document.head.appendChild(style);
  }

  // auto-select first job
  const first = $('#ta-job-list .ta-job-item:not([hidden])');
  if (first) selectJob(first);

  // =========================
  // CRITICAL SAFETY: Warn before leaving page with unsaved changes
  // =========================
  window.addEventListener('beforeunload', (e) => {
    if (dirty) {
      // Modern browsers ignore custom message and show default warning
      // But we still need to set returnValue for compatibility
      const msg = 'Anda memiliki perubahan yang belum disimpan. Yakin ingin meninggalkan halaman?';
      e.preventDefault();
      e.returnValue = msg; // Required for Chrome/Firefox
      console.log('[BEFOREUNLOAD] Warned user about unsaved changes');
      return msg; // For older browsers
    }
  });

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
