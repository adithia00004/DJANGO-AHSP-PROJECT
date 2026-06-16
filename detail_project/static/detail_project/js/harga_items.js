// harga_items.js — Drop-in full version (formal terms + robust conversion)
// - Patuh SSOT (tidak menulis --dp-*), hanya menulis var halaman (--hi-toolbar-h)
// - Fitur: null-vs-zero, validasi angka (negatif/>2dp/out-of-range), bulk paste, konversi satuan
(function () {
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

  // PERF: bootstrap SSR (payload canon=1) supaya fetchList() pertama tidak perlu
  // round-trip AJAX saat halaman dibuka. null jika tidak tersedia → fallback fetch.
  // Freshness payload dijamin oleh DetailProjectNoStoreMiddleware pada respons HTML.
  const HI_BOOTSTRAP = (() => {
    try {
      const el = document.getElementById('hi-bootstrap');
      if (!el) return null;
      const data = JSON.parse(el.textContent || 'null');
      return (data && typeof data === 'object') ? data : null;
    } catch (e) {
      console.warn('[HI] Gagal membaca bootstrap SSR:', e);
      return null;
    }
  })();

  // DOM
  const $tbody = document.getElementById('hi-tbody');
  const $filter = document.getElementById('hi-filter');
  const $btnSave = document.getElementById('hi-btn-save');
  // Unified export (dropdown like Rekap RAB)
  const btnExportCSV = document.getElementById('btn-export-csv');
  const btnExportPDF = document.getElementById('btn-export-pdf');
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
  const debounce = (fn, ms = 120) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
  function syncToolbarH() {
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
  const toast = (msg, variant = 'info', delay = 3000) => {
    const type = variant === 'danger' ? 'error' : variant;
    if (window.DP && DP.toast && DP.toast.show) return DP.toast.show(msg, type, delay);
    if (window.DP && DP.core && DP.core.toast && DP.core.toast.show) return DP.core.toast.show(msg, type, delay);
    if (typeof window.showToast === 'function') return window.showToast(msg, type, delay);
    console.warn('[HI] Toast:', msg);
  };

  const confirmModal = (message, options = {}) => {
    const modalApi = window.DP && DP.core && DP.core.modal ? DP.core.modal : null;
    if (modalApi && modalApi.confirm) return modalApi.confirm(message, options);
    if (window.DP && DP.toast) DP.toast.warning('Konfirmasi tidak tersedia.');
    return Promise.resolve(false);
  };

  // State
  const katMap = { TK: 'Tenaga', BHN: 'Bahan', ALT: 'Alat', LAIN: 'Lainnya' };
  const Dim = { MASS: 'mass', VOL: 'volume', COUNT: 'count', OTHER: 'other' };
  let rows = [];
  let viewRows = [];
  let bukCanonLoaded = "";

  // Dirty state tracking
  let dirty = false;
  let allowUnload = false;
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
    } else {
      toast('Halaman Template AHSP tidak tersedia.', 'warning');
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

  window.addEventListener('dp:sync-refresh-request', (event) => {
    const detail = event.detail || {};
    if (Number(detail.projectId) !== projectId) return;
    if (detail.scope && detail.scope !== 'harga' && detail.scope !== 'global') return;

    event.preventDefault();
    const isAuto = detail.reason === 'auto';

    const refreshList = () => fetchList()
      .then(() => {
        updateSyncLockState();
        if (!isAuto) {
          toast('Data harga berhasil disegarkan.', 'info');
        }
      })
      .catch((err) => {
        console.error('[HI] Sync refresh failed:', err);
        toast('Gagal menyegarkan data harga.', 'error');
      });

    if (!dirty) {
      refreshList();
      return;
    }

    if (isAuto) {
      toast('Perubahan belum disimpan. Sinkronisasi otomatis ditunda.', 'warning');
      return;
    }

    confirmModal(
      'Perubahan harga yang belum disimpan akan hilang jika Anda melanjutkan sinkronisasi.',
      {
        title: 'Konfirmasi Sinkronisasi',
        confirmText: 'Sinkronkan',
        cancelText: 'Batal',
        confirmClass: 'btn btn-warning',
      }
    ).then((ok) => {
      if (!ok) return;
      refreshList();
    });
  });

  // ===== Helpers: numeric & format
  const toUI = (s) => N ? N.formatForUI(N.enforceDp(s || '', DP)) : (s || '');
  // Locale-aware canonicalizer: prevents "100.000" (id-ID grouping) becoming 100.00
  function canonFromUI(raw, dp) {
    const s0 = String(raw ?? '').trim();
    if (!s0) return '';
    const hasDot = s0.includes('.');
    const hasComma = s0.includes(',');
    if (hasDot && !hasComma) {
      const dotGrouping = /^\d{1,3}(\.\d{3})+$/;
      if (dotGrouping.test(s0)) {
        const noGroup = s0.replace(/\./g, '');
        return N ? (N.enforceDp(noGroup, dp) || '') : noGroup;
      }
    }
    if (hasComma && !hasDot) {
      const commaGrouping = /^\d{1,3}(,\d{3})+$/;
      if (commaGrouping.test(s0)) {
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
  const toCanon = (v) => canonFromUI(v, DP);
  const toUI2 = (s) => N ? N.formatForUI(N.enforceDp(s || '', 2)) : (s || '');
  const toCanon2 = (v) => canonFromUI(v, 2);
  const toCanonFloat = (v, dp = 6) => canonFromUI(v, dp);
  const rupiah = (canon) => {
    if (canon == null || canon === '') return '—';
    const n = Number(canon); if (!isFinite(n)) return '—';
    return fmtRp.format(n);
  };
  const decCountFromCanon = (canon) => {
    const s = String(canon ?? '');
    if (!s) return 0;
    const i = s.lastIndexOf('.');
    return i === -1 ? 0 : (s.length - i - 1);
  };
  const csrfToken = () => {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  };
  function inferDim(u) {
    const s = (u || '').toLowerCase().trim();
    if (['kg', 'g', 'gram', 'ons', 'ton', 'mg'].includes(s)) return Dim.MASS;
    if (['m3', 'm³', 'l', 'lt', 'liter', 'ml'].includes(s)) return Dim.VOL;
    if (['zak', 'pcs', 'buah', 'unit', 'bh'].includes(s)) return Dim.COUNT;
    return Dim.OTHER;
  }

  function doSafeReload() {
    allowUnload = true;
    window.location.reload();
  }

  async function confirmReload(reason) {
    if (!dirty) {
      doSafeReload();
      return true;
    }
    const message = reason
      ? `${reason}\n\nPerubahan harga yang belum disimpan akan hilang jika Anda melanjutkan.`
      : 'Perubahan harga yang belum disimpan akan hilang jika Anda melanjutkan reload halaman.';
    const ok = await confirmModal(message, {
      title: 'Konfirmasi Reload',
      confirmText: 'Reload',
      cancelText: 'Batal',
      confirmClass: 'btn btn-danger',
    });
    if (ok) {
      doSafeReload();
    }
    return ok;
  }

  // P0 FIX: Unsaved changes warning - prevent data loss on browser close/refresh
  window.addEventListener('beforeunload', (e) => {
    if (dirty && !allowUnload) {
      const msg = 'Anda memiliki perubahan harga yang belum disimpan. Yakin ingin meninggalkan halaman?';
      e.preventDefault();
      e.returnValue = msg;
      return msg;
    }
  });

  window.addEventListener('keydown', (e) => {
    if (!dirty) return;
    const key = String(e.key || '').toLowerCase();
    const isReload = e.key === 'F5' || ((e.ctrlKey || e.metaKey) && key === 'r');
    if (!isReload) return;
    e.preventDefault();
    confirmReload('Anda akan memuat ulang halaman.');
  });

  // ===== Konversi: in-memory, server-backed (no localStorage — WP-P1f/HI-08).
  // Profile shape is backend-keyed: {market_unit, market_price, factor_to_base,
  // density, capacity_m3, capacity_ton, method, base_unit?}.
  const convStore = new Map(); // key: item.id -> profile

  // ===== Fetch list
  async function fetchList(preloaded) {
    // PERF: pakai bootstrap SSR pada panggilan pertama agar tidak ada flash "Memuat data…".
    if (!preloaded) setEmpty('Memuat data…');
    try {
      let j = preloaded;
      if (!j) {
        const res = await fetch(EP_LIST, { credentials: 'same-origin' });
        j = await res.json();
      }
      if (!j.ok) throw new Error('Gagal memuat.');
      rows = (j.items || []).map((it, i) => ({
        idx: i + 1,
        id: it.id,
        kode: it.kode_item,
        uraian: it.uraian,
        satuan: it.satuan || '',
        kategori: it.kategori,
        harga_canon: it.harga_satuan == null ? '' : String(it.harga_satuan),
        conv: it.conv || null // opsional dari server
      }));

      // WP-P1f (HI-08): conversion profiles come ONLY from the server (the SSOT).
      // The old per-browser localStorage fallback is removed — it was not
      // project-scoped (same kode in two projects shared a browser profile) and
      // could resurrect stale data.
      rows.forEach(r => {
        if (r.conv) convStore.set(r.id, r.conv);
      });

      // Profit/Margin
      if (j.meta && typeof j.meta.markup_percent !== 'undefined') {
        bukCanonLoaded = String(j.meta.markup_percent || '10.00');
        if ($bukInput) $bukInput.value = toUI2(bukCanonLoaded);
      }

      // P0 FIX: OPTIMISTIC LOCKING - Store timestamp when data is loaded

      renderTable(rows);
      setDirty(false);  // Mark as clean after loading
    } catch (e) {
      setEmpty('Gagal memuat data.');
      console.error(e);
    }
  }

  function setEmpty(text) {
    $tbody.innerHTML = `<tr class="hi-empty"><td colspan="7">${text}</td></tr>`;
    $stats.textContent = '0 item';
  }

  // ===== Render table
  function renderTable(data) {
    if (!data || data.length === 0) { setEmpty('Tidak ada item harga yang digunakan di Detail AHSP.'); return; }
    const fr = document.createDocumentFragment();
    viewRows = [];
    data.forEach((r, i) => {
      const tr = document.createElement('tr');
      tr.dataset.itemId = r.id;
      tr.dataset.kode = (r.kode || '').toLowerCase();
      tr.dataset.uraian = (r.uraian || '').toLowerCase();
      tr.dataset.kategori = r.kategori || '';
      tr.dataset.satuan = r.satuan || '';
      // HI-01 / UF-011: harga NULL ("belum diisi") tetap KOSONG — jangan render
      // "0.00" dan jangan jadikan baseline 0, karena itu meng-convert belum-diisi
      // → 0 eksplisit saat save (mematahkan null≠zero & sinyal missing_price).
      const isUnfilled = (r.harga_canon === '' || r.harga_canon == null);
      const canonDisp = isUnfilled ? '' : r.harga_canon;

      tr.innerHTML = `
        <td class="mono text-center">${i + 1}</td>
        <td><span class="hi-cat-badge hi-cat-badge-${r.kategori || 'LAIN'}">${escapeHtml(katMap[r.kategori] || r.kategori || 'LAIN')}</span></td>
        <td class="mono">${escapeHtml(r.kode)}</td>
        <td>${escapeHtml(r.uraian)}</td>
        <td>${escapeHtml(r.satuan)}</td>
        <td>
          <div class="d-flex align-items-center gap-2">
            <input type="text" inputmode="decimal"
                   class="form-control form-control-sm ux-focusable hi-input-price text-end ux-tabular"
                   value="${escapeAttr(isUnfilled ? '' : toUI(canonDisp))}"
                   placeholder="belum diisi"
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
      // simpan canon awal untuk deteksi edit/empty ('' utk belum-diisi → tak dirty)
      tr.dataset.origCanon = canonDisp;
      tr.dataset.manualEdited = '0';
      // HI-01/UF-011: hanya baris BELUM DIISI (null/empty) yang ditandai empty;
      // harga 0 eksplisit = gratis, bukan belum-diisi.
      if (isUnfilled) {
        tr.classList.add('hi-row-empty');
        const inp = tr.querySelector('.hi-input-price');
        if (inp) inp.classList.add('vp-empty');
      }
      fr.appendChild(tr);
      viewRows.push(tr);
    });
    $tbody.innerHTML = '';
    $tbody.appendChild(fr);
    $stats.textContent = `${data.length} item`;
    updateStats(); // Update summary cards
  }

  const escapeHtml = (s) => (s ?? '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m]));
  const escapeAttr = (s) => escapeHtml(s);

  // ===== Stats Update (Simplified) =====
  function updateStats() {
    const total = viewRows.length;
    let filled = 0, emptyCount = 0;
    const catCounts = { TK: 0, BHN: 0, ALT: 0, LAIN: 0 };

    viewRows.forEach(tr => {
      const cat = tr.dataset.kategori || 'LAIN';
      catCounts[cat] = (catCounts[cat] || 0) + 1;

      const isEmptyRow = tr.classList.contains('hi-row-empty');
      if (isEmptyRow) {
        emptyCount++;
      } else {
        filled++;
      }
    });

    // Update filter counts
    const countAll = document.getElementById('hi-count-all');
    const countTK = document.getElementById('hi-count-TK');
    const countBHN = document.getElementById('hi-count-BHN');
    const countALT = document.getElementById('hi-count-ALT');
    const countLAIN = document.getElementById('hi-count-LAIN');
    const countEmpty = document.getElementById('hi-count-empty');
    if (countAll) countAll.textContent = total;
    if (countTK) countTK.textContent = catCounts.TK || 0;
    if (countBHN) countBHN.textContent = catCounts.BHN || 0;
    if (countALT) countALT.textContent = catCounts.ALT || 0;
    if (countLAIN) countLAIN.textContent = catCounts.LAIN || 0;
    if (countEmpty) countEmpty.textContent = emptyCount;
  }

  // ===== Category Filter Buttons =====
  let currentCatFilter = 'all';
  document.querySelectorAll('.hi-filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.hi-filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentCatFilter = btn.dataset.filter;
      applyFilters();
    });
  });

  function applyFilters() {
    const q = ($filter?.value || '').trim().toLowerCase();
    let show = 0;

    viewRows.forEach(tr => {
      let matchCat = true;
      if (currentCatFilter === 'empty') {
        matchCat = tr.classList.contains('hi-row-empty');
      } else if (currentCatFilter !== 'all') {
        matchCat = tr.dataset.kategori === currentCatFilter;
      }

      let matchSearch = true;
      if (q) {
        matchSearch = tr.dataset.kode.includes(q)
          || tr.dataset.uraian.includes(q)
          || (katMap[tr.dataset.kategori] || '').toLowerCase().includes(q);
      }

      const visible = matchCat && matchSearch;
      tr.hidden = !visible;
      if (visible) show++;
    });

    $stats.textContent = show === viewRows.length ? `${show} item` : `${show} / ${viewRows.length} item`;
  }

  // ===== Search Filter (enhanced)
  $filter?.addEventListener('input', () => {
    applyFilters();
  });

  // ===== Input/Blur: validasi live + autofill 0
  function setRowDirtyVisual(tr, isDirty) {
    if (!tr) return;
    tr.classList.toggle('hi-row-edited', !!isDirty);
    // Hindari background kuning Bootstrap di dark mode
    if (tr.classList.contains('table-warning')) tr.classList.remove('table-warning');
  }
  $tbody.addEventListener('input', (e) => {
    const el = e.target;
    if (!(el instanceof HTMLInputElement) || !el.classList.contains('hi-input-price')) return;
    const tr = el.closest('tr');
    // WP-P1b-wiring (Model A last-write-wins): a manual edit to a converted row
    // drops its conversion profile (signalled to the server via clear_conversion).
    // The modal sets the price programmatically and does NOT fire 'input', so this
    // only triggers on real user typing/paste.
    const _rid = Number(tr?.dataset.itemId);
    if (tr && convStore.has(_rid)) {
      convStore.delete(_rid);
      tr.dataset.clearConv = '1';
    }
    const raw = (el.value || '').trim();

    // Menghapus harga yang sebelumnya terisi adalah perubahan valid: simpan
    // sebagai NULL ("belum diisi"), aktifkan tombol Simpan, dan jangan tandai
    // field sebagai angka invalid.
    if (raw === '') {
      el.classList.remove('ux-invalid');
      el.classList.add('vp-empty');
      tr?.classList.remove('hi-row-invalid', 'hi-row-zero');
      tr?.classList.add('hi-row-empty');
      const prev = tr?.querySelector('.hi-price-preview');
      if (prev) prev.textContent = rupiah('');
      if (tr) {
        const orig = tr.dataset.origCanon || '';
        const isDirty = orig !== '';
        tr.dataset.manualEdited = isDirty ? '1' : '0';
        setRowDirtyVisual(tr, isDirty);
        if (isDirty || $bukInput?.value !== toUI2(bukCanonLoaded)) {
          setDirty(true);
        }
      }
      return;
    }

    const canon = toCanon(el.value) || '';
    const num = Number(canon || 'NaN');
    const invalid = !isFinite(num) || num < 0 || num > MAX_PRICE;
    el.classList.toggle('ux-invalid', invalid);
    if (tr) tr.classList.toggle('hi-row-invalid', invalid);
    const prev = tr?.querySelector('.hi-price-preview');
    if (prev) prev.textContent = invalid ? '-' : rupiah(canon || '0.00');
    if (tr) tr.dataset.manualEdited = '1';
    // Harga terisi: hilangkan tanda empty saat user mengetik.
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
  $tbody.addEventListener('blur', (e) => {
    const el = e.target;
    if (!(el instanceof HTMLInputElement) || !el.classList.contains('hi-input-price')) return;

    const tr = el.closest('tr');
    const raw = (el.value || '').trim();

    // HI-01 / UF-011: field kosong = "belum diisi" — JANGAN autofill 0.00.
    if (raw === '') {
      el.value = '';
      el.classList.remove('ux-invalid');
      el.classList.add('vp-empty');
      const prevEmpty = tr?.querySelector('.hi-price-preview');
      if (prevEmpty) prevEmpty.textContent = rupiah('');  // "—"
      if (tr) {
        tr.classList.remove('hi-row-invalid', 'hi-row-zero');
        tr.classList.add('hi-row-empty');
        const orig = tr.dataset.origCanon || '';
        const isDirty = (orig !== '');  // sebelumnya ada nilai → dikosongkan = perubahan
        tr.dataset.manualEdited = isDirty ? '1' : '0';
        setRowDirtyVisual(tr, isDirty);
      }
      return;
    }

    const canon = toCanon(el.value);
    const num = Number(canon);

    const invalid = !isFinite(num) || num < 0 || num > MAX_PRICE;
    el.value = toUI(canon);
    el.classList.toggle('ux-invalid', invalid);
    el.classList.remove('vp-empty');
    if (tr) tr.classList.toggle('hi-row-invalid', invalid);

    const prev = tr?.querySelector('.hi-price-preview');
    if (prev) prev.textContent = invalid ? '-' : rupiah(canon);
    if (tr) {
      tr.classList.remove('hi-row-empty');
      const orig = tr.dataset.origCanon || '';
      const isDirty = (orig !== canon);
      tr.dataset.manualEdited = isDirty ? '1' : '0';
      setRowDirtyVisual(tr, isDirty);
      // Atur tanda nol setelah normalisasi
      tr.classList.toggle('hi-row-zero', Number(canon) === 0);
    }
  }, true);

  // ===== Profit/Margin: enforce 2dp pada blur
  // P0 FIX: Mark dirty when BUK/markup changes
  $bukInput?.addEventListener('input', () => {
    const canon = toCanon2($bukInput.value);
    if (canon && canon !== bukCanonLoaded) {
      setDirty(true);
    }
  });

  $bukInput?.addEventListener('blur', () => {
    const canon = toCanon2($bukInput.value);
    $bukInput.value = toUI2(canon || bukCanonLoaded);
  });

  // ===== SAVE
  $btnSave?.addEventListener('click', async () => {
    try {
      const payload = { items: [] };
      const mpCanon = toCanon2($bukInput?.value);

      // kumpulkan harga dengan validasi ketat (abort jika ada invalid)
      let invalidCount = 0;
      const idsSaving = [];
      viewRows.forEach(tr => {
        const id = Number(tr.dataset.itemId);
        const input = tr.querySelector('.hi-input-price');
        if (!input) return;

        // WP-P1b-wiring: explicit signal that a converted row was manually overridden
        // → server drops the now-stale profile (Model A). Non-destructive otherwise.
        const clearConv = tr.dataset.clearConv === '1';
        const withClear = (obj) => clearConv ? { ...obj, clear_conversion: true } : obj;

        // HI-01 / UF-011: field kosong = "belum diisi" → kirim null (JANGAN koersi 0.00).
        const raw = (input.value || '').trim();
        if (raw === '') {
          input.classList.remove('ux-invalid');
          payload.items.push(withClear({ id, harga_satuan: null }));
          idsSaving.push({ id, canon: '' });
          return;
        }
        const canon = toCanon(input.value);
        const n = Number(canon);
        const invalid = !canon || !isFinite(n) || n < 0 || n > MAX_PRICE;
        input.classList.toggle('ux-invalid', invalid);
        if (invalid) { invalidCount++; return; }

        payload.items.push(withClear({ id, harga_satuan: canon }));
        idsSaving.push({ id, canon });
      });

      if (invalidCount > 0) {
        toast(`Terdapat ${invalidCount} input tidak valid. Perbaiki sebelum menyimpan.`, 'warning');
        return;
      }

      // WP-P1b-wiring (HI-02): every staged/loaded conversion is sent so the
      // server applies it atomically (it recomputes harga_satuan = market/factor).
      // Re-sending an unchanged profile is an idempotent no-op.
      const conversions = [];
      convStore.forEach((p, id) => {
        if (!p) return;
        conversions.push({
          id,
          market_unit: p.market_unit,
          market_price: p.market_price,
          factor_to_base: p.factor_to_base,
          density: p.density || null,
          capacity_m3: p.capacity_m3 || null,
          capacity_ton: p.capacity_ton || null,
          method: p.method,
        });
      });
      if (conversions.length) payload.conversions = conversions;
      if (mpCanon) payload.markup_percent = mpCanon;

      if (payload.items.length === 0 && !payload.conversions && (!mpCanon || mpCanon === bukCanonLoaded)) {
        toast('Tidak ada perubahan valid untuk disimpan.', 'info');
        return;
      }

      // Application policy: last-write-wins. Atomicity is enforced per request.

      const spin = document.getElementById('hi-save-spin');
      $btnSave.disabled = true; spin?.removeAttribute('hidden');

      const res = await fetch(EP_SAVE, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken() },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      const j = await res.json();

      // P0 FIX: Use user_message from server
      if (!res.ok || !j.ok) {
        // Atomic rejection: no submitted row was persisted. Keep all rows dirty
        // and only mark the fields identified by the server as invalid.
        const userMsg = j.user_message || 'Data tidak disimpan. Perbaiki input lalu coba lagi.';
        toast(userMsg, 'warning');
        console.warn('[SAVE] Errors:', j.errors || []);

        // Petakan index error payload → baris (payload.items & idsSaving urut sama).
        const failedIdx = new Set();
        (j.errors || []).forEach((er) => {
          const m = /items\[(\d+)\]/.exec((er && er.field) || '');
          if (m) failedIdx.add(Number(m[1]));
        });

        idsSaving.forEach(({ id, canon }, i) => {
          const tr = $tbody.querySelector(`tr[data-item-id="${id}"]`);
          if (!tr) return;
          const input = tr.querySelector('.hi-input-price');
          if (failedIdx.has(i)) {
            input?.classList.add('ux-invalid');
          } else {
            input?.classList.remove('ux-invalid');
          }
        });
      } else {
        const userMsg = j.user_message || `✅ Berhasil menyimpan ${j.updated ?? payload.items.length} item.`;
        toast(userMsg, 'success');
        setDirty(false);  // Mark as clean after successful save

        // Tandai baris-baris yang tersimpan dan bersihkan status dirty/empty
        idsSaving.forEach(({ id, canon }) => {
          const tr = $tbody.querySelector(`tr[data-item-id="${id}"]`);
          if (!tr) return;
          tr.classList.add('hi-row-saved');
          setTimeout(() => tr.classList.remove('hi-row-saved'), 1200);
          const unfilled = (canon === '' || canon == null);
          tr.classList.toggle('hi-row-empty', unfilled);
          tr.classList.toggle('hi-row-zero', !unfilled && Number(canon) === 0);
          setRowDirtyVisual(tr, false);
          tr.dataset.origCanon = unfilled ? '' : canon;
          const input = tr.querySelector('.hi-input-price');
          input?.classList.remove('ux-invalid');
        });
        // Tunda refresh agar highlight terlihat
        setTimeout(() => fetchList(), 900);
      }
    } catch (e) {
      console.error(e);
      // SAFETY (#2): jangan fetchList() saat gagal jaringan — pertahankan input lokal pengguna.
      toast('❌ Gagal menyimpan (masalah jaringan). Perubahan Anda tetap ada — coba simpan lagi.', 'error');
    } finally {
      const spin = document.getElementById('hi-save-spin');
      $btnSave.disabled = false; spin?.setAttribute('hidden', '');
      // fetchList dipanggil pada cabang di atas
    }
  });

  // ===== EXPORT CSV
  // Export CSV (fallback local), or unified via ExportManager if available
  function exportCSVLocal() {
    const headers = ['No', 'Kategori', 'Kode', 'Uraian', 'Satuan', 'Harga', 'Nominal'];
    const lines = [headers.join(';')];
    let idx = 0;
    viewRows.forEach(tr => {
      if (tr.hidden) return;
      const kategori = tr.children[1].textContent.trim();
      const kode = tr.children[2].textContent.trim();
      const uraian = tr.children[3].textContent.trim().replace(/;/g, ',');
      const satuan = tr.children[4].textContent.trim();
      const input = tr.querySelector('.hi-input-price');
      const canon = toCanon(input.value);  // '' jika belum diisi — biarkan kosong di CSV
      const nominal = canon ? rupiah(canon).replace(/^Rp\s?/, 'Rp ') : '';
      lines.push([++idx, kategori, kode, uraian, satuan, canon || '', nominal].join(';'));
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url;
    a.download = `harga_items_${(new Date()).toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
  }

  (function initUnifiedExport() {
    if (!projectId) {
      // bind CSV local only
      btnExportCSV?.addEventListener('click', exportCSVLocal);
      return;
    }
    // ExportManager initialization is now handled in the template with modal spinner
    // Only provide CSV local fallback here if ExportManager loads fail
    if (typeof ExportManager === 'undefined') {
      console.log('[HI] ExportManager not available, using local CSV fallback');
      btnExportCSV?.addEventListener('click', exportCSVLocal);
    }
  })();

  // ===== BULK PASTE (Kode;[Unit];Harga;[Factor];[Density])
  // WP-P1e (HI-07): a row WITH a factor is a MARKET-price paste → the base price
  // is computed (market ÷ factor) before it lands in the price column, so a market
  // price can never be stored as the base price. A row WITHOUT a factor is a plain
  // BASE-price paste. Both are shown in a preview and applied only on confirm.
  document.addEventListener('paste', async (e) => {
    if (!e.clipboardData) return;
    const text = e.clipboardData.getData('text');
    if (!text || !text.includes('\n')) return; // bukan tabel
    const rowsPaste = text.trim().split(/\r?\n/).map(line => line.split(/\t|;/));
    const byKode = new Map();

    rowsPaste.forEach(cols => {
      const [kode, unit, harga, factor, density] = cols;
      const k = String(kode || '').trim().toLowerCase(); if (!k) return;
      byKode.set(k, {
        unit,
        harga: toCanon(harga || '0') || '0.00',
        factor: toCanonFloat(factor || '', 6),
        density: toCanonFloat(density || '', 6),
      });
    });

    // Build a plan: resolve each matched row's FINAL base price (market→base) and
    // its mode, without mutating anything yet.
    const plan = [];
    viewRows.forEach(tr => {
      const k = (tr.dataset.kode || '').toLowerCase();
      if (!byKode.has(k)) return;
      const { harga, factor, unit, density } = byKode.get(k);
      const isMarket = !!factor && Number(factor) > 0;
      let basePrice = harga;
      if (isMarket) {
        const b = Number(harga) / Number(factor);
        basePrice = isFinite(b) ? b.toFixed(2) : harga;
      }
      const n = Number(basePrice);
      const invalid = !isFinite(n) || n < 0 || n > MAX_PRICE;
      plan.push({ tr, kode: tr.dataset.kode || k, isMarket, basePrice, market: harga, factor, unit, density, invalid });
    });

    if (!plan.length) return;  // nothing in the project matches the pasted kode

    // Preview + confirm (formatMessage escapes everything and turns \n into <br>).
    const baseN = plan.filter(p => !p.isMarket && !p.invalid).length;
    const marketN = plan.filter(p => p.isMarket && !p.invalid).length;
    const invalidN = plan.filter(p => p.invalid).length;
    const sample = plan.slice(0, 6).map(p => {
      if (p.invalid) return `• ${p.kode}: tidak valid (dilewati)`;
      return p.isMarket
        ? `• ${p.kode}: Rp ${rupiah(p.market)}/${p.unit || 'satuan'} ÷ ${p.factor} = Rp ${rupiah(p.basePrice)} /satuan dasar`
        : `• ${p.kode}: Rp ${rupiah(p.basePrice)} (harga dasar)`;
    }).join('\n');
    const more = plan.length > 6 ? `\n… dan ${plan.length - 6} baris lain` : '';
    const msg =
      `Tempel massal akan menerapkan ke ${plan.length} item:\n` +
      `- ${baseN} harga dasar\n- ${marketN} konversi market (dihitung ke harga dasar)` +
      (invalidN ? `\n- ${invalidN} tidak valid (dilewati)` : '') +
      `\n\n${sample}${more}`;

    const ok = await confirmModal(msg, {
      title: 'Konfirmasi Tempel Massal', confirmText: 'Terapkan', cancelText: 'Batal',
    });
    if (!ok) { toast('Tempel massal dibatalkan.', 'info'); return; }

    // Apply the confirmed plan.
    let hit = 0, invalid = 0;
    plan.forEach(p => {
      const input = p.tr.querySelector('.hi-input-price');
      const prev = p.tr.querySelector('.hi-price-preview');
      if (!input || !prev) return;
      if (p.invalid) { input.classList.add('ux-invalid'); prev.textContent = '—'; invalid++; return; }

      input.value = toUI(p.basePrice);  // already the BASE price (market converted)
      input.classList.remove('ux-invalid');
      prev.textContent = rupiah(p.basePrice);
      setRowDirtyVisual(p.tr, true);
      hit++;

      const pid = Number(p.tr.dataset.itemId);
      if (p.isMarket) {
        // Stage the conversion (backend-keyed); server recomputes the same base.
        convStore.set(pid, {
          market_unit: (p.unit || '').toString(),
          market_price: p.market,
          factor_to_base: p.factor,
          density: p.density || '',
          capacity_m3: '',
          capacity_ton: '',
          method: 'direct',
          base_unit: p.tr.dataset.satuan || p.tr.children[4].textContent.trim(),
        });
        p.tr.dataset.clearConv = '0';
      } else if (convStore.has(pid)) {
        // Plain base-price paste over a converted row = manual override (Model A).
        convStore.delete(pid);
        p.tr.dataset.clearConv = '1';
      }
    });

    if (hit > 0) setDirty(true);
    toast(`Tempel massal: ${hit} baris${invalid ? `, ${invalid} tidak valid` : ''}.`, invalid ? 'warning' : 'success');
  });

  // ===== Modal Konversi: setup
  let convCtx = { tr: null, id: null, kode: '', base: '', baseDim: Dim.OTHER };

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

  function setUnitLabel(lbl) { $convUnitLabel.textContent = lbl; }
  function resetModal() {
    [$convPrice, $convCapM3, $convCapTon, $convDensity, $convFactor].forEach(i => { if (i) { i.value = ''; } });
    $convResult.textContent = '—'; $convHint.textContent = '';
    $convApply.disabled = true; $convError?.classList.add('d-none');
    // Add null checks for wrap elements (may not exist in simplified modal)
    $convCapM3Wrap?.classList.add('d-none'); $convCapTonWrap?.classList.add('d-none'); $convDensityWrap?.classList.add('d-none');
    const formula = document.getElementById('hi-conv-formula');
    if (formula) formula.textContent = 'Rumus: Harga per satuan pembelian dari Supplier ÷ Konstanta konversi';
  }

  // buka modal dari baris
  $tbody.addEventListener('click', (e) => {
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
    if (prof) {
      const unitName = prof.market_unit || '';
      const unitOpt = ['dump_truck', 'm3', 'ton', 'zak', 'custom'].includes(unitName) ? unitName : 'custom';
      $convUnit.value = unitOpt;
      if (unitOpt === 'custom') {
        $convUnitCustom.classList.remove('d-none');
        $convUnitCustom.value = unitName || 'satuan pembelian dari Supplier';
        setUnitLabel($convUnitCustom.value || 'satuan pembelian dari Supplier');
      } else {
        setUnitLabel(unitOpt);
      }
      if (prof.market_price) $convPrice.value = toUI2(prof.market_price);
      if (prof.factor_to_base) $convFactor.value = (N ? N.formatForUI(N.enforceDp(prof.factor_to_base, 6)) : (prof.factor_to_base || ''));
      if (prof.capacity_m3) { $convCapM3Wrap.classList.remove('d-none'); $convCapM3.value = (N ? N.formatForUI(N.enforceDp(prof.capacity_m3, 6)) : (prof.capacity_m3 || '')); }
      if (prof.capacity_ton) { $convCapTonWrap.classList.remove('d-none'); $convCapTon.value = (N ? N.formatForUI(N.enforceDp(prof.capacity_ton, 6)) : (prof.capacity_ton || '')); }
      if (prof.density) { $convDensityWrap.classList.remove('d-none'); $convDensity.value = (N ? N.formatForUI(N.enforceDp(prof.density, 6)) : (prof.density || '')); }
    }

    updateHelperVisibility();
    recalcConv();
  });

  // perubahan unit
  $convUnit?.addEventListener('change', () => {
    const v = $convUnit.value;
    if (v === 'custom') {
      $convUnitCustom.classList.remove('d-none');
      setUnitLabel($convUnitCustom.value || 'satuan pembelian dari Supplier');
    } else {
      $convUnitCustom.classList.add('d-none');
      setUnitLabel(v);
    }
    updateHelperVisibility();
    recalcConv();
  });

  $convUnitCustom?.addEventListener('input', () => {
    if ($convUnit.value === 'custom') {
      setUnitLabel($convUnitCustom.value || 'satuan pembelian dari Supplier');
      recalcConv();
    }
  });

  // input → hitung ulang
  [$convPrice, $convCapM3, $convCapTon, $convDensity, $convFactor].forEach(el => {
    el?.addEventListener('input', () => {
      if (el === $convCapM3 || el === $convCapTon || el === $convDensity) autoFillFactor();
      recalcConv();
    });
  });

  // apply konversi
  $convApply?.addEventListener('click', async () => {
    const canon = recalcConv(true);
    if (!canon) { $convError?.classList.remove('d-none'); return; }

    const input = convCtx.tr?.querySelector('.hi-input-price');
    const prev = convCtx.tr?.querySelector('.hi-price-preview');
    // Jika user sudah edit manual dan nilai akan berbeda, minta konfirmasi
    if (convCtx.tr) {
      const wasManual = convCtx.tr.dataset.manualEdited === '1';
      const curCanon = toCanon(input?.value);
      if (wasManual && curCanon && curCanon !== canon) {
      const ok = await confirmModal(
        'Nilai harga pada baris ini telah diisi manual. Terapkan hasil konversi akan mengganti nilai tersebut. Lanjutkan?',
        { title: 'Konfirmasi', confirmText: 'Lanjutkan', cancelText: 'Batal' },
      );
      if (!ok) return;
      }
    }
    if (input) { input.value = toUI(canon); input.classList.remove('ux-invalid'); }
    if (prev) { prev.textContent = rupiah(canon); }
    // Tampilkan indikator edited (kuning) untuk hasil konversi juga
    if (convCtx.tr) {
      convCtx.tr.classList.remove('hi-row-empty');
      convCtx.tr.classList.toggle('hi-row-zero', Number(canon) === 0);
      const orig = convCtx.tr.dataset.origCanon || '';
      const isDirtyRow = (orig && orig !== canon);
      setRowDirtyVisual(convCtx.tr, isDirtyRow);
      // P0 FIX: Activate save button when conversion changes value
      if (isDirtyRow) {
        setDirty(true);
      }
    }

    // WP-P1b-wiring (HI-02): STAGE the profile only — do NOT commit to a separate
    // endpoint. The conversion is persisted atomically with the page "Simpan"
    // (sent in payload.conversions), so the profile and harga_satuan can never
    // diverge. Profile is backend-keyed; the server recomputes harga_satuan.
    const unitName = ($convUnit.value === 'custom') ? ($convUnitCustom.value || 'satuan pembelian dari Supplier') : $convUnit.value;
    const prof = {
      market_unit: unitName,
      market_price: toCanon2($convPrice.value) || '',
      factor_to_base: toCanonFloat($convFactor.value, 6) || '',
      density: toCanonFloat($convDensity.value, 6) || '',
      capacity_m3: toCanonFloat($convCapM3.value, 6) || '',
      capacity_ton: toCanonFloat($convCapTon.value, 6) || '',
      method: deriveMethod(),
      base_unit: convCtx.base,
    };
    convStore.set(convCtx.id, prof);
    // This row is conversion-driven again → cancel any pending manual-override clear.
    if (convCtx.tr) convCtx.tr.dataset.clearConv = '0';
    setDirty(true);  // staged conversion must be persisted on the next page Simpan

    if (window.bootstrap && $convModal) {
      window.bootstrap.Modal.getOrCreateInstance($convModal).hide();
    }
    // Tandai baris sebagai tidak manual (diganti hasil konversi)
    if (convCtx.tr) { convCtx.tr.dataset.manualEdited = '0'; }
  });

  $convModal?.addEventListener('hidden.bs.modal', resetModal);

  function deriveMethod() {
    if ($convFactor.value && ($convCapM3.value || $convCapTon.value || $convDensity.value)) return 'hybrid';
    if ($convFactor.value) return 'direct';
    if ($convCapM3.value || $convCapTon.value || $convDensity.value) return 'calc';
    return 'unknown';
  }

  function updateHelperVisibility() {
    const unit = $convUnit.value;
    // Add null checks (wrap elements may not exist in simplified modal)
    $convCapM3Wrap?.classList.add('d-none');
    $convCapTonWrap?.classList.add('d-none');
    $convDensityWrap?.classList.add('d-none');

    // tampilkan helper sesuai unit (only if wrap elements exist)
    if (unit === 'dump_truck' || unit === 'm3') $convCapM3Wrap?.classList.remove('d-none');
    if (unit === 'ton') $convCapTonWrap?.classList.remove('d-none');

    // density hanya bila konversi volume -> massa
    const unitDim = (unit === 'm3' || unit === 'dump_truck') ? Dim.VOL : (unit === 'ton' ? Dim.MASS : Dim.OTHER);
    if (unitDim === Dim.VOL && convCtx.baseDim === Dim.MASS) $convDensityWrap?.classList.remove('d-none');

    // label unit
    setUnitLabel(unit === 'custom' ? ($convUnitCustom.value || 'satuan pembelian dari Supplier') : unit);
  }

  function autoFillFactor() {
    // hitung faktor dari parameter (jika masuk akal)
    const unit = $convUnit.value;
    let factor = '';

    if ((unit === 'dump_truck' || unit === 'm3') && convCtx.baseDim === Dim.MASS) {
      const cap = Number(toCanonFloat($convCapM3.value, 6) || 'NaN'); // m3
      const dens = Number(toCanonFloat($convDensity.value, 6) || 'NaN'); // kg/m3
      if (isFinite(cap) && cap > 0 && isFinite(dens) && dens > 0) {
        factor = String(cap * dens); // m3 * (kg/m3) = kg
      }
    } else if ((unit === 'dump_truck' || unit === 'm3') && convCtx.baseDim === Dim.VOL) {
      const cap = Number(toCanonFloat($convCapM3.value, 6) || 'NaN'); // m3
      if (isFinite(cap) && cap > 0) { factor = String(cap); } // m3 -> m3
    } else if (unit === 'ton' && convCtx.baseDim === Dim.MASS) {
      const capTon = Number(toCanonFloat($convCapTon.value, 6) || 'NaN'); // ton
      if (isFinite(capTon) && capTon > 0) {
        const base = (convCtx.base || '').toLowerCase();
        const toKg = base === 'kg' ? 1000 : 1; // asumsi: jika base kg, 1 ton = 1000 kg
        factor = String(capTon * toKg);
      }
    }
    if (factor) {
      $convFactor.value = N ? N.formatForUI(N.enforceDp(factor, 6)) : factor;
    }
  }

  function recalcConv(strict = false) {
    const price = toCanon2($convPrice.value);
    const factor = toCanonFloat($convFactor.value, 6);

    const pn = Number(price), fn = Number(factor);
    const invalid = !isFinite(pn) || pn < 0 || pn > MAX_PRICE || !isFinite(fn) || fn <= 0;
    $convApply.disabled = invalid;
    $convError?.classList.toggle('d-none', !invalid);

    if (invalid) {
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
    const unitName = ($convUnit.value === 'custom') ? ($convUnitCustom.value || 'satuan pembelian dari Supplier') : $convUnit.value;
    if ($convCapM3.value) bits.push(`${toUI2(toCanonFloat($convCapM3.value, 2))} m³`);
    if ($convCapTon.value) bits.push(`${toUI2(toCanonFloat($convCapTon.value, 2))} ton`);
    if ($convDensity.value) bits.push(`${toUI2(toCanonFloat($convDensity.value, 2))} kg/m³`);
    const factorPretty = toUI2(factor);
    const arrow = factorPretty ? ` → ${factorPretty} ${convCtx.base}` : '';
    $convHint.textContent = bits.length
      ? `Ringkasan perhitungan: ${unitName}${bits.length ? `, ` : ''}${bits.join(', ')}${arrow}`
      : '';

    return outCanon;
  }

  // ===== Init
  fetchList(HI_BOOTSTRAP);  // PERF: seed dari bootstrap SSR; null → fetch normal

  // ===== Export buttons already initialized in initUnifiedExport() IIFE above =====
  // (Removed duplicate initExportButtons function - it was causing projectId undefined error)

})();
