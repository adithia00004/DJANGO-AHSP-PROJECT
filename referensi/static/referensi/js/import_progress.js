/**
 * Import Progress Handler
 * Handles loading states, progress tracking, and prevents browser freeze
 */

(function() {
    'use strict';

    // =====================================================
    // LOADING OVERLAY
    // =====================================================

    const LoadingOverlay = {
        overlay: null,

        create() {
            if (this.overlay) return;

            const html = `
                <div id="importLoadingOverlay" class="import-loading-overlay">
                    <div class="loading-content">
                        <div class="loading-spinner">
                            <div class="spinner-border text-primary" role="status" style="width: 4rem; height: 4rem;">
                                <span class="visually-hidden">Loading...</span>
                            </div>
                        </div>
                        <h4 class="loading-title mt-4">Memproses Import...</h4>
                        <p class="loading-message">Mohon tunggu, jangan tutup halaman ini</p>

                        <div class="progress-container mt-4" style="width: 400px; max-width: 90%;">
                            <div class="progress" style="height: 25px;">
                                <div id="importProgressBar"
                                     class="progress-bar progress-bar-striped progress-bar-animated"
                                     role="progressbar"
                                     style="width: 0%"
                                     aria-valuenow="0"
                                     aria-valuemin="0"
                                     aria-valuemax="100">
                                    <span id="importProgressText">0%</span>
                                </div>
                            </div>
                            <div id="importProgressDetails" class="text-center mt-2 small text-muted"></div>
                        </div>

                        <div id="importStageInfo" class="mt-3 small">
                            <div class="stage-item">
                                <i class="bi bi-check-circle text-success" id="stageParsingIcon"></i>
                                <span id="stageParsingText">Membaca file Excel...</span>
                            </div>
                            <div class="stage-item">
                                <i class="bi bi-circle text-muted" id="stageValidationIcon"></i>
                                <span id="stageValidationText">Validasi data</span>
                            </div>
                            <div class="stage-item">
                                <i class="bi bi-circle text-muted" id="stageRenderIcon"></i>
                                <span id="stageRenderText">Menampilkan preview</span>
                            </div>
                        </div>

                        <button type="button" class="btn btn-sm btn-outline-secondary mt-4" id="btnCancelImport" style="display: none;">
                            <i class="bi bi-x-circle"></i> Batalkan
                        </button>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', html);
            this.overlay = document.getElementById('importLoadingOverlay');
        },

        show(message = 'Memproses Import...', stage = 'parsing') {
            this.create();
            this.overlay.style.display = 'flex';

            const title = this.overlay.querySelector('.loading-title');
            if (title) title.textContent = message;

            this.setStage(stage);

            // Prevent body scroll
            document.body.style.overflow = 'hidden';
        },

        hide() {
            if (this.overlay) {
                this.overlay.style.display = 'none';
                document.body.style.overflow = '';
            }
        },

        setProgress(percent, details = '') {
            const bar = document.getElementById('importProgressBar');
            const text = document.getElementById('importProgressText');
            const detailsEl = document.getElementById('importProgressDetails');

            if (bar) {
                bar.style.width = percent + '%';
                bar.setAttribute('aria-valuenow', percent);
            }

            if (text) {
                text.textContent = Math.round(percent) + '%';
            }

            if (detailsEl && details) {
                detailsEl.textContent = details;
            }
        },

        setStage(stage) {
            // Reset all stages
            document.querySelectorAll('.stage-item i').forEach(icon => {
                icon.className = 'bi bi-circle text-muted';
            });

            // Set current stage
            const stages = {
                'parsing': {
                    icon: 'stageParsingIcon',
                    text: 'stageParsingText',
                    message: 'Membaca file Excel...'
                },
                'validation': {
                    icon: 'stageValidationIcon',
                    text: 'stageValidationText',
                    message: 'Memvalidasi data...'
                },
                'render': {
                    icon: 'stageRenderIcon',
                    text: 'stageRenderText',
                    message: 'Menampilkan preview...'
                }
            };

            const stageInfo = stages[stage];
            if (stageInfo) {
                const icon = document.getElementById(stageInfo.icon);
                const textEl = document.getElementById(stageInfo.text);

                if (icon) {
                    icon.className = 'bi bi-arrow-repeat spin text-primary';
                }

                if (textEl) {
                    textEl.innerHTML = `<strong>${stageInfo.message}</strong>`;
                }

                // Mark previous stages as complete
                const stageOrder = ['parsing', 'validation', 'render'];
                const currentIndex = stageOrder.indexOf(stage);
                for (let i = 0; i < currentIndex; i++) {
                    const prevStage = stages[stageOrder[i]];
                    const prevIcon = document.getElementById(prevStage.icon);
                    if (prevIcon) {
                        prevIcon.className = 'bi bi-check-circle text-success';
                    }
                }
            }
        }
    };

    // =====================================================
    // CHUNKED PROCESSING
    // =====================================================

    const ChunkedProcessor = {
        /**
         * Process large array in chunks to prevent browser freeze
         */
        async processInChunks(items, processor, chunkSize = 100, onProgress = null) {
            const totalItems = items.length;
            let processedCount = 0;

            for (let i = 0; i < items.length; i += chunkSize) {
                const chunk = items.slice(i, i + chunkSize);

                // Process chunk
                await processor(chunk, i);

                // Update progress
                processedCount += chunk.length;
                const percent = (processedCount / totalItems) * 100;

                if (onProgress) {
                    onProgress(percent, processedCount, totalItems);
                }

                // Yield to browser (prevent freeze)
                await this.sleep(0);
            }
        },

        sleep(ms) {
            return new Promise(resolve => setTimeout(resolve, ms));
        }
    };

    // =====================================================
    // FORM HANDLER WITH PROGRESS
    // =====================================================

    const ImportFormHandler = {
        init() {
            const form = document.querySelector('form[enctype="multipart/form-data"]');
            if (!form) return;

            form.addEventListener('submit', (e) => {
                const fileInput = form.querySelector('input[type="file"]');
                const file = fileInput?.files[0];

                if (file) {
                    // Show loading for file upload
                    const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
                    LoadingOverlay.show('Mengunggah file...', 'parsing');
                    LoadingOverlay.setProgress(10, `Mengunggah ${file.name} (${sizeMB} MB)`);

                    // Simulate upload progress (since we can't track actual upload easily)
                    this.simulateUploadProgress(file.size);
                }
            });
        },

        simulateUploadProgress(fileSize) {
            // Estimate upload time based on file size (rough estimate)
            const estimatedSeconds = Math.min(fileSize / (1024 * 1024), 10); // Max 10 seconds
            const steps = 50;
            const interval = (estimatedSeconds * 1000) / steps;

            let progress = 10;
            const timer = setInterval(() => {
                progress += (80 / steps); // Go from 10% to 90%
                if (progress >= 90) {
                    clearInterval(timer);
                    LoadingOverlay.setProgress(90, 'Memproses file di server...');
                    LoadingOverlay.setStage('validation');
                } else {
                    LoadingOverlay.setProgress(progress, 'Mengunggah file...');
                }
            }, interval);
        }
    };

    // =====================================================
    // PREVIEW TABLE OPTIMIZATION
    // =====================================================

    const PreviewOptimizer = {
        init() {
            // Lazy load images if any
            this.lazyLoadImages();

            // Virtualize long tables
            this.optimizeTables();
        },

        lazyLoadImages() {
            const images = document.querySelectorAll('img[data-src]');
            const imageObserver = new IntersectionObserver((entries) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.removeAttribute('data-src');
                        imageObserver.unobserve(img);
                    }
                });
            });

            images.forEach(img => imageObserver.observe(img));
        },

        optimizeTables() {
            // Add progressive rendering for large tables
            const tables = document.querySelectorAll('.preview-table table tbody');

            tables.forEach(tbody => {
                const rows = tbody.querySelectorAll('tr');

                // If table has many rows, hide excess initially
                if (rows.length > 200) {
                    console.warn(`Large table detected (${rows.length} rows). Consider using pagination.`);

                    // Show first 100 rows immediately
                    for (let i = 100; i < rows.length; i++) {
                        rows[i].style.display = 'none';
                        rows[i].setAttribute('data-lazy-row', 'true');
                    }

                    // Add "Load More" functionality
                    this.addLoadMoreButton(tbody, rows);
                }
            });
        },

        addLoadMoreButton(tbody, allRows) {
            const loadMoreRow = document.createElement('tr');
            loadMoreRow.className = 'load-more-row';
            loadMoreRow.innerHTML = `
                <td colspan="100" class="text-center py-3">
                    <button type="button" class="btn btn-outline-primary btn-sm">
                        <i class="bi bi-arrow-down-circle"></i> Muat Lebih Banyak Baris
                    </button>
                </td>
            `;

            tbody.appendChild(loadMoreRow);

            const button = loadMoreRow.querySelector('button');
            button.addEventListener('click', () => {
                let loadedCount = 0;
                const batchSize = 100;

                for (let i = 0; i < allRows.length && loadedCount < batchSize; i++) {
                    const row = allRows[i];
                    if (row.hasAttribute('data-lazy-row') && row.style.display === 'none') {
                        row.style.display = '';
                        row.removeAttribute('data-lazy-row');
                        loadedCount++;
                    }
                }

                // Check if all rows loaded
                const remainingRows = tbody.querySelectorAll('tr[data-lazy-row]');
                if (remainingRows.length === 0) {
                    loadMoreRow.remove();
                }

                button.innerHTML = `<i class="bi bi-check-circle"></i> Loaded ${loadedCount} rows`;
                setTimeout(() => {
                    button.innerHTML = `<i class="bi bi-arrow-down-circle"></i> Muat Lebih Banyak Baris`;
                }, 1000);
            });
        }
    };

    // =====================================================
    // MEMORY MANAGEMENT
    // =====================================================

    const MemoryManager = {
        init() {
            // Monitor memory usage if available
            if (performance.memory) {
                this.monitorMemory();
            }

            // Cleanup on page unload
            window.addEventListener('beforeunload', () => {
                this.cleanup();
            });
        },

        monitorMemory() {
            setInterval(() => {
                if (performance.memory) {
                    const usedMB = (performance.memory.usedJSHeapSize / (1024 * 1024)).toFixed(2);
                    const limitMB = (performance.memory.jsHeapSizeLimit / (1024 * 1024)).toFixed(2);
                    const percentUsed = (performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100;

                    if (percentUsed > 80) {
                        console.warn(`Memory usage high: ${usedMB} MB / ${limitMB} MB (${percentUsed.toFixed(1)}%)`);

                        // Suggest user action
                        if (percentUsed > 90) {
                            const warning = document.createElement('div');
                            warning.className = 'alert alert-warning alert-dismissible fade show position-fixed top-0 start-50 translate-middle-x mt-3';
                            warning.style.zIndex = '99999';
                            warning.innerHTML = `
                                <strong>Peringatan Memori!</strong> Browser menggunakan banyak memori.
                                Pertimbangkan untuk me-refresh halaman atau mengurangi jumlah data yang ditampilkan.
                                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
                            `;
                            document.body.appendChild(warning);
                            setTimeout(() => warning.remove(), 10000);
                        }
                    }
                }
            }, 30000); // Check every 30 seconds
        },

        cleanup() {
            // Clear large data structures
            // Note: Most cleanup is automatic in modern browsers
            console.log('Cleaning up before page unload...');
        }
    };

    // =====================================================
    // INITIALIZATION
    // =====================================================

    document.addEventListener('DOMContentLoaded', function() {
        // Hide loading overlay on page load (in case it was shown before refresh)
        LoadingOverlay.hide();

        // Initialize handlers
        ImportFormHandler.init();
        PreviewOptimizer.init();
        MemoryManager.init();

        // Expose to window for external access
        window.ImportProgress = {
            show: (message, stage) => LoadingOverlay.show(message, stage),
            hide: () => LoadingOverlay.hide(),
            setProgress: (percent, details) => LoadingOverlay.setProgress(percent, details),
            setStage: (stage) => LoadingOverlay.setStage(stage),
            processInChunks: (items, processor, chunkSize, onProgress) =>
                ChunkedProcessor.processInChunks(items, processor, chunkSize, onProgress)
        };

        console.log('[Import Progress] Initialized');
    });

})();
