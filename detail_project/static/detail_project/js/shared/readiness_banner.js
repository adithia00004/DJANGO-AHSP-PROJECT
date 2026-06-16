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
  // CUSTOM master reference sync (B7b) — advisory: a newer corrected version of
  // the chosen master AHSP exists; user can sync in Template AHSP.
  const rua = readiness.reference_update_available || [];
  if (rua.length) {
    lines.push(`<li><strong>${rua.length}</strong> bundle memakai versi master AHSP lama: ${codes(rua, 'kode')} <span class="text-muted">(sinkronkan di Template AHSP)</span></li>`);
  }
  // Jadwal-derived signals (live since inc-4a).
  const awv = readiness.allocation_without_volume || [];
  if (awv.length) {
    lines.push(`<li><strong>${awv.length}</strong> pekerjaan dijadwalkan tanpa volume: ${codes(awv, 'kode')} <span class="text-muted">(isi Volume atau perbaiki Jadwal)</span></li>`);
  }
  const ipa = readiness.incomplete_planned_allocation || [];
  if (ipa.length) {
    lines.push(`<li><strong>${ipa.length}</strong> pekerjaan jadwalnya belum 100%: ${codes(ipa, 'kode')} <span class="text-muted">(lengkapi di Jadwal)</span></li>`);
  }
  if (readiness.timeline_stale) {
    lines.push('<li>Jadwal tidak sesuai rentang tanggal proyek <span class="text-muted">(perlu regenerasi di Jadwal)</span></li>');
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
