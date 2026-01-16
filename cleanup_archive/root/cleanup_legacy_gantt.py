#!/usr/bin/env python3
"""
Script to remove legacy Gantt V2 code from jadwal_kegiatan_app.js
"""

import re

# Read the file
file_path = r"D:\PORTOFOLIO ADIT\DJANGO AHSP PROJECT\detail_project\static\detail_project\js\src\jadwal_kegiatan_app.js"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1: Remove _initializeFrozenGantt method (lines 1804-1825)
pattern1 = r'''  /\*\*
   \* Initialize V2: Frozen Column Gantt \(Now Default\)
   \* @private
   \*/
  async _initializeFrozenGantt\(container\) \{
    console\.log\('\[JadwalKegiatanApp\] ✅ Container found:', container\);

    // Lazy load V2 module
    const \{ GanttFrozenGrid \} = await import\('@modules/gantt-v2/gantt-frozen-grid\.js'\);

    // Create Gantt instance
    this\.ganttFrozenGrid = new GanttFrozenGrid\(container, \{
      rowHeight: 40,
      timeScale: 'week'
    \}\);

    // Initialize with app context \(provides StateManager, tahapanList, etc\.\)
    await this\.ganttFrozenGrid\.initialize\(this\);

    console\.log\('\[JadwalKegiatanApp\] ✅ Gantt V2 \(Frozen Column\) initialized successfully!'\);
    Toast\.success\('📊 Gantt Chart loaded', 2000\);
  \}'''

content = re.sub(pattern1, '', content, flags=re.MULTILINE)

# Pattern 2: Simplify _initializeRedesignedGantt method
old_method = r'''  async _initializeRedesignedGantt\(retryCount = 0\) \{
    const MAX_RETRIES = 3;
    const RETRY_DELAY = 200; // ms

    if \(this\.state\.useUnifiedTable && this\.state\.keepLegacyGantt === false\) \{
      console\.log\('\[JadwalKegiatanApp\] Unified mode active - rendering Gantt via unified table overlay'\);
      const ganttContainer = document\.getElementById\('gantt-redesign-container'\);
      if \(!ganttContainer\) \{
        console\.warn\('\[JadwalKegiatanApp\] Gantt container not found for unified overlay'\);
        return;
      \}
      await this\._initializeUnifiedGanttOverlay\(ganttContainer\);
      return;
    \}

    // Check if already initialized
    if \(this\.ganttFrozenGrid\) \{
      console\.log\('\[JadwalKegiatanApp\] Gantt already initialized, skipping'\);
      return;
    \}

    // Wait a bit for DOM to be ready \(Bootstrap tab transition\)
    if \(retryCount === 0\) \{
      await new Promise\(resolve => setTimeout\(resolve, 100\)\);
    \}

    const ganttContainer = document\.getElementById\('gantt-redesign-container'\);

    if \(!ganttContainer\) \{
      console\.warn\(`\[JadwalKegiatanApp\] ⏳ Gantt container not found \(attempt \$\{retryCount \+ 1\}/\$\{MAX_RETRIES\}\)`\);

      // Retry if not max retries
      if \(retryCount < MAX_RETRIES\) \{
        console\.log\(`\[JadwalKegiatanApp\] Retrying in \$\{RETRY_DELAY\}ms\.\.\\.`\);
        await new Promise\(resolve => setTimeout\(resolve, RETRY_DELAY\)\);
        return this\._initializeRedesignedGantt\(retryCount \+ 1\);
      \}

      console\.error\('\[JadwalKegiatanApp\] ❌ Gantt container not found after retries'\);
      console\.error\('\[JadwalKegiatanApp\] DOM state:', \{
        ganttView: document\.getElementById\('gantt-view'\),
        ganttTab: document\.getElementById\('gantt-tab'\)
      \}\);
      Toast\.error\('Failed to find Gantt container'\);
      return;
    \}

    try \{
      // Initialize V2: Frozen Column Architecture \(now default\)
      console\.log\('🚀 Initializing Gantt V2 \(Frozen Column\)\.\.\.'\);
      await this\._initializeFrozenGantt\(ganttContainer\);

    \} catch \(error\) \{
      console\.error\('\[JadwalKegiatanApp\] ❌ Failed to initialize Gantt:', error\);
      console\.error\('\[JadwalKegiatanApp\] Error stack:', error\.stack\);
      Toast\.error\('Failed to load Gantt Chart'\);
      throw error;
    \}
  \}'''

new_method = '''  async _initializeRedesignedGantt(retryCount = 0) {
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
  }'''

content = re.sub(old_method, new_method, content, flags=re.MULTILINE)

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully removed legacy Gantt V2 code")
print("Simplified _initializeRedesignedGantt to always use unified overlay")
