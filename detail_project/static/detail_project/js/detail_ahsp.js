/* ================================
   detail_ahsp.js (skeleton)
   ================================ */

(() => {
  "use strict";

  // ---------- Dom helpers ----------
  const $  = (sel, ctx = document) => ctx.querySelector(sel);
  const $$ = (sel, ctx = document) => Array.from(ctx.querySelectorAll(sel));
  const on = (el, ev, fn, opts) => el.addEventListener(ev, fn, opts);
  const ce = (tag, cls) => { const n = document.createElement(tag); if (cls) n.className = cls; return n; };

  // ---------- App root & endpoints ----------
  const app = $("#da-app");
  const PROJECT_ID = Number(app.dataset.projectId);
  const EP_HARGA   = app.dataset.endpointHargaItems; // GET list harga items in-use
  const EP_SAVE_PER_TEMPLATE = app.dataset.endpointSavePer; // .../detail-ahsp/0/save/
  const EP_SAVE_GAB = app.dataset.endpointSaveGabungan;
  const EP_REKAP    = app.dataset.endpointRekap;

  // ---------- Intl number helpers (id-ID) ----------
  const nfID = new Intl.NumberFormat("id-ID", { maximumFractionDigits: 6 });
  function parseIdNumber(input) {
    if (input == null) return NaN;
    let s = String(input).trim();
    if (!s) return NaN;
    // if contains comma, treat comma as decimal sep -> remove dots as thousands
    if (s.includes(",")) {
      s = s.replace(/\./g, "").replace(",", ".");
    } else {
      // no comma; interpret dot as decimal
      // also strip spaces/underscores
      s = s.replace(/[_\s]/g, "");
    }
    const v = Number(s);
    return Number.isFinite(v) ? v : NaN;
  }
  function formatIdNumber(v) {
    if (v == null || v === "") return "";
    const n = typeof v === "number" ? v : parseIdNumber(v);
    if (!Number.isFinite(n)) return "";
    return nfID.format(n);
  }

  // ---------- State ----------
  const state = {
    activeJobId: null,
    // Per pekerjaan: {rows: {TK:[], BHN:[], ALT:[], LAIN:[]}, dirty: false}
    jobs: new Map(),
    // Katalog HargaItemProject (in-use) cache
    catalog: {
      loaded: false,
      items: [], // {id,kode_item,kategori,uraian,satuan,harga_satuan}
      byCode: new Map(), // kode_item -> item
    },
    selection: new Set(), // DOM tr dataset.rid (row uid)
  };

  // Generate row uid
  let _ridCounter = 1;
  const genRid = () => `r${Date.now().toString(36)}_${(_ridCounter++).toString(36)}`;

  // Row shape (FE)
  // {rid, kategori, kode, uraian, satuan, koefisien:number}
  function makeRow(kat = "BHN") {
    return { rid: genRid(), kategori: kat, kode: "", uraian: "", satuan: "", koefisien: 0 };
  }

  // ---------- Initial payload from HTML ----------
  function readInitial() {
    const el = $("#da-initial");
    if (!el) return;
    try {
      const data = JSON.parse(el.textContent || "{}");
      (data.pekerjaan || []).forEach(p => {
        state.jobs.set(p.id, {
          meta: { kode: p.kode, uraian: p.uraian, satuan: p.satuan, source_type: p.source_type },
          rows: { TK: [], BHN: [], ALT: [], LAIN: [] },
          dirty: false
        });
      });
      const rmap = data.rows_by_job || {};
      Object.keys(rmap).forEach(k => {
        const pid = Number(k);
        ensureJob(pid);
        // Normalize rows by kategori
        const buckets = { TK: [], BHN: [], ALT: [], LAIN: [] };
        (rmap[k] || []).forEach(raw => {
          const kat = (raw.kategori || "").toUpperCase();
          const row = {
            rid: genRid(),
            kategori: kat,
            kode: raw.kode || "",
            uraian: raw.uraian || "",
            satuan: raw.satuan || "",
            koefisien: Number(raw.koefisien) || 0,
          };
          if (!buckets[kat]) buckets[kat] = [];
          buckets[kat].push(row);
        });
        state.jobs.get(pid).rows = buckets;
      });
    } catch (e) {
      console.warn("Failed to parse initial payload:", e);
    }
  }

  function ensureJob(jobId) {
    if (!state.jobs.has(jobId)) {
      state.jobs.set(jobId, { meta: { kode: "", uraian: "", satuan: "", source_type: "" }, rows: { TK: [], BHN: [], ALT: [], LAIN: [] }, dirty: false });
    }
    return state.jobs.get(jobId);
  }

  // ---------- Toasts ----------
  const toastsEl = $("#da-toasts");
  function toast(msg, type = "success", timeout = 4000) {
    const n = ce("div", `da-toast ${type}`);
    n.textContent = msg;
    toastsEl.appendChild(n);
    setTimeout(() => n.remove(), timeout);
  }

  // ---------- Dirty indicator ----------
  const dot = $("#da-dirty-dot"), dotText = $("#da-dirty-text");
  function setDirty(d) {
    const job = state.jobs.get(state.activeJobId);
    if (!job) return;
    job.dirty = d;
    if (d) { dot.hidden = false; dotText.hidden = false; }
    else   { dot.hidden = true;  dotText.hidden = true;  }
  }

  // ---------- Harga items (catalog) cache ----------
  async function loadCatalog() {
    if (state.catalog.loaded) return;
    try {
      const res = await fetch(EP_HARGA, { credentials: "same-origin" });
      const js = await res.json();
      const items = (js.items || []).slice();
      state.catalog.items = items;
      const map = new Map();
      items.forEach(it => { map.set(it.kode_item, it); });
      state.catalog.byCode = map;
      state.catalog.loaded = true;
    } catch (e) {
      console.warn("catalog load failed:", e);
    }
  }
  function filterCatalog(query, max = 15) {
    query = (query || "").trim().toLowerCase();
    if (!query) return [];
    const q = query;
    const out = [];
    for (const it of state.catalog.items) {
      const hay = `${it.kode_item} ${it.uraian}`.toLowerCase();
      if (hay.includes(q)) out.push(it);
      if (out.length >= max) break;
    }
    return out;
  }

  // ---------- Rendering ----------
  const segBodies = {
    TK:  $("#seg-TK-body"),
    BHN: $("#seg-BHN-body"),
    ALT: $("#seg-ALT-body"),
    LAIN:$("#seg-LAIN-body"),
  };

  const activeHead = {
    kode:   $("#da-active-kode"),
    uraian: $("#da-active-uraian"),
    satuan: $("#da-active-satuan"),
    source: $("#da-active-source .badge")
  };

  function renderActiveHeader() {
    const job = state.jobs.get(state.activeJobId);
    if (!job) {
      activeHead.kode.textContent = "—";
      activeHead.uraian.textContent = "—";
      activeHead.satuan.textContent = "—";
      activeHead.source.textContent = "—";
      return;
    }
    activeHead.kode.textContent = job.meta.kode || "—";
    activeHead.uraian.textContent = job.meta.uraian || "—";
    activeHead.satuan.textContent = job.meta.satuan || "—";
    activeHead.source.textContent = (job.meta.source_type === "ref_modified" ? "MOD" : (job.meta.source_type === "custom" ? "CUS" : "—"));
  }

  function emptyRowHTML(colspan = 5, text = "Belum ada item.") {
    const tr = ce("tr"); tr.className = "da-empty";
    const td = ce("td"); td.colSpan = colspan; td.textContent = text;
    tr.appendChild(td);
    return tr;
  }

  function rowToTr(row) {
    const tr = $("#da-row-template").content.firstElementChild.cloneNode(true);
    tr.dataset.rid = row.rid;
    tr.dataset.kategori = row.kategori;

    // Fill cells
    tr.querySelector(".row-index").textContent = "–";
    const wrap = tr.querySelector('[data-field="uraian"]');
    wrap.textContent = row.uraian || "";
    const iKode = tr.querySelector('[data-field="kode"]');
    const iSat  = tr.querySelector('[data-field="satuan"]');
    const iKoef = tr.querySelector('[data-field="koefisien"]');

    iKode.value = row.kode || "";
    iSat.value  = row.satuan || "";
    iKoef.value = formatIdNumber(row.koefisien);

    // price hint chip
    const chip = tr.querySelector(".da-need-price");
    const catItem = state.catalog.byCode.get(row.kode);
    if (catItem && (catItem.harga_satuan === null || catItem.harga_satuan === undefined)) {
      chip.hidden = false;
    } else {
      chip.hidden = true;
    }

    // handlers
    // contenteditable Uraian
    on(wrap, "input", () => { row.uraian = wrap.textContent.trim(); setDirty(true); });
    on(wrap, "blur",  () => { wrap.textContent = row.uraian; });

    // Kode / Satuan / Koef
    on(iKode, "input", () => { row.kode = iKode.value.trim(); setDirty(true); updatePriceChip(chip, row.kode); });
    on(iSat,  "input", () => { row.satuan = iSat.value.trim(); setDirty(true); });
    on(iKoef, "blur", () => {
      const v = parseIdNumber(iKoef.value);
      if (!Number.isFinite(v) || v < 0) {
        tr.classList.add("error");
      } else {
        tr.classList.remove("error");
        row.koefisien = v;
        iKoef.value = formatIdNumber(v);
        setDirty(true);
      }
    });
    on(iKoef, "input", () => { tr.classList.remove("error"); });

    // selection
    const cb = tr.querySelector(".row-select");
    on(cb, "change", () => {
      if (cb.checked) state.selection.add(row.rid); else state.selection.delete(row.rid);
    });

    // keyboard navigation within row
    const inputs = [wrap, iKode, iSat, iKoef];
    inputs.forEach(inp => on(inp, "keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const forward = !e.shiftKey;
        focusNextCell(tr, inp, forward);
      }
    }));

    // drag & drop
    tr.addEventListener("dragstart", (e) => {
      tr.classList.add("dragging");
      e.dataTransfer.setData("text/plain", row.rid);
    });
    tr.addEventListener("dragend", () => tr.classList.remove("dragging"));

    return tr;
  }

  function updatePriceChip(chip, kode) {
    const catItem = state.catalog.byCode.get(kode);
    chip.hidden = !(catItem && (catItem.harga_satuan === null || catItem.harga_satuan === undefined));
  }

  function renderSegment(seg) {
    const body = segBodies[seg];
    body.innerHTML = "";
    const job = state.jobs.get(state.activeJobId);
    if (!job || !job.rows[seg] || job.rows[seg].length === 0) {
      body.appendChild(emptyRowHTML(5, seg === "LAIN" ? "Belum ada komponen. Tambah melalui “Tambah Komponen AHSP…”." : "Belum ada item. Tambah dari katalog atau buat baris kosong."));
      return;
    }
    job.rows[seg].forEach((row, idx) => {
      const tr = rowToTr(row);
      tr.querySelector(".row-index").textContent = String(idx + 1);
      body.appendChild(tr);
    });

    // enable drop reordering
    enableDropSort(body, seg);
  }

  function renderAllSegments() {
    renderSegment("TK");
    renderSegment("BHN");
    renderSegment("ALT");
    renderSegment("LAIN");
  }

  function focusNextCell(tr, currentEl, forward) {
    const order = [tr.querySelector('[data-field="uraian"]'), tr.querySelector('[data-field="kode"]'), tr.querySelector('[data-field="satuan"]'), tr.querySelector('[data-field="koefisien"]')];
    const idx = order.findIndex(x => x === currentEl);
    let nextIdx = forward ? idx + 1 : idx - 1;
    let target = order[nextIdx];
    if (!target) {
      // move to next/prev row
      const allRows = $$("#" + tr.parentElement.id + " .da-row");
      const rIndex = allRows.indexOf(tr);
      const nextRow = allRows[forward ? rIndex + 1 : rIndex - 1];
      if (nextRow) {
        const nOrder = [nextRow.querySelector('[data-field="uraian"]'), nextRow.querySelector('[data-field="kode"]'), nextRow.querySelector('[data-field="satuan"]'), nextRow.querySelector('[data-field="koefisien"]')];
        target = nOrder[forward ? 0 : nOrder.length - 1];
      }
    }
    if (target) {
      target.focus();
      if ("select" in target) target.select?.();
    }
  }

  // ---------- Drop sorting ----------
  function enableDropSort(tbody, seg) {
    tbody.addEventListener("dragover", (e) => {
      e.preventDefault();
      const dragging = tbody.querySelector(".dragging");
      const after = getDragAfterElement(tbody, e.clientY);
      if (!dragging) return;
      if (after == null) {
        tbody.appendChild(dragging);
      } else {
        tbody.insertBefore(dragging, after);
      }
    });
    tbody.addEventListener("drop", () => {
      // Update order in state
      const job = state.jobs.get(state.activeJobId);
      if (!job) return;
      const ridOrder = $$(".da-row", tbody).map(tr => tr.dataset.rid);
      const newArr = [];
      const old = job.rows[seg];
      ridOrder.forEach(rid => {
        const found = old.find(r => r.rid === rid);
        if (found) newArr.push(found);
      });
      job.rows[seg] = newArr;
      setDirty(true);
      renderSegment(seg);
    });
  }
  function getDragAfterElement(container, y) {
    const els = [...container.querySelectorAll(".da-row:not(.dragging)")];
    return els.reduce((closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        return { offset, element: child };
      } else {
        return closest;
      }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
  }

  // ---------- Job list interactions ----------
  const jobList = $("#da-job-list");
  on(jobList, "click", (e) => {
    const li = e.target.closest(".da-job-item");
    if (!li) return;
    const id = Number(li.dataset.pekerjaanId);
    selectJob(id);
  });
  on(jobList, "keydown", (e) => {
    if (e.key === "Enter") {
      const li = e.target.closest(".da-job-item");
      if (!li) return;
      const id = Number(li.dataset.pekerjaanId);
      selectJob(id);
    }
  });

  function selectJob(jobId) {
    state.activeJobId = jobId;
    const meta = state.jobs.get(jobId)?.meta;
    // render header & segments
    renderActiveHeader();
    renderAllSegments();
    setDirty(state.jobs.get(jobId)?.dirty || false);
    // update Save endpoint template
    computeSaveUrlForActive();
    // clear selection
    state.selection.clear();
    $$("#da-job-list .da-job-item").forEach(li => li.classList.toggle("active", Number(li.dataset.pekerjaanId) === jobId));
  }

  function computeSaveUrlForActive() {
    // EP_SAVE_PER_TEMPLATE is e.g. ".../detail-ahsp/0/save/"
    // Replace "/0/save/" with `/${activeId}/save/`
    const saveBtn = $("#da-btn-save");
    let url = EP_SAVE_PER_TEMPLATE;
    if (state.activeJobId != null) {
      url = url.replace(/\/0\/save\/?$/, `/${state.activeJobId}/save/`);
    }
    saveBtn.dataset.saveUrl = url;
  }

  // ---------- Add catalog / empty rows ----------
  // Toolbar combobox
  const cbInput = $("#da-catalog-input");
  const cbList  = $("#da-catalog-listbox");
  on(cbInput, "input", async () => {
    await loadCatalog();
    const q = cbInput.value;
    const items = filterCatalog(q, 15);
    renderCBList(items);
  });
  on(cbInput, "keydown", (e) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      const first = cbList.querySelector("[role=option]");
      first?.focus();
    }
  });

  function renderCBList(items) {
    cbList.innerHTML = "";
    if (!items.length) { cbList.hidden = true; cbInput.setAttribute("aria-expanded", "false"); return; }
    items.forEach((it, idx) => {
      const li = ce("li");
      li.setAttribute("role", "option");
      li.tabIndex = 0;
      li.innerHTML = `<span class="code mono">${it.kode_item}</span><span>${it.uraian}</span><span class="desc">${it.satuan || ""}</span>`;
      on(li, "click", () => addRowFromCatalog(it));
      on(li, "keydown", (e) => {
        if (e.key === "Enter") { addRowFromCatalog(it); }
      });
      cbList.appendChild(li);
    });
    cbList.hidden = false;
    cbInput.setAttribute("aria-expanded", "true");
  }

  function addRowFromCatalog(it) {
    if (!state.activeJobId) { toast("Pilih pekerjaan dulu.", "warn"); return; }
    // target segment = last focused seg; fallback to BHN
    const seg = lastFocusedSeg || "BHN";
    const job = state.jobs.get(state.activeJobId);
    const r = makeRow(seg);
    r.kode = it.kode_item;
    r.uraian = it.uraian || "";
    r.satuan = it.satuan || "";
    r.koefisien = 0;
    job.rows[seg].push(r);
    setDirty(true);
    renderSegment(seg);
    cbList.hidden = true; cbInput.setAttribute("aria-expanded", "false"); cbInput.value = "";
  }

  // Per-segment buttons
  $$(".da-seg-add-catalog").forEach(btn => on(btn, "click", async (e) => {
    await loadCatalog();
    // Focus global combobox but set lastFocusedSeg to this seg
    lastFocusedSeg = e.currentTarget.dataset.targetSeg;
    cbInput.focus();
  }));
  $$(".da-seg-add-empty").forEach(btn => on(btn, "click", (e) => {
    const seg = e.currentTarget.dataset.targetSeg;
    if (!state.activeJobId) { toast("Pilih pekerjaan dulu.", "warn"); return; }
    const job = state.jobs.get(state.activeJobId);
    job.rows[seg].push(makeRow(seg));
    setDirty(true);
    renderSegment(seg);
  }));

  // Track last focused seg
  let lastFocusedSeg = "BHN";
  Object.entries(segBodies).forEach(([seg, body]) => {
    body.addEventListener("focusin", () => { lastFocusedSeg = seg; });
  });

  // ---------- Modal Komponen AHSP (LAIN) ----------
  const modal = $("#da-modal-component");
  const btnOpenComp = $("#da-btn-add-component");
  const tabs = $$(".tab", modal);
  const panels = $$(".tabpanel", modal);

  on(btnOpenComp, "click", () => openModal(modal));
  modal.addEventListener("click", (e) => {
    if (e.target.hasAttribute("data-modal-close") || e.target === modal) closeModal(modal);
  });
  tabs.forEach(t => on(t, "click", () => {
    tabs.forEach(x => x.classList.remove("active"));
    t.classList.add("active");
    panels.forEach(p => p.hidden = p.dataset.panel !== t.dataset.tab);
  }));

  function openModal(m) { m.hidden = false; $("#da-ref-search").focus(); }
  function closeModal(m) { m.hidden = true; clearCompForm(); }

  // Stub search (silakan ganti dengan fetch ke app referensi bila ada)
  const refResults = $("#da-ref-results");
  const refSearch  = $("#da-ref-search");
  on(refSearch, "input", () => {
    // TODO: wire ke endpoint pencarian referensi jika tersedia
    // Untuk skeleton, tampilkan contoh hasil lokal agar alur bisa diuji.
    const q = refSearch.value.trim();
    refResults.innerHTML = "";
    if (!q) return;
    const samples = [
      { id: 1001, kode: "B.2",     uraian: "1 m3 Beton f'c 15 MPa", satuan: "m³" },
      { id: 1101, kode: "B.11.a",  uraian: "1 kg Penulangan Utama", satuan: "kg" },
      { id: 1102, kode: "B.11.b",  uraian: "1 kg Penulangan Sengkang", satuan: "kg" },
      { id: 1010, kode: "B.10.c",  uraian: "1 m2 Bekisting Kolom (3x)", satuan: "m²" },
    ].filter(x => (x.kode + " " + x.uraian).toLowerCase().includes(q.toLowerCase()));
    samples.forEach(s => {
      const item = ce("div", "item");
      item.innerHTML = `<div class="code mono">${s.kode}</div><div>${s.uraian}</div><div class="unit">${s.satuan}</div>`;
      item.tabIndex = 0;
      item.role = "option";
      on(item, "click", () => fillCompFormFromRef(s));
      on(item, "keydown", (e) => { if (e.key === "Enter") fillCompFormFromRef(s); });
      refResults.appendChild(item);
    });
  });

  const compForm = $("#da-component-form");
  const compInsertBtn = $("#da-comp-insert");
  const fUraian = $("#da-comp-uraian");
  const fKode   = $("#da-comp-kode");
  const fSat    = $("#da-comp-satuan");
  const fKoef   = $("#da-comp-koef");

  function fillCompFormFromRef(row) {
    fUraian.value = row.uraian;
    fKode.value   = `COMP:REF:${row.id}`; // Semantik referensi by id
    fSat.value    = row.satuan || "";
    compInsertBtn.disabled = false;
    fKoef.focus();
  }
  function clearCompForm() {
    fUraian.value = ""; fKode.value = ""; fSat.value = ""; fKoef.value = "";
    compInsertBtn.disabled = true;
    refResults.innerHTML = "";
    refSearch.value = "";
  }

  on(compForm, "submit", () => {
    const koef = parseIdNumber(fKoef.value);
    if (!Number.isFinite(koef) || koef < 0) {
      toast("Koefisien komponen harus angka ≥ 0.", "error");
      return;
    }
    // validate code pattern
    if (!/^COMP:(REF|REFCODE|PKJ):.+$/.test(fKode.value.trim())) {
      toast("Kode komponen harus COMP:REF:… / COMP:REFCODE:… / COMP:PKJ:…", "error");
      return;
    }
    // Insert to LAIN
    if (!state.activeJobId) { toast("Pilih pekerjaan dulu.", "warn"); return; }
    const job = state.jobs.get(state.activeJobId);
    const r = makeRow("LAIN");
    r.uraian = fUraian.value.trim();
    r.kode = fKode.value.trim();
    r.satuan = fSat.value.trim();
    r.koefisien = koef;
    job.rows.LAIN.push(r);
    setDirty(true);
    renderSegment("LAIN");
    closeModal(modal);
    toast("Komponen ditambahkan.", "success");
  });

  // ---------- Save ----------
  const btnSave = $("#da-btn-save");
  on(btnSave, "click", () => saveActive());
  on(document, "keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "s") {
      e.preventDefault(); saveActive();
    }
    if (e.key === "Delete") {
      deleteSelectedRows();
    }
  });

  function gatherRowsForActive() {
    const job = state.jobs.get(state.activeJobId);
    if (!job) return [];
    const rows = [].concat(job.rows.TK, job.rows.BHN, job.rows.ALT, job.rows.LAIN);
    // Validate and map to payload shape
    const errors = [];
    const payloadRows = rows.map((r, idx) => {
      // Basic validations
      if (!r.uraian?.trim()) errors.push({ i: idx, field: "uraian", msg: "Uraian wajib" });
      if (!r.kode?.trim()) errors.push({ i: idx, field: "kode", msg: "Kode wajib" });
      if (!r.satuan?.trim()) errors.push({ i: idx, field: "satuan", msg: "Satuan wajib" });
      if (!(r.koefisien >= 0)) errors.push({ i: idx, field: "koefisien", msg: "Koefisien ≥ 0" });

      // For LAIN rows, enforce COMP:* pattern
      if (r.kategori === "LAIN" && !/^COMP:(REF|REFCODE|PKJ):.+$/.test(r.kode)) {
        // Boleh juga baris LAIN non-komponen, tapi untuk nested flow kita sarankan COMP:*
        // Tandai warning (bukan fatal). Di sini anggapkan fatal agar konsisten.
        errors.push({ i: idx, field: "kode", msg: "Baris LAIN harus Kode COMP:* (komponen)" });
      }
      return {
        kategori: r.kategori,
        kode: r.kode,
        uraian: r.uraian,
        satuan: r.satuan,
        koefisien: r.koefisien
      };
    });
    return { payloadRows, errors, rows };
  }

  async function saveActive() {
    if (!state.activeJobId) { toast("Pilih pekerjaan dulu.", "warn"); return; }
    const { payloadRows, errors, rows } = gatherRowsForActive();
    // local validation
    if (errors.length) {
      markRowErrors(errors, rows);
      toast("Periksa isian: ada kolom wajib/angka tidak valid.", "error");
      return;
    }
    const url = btnSave.dataset.saveUrl;
    if (!url) { computeSaveUrlForActive(); }
    // spinner
    const spinner = btnSave.querySelector(".spinner");
    spinner.hidden = false; btnSave.disabled = true;

    try {
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ rows: payloadRows })
      });
      const js = await res.json();
      spinner.hidden = true; btnSave.disabled = false;

      if (res.status === 200) {
        setDirty(false);
        toast("Detail AHSP tersimpan.", "success");
      } else if (res.status === 207) {
        setDirty(true);
        toast("Sebagian baris gagal disimpan (207).", "warn");
        highlightServerErrors(js.errors || [], rows);
      } else {
        setDirty(true);
        toast("Gagal menyimpan detail (400).", "error");
        highlightServerErrors(js.errors || [], rows);
      }
    } catch (e) {
      spinner.hidden = true; btnSave.disabled = false;
      toast("Jaringan/Server error saat menyimpan.", "error");
      console.error(e);
    }
  }

  function markRowErrors(errs, rows) {
    // errs: [{i, field, msg}]
    const merged = new Map();
    errs.forEach(e => merged.set(e.i, (merged.get(e.i) || []).concat(e)));
    // find TR by rid order across 4 segs (we used concat order TK,BHN,ALT,LAIN)
    const allTrs = [
      ...$("#seg-TK-body").children,
      ...$("#seg-BHN-body").children,
      ...$("#seg-ALT-body").children,
      ...$("#seg-LAIN-body").children,
    ].filter(n => n.classList.contains("da-row"));

    merged.forEach((list, idx) => {
      const tr = allTrs[idx];
      if (tr) tr.classList.add("error");
    });
  }

  function highlightServerErrors(errors, rows) {
    // Server paths like "rows[3].koefisien" -> index
    const idxSet = new Set();
    (errors || []).forEach(er => {
      const m = /\[(\d+)\]/.exec(er.path || "");
      if (m) idxSet.add(Number(m[1]));
    });
    if (!idxSet.size) return;
    const allTrs = [
      ...$("#seg-TK-body").children,
      ...$("#seg-BHN-body").children,
      ...$("#seg-ALT-body").children,
      ...$("#seg-LAIN-body").children,
    ].filter(n => n.classList.contains("da-row"));

    idxSet.forEach(i => {
      const tr = allTrs[i];
      if (tr) tr.classList.add("error");
    });
  }

  // ---------- Delete selected rows ----------
  function deleteSelectedRows() {
    if (!state.activeJobId) return;
    const job = state.jobs.get(state.activeJobId);
    if (!job) return;
    let changed = false;
    ["TK","BHN","ALT","LAIN"].forEach(seg => {
      const arr = job.rows[seg];
      const before = arr.length;
      job.rows[seg] = arr.filter(r => !state.selection.has(r.rid));
      if (job.rows[seg].length !== before) {
        renderSegment(seg);
        changed = true;
      }
    });
    if (changed) {
      state.selection.clear();
      setDirty(true);
    }
  }

  // ---------- Export CSV ----------
  $("#da-btn-export").addEventListener("click", (e) => {
    e.preventDefault();
    const job = state.jobs.get(state.activeJobId);
    if (!job) { toast("Pilih pekerjaan dulu.", "warn"); return; }
    const rows = [].concat(job.rows.TK, job.rows.BHN, job.rows.ALT, job.rows.LAIN);
    const csv = [
      ["kategori","kode","uraian","satuan","koefisien"].join(","),
      ...rows.map(r => [
        r.kategori,
        `"${(r.kode||"").replace(/"/g,'""')}"`,
        `"${(r.uraian||"").replace(/"/g,'""')}"`,
        `"${(r.satuan||"").replace(/"/g,'""')}"`,
        String(r.koefisien)
      ].join(","))
    ].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = ce("a");
    a.href = url;
    a.download = `detail_ahsp_${state.activeJobId}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  });

  // ---------- Focus management ----------
  // Restore focus to last focused cell after save (spec requirement)
  // Simple approach: keep lastFocusedElement reference
  let lastFocusedEl = null;
  document.addEventListener("focusin", (e) => { lastFocusedEl = e.target; });
  document.addEventListener("save-done", () => {
    lastFocusedEl?.focus?.();
  });

  // ---------- Init ----------
  readInitial();
  loadCatalog().then(() => {
    // render price chips properly after catalog loaded
    renderAllSegments();
  });

  // Auto-select first job
  const firstJob = $("#da-job-list .da-job-item");
  if (firstJob) selectJob(Number(firstJob.dataset.pekerjaanId));

})();
