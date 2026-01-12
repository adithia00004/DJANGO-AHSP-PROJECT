/**
 * Compact LED Sync Indicator
 * Shows a small colored dot with hover tooltip for sync status
 */
(() => {
    const leds = document.querySelectorAll(".dp-sync-led");
    if (!leds.length) return;

    const POLL_INTERVAL_MS = 30000;

    function parseTs(value) {
        if (!value) return 0;
        const date = new Date(value);
        return Number.isNaN(date.getTime()) ? 0 : date.getTime();
    }

    function getWatchLabel(watch) {
        const labels = {
            'harga': 'Harga Items',
            'ahsp': 'Template AHSP',
            'pekerjaan': 'List Pekerjaan',
            'volume': 'Volume',
            'jadwal': 'Jadwal',
            'both': 'AHSP & Harga',
            'all': 'Semua data'
        };
        return labels[watch] || 'Data terkait';
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

        // Reset classes
        dot.classList.remove('dp-sync-led__dot--synced', 'dp-sync-led__dot--changed',
            'dp-sync-led__dot--error', 'dp-sync-led__dot--checking');

        if (error) {
            dot.classList.add('dp-sync-led__dot--error');
            if (status) status.textContent = '❌ Gagal cek';
            if (message) message.textContent = error;
            led.dataset.hasChanges = 'false';
            return;
        }

        if (!payload) {
            dot.classList.add('dp-sync-led__dot--checking');
            if (status) status.textContent = 'Memeriksa...';
            if (message) message.textContent = 'Menunggu respon server';
            return;
        }

        // Check changes for each type
        const hargaChanged = parseTs(payload?.harga_changed_at) > lastSeenHarga;
        const ahspChanged = parseTs(payload?.ahsp_changed_at) > lastSeenAhsp;
        const pekerjaanChanged = parseTs(payload?.pekerjaan_changed_at) > lastSeenPekerjaan;
        const volumeChanged = parseTs(payload?.volume_changed_at) > lastSeenVolume;
        const jadwalChanged = parseTs(payload?.jadwal_changed_at) > lastSeenJadwal;

        let hasChanges = false;
        let changeInfo = '';
        const changes = [];

        // Determine what to watch based on watch type
        const watchTypes = watch.split(',').map(w => w.trim());

        watchTypes.forEach(w => {
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

        changeInfo = changes.length > 0 ? `${changes.join(', ')} berubah` : '';

        if (hasChanges) {
            dot.classList.add('dp-sync-led__dot--changed');
            if (status) status.textContent = `⚠️ ${changeInfo}`;
            if (message) message.textContent = 'Klik reload untuk update data';
            if (reloadBtn) reloadBtn.classList.remove('d-none');
        } else {
            dot.classList.add('dp-sync-led__dot--synced');
            if (status) status.textContent = `✅ ${watchLabel} tersinkron`;
            if (message) message.textContent = `Terakhir cek: ${new Date().toLocaleTimeString('id-ID')}`;
            if (reloadBtn) reloadBtn.classList.add('d-none');
        }

        led.dataset.hasChanges = hasChanges ? 'true' : 'false';
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

        // Reload button click
        const reloadBtn = led.querySelector('.dp-sync-led__reload');
        reloadBtn?.addEventListener('click', (e) => {
            e.stopPropagation();
            window.location.reload();
        });

        // LED click = reload if has changes
        led.addEventListener('click', () => {
            if (led.dataset.hasChanges === 'true') {
                window.location.reload();
            }
        });

        // Initial poll and interval
        pollLed(led);
        setInterval(() => pollLed(led), POLL_INTERVAL_MS);
    });
})();
