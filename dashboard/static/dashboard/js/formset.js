// dashboard/static/dashboard/js/formset.js
(function () {
  if (window.__FORMSET_INIT__) return;
  window.__FORMSET_INIT__ = true;

  document.addEventListener("DOMContentLoaded", function () {
    const addBtn = document.getElementById("add-row-btn");
    const removeBtn = document.getElementById("remove-row-btn");
    const body = document.getElementById("formset-body");
    const tpl = document.getElementById("empty-form-template");
    const dashForm = document.querySelector('form.dashboard-form');

    if (!addBtn || !body || !tpl) return;

    // ===== prefix formset =====
    let prefix = tpl.dataset.prefix;
    if (!prefix) {
      const mgmt = document.querySelector('[id$="-TOTAL_FORMS"]');
      if (mgmt) prefix = mgmt.id.replace(/^id_/, "").replace(/-TOTAL_FORMS$/, "");
    }

    const totalFormsInput = document.getElementById(`id_${prefix}-TOTAL_FORMS`);
    const initialFormsInput = document.getElementById(`id_${prefix}-INITIAL_FORMS`);
    const maxFormsInput = document.getElementById(`id_${prefix}-MAX_NUM_FORMS`);
    if (!totalFormsInput) return;

    const getTotal = () => parseInt(totalFormsInput.value || "0", 10);
    const setTotal = (n) => (totalFormsInput.value = String(n));

    // ===== Rupiah helpers (delegated) =====
    function stripRupiah(v) {
      return (v || '')
        .toString()
        .replace(/[^\d.,\-]/g, '')
        .replace(/\./g, '')
        .replace(',', '.');
    }
    function formatRupiahDisplay(input) {
      let raw = input.value || '';
      raw = raw.replace(/[^\d\-]/g, '');
      if (raw === '' || raw === '-') { input.value = raw; return; }
      const negative = raw.startsWith('-');
      if (negative) raw = raw.slice(1);
      const withDots = raw.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
      input.value = (negative ? '-' : '') + 'Rp ' + withDots;
    }

    body.addEventListener('focusin', (e) => {
      const inp = e.target;
      if (inp.matches('input[name$="-anggaran_owner"]')) {
        inp.value = stripRupiah(inp.value).replace(/\.\d+$/, '');
      }
    });
    body.addEventListener('input', (e) => {
      const inp = e.target;
      if (inp.matches('input[name$="-anggaran_owner"]')) {
        inp.value = inp.value.replace(/[^\d\-]/g, '');
      }
    });
    body.addEventListener('focusout', (e) => {
      const inp = e.target;
      if (inp.matches('input[name$="-anggaran_owner"]')) {
        formatRupiahDisplay(inp);
      }
    });

    // ===== builder row dari <template> =====
    function buildRow(index) {
      // clone isi template → node tree siap pakai
      const fragment = tpl.content ? tpl.content.cloneNode(true) : (function(){
        const tmp = document.createElement('tbody');
        tmp.innerHTML = tpl.innerHTML;
        return tmp;
      })();

      const row = fragment.querySelector('tr.formset-row');
      if (!row) return null;

      // replace __prefix__ -> index (id/name/for)
      row.querySelectorAll('*').forEach((el) => {
        ['id', 'name', 'for'].forEach((attr) => {
          if (!el.hasAttribute(attr)) return;
          const val = el.getAttribute(attr);
          if (val && val.includes('__prefix__')) {
            el.setAttribute(attr, val.replaceAll('__prefix__', index));
          }
        });
      });

      // reset nilai (kecuali hidden)
      row.querySelectorAll('input, textarea, select').forEach((input) => {
        const type = (input.getAttribute('type') || '').toLowerCase();
        if (type === 'hidden') return;
        if (type === 'checkbox' || type === 'radio') input.checked = false;
        else if (input.tagName === 'SELECT') input.selectedIndex = 0;
        else input.value = '';
      });

      // hint numerik
      row.querySelector('input[name$="-tahun_project"]')?.setAttribute('inputmode', 'numeric');
      row.querySelector('input[name$="-tahun_project"]')?.setAttribute('min', '1900');
      row.querySelector('input[name$="-tahun_project"]')?.setAttribute('max', '2100');
      row.querySelector('input[name$="-tahun_project"]')?.setAttribute('step', '1');
      row.querySelector('input[name$="-anggaran_owner"]')?.setAttribute('inputmode', 'decimal');

      return row;
    }

    function addRow() {
      const index = getTotal();
      const row = buildRow(index);
      if (!row) return;
      body.appendChild(row);
      setTotal(index + 1);
      row.querySelector("input, select, textarea")?.focus();
    }

    function bulkAddRows(n) {
      if (n <= 0) return;
      const start = getTotal();
      const frag = document.createDocumentFragment();
      for (let i = 0; i < n; i++) {
        const row = buildRow(start + i);
        if (row) frag.appendChild(row);
      }
      body.appendChild(frag);
      setTotal(start + n);
    }

    function removeLastRow() {
      const cur = getTotal();
      const minCount = Math.max(parseInt(initialFormsInput?.value || '0', 10) || 0, 1);
      if (cur <= minCount) return;
      const rows = body.querySelectorAll("tr.formset-row");
      const last = rows[rows.length - 1];
      if (!last) return;
      last.remove();
      setTotal(cur - 1);
    }

    addBtn.addEventListener("click", function (e) {
      e.preventDefault();
      const max = parseInt(maxFormsInput?.value || "100000", 10);
      if (getTotal() >= max) {
        alert("Jumlah baris sudah mencapai batas maksimum.");
        return;
      }
      addRow();
    });

    removeBtn?.addEventListener("click", function (e) {
      e.preventDefault();
      removeLastRow();
    });

    // ===== paste Excel (bulk, cepat) =====
    body.addEventListener('paste', function (e) {
      const target = e.target;
      if (!(target instanceof HTMLInputElement) &&
          !(target instanceof HTMLTextAreaElement) &&
          !(target instanceof HTMLSelectElement)) return;

      const clip = e.clipboardData || window.clipboardData;
      if (!clip) return;
      const text = clip.getData('Text');
      if (!text) return;

      const rows = text.replace(/\r/g, '').split('\n').filter(r => r.trim().length > 0);
      if (!rows.length) return;
      const table = rows.map(r => r.split('\t'));

      e.preventDefault();

      const nameAttr = target.getAttribute('name') || '';
      const match = nameAttr.match(new RegExp(`^${prefix}-(\\d+)-`));
      const startIndex = match ? parseInt(match[1], 10) : getTotal();

      const needRows = startIndex + table.length;
      const toAdd = needRows - getTotal();
      if (toAdd > 0) bulkAddRows(toAdd);

      const COLUMN_FIELDS = [
        'nama','tahun_project','sumber_dana','lokasi_project','nama_client','anggaran_owner',
        'ket_project1','ket_project2','jabatan_client','instansi_client',
        'nama_kontraktor','instansi_kontraktor',
        'nama_konsultan_perencana','instansi_konsultan_perencana',
        'nama_konsultan_pengawas','instansi_konsultan_pengawas',
      ];

      for (let r = 0; r < table.length; r++) {
        const rowIndex = startIndex + r;
        const cols = table[r];
        for (let c = 0; c < COLUMN_FIELDS.length; c++) {
          const field = COLUMN_FIELDS[c];
          const rawVal = cols[c] != null ? String(cols[c]).trim() : '';
          const input = body.querySelector(`[name="${prefix}-${rowIndex}-${field}"]`);
          if (!input) continue;

          if (field === 'anggaran_owner') {
            input.value = stripRupiah(rawVal).replace(/\.\d+$/, '');
            continue; // format saat blur/submit
          }

          if (input.tagName === 'SELECT') {
            const selEl = /** @type {HTMLSelectElement} */(input);
            const byValue = Array.from(selEl.options).find(o => (o.value || '').toLowerCase().trim() === rawVal.toLowerCase());
            if (byValue) selEl.value = byValue.value;
            else {
              const byText = Array.from(selEl.options).find(o => (o.text || '').toLowerCase().trim() === rawVal.toLowerCase());
              if (byText) selEl.value = byText.value;
            }
          } else {
            input.value = rawVal;
          }
        }
      }
    });

    // ===== normalisasi sebelum submit (strip "Rp ") =====
    if (dashForm) {
      dashForm.addEventListener('submit', function () {
        dashForm.querySelectorAll('input[name$="-anggaran_owner"]').forEach(inp => {
          const stripped = stripRupiah(inp.value).replace(/\.\d+$/, '');
          inp.value = stripped || '0';
        });
      });
    }
  });
})();
