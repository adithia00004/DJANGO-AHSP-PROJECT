/*! volume_numeric_patch.js — aman, tidak override handler-mu */
(function () {
  const N = window.Numeric;
  if (!N) return; // aman jika numeric belum dimuat

  const ROOT = document.getElementById('vol-app');
  if (!ROOT) return;

  const DP = 3; // volume = 3 dp

  // Format UI on blur (idempotent)
  document.addEventListener('blur', function (e) {
    const el = e.target;
    if (!el || !el.classList || !el.classList.contains('qty-input')) return;
    if (!ROOT.contains(el)) return;
    const canon = N.canonicalizeForAPI(el.value);
    if (canon === '') { el.value = ''; return; }
    el.value = N.formatForUI(N.enforceDp(canon, DP));
  }, true);

  // Helper global untuk dipanggil saat men-serialize payload
  window.VolumeNumeric = {
    /** kembalikan string kanonik dp=3 untuk sebuah input qty */
    getCanonValue(el) {
      if (!el) return '';
      const canon = N.canonicalizeForAPI(el.value);
      return canon ? N.enforceDp(canon, DP) : '';
    },
    /** memaksa isi input menjadi tampilan lokal (koma) dp=3 */
    canonizeInputEl(el) {
      if (!el) return;
      const canon = N.canonicalizeForAPI(el.value);
      el.value = canon ? N.formatForUI(N.enforceDp(canon, DP)) : '';
    }
  };
})();
