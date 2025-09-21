/*! harga_numeric_patch.js — format UI (koma), kirim kanonik dp=2 */
(function () {
  const N = window.Numeric;
  if (!N) return;

  // ganti selector sesuai input di halaman harga kamu:
  const ROOT = document; // atau batasi ke container spesifik
  const DP = 2;

  document.addEventListener('blur', function (e) {
    const el = e.target;
    if (!el || !el.classList) return;
    // asumsi class input harga: .harga-input (ubah bila perlu)
    if (!el.classList.contains('harga-input')) return;
    const canon = N.canonicalizeForAPI(el.value);
    el.value = canon ? N.formatForUI(N.enforceDp(canon, DP)) : '';
  }, true);

  // helper global untuk serialize payload
  window.HargaNumeric = {
    getCanonValue(el) {
      if (!el) return '';
      const canon = N.canonicalizeForAPI(el.value);
      return canon ? N.enforceDp(canon, DP) : '';
    }
  };
})();
