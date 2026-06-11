/**
 * Compact LED Sync Indicator
 * Shows a small colored dot with hover tooltip for sync status
 */
(() => {
    const leds = document.querySelectorAll('.dp-sync-led');
    if (!leds.length) return;

    const POLL_INTERVAL_MS = 30000;
    const FULL_RELOAD_SCOPES = new Set(['rekap_rab', 'rincian_rab', 'rekap_kebutuhan']);

    function parseTs(value) {
        if (!value) return 0;
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? 0 : date.getTime();
    }

    function getWatchLabel(watch) {
        const labels = {
            harga: 'Harga Items',
            ahsp: 'Template AHSP',
            pekerjaan: 'List Pekerjaan',
            volume: 'Volume',
            jadwal: 'Jadwal',
            both: 'AHSP dan Harga',
            all: 'Semua data',
        };
        return labels[watch] || 'Data terkait';
    }

    function readLastPayload(led) {
        const raw = led.dataset.lastPayload || '';
        if (!raw) return null;
        try {
            return JSON.parse(raw);
        } catch (_) {
            return null;
        }
    }

    function emitStatusEvent(led, detail = {}) {
        const payload = {
            projectId: Number(led.dataset.projectId) || null,
            scope: led.dataset.scope || 'global',
            watch: led.dataset.watch || 'both',
            endpoint: led.dataset.endpoint || '',
            ...detail,
        };
        window.dispatchEvent(new CustomEvent('dp:change-status', { detail: payload }));
    }

    function acknowledgeLed(led, options = {}) {
        if (!led) return;
        const payload = options.payload || readLastPayload(led) || {};
        const nowIso = new Date().toISOString();
        const touch = (key, payloadKey, forceNow = false) => {
            if (forceNow) {
                led.dataset[key] = nowIso;
                return;
            }
            const next = payload && payload[payloadKey] ? String(payload[payloadKey]) : '';
            led.dataset[key] = next || nowIso;
        };
        if (options.ahsp) touch('lastSeenAhsp', 'ahsp_changed_at');
        if (options.harga) touch('lastSeenHarga', 'harga_changed_at');
        if (options.pekerjaan) touch('lastSeenPekerjaan', 'pekerjaan_changed_at', true);
        if (options.volume) touch('lastSeenVolume', 'volume_changed_at', true);
        if (options.jadwal) touch('lastSeenJadwal', 'jadwal_changed_at', true);
    }

    function requestScopedRefresh(led, reason = 'manual') {
        const refreshDetail = {
            projectId: Number(led.dataset.projectId) || null,
            scope: led.dataset.scope || 'global',
            watch: led.dataset.watch || 'both',
            endpoint: led.dataset.endpoint || '',
            source: 'sync-led',
            reason,
            hasChanges: led.dataset.hasChanges === 'true',
            payload: readLastPayload(led),
        };
        const refreshEvent = new CustomEvent('dp:sync-refresh-request', {
            detail: refreshDetail,
            cancelable: true,
        });
        const handled = !window.dispatchEvent(refreshEvent);
        if (!handled) {
            if (FULL_RELOAD_SCOPES.has(refreshDetail.scope)) {
                window.location.reload();
                return true;
            }
            const message = led.querySelector('.dp-sync-led__message');
            if (message) {
                message.textContent = 'Halaman ini belum mendukung sinkronisasi parsial.';
            }
        }
        return handled;
    }

    function updateLed(led, payload, error = null) {
        const dot = led.querySelector('.dp-sync-led__dot');
        const status = led.querySelector('.dp-sync-led__status');
        const message = led.querySelector('.dp-sync-led__message');
        const reloadBtn = led.querySelector('.dp-sync-led__reload');
        if (!dot) return;

        const watch = led.dataset.watch || 'both';
        const watchLabel = getWatchLabel(watch);
        const lastSeenHarga = parseTs(led.dataset.lastSeenHarga || led.dataset.initialHarga);
        const lastSeenAhsp = parseTs(led.dataset.lastSeenAhsp || led.dataset.initialAhsp);
        const lastSeenPekerjaan = parseTs(led.dataset.lastSeenPekerjaan || led.dataset.initialPekerjaan);
        const lastSeenVolume = parseTs(led.dataset.lastSeenVolume || led.dataset.initialVolume);
        const lastSeenJadwal = parseTs(led.dataset.lastSeenJadwal || led.dataset.initialJadwal);
        const previousState = led.dataset.hasChanges === 'true';

        dot.classList.remove(
            'dp-sync-led__dot--synced',
            'dp-sync-led__dot--changed',
            'dp-sync-led__dot--error',
            'dp-sync-led__dot--checking',
        );

        if (error) {
            dot.classList.add('dp-sync-led__dot--error');
            if (status) status.textContent = 'Gagal cek';
            if (message) message.textContent = error;
            led.dataset.hasChanges = 'false';
            emitStatusEvent(led, { type: 'update', hasChanges: false, payload: null, error });
            return;
        }

        if (!payload) {
            dot.classList.add('dp-sync-led__dot--checking');
            if (status) status.textContent = 'Memeriksa...';
            if (message) message.textContent = 'Menunggu respon server';
            return;
        }

        const hargaChanged = parseTs(payload?.harga_changed_at) > lastSeenHarga;
        const ahspChanged = parseTs(payload?.ahsp_changed_at) > lastSeenAhsp;
        const pekerjaanChanged = parseTs(payload?.pekerjaan_changed_at) > lastSeenPekerjaan;
        const volumeChanged = parseTs(payload?.volume_changed_at) > lastSeenVolume;
        const jadwalChanged = parseTs(payload?.jadwal_changed_at) > lastSeenJadwal;

        let hasChanges = false;
        const changes = [];
        const watchTypes = watch.split(',').map((w) => w.trim());

        watchTypes.forEach((w) => {
            if (w === 'harga' && hargaChanged) { hasChanges = true; changes.push('Harga'); }
            if (w === 'ahsp' && ahspChanged) { hasChanges = true; changes.push('AHSP'); }
            if (w === 'pekerjaan' && pekerjaanChanged) { hasChanges = true; changes.push('Pekerjaan'); }
            if (w === 'volume' && volumeChanged) { hasChanges = true; changes.push('Volume'); }
            if (w === 'jadwal' && jadwalChanged) { hasChanges = true; changes.push('Jadwal'); }
            if (w === 'both') {
                if (hargaChanged) { hasChanges = true; changes.push('Harga'); }
                if (ahspChanged) { hasChanges = true; changes.push('AHSP'); }
            }
            if (w === 'all') {
                if (hargaChanged) { hasChanges = true; changes.push('Harga'); }
                if (ahspChanged) { hasChanges = true; changes.push('AHSP'); }
                if (pekerjaanChanged) { hasChanges = true; changes.push('Pekerjaan'); }
                if (volumeChanged) { hasChanges = true; changes.push('Volume'); }
                if (jadwalChanged) { hasChanges = true; changes.push('Jadwal'); }
            }
        });

        const changeInfo = changes.length > 0 ? `${changes.join(', ')} berubah` : '';

        if (hasChanges) {
            dot.classList.add('dp-sync-led__dot--changed');
            if (status) status.textContent = `[!] ${changeInfo}`;
            if (message) message.textContent = 'Klik sinkronkan untuk memuat data terbaru';
            if (reloadBtn) reloadBtn.classList.remove('d-none');
        } else {
            dot.classList.add('dp-sync-led__dot--synced');
            if (status) status.textContent = `[OK] ${watchLabel} tersinkron`;
            if (message) message.textContent = `Terakhir cek: ${new Date().toLocaleTimeString('id-ID')}`;
            if (reloadBtn) reloadBtn.classList.add('d-none');
        }

        led.dataset.hasChanges = hasChanges ? 'true' : 'false';
        if (previousState !== hasChanges) {
            emitStatusEvent(led, { type: 'update', hasChanges, payload });
        }
    }

    async function pollLed(led) {
        const endpoint = led.dataset.endpoint;
        if (!endpoint) return;

        const params = new URLSearchParams();
        if (led.dataset.lastSeenAhsp) {
            params.set('since_ahsp', led.dataset.lastSeenAhsp);
        }
        if (led.dataset.lastSeenHarga) {
            params.set('since_harga', led.dataset.lastSeenHarga);
        }

        try {
            const response = await fetch(`${endpoint}?${params.toString()}`, {
                credentials: 'same-origin',
            });
            if (!response.ok) throw new Error(`Status ${response.status}`);
            const data = await response.json();
            if (!data.ok) throw new Error(data.user_message || 'Unknown error');
            const sourceChange = window.DP?.sourceChange || null;
            if (
                sourceChange &&
                typeof sourceChange.syncFlags === 'function' &&
                Array.isArray(data.pending_reload_job_ids) &&
                Array.isArray(data.pending_volume_reset_job_ids)
            ) {
                sourceChange.syncFlags(Number(led.dataset.projectId), {
                    reload_job_ids: data.pending_reload_job_ids,
                    volume_reset_job_ids: data.pending_volume_reset_job_ids,
                });
            }
            updateLed(led, data);
            led.dataset.lastPayload = JSON.stringify(data);
        } catch (error) {
            updateLed(led, null, error.message);
        }
    }

    leds.forEach((led) => {
        led.dataset.lastSeenAhsp = led.dataset.initialAhsp || '';
        led.dataset.lastSeenHarga = led.dataset.initialHarga || '';
        led.dataset.lastSeenPekerjaan = led.dataset.initialPekerjaan || '';
        led.dataset.lastSeenVolume = led.dataset.initialVolume || '';
        led.dataset.lastSeenJadwal = led.dataset.initialJadwal || '';

        const reloadBtn = led.querySelector('.dp-sync-led__reload');
        reloadBtn?.addEventListener('click', (event) => {
            event.stopPropagation();
            requestScopedRefresh(led, 'manual');
        });

        led.addEventListener('click', () => {
            if (led.dataset.hasChanges === 'true') {
                requestScopedRefresh(led, 'manual');
            }
        });

        pollLed(led);
        setInterval(() => pollLed(led), POLL_INTERVAL_MS);
    });

    window.addEventListener('dp:sync-led-ack', (event) => {
        const detail = event?.detail || {};
        const projectId = Number(detail.projectId);
        if (!Number.isFinite(projectId) || projectId <= 0) return;
        const payload = detail.payload || null;
        let updated = false;
        leds.forEach((led) => {
            if (Number(led.dataset.projectId) !== projectId) return;
            acknowledgeLed(led, {
                payload,
                ahsp: !!detail.ahsp,
                harga: !!detail.harga,
                pekerjaan: !!detail.pekerjaan,
                volume: !!detail.volume,
                jadwal: !!detail.jadwal,
            });
            updateLed(led, payload || readLastPayload(led) || null);
            updated = true;
        });
        if (!updated) return;
    });
})();
