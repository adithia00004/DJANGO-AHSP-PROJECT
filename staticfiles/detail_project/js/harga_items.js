(async function () {
  const root = document.getElementById('hi-app');
  if (!root) return;

  // Standar: project_id (fallback ke pid untuk transisi)
  const projectId = root.dataset.projectId || root.dataset.pid;

  const tbody = document.querySelector('#hi-table tbody');
  const btnSave = document.getElementById('btn-save-harga');

  const base = `/detail_project/api/project/${projectId}/`;

  async function fetchJSON(url, options) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, data };
  }

  // 1) Muat daftar harga items yang terpakai di Detail AHSP
  const { ok, data } = await fetchJSON(`${base}harga-items/list/`);
  if (ok && data && Array.isArray(data.items)) {
    tbody.innerHTML = '';
    data.items.forEach((it, i) => {
      const tr = document.createElement('tr');
      tr.dataset.id = it.id;
      tr.innerHTML = `
        <td>${i + 1}</td>
        <td>${it.kode_item}</td>
        <td>${it.kategori}</td>
        <td>${it.uraian}</td>
        <td>${it.satuan || ''}</td>
        <td><input type="number" min="0" step="0.01" class="form-control form-control-sm harga" value="${it.harga_satuan ?? ''}"></td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = `<tr><td colspan="6" class="text-muted text-center">Tidak bisa memuat data harga. Pastikan endpoint <code>harga-items/list/</code> aktif.</td></tr>`;
  }

  // (Opsional) kalau ingin memicu perhitungan rekap di server sebelum load list:
  // await fetchJSON(`${base}rekap/`); // GET, side-effect hitung rekap

  // 2) Simpan perubahan harga
  btnSave.onclick = async function () {
    const items = Array.from(tbody.children).map(tr => {
      const id = parseInt(tr.dataset.id);
      const valStr = tr.querySelector('.harga').value;
      const harga = valStr === '' ? 0 : parseFloat(valStr);
      return { id, harga_satuan: Number.isFinite(harga) ? harga : 0 };
    });

    btnSave.disabled = true;
    try {
      const { ok, data } = await fetchJSON(`${base}harga-items/save/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        credentials: 'same-origin',
        body: JSON.stringify({ items })
      });
      if (!ok) {
        alert(`❌ Gagal update harga:\n${data && data.errors ? JSON.stringify(data.errors, null, 2) : 'Server error'}`);
        return;
      }
      alert(`✅ Update harga: ${data.updated ?? 0}`);
    } catch (e) {
      console.error(e);
      alert('❌ Gagal update harga (network/server error).');
    } finally {
      btnSave.disabled = false;
    }
  };

  function csrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }
})();
