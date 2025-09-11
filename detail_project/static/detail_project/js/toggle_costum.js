(function(){
  // CSRF helper
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
  }
  const csrf = getCookie('csrftoken');

  const sel = document.getElementById('selectPekerjaan');
  const wrap = document.getElementById('customToggleWrap');
  const chk = document.getElementById('toggleCustom');
  const hint = document.getElementById('toggleHint');

  if (!sel || !wrap || !chk) return;

  let currentId = null;
  let currentMode = 'reference';

  async function refreshItems() {
    if (!currentId) return;
    const url = DP_ENDPOINTS.itemsGet + `?pekerjaan_id=${currentId}`;
    const resp = await fetch(url, {credentials:'same-origin'});
    const data = await resp.json();
    window.DP_CURRENT = data;
    currentMode = data.mode;
    // tampilkan/isi tabel
    window.renderItemsTable(data);
    // tampilkan toggle
    wrap.style.display = 'block';
    chk.checked = (data.mode === 'custom');
    hint.innerText = (data.mode === 'custom')
      ? 'Mode Custom aktif. Anda bisa tambah/ubah/hapus item.'
      : 'Mode Referensi (read-only). Aktifkan Custom untuk mengedit.';
  }

  sel.addEventListener('change', () => {
    currentId = sel.value || null;
    if (!currentId) {
      wrap.style.display = 'none';
      document.getElementById('itemsWrap').innerHTML = '<div class="text-muted">Pilih pekerjaan terlebih dahulu.</div>';
      document.getElementById('itemsActions').style.display = 'none';
      return;
    }
    refreshItems();
  });

  chk.addEventListener('change', async () => {
    if (!currentId) return;
    const enable = chk.checked;

    // Jika mematikan custom dan sudah ada perubahan, server akan minta konfirmasi (409)
    async function postToggle(confirmDiscard) {
      const resp = await fetch(DP_ENDPOINTS.toggleCustom, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {'Content-Type':'application/json', 'X-CSRFToken': csrf},
        body: JSON.stringify({ pekerjaan_id: Number(currentId), enable, confirm_discard: !!confirmDiscard })
      });
      if (resp.status === 409) {
        const data = await resp.json();
        if (data.requires_confirmation) {
          if (confirm('Perubahan pada item akan dihapus dan kembali ke Referensi. Lanjutkan?')) {
            return postToggle(true);
          } else {
            chk.checked = true; // tetap custom
            return;
          }
        }
      }
      const data = await resp.json();
      if (data.error) {
        alert(data.error);
        // rollback UI
        chk.checked = !enable;
        return;
      }
      await refreshItems();
    }

    await postToggle(false);
  });

  // Auto-select jika ada query pekerjaan_id
  const url = new URL(window.location.href);
  const pre = url.searchParams.get('pekerjaan_id');
  if (pre) {
    sel.value = pre;
    sel.dispatchEvent(new Event('change'));
  }
})();
