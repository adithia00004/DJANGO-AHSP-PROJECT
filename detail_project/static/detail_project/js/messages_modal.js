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
            const level = tags.split(' ')[0]; // Get first tag as level

            messages.push({
                level: level,
                tags: tags,
                message: item.dataset.message
            });
        });

        return messages;
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

            // Split message by newlines for better formatting
            const messageLines = msg.message.split('\n');
            const messageHtml = messageLines.map(line => {
                if (!line.trim()) return '';
                return `<p class="mb-2">${line}</p>`;
            }).join('');

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
    function init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }

        // Wait for Bootstrap to be loaded
        if (typeof bootstrap === 'undefined') {
            console.warn('Bootstrap not loaded yet, retrying...');
            setTimeout(init, 100);
            return;
        }

        // Parse and show messages
        const messages = parseMessages();
        if (messages.length > 0) {
            showMessagesModal(messages);
        }
    }

    // Start initialization
    init();

    // Export for manual usage
    window.showDjangoMessages = function(messages) {
        showMessagesModal(messages);
    };

})();
