## Roadmap Refactor Gantt Canvas Overlay (Freeze-safe)

Dokumen ini memandu refactor total mode Gantt agar kanvas barchart tidak pernah menimpa kolom freeze. Berisi arsitektur baru, langkah backend/frontend, pengelolaan memori/visual, serta plan testing dan rollout yang bisa dilacak tim.

### Prinsip Arsitektur Baru
- Pisah pane kiri (freeze) dan pane kanan (timeline) secara fisik. Pane kanan saja yang memiliki scroll horizontal dan menampung kanvas.
- Hitung lebar freeze (`pinnedWidth`) satu kali di grid manager, kirim ke overlay sebagai kontrak eksplisit (bukan tersirat lewat CSS).
- Koordinat sel (cellRects) dan bar di-offset dengan `-pinnedWidth` sebelum digambar sehingga kanvas selalu mulai dari x=0 di pane kanan.
- Observability wajib: setiap sinkronisasi publikasikan metrik overlay (pinnedWidth, viewport, barsDrawn/skipped) untuk audit otomatis.

### Target Keberhasilan (Acceptance)
1) Secara visual: bar kanvas tidak pernah muncul di area freeze pada semua level zoom/scroll.
2) Secara metrik: `barsSkipped` bertambah saat bar berada di area freeze, dan `GanttOverlayMetrics.clipLeft === pinnedWidth`.
3) Uji otomatis: semua tes overlay lulus dan mencakup kasus freeze/viewport.
4) Beban kinerja: render dan hit-test tetap O(n) per refresh, tanpa lonjakan memori pada data real.

### Rencana Teknis Frontend
1) Layout ulang container
   - Tambah wrapper `gantt-shell` dengan dua pane: `.gantt-left` (freeze) dan `.gantt-right.timeline-scroll` (overflow-x: auto).
   - Pindahkan kanvas ke dalam `.timeline-scroll`; jangan tempatkan di wrapper yang sama dengan freeze.
   - CSS: `.gantt-left { position: sticky; left: 0; z-index: 5; }`, `.timeline-scroll { position: relative; overflow: auto; flex: 1; }`, `.gantt-canvas { position: absolute; top: 0; left: 0; z-index: 1; }`.
2) Overlay API dan koordinat
   - `tableManager` menyediakan `getPinnedColumnsWidth()` dan `getTimelineCellRects()` yang sudah dipisah untuk pane kanan.
   - `syncWithTable()`:
     - `timelineWidth = scrollArea.scrollWidth - pinnedWidth`
     - `canvas.width = timelineWidth`, `canvas.height = scrollArea.scrollHeight`
     - Offset semua rect: `x' = rect.x - pinnedWidth`
   - `_drawBars()` dan `_drawDependencies()` memakai rect yang sudah di-offset; `barRects` disimpan dalam koordinat kanvas.
3) Scroll sinkron
   - Sumber kebenaran scroll horizontal hanya dari `.timeline-scroll`.
   - Saat scroll: set `bodyScroll.scrollLeft = pinnedWidth + timelineScroll.scrollLeft` agar grid virtual tetap selaras.
   - Mousewheel/drag di grid kanan diarahkan ke `.timeline-scroll`.
4) Observability
   - `window.GanttOverlayMetrics = { pinnedWidth, viewportLeft, viewportWidth, clipLeft, barsDrawn, barsSkipped, cellRects }` pada setiap sync.
   - Tambah hook optional `onOverlayMetrics(metrics)` untuk integrasi logging.
5) Styling dan z-index
   - Pastikan tidak ada `clip-path` atau masker: keamanan freeze dijamin oleh pemisahan pane.
   - Pinned header/cell tetap memiliki `z-index` > kanvas (mis. 5 untuk header, 4 untuk cell).

### Rencana Backend
1) Endpoint data Gantt tetap; pastikan payload waktu/pekerjaan menyediakan info yang cukup untuk membangun cellRects kanan.
2) Tambah field opsional `pinnedWidth` di response layout (jika backend mengetahuinya), atau tetap dihitung di frontend jika tidak tersedia.
3) Logging server: terima event metrik (opsional) dari frontend untuk audit jika diperlukan.

### Pengelolaan Memori & Kinerja
1) Gunakan satu kanvas untuk pane kanan; jangan menggandakan di kiri.
2) Simpan `barRects` hanya untuk bar yang tergambar (setelah filter viewport).
3) Hindari reflow: gunakan `requestAnimationFrame` pada sinkronisasi scroll jika perlu debounce.
4) Validasi pada dataset besar (>= 200 kolom, 200 bar) untuk memastikan frame time stabil.

### Rencana Visual & UX
1) Freeze harus selalu menindih bar: verifikasi manual pada semua tema (light/dark).
2) Tooltip/hit-test hanya aktif di pane kanan; koordinat disesuaikan dengan offset kanvas.
3) Dependency arrows digambar di pane kanan; panah tidak boleh melewati batas freeze.

### Testing Plan
- Unit/Integration (Vitest, happy-dom):
  - `syncWithTable` mengatur `canvas.width = scrollWidth - pinnedWidth`.
  - `_drawBars` meng-offset rect dan men-skip bar di area freeze.
  - `GanttOverlayMetrics` terpublikasi dan mencerminkan `pinnedWidth`/`clipLeft`.
- Manual QA checklist:
  - Scroll horizontal penuh: bar tidak muncul di kiri.
  - Resize jendela: freeze tetap menutup area kiri.
  - Tooltip mengikuti bar setelah offset.
  - Dependency arrows tidak menembus freeze.
- Performance check:
  - Ukur frame time saat scroll dengan dataset besar.
  - Profil memori: barRects tidak tumbuh di luar jumlah bar ter-render.

### Rollout & Tracking
1) Implementasi bertahap di branch khusus `feature/gantt-pane-split`.
2) Pasang flag (opsional) `USE_SPLIT_GANTT_OVERLAY` untuk toggle di staging.
3) Checklist sebelum merge:
   - Semua tes overlay hijau.
   - Manual QA lulus pada Chrome/Edge.
   - Metrik `barsSkipped` > 0 ketika bar berada di area freeze (kasus uji eksplisit).
4) Setelah deploy: pantau log metrik overlay (jika diaktifkan) selama 1–2 hari.

### Langkah Kerja Berikutnya
1) Ubah layout DOM sesuai desain pane split.
2) Refactor `GanttCanvasOverlay` ke sumber scroll kanan, offset koordinat, buang clip-path/masker.
3) Update `tableManager` agar menyediakan rect hanya untuk pane kanan atau menyediakan offset untuk kanan.
4) Sesuaikan test `gantt-canvas-overlay.test.js` dengan arsitektur baru (pane kanan, offset).
5) QA manual dengan dataset nyata dan catat metrik via konsol (`window.GanttOverlayMetrics`).

Dokumen ini dapat diperbarui setiap milestone (layout selesai, sync offset selesai, testing selesai, rollout). Tambahkan catatan status di tiap langkah untuk pelacakan tim.
