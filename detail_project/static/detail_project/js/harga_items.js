// harga_items.js — page script (scoped by #hi-app)
(function(){
  const ROOT = document.getElementById('hi-app');
  if (!ROOT) return;

  const N = window.Numeric || null; // util numerik (UMD)
  const DP = 2; // harga = 2 decimal places
  const locale = ROOT.dataset.locale || 'id-ID';
  const fmtRp = new Intl.NumberFormat(locale, { style: 'currency', currency: 'IDR', minimumFractionDigits: 2, maximumFractionDigits: 2 });

  const EP_LIST = (ROOT.dataset.endpointList || '') + '?canon=1'; // minta string kanonik
  const EP_SAVE = ROOT.dataset.endpointSave || '';

  const $tbody = ROOT.querySelector('#hi-tbody');
  const $filter = ROOT.querySelector('#hi-filter');
  const $btnSave = ROOT.querySelector('#hi-btn-save');
  const $btnExport = ROOT.querySelector('#hi-btn-export');
  const $stats = ROOT.querySelector('#hi-stats');
  const $bukInput = ROOT.querySelector('#hi-buk-input');

  let bukCanonLoaded = ""; // "10.00"
  function toUI2(canonStr){
    if (!N) return canonStr ?? '';
    const s = canonStr ?? '';
    if (!s) return '';
    return N.formatForUI(N.enforceDp(s, 2));
  }
  function toCanon2(inputStr){
    if (!N) return (inputStr ?? '').trim();
    const s = N.canonicalizeForAPI(inputStr ?? '');
    return s ? N.enforceDp(s, 2) : '';
  }

  const katMap = { TK: 'Tenaga', BHN: 'Bahan', ALT: 'Alat', LAIN: 'Lainnya' };
  let rows = [];        // data asal dari server
  let viewRows = [];    // referensi elemen DOM

  function csrfToken(){
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function toUI(canonStr){
    if (!N) return canonStr ?? '';
    const s = (canonStr ?? '');
    if (!s) return '';
    return N.formatForUI(N.enforceDp(s, DP)); // ganti '.' → ','; paksa 2dp
  }

  function toCanon(inputStr){
    if (!N) return (inputStr ?? '').trim();
    const s = N.canonicalizeForAPI(inputStr ?? '');
    return s ? N.enforceDp(s, DP) : '';
  }

  function rupiahFromCanon(canonStr){
    if (canonStr == null || canonStr === '') return '—';
    const num = Number(canonStr); // canonStr pakai '.' desimal → aman
    if (!isFinite(num)) return '—';
    return fmtRp.format(num);
  }

  async function fetchList(){
    setEmpty('Memuat data…');
    try{
      const res = await fetch(EP_LIST, { credentials:'same-origin' });
      const j = await res.json();
      if (!j.ok) throw new Error('Gagal memuat.');
      rows = (j.items || []).map((it, i) => ({
        idx: i+1,
        id: it.id,
        kode: it.kode_item,
        uraian: it.uraian,
        satuan: it.satuan || '',
        kategori: it.kategori,  // TK/BHN/ALT/LAIN
        harga_canon: it.harga_satuan === null ? '' : String(it.harga_satuan) // "12345.67" | ""
      }));
            // === NEW: muat BUK dari meta
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

  function renderTable(data){
    if (!data || data.length === 0){
      setEmpty('Tidak ada item harga yang digunakan di Detail AHSP.');
      return;
    }
    const fr = document.createDocumentFragment();
    viewRows = [];
    data.forEach((r, i) => {
      const tr = document.createElement('tr');
      tr.dataset.itemId = r.id;
      tr.dataset.kode = r.kode?.toLowerCase() || '';
      tr.dataset.uraian = r.uraian?.toLowerCase() || '';
      tr.dataset.kategori = r.kategori || '';

      tr.innerHTML = `
        <td class="mono">${i+1}</td>
        <td class="mono">${escapeHtml(r.kode)}</td>
        <td>${escapeHtml(r.uraian)}</td>
        <td>${escapeHtml(r.satuan)}</td>
        <td>${escapeHtml(katMap[r.kategori] || r.kategori || '')}</td>
        <td>
          <input type="text" inputmode="decimal" class="hi-input-price" value="${escapeAttr(toUI(r.harga_canon))}" aria-label="Harga satuan untuk ${escapeAttr(r.kode)}">
        </td>
        <td class="mono hi-price-preview">${escapeHtml(rupiahFromCanon(r.harga_canon))}</td>
      `;
      fr.appendChild(tr);
      viewRows.push(tr);
    });
    $tbody.innerHTML = '';
    $tbody.appendChild(fr);
    $stats.textContent = `${data.length} item`;
  }

  function escapeHtml(s){
    return (s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  }
  function escapeAttr(s){ return escapeHtml(s); }

  // Filter live
  $filter.addEventListener('input', () => {
    const q = ($filter.value || '').trim().toLowerCase();
    if (!q){
      viewRows.forEach(tr => tr.hidden = false);
      $stats.textContent = `${viewRows.length} item`;
      return;
    }
    let show = 0;
    viewRows.forEach(tr => {
      const hit = (tr.dataset.kode.includes(q) || tr.dataset.uraian.includes(q) || (katMap[tr.dataset.kategori]||'').toLowerCase().includes(q));
      tr.hidden = !hit;
      if (hit) show++;
    });
    $stats.textContent = `${show} / ${viewRows.length} item`;
  });

  // Format UI on blur + update preview
  $tbody.addEventListener('blur', (e) => {
    const el = e.target;
    if (!(el instanceof HTMLInputElement)) return;
    if (!el.classList.contains('hi-input-price')) return;
    const canon = toCanon(el.value);
    el.value = toUI(canon);
    const prev = el.closest('tr')?.querySelector('.hi-price-preview');
    if (prev) prev.textContent = rupiahFromCanon(canon);
  }, true);

  // NEW: format BUK saat blur
  $bukInput?.addEventListener('blur', () => {
    const canon = toCanon2($bukInput.value);
    // kalau kosong, kembalikan ke nilai saat load
    $bukInput.value = toUI2(canon || bukCanonLoaded);
  });

  // SAVE
  $btnSave.addEventListener('click', async () => {
    try{
      const payload = { items: [] };
      // NEW: sertakan BUK (selalu dikirim saat ada nilai)
      const mpCanon = toCanon2($bukInput?.value);
      viewRows.forEach(tr => {
        if (tr.hidden) return; // abaikan yang ter-filter? (boleh kirim semua juga)
        const id = Number(tr.dataset.itemId);
        const input = tr.querySelector('.hi-input-price');
        if (!input) return;
        const canon = toCanon(input.value);
        if (canon === '') return; // kosong → abaikan (tidak update)
        payload.items.push({ id, harga_satuan: canon });
      });
      if (mpCanon) payload.markup_percent = mpCanon;
      if (payload.items.length === 0 && (!mpCanon || mpCanon === bukCanonLoaded)){
        toast('Tidak ada perubahan untuk disimpan.', 'info');
        return;
      }
      $btnSave.disabled = true;
      $btnSave.classList.add('is-loading');

      const res = await fetch(EP_SAVE, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrfToken(),
        },
        credentials: 'same-origin',
        body: JSON.stringify(payload),
      });
      const j = await res.json();
      if (!res.ok || !j.ok){
        console.warn(j);
        toast('Sebagian gagal disimpan. Cek konsol/log.', 'warn');
      } else {
        toast(`Berhasil menyimpan ${j.updated} item.`, 'success');
      }
    }catch(e){
      console.error(e);
      toast('Gagal menyimpan harga.', 'error');
    }finally{
      $btnSave.disabled = false;
      $btnSave.classList.remove('is-loading');
      // refresh list biar preview sinkron (opsional)
      fetchList();
    }
  });

  // EXPORT CSV (sederhana)
  $btnExport.addEventListener('click', () => {
    const headers = ['No','Kode','Uraian','Satuan','Kategori','HargaSatuanCanon','HargaRupiah'];
    const lines = [headers.join(';')];
    let idx = 0;
    viewRows.forEach(tr => {
      if (tr.hidden) return;
      const kode = tr.children[1].textContent.trim();
      const uraian = tr.children[2].textContent.trim().replace(/;/g, ',');
      const satuan = tr.children[3].textContent.trim();
      const kat = tr.children[4].textContent.trim();
      const input = tr.querySelector('.hi-input-price');
      const canon = toCanon(input.value);
      const rupiah = rupiahFromCanon(canon).replace(/^Rp\s?/, 'Rp ');
      lines.push([++idx, kode, uraian, satuan, kat, canon, rupiah].join(';'));
    });
    const blob = new Blob([lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `harga_items_${(new Date()).toISOString().slice(0,10)}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  });

  // Toast minimal (tanpa dep)
  function toast(msg, level){
    // gunakan alert minimal; bisa diganti ke toasts bootstrap jika ada
    const styles = {
      success: 'background:#16a34a;color:#fff',
      error: 'background:#dc2626;color:#fff',
      warn: 'background:#f59e0b;color:#111',
      info: 'background:#0ea5e9;color:#fff'
    };
    const div = document.createElement('div');
    div.setAttribute('style', `position:fixed;right:16px;top:16px;padding:8px 12px;border-radius:8px;z-index:1100;${styles[level||'info']};box-shadow:0 2px 8px rgba(0,0,0,.15)`);
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), 2200);
  }

  // Init
  fetchList();
})();
