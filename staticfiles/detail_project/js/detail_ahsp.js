(function () {
  const root = document.getElementById('da-app');
  if (!root) return;

  // Standar: project_id (fallback pid untuk transisi)
  const projectId = root.dataset.projectId || root.dataset.pid;

  const tbody = document.getElementById('tbody-rows');
  const sel = document.getElementById('pekerjaan-select');

  function addRow(data = {}) {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td class="row-idx"></td>
      <td><input class="form-control form-control-sm uraian" value="${data.uraian || ''}"></td>
      <td>
        <select class="form-select form-select-sm kategori">
          <option value="TK"${data.kategori==='TK'?' selected':''}>TK</option>
          <option value="BHN"${data.kategori==='BHN'?' selected':''}>BHN</option>
          <option value="ALT"${data.kategori==='ALT'?' selected':''}>ALT</option>
          <option value="LAIN"${data.kategori==='LAIN'?' selected':''}>LAIN</option>
        </select>
      </td>
      <td><input class="form-control form-control-sm kode" value="${data.kode || ''}"></td>
      <td><input class="form-control form-control-sm satuan" value="${data.satuan || ''}"></td>
      <td><input type="number" step="0.000001" min="0" class="form-control form-control-sm koef" value="${(data.koefisien ?? '')}"></td>
      <td><button class="btn btn-sm btn-outline-danger">✕</button></td>
    `;
    tr.querySelector('button').onclick = () => { tr.remove(); renum(); };
    tbody.appendChild(tr);
    renum();
  }

  function renum() {
    Array.from(tbody.children).forEach((tr, i) => tr.querySelector('.row-idx').innerText = i + 1);
  }

  document.getElementById('btn-add-row').onclick = () => addRow();

  document.getElementById('btn-save').onclick = async function () {
    const pekerjaanId = sel.value;
    const rows = Array.from(tbody.children).map(tr => {
      const uraian = (tr.querySelector('.uraian').value || '').trim();
      const kategori = tr.querySelector('.kategori').value;
      const kode = (tr.querySelector('.kode').value || '').trim();
      const satuan = (tr.querySelector('.satuan').value || '').trim();
      const koefStr = tr.querySelector('.koef').value;
      const koef = koefStr === '' ? null : parseFloat(koefStr);
      return {
        uraian,
        kategori,
        kode,
        satuan,
        koefisien: Number.isFinite(koef) ? koef : 0
      };
    });

    try {
      const res = await fetch(`/detail_project/api/project/${projectId}/detail-ahsp/${pekerjaanId}/save/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf()
        },
        credentials: 'same-origin',
        body: JSON.stringify({ rows })
      });
      const json = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = json && json.errors ? JSON.stringify(json.errors, null, 2) : 'Gagal simpan';
        alert(`❌ ${msg}`);
        return;
      }
      alert(`✅ Disimpan: ${json.saved_rows ?? 0} baris`);
    } catch (e) {
      console.error(e);
      alert('❌ Gagal simpan (network/server error).');
    }
  };

  function csrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }
})();
