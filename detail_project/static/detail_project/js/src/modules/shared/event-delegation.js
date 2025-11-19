/**
 * Event Delegation Module
 * Provides memory-efficient event handling using delegation pattern
 * Prevents memory leaks from thousands of individual event listeners
 * License: MIT
 */

/**
 * Event Delegation Manager
 * Manages delegated event listeners on a parent element
 */
export class EventDelegationManager {
  constructor(rootElement) {
    this.rootElement = rootElement;
    this.handlers = new Map(); // event type -> array of handler configs
    this.activeListeners = new Map(); // event type -> actual listener function
  }

  /**
   * Registers a delegated event handler
   *
   * @param {string} eventType - Event type (e.g., 'click', 'input')
   * @param {string} selector - CSS selector to match target elements
   * @param {Function} handler - Event handler function
   * @param {Object} options - Configuration options
   * @param {boolean} options.capture - Use capture phase
   * @param {boolean} options.passive - Mark as passive listener
   *
   * @example
   * manager.on('click', '.time-cell.editable', (event, target) => {
   *   console.log('Clicked cell:', target.dataset.cellId);
   * });
   */
  on(eventType, selector, handler, options = {}) {
    if (!this.handlers.has(eventType)) {
      this.handlers.set(eventType, []);
      this._attachListener(eventType, options);
    }

    this.handlers.get(eventType).push({
      selector,
      handler,
      options,
    });
  }

  /**
   * Removes a delegated event handler
   *
   * @param {string} eventType - Event type
   * @param {string} selector - CSS selector
   * @param {Function} handler - Handler function to remove
   */
  off(eventType, selector, handler) {
    if (!this.handlers.has(eventType)) {
      return;
    }

    const handlers = this.handlers.get(eventType);
    const index = handlers.findIndex(
      (h) => h.selector === selector && h.handler === handler
    );

    if (index !== -1) {
      handlers.splice(index, 1);

      // If no more handlers for this event type, remove the listener
      if (handlers.length === 0) {
        this._detachListener(eventType);
        this.handlers.delete(eventType);
      }
    }
  }

  /**
   * Removes all handlers for an event type
   *
   * @param {string} eventType - Event type to clear
   */
  clearEvent(eventType) {
    if (!this.handlers.has(eventType)) {
      return;
    }

    this._detachListener(eventType);
    this.handlers.delete(eventType);
  }

  /**
   * Removes all handlers and cleans up
   */
  destroy() {
    for (const eventType of this.handlers.keys()) {
      this._detachListener(eventType);
    }

    this.handlers.clear();
    this.activeListeners.clear();
    this.rootElement = null;
  }

  /**
   * Internal: Attaches the actual event listener to root element
   */
  _attachListener(eventType, options = {}) {
    const listener = (event) => {
      const handlers = this.handlers.get(eventType) || [];

      for (const { selector, handler } of handlers) {
        // Find the matching target (could be event.target or an ancestor)
        const target = event.target.closest(selector);

        if (target && this.rootElement.contains(target)) {
          handler.call(target, event, target);
        }
      }
    };

    this.rootElement.addEventListener(eventType, listener, {
      capture: options.capture || false,
      passive: options.passive || false,
    });

    this.activeListeners.set(eventType, listener);
  }

  /**
   * Internal: Detaches the event listener from root element
   */
  _detachListener(eventType) {
    const listener = this.activeListeners.get(eventType);

    if (listener) {
      this.rootElement.removeEventListener(eventType, listener);
      this.activeListeners.delete(eventType);
    }
  }
}

/**
 * Simplified event delegation helper function
 *
 * @param {HTMLElement} rootElement - Parent element to attach listener to
 * @param {string} eventType - Event type (e.g., 'click')
 * @param {string} selector - CSS selector for target elements
 * @param {Function} handler - Event handler
 * @param {Object} options - Event options
 * @returns {Function} Cleanup function
 *
 * @example
 * const cleanup = delegate(
 *   document.getElementById('grid-container'),
 *   'click',
 *   '.time-cell',
 *   (event, target) => {
 *     handleCellClick(target);
 *   }
 * );
 *
 * // Later, to cleanup:
 * cleanup();
 */
export function delegate(rootElement, eventType, selector, handler, options = {}) {
  const listener = (event) => {
    const target = event.target.closest(selector);

    if (target && rootElement.contains(target)) {
      handler.call(target, event, target);
    }
  };

  rootElement.addEventListener(eventType, listener, options);

  // Return cleanup function
  return () => {
    rootElement.removeEventListener(eventType, listener);
  };
}

/**
 * Creates multiple delegated event listeners and returns cleanup function
 *
 * @param {HTMLElement} rootElement - Parent element
 * @param {Object} eventMap - Map of event configs
 * @returns {Function} Cleanup function for all listeners
 *
 * @example
 * const cleanup = delegateMultiple(gridContainer, {
 *   click: {
 *     '.time-cell': handleCellClick,
 *     '.expand-btn': handleExpand,
 *   },
 *   input: {
 *     '.time-cell input': handleInput,
 *   },
 *   blur: {
 *     '.time-cell input': handleBlur,
 *   },
 * });
 *
 * // Cleanup all listeners
 * cleanup();
 */
export function delegateMultiple(rootElement, eventMap) {
  const cleanupFunctions = [];

  for (const [eventType, selectorHandlers] of Object.entries(eventMap)) {
    for (const [selector, handler] of Object.entries(selectorHandlers)) {
      const cleanup = delegate(rootElement, eventType, selector, handler);
      cleanupFunctions.push(cleanup);
    }
  }

  // Return function that cleans up all listeners
  return () => {
    cleanupFunctions.forEach((cleanup) => cleanup());
  };
}

/**
 * Safely removes old event listeners from an element
 * Useful for cleaning up before re-attaching new listeners
 *
 * @param {HTMLElement} element - Element to clean
 *
 * @example
 * cleanupEventListeners(gridContainer);
 * // Now safe to attach new listeners without duplicates
 */
export function cleanupEventListeners(element) {
  if (!element || !element._delegatedHandlers) {
    return;
  }

  const handlers = element._delegatedHandlers || [];

  handlers.forEach(({ event, handler, options }) => {
    element.removeEventListener(event, handler, options);
  });

  delete element._delegatedHandlers;
}

/**
 * Stores event listener references for later cleanup
 *
 * @param {HTMLElement} element - Element to track
 * @param {string} eventType - Event type
 * @param {Function} handler - Handler function
 * @param {Object} options - Event options
 */
export function trackEventListener(element, eventType, handler, options = {}) {
  if (!element._delegatedHandlers) {
    element._delegatedHandlers = [];
  }

  element._delegatedHandlers.push({
    event: eventType,
    handler,
    options,
  });
}

/**
 * One-time event listener with automatic cleanup
 *
 * @param {HTMLElement} element - Element to listen on
 * @param {string} eventType - Event type
 * @param {Function} handler - Handler function
 *
 * @example
 * once(saveButton, 'click', () => {
 *   console.log('This will only fire once');
 * });
 */
export function once(element, eventType, handler) {
  const onceHandler = (event) => {
    handler(event);
    element.removeEventListener(eventType, onceHandler);
  };

  element.addEventListener(eventType, onceHandler);

  return () => {
    element.removeEventListener(eventType, onceHandler);
  };
}
