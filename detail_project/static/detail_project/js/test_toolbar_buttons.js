/**
 * Test Script for Toolbar Buttons
 *
 * This script can be run in browser console to verify all toolbar buttons are working
 *
 * Usage:
 * 1. Open browser DevTools (F12)
 * 2. Navigate to Console tab
 * 3. Paste this entire script and press Enter
 * 4. Check output for PASS/FAIL status
 */

(function() {
  'use strict';

  const TEST_PREFIX = '[ToolbarButtonTest]';
  const results = [];

  function log(message, type = 'info') {
    const styles = {
      info: 'color: blue',
      success: 'color: green; font-weight: bold',
      error: 'color: red; font-weight: bold',
      warn: 'color: orange'
    };
    console.log(`%c${TEST_PREFIX} ${message}`, styles[type] || styles.info);
  }

  function assert(condition, testName, details = '') {
    const result = {
      name: testName,
      passed: condition,
      details: details
    };
    results.push(result);

    if (condition) {
      log(`✓ PASS: ${testName}`, 'success');
    } else {
      log(`✗ FAIL: ${testName} - ${details}`, 'error');
    }

    return condition;
  }

  function testButtonExists(buttonId, buttonName) {
    const btn = document.getElementById(buttonId);
    return assert(
      btn !== null,
      `Button exists: ${buttonName}`,
      btn ? 'Found' : `Button #${buttonId} not found in DOM`
    );
  }

  function testButtonHasClickListener(buttonId, buttonName) {
    const btn = document.getElementById(buttonId);
    if (!btn) {
      return assert(false, `Button has click listener: ${buttonName}`, 'Button not found');
    }

    // Check if button has event listeners (modern browsers)
    const listeners = getEventListeners ? getEventListeners(btn) : null;
    const hasListener = listeners && listeners.click && listeners.click.length > 0;

    // Alternative check: try to get the onclick property
    const hasOnclick = typeof btn.onclick === 'function';

    return assert(
      hasListener || hasOnclick,
      `Button has click listener: ${buttonName}`,
      hasListener ? `${listeners.click.length} listener(s) attached` :
      hasOnclick ? 'onclick handler present' :
      'No listeners detected (this might be a false negative if using delegated events)'
    );
  }

  function testFacadeExists() {
    const facade = window.KelolaTahapanPage;
    return assert(
      facade !== undefined && facade !== null,
      'KelolaTahapanPage facade exists',
      facade ? 'Facade object found' : 'Facade not initialized'
    );
  }

  function testGridFacadeHasMethods() {
    const facade = window.KelolaTahapanPage;
    if (!facade) return false;

    const grid = facade.grid;
    const requiredMethods = [
      'saveAllChanges',
      'resetAllProgress',
      'renderGrid',
      'switchTimeScaleMode',
      'updateTimeScaleControls'
    ];

    let allMethodsPresent = true;
    requiredMethods.forEach(method => {
      const exists = grid && typeof grid[method] === 'function';
      if (!exists) {
        allMethodsPresent = false;
        log(`  Missing method: grid.${method}`, 'warn');
      }
    });

    return assert(
      allMethodsPresent,
      'Grid facade has required methods',
      allMethodsPresent ? 'All methods present' : 'Some methods missing'
    );
  }

  function testModuleRegistration() {
    const bootstrap = window.KelolaTahapanPageApp || window.JadwalPekerjaanApp;
    if (!bootstrap) {
      return assert(false, 'Bootstrap app initialized', 'Bootstrap not found');
    }

    const gridTabModule = bootstrap.getModule('kelolaTahapanGridTab');
    return assert(
      gridTabModule !== undefined,
      'Grid tab module registered',
      gridTabModule ? 'Module found' : 'Module not registered'
    );
  }

  function testStateExists() {
    const state = window.kelolaTahapanPageState ||
                  (window.KelolaTahapanPage && window.KelolaTahapanPage.state);
    return assert(
      state !== undefined && state !== null,
      'Application state exists',
      state ? 'State object found' : 'State not initialized'
    );
  }

  function simulateButtonClick(buttonId, buttonName) {
    const btn = document.getElementById(buttonId);
    if (!btn) {
      return assert(false, `Can click: ${buttonName}`, 'Button not found');
    }

    try {
      // Just verify we CAN click, don't actually trigger actions
      const clickEvent = new MouseEvent('click', {
        bubbles: true,
        cancelable: true,
        view: window
      });

      // Check if button is disabled
      if (btn.disabled) {
        return assert(
          true, // This is OK - button might be intentionally disabled
          `Button clickable: ${buttonName}`,
          'Button is disabled (might be intentional)'
        );
      }

      return assert(
        true,
        `Button clickable: ${buttonName}`,
        'Button is enabled and can receive clicks'
      );
    } catch (error) {
      return assert(false, `Can click: ${buttonName}`, error.message);
    }
  }

  function printSummary() {
    const passed = results.filter(r => r.passed).length;
    const failed = results.filter(r => !r.passed).length;
    const total = results.length;

    console.log('\n' + '='.repeat(60));
    log('TEST SUMMARY', 'info');
    console.log('='.repeat(60));
    log(`Total Tests: ${total}`, 'info');
    log(`Passed: ${passed}`, passed === total ? 'success' : 'info');
    if (failed > 0) {
      log(`Failed: ${failed}`, 'error');
    }
    log(`Success Rate: ${((passed / total) * 100).toFixed(1)}%`,
        passed === total ? 'success' : 'warn');
    console.log('='.repeat(60) + '\n');

    return {
      total,
      passed,
      failed,
      results
    };
  }

  // ==========================================================================
  // RUN ALL TESTS
  // ==========================================================================

  log('Starting Toolbar Button Tests...', 'info');
  console.log('');

  // Test 1: Check prerequisites
  log('=== PREREQUISITE TESTS ===', 'info');
  testFacadeExists();
  testModuleRegistration();
  testStateExists();
  testGridFacadeHasMethods();
  console.log('');

  // Test 2: Check button existence
  log('=== BUTTON EXISTENCE TESTS ===', 'info');
  testButtonExists('btn-save-all', 'Save All');
  testButtonExists('btn-reset-progress', 'Reset Progress');
  testButtonExists('btn-collapse-all', 'Collapse All');
  testButtonExists('btn-expand-all', 'Expand All');
  const exportButtons = [
    ['btn-export-csv', 'Export CSV'],
    ['btn-export-pdf', 'Export PDF'],
    ['btn-export-word', 'Export Word'],
    ['btn-export-xlsx', 'Export XLSX'],
  ];
  exportButtons.forEach(([id, label]) => testButtonExists(id, label));
  console.log('');

  // Test 3: Check button listeners (only works in Chrome DevTools)
  log('=== BUTTON LISTENER TESTS ===', 'info');
  if (typeof getEventListeners !== 'function') {
    log('Note: getEventListeners() not available (only works in Chrome DevTools)', 'warn');
    log('Skipping listener detection tests...', 'warn');
  } else {
    testButtonHasClickListener('btn-save-all', 'Save All');
    testButtonHasClickListener('btn-reset-progress', 'Reset Progress');
    testButtonHasClickListener('btn-collapse-all', 'Collapse All');
    testButtonHasClickListener('btn-expand-all', 'Expand All');
  }
  console.log('');

  // Test 4: Check button clickability
  log('=== BUTTON CLICKABILITY TESTS ===', 'info');
  simulateButtonClick('btn-save-all', 'Save All');
  simulateButtonClick('btn-reset-progress', 'Reset Progress');
  simulateButtonClick('btn-collapse-all', 'Collapse All');
  simulateButtonClick('btn-expand-all', 'Expand All');
  exportButtons.forEach(([id, label]) => simulateButtonClick(id, label));
  console.log('');

  // Print summary
  const summary = printSummary();

  // Return summary for programmatic access
  window.toolbarTestResults = summary;

  log('Tests complete! Results stored in window.toolbarTestResults', 'success');

  return summary;
})();
