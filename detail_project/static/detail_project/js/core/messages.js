// /static/detail_project/js/core/messages.js
// Single Source of Truth for UI Messages (i18n-ready)
(() => {
    const DP = (window.DP = window.DP || {});
    DP.core = DP.core || {};
    if (DP.core.messages) return;

    /**
     * Centralized UI Messages for consistency across all pages
     * Usage: DP.core.messages.export.processing
     */
    const messages = {
        // Export operations
        export: {
            processing: 'Memproses export...',
            generating: 'Membuat dokumen...',
            downloading: 'Mengunduh file...',
            success: 'Export berhasil!',
            error: 'Gagal export. Silakan coba lagi.',
            cancelled: 'Export dibatalkan.',
            noData: 'Tidak ada data untuk di-export.',
            formatError: 'Format export tidak valid.',
        },

        // Save operations
        save: {
            processing: 'Menyimpan...',
            saving: 'Menyimpan perubahan...',
            success: 'Perubahan berhasil disimpan.',
            error: 'Gagal menyimpan. Silakan coba lagi.',
            noChanges: 'Tidak ada perubahan untuk disimpan.',
            unsaved: 'Ada perubahan yang belum disimpan.',
            confirmLeave: 'Anda yakin ingin meninggalkan halaman? Perubahan yang belum disimpan akan hilang.',
        },

        // Loading states
        loading: {
            default: 'Memuat...',
            data: 'Memuat data...',
            page: 'Memuat halaman...',
            please_wait: 'Mohon tunggu...',
        },

        // Validation
        validation: {
            required: 'Field ini wajib diisi.',
            invalid: 'Format tidak valid.',
            minLength: 'Minimal {min} karakter.',
            maxLength: 'Maksimal {max} karakter.',
            numeric: 'Harus berupa angka.',
            percentage: 'Nilai harus antara 0-100.',
            positive: 'Nilai harus positif.',
            date: 'Format tanggal tidak valid.',
            email: 'Format email tidak valid.',
        },

        // Confirmation dialogs
        confirm: {
            delete: 'Anda yakin ingin menghapus?',
            reset: 'Anda yakin ingin mereset?',
            cancel: 'Anda yakin ingin membatalkan?',
            proceed: 'Anda yakin ingin melanjutkan?',
        },

        // Success/Error notifications
        notify: {
            success: 'Berhasil!',
            error: 'Terjadi kesalahan.',
            warning: 'Perhatian!',
            info: 'Informasi',
            copied: 'Berhasil disalin ke clipboard.',
            deleted: 'Berhasil dihapus.',
            updated: 'Berhasil diperbarui.',
            created: 'Berhasil dibuat.',
        },

        // Empty states
        empty: {
            default: 'Tidak ada data.',
            search: 'Tidak ada hasil pencarian.',
            filter: 'Tidak ada data yang sesuai filter.',
            items: 'Belum ada item.',
            select: 'Pilih item untuk melihat detail.',
        },

        // Network/Connection
        network: {
            error: 'Koneksi terputus. Periksa jaringan Anda.',
            timeout: 'Waktu koneksi habis.',
            serverError: 'Server sedang bermasalah. Coba lagi nanti.',
            offline: 'Anda sedang offline.',
        }
    };

    /**
     * Get message with parameter substitution
     * @param {string} path - Dot notation path, e.g. 'validation.minLength'
     * @param {Object} params - Parameters to substitute, e.g. { min: 5 }
     * @returns {string} Message with substituted parameters
     */
    function get(path, params = {}) {
        const keys = path.split('.');
        let result = messages;

        for (const key of keys) {
            if (result && typeof result === 'object' && key in result) {
                result = result[key];
            } else {
                console.warn(`Message not found: ${path}`);
                return path;
            }
        }

        if (typeof result !== 'string') {
            console.warn(`Message path does not resolve to string: ${path}`);
            return path;
        }

        // Substitute parameters like {min}, {max}
        return result.replace(/\{(\w+)\}/g, (match, key) => {
            return params[key] !== undefined ? params[key] : match;
        });
    }

    // Export
    DP.core.messages = { ...messages, get };
})();
