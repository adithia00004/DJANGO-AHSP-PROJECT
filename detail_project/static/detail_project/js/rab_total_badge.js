/**
 * Badge total RAB — menyegarkan nilainya setelah save berhasil.
 *
 * Nilai pertama datang dari SSR (lihat _rab_total_badge.html), jadi modul ini
 * tidak melakukan fetch saat halaman dibuka. Ia hanya menunggu event
 * `dp:saved`, yang di-dispatch halaman Volume / Harga Items / Template AHSP
 * ketika penyimpanan benar-benar sukses.
 *
 * Angka yang ditampilkan adalah nilai pembulatan (sudah termasuk PPN), dihitung
 * di server oleh compute_rab_grand_total() supaya identik dengan footer halaman
 * Rekap RAB. Rumusnya sengaja tidak disalin ke sini — salinan pasti menyimpang.
 */
(function () {
  'use strict';

  const el = document.querySelector('[data-rab-total]');
  if (!el) return;

  const valueEl = el.querySelector('[data-rab-total-value]');
  const endpoint = el.dataset.endpoint;
  if (!valueEl || !endpoint) return;

  const fmt = new Intl.NumberFormat('id-ID', { maximumFractionDigits: 0 });

  let inFlight = false;

  async function refresh() {
    // Save beruntun bisa memicu beberapa event sekaligus; satu permintaan cukup.
    if (inFlight) return;
    inFlight = true;
    try {
      const res = await fetch(endpoint, {
        method: 'GET',
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' },
      });
      if (!res.ok) return;

      const data = await res.json();
      if (!data || data.ok !== true) return;

      valueEl.textContent = 'Rp ' + fmt.format(Number(data.rounded_total));
      el.title =
        'Total RAB termasuk PPN ' + data.ppn_percent + '%, ' +
        'dibulatkan ke kelipatan Rp ' + fmt.format(Number(data.rounding_base));
    } catch (err) {
      // Badge ini pelengkap tampilan. Gagal menyegarkan tidak boleh mengganggu
      // alur simpan yang baru saja berhasil; angka lama tetap tampil.
    } finally {
      inFlight = false;
    }
  }

  document.addEventListener('dp:saved', refresh);

  // Titik masuk manual untuk alur simpan yang belum memakai event bus.
  const DP = (window.DP = window.DP || {});
  DP.refreshRabTotal = refresh;
})();
