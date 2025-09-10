// /static/detail_project/js/core/format.js
(() => {
  const DP = (window.DP = window.DP || {}); 
  DP.core = DP.core || {};
  if (DP.core.format) return;

  // ---- ENV / Guard ----
  const hasIntl = typeof Intl !== 'undefined' && !!Intl.NumberFormat;

  // ---- Helpers ----
  // Rounding HALF_UP yang stabil untuk dp desimal.
  function roundHalfUp(num, dp = 0) {
    if (!isFinite(num)) return NaN;
    const f = Math.pow(10, dp);
    // Hindari artefak float, pakai toFixed setelah round
    const r = Math.round((num + Number.EPSILON) * f) / f;
    // Pastikan presisi dp dengan toFixed lalu cast balik number
    return dp > 0 ? Number(r.toFixed(dp)) : Math.round(r);
  }

  // Intl formatter id-ID fleksibel
  function makeIdFormatter(minDp = 0, maxDp = 2) {
    if (hasIntl) {
      return new Intl.NumberFormat('id-ID', { minimumFractionDigits: minDp, maximumFractionDigits: maxDp });
    }
    // Fallback manual sederhana (tanpa grouping kompleks, tetap konsisten)
    return {
      format(n) {
        if (!isFinite(n)) return '';
        const parts = n.toFixed(Math.max(minDp, Math.min(maxDp, 20))).split('.');
        const int = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.');
        const frac = parts[1] ? ',' + parts[1].replace(/0+$/,'') : '';
        return (frac === ',' ? int + ',0' : int + frac);
      }
    };
  }

  // ---- Parsing ----
  /**
   * parseId(str) → number
   * - Terima "1.234,56", "1 234,56", "1 234,56" (NBSP), "1_234,56"
   * - Hilangkan titik ribuan, spasi/NBSP/underscore, koma→titik
   * - Jika string merupakan formula (diawali "=") → NaN (biar FE formula-engine yang urus)
   * - Kosong/null/undefined → 0 (kompat lama)
   */
  function parseId(input) {
    if (typeof input === 'number') return input;
    if (input === null || input === undefined) return 0;
    let s = String(input).trim();

    // Formula → biarkan engine formula yang menangani
    if (s.startsWith('=')) return NaN;

    // Normalisasi whitespace umum (space, NBSP \u00A0, thin \u2009, dsb) & underscore
    s = s.replace(/[\s\u00A0\u2000-\u200A\u202F\u205F\u3000_]/g, '');

    // Ubah ribuan dan decimal: hapus titik sebagai ribuan, koma→titik
    s = s.replace(/\./g, '').replace(',', '.');

    // Tangani tanda negatif bila ada spasi sebelumnya (mis "- 123" setelah trim spasi khusus)
    s = s.replace(/^-\s*/, '-');

    const n = Number(s);
    if (Number.isNaN(n)) return 0; // kompat lama: fallback 0
    return n;
  }

  // ---- Formatting untuk UI id-ID ----
  /**
   * toId(num, { dp }) → string id-ID
   * - Jika dp ditentukan → min=max=dp
   * - Jika tidak → default min 0, max 2
   */
  function toId(num, opts = {}) {
    if (!isFinite(num)) return '';
    const dp = typeof opts.dp === 'number' ? Math.max(0, opts.dp) : null;
    const f = dp !== null ? makeIdFormatter(dp, dp) : makeIdFormatter(0, 2);
    return f.format(num);
  }

  /**
   * toId3(num) → string id-ID 3 desimal, pembulatan HALF_UP
   * - Dipakai di Volume
   */
  function toId3(num) {
    if (!isFinite(num)) return '';
    const r = roundHalfUp(num, 3);
    const f = makeIdFormatter(3, 3);
    return f.format(r);
  }

  // ---- “Angka bersih” untuk kirim ke server ----
  /**
   * toServer(num, dp=null) → number
   * - Jika dp diberikan → bulatkan HALF_UP ke dp
   * - Jika dp null → kembalikan apa adanya (as number)
   */
  function toServer(num, dp = null) {
    if (!isFinite(num)) return NaN;
    return (typeof dp === 'number') ? roundHalfUp(num, Math.max(0, dp)) : num;
  }

  // ---- Backward compatibility exports ----
  // nf & fmt: jaga kompat lama (tanpa memaksa dp = 3)
  const nf = makeIdFormatter(0, 3);
  function fmt(num, maxDp = 3) {
    const f = makeIdFormatter(0, maxDp);
    return f.format(num);
  }

  DP.core.format = {
    // lama (kompat)
    nf, fmt, parseId,
    // baru (disarankan dipakai kedepan)
    toId, toId3, toServer, roundHalfUp
  };
})();
