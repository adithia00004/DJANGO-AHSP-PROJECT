#!/usr/bin/env python3
"""
Simple script to remove legacy Gantt V2 code using line-based approach
"""

file_path = r"D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\src\jadwal_kegiatan_app.js"

# Read all lines
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Step 1: Remove _initializeFrozenGantt method (lines 1804-1825, 0-indexed: 1803-1824)
# This removes 22 lines
lines_to_remove_frozen = range(1803, 1826)  # 1804-1825 inclusive

# Step 2: Simplify _initializeRedesignedGantt (lines 1744-1802, 0-indexed: 1743-1801)
# Replace the entire method

# Create the new simplified method
new_method_lines = '''  async _initializeRedesignedGantt(retryCount = 0) {
    const MAX_RETRIES = 3;
    const RETRY_DELAY = 200; // ms

    console.log('[JadwalKegiatanApp] Rendering Gantt via unified table overlay');

    // Wait a bit for DOM to be ready (Bootstrap tab transition)
    if (retryCount === 0) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    const ganttContainer = document.getElementById('gantt-redesign-container');

    if (!ganttContainer) {
      console.warn(`[JadwalKegiatanApp] ⏳ Gantt container not found (attempt ${retryCount + 1}/${MAX_RETRIES})`);

      // Retry if not max retries
      if (retryCount < MAX_RETRIES) {
        console.log(`[JadwalKegiatanApp] Retrying in ${RETRY_DELAY}ms...`);
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));
        return this._initializeRedesignedGantt(retryCount + 1);
      }

      console.error('[JadwalKegiatanApp] ❌ Gantt container not found after retries');
      console.error('[JadwalKegiatanApp] DOM state:', {
        ganttView: document.getElementById('gantt-view'),
        ganttTab: document.getElementById('gantt-tab')
      });
      Toast.error('Failed to find Gantt container');
      return;
    }

    try {
      await this._initializeUnifiedGanttOverlay(ganttContainer);
    } catch (error) {
      console.error('[JadwalKegiatanApp] ❌ Failed to initialize Gantt:', error);
      console.error('[JadwalKegiatanApp] Error stack:', error.stack);
      Toast.error('Failed to load Gantt Chart');
      throw error;
    }
  }
'''.split('\n')

# Build new file content
new_lines = []

# Copy lines before _initializeRedesignedGantt
new_lines.extend(lines[:1743])  # Lines 1-1743

# Add the new simplified method
new_lines.extend([line + '\n' for line in new_method_lines])

# Skip old method lines (1744-1802) and _initializeFrozenGantt (1804-1825)
# Continue from line 1826 (0-indexed: 1825)
new_lines.extend(lines[1825:])

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Removed {len(lines_to_remove_frozen)} lines (_initializeFrozenGantt)")
print(f"Simplified _initializeRedesignedGantt method")
print(f"Original: {len(lines)} lines")
print(f"New: {len(new_lines)} lines")
print(f"Removed: {len(lines) - len(new_lines)} lines total")
