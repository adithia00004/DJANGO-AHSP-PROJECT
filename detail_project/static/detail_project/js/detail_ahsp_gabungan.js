(function(){
  const root = document.getElementById('dag-app');
  if (!root) return;

  // Standar: project_id (fallback: pid untuk transisi)
  const projectId = root.dataset.projectId || root.dataset.pid;

  const sel = document.getElementById('pkj-multi');
  const tbody = document.querySelector('#dag-table tbody');

  document.getElementById('btn-save-dag').onclick = async function(){
    // Kumpulkan semua baris per pekerjaan
    const groups = {};
    Array.from(tbody.children).forEach(tr => {
      const pkj = parseInt(tr.dataset.pkj);
      if (!pkj || Number.isNaN(pkj)) return;

      const kategori = tr.querySelector('.kat').value;
      const kode = (tr.querySelector('.kode').value || '').trim();
      const uraian = (tr.querySelector('.uraian').value || '').trim();
      const satuan = (tr.querySelector('.sat').value || '').trim();
      const koefStr = tr.querySelector('.koef').value;
      const koef = koefStr === '' ? null : parseFloat(koefStr);

      // Skip baris kosong total
      if (!kode && !uraian) return;

      groups[pkj] = groups[pkj] || [];
      groups[pkj].push({
        kategori: kategori,                 // 'TK' | 'BHN' | 'ALT' | 'LAIN'
        kode: kode,                         // wajib di server
        uraian: uraian,                     // wajib di server
        satuan: satuan || null,             // opsional
        koefisien: Number.isFinite(koef) ? koef : 0
      });
    });

    const items = Object.entries(groups).map(([pkj, rows]) => ({
      pekerjaan_id: parseInt(pkj),
      rows
    }));

    try {
      const res = await fetch(`/detail_project/api/project/${projectId}/detail-ahsp/save/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': csrf()
        },
        credentials: 'same-origin',
        body: JSON.stringify({ items })
      });

      const js = await res.json().catch(() => ({}));
      if (!res.ok) {
        const msg = js && js.errors ? JSON.stringify(js.errors, null, 2) : 'Gagal simpan';
        alert(`❌ ${msg}`);
        return;
      }
      alert(`✅ Disimpan: ${js.saved_rows ?? 0} baris`);
    } catch (e) {
      console.error(e);
      alert('❌ Gagal simpan (network/server error).');
    }
  };

  // (Opsional) tambahkan UI untuk memuat baris dari pekerjaan terpilih
  if (sel) {
    sel.onchange = function(){
      const ids = Array.from(sel.selectedOptions).map(o => parseInt(o.value)).filter(Boolean);
      tbody.innerHTML = '';
      ids.forEach(id => addRow(id));
    };
  }

  function addRow(pkj, data = {}) {
    const tr = document.createElement('tr');
    tr.dataset.pkj = pkj;
    tr.innerHTML = `
      <td>${pkj}</td>
      <td>
        <select class="form-select form-select-sm kat">
          <option value="TK"${(data.kategori==='TK')?' selected':''}>TK</option>
          <option value="BHN"${(data.kategori==='BHN')?' selected':''}>BHN</option>
          <option value="ALT"${(data.kategori==='ALT')?' selected':''}>ALT</option>
          <option value="LAIN"${(data.kategori==='LAIN')?' selected':''}>LAIN</option>
        </select>
      </td>
      <td><input class="form-control form-control-sm kode" value="${data.kode || ''}"></td>
      <td><input class="form-control form-control-sm uraian" value="${data.uraian || ''}"></td>
      <td><input class="form-control form-control-sm sat" value="${data.satuan || ''}"></td>
      <td><input type="number" min="0" step="0.000001" class="form-control form-control-sm koef" value="${(data.koefisien ?? '')}"></td>
    `;
    tbody.appendChild(tr);
  }

  function csrf() {
    const m = document.cookie.match(/csrftoken=([^;]+)/);
    return m ? m[1] : '';
  }
})();
