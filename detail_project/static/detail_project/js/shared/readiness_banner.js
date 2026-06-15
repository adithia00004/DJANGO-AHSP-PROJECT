/* =====================================================================
   WP-B4 — Shared readiness banner builder (display-only).

   Pure function: turns the server's canonical readiness schema into a
   non-blocking advisory banner HTML string. Consumers render the verdict;
   they NEVER recompute readiness. All dynamic values are escaped.

   Pending jadwal signals are intentionally ignored here — the banner only
   ever warns about live problems and never emits a positive "all clear"
   message, so a pending (null) signal can't be mistaken for "done".

   Loaded as a classic script before consumers so the global is available
   synchronously on first page load. Tests import the file for its side effect.
   ===================================================================== */

function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (m) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[m]));
}

function buildReadinessBannerHTML(readiness) {
  if (!readiness || typeof readiness !== 'object') return null;

  const codes = (arr, key, max = 8) => {
    const list = (arr || []).map((e) => e && e[key]).filter(Boolean);
    const shown = list.slice(0, max).map(escapeHtml).join(', ');
    return list.length > max ? `${shown}, …` : shown;
  };

  const lines = [];
  const mp = readiness.missing_price || [];
  if (mp.length) {
    lines.push(`<li><strong>${mp.length}</strong> harga item belum diisi: ${codes(mp, 'kode')} <span class="text-muted">(perbaiki di Harga Items)</span></li>`);
  }
  const mv = readiness.missing_volume || [];
  if (mv.length) {
    lines.push(`<li><strong>${mv.length}</strong> pekerjaan belum punya volume: ${codes(mv, 'kode')} <span class="text-muted">(perbaiki di Volume)</span></li>`);
  }
  const enr = readiness.expansion_not_ready || [];
  if (enr.length) {
    lines.push(`<li><strong>${enr.length}</strong> sumber AHSP belum sinkron dengan hasil ekspansi <span class="text-muted">(periksa dan simpan ulang di Template AHSP)</span></li>`);
  }
  const inv = readiness.invalid_coefficient || [];
  if (inv.length) {
    lines.push(`<li><strong>${inv.length}</strong> koefisien tidak valid (negatif): ${codes(inv, 'kode')}</li>`);
  }

  if (!lines.length) return null;

  return (
    '<div class="fw-semibold mb-1"><i class="bi bi-exclamation-triangle-fill"></i> Beberapa data belum lengkap atau belum sinkron — total RAB belum dapat dianggap final:</div>' +
    `<ul class="mb-0 ps-3">${lines.join('')}</ul>`
  );
}

if (typeof globalThis !== 'undefined') {
  globalThis.ReadinessBanner = { buildReadinessBannerHTML, escapeHtml };
}
