(async function () {
  const root = document.getElementById('rekap-app');
  if (!root) return;

  // standar: project_id (fallback pid untuk transisi)
  const projectId = root.dataset.projectId || root.dataset.pid;

  const tbody = document.querySelector('#rekap-table tbody');
  const gt = document.getElementById('gt');

  async function fetchJSON(url, options) {
    const res = await fetch(url, options);
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, data };
  }

  const { ok, data: js } = await fetchJSON(`/detail_project/api/project/${projectId}/rekap/`);
  if (!ok || !js.ok || !Array.isArray(js.rows)) {
    tbody.innerHTML = '<tr><td colspan="12" class="text-center text-muted">Gagal memuat</td></tr>';
    return;
  }

  let grand = 0;
  tbody.innerHTML = '';
  js.rows.forEach((r, i) => {
    grand += (r.total || 0);
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${i + 1}</td>
      <td>${r.kode ?? ''}</td>
      <td>${r.uraian ?? ''}</td>
      <td>${r.satuan ?? ''}</td>
      <td class="text-end">${fmt(r.A)}</td>
      <td class="text-end">${fmt(r.B)}</td>
      <td class="text-end">${fmt(r.C)}</td>
      <td class="text-end">${fmt(r.D)}</td>
      <td class="text-end">${fmt(r.E)}</td>
      <td class="text-end">${fmt(r.HSP)}</td>
      <td class="text-end">${fmt(r.volume)}</td>
      <td class="text-end">${fmt(r.total)}</td>`;
    tbody.appendChild(tr);
  });
  gt.textContent = fmt(grand);

  function fmt(v) {
    if (v == null) return '';
    return new Intl.NumberFormat('id-ID', { maximumFractionDigits: 3 }).format(v);
  }
})();
