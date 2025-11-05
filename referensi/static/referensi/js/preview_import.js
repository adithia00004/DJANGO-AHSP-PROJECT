document.addEventListener('DOMContentLoaded', () => {
    const previewRoot = document.getElementById('preview-root');
    if (!previewRoot || !window.fetch) {
        return;
    }

    const messageTarget = document.getElementById('ajax-messages');
    const schemaCard = document.getElementById('excel-schema-card');
    const debugStatsCard = document.getElementById('debug-stats-card');
    const toolbar = document.getElementById('preview-toolbar');

    const renderMessages = (html) => {
        if (messageTarget) {
            messageTarget.innerHTML = html || '';
        }
    };

    const showGenericError = () => {
        renderMessages(
            '<div class="alert alert-danger alert-dismissible fade show" role="alert">' +
                'Terjadi kesalahan saat memuat data. Silakan muat ulang halaman.' +
                '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
            '</div>'
        );
    };

    const updateSection = (section, html) => {
        const targetId = section === 'jobs' ? 'jobs-preview-container' : 'details-preview-container';
        const container = document.getElementById(targetId);
        if (container && typeof html === 'string') {
            container.innerHTML = html;
        }
    };

    const requestSection = (section, url, options = {}) => {
        const targetId = section === 'jobs' ? 'jobs-preview-container' : 'details-preview-container';
        const container = document.getElementById(targetId);
        if (container) {
            container.classList.add('opacity-50');
        }

        return fetch(url, options)
            .then((response) => {
                if (!response.ok) {
                    throw new Error('Request failed');
                }
                return response.json();
            })
            .then((payload) => {
                updateSection(section, payload.html || '');
                renderMessages(payload.messages_html || '');
            })
            .catch(() => {
                showGenericError();
            })
            .finally(() => {
                if (container) {
                    container.classList.remove('opacity-50');
                }
            });
    };

    previewRoot.addEventListener('click', (event) => {
        const link = event.target.closest('[data-preview-link]');
        if (!link) {
            return;
        }

        const section = link.getAttribute('data-preview-section');
        if (!section) {
            return;
        }

        event.preventDefault();
        const requestUrl = new URL(link.href, window.location.href);
        requestUrl.searchParams.set('section', section);
        requestUrl.searchParams.set('format', 'json');

        requestSection(section, requestUrl.toString(), {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
    });

    previewRoot.addEventListener('submit', (event) => {
        const form = event.target.closest('.js-preview-form');
        if (!form) {
            return;
        }

        const section = form.getAttribute('data-preview-section');
        if (!section) {
            return;
        }

        event.preventDefault();
        const formData = new FormData(form);
        formData.set('section', section);

        const action = form.getAttribute('action') || window.location.href;
        requestSection(section, action, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
        });
    });

    if (toolbar) {
        toolbar.addEventListener('click', (event) => {
            const button = event.target.closest('[data-action]');
            if (!button) {
                return;
            }

            const action = button.getAttribute('data-action');
            if (action === 'toggle-info') {
                if (!schemaCard && !debugStatsCard) {
                    return;
                }

                // Toggle both schema and debug stats cards
                let hidden = true;
                if (schemaCard) {
                    hidden = schemaCard.classList.toggle('d-none');
                }
                if (debugStatsCard) {
                    debugStatsCard.classList.toggle('d-none');
                }

                button.setAttribute('aria-pressed', hidden ? 'false' : 'true');
                button.classList.toggle('btn-outline-secondary', hidden);
                button.classList.toggle('btn-secondary', !hidden);
                button.classList.toggle('active', !hidden);

                if (!hidden) {
                    // Scroll to debug stats if available, otherwise schema
                    const scrollTarget = debugStatsCard || schemaCard;
                    if (scrollTarget) {
                        scrollTarget.scrollIntoView({ behavior: 'smooth', block: 'start' });
                    }
                }
            } else if (action === 'refresh-preview') {
                window.location.reload();
            } else if (action === 'download-template') {
                renderMessages(
                    '<div class="alert alert-info alert-dismissible fade show" role="alert">' +
                        'Template impor akan tersedia pada pembaruan selanjutnya.' +
                        '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>' +
                    '</div>'
                );
            }
        });
    }
});
