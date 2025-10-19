/*! volume_numeric_patch.js — aman, tidak override handler-mu */
(function () {
  const N = window.Numeric;
  if (!N) return; // aman jika numeric belum dimuat

  const ROOT = document.getElementById('vol-app');
  if (!ROOT) return;

  const DP = 3; // volume = 3 dp

  function canonFromUIQty(raw){
    let s = String(raw ?? '').trim();
    if (!s) return '';
    s = s.replace(/\u00A0/g,' ').replace(/\s+/g,'').replace(/_/g,'');
    const hasDot = s.includes('.');
    const hasComma = s.includes(',');
    if (hasDot && !hasComma){
      const dotGrouping = /^\d{1,3}(\.\d{3})+$/;
      if (dotGrouping.test(s)) s = s.replace(/\./g, '');
    } else if (hasComma && !hasDot){
      const commaGrouping = /^\d{1,3}(,\d{3})+$/;
      if (commaGrouping.test(s)) s = s.replace(/,/g, '');
      else s = s.replace(/,/g, '.');
    } else if (hasDot && hasComma){
      const lastComma = s.lastIndexOf(',');
      const lastDot = s.lastIndexOf('.');
      if (lastComma > lastDot){
        s = s.replace(/\./g, '').replace(/,/g, '.');
      } else {
        s = s.replace(/,/g, '');
      }
    }
    // valid kanonik sederhana
    if (!/^\-?\d+(\.\d+)?$/.test(s)) return '';
    return s;
  }

  // Format UI on blur (idempotent)
  document.addEventListener('blur', function (e) {
    const el = e.target;
    if (!el || !el.classList || !el.classList.contains('qty-input')) return;
    if (!ROOT.contains(el)) return;
    // Jangan menyentuh input dalam mode formula
    const raw = String(el.value || '').trim();
    if (raw.startsWith('=')) return;
    const canon = canonFromUIQty(el.value);
    if (canon === '') { el.value = ''; return; }
    el.value = N.formatForUI(N.enforceDp(canon, DP));
  }, true);

  // Helper global untuk dipanggil saat men-serialize payload
  window.VolumeNumeric = {
    /** kembalikan string kanonik dp=3 untuk sebuah input qty */
    getCanonValue(el) {
      if (!el) return '';
      const raw = String(el.value || '').trim();
      if (raw.startsWith('=')) return ''; // formula tidak dikonversi ke angka murni
      const canon = canonFromUIQty(el.value);
      return canon ? N.enforceDp(canon, DP) : '';
    },
    /** memaksa isi input menjadi tampilan lokal (koma) dp=3 */
    canonizeInputEl(el) {
      if (!el) return;
      const raw = String(el.value || '').trim();
      if (raw.startsWith('=')) return; // biarkan formula apa adanya
      const canon = canonFromUIQty(el.value);
      el.value = canon ? N.formatForUI(N.enforceDp(canon, DP)) : '';
    }
  };
})();
