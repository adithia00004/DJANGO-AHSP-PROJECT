(() => {
  const app = document.getElementById("audit-app");
  if (!app) return;

  const endpoint = app.dataset.endpoint;
  const tableBody = document.getElementById("audit-table-body");
  const paginationInfo = document.getElementById("audit-pagination-info");
  const prevBtn = document.getElementById("audit-prev");
  const nextBtn = document.getElementById("audit-next");
  const alertBox = document.getElementById("audit-alert");
  const refreshBtn = document.getElementById("audit-refresh");

  const filters = {
    action: document.getElementById("filter-action"),
    trigger: document.getElementById("filter-trigger"),
    pekerjaan: document.getElementById("filter-pekerjaan"),
    dateFrom: document.getElementById("filter-date-from"),
    dateTo: document.getElementById("filter-date-to"),
  };

  let currentPage = 1;
  let hasNext = false;

  function showAlert(message, variant = "info") {
    if (!message) {
      alertBox.classList.add("d-none");
      alertBox.textContent = "";
      return;
    }
    alertBox.textContent = message;
    alertBox.className = `alert alert-${variant} mt-3`;
  }

  function getFilterParams() {
    const params = new URLSearchParams();
    if (filters.action.value) params.set("action", filters.action.value);
    if (filters.trigger.value) params.set("triggered_by", filters.trigger.value);
    if (filters.pekerjaan.value) params.set("pekerjaan_id", filters.pekerjaan.value);
    if (filters.dateFrom.value) params.set("date_from", filters.dateFrom.value);
    if (filters.dateTo.value) params.set("date_to", filters.dateTo.value);
    return params;
  }

  function formatDate(iso) {
    if (!iso) return "—";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return iso;
    return date.toLocaleString("id-ID", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }

  function renderRows(results) {
    if (!results.length) {
      tableBody.innerHTML =
        '<tr class="audit-empty"><td colspan="7" class="text-center text-muted py-4">Tidak ada data audit.</td></tr>';
      return;
    }

    tableBody.innerHTML = "";
    results.forEach((entry) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="text-nowrap">${formatDate(entry.created_at)}</td>
        <td>
          <div class="fw-semibold">${entry.pekerjaan?.kode || "-"}</div>
          <small class="text-muted">${entry.pekerjaan?.uraian || ""}</small>
        </td>
        <td><span class="badge text-bg-secondary">${entry.action}</span></td>
        <td>${entry.triggered_by}</td>
        <td>${entry.user?.username || "-"}</td>
        <td>${entry.change_summary || "-"}</td>
        <td><button class="btn btn-link btn-sm p-0 audit-detail-btn" type="button">Lihat</button></td>
      `;

      const detailBtn = tr.querySelector(".audit-detail-btn");
      const detailCell = document.createElement("td");
      detailCell.colSpan = 7;
      detailCell.classList.add("audit-diff");
      detailCell.innerHTML = `
        <div class="audit-diff">
          <details>
            <summary>Old Data</summary>
            <pre>${JSON.stringify(entry.old_data, null, 2) || "null"}</pre>
          </details>
          <details>
            <summary>New Data</summary>
            <pre>${JSON.stringify(entry.new_data, null, 2) || "null"}</pre>
          </details>
        </div>
      `;
      detailCell.style.display = "none";

      detailBtn.addEventListener("click", () => {
        const isVisible = detailCell.style.display === "table-cell";
        detailCell.style.display = isVisible ? "none" : "table-cell";
        detailCell.previousSibling?.classList?.toggle?.("table-active", !isVisible);
      });

      tableBody.appendChild(tr);
      const detailRow = document.createElement("tr");
      detailRow.appendChild(detailCell);
      tableBody.appendChild(detailRow);
    });
  }

  function updatePagination(pagination) {
    const { page, page_size, total_count } = pagination;
    currentPage = page;
    hasNext = pagination.has_next;
    const start = total_count === 0 ? 0 : (page - 1) * page_size + 1;
    const end = Math.min(page * page_size, total_count);
    paginationInfo.textContent = `Menampilkan ${start}-${end} dari ${total_count} entri`;
    prevBtn.disabled = page <= 1;
    nextBtn.disabled = !hasNext;
  }

  async function load(page = 1) {
    showAlert("");
    const params = getFilterParams();
    params.set("page", page);
    params.set("page_size", 20);

    tableBody.innerHTML =
      '<tr class="audit-empty"><td colspan="7" class="text-center text-muted py-4">Memuat data...</td></tr>';

    try {
      const response = await fetch(`${endpoint}?${params.toString()}`, {
        credentials: "same-origin",
      });
      if (!response.ok) {
        throw new Error(`Gagal memuat data (${response.status})`);
      }
      const data = await response.json();
      if (!data.ok) {
        throw new Error(data.user_message || "Gagal memuat audit trail.");
      }
      renderRows(data.results || []);
      updatePagination(data.pagination || { page: 1, page_size: 20, total_count: 0, has_next: false });
    } catch (error) {
      console.error(error);
      showAlert(error.message || "Gagal memuat audit trail.", "danger");
      tableBody.innerHTML =
        '<tr class="audit-empty"><td colspan="7" class="text-center text-muted py-4">Tidak dapat memuat data.</td></tr>';
    }
  }

  prevBtn.addEventListener("click", () => {
    if (currentPage > 1) {
      load(currentPage - 1);
    }
  });

  nextBtn.addEventListener("click", () => {
    if (hasNext) {
      load(currentPage + 1);
    }
  });

  Object.values(filters).forEach((input) => {
    input?.addEventListener("change", () => load(1));
  });

  refreshBtn.addEventListener("click", () => load(currentPage));

  load(1);
})();
