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

function expansionIssueLabel(issue) {
  const labels = {
    missing_expansion: 'Belum diekspansi',
    stale_expansion: 'Ekspansi basi',
    incomplete_expansion: 'Ekspansi kurang',
    excess_expansion: 'Ekspansi berlebih',
  };
  return labels[issue] || issue || 'Perlu diperiksa';
}

function expansionActionLabel(issue) {
  if (issue === 'missing_expansion') return 'Buka Template AHSP, pilih pekerjaan ini, lalu simpan ulang/sinkronkan.';
  if (issue === 'stale_expansion') return 'Sumber berubah setelah ekspansi dibuat; simpan ulang/sinkronkan di Template AHSP.';
  if (issue === 'incomplete_expansion') return 'Hasil ekspansi kurang; periksa bundle/ref AHSP lalu simpan ulang.';
  if (issue === 'excess_expansion') return 'Hasil ekspansi berlebih; simpan ulang agar ekspansi dibangun ulang.';
  return 'Periksa baris ini di Template AHSP.';
}

function expansionExpectedActual(e) {
  const expected = e && e.expected;
  const actual = e && e.actual;
  if (expected === null || typeof expected === 'undefined') return escapeHtml(actual ?? '-');
  return `${escapeHtml(actual ?? 0)} / ${escapeHtml(expected)}`;
}

function expansionDetails(enr, max = 10) {
  const shown = (enr || []).slice(0, max);
  if (!shown.length) return '';
  const rows = shown.map((e) => {
    const pekerjaan = [
      e.pekerjaan_kode || `#${e.pekerjaan_id || '-'}`,
      e.pekerjaan_uraian,
    ].filter(Boolean).join(' - ');
    const komponen = [
      e.kode || `Detail #${e.source_detail_id || '-'}`,
      e.uraian,
    ].filter(Boolean).join(' - ');
    const komponenWithId = e.source_detail_id
      ? `${komponen || 'Baris AHSP'} (Detail #${e.source_detail_id})`
      : komponen;
    return (
      '<tr>' +
      `<td>${escapeHtml(pekerjaan || '-')}</td>` +
      `<td>${escapeHtml(komponenWithId || '-')}</td>` +
      `<td>${escapeHtml(expansionIssueLabel(e.issue))}</td>` +
      `<td class="text-nowrap">${expansionExpectedActual(e)}</td>` +
      `<td>${escapeHtml(expansionActionLabel(e.issue))}</td>` +
      '</tr>'
    );
  }).join('');
  const more = enr.length > max
    ? `<div class="text-muted mt-1">Menampilkan ${max} dari ${enr.length} masalah. Perbaiki dari atas, lalu refresh banner.</div>`
    : '';
  return (
    '<details class="mt-2">' +
    '<summary class="fw-semibold">Lihat detail sumber AHSP yang perlu diperbaiki</summary>' +
    '<div class="table-responsive mt-2">' +
    '<table class="table table-sm table-bordered align-middle mb-1 readiness-expansion-table">' +
    '<thead><tr><th>Pekerjaan</th><th>Baris AHSP</th><th>Masalah</th><th>Aktual/Ekspektasi</th><th>Aksi</th></tr></thead>' +
    `<tbody>${rows}</tbody>` +
    '</table>' +
    '</div>' +
    more +
    '</details>'
  );
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
    lines.push(`<li><strong>${enr.length}</strong> sumber AHSP belum sinkron dengan hasil ekspansi <span class="text-muted">(lihat detail masalah di bawah; perbaiki di Template AHSP)</span>${expansionDetails(enr)}</li>`);
  }
  // (Sinyal "koefisien negatif" dihapus — DB CheckConstraint P2a menjamin koef ≥ 0.)
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
