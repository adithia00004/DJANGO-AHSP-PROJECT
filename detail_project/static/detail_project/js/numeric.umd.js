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

  function canonicalizeForAPI(input) {
    if (input == null) return '';
    let s = String(input).trim();
    if (!s) return '';
    s = s.replace(/_/g, '').replace(/\s+/g, '');
    const hasC = s.includes(','), hasD = s.includes('.');
    if (hasC && hasD) {
      // desimal = pemisah yang MUNCUL TERAKHIR
      if (s.lastIndexOf(',') > s.lastIndexOf('.')) {
        s = s.replace(/\./g, '').replace(/,/g, '.');
      } else {
        s = s.replace(/,/g, '');
      }
    } else if (hasC) {
      s = s.replace(/\./g, '').replace(/,/g, '.');
    }
    return s;
  }

  function enforceDp(str, dp) {
    if (str == null || str === '') return '';
    const t = String(str);
    const parts = t.split('.');
    const head = parts[0];
    const tail = parts[1] || '';
    return dp > 0 ? head + '.' + (tail + '0'.repeat(dp)).slice(0, dp) : head;
  }

  function formatForUI(canon) {
    if (canon == null || canon === '') return '';
    return String(canon).replace('.', ','); // mudah untuk edit; tanpa ribuan
  }

  return {
    canonicalizeForAPI,
    enforceDp,
    formatForUI
  };
}));
