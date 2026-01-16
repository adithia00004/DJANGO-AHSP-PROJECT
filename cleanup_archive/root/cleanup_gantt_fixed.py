#!/usr/bin/env python3
"""
Fixed script to remove legacy Gantt V2 code
"""

file_path = r"D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\src\jadwal_kegiatan_app.js"

# Read all lines
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Step 1: Remove _initializeFrozenGantt method (lines 1804-1825, 0-indexed: 1803-1824)
# Lines 1804-1825 inclusive = indices 1803-1824
# BUT there's also a blank line at 1826, so remove 1803-1825 inclusive (indices 1803-1825)

# Step 2: Simplify _initializeRedesignedGantt (lines 1744-1802, 0-indexed: 1743-1801)
# We need to replace lines 1744-1802 (59 lines)

# New simplified method (will be 44 lines instead of 59)
new_method_lines = [
    "  async _initializeRedesignedGantt(retryCount = 0) {\n",
    "    const MAX_RETRIES = 3;\n",
    "    const RETRY_DELAY = 200; // ms\n",
    "\n",
    "    console.log('[JadwalKegiatanApp] Rendering Gantt via unified table overlay');\n",
    "\n",
    "    // Wait a bit for DOM to be ready (Bootstrap tab transition)\n",
    "    if (retryCount === 0) {\n",
    "      await new Promise(resolve => setTimeout(resolve, 100));\n",
    "    }\n",
    "\n",
    "    const ganttContainer = document.getElementById('gantt-redesign-container');\n",
    "\n",
    "    if (!ganttContainer) {\n",
    "      console.warn(`[JadwalKegiatanApp] ⏳ Gantt container not found (attempt ${retryCount + 1}/${MAX_RETRIES})`);\n",
    "\n",
    "      // Retry if not max retries\n",
    "      if (retryCount < MAX_RETRIES) {\n",
    "        console.log(`[JadwalKegiatanApp] Retrying in ${RETRY_DELAY}ms...`);\n",
    "        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY));\n",
    "        return this._initializeRedesignedGantt(retryCount + 1);\n",
    "      }\n",
    "\n",
    "      console.error('[JadwalKegiatanApp] ❌ Gantt container not found after retries');\n",
    "      console.error('[JadwalKegiatanApp] DOM state:', {\n",
    "        ganttView: document.getElementById('gantt-view'),\n",
    "        ganttTab: document.getElementById('gantt-tab')\n",
    "      });\n",
    "      Toast.error('Failed to find Gantt container');\n",
    "      return;\n",
    "    }\n",
    "\n",
    "    try {\n",
    "      await this._initializeUnifiedGanttOverlay(ganttContainer);\n",
    "    } catch (error) {\n",
    "      console.error('[JadwalKegiatanApp] ❌ Failed to initialize Gantt:', error);\n",
    "      console.error('[JadwalKegiatanApp] Error stack:', error.stack);\n",
    "      Toast.error('Failed to load Gantt Chart');\n",
    "      throw error;\n",
    "    }\n",
    "  }\n",
    "\n",
]

# Build new file content
new_lines = []

# Part 1: Lines before _initializeRedesignedGantt (1-1743)
new_lines.extend(lines[:1743])  # 0-1742

# Part 2: New simplified _initializeRedesignedGantt method
new_lines.extend(new_method_lines)

# Part 3: Skip old _initializeRedesignedGantt (1744-1802) and _initializeFrozenGantt (1804-1825)
# Continue from _initializeUnifiedGanttOverlay which is at line 1827 (index 1826)
new_lines.extend(lines[1826:])

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Original: {len(lines)} lines")
print(f"New: {len(new_lines)} lines")
print(f"Removed: {len(lines) - len(new_lines)} lines total")
print("Successfully cleaned up legacy Gantt V2 code!")
