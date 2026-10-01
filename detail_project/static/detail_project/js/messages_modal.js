/**
 * Messages Modal Handler
 * Displays Django messages in a Bootstrap modal popup instead of inline alerts
 *
 * Usage: Include this script in base.html and it will automatically show
 * messages in a modal when the page loads.
 */

(function() {
    'use strict';

    // Message level to Bootstrap color mapping
    const MESSAGE_LEVEL_MAP = {
        'debug': 'secondary',
        'info': 'info',
        'success': 'success',
        'warning': 'warning',
        'error': 'danger'
    };

    // Message level to icon mapping
    const MESSAGE_ICON_MAP = {
        'debug': 'bi-bug',
        'info': 'bi-info-circle',
        'success': 'bi-check-circle',
        'warning': 'bi-exclamation-triangle',
        'error': 'bi-x-circle'
    };

    // Message level to modal header color
    const HEADER_COLOR_MAP = {
        'debug': 'bg-secondary text-white',
        'info': 'bg-info text-white',
        'success': 'bg-success text-white',
        'warning': 'bg-warning text-dark',
        'error': 'bg-danger text-white'
    };

    const KNOWN_LEVELS = ['error', 'warning', 'success', 'info', 'debug'];

    /**
     * Level dari tags Django. Django menyusun tags sebagai "extra_tags level"
     * (mis. "import-error error"), jadi token pertama BUKAN selalu level.
     */
    function levelFromTags(tags) {
        const tokens = String(tags || '').split(/\s+/);
        return KNOWN_LEVELS.find(level => tokens.includes(level)) || 'info';
    }

    function hasTag(msg, tag) {
        return String(msg.tags || '').split(/\s+/).includes(tag);
    }

    /**
     * Template memakai |escapejs di atribut data, yang menghasilkan teks
     * """, "-" dst. (atribut HTML tidak mendekodenya). Didekode di
     * sini lalu tetap dirender sebagai teks.
     */
    function decodeEscapeJs(text) {
        return String(text || '').replace(/\\u([0-9a-fA-F]{4})/g,
            (_, hex) => String.fromCharCode(parseInt(hex, 16)));
    }

    /**
     * Parse Django messages from hidden div
     */
    function parseMessages() {
        const messagesContainer = document.getElementById('django-messages-data');
        if (!messagesContainer) {
            return [];
        }

        const messageItems = messagesContainer.querySelectorAll('.message-item');
        const messages = [];

        messageItems.forEach(item => {
            const tags = item.dataset.tags || 'info';
            const raw = item.dataset.message || '';
            const msg = { level: levelFromTags(tags), tags: tags, message: raw };
            // HTML error import dibiarkan apa adanya (perilaku lama); pesan
            // biasa didekode lalu di-escape saat dirender.
            if (!hasTag(msg, 'import-error')) {
                msg.message = decodeEscapeJs(raw);
            }
            messages.push(msg);
        });

        return messages;
    }

    /**
     * Owner 2026-10-01 (K-6): sukses/info tampil sebagai toast yang hilang
     * sendiri; error/peringatan (dan HTML error import) tetap modal.
     */
    function isToastMessage(msg) {
        return ['success', 'info', 'debug'].includes(msg.level) && !hasTag(msg, 'import-error');
    }

    /**
     * Get modal title based on message levels
     */
    function getModalTitle(messages) {
        if (messages.length === 0) return 'Notifikasi';

        // Count message types
        const hasError = messages.some(m => m.level === 'error');
        const hasWarning = messages.some(m => m.level === 'warning');
        const hasSuccess = messages.some(m => m.level === 'success');

        if (hasError) {
            return '⚠️ Error';
        } else if (hasWarning) {
            return '⚠️ Peringatan';
        } else if (hasSuccess) {
            return '✅ Berhasil';
        } else {
            return '📢 Informasi';
        }
    }

    /**
     * Get header class based on most severe message level
     */
    function getHeaderClass(messages) {
        if (messages.length === 0) return '';

        // Priority: error > warning > success > info > debug
        const hasError = messages.some(m => m.level === 'error');
        const hasWarning = messages.some(m => m.level === 'warning');
        const hasSuccess = messages.some(m => m.level === 'success');
        const hasInfo = messages.some(m => m.level === 'info');

        if (hasError) return HEADER_COLOR_MAP['error'];
        if (hasWarning) return HEADER_COLOR_MAP['warning'];
        if (hasSuccess) return HEADER_COLOR_MAP['success'];
        if (hasInfo) return HEADER_COLOR_MAP['info'];
        return HEADER_COLOR_MAP['debug'];
    }

    /**
     * Render messages HTML
     */
    function renderMessages(messages) {
        if (messages.length === 0) return '';

        let html = '<div class="messages-list">';

        messages.forEach((msg, index) => {
            const level = msg.level || 'info';
            const color = MESSAGE_LEVEL_MAP[level] || 'info';
            const icon = MESSAGE_ICON_MAP[level] || 'bi-info-circle';
            const tags = msg.tags || '';

            let messageHtml;

            // Check if this is an import-error with HTML content
            if (tags.includes('import-error')) {
                // Render HTML directly (it's already safe from mark_safe)
                messageHtml = msg.message;
            } else {
                // Split message by newlines for better formatting
                const messageLines = msg.message.split('\n');
                messageHtml = messageLines.map(line => {
                    if (!line.trim()) return '';
                    // Escape HTML for safety
                    const escaped = line
                        .replace(/&/g, '&amp;')
                        .replace(/</g, '&lt;')
                        .replace(/>/g, '&gt;')
                        .replace(/"/g, '&quot;');
                    return `<p class="mb-2">${escaped}</p>`;
                }).join('');
            }

            html += `
                <div class="alert alert-${color} mb-3" role="alert">
                    <div class="d-flex align-items-start">
                        <i class="bi ${icon} fs-4 me-3 flex-shrink-0"></i>
                        <div class="flex-grow-1">
                            ${messageHtml}
                        </div>
                    </div>
                </div>
            `;
        });

        html += '</div>';

        return html;
    }

    /**
     * Show messages modal
     */
    function showMessagesModal(messages) {
        if (messages.length === 0) return;

        // Get modal elements
        const modal = document.getElementById('messagesModal');
        const modalTitle = document.getElementById('messagesModalTitle');
        const modalBody = document.getElementById('messagesModalBody');
        const modalHeader = document.getElementById('messagesModalHeader');

        if (!modal || !modalTitle || !modalBody || !modalHeader) {
            console.error('Messages modal elements not found');
            return;
        }

        // Set modal content
        modalTitle.textContent = getModalTitle(messages);
        modalBody.innerHTML = renderMessages(messages);

        // Set header color
        modalHeader.className = 'modal-header ' + getHeaderClass(messages);

        // Show modal
        const bsModal = new bootstrap.Modal(modal, {
            keyboard: true,
            backdrop: true
        });
        bsModal.show();

        // Cleanup hidden messages container
        const messagesContainer = document.getElementById('django-messages-data');
        if (messagesContainer) {
            messagesContainer.remove();
        }
    }

    /**
     * Initialize on page load
     */
    function showModalWhenReady(messages, attempt) {
        // Wait for Bootstrap to be loaded
        if (typeof bootstrap === 'undefined') {
            if ((attempt || 0) < 50) {
                setTimeout(() => showModalWhenReady(messages, (attempt || 0) + 1), 100);
            } else {
                console.error('Bootstrap tidak termuat; pesan server tidak dapat ditampilkan.');
            }
            return;
        }
        showMessagesModal(messages);
    }

    function init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        const messages = parseMessages();
        if (messages.length === 0) return;

        // Sukses/info -> toast (hilang sendiri). Tanpa DP.toast, semuanya
        // tetap tampil di modal agar tidak ada pesan yang hilang.
        const toastApi = window.DP && window.DP.toast;
        const toastMessages = toastApi ? messages.filter(isToastMessage) : [];
        const modalMessages = messages.filter(msg => !toastMessages.includes(msg));
        toastMessages.forEach(msg => {
            toastApi.show(msg.message, msg.level === 'debug' ? 'info' : msg.level);
        });

        if (modalMessages.length > 0) {
            showModalWhenReady(modalMessages, 0);
        } else {
            const messagesContainer = document.getElementById('django-messages-data');
            if (messagesContainer) messagesContainer.remove();
        }
    }

    // Start initialization
    init();

    // Export for manual usage
    window.showDjangoMessages = function(messages) {
        showMessagesModal(messages);
    };

})();
