(() => {
  const app = document.getElementById("oc-app");
  if (!app) return;

  const tableBody = document.getElementById("oc-table-body");
  const refreshBtn = document.getElementById("oc-refresh");
  const deleteBtn = document.getElementById("oc-delete");
  const deleteSpin = document.getElementById("oc-delete-spin");
  const selectAll = document.getElementById("oc-select-all");
  const alertBox = document.getElementById("oc-alert");
  const countEl = document.getElementById("oc-count");
  const totalValueEl = document.getElementById("oc-total-value");
  const selectedCountEl = document.getElementById("oc-selected-count");
  const selectedValueEl = document.getElementById("oc-selected-value");

  const listUrl = app.dataset.endpointList;
  const cleanupUrl = app.dataset.endpointCleanup;
  const currency = new Intl.NumberFormat("id-ID", {
    style: "currency",
    currency: "IDR",
    maximumFractionDigits: 2,
  });

  let rows = [];
  const selected = new Set();

  function showAlert(message, variant = "info") {
    alertBox.textContent = message;
    alertBox.className = `alert alert-${variant} mt-3`;
    if (!message) {
      alertBox.classList.add("d-none");
    } else {
      alertBox.classList.remove("d-none");
    }
  }

  function formatCurrencyString(value) {
    const num = typeof value === "number" ? value : Number(value);
    if (!Number.isFinite(num)) return "Rp 0";
    return currency.format(num);
  }

  function updateSummary() {
    countEl.textContent = rows.length;
    totalValueEl.textContent = formatCurrencyString(
      rows.reduce((acc, item) => acc + Number(item.harga_satuan || 0), 0)
    );

    const selectedRows = rows.filter((item) => selected.has(item.id));
    selectedCountEl.textContent = selectedRows.length;
    const selectedValue = selectedRows.reduce(
      (acc, item) => acc + Number(item.harga_satuan || 0),
      0
    );
    selectedValueEl.textContent = formatCurrencyString(selectedValue);

    deleteBtn.disabled = selectedRows.length === 0;
    selectAll.checked =
      rows.length > 0 && selectedRows.length === rows.length;
    selectAll.indeterminate =
      selectedRows.length > 0 && selectedRows.length < rows.length;
  }

  function renderTable() {
    if (!rows.length) {
      tableBody.innerHTML =
        '<tr class="oc-empty"><td colspan="6" class="text-center text-muted py-4">Tidak ada orphaned item 🎉</td></tr>';
      updateSummary();
      return;
    }

    tableBody.innerHTML = rows
      .map((item) => {
        const checked = selected.has(item.id) ? "checked" : "";
        const lastUsed = item.last_used
          ? new Date(item.last_used).toLocaleDateString("id-ID")
          : "—";
        return `
          <tr>
            <td>
              <input type="checkbox"
                     class="form-check-input oc-checkbox"
                     data-item-id="${item.id}"
                     ${checked}
                     aria-label="Pilih ${item.kode}">
            </td>
            <td class="font-monospace">${item.kode}</td>
            <td>
              <div>${item.uraian}</div>
              <small class="text-muted">${item.safety_note || ""}</small>
            </td>
            <td>${item.kategori}</td>
            <td>${formatCurrencyString(item.harga_satuan)}</td>
            <td>${lastUsed}</td>
          </tr>
        `;
      })
      .join("");

    tableBody.querySelectorAll(".oc-checkbox").forEach((checkbox) => {
      checkbox.addEventListener("change", (event) => {
        const id = Number(event.target.dataset.itemId);
        if (event.target.checked) {
          selected.add(id);
        } else {
          selected.delete(id);
        }
        updateSummary();
      });
    });

    updateSummary();
  }

  async function loadData() {
    showAlert("");
    tableBody.innerHTML =
      '<tr class="oc-empty"><td colspan="6" class="text-center text-muted py-4">Memuat data...</td></tr>';
    try {
      const response = await fetch(listUrl, { credentials: "same-origin" });
      if (!response.ok) {
        throw new Error(`Gagal memuat data (${response.status})`);
      }
      const data = await response.json();
      rows = data.orphaned_items || [];
      selected.clear();
      renderTable();
    } catch (error) {
      console.error(error);
      showAlert(error.message || "Gagal memuat data orphaned items.", "danger");
      tableBody.innerHTML =
        '<tr class="oc-empty"><td colspan="6" class="text-center text-muted py-4">Tidak dapat memuat data.</td></tr>';
    }
  }

  function getCsrfToken() {
    const name = "csrftoken";
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (let cookie of cookies) {
      const trimmed = cookie.trim();
      if (trimmed.startsWith(name + "=")) {
        return decodeURIComponent(trimmed.substring(name.length + 1));
      }
    }
    return "";
  }

  async function handleDelete() {
    if (!selected.size) {
      showAlert("Pilih minimal satu item untuk dihapus.", "warning");
      return;
    }

    const confirmDelete = window.confirm(
      `Hapus ${selected.size} orphaned item? Tindakan ini tidak bisa dibatalkan.`
    );
    if (!confirmDelete) {
      return;
    }

    deleteBtn.disabled = true;
    deleteSpin.hidden = false;

    try {
      const response = await fetch(cleanupUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCsrfToken(),
        },
        body: JSON.stringify({
          item_ids: Array.from(selected.values()),
          confirm: true,
        }),
      });

      const data = await response.json();
      if (!response.ok || data.ok === false) {
        throw new Error(
          (data && (data.user_message || data.message)) ||
            "Gagal menghapus orphaned items."
        );
      }

      showAlert(data.message || "Berhasil menghapus orphaned items.", "success");
      await loadData();
    } catch (error) {
      console.error(error);
      showAlert(error.message || "Gagal menghapus data.", "danger");
    } finally {
      deleteSpin.hidden = true;
      deleteBtn.disabled = selected.size === 0;
    }
  }

  refreshBtn.addEventListener("click", loadData);
  deleteBtn.addEventListener("click", handleDelete);
  selectAll.addEventListener("change", (event) => {
    if (event.target.checked) {
      rows.forEach((item) => selected.add(item.id));
    } else {
      selected.clear();
    }
    renderTable();
  });

  loadData();
})();
