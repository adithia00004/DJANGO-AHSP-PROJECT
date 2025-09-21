// static/detail_project/js/rekap_kebutuhan.js
(function () {
  const $ = (s, c=document) => c.querySelector(s);
  const app = $('#rk-app');
  if (!app) return;

  const endpoint = app.dataset.endpoint;
  const endpointExport = app.dataset.endpointExport; // boleh kosong
  if (!endpoint) {
    console.error('[rk] data-endpoint kosong pada #rk-app');
    return;
  }

  const tbody    = $('#rk-tbody') || $('#rk-table tbody');
  const emptyEl  = $('#rk-empty');
  const loadingEl= $('#rk-loading');

  const countTK  = $('#rk-count-TK');
  const countBHN = $('#rk-count-BHN');
  const countALT = $('#rk-count-ALT');
  const countLAIN= $('#rk-count-LAIN');
  const nrowsEl  = $('#rk-nrows');
  const genEl    = $('#rk-generated');

  const btnExport = $('#rk-btn-export');

  // Sembunyikan tombol export jika endpoint export tidak tersedia
  if (!endpointExport && btnExport) {
    btnExport.classList.add('d-none');
  }

  function setLoading(v){
    if (loadingEl) loadingEl.classList.toggle('d-none', !v);
  }
  function setEmpty(v){
    if (emptyEl) emptyEl.classList.toggle('d-none', !v);
  }

  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, c => (
    { '&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;' }[c]
  ));

  function renderRows(rows){
    if (!tbody) return;
    // rapi: sort by kategori, lalu kode
    rows.sort((a,b) =>
      (a.kategori||'').localeCompare(b.kategori||'') ||
      (a.kode||'').localeCompare(b.kode||'')
    );

    if (!rows.length){
      tbody.innerHTML = '';
      setEmpty(true);
      return;
    }
    setEmpty(false);

    const frag = document.createDocumentFragment();
    rows.forEach(r=>{
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="text-nowrap">${esc(r.kategori)}</td>
        <td class="text-nowrap mono">${esc(r.kode)}</td>
        <td>${esc((r.uraian||'').replace(/\r?\n/g,' '))}</td>
        <td class="text-nowrap">${esc(r.satuan)}</td>
        <td class="text-end mono">${esc(r.quantity ?? '')}</td>
      `;
      frag.appendChild(tr);
    });
    tbody.innerHTML = '';
    tbody.appendChild(frag);
  }

  function renderMeta(meta, rows){
    // Jika server tidak kirim meta, hitung lokal dari rows
    const counts = {TK:0, BHN:0, ALT:0, LAIN:0};
    let nrows = 0;
    let generated = '';

    if (meta && meta.counts_per_kategori){
      const m = meta.counts_per_kategori;
      counts.TK   = m.TK   || 0;
      counts.BHN  = m.BHN  || 0;
      counts.ALT  = m.ALT  || 0;
      counts.LAIN = m.LAIN || 0;
      nrows = meta.n_rows ?? (rows ? rows.length : 0);
      generated = meta.generated_at || '';
    } else if (Array.isArray(rows)) {
      rows.forEach(r=>{
        if (r.kategori && counts.hasOwnProperty(r.kategori)) counts[r.kategori]++;
      });
      nrows = rows.length;
    }

    if (countTK)  countTK.textContent  = counts.TK;
    if (countBHN) countBHN.textContent = counts.BHN;
    if (countALT) countALT.textContent = counts.ALT;
    if (countLAIN)countLAIN.textContent= counts.LAIN;
    if (nrowsEl)  nrowsEl.textContent  = nrows;
    if (genEl)    genEl.textContent    = generated ? `· ${generated}` : '';
  }

  async function load(){
    setLoading(true);
    try {
      const resp = await fetch(endpoint, {credentials: 'same-origin'});
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const js = await resp.json();
      const rows = js.rows || [];
      renderRows(rows);
      renderMeta(js.meta, rows);
    } catch(e){
      console.error('[rk] gagal ambil data:', e);
      if (tbody) tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">Gagal memuat data.</td></tr>`;
      setEmpty(false);
    } finally {
      setLoading(false);
    }
  }

  if (btnExport && endpointExport){
    btnExport.addEventListener('click', ()=>{
      window.open(endpointExport, '_blank');
    });
  }

  load();
})();
