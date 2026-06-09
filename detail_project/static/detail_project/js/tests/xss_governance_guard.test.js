/**
 * XSS Governance Guard — innerHTML Allowlist Test
 *
 * Sprint 2.2: This test maintains an explicit allowlist of all innerHTML
 * callsites in volume_pekerjaan.js. If a new innerHTML usage is added
 * without updating this allowlist, the test will FAIL — prompting the
 * developer to verify escapeHtml() usage before adding to the allowlist.
 *
 * Run: npm run test:frontend -- xss_governance_guard.test.js
 */

import { describe, test, expect, beforeAll } from 'vitest';
import { readFileSync } from 'fs';
import { resolve } from 'path';

let fileContent = '';
let innerHTMLLines = [];

beforeAll(() => {
    const filePath = resolve(
        __dirname,
        '..',
        'volume_pekerjaan.js'
    );
    fileContent = readFileSync(filePath, 'utf-8');
    const lines = fileContent.split('\n');
    innerHTMLLines = [];
    lines.forEach((line, idx) => {
        if (line.includes('innerHTML')) {
            innerHTMLLines.push({ lineNumber: idx + 1, content: line.trim() });
        }
    });
});

/**
 * ALLOWLIST — every innerHTML callsite in volume_pekerjaan.js.
 *
 * Each entry documents:
 * - line: approximate line number (may shift with edits)
 * - context: function or section where it appears
 * - safe: why this callsite is safe
 *
 * To add a new callsite:
 * 1. Verify ALL dynamic values use escapeHtml() or formatIdSmart()
 * 2. Add an entry here with justification
 * 3. Run this test to confirm count matches
 */
const INNERHTML_ALLOWLIST = [
    // showActionToast — escapeHtml(message) + escapeHtml(a.label)
    { context: 'showActionToast', safe: 'escapeHtml on message and label' },
    // search dropdown — static "no results" text
    { context: 'renderSearchDropdown (empty)', safe: 'static string, no user data' },
    // search dropdown — highlightLabel uses escapeHtml on all parts
    { context: 'renderSearchDropdown (results)', safe: 'highlightLabel escapes all segments, it.type is enum' },
    // suggest list — clear
    { context: 'suggest ul.innerHTML = ""', safe: 'clearing content' },
    { context: 'suggest ul.innerHTML = "" (2)', safe: 'clearing content' },
    // suggest list item — li.innerHTML with escapeHtml on user data
    { context: 'suggest li render', safe: 'escapeHtml on label/code' },
    // formula editor view toggle — static icon HTML
    { context: 'formulaEditorViewToggleBtn', safe: 'static icon strings' },
    // renderFormulaToTarget — escapeHtml(emptyText)
    { context: 'renderFormulaToTarget (empty)', safe: 'escapeHtml on emptyText' },
    // renderFormulaToTarget — buildFormulaChipHtml (internal escaping)
    { context: 'renderFormulaToTarget (chips)', safe: 'buildFormulaChipHtml uses escapeHtml internally' },
    // param palette — static empty message
    { context: 'paramPaletteList (empty)', safe: 'static string' },
    // param palette — escapeHtml on code, label, type
    { context: 'paramPaletteList (items)', safe: 'escapeHtml on code/label/type, formatIdSmart on value' },
    // formula highlight overlay — clear
    { context: 'formulaEditorHighlightContent (clear)', safe: 'static &nbsp;' },
    // formula highlight overlay — tokenized HTML (from internal escaping)
    { context: 'formulaEditorHighlightContent (render)', safe: 'internal token escaping' },
    // formula preview
    { context: 'previewEl formula result', safe: 'numeric output, no user string' },
    // renderVarTable — tbody clear
    { context: 'renderVarTable (clear)', safe: 'clearing content' },
    // renderVarTable — empty state
    { context: 'renderVarTable (empty row)', safe: 'static string' },
    // renderVarTable — row with escapeHtml(label), formatIdSmart(val)
    { context: 'renderVarTable (data row)', safe: 'escapeHtml on label, formatIdSmart on value' },
    // renderComputedTable — tbody clear
    { context: 'renderComputedTable (clear)', safe: 'clearing content' },
    // renderComputedTable — empty state
    { context: 'renderComputedTable (empty row)', safe: 'static string' },
    // renderComputedTable — row with escapeHtml on dynamic fields
    { context: 'renderComputedTable (row)', safe: 'escapeHtml on label/formula' },
    // renderComputedTableHistoryRows
    { context: 'renderComputedTableHistoryRows', safe: 'escapeHtml on dynamic fields' },
    // renderComputedTableHistoryRows 2
    { context: 'renderComputedTableHistoryRows (2)', safe: 'escapeHtml on dynamic fields' },
    // showExportMenu — static menu items
    { context: 'showExportMenu', safe: 'static menu HTML, no user data' },
    // renderFormulaOverviewTable — tbody clear
    { context: 'renderFormulaOverviewTable (clear)', safe: 'clearing content' },
    // renderFormulaOverviewTable rows — escapeHtml on labels
    { context: 'renderFormulaOverviewTable (klasifikasi row)', safe: 'escapeHtml on name' },
    { context: 'renderFormulaOverviewTable (sub row)', safe: 'escapeHtml on name' },
    { context: 'renderFormulaOverviewTable (pekerjaan row)', safe: 'escapeHtml on name' },
    // sync indicator — static icon HTML
    { context: 'syncIndicator (syncing)', safe: 'static icon' },
    { context: 'syncIndicator (synced)', safe: 'static icon' },
    { context: 'syncIndicator (clear)', safe: 'clearing content' },
    { context: 'syncIndicator (offline)', safe: 'static icon' },
    { context: 'syncIndicator (error)', safe: 'static icon' },
];

describe('XSS Governance Guard', () => {
    test('innerHTML callsite count matches allowlist', () => {
        const actual = innerHTMLLines.length;
        const expected = INNERHTML_ALLOWLIST.length;

        if (actual !== expected) {
            // Find which lines are new/removed
            console.log(`\nInnerHTML callsites found (${actual}):`);
            innerHTMLLines.forEach(({ lineNumber, content }) => {
                console.log(`  L${lineNumber}: ${content.substring(0, 100)}`);
            });
        }

        expect(actual).toBe(expected);
    });

    test('every callsite that uses dynamic data has escapeHtml nearby', () => {
        // Check: for each non-clearing, non-static innerHTML line,
        // verify escapeHtml appears in the surrounding context
        const dynamicCallsites = innerHTMLLines.filter(({ content }) => {
            // Skip clearing (= '';  = '&nbsp;') and static icon assignments
            if (content.match(/innerHTML\s*=\s*'[^$]*';?\s*$/)) return false;
            if (content.match(/innerHTML\s*=\s*'';?\s*$/)) return false;
            return true;
        });

        const lines = fileContent.split('\n');
        const missingEscape = [];

        dynamicCallsites.forEach(({ lineNumber, content }) => {
            // Check 15 lines around the callsite for escapeHtml usage
            const start = Math.max(0, lineNumber - 5);
            const end = Math.min(lines.length, lineNumber + 15);
            const context = lines.slice(start, end).join('\n');

            const hasEscape = context.includes('escapeHtml') ||
                context.includes('formatIdSmart') ||
                context.includes('buildFormulaChipHtml') ||
                context.includes('highlightLabel') ||
                context.includes('buildUsageBadgeHtml');

            // Also safe: static template with only class/icon elements (no ${} variables with user data)
            const hasTemplateLiteral = content.includes('${');
            if (hasTemplateLiteral && !hasEscape) {
                missingEscape.push({ lineNumber, content: content.substring(0, 120) });
            }
        });

        if (missingEscape.length > 0) {
            console.log('\nInnerHTML callsites with template literals but no escapeHtml:');
            missingEscape.forEach(({ lineNumber, content }) => {
                console.log(`  ⚠ L${lineNumber}: ${content}`);
            });
        }

        // Currently all dynamic callsites use escapeHtml or safe helpers
        expect(missingEscape.length).toBe(0);
    });

    test('escapeHtml function exists and is defined', () => {
        expect(fileContent).toContain('function escapeHtml');
    });
});
