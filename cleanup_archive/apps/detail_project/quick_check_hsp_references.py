#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Quick Check Script: Find Potential Issues After HSP Fix

Scans files for references to old variable names and formulas that may need updating.

Usage:
    python quick_check_hsp_references.py
"""

import os
import re
from pathlib import Path

# Base directory - automatically detect from script location
SCRIPT_DIR = Path(__file__).parent
BASE_DIR = SCRIPT_DIR  # detail_project/

# Patterns to search for (potential issues)
PATTERNS = {
    "old_variable_sD": {
        "pattern": r'\bsD\s*=',
        "description": "Old variable name 'sD' (should be 'LAIN')",
        "severity": "HIGH",
        "files": ["*.js"],
    },
    "old_label_G_HSP": {
        "pattern": r'G\s*[—-]\s*HSP',
        "description": "Old label 'G — HSP' (should be 'G — Harga Satuan')",
        "severity": "MEDIUM",
        "files": ["*.js", "*.html", "*.md"],
    },
    "old_label_D_Lainnya": {
        "pattern": r'D\s*[—-]\s*Lainnya',
        "description": "Old label 'D — Lainnya' (should be 'LAIN — Lainnya')",
        "severity": "MEDIUM",
        "files": ["*.js", "*.html"],
    },
    "old_formula_ABCD": {
        "pattern": r'A\s*\+\s*B\s*\+\s*C\s*\+\s*D\b',
        "description": "Old formula 'A+B+C+D' (should be 'A+B+C+LAIN')",
        "severity": "LOW",
        "files": ["*.js", "*.py", "*.md"],
    },
    "hsp_overwrite": {
        "pattern": r'HSP["\']?\s*=\s*d_direct|HSP["\']?\s*=\s*D\b',
        "description": "HSP being overwritten with D (CRITICAL BUG!)",
        "severity": "CRITICAL",
        "files": ["*.py"],
    },
    "const_E_not_E_base": {
        "pattern": r'\bconst\s+E\s*=\s*sA\s*\+\s*sB\s*\+\s*sC\s*\+\s*sD',
        "description": "Old: 'const E = sA+sB+sC+sD' (should be 'const E_base = A+B+C+LAIN')",
        "severity": "HIGH",
        "files": ["*.js"],
    },
}

# Directories to exclude
EXCLUDE_DIRS = {
    '__pycache__',
    'node_modules',
    '.git',
    'migrations',
    'static/detail_project/js/vendor',
    'static/detail_project/css/vendor',
}

# Files to exclude (already fixed)
EXCLUDE_FILES = {
    'views_api.py.backup',
    'rincian_ahsp.js',  # Already fixed
    'views_api.py',     # Already fixed (but check for confirmation)
}


def should_skip(file_path):
    """Check if file should be skipped"""
    # Check if in excluded directory
    for exc_dir in EXCLUDE_DIRS:
        if exc_dir in file_path.parts:
            return True

    # Check if excluded file
    if file_path.name in EXCLUDE_FILES:
        return True

    return False


def search_file(file_path, pattern_info):
    """Search for pattern in file"""
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            matches = list(re.finditer(pattern_info['pattern'], content, re.IGNORECASE))

            if matches:
                return {
                    'file': str(file_path.relative_to(BASE_DIR)),
                    'matches': len(matches),
                    'lines': [content[:m.start()].count('\n') + 1 for m in matches],
                }
    except Exception as e:
        print(f"⚠️  Error reading {file_path}: {str(e)}")

    return None


def scan_directory():
    """Scan directory for all patterns"""
    print("=" * 100)
    print("QUICK CHECK: HSP Fix - Potential Issues Scanner")
    print("=" * 100)
    print(f"\nScanning: {BASE_DIR}")
    print(f"Patterns: {len(PATTERNS)}")
    print(f"\n{'-' * 100}\n")

    results = {pattern_name: [] for pattern_name in PATTERNS}

    # Scan all files
    for pattern_name, pattern_info in PATTERNS.items():
        print(f"🔍 Searching for: {pattern_info['description']}")
        print(f"   Severity: {pattern_info['severity']}")
        print(f"   Pattern: {pattern_info['pattern']}")

        for file_ext in pattern_info['files']:
            ext = file_ext.replace('*', '')

            for file_path in BASE_DIR.rglob(file_ext):
                if should_skip(file_path):
                    continue

                result = search_file(file_path, pattern_info)
                if result:
                    results[pattern_name].append(result)

        if results[pattern_name]:
            print(f"   [WARN] Found {len(results[pattern_name])} file(s) with matches\n")
        else:
            print(f"   [OK] No matches found\n")

    # Print summary
    print("=" * 100)
    print("SUMMARY REPORT")
    print("=" * 100)

    total_issues = sum(len(files) for files in results.values())

    if total_issues == 0:
        print("\nNO ISSUES FOUND! All files look good!\n")
        return

    print(f"\nFound issues in {total_issues} file(s)\n")

    # Group by severity
    by_severity = {'CRITICAL': [], 'HIGH': [], 'MEDIUM': [], 'LOW': []}

    for pattern_name, files in results.items():
        if files:
            severity = PATTERNS[pattern_name]['severity']
            by_severity[severity].append({
                'pattern': pattern_name,
                'description': PATTERNS[pattern_name]['description'],
                'files': files,
            })

    # Print by severity
    for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        if by_severity[severity]:
            icon = "[CRITICAL]" if severity == 'CRITICAL' else "[WARNING]"
            print(f"\n{icon}  {severity} SEVERITY ({len(by_severity[severity])} issue type(s))")
            print("-" * 100)

            for issue in by_severity[severity]:
                print(f"\n   Issue: {issue['description']}")
                print(f"   Pattern: {issue['pattern']}")
                print(f"   Files affected: {len(issue['files'])}")

                for file_info in issue['files'][:5]:  # Max 5 files per issue
                    lines_str = ', '.join(map(str, file_info['lines'][:3]))
                    if len(file_info['lines']) > 3:
                        lines_str += f", ... (+{len(file_info['lines']) - 3} more)"

                    print(f"      - {file_info['file']}")
                    print(f"        Lines: {lines_str}")
                    print(f"        Matches: {file_info['matches']}")

                if len(issue['files']) > 5:
                    print(f"      ... and {len(issue['files']) - 5} more file(s)")

    # Recommendations
    print("\n" + "=" * 100)
    print("RECOMMENDATIONS")
    print("=" * 100)

    if by_severity['CRITICAL']:
        print("\n[CRITICAL] CRITICAL ISSUES FOUND!")
        print("   These are bugs that MUST be fixed immediately:")
        for issue in by_severity['CRITICAL']:
            print(f"   - {issue['description']}")
        print("\n   Action: Review and fix these files ASAP!")

    if by_severity['HIGH']:
        print("\n[WARNING] HIGH PRIORITY ISSUES:")
        print("   These may cause incorrect behavior:")
        for issue in by_severity['HIGH']:
            print(f"   - {issue['description']}")
        print("\n   Action: Review and update variable names for consistency")

    if by_severity['MEDIUM']:
        print("\n[WARNING] MEDIUM PRIORITY ISSUES:")
        print("   These are cosmetic/label issues:")
        for issue in by_severity['MEDIUM']:
            print(f"   - {issue['description']}")
        print("\n   Action: Update labels for clarity (not critical)")

    if by_severity['LOW']:
        print("\n[INFO] LOW PRIORITY ISSUES:")
        print("   These may be in documentation or comments:")
        for issue in by_severity['LOW']:
            print(f"   - {issue['description']}")
        print("\n   Action: Update for consistency when convenient")

    print("\n" + "=" * 100)
    print("\nFor detailed review checklist, see: FILES_TO_REVIEW_AFTER_HSP_FIX.md")
    print("=" * 100 + "\n")


if __name__ == '__main__':
    scan_directory()
