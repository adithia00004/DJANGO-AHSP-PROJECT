"""
Gantt Legacy Cleanup Script
============================

Removes legacy dual-panel Gantt files and archives documentation.

Run ONLY after frozen column migration is complete and tested!

Usage:
    python cleanup_gantt_legacy.py [--dry-run]

Options:
    --dry-run    Show what would be deleted/archived without actually doing it
"""

import os
import shutil
import sys
from pathlib import Path
from datetime import datetime

# Fix unicode encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Base directory
BASE_DIR = Path(__file__).parent

# Files to DELETE (dual-panel components)
FILES_TO_DELETE = [
    'detail_project/static/detail_project/js/src/modules/gantt/gantt-tree-panel.js',
    'detail_project/static/detail_project/js/src/modules/gantt/gantt-timeline-panel.js',
    'detail_project/static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/gantt_module.js',
    'detail_project/static/detail_project/js/jadwal_pekerjaan/kelola_tahapan/gantt_tab.js',
]

# Directories to DELETE (staticfiles - will regenerate)
DIRS_TO_DELETE = [
    'staticfiles/detail_project/js/src/modules/gantt',
    'staticfiles/detail_project/js/jadwal_pekerjaan/kelola_tahapan',
]

# Files to ARCHIVE (move to docs/archive/gantt/dual-panel/)
FILES_TO_ARCHIVE = [
    'detail_project/GANTT_CHART_REDESIGN_PLAN.md',
    'detail_project/GANTT_CHART_IMPLEMENTATION_COMPLETE.md',
    'detail_project/GANTT_FIX_APPLIED.md',
    'detail_project/GANTT_CONTAINER_FIX.md',
    'detail_project/GANTT_DATA_LOADING_FIX.md',
    'detail_project/GANTT_RENDERING_FIX.md',
    'detail_project/GANTT_LAYOUT_FIX.md',
    'detail_project/GANTT_FIXES_BATCH_1.md',
    'detail_project/GANTT_COMPREHENSIVE_FIXES.md',
    'detail_project/GANTT_UNKNOWN_NAMES_FIX.md',
    'detail_project/GANTT_CRITICAL_FIXES_BATCH_2.md',
    'detail_project/GANTT_TRANSITION_STRATEGY.md',
    'detail_project/GANTT_V2_POC_SETUP_COMPLETE.md',
    'detail_project/GANTT_V2_TOGGLE_FIX.md',
    'detail_project/GANTT_V2_TRANSITION_COMPLETE.md',
    'detail_project/GANTT_V2_PHASE_2_COMPLETE.md',
    'detail_project/docs/GANTT_CANVAS_OVERLAY_ROADMAP.md',  # Old roadmap
]

# Archive directory
ARCHIVE_DIR = BASE_DIR / 'docs' / 'archive' / 'gantt' / 'dual-panel'


def print_header(message):
    """Print formatted header"""
    print("\n" + "=" * 70)
    print(f"  {message}")
    print("=" * 70)


def print_section(message):
    """Print section header"""
    print(f"\n{message}")
    print("-" * 70)


def confirm_action(dry_run=False):
    """Ask user to confirm cleanup"""
    if dry_run:
        print("\n🔍 DRY RUN MODE - No files will be modified")
        return True

    print_section("⚠️  WARNING: This will DELETE and ARCHIVE files!")
    print("\nFiles to DELETE:")
    for f in FILES_TO_DELETE:
        status = "✅ exists" if (BASE_DIR / f).exists() else "⚠️  not found"
        print(f"  - {f} ({status})")

    print("\nDirectories to DELETE:")
    for d in DIRS_TO_DELETE:
        status = "✅ exists" if (BASE_DIR / d).exists() else "⚠️  not found"
        print(f"  - {d} ({status})")

    print("\nFiles to ARCHIVE:")
    for f in FILES_TO_ARCHIVE:
        status = "✅ exists" if (BASE_DIR / f).exists() else "⚠️  not found"
        print(f"  - {f} ({status})")

    print(f"\nArchive location: {ARCHIVE_DIR.relative_to(BASE_DIR)}")

    response = input("\n❓ Continue with cleanup? (yes/no): ").strip().lower()
    return response == 'yes'


def create_cleanup_report(deleted_files, deleted_dirs, archived_files, dry_run=False):
    """Create cleanup report file"""
    report_path = ARCHIVE_DIR / 'CLEANUP_REPORT.md'

    mode = "DRY RUN" if dry_run else "ACTUAL"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# Gantt Legacy Cleanup Report ({mode})

**Date:** {timestamp}
**Script:** cleanup_gantt_legacy.py
**Mode:** {'Dry Run (no changes made)' if dry_run else 'Actual Cleanup'}

---

## Summary

- **Files Deleted:** {len(deleted_files)}
- **Directories Deleted:** {len(deleted_dirs)}
- **Files Archived:** {len(archived_files)}

---

## Files Deleted

"""

    if deleted_files:
        for f in deleted_files:
            report += f"- `{f}`\n"
    else:
        report += "None\n"

    report += "\n---\n\n## Directories Deleted\n\n"

    if deleted_dirs:
        for d in deleted_dirs:
            report += f"- `{d}`\n"
    else:
        report += "None\n"

    report += "\n---\n\n## Files Archived\n\n"

    if archived_files:
        for src, dest in archived_files:
            report += f"- `{src}` → `{dest}`\n"
    else:
        report += "None\n"

    report += """

---

## Restoration

If you need to restore these files:

1. Check the archive directory: `docs/archive/gantt/dual-panel/`
2. Documentation files are preserved there
3. Code files are deleted (restore from git if needed)

```bash
# Restore from git (if needed)
git checkout HEAD -- detail_project/static/detail_project/js/src/modules/gantt/gantt-tree-panel.js
git checkout HEAD -- detail_project/static/detail_project/js/src/modules/gantt/gantt-timeline-panel.js
```

---

## Next Steps

After cleanup:

1. Run tests: `npm run test:frontend`
2. Build assets: `npm run build`
3. Collect static: `python manage.py collectstatic --no-input`
4. Verify Gantt chart works
5. Commit changes

---

**Cleanup by:** cleanup_gantt_legacy.py
**Date:** {timestamp}
"""

    if not dry_run:
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        print(f"  ✅ Cleanup report saved: {report_path.relative_to(BASE_DIR)}")
    else:
        print(f"  📄 Would save report to: {report_path.relative_to(BASE_DIR)}")

    return report


def main():
    """Main cleanup function"""
    # Check for dry-run flag
    dry_run = '--dry-run' in sys.argv

    # Print header
    print_header("🧹 Gantt Legacy Cleanup Script")

    if not confirm_action(dry_run):
        print("\n❌ Cleanup cancelled by user")
        return

    print_section("🚀 Starting cleanup...")

    # Create archive directory
    if not dry_run:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        print(f"✅ Archive directory created: {ARCHIVE_DIR.relative_to(BASE_DIR)}")
    else:
        print(f"📁 Would create archive directory: {ARCHIVE_DIR.relative_to(BASE_DIR)}")

    # Track actions
    deleted_files = []
    deleted_dirs = []
    archived_files = []

    # Delete files
    print_section("📁 Deleting legacy files...")
    for file_path in FILES_TO_DELETE:
        full_path = BASE_DIR / file_path
        if full_path.exists():
            if not dry_run:
                full_path.unlink()
                print(f"  ✅ Deleted: {file_path}")
                deleted_files.append(file_path)
            else:
                print(f"  🔍 Would delete: {file_path}")
                deleted_files.append(file_path)
        else:
            print(f"  ⚠️  Not found (skip): {file_path}")

    # Delete directories
    print_section("📁 Deleting legacy directories...")
    for dir_path in DIRS_TO_DELETE:
        full_path = BASE_DIR / dir_path
        if full_path.exists():
            if not dry_run:
                shutil.rmtree(full_path)
                print(f"  ✅ Deleted: {dir_path}")
                deleted_dirs.append(dir_path)
            else:
                print(f"  🔍 Would delete: {dir_path}")
                deleted_dirs.append(dir_path)
        else:
            print(f"  ⚠️  Not found (skip): {dir_path}")

    # Archive documentation
    print_section("📁 Archiving legacy documentation...")
    for file_path in FILES_TO_ARCHIVE:
        full_path = BASE_DIR / file_path
        if full_path.exists():
            dest = ARCHIVE_DIR / Path(file_path).name
            if not dry_run:
                shutil.move(str(full_path), str(dest))
                print(f"  ✅ Archived: {file_path}")
                print(f"     → {dest.relative_to(BASE_DIR)}")
                archived_files.append((file_path, dest.relative_to(BASE_DIR)))
            else:
                print(f"  🔍 Would archive: {file_path}")
                print(f"     → {dest.relative_to(BASE_DIR)}")
                archived_files.append((file_path, dest.relative_to(BASE_DIR)))
        else:
            print(f"  ⚠️  Not found (skip): {file_path}")

    # Create cleanup report
    print_section("📋 Creating cleanup report...")
    create_cleanup_report(deleted_files, deleted_dirs, archived_files, dry_run)

    # Summary
    print_header("✅ Cleanup Complete!")
    print(f"\n📊 Summary:")
    print(f"  - Files deleted: {len(deleted_files)}")
    print(f"  - Directories deleted: {len(deleted_dirs)}")
    print(f"  - Files archived: {len(archived_files)}")

    if dry_run:
        print(f"\n🔍 DRY RUN - No actual changes were made")
        print(f"   Run without --dry-run to perform actual cleanup")
    else:
        print(f"\n📁 Archived files location: {ARCHIVE_DIR.relative_to(BASE_DIR)}")
        print(f"\n🎯 Next steps:")
        print(f"  1. Verify Gantt chart still works")
        print(f"  2. Run: npm run test:frontend")
        print(f"  3. Run: npm run build")
        print(f"  4. Run: python manage.py collectstatic --no-input")
        print(f"  5. Commit changes")

    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cleanup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
