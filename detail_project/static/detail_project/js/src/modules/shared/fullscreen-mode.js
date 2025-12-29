/**
 * Fullscreen Mode Manager
 * Provides unified fullscreen functionality for Grid, Gantt, and Kurva S modes
 */

const LOG_PREFIX = '[FullscreenMode]';

class FullscreenModeManager {
    constructor(options = {}) {
        this.container = options.container || null;
        this.onEnter = options.onEnter || null;
        this.onExit = options.onExit || null;
        this.isFullscreen = false;
        this.originalParent = null;
        this.originalNextSibling = null;
        this.overlay = null;

        // Bind ESC key handler
        this._boundKeyHandler = this._handleKeyDown.bind(this);
    }

    /**
     * Enter fullscreen mode for the given container
     * @param {HTMLElement} container - The container to make fullscreen
     * @param {Object} options - Options for fullscreen
     */
    enter(container, options = {}) {
        if (this.isFullscreen) {
            console.warn(LOG_PREFIX, 'Already in fullscreen mode');
            return;
        }

        const targetContainer = container || this.container;
        if (!targetContainer) {
            console.error(LOG_PREFIX, 'No container provided for fullscreen');
            return;
        }

        this.container = targetContainer;
        this.originalParent = targetContainer.parentNode;
        this.originalNextSibling = targetContainer.nextSibling;

        // Create fullscreen overlay
        this.overlay = document.createElement('div');
        this.overlay.className = 'fullscreen-overlay';
        this.overlay.innerHTML = `
      <div class="fullscreen-header">
        <div class="fullscreen-title">
          <i class="bi bi-arrows-fullscreen"></i>
          <span>${options.title || 'Fullscreen Mode'}</span>
        </div>
        <button class="fullscreen-close-btn" title="Exit Fullscreen (ESC)">
          <i class="bi bi-x-lg"></i>
        </button>
      </div>
      <div class="fullscreen-content"></div>
      <div class="fullscreen-hint">Press ESC to exit</div>
    `;

        // Move container to fullscreen overlay
        const content = this.overlay.querySelector('.fullscreen-content');
        content.appendChild(targetContainer);

        // Append overlay to body
        document.body.appendChild(this.overlay);

        // Bind events
        const closeBtn = this.overlay.querySelector('.fullscreen-close-btn');
        closeBtn.addEventListener('click', () => this.exit());
        document.addEventListener('keydown', this._boundKeyHandler);

        // Prevent body scroll
        document.body.style.overflow = 'hidden';

        this.isFullscreen = true;

        // Wait for layout to stabilize, then trigger resize and callback
        requestAnimationFrame(() => {
            // Dispatch resize event so charts can recalculate dimensions
            window.dispatchEvent(new Event('resize'));

            // Small delay to ensure layout is complete
            setTimeout(() => {
                // Trigger callback
                if (typeof this.onEnter === 'function') {
                    this.onEnter(targetContainer);
                }
            }, 100);
        });

        console.log(LOG_PREFIX, 'Entered fullscreen mode');
    }

    /**
     * Exit fullscreen mode
     */
    exit() {
        if (!this.isFullscreen || !this.overlay) {
            return;
        }

        // Add exit animation
        this.overlay.classList.add('exiting');

        setTimeout(() => {
            // Move container back to original position
            if (this.originalParent) {
                if (this.originalNextSibling) {
                    this.originalParent.insertBefore(this.container, this.originalNextSibling);
                } else {
                    this.originalParent.appendChild(this.container);
                }
            }

            // Remove overlay
            if (this.overlay && this.overlay.parentNode) {
                this.overlay.parentNode.removeChild(this.overlay);
            }

            // Restore body scroll
            document.body.style.overflow = '';

            // Remove event listeners
            document.removeEventListener('keydown', this._boundKeyHandler);

            this.overlay = null;
            this.isFullscreen = false;

            // Wait for layout to stabilize, then trigger resize and callback
            requestAnimationFrame(() => {
                // Dispatch resize event so charts can recalculate dimensions
                window.dispatchEvent(new Event('resize'));

                // Small delay to ensure layout is complete
                setTimeout(() => {
                    // Trigger callback
                    if (typeof this.onExit === 'function') {
                        this.onExit(this.container);
                    }
                }, 100);
            });

            console.log(LOG_PREFIX, 'Exited fullscreen mode');
        }, 200); // Match animation duration
    }

    /**
     * Toggle fullscreen mode
     */
    toggle(container, options = {}) {
        if (this.isFullscreen) {
            this.exit();
        } else {
            this.enter(container, options);
        }
    }

    /**
     * Handle ESC key
     */
    _handleKeyDown(event) {
        if (event.key === 'Escape' && this.isFullscreen) {
            event.preventDefault();
            this.exit();
        }
    }
}

/**
 * Add fullscreen toggle button to a container
 * @param {HTMLElement} container - Container to add button to
 * @param {Object} options - Button options
 * @returns {HTMLButtonElement} The created button
 */
function addFullscreenButton(container, options = {}) {
    if (!container) return null;

    // Check if button already exists
    const existingBtn = container.querySelector('.fullscreen-toggle-btn');
    if (existingBtn) return existingBtn;

    // Ensure container has relative positioning
    const containerStyle = window.getComputedStyle(container);
    if (containerStyle.position === 'static') {
        container.style.position = 'relative';
    }

    // Create button
    const btn = document.createElement('button');
    btn.className = 'fullscreen-toggle-btn';
    btn.innerHTML = '<i class="bi bi-arrows-fullscreen"></i>';
    btn.title = options.title || 'Enter Fullscreen';
    btn.setAttribute('aria-label', 'Toggle Fullscreen');

    // Add to container
    container.appendChild(btn);

    return btn;
}

/**
 * Remove fullscreen button from a container
 * @param {HTMLElement} container - Container to remove button from
 */
function removeFullscreenButton(container) {
    if (!container) return;
    const btn = container.querySelector('.fullscreen-toggle-btn');
    if (btn) {
        btn.parentNode.removeChild(btn);
    }
}

/**
 * Add download image button to a container (positioned next to fullscreen button)
 * @param {HTMLElement} container - Container to add button to
 * @param {Object} options - Button options
 * @param {Function} options.onClick - Click handler for download
 * @param {string} options.title - Button tooltip
 * @returns {HTMLButtonElement} The created button
 */
function addDownloadImageButton(container, options = {}) {
    if (!container) return null;

    // Check if button already exists
    const existingBtn = container.querySelector('.download-image-btn');
    if (existingBtn) return existingBtn;

    // Ensure container has relative positioning
    const containerStyle = window.getComputedStyle(container);
    if (containerStyle.position === 'static') {
        container.style.position = 'relative';
    }

    // Create button
    const btn = document.createElement('button');
    btn.className = 'download-image-btn';
    btn.innerHTML = '<i class="bi bi-image"></i>';
    btn.title = options.title || 'Download as PNG Image';
    btn.setAttribute('aria-label', 'Download as Image');

    // Style to position next to fullscreen button (to its right)
    btn.style.cssText = `
        position: absolute;
        top: 8px;
        left: 48px;
        z-index: 100;
        width: 32px;
        height: 32px;
        border-radius: 6px;
        border: 1px solid rgba(0, 0, 0, 0.1);
        background: rgba(255, 255, 255, 0.95);
        color: #374151;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 14px;
        transition: all 0.2s ease;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    `;

    // Hover effect
    btn.addEventListener('mouseenter', () => {
        btn.style.background = '#3b82f6';
        btn.style.color = '#ffffff';
        btn.style.transform = 'scale(1.05)';
    });
    btn.addEventListener('mouseleave', () => {
        btn.style.background = 'rgba(255, 255, 255, 0.95)';
        btn.style.color = '#374151';
        btn.style.transform = 'scale(1)';
    });

    // Click handler
    if (options.onClick) {
        btn.addEventListener('click', options.onClick);
    }

    // Add to container
    container.appendChild(btn);

    return btn;
}

/**
 * Remove download image button from a container
 * @param {HTMLElement} container - Container to remove button from
 */
function removeDownloadImageButton(container) {
    if (!container) return;
    const btn = container.querySelector('.download-image-btn');
    if (btn) {
        btn.parentNode.removeChild(btn);
    }
}

export { FullscreenModeManager, addFullscreenButton, removeFullscreenButton, addDownloadImageButton, removeDownloadImageButton };
export default FullscreenModeManager;
