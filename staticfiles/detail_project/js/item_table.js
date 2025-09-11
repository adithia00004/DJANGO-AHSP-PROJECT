(function(){
  // CSRF helper
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }
  const csrf = getCookie('csrftoken');

  const wrap = document.getElementById('itemsWrap');
  const actions = document.getElementById('itemsActions');
  const btnSave = document.getElementById('btnSaveItems');

  function rowTpl(it, editable) {
    return `
      <tr data-id="${it.id ?? ''}">
        <td>${editable ? `
          <select class="form-select form-select-sm" data-field="kategori">
            <option value="TK" ${it.kategori==='TK'?'selected':''}>TK</option>
            <option value="BHN" ${it.kategori==='BHN'?'selected':''}>BHN</option>
            <option value="ALT" ${it.kategori==='ALT'?'selected':''}>ALT</option>
            <option value="LAIN" ${it.kategori==='LAIN'?'selected':''}>LAIN</option>
          </select>` : it.kategori}</td>
        <td>${editable ? `<input class="form-control form-control-sm" data-field="kode_item" value="${it.kode_item ?? ''}">` : (it.kode_item ?? '')}</td>
        <td>${editable ? `<input class="form-control form-control-sm" data-field="uraian_item" value="${it.uraian_item ?? ''}">` : (it.uraian_item ?? '')}</td>
        <td>${editable ? `<input class="form-control form-control-sm" data-field="satuan_item" value="${it.satuan_item ?? ''}">` : (it.satuan_item ?? '')}</td>
        <td>${editable ? `<input type="number" step="0.000001" min="0" class="form-control form-control-sm" data-field="koefisien" value="${it.koefisien ?? '0'}">` : (it.koefisien ?? '0')}</td>
        <td>${editable ? `<input type="number" step="0.01" min="0" class="form-control form-control-sm" data-field="harga_satuan" value="${it.harga_satuan ?? ''}">` : (it.harga_satuan ?? '')}</td>
        <td class="text-nowrap">${editable ? `
          <button class="btn btn-sm btn-outline-danger" data-action="delete">Hapus</button>
        ` : ''}</td>
      </tr>
    `;
  }

  function renderReference(items) {
    actions.style.display = 'none';
    wrap.innerHTML = `
      <div class="table-responsive">
        <table class="table table-sm align-middle">
          <thead><tr>
            <th>Kat</th><th>Kode Item</th><th>Uraian</th><th>Satuan</th><th>Koefisien</th><th>Harga</th><th></th>
          </tr></thead>
          <tbody>
            ${items.map(it => rowTpl(it, false)).join('')}
          </tbody>
        </table>
      </div>
      <div class="alert alert-info mt-2">Mode Referensi (read-only). Aktifkan Custom Mode untuk mengedit & mengisi harga.</div>
    `;
  }

  function renderCustom(items) {
    actions.style.display = 'flex';
    wrap.innerHTML = `
      <div class="table-responsive">
        <table class="table table-sm align-middle" id="tblItems">
          <thead><tr>
            <th>Kat</th><th>Kode Item</th><th>Uraian</th><th>Satuan</th><th>Koefisien</th><th>Harga</th><th></th>
          </tr></thead>
          <tbody>
            ${items.map(it => rowTpl(it, true)).join('')}
          </tbody>
        </table>
      </div>
      <div class="mt-2">
        <button class="btn btn-outline-secondary btn-sm" id="btnAddRow">Tambah Baris</button>
      </div>
    `;

    document.getElementById('btnAddRow').addEventListener('click', () => {
      const tbody = document.querySelector('#tblItems tbody');
      const empty = {id:null, kategori:'TK', kode_item:'', uraian_item:'', satuan_item:'', koefisien:'0', harga_satuan:''};
      tbody.insertAdjacentHTML('beforeend', rowTpl(empty, true));
    });

    // delete row
    wrap.addEventListener('click', (e) => {
      const btn = e.target.closest('[data-action="delete"]');
      if (!btn) return;
      const tr = btn.closest('tr');
      if (tr.dataset.id) {
        tr.dataset.delete = '1';
        tr.classList.add('table-danger');
        btn.disabled = true;
        btn.textContent = 'Dihapus';
      } else {
        tr.remove();
      }
    });
  }

  window.renderItemsTable = function(data){
    if (data.mode === 'reference') renderReference(data.items);
    else renderCustom(data.items);
  };

  btnSave?.addEventListener('click', async () => {
    const cur = window.DP_CURRENT;
    if (!cur || cur.mode !== 'custom') return;

    const rows = Array.from(wrap.querySelectorAll('tbody tr'));
    const items = rows.map(tr => {
      const get = (sel) => tr.querySelector(`[data-field="${sel}"]`);
      const payload = {
        id: tr.dataset.id ? Number(tr.dataset.id) : null,
        delete: tr.dataset.delete === '1' ? true : undefined,
      };
      if (!payload.delete) {
        payload.kategori = get('kategori') ? get('kategori').value : tr.children[0].textContent.trim();
        payload.kode_item = get('kode_item') ? get('kode_item').value.trim() : tr.children[1].textContent.trim();
        payload.uraian_item = get('uraian_item') ? get('uraian_item').value.trim() : tr.children[2].textContent.trim();
        payload.satuan_item = get('satuan_item') ? get('satuan_item').value.trim() : tr.children[3].textContent.trim();
        payload.koefisien  = get('koefisien') ? get('koefisien').value : tr.children[4].textContent.trim();
        payload.harga_satuan = get('harga_satuan') ? get('harga_satuan').value : tr.children[5].textContent.trim();
      }
      return payload;
    });

    try {
      const resp = await fetch(DP_ENDPOINTS.itemsUpsert, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type':'application/json', 'X-CSRFToken': csrf},
        body: JSON.stringify({ pekerjaan_id: cur.pekerjaan_id, items })
      });
      const data = await resp.json();
      if (!resp.ok || data.error) {
        alert(data.error || 'Gagal menyimpan');
        return;
      }
      // reload current items
      document.getElementById('selectPekerjaan').dispatchEvent(new Event('change'));
    } catch (err) {
      alert('Error: ' + err);
    }
  });
})();
