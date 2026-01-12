/**
 * UX Enhancements Module
 * Provides keyboard shortcuts, ripple effects, and other UX improvements
 * @module ux-enhancements
 */

/**
 * Keyboard Shortcuts Manager
 */
export class KeyboardShortcuts {
  constructor() {
    this.shortcuts = new Map();
    this.enabled = true;
    this._boundHandler = this._handleKeyDown.bind(this);
    this.init();
  }

  init() {
    document.addEventListener('keydown', this._boundHandler);
    console.log('⌨️ Keyboard shortcuts initialized');
  }

  /**
   * Register a keyboard shortcut
   * @param {string} key - Key combination (e.g., 'ctrl+s', 'alt+p')
   * @param {Function} callback - Function to call when shortcut triggered
   * @param {Object} options - Additional options
   */
  register(key, callback, options = {}) {
    const { description = '', preventDefault = true } = options;

    this.shortcuts.set(key.toLowerCase(), {
      callback,
      description,
      preventDefault
    });
  }

  /**
   * Unregister a keyboard shortcut
   */
  unregister(key) {
    this.shortcuts.delete(key.toLowerCase());
  }

  /**
   * Handle keydown events
   */
  _handleKeyDown(event) {
    if (!this.enabled) return;

    // Don't trigger shortcuts when typing in input/textarea
    const activeElement = document.activeElement;
    const isInput = activeElement.tagName === 'INPUT' ||
                   activeElement.tagName === 'TEXTAREA' ||
                   activeElement.isContentEditable;

    // Build key combination string
    const parts = [];
    if (event.ctrlKey) parts.push('ctrl');
    if (event.altKey) parts.push('alt');
    if (event.shiftKey) parts.push('shift');
    if (event.metaKey) parts.push('meta');

    const key = event.key.toLowerCase();
    if (!['control', 'alt', 'shift', 'meta'].includes(key)) {
      parts.push(key);
    }

    const combo = parts.join('+');
    const shortcut = this.shortcuts.get(combo);

    if (shortcut) {
      // Allow Ctrl+A, Ctrl+C, Ctrl+V, Ctrl+X in inputs
      const allowedInInput = ['ctrl+a', 'ctrl+c', 'ctrl+v', 'ctrl+x', 'ctrl+z'];
      if (isInput && !allowedInInput.includes(combo)) {
        return;
      }

      if (shortcut.preventDefault) {
        event.preventDefault();
      }

      shortcut.callback(event);
      console.log(`⌨️ Shortcut triggered: ${combo}`);
    }
  }

  /**
   * Enable shortcuts
   */
  enable() {
    this.enabled = true;
  }

  /**
   * Disable shortcuts
   */
  disable() {
    this.enabled = false;
  }

  /**
   * Get all registered shortcuts
   */
  getShortcuts() {
    return Array.from(this.shortcuts.entries()).map(([key, data]) => ({
      key,
      description: data.description
    }));
  }

  /**
   * Cleanup
   */
  destroy() {
    document.removeEventListener('keydown', this._boundHandler);
    this.shortcuts.clear();
  }
}

/**
 * Ripple Effect Manager
 */
export class RippleEffect {
  /**
   * Add ripple effect to element
   * @param {HTMLElement} element - Target element
   */
  static add(element) {
    if (!element) return;

    element.classList.add('btn-ripple');

    // Optional: Add click listener for more control
    element.addEventListener('click', function(e) {
      const ripple = document.createElement('span');
      ripple.classList.add('ripple-circle');

      const rect = this.getBoundingClientRect();
      const size = Math.max(rect.width, rect.height);
      const x = e.clientX - rect.left - size / 2;
      const y = e.clientY - rect.top - size / 2;

      ripple.style.width = ripple.style.height = size + 'px';
      ripple.style.left = x + 'px';
      ripple.style.top = y + 'px';

      this.appendChild(ripple);

      setTimeout(() => ripple.remove(), 600);
    });
  }

  /**
   * Add ripple to multiple elements
   * @param {string} selector - CSS selector
   */
  static addToAll(selector) {
    document.querySelectorAll(selector).forEach(el => {
      RippleEffect.add(el);
    });
  }
}

/**
 * Button State Manager
 */
export class ButtonStateManager {
  /**
   * Set button to loading state
   * @param {HTMLElement} button - Button element
   * @param {string} loadingText - Optional loading text
   */
  static setLoading(button, loadingText = 'Loading...') {
    if (!button) return;

    button.dataset.originalText = button.innerHTML;
    button.disabled = true;
    button.classList.add('loading');

    const spinner = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>';
    button.innerHTML = spinner + loadingText;
  }

  /**
   * Set button to success state
   * @param {HTMLElement} button - Button element
   * @param {number} duration - Duration to show success state (ms)
   */
  static setSuccess(button, duration = 2000) {
    if (!button) return;

    button.disabled = false;
    button.classList.remove('loading');
    button.classList.add('success');

    if (button.dataset.originalText) {
      button.innerHTML = button.dataset.originalText;
    }

    setTimeout(() => {
      button.classList.remove('success');
    }, duration);
  }

  /**
   * Set button to error state
   * @param {HTMLElement} button - Button element
   * @param {number} duration - Duration to show error state (ms)
   */
  static setError(button, duration = 2000) {
    if (!button) return;

    button.disabled = false;
    button.classList.remove('loading');
    button.classList.add('error');

    if (button.dataset.originalText) {
      button.innerHTML = button.dataset.originalText;
    }

    setTimeout(() => {
      button.classList.remove('error');
    }, duration);
  }

  /**
   * Reset button to normal state
   * @param {HTMLElement} button - Button element
   */
  static reset(button) {
    if (!button) return;

    button.disabled = false;
    button.classList.remove('loading', 'success', 'error');

    if (button.dataset.originalText) {
      button.innerHTML = button.dataset.originalText;
    }
  }

  /**
   * Mark button with "has changes" indicator
   * @param {HTMLElement} button - Button element
   * @param {boolean} hasChanges - Whether there are unsaved changes
   */
  static markChanges(button, hasChanges) {
    if (!button) return;

    if (hasChanges) {
      button.classList.add('has-changes');
      button.setAttribute('data-tooltip', 'You have unsaved changes');
    } else {
      button.classList.remove('has-changes');
      button.removeAttribute('data-tooltip');
    }
  }
}

/**
 * Toast Notifications (wrapper untuk DP.core.toast)
 */
export class Toast {
  /**
   * Show success toast
   */
  static success(message, duration = 1600) {
    if (window.DP?.core?.toast) {
      window.DP.core.toast.show(message, 'success', duration);
    } else {
      console.log(`✅ ${message}`);
    }
  }

  /**
   * Show error toast
   */
  static error(message, duration = 3000) {
    if (window.DP?.core?.toast) {
      window.DP.core.toast.show(message, 'danger', duration);
    } else {
      console.error(`❌ ${message}`);
    }
  }

  /**
   * Show warning toast
   */
  static warning(message, duration = 2000) {
    if (window.DP?.core?.toast) {
      window.DP.core.toast.show(message, 'warning', duration);
    } else {
      console.warn(`⚠️ ${message}`);
    }
  }

  /**
   * Show info toast
   */
  static info(message, duration = 1600) {
    if (window.DP?.core?.toast) {
      window.DP.core.toast.show(message, 'info', duration);
    } else {
      console.info(`ℹ️ ${message}`);
    }
  }
}

/**
 * Smooth Scroll Helper
 */
export class SmoothScroll {
  /**
   * Scroll to element smoothly
   * @param {HTMLElement|string} target - Element or selector
   * @param {Object} options - Scroll options
   */
  static to(target, options = {}) {
    const element = typeof target === 'string'
      ? document.querySelector(target)
      : target;

    if (!element) return;

    const {
      offset = 0,
      behavior = 'smooth',
      block = 'start'
    } = options;

    const elementPosition = element.getBoundingClientRect().top;
    const offsetPosition = elementPosition + window.pageYOffset - offset;

    window.scrollTo({
      top: offsetPosition,
      behavior
    });
  }

  /**
   * Scroll to top
   */
  static toTop() {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  }
}

/**
 * Debounce utility
 */
export function debounce(func, wait = 300) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle utility
 */
export function throttle(func, limit = 100) {
  let inThrottle;
  return function executedFunction(...args) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

/**
 * Initialize all UX enhancements
 */
export function initializeUXEnhancements() {
  console.log('🎨 Initializing UX enhancements...');

  // Add ripple effects to all primary buttons
  RippleEffect.addToAll('.btn-primary, .btn-save, .btn-danger');

  // Add tooltips to buttons with title attribute
  document.querySelectorAll('button[title]').forEach(btn => {
    if (!btn.hasAttribute('data-tooltip')) {
      btn.setAttribute('data-tooltip', btn.getAttribute('title'));
    }
  });

  console.log('✅ UX enhancements initialized');
}

/**
 * Default export
 */
export default {
  KeyboardShortcuts,
  RippleEffect,
  ButtonStateManager,
  Toast,
  SmoothScroll,
  debounce,
  throttle,
  initializeUXEnhancements
};
