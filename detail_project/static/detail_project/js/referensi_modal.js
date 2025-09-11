(function(){
  // CSRF helper (tak dipakai untuk GET, tapi biar konsisten)
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }

  const form = document.getElementById('formSearchRef');
  const results = document.getElementById('refResults');
  if (!form || !results) return;

  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const endpoint = window.DP_ENDPOINTS && window.DP_ENDPOINTS.refSearch;
    if (!endpoint) {
      results.innerHTML = `<tr><td colspan="6" class="text-danger">Config URL pencarian hilang.</td></tr>`;
      return;
    }

    const params = new URLSearchParams(new FormData(form));
    results.innerHTML = `<tr><td colspan="6">Mencari...</td></tr>`;

    try {
      const resp = await fetch(`${endpoint}?${params.toString()}`, { credentials: 'same-origin' });

      // Guard: kalau server balas HTML (login/404), jangan parse JSON
      const ctype = resp.headers.get('content-type') || '';
      if (!resp.ok || !ctype.includes('application/json')) {
        const text = await resp.text();
        results.innerHTML = `<tr><td colspan="6" class="text-danger">Error: ${resp.status} — ${text.slice(0,120)}...</td></tr>`;
        return;
      }

      const data = await resp.json();
      if (!data.results || data.results.length === 0) {
        results.innerHTML = `<tr><td colspan="6" class="text-muted">Tidak ada hasil.</td></tr>`;
        return;
      }

      results.innerHTML = data.results.map(r => `
        <tr>
          <td>${r.kode_ahsp}</td>
          <td>${r.nama_ahsp}</td>
          <td>${r.klasifikasi ?? ''}</td>
          <td>${r.sub_klasifikasi ?? ''}</td>
          <td>${r.satuan ?? ''}</td>
          <td class="text-end">
            <form method="post">
              <input type="hidden" name="csrfmiddlewaretoken" value="${getCookie('csrftoken') || ''}">
              <input type="hidden" name="action" value="add_ref">
              <input type="hidden" name="ref_ahsp_id" value="${r.id}">
              <button class="btn btn-sm btn-primary">Pilih</button>
            </form>
          </td>
        </tr>
      `).join('');
    } catch (err) {
      results.innerHTML = `<tr><td colspan="6" class="text-danger">Error: ${err}</td></tr>`;
    }
  });
})();
