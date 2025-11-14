(() => {
  const indicators = document.querySelectorAll(".dp-sync-indicator");
  if (!indicators.length) return;

  const POLL_INTERVAL_MS = 30000;

  function parseTs(value) {
    if (!value) return 0;
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? 0 : date.getTime();
  }

  function formatMessage(hasChanges, targetLabel) {
    if (hasChanges) {
      return `⚠️ ${targetLabel} berubah. Silakan refresh.`;
    }
    return `✅ ${targetLabel} tersinkron.`;
  }

  function acknowledge(indicator, payload) {
    if (payload?.ahsp_changed_at) {
      indicator.dataset.lastSeenAhsp = payload.ahsp_changed_at;
    }
    if (payload?.harga_changed_at) {
      indicator.dataset.lastSeenHarga = payload.harga_changed_at;
    }
    indicator.dataset.lastSeenPekerjaan = new Date().toISOString();
    updateIndicator(indicator, payload);
  }

  function updateIndicator(indicator, payload) {
    const badge = indicator.querySelector(".dp-sync-indicator__badge");
    const message = indicator.querySelector(".dp-sync-indicator__message");
    if (!badge || !message) return;

    const scope = indicator.dataset.scope || "global";
    const watch = indicator.dataset.watch || "both";
    const lastSeenHarga = parseTs(indicator.dataset.lastSeenHarga || indicator.dataset.initialHarga);
    const lastSeenAhsp = parseTs(indicator.dataset.lastSeenAhsp || indicator.dataset.initialAhsp);
    const hargaChanged = parseTs(payload?.harga_changed_at) > lastSeenHarga;
    const ahspChanged = parseTs(payload?.ahsp_changed_at) > lastSeenAhsp;

    let hasChanges = false;
    let targetLabel = "";

    if (watch === "harga") {
      hasChanges = hargaChanged;
      targetLabel = "Harga Items";
    } else if (watch === "ahsp") {
      hasChanges = ahspChanged;
      targetLabel = "Template AHSP";
    } else {
      hasChanges = hargaChanged || ahspChanged || (payload?.affected_pekerjaan_count || 0) > 0;
      targetLabel = "Data terkait";
    }

    badge.classList.toggle("text-bg-danger", hasChanges);
    badge.classList.toggle("text-bg-success", !hasChanges);
    message.textContent = formatMessage(hasChanges, targetLabel);
    indicator.dataset.hasChanges = hasChanges ? "true" : "false";

    if (
      hasChanges &&
      indicator.dataset.autoEnabled === "true" &&
      indicator.dataset.autoRefreshing !== "true"
    ) {
      indicator.dataset.autoRefreshing = "true";
      setTimeout(() => {
        window.location.reload();
      }, 500);
    }
  }

  async function pollIndicator(indicator) {
    const endpoint = indicator.dataset.endpoint;
    if (!endpoint) return;

    const params = new URLSearchParams();
    if (indicator.dataset.lastSeenAhsp) {
      params.set("since_ahsp", indicator.dataset.lastSeenAhsp);
    }
    if (indicator.dataset.lastSeenHarga) {
      params.set("since_harga", indicator.dataset.lastSeenHarga);
    }
    if (indicator.dataset.lastSeenPekerjaan) {
      params.set("pekerjaan_since", indicator.dataset.lastSeenPekerjaan);
    }

    try {
      const response = await fetch(`${endpoint}?${params.toString()}`, {
        credentials: "same-origin",
      });
      if (!response.ok) throw new Error(`Status ${response.status}`);
      const data = await response.json();
      if (!data.ok) throw new Error(data.user_message || "Unknown error");
      updateIndicator(indicator, data);
      indicator.dataset.lastPayload = JSON.stringify(data);
    } catch (error) {
      const message = indicator.querySelector(".dp-sync-indicator__message");
      const badge = indicator.querySelector(".dp-sync-indicator__badge");
      if (message) {
        message.textContent = `Gagal cek sinkronisasi: ${error.message}`;
      }
      if (badge) {
        badge.classList.remove("text-bg-success");
        badge.classList.add("text-bg-danger");
      }
    }
  }

  indicators.forEach((indicator) => {
    indicator.dataset.lastSeenAhsp = indicator.dataset.initialAhsp || "";
    indicator.dataset.lastSeenHarga = indicator.dataset.initialHarga || "";
    indicator.dataset.lastSeenPekerjaan = indicator.dataset.pageLoaded || new Date().toISOString();

    const ackButton = indicator.querySelector(".dp-sync-indicator__ack");
    ackButton?.addEventListener("click", () => {
      const lastPayload = indicator.dataset.lastPayload;
      if (lastPayload) {
        acknowledge(indicator, JSON.parse(lastPayload));
      } else {
        acknowledge(indicator, null);
      }
      indicator.dataset.autoRefreshing = "false";
    });

    const autoOption = indicator.dataset.autoOption === "true";
    const autoCheckbox = indicator.querySelector(".dp-sync-indicator__auto");
    if (autoOption && autoCheckbox) {
      autoCheckbox.addEventListener("change", (event) => {
        const enabled = event.target.checked;
        indicator.dataset.autoEnabled = enabled ? "true" : "false";
        indicator.dataset.autoRefreshing = "false";
        if (!enabled) {
          event.target.blur();
        }
      });
    } else {
      indicator.dataset.autoEnabled = "false";
    }

    pollIndicator(indicator);
    setInterval(() => pollIndicator(indicator), POLL_INTERVAL_MS);
  });
})();
