/**
 * List Pekerjaan - Test Helper Functions
 *
 * Usage:
 * 1. Open List Pekerjaan page
 * 2. Open DevTools Console
 * 3. Copy-paste this entire file into console
 * 4. Run test commands (see examples below)
 *
 * Example Commands:
 * - LP_TEST.checkDirtyTracking()
 * - LP_TEST.simulateDragDrop(fromIndex, toIndex)
 * - LP_TEST.testCrossTabSync()
 * - LP_TEST.runAllTests()
 */

window.LP_TEST = {

  // ============================================================================
  // UTILITY FUNCTIONS
  // ============================================================================

  log: (msg, ...args) => {
    console.log(`%c[LP_TEST] ${msg}`, 'color: #0066cc; font-weight: bold', ...args);
  },

  success: (msg) => {
    console.log(`%c✅ ${msg}`, 'color: #28a745; font-weight: bold');
  },

  error: (msg) => {
    console.log(`%c❌ ${msg}`, 'color: #dc3545; font-weight: bold');
  },

  warn: (msg) => {
    console.log(`%c⚠️ ${msg}`, 'color: #ffc107; font-weight: bold');
  },

  // Get all pekerjaan rows
  getAllRows: () => {
    return Array.from(document.querySelectorAll('#klas-list tbody tr'));
  },

  // Get row by index
  getRow: (index) => {
    const rows = window.LP_TEST.getAllRows();
    return rows[index] || null;
  },

  // Get save button
  getSaveButton: () => {
    return document.querySelector('#btn-save');
  },

  // Check if dirty
  isDirty: () => {
    const btn = window.LP_TEST.getSaveButton();
    return btn && btn.classList.contains('btn-neon');
  },

  // ============================================================================
  // TEST: DIRTY TRACKING
  // ============================================================================

  checkDirtyTracking: () => {
    window.LP_TEST.log('Testing dirty tracking system...');

    const initialDirty = window.LP_TEST.isDirty();
    window.LP_TEST.log('Initial dirty state:', initialDirty);

    // Find first uraian input
    const uraianInput = document.querySelector('#klas-list tbody .uraian');
    if (!uraianInput) {
      window.LP_TEST.error('No uraian input found. Add a pekerjaan first.');
      return;
    }

    // Simulate input
    const originalValue = uraianInput.value;
    uraianInput.value = 'TEST_' + Date.now();
    uraianInput.dispatchEvent(new Event('input', { bubbles: true }));

    // Check dirty state
    setTimeout(() => {
      const afterEditDirty = window.LP_TEST.isDirty();

      if (afterEditDirty) {
        window.LP_TEST.success('Dirty tracking works! Save button is pulsing.');

        // Check FAB
        const fab = document.getElementById('btn-save-fab');
        if (fab && !fab.classList.contains('d-none')) {
          window.LP_TEST.success('FAB button is visible.');
        } else {
          window.LP_TEST.warn('FAB button not visible.');
        }

        // Restore original value
        uraianInput.value = originalValue;
        uraianInput.dispatchEvent(new Event('input', { bubbles: true }));

      } else {
        window.LP_TEST.error('Dirty tracking FAILED! Save button not pulsing.');
      }
    }, 100);
  },

  // ============================================================================
  // TEST: BEFOREUNLOAD WARNING
  // ============================================================================

  testBeforeUnload: () => {
    window.LP_TEST.log('Testing beforeunload warning...');

    // Make page dirty
    const uraianInput = document.querySelector('#klas-list tbody .uraian');
    if (!uraianInput) {
      window.LP_TEST.error('No uraian input found.');
      return;
    }

    uraianInput.value = 'TEST_UNLOAD_' + Date.now();
    uraianInput.dispatchEvent(new Event('input', { bubbles: true }));

    setTimeout(() => {
      if (window.LP_TEST.isDirty()) {
        window.LP_TEST.success('Page is dirty. Now try closing this tab.');
        window.LP_TEST.warn('You should see a confirmation dialog.');
        window.LP_TEST.log('Test complete. Press Ctrl+W or close tab to verify.');
      }
    }, 100);
  },

  // ============================================================================
  // TEST: DRAG-AND-DROP SIMULATION
  // ============================================================================

  simulateDragDrop: (fromIndex, toIndex) => {
    window.LP_TEST.log(`Simulating drag from row ${fromIndex} to row ${toIndex}...`);

    const fromRow = window.LP_TEST.getRow(fromIndex);
    const toRow = window.LP_TEST.getRow(toIndex);

    if (!fromRow || !toRow) {
      window.LP_TEST.error(`Invalid indices. Found ${window.LP_TEST.getAllRows().length} rows.`);
      return;
    }

    const tbody = fromRow.closest('tbody');
    if (!tbody) {
      window.LP_TEST.error('No tbody found.');
      return;
    }

    // Simulate drag events
    window.LP_TEST.log('Dispatching dragstart event...');
    const dragStartEvent = new DragEvent('dragstart', {
      bubbles: true,
      cancelable: true,
      dataTransfer: new DataTransfer()
    });
    fromRow.dispatchEvent(dragStartEvent);

    // Simulate drop
    window.LP_TEST.log('Inserting row at new position...');
    if (toIndex < fromIndex) {
      tbody.insertBefore(fromRow, toRow);
    } else {
      tbody.insertBefore(fromRow, toRow.nextSibling);
    }

    // Trigger renumbering (if available)
    if (typeof window.LP_DEBUG !== 'undefined' && window.LP_DEBUG.scheduleSidebarRebuild) {
      window.LP_DEBUG.scheduleSidebarRebuild();
    }

    // Dispatch dragend
    const dragEndEvent = new DragEvent('dragend', { bubbles: true });
    fromRow.dispatchEvent(dragEndEvent);

    window.LP_TEST.success(`Row moved from position ${fromIndex} to ${toIndex}`);
    window.LP_TEST.log('Check if dirty state was triggered.');
  },

  // ============================================================================
  // TEST: CROSS-TAB SYNC
  // ============================================================================

  testCrossTabSync: () => {
    window.LP_TEST.log('Testing cross-tab sync...');

    // Check if BroadcastChannel is available
    if (typeof BroadcastChannel === 'undefined') {
      window.LP_TEST.error('BroadcastChannel not supported in this browser.');
      return;
    }

    // Create test channel
    const testChannel = new BroadcastChannel('list_pekerjaan_sync');

    // Listen for messages
    testChannel.onmessage = (event) => {
      window.LP_TEST.log('Received broadcast message:', event.data);

      if (event.data.type === 'ordering_changed') {
        window.LP_TEST.success('Cross-tab sync works! Message received.');
        window.LP_TEST.log('Project ID:', event.data.projectId);
        window.LP_TEST.log('Timestamp:', new Date(event.data.timestamp));
      }
    };

    // Send test message
    window.LP_TEST.log('Sending test broadcast message...');
    testChannel.postMessage({
      type: 'ordering_changed',
      projectId: 'TEST_PROJECT',
      timestamp: Date.now()
    });

    setTimeout(() => {
      window.LP_TEST.log('Test message sent. Check other tabs for notification.');
      testChannel.close();
    }, 500);
  },

  // ============================================================================
  // TEST: TOOLTIP INITIALIZATION
  // ============================================================================

  testTooltips: () => {
    window.LP_TEST.log('Testing tooltip initialization...');

    const tooltipButtons = document.querySelectorAll('[data-bs-toggle="tooltip"]');
    window.LP_TEST.log(`Found ${tooltipButtons.length} tooltip buttons.`);

    if (tooltipButtons.length === 0) {
      window.LP_TEST.warn('No tooltip buttons found in DOM.');
      return;
    }

    // Check if Bootstrap is available
    if (typeof bootstrap === 'undefined') {
      window.LP_TEST.error('Bootstrap not loaded.');
      return;
    }

    if (typeof bootstrap.Tooltip === 'undefined') {
      window.LP_TEST.error('Bootstrap.Tooltip not available.');
      return;
    }

    window.LP_TEST.success('Bootstrap.Tooltip is available.');

    // Try to get tooltip instance
    const firstButton = tooltipButtons[0];
    const tooltipInstance = bootstrap.Tooltip.getInstance(firstButton);

    if (tooltipInstance) {
      window.LP_TEST.success('Tooltip instance found on button.');
      window.LP_TEST.log('Try hovering over the info button to see tooltip.');
    } else {
      window.LP_TEST.warn('No tooltip instance found. May need initialization.');
    }
  },

  // ============================================================================
  // TEST: DRAG HANDLE VISIBILITY
  // ============================================================================

  testDragHandle: () => {
    window.LP_TEST.log('Testing drag handle visibility...');

    const rows = window.LP_TEST.getAllRows();
    if (rows.length === 0) {
      window.LP_TEST.error('No pekerjaan rows found.');
      return;
    }

    const firstRow = rows[0];
    const isDraggable = firstRow.getAttribute('draggable') === 'true';

    if (isDraggable) {
      window.LP_TEST.success('Row is draggable (draggable="true").');
    } else {
      window.LP_TEST.error('Row is NOT draggable!');
      return;
    }

    // Check CSS
    const colNum = firstRow.querySelector('td.col-num');
    if (!colNum) {
      window.LP_TEST.error('No col-num cell found.');
      return;
    }

    const styles = window.getComputedStyle(colNum, '::before');
    const content = styles.content;

    window.LP_TEST.log('CSS ::before content:', content);

    if (content.includes('⋮⋮') || content.includes('\\22ee')) {
      window.LP_TEST.success('Drag handle icon (⋮⋮) is present in CSS.');
    } else {
      window.LP_TEST.warn('Drag handle icon may not be visible. Check CSS.');
    }
  },

  // ============================================================================
  // TEST: ORDERING INDEX
  // ============================================================================

  testOrderingIndex: () => {
    window.LP_TEST.log('Testing ordering_index dataset...');

    const rows = window.LP_TEST.getAllRows();
    if (rows.length === 0) {
      window.LP_TEST.error('No rows found.');
      return;
    }

    window.LP_TEST.log(`Found ${rows.length} total rows.`);

    const indices = rows.map((row, i) => ({
      rowIndex: i,
      orderingIndex: row.dataset.orderingIndex,
      id: row.dataset.id || row.id
    }));

    console.table(indices);

    // Check if sequential
    const hasOrderingIndex = indices.every(item => item.orderingIndex !== undefined);

    if (hasOrderingIndex) {
      window.LP_TEST.success('All rows have orderingIndex in dataset.');
    } else {
      window.LP_TEST.warn('Some rows missing orderingIndex. Will be set on save.');
    }
  },

  // ============================================================================
  // TEST: SAVE BUTTON STATE
  // ============================================================================

  testSaveButton: () => {
    window.LP_TEST.log('Testing save button state...');

    const btn = window.LP_TEST.getSaveButton();
    if (!btn) {
      window.LP_TEST.error('Save button not found.');
      return;
    }

    const isDirty = window.LP_TEST.isDirty();
    const isDisabled = btn.disabled;
    const hasNeon = btn.classList.contains('btn-neon');

    window.LP_TEST.log('Button state:', {
      disabled: isDisabled,
      hasNeonClass: hasNeon,
      isDirty: isDirty
    });

    if (hasNeon && isDirty) {
      window.LP_TEST.success('Save button correctly shows dirty state (pulsing).');
    } else if (!hasNeon && !isDirty) {
      window.LP_TEST.success('Save button correctly shows clean state.');
    } else {
      window.LP_TEST.warn('Save button state may be inconsistent.');
    }
  },

  // ============================================================================
  // RUN ALL TESTS
  // ============================================================================

  runAllTests: () => {
    window.LP_TEST.log('========================================');
    window.LP_TEST.log('Running all automated tests...');
    window.LP_TEST.log('========================================');

    setTimeout(() => window.LP_TEST.testSaveButton(), 100);
    setTimeout(() => window.LP_TEST.testDragHandle(), 300);
    setTimeout(() => window.LP_TEST.testOrderingIndex(), 500);
    setTimeout(() => window.LP_TEST.testTooltips(), 700);
    setTimeout(() => window.LP_TEST.checkDirtyTracking(), 900);

    setTimeout(() => {
      window.LP_TEST.log('========================================');
      window.LP_TEST.log('Automated tests complete.');
      window.LP_TEST.log('========================================');
      window.LP_TEST.warn('Some tests require manual verification:');
      window.LP_TEST.log('- LP_TEST.testBeforeUnload() - then close tab');
      window.LP_TEST.log('- LP_TEST.testCrossTabSync() - requires 2 tabs');
      window.LP_TEST.log('- LP_TEST.simulateDragDrop(0, 2) - drag simulation');
    }, 1500);
  },

  // ============================================================================
  // HELP
  // ============================================================================

  help: () => {
    console.log(`
%c========================================
List Pekerjaan - Test Helper Commands
========================================

BASIC TESTS:
  LP_TEST.runAllTests()           - Run all automated tests
  LP_TEST.checkDirtyTracking()    - Test dirty state
  LP_TEST.testSaveButton()        - Check save button state
  LP_TEST.testDragHandle()        - Check drag handle visibility
  LP_TEST.testOrderingIndex()     - Show ordering indices

INTERACTIVE TESTS:
  LP_TEST.testBeforeUnload()      - Test page close warning (then close tab)
  LP_TEST.testCrossTabSync()      - Test cross-tab broadcast (need 2 tabs)
  LP_TEST.testTooltips()          - Check Bootstrap tooltips

DRAG-DROP SIMULATION:
  LP_TEST.simulateDragDrop(0, 2)  - Move row 0 to position 2
  LP_TEST.getAllRows()            - List all pekerjaan rows

UTILITIES:
  LP_TEST.isDirty()               - Check if page is dirty
  LP_TEST.getRow(index)           - Get row by index
  LP_TEST.help()                  - Show this help

EXAMPLE WORKFLOW:
1. LP_TEST.runAllTests()
2. Manually drag-and-drop a row
3. LP_TEST.testSaveButton()  (should be pulsing)
4. Open another tab with same project
5. Click Save in first tab
6. Check second tab for notification

`, 'font-family: monospace; color: #0066cc');
  }
};

// Auto-show help on load
console.log('%c========================================', 'color: #28a745; font-weight: bold');
console.log('%c List Pekerjaan Test Helpers Loaded! ', 'color: #28a745; font-weight: bold');
console.log('%c========================================', 'color: #28a745; font-weight: bold');
console.log('%cType LP_TEST.help() for available commands', 'color: #666; font-style: italic');
console.log('%cQuick start: LP_TEST.runAllTests()', 'color: #0066cc; font-weight: bold');
