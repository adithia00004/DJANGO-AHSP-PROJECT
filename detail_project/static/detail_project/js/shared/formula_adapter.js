(function () {
  const G = (typeof window !== 'undefined') ? window : globalThis;

  function evaluate(raw, paramSnapshot, options) {
    const text = String(raw || '').trim();
    if (!text) {
      return { ok: false, code: 'empty_formula', error: 'Formula kosong' };
    }
    if (!text.startsWith('=')) {
      return { ok: false, code: 'not_formula', error: 'Formula harus diawali tanda = ' };
    }
    if (!G.VolFormula || typeof G.VolFormula.evaluate !== 'function') {
      return { ok: false, code: 'engine_unavailable', error: 'Formula engine tidak tersedia' };
    }

    const min = Number(options && options.min);
    const max = Number(options && options.max);
    const hasMin = Number.isFinite(min);
    const hasMax = Number.isFinite(max);

    try {
      const value = G.VolFormula.evaluate(text, paramSnapshot || {});
      if (!Number.isFinite(value)) {
        return { ok: false, code: 'nan_result', error: 'Hasil formula tidak valid' };
      }
      if ((hasMin && value < min) || (hasMax && value > max)) {
        return {
          ok: false,
          code: 'out_of_range',
          error: `Hasil formula di luar range (${hasMin ? min : '-inf'} s/d ${hasMax ? max : '+inf'})`,
        };
      }
      return { ok: true, value };
    } catch (err) {
      const message = (err && err.message) ? err.message : 'Gagal evaluasi formula';
      const isMissingIdentifier = (
        (/identifier/i.test(message) && /tidak ditemukan/i.test(message))
        || /variabel tidak dikenal/i.test(message)
        || /unknown variable/i.test(message)
      );
      return {
        ok: false,
        code: isMissingIdentifier ? 'missing_identifier' : 'eval_error',
        error: message,
      };
    }
  }

  G.FormulaAdapter = { evaluate };
})();
