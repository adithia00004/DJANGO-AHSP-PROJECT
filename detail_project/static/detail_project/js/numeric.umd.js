/*! numeric.umd.js — util angka kanonik lintas halaman (idempotent) */
(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.Numeric = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var HAS_INTL = (typeof Intl !== 'undefined' && typeof Intl.NumberFormat === 'function');

  function _stripAll(s) {
    // hilangkan NBSP, spasi, underscore, dan karakter non angka/pemisah umum
    return String(s)
      .replace(/\u00A0/g, ' ')
      .replace(/\s+/g, '')
      .replace(/_/g, '')
      .replace(/[^0-9,.\-]/g, ''); // sisakan digit, koma, titik, minus
  }

  function isCanonical(s) {
    return typeof s === 'string' && /^-?\d+(\.\d+)?$/.test(s);
  }

  function canonicalizeForAPI(input) {
    if (input == null) return null;
    let s = String(input).trim();
    if (!s) return null;
    s = _stripAll(s);

    // rapikan minus: hanya boleh di depan
    if ((s.match(/-/g) || []).length > 1) s = s.replace(/-/g, '');
    if (s.includes('-') && s[0] !== '-') s = s.replace(/-/g, ''); // minus liar di tengah → buang

    const hasC = s.includes(','), hasD = s.includes('.');
    if (hasC && hasD) {
      // desimal = pemisah yang muncul TERAKHIR
      if (s.lastIndexOf(',') > s.lastIndexOf('.')) {
        s = s.replace(/\./g, '').replace(/,/g, '.'); // Eropa: . ribuan, , desimal
      } else {
        s = s.replace(/,/g, ''); // koma ribuan, titik desimal
      }
    } else if (hasC && !hasD) {
      s = s.replace(/,/g, '.'); // hanya koma → koma = desimal
    }
    // hanya titik → biarkan; tanpa pemisah → biarkan

    // validasi bentuk kanonik
    if (!/^-?\d+(\.\d+)?$/.test(s)) return null;
    return s; // contoh: "26.406"
  }

  function enforceDp(str, dp) {
    if (str == null || str === '') return '';
    if (!isCanonical(str)) {
      const canon = canonicalizeForAPI(str);
      if (!canon) return '';
      str = canon;
    }
    if (typeof dp !== 'number') return str;
    const parts = str.split('.');
    const head = parts[0];
    const tail = parts[1] || '';
    return dp > 0 ? head + '.' + (tail + '0'.repeat(dp)).slice(0, dp) : head;
  }

  function formatForUI(canon, opts) {
    opts = opts || {};
    if (canon == null || canon === '') return '';
    if (!isCanonical(canon)) {
      canon = canonicalizeForAPI(canon);
      if (!canon) return '';
    }
    if (opts.simple === true || !HAS_INTL) {
      // mode sederhana: desimal koma, tanpa ribuan
      return canon.replace('.', ',');
    }
    const maxFrac = typeof opts.maxFractionDigits === 'number'
      ? opts.maxFractionDigits
      : (canon.includes('.') ? canon.split('.')[1].length : 0);

    return new Intl.NumberFormat(opts.locale || 'id-ID', {
      useGrouping: (opts.useGrouping !== false),
      minimumFractionDigits: 0,
      maximumFractionDigits: maxFrac
    }).format(Number(canon)); // hanya untuk display!
  }

  // Backward-compat: ekspor nama lama + baru
  return {
    canonicalizeForAPI,  // parse → string kanonik untuk payload API
    enforceDp,           // padding nol (tampilan)
    formatForUI,         // tampil lokal ('id-ID' default)
    isCanonical          // helper validasi
  };
}));
