/* =====================================================================
   Langkah 3.1 — perbaikan timeline terpandu di halaman Jadwal.

   Menggantikan tombol "Perbarui Struktur Waktu" yang dulu permanen di toolbar
   dan langsung memutasi tanpa analisis dampak. Sekarang:

     1. muncul HANYA bila server menyatakan `timeline_stale` (readiness B4);
     2. klik memanggil `timeline/preview` lebih dulu — tidak ada mutasi;
     3. user memilih dari opsi yang server nyatakan sah, dengan tabel nilai
        lama -> baru yang sama persis dengan dialog di form edit project;
     4. commit lewat `timeline/commit` dengan `schedule_revision`.

   Tidak menambah teks sinyal baru: banner readiness sudah menyebut jadwal basi,
   di sini hanya ditambahkan jalan keluarnya.

   Seluruh teks disisipkan lewat textContent, bukan innerHTML.
   ===================================================================== */
(function () {
  'use strict';

  const HOST_ID = 'kt-timeline-repair';

  function csrfToken() {
    const input = document.querySelector('[name=csrfmiddlewaretoken]');
    if (input && input.value) return input.value;
    const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]*)/);
    return match ? decodeURIComponent(match[1]) : '';
  }

  function scheduleRevision() {
    const app = document.getElementById('tahapan-grid-app');
    const raw = app && app.getAttribute('data-schedule-revision');
    const value = Number(raw);
    return Number.isFinite(value) ? value : null;
  }

  function timelinePayload(host, revision) {
    const additionalEnd = host.getAttribute('data-project-additional-end');
    const contractEnd =
      host.getAttribute('data-project-contract-end') || host.getAttribute('data-project-end');
    const payload = {
      tanggal_mulai: host.getAttribute('data-project-start'),
      schedule_revision: revision,
    };
    if (additionalEnd) {
      payload.target_field = 'tanggal_akhir_tambahan';
      payload.tanggal_akhir_tambahan = additionalEnd;
    } else {
      payload.target_field = 'tanggal_selesai';
      payload.tanggal_selesai = contractEnd;
    }
    return payload;
  }

  function post(url, payload) {
    return fetch(url, {
      method: 'POST',
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrfToken(),
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify(payload),
    }).then(async (response) => {
      const data = await response.json().catch(() => null);
      return { ok: response.ok, status: response.status, data };
    });
  }

  function notify(message, type) {
    if (typeof window.showToast === 'function') {
      window.showToast(message, type);
    } else {
      console.warn('[timeline-repair]', message);
    }
  }

  function confirmModal(message, options) {
    const modalApi = window.DP && window.DP.core && window.DP.core.modal;
    if (!modalApi || typeof modalApi.confirm !== 'function') {
      notify('Konfirmasi perubahan tidak tersedia. Silakan muat ulang halaman.', 'warning');
      return Promise.resolve(false);
    }
    return Promise.resolve(modalApi.confirm(message, options)).catch(() => false);
  }

  // --- rendering -----------------------------------------------------------

  function buildWeekTable(preview) {
    const wrapper = document.createElement('div');
    wrapper.className = 'table-responsive mt-2';

    const table = document.createElement('table');
    table.className = 'table table-sm table-bordered mb-0 small';

    const head = document.createElement('thead');
    head.className = 'table-light';
    const headRow = document.createElement('tr');
    ['Minggu', 'Tanggal lama', 'Tanggal baru', 'Rencana lama', 'Rencana baru']
      .forEach((label, index) => {
        const th = document.createElement('th');
        th.textContent = label;
        if (index >= 3) th.className = 'text-end';
        headRow.appendChild(th);
      });
    head.appendChild(headRow);
    table.appendChild(head);

    const body = document.createElement('tbody');
    (preview.weeks || []).forEach((week) => {
      const tr = document.createElement('tr');
      if (!week.exists_after) tr.className = 'table-danger';
      else if (week.changed) tr.className = 'table-warning';

      const cells = [
        `Minggu ${week.week_number}`,
        week.old_start ? `${week.old_start} – ${week.old_end}` : '—',
        week.new_start ? `${week.new_start} – ${week.new_end}` : 'tidak ada lagi',
        `${week.planned_before}%`,
        `${week.planned_after}%`,
      ];
      cells.forEach((text, index) => {
        const td = document.createElement('td');
        td.textContent = text;
        if (index >= 3) td.className = 'text-end';
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    table.appendChild(body);

    wrapper.appendChild(table);
    return wrapper;
  }

  function buildOptionCard(preview, recommended, onChoose) {
    const card = document.createElement('div');
    card.className = 'border rounded p-3 mb-3';

    const header = document.createElement('div');
    header.className = 'd-flex justify-content-between align-items-start flex-wrap gap-2';

    const info = document.createElement('div');
    const title = document.createElement('div');
    title.className = 'fw-semibold';
    title.textContent = preview.label;
    if (preview.resolution === recommended) {
      const badge = document.createElement('span');
      badge.className = 'badge bg-success ms-1';
      badge.textContent = 'Disarankan';
      title.appendChild(badge);
    }
    const help = document.createElement('div');
    help.className = 'small text-muted';
    help.textContent = preview.help;
    info.appendChild(title);
    info.appendChild(help);

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-sm ' +
      (preview.resolution === recommended ? 'btn-primary' : 'btn-outline-primary');
    button.textContent = 'Gunakan opsi ini';
    button.addEventListener('click', () => onChoose(preview, button));

    header.appendChild(info);
    header.appendChild(button);
    card.appendChild(header);

    const totals = document.createElement('div');
    totals.className = 'mt-2 small';
    const lost = Number(preview.planned_lost);
    totals.textContent =
      `Total rencana: ${preview.total_planned_before}% → ${preview.total_planned_after}%` +
      (lost > 0 ? ` (hilang ${preview.planned_lost}%)` : ' (tidak ada yang hilang)');
    if (lost > 0) totals.classList.add('text-danger', 'fw-semibold');
    card.appendChild(totals);

    card.appendChild(buildWeekTable(preview));
    return card;
  }

  function renderDialog(host, payload) {
    const previews = payload.previews || [];
    const impact = payload.impact || {};

    let panel = document.getElementById('kt-timeline-repair-panel');
    if (panel) panel.remove();

    panel = document.createElement('div');
    panel.id = 'kt-timeline-repair-panel';
    panel.className = 'card border-warning mt-2';

    const header = document.createElement('div');
    header.className = 'card-header bg-warning-subtle fw-semibold';
    header.textContent = 'Pilih cara merapikan struktur waktu';
    panel.appendChild(header);

    const bodyEl = document.createElement('div');
    bodyEl.className = 'card-body';

    if (!previews.length) {
      const note = document.createElement('div');
      note.className = 'small';
      note.textContent = impact.blocking_reason
        ? 'Struktur tidak dapat dirapikan otomatis karena ada realisasi pada ' +
          'minggu di luar rentang tanggal proyek. Perbaiki realisasi tersebut ' +
          'atau sesuaikan tanggal proyek lewat menu Edit Project.'
        : 'Tidak ada opsi yang berlaku untuk kondisi ini.';
      bodyEl.appendChild(note);
    } else {
      previews.forEach((preview) => {
        bodyEl.appendChild(
          buildOptionCard(preview, impact.recommended_resolution, (chosen, button) => {
            commit(host, chosen, payload.schedule_revision, button);
          })
        );
      });
    }

    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.className = 'btn btn-outline-secondary btn-sm';
    cancel.textContent = 'Tutup';
    cancel.addEventListener('click', () => panel.remove());
    bodyEl.appendChild(cancel);

    panel.appendChild(bodyEl);
    host.appendChild(panel);
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function renderAlert(host) {
    host.textContent = '';
    host.className = 'alert alert-warning py-2 px-3 small mb-2';
    host.setAttribute('role', 'status');

    const row = document.createElement('div');
    row.className = 'd-flex justify-content-between align-items-center flex-wrap gap-2';

    const text = document.createElement('div');
    text.textContent =
      'Struktur waktu tidak lagi sesuai rentang tanggal proyek. ' +
      'Perbaiki agar kolom minggu dan jadwal kembali sinkron.';

    const button = document.createElement('button');
    button.type = 'button';
    button.id = 'btn-repair-timeline';
    button.className = 'btn btn-warning btn-sm';
    button.textContent = 'Perbaiki Struktur Waktu';
    button.addEventListener('click', () => preview(host, button));

    row.appendChild(text);
    row.appendChild(button);
    host.appendChild(row);
  }

  // --- alur ----------------------------------------------------------------

  function preview(host, button) {
    const revision = scheduleRevision();
    button.disabled = true;
    post(host.getAttribute('data-preview-url'), timelinePayload(host, revision)).then(({ ok, data }) => {
      button.disabled = false;
      if (!ok || !data || !data.ok) {
        notify((data && data.error) || 'Gagal menganalisis struktur waktu.', 'danger');
        return;
      }
      renderDialog(host, data);
    }).catch(() => {
      button.disabled = false;
      notify('Gagal menganalisis struktur waktu.', 'danger');
    });
  }

  async function commit(host, chosen, revision, button) {
    const lost = Number(chosen.planned_lost);
    if (lost > 0) {
      const proceed = await confirmModal(
        `Opsi ini menghapus ${chosen.planned_lost}% rencana progress yang tidak ` +
        'muat di rentang tanggal proyek. Lanjutkan?',
        {
          title: 'Konfirmasi perbaikan jadwal',
          confirmText: 'Lanjutkan',
          cancelText: 'Batal',
          confirmClass: 'btn btn-danger',
        },
      );
      if (!proceed) return;
    }

    button.disabled = true;
    post(host.getAttribute('data-commit-url'), {
      ...timelinePayload(host, revision),
      resolution: chosen.resolution,
    }).then(({ ok, data }) => {
      if (!ok || !data || !data.ok) {
        button.disabled = false;
        notify((data && data.error) || 'Gagal merapikan struktur waktu.', 'danger');
        return;
      }
      notify('Struktur waktu diperbarui.', 'success');
      setTimeout(() => window.location.reload(), 1200);
    }).catch(() => {
      button.disabled = false;
      notify('Gagal merapikan struktur waktu.', 'danger');
    });
  }

  // --- init ----------------------------------------------------------------

  function onReadiness(event) {
    const host = document.getElementById(HOST_ID);
    if (!host) return;
    const readiness = event.detail || {};

    // Sinyal otoritatif server. Tidak ada perhitungan basi di sisi klien.
    if (!readiness.timeline_stale) {
      host.textContent = '';
      host.className = 'd-none';
      return;
    }
    renderAlert(host);
  }

  document.addEventListener('readiness:loaded', onReadiness);

  if (typeof window !== 'undefined') {
    window.TimelineRepair = { onReadiness, renderAlert };
  }
})();
