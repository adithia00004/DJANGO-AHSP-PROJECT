/**
 * Gantt Timeline Panel Component
 * Canvas-based rendering for high performance
 * @module gantt-timeline-panel
 */

/**
 * Timeline Panel Component
 */
export class GanttTimelinePanel {
  constructor(container, dataModel, options = {}) {
    this.container = container;
    this.dataModel = dataModel;

    // Options - Phase 2.3: Default zoom changed to 'week'
    this.options = {
      rowHeight: options.rowHeight || 40,
      barHeight: options.barHeight || 24,
      barPadding: options.barPadding || 8,
      zoom: options.zoom || 'week', // 'week' or 'month' only (removed 'day' and 'quarter')
      mode: options.mode || 'planned', // 'planned' or 'actual'
      showGrid: options.showGrid !== false,
      showToday: options.showToday !== false,
      showMilestones: options.showMilestones !== false,
      ...options
    };

    // Canvas rendering state
    this.canvas = {
      scale: null,
      timeline: null,
      scaleCtx: null,
      timelineCtx: null,
      pixelsPerDay: 1,
      totalWidth: 0,
      totalHeight: 0,
      visibleNodes: []
    };

    // Date range
    this.dateRange = {
      start: null,
      end: null,
      totalDays: 0
    };

    // Scroll state
    this.scrollState = {
      x: 0,
      y: 0
    };

    // Event callbacks
    this.onBarClick = options.onBarClick || (() => {});
    this.onMilestoneClick = options.onMilestoneClick || (() => {});
    this.onScroll = options.onScroll || (() => {});

    // Colors - Phase 2.1: Improved bar visibility
    this.colors = {
      planned: {
        fill: 'rgba(13, 110, 252, 0.4)',      // Blue semi-transparent (increased from 0.2 to 0.4)
        stroke: '#0d6efd',                     // Blue border
        progress: 'rgba(8, 66, 152, 0.9)'     // Darker blue for progress fill
      },
      actual: {
        fill: 'rgba(253, 126, 20, 1.0)',      // Orange solid (changed from green, opacity 1.0)
        stroke: '#dc6d08',                     // Darker orange border
        progress: '#b34d00'                    // Even darker orange for progress
      },
      grid: '#e9ecef',
      today: '#dc3545',
      text: '#212529',
      textSecondary: '#6c757d'
    };

    // Performance optimization
    this._animationFrameId = null;
    this._renderPending = false;

    this.init();
  }

  /**
   * Initialize timeline panel
   */
  init() {
    console.log('📅 Initializing Timeline Panel...');
    this._buildDOM();
    this._setupCanvas();
    this._calculateDateRange();
    this._attachEventListeners();
    this.render();
    console.log('✅ Timeline Panel initialized');
  }

  /**
   * Build DOM structure
   */
  _buildDOM() {
    this.container.innerHTML = '';
    this.container.className = 'gantt-timeline-panel';

    // Header with toolbar
    const header = document.createElement('div');
    header.className = 'timeline-header';
    header.innerHTML = `
      <div class="timeline-toolbar">
        <div class="timeline-toolbar-group">
          <span class="timeline-toolbar-label">Zoom:</span>
          <button class="timeline-zoom-btn active" data-zoom="week">Week</button>
          <button class="timeline-zoom-btn" data-zoom="month">Month</button>
        </div>
        <div class="timeline-toolbar-group">
          <button class="btn btn-sm btn-outline-primary" id="timeline-fit-btn">
            <i class="bi bi-arrows-angle-contract"></i> Fit to Screen
          </button>
        </div>
        <div class="timeline-toolbar-group">
          <button class="btn btn-sm btn-outline-secondary" id="timeline-today-btn">
            <i class="bi bi-calendar-check"></i> Today
          </button>
        </div>
      </div>
      <div class="timeline-scale-wrapper" style="overflow: hidden; position: relative;">
        <div class="timeline-scale" style="position: relative; will-change: transform;">
          <canvas class="timeline-scale-canvas"></canvas>
        </div>
      </div>
    `;
    this.container.appendChild(header);

    // Timeline content
    const content = document.createElement('div');
    content.className = 'timeline-content';
    content.innerHTML = `
      <div class="timeline-canvas-wrapper">
        <canvas class="timeline-canvas"></canvas>
      </div>
    `;
    this.container.appendChild(content);

    // Store references - FIXED: Use transform for scale sync
    this.elements = {
      header,
      toolbar: header.querySelector('.timeline-toolbar'),
      scaleWrapper: header.querySelector('.timeline-scale-wrapper'),
      scale: header.querySelector('.timeline-scale'),
      scaleCanvas: header.querySelector('.timeline-scale-canvas'),
      content,
      timelineCanvas: content.querySelector('.timeline-canvas')
    };
  }

  /**
   * Setup canvas contexts
   */
  _setupCanvas() {
    this.canvas.scale = this.elements.scaleCanvas;
    this.canvas.timeline = this.elements.timelineCanvas;

    this.canvas.scaleCtx = this.canvas.scale.getContext('2d');
    this.canvas.timelineCtx = this.canvas.timeline.getContext('2d');

    // Enable high DPI rendering
    this._setupHighDPICanvas(this.canvas.scale, this.canvas.scaleCtx);
    this._setupHighDPICanvas(this.canvas.timeline, this.canvas.timelineCtx);
  }

  /**
   * Setup high DPI canvas
   */
  _setupHighDPICanvas(canvas, ctx) {
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;

    canvas.style.width = rect.width + 'px';
    canvas.style.height = rect.height + 'px';

    ctx.scale(dpr, dpr);
  }

  /**
   * Calculate date range from data
   */
  _calculateDateRange() {
    const projectRange = this.dataModel.getProjectDateRange();

    if (projectRange.start && projectRange.end) {
      this.dateRange.start = new Date(projectRange.start);
      this.dateRange.end = new Date(projectRange.end);
    } else {
      // Default to 1 year range
      this.dateRange.start = new Date();
      this.dateRange.end = new Date();
      this.dateRange.end.setFullYear(this.dateRange.end.getFullYear() + 1);
    }

    // Add padding (10% on each side)
    const totalMs = this.dateRange.end - this.dateRange.start;
    const padding = totalMs * 0.1;

    this.dateRange.start = new Date(this.dateRange.start.getTime() - padding);
    this.dateRange.end = new Date(this.dateRange.end.getTime() + padding);

    // Calculate total days
    const diffTime = Math.abs(this.dateRange.end - this.dateRange.start);
    this.dateRange.totalDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    console.log(`📅 Date range: ${this.dateRange.start.toLocaleDateString()} - ${this.dateRange.end.toLocaleDateString()} (${this.dateRange.totalDays} days)`);
  }

  /**
   * Attach event listeners
   */
  _attachEventListeners() {
    // Zoom buttons
    this.elements.toolbar.querySelectorAll('.timeline-zoom-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        this._setZoom(btn.dataset.zoom);
      });
    });

    // Fit to screen button
    const fitBtn = this.elements.toolbar.querySelector('#timeline-fit-btn');
    if (fitBtn) {
      fitBtn.addEventListener('click', () => this._fitToScreen());
    }

    // Today button
    const todayBtn = this.elements.toolbar.querySelector('#timeline-today-btn');
    if (todayBtn) {
      todayBtn.addEventListener('click', () => this._scrollToToday());
    }

    // Canvas click events
    this.canvas.timeline.addEventListener('click', (e) => {
      this._handleCanvasClick(e);
    });

    // Canvas double-click for milestone creation - Phase 3.4
    this.canvas.timeline.addEventListener('dblclick', (e) => {
      this._handleCanvasDoubleClick(e);
    });

    // Scroll sync - FIXED: Use CSS transform for scale header sync
    this.elements.content.addEventListener('scroll', () => {
      this.scrollState.x = this.elements.content.scrollLeft;
      this.scrollState.y = this.elements.content.scrollTop;

      // Sync scale header using CSS transform (smoother than scrollLeft)
      if (this.elements.scale) {
        this.elements.scale.style.transform = `translateX(-${this.scrollState.x}px)`;
      }

      this.onScroll(this.scrollState);
      this._scheduleRender();
    });

    // Resize observer
    this.resizeObserver = new ResizeObserver(() => {
      this._handleResize();
    });
    this.resizeObserver.observe(this.container);
  }

  /**
   * Set zoom level
   */
  _setZoom(zoom) {
    this.options.zoom = zoom;

    // Update active button
    this.elements.toolbar.querySelectorAll('.timeline-zoom-btn').forEach(btn => {
      btn.classList.toggle('active', btn.dataset.zoom === zoom);
    });

    // Recalculate pixels per day
    this._calculatePixelsPerDay();
    this._scheduleRender();
  }

  /**
   * Calculate pixels per day based on zoom - Phase 2.3: Only Week and Month
   */
  _calculatePixelsPerDay() {
    const zoomSettings = {
      week: 8,   // 8 pixels per day for week view
      month: 2   // 2 pixels per day for month view
    };

    this.canvas.pixelsPerDay = zoomSettings[this.options.zoom] || 8; // Default to week
    this.canvas.totalWidth = this.dateRange.totalDays * this.canvas.pixelsPerDay;
  }

  /**
   * Fit timeline to screen width
   */
  _fitToScreen() {
    const contentWidth = this.elements.content.offsetWidth;
    this.canvas.pixelsPerDay = contentWidth / this.dateRange.totalDays;
    this.canvas.totalWidth = contentWidth;

    // Update zoom button (custom)
    this.elements.toolbar.querySelectorAll('.timeline-zoom-btn').forEach(btn => {
      btn.classList.remove('active');
    });

    this._scheduleRender();
  }

  /**
   * Scroll to today's date - Phase 3.2: Added today marker visibility
   */
  _scrollToToday() {
    const today = new Date();

    // Check if today is within project date range
    if (today < this.dateRange.start || today > this.dateRange.end) {
      console.warn('Today is outside project date range');
      // Show toast notification if available
      if (window.Toast) {
        window.Toast.warning('Today is outside the project date range');
      }
      return;
    }

    const daysFromStart = Math.floor((today - this.dateRange.start) / (1000 * 60 * 60 * 24));
    const scrollX = daysFromStart * this.canvas.pixelsPerDay - (this.elements.content.offsetWidth / 2);

    this.elements.content.scrollLeft = Math.max(0, scrollX);

    // Ensure today marker is visible
    this.options.showToday = true;
    this._scheduleRender();

    console.log(`Scrolled to today: ${today.toLocaleDateString()}`);
  }

  /**
   * Handle canvas click
   */
  _handleCanvasClick(e) {
    const rect = this.canvas.timeline.getBoundingClientRect();
    const x = e.clientX - rect.left + this.scrollState.x;
    const y = e.clientY - rect.top + this.scrollState.y;

    // Check milestone clicks
    const milestone = this._getMilestoneAtPoint(x, y);
    if (milestone) {
      this.onMilestoneClick(milestone, e);
      return;
    }

    // Check bar clicks
    const bar = this._getBarAtPoint(x, y);
    if (bar) {
      this.onBarClick(bar.node, bar.type, e);
      return;
    }
  }

  /**
   * Handle canvas double-click for milestone creation - Phase 3.4
   */
  _handleCanvasDoubleClick(e) {
    const rect = this.canvas.timeline.getBoundingClientRect();
    const x = e.clientX - rect.left + this.scrollState.x;

    // Convert X coordinate to date
    const clickedDate = this._xToDate(x);

    // Prompt user for milestone details
    this._showMilestoneCreationDialog(clickedDate);
  }

  /**
   * Convert X coordinate to date - Phase 3.4
   */
  _xToDate(x) {
    const daysFromStart = x / this.canvas.pixelsPerDay;
    const date = new Date(this.dateRange.start);
    date.setDate(date.getDate() + Math.round(daysFromStart));
    return date;
  }

  /**
   * Show milestone creation dialog - Phase 3.4
   */
  _showMilestoneCreationDialog(date) {
    // Format date for display
    const dateStr = date.toLocaleDateString('id-ID', {
      weekday: 'long',
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });

    // Use Bootstrap modal if available, otherwise use prompt
    if (window.bootstrap && window.bootstrap.Modal) {
      this._showBootstrapMilestoneModal(date, dateStr);
    } else {
      this._showSimpleMilestonePrompt(date, dateStr);
    }
  }

  /**
   * Show simple prompt for milestone - Phase 3.4
   */
  _showSimpleMilestonePrompt(date, dateStr) {
    const title = prompt(`Create Milestone on ${dateStr}\n\nEnter milestone title:`);

    if (title && title.trim()) {
      const description = prompt('Enter milestone description (optional):') || '';

      // Create milestone
      const milestone = this.dataModel.addMilestone({
        date: date,
        title: title.trim(),
        description: description.trim(),
        color: '#ff6b6b',
        icon: '📍',
        createdBy: 'User'
      });

      // Re-render to show new milestone
      this._scheduleRender();

      console.log('Milestone created:', milestone);

      // Show success message
      if (window.Toast) {
        window.Toast.success('Milestone created successfully');
      }
    }
  }

  /**
   * Show Bootstrap modal for milestone creation - Phase 3.4
   * (Placeholder - implement if Bootstrap modal HTML is available)
   */
  _showBootstrapMilestoneModal(date, dateStr) {
    // For now, fallback to simple prompt
    // In future, create dynamic Bootstrap modal
    this._showSimpleMilestonePrompt(date, dateStr);
  }

  /**
   * Get milestone at point
   */
  _getMilestoneAtPoint(x, y) {
    const milestoneRadius = 12;

    for (const milestone of this.dataModel.milestones) {
      const milestoneX = this._dateToX(milestone.date);
      const milestoneY = 20; // Fixed Y position in scale area

      const distance = Math.sqrt(
        Math.pow(x - milestoneX, 2) + Math.pow(y - milestoneY, 2)
      );

      if (distance <= milestoneRadius) {
        return milestone;
      }
    }

    return null;
  }

  /**
   * Get bar at point
   */
  _getBarAtPoint(x, y) {
    const nodes = this.canvas.visibleNodes;

    for (let i = 0; i < nodes.length; i++) {
      const node = nodes[i];
      const nodeY = i * this.options.rowHeight;

      if (y < nodeY || y > nodeY + this.options.rowHeight) continue;

      if (node.type === 'pekerjaan') {
        // Check planned bar
        const planned = node.planned;
        if (planned.isValid()) {
          const startX = this._dateToX(planned.startDate);
          const endX = this._dateToX(planned.endDate);
          const barY = nodeY + this.options.barPadding;
          const barHeight = this.options.barHeight;

          if (x >= startX && x <= endX && y >= barY && y <= barY + barHeight) {
            return { node, type: 'planned' };
          }
        }

        // Check actual bar
        const actual = node.actual;
        if (actual.isValid()) {
          const startX = this._dateToX(actual.startDate);
          const endX = this._dateToX(actual.endDate);
          const barY = nodeY + this.options.barPadding + (this.options.barHeight / 2) - 6;
          const barHeight = 12;

          if (x >= startX && x <= endX && y >= barY && y <= barY + barHeight) {
            return { node, type: 'actual' };
          }
        }
      }
    }

    return null;
  }

  /**
   * Handle resize
   */
  _handleResize() {
    this._setupHighDPICanvas(this.canvas.scale, this.canvas.scaleCtx);
    this._setupHighDPICanvas(this.canvas.timeline, this.canvas.timelineCtx);
    this._scheduleRender();
  }

  /**
   * Schedule render (throttled via requestAnimationFrame)
   */
  _scheduleRender() {
    if (this._renderPending) return;

    this._renderPending = true;
    this._animationFrameId = requestAnimationFrame(() => {
      this.render();
      this._renderPending = false;
    });
  }

  /**
   * Render timeline
   */
  render() {
    this._calculatePixelsPerDay();

    // Get visible nodes from data model
    this.canvas.visibleNodes = this.dataModel.getFlattenedTree();
    this.canvas.totalHeight = this.canvas.visibleNodes.length * this.options.rowHeight;

    // Resize timeline canvas
    this.canvas.timeline.style.width = this.canvas.totalWidth + 'px';
    this.canvas.timeline.style.height = this.canvas.totalHeight + 'px';
    this._setupHighDPICanvas(this.canvas.timeline, this.canvas.timelineCtx);

    // Resize scale canvas
    this.canvas.scale.style.width = this.canvas.totalWidth + 'px';
    this._setupHighDPICanvas(this.canvas.scale, this.canvas.scaleCtx);

    // Render scale
    this._renderScale();

    // Render timeline
    this._renderTimeline();
  }

  /**
   * Render scale (date headers)
   */
  _renderScale() {
    const ctx = this.canvas.scaleCtx;
    const width = this.canvas.totalWidth;
    const height = this.canvas.scale.offsetHeight;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Background
    ctx.fillStyle = '#f8f9fa';
    ctx.fillRect(0, 0, width, height);

    // Draw scale based on zoom level
    switch (this.options.zoom) {
      case 'day':
        this._renderDayScale(ctx);
        break;
      case 'week':
        this._renderWeekScale(ctx);
        break;
      case 'month':
        this._renderMonthScale(ctx);
        break;
      case 'quarter':
        this._renderQuarterScale(ctx);
        break;
    }

    // Draw milestones
    if (this.options.showMilestones) {
      this._renderMilestonesInScale(ctx);
    }
  }

  /**
   * Render day scale
   */
  _renderDayScale(ctx) {
    const startDate = new Date(this.dateRange.start);
    const endDate = new Date(this.dateRange.end);

    ctx.font = '11px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';

    let currentDate = new Date(startDate);
    let currentMonth = null;

    while (currentDate <= endDate) {
      const x = this._dateToX(currentDate);

      // Month separator
      if (currentDate.getMonth() !== currentMonth) {
        currentMonth = currentDate.getMonth();
        ctx.strokeStyle = '#dee2e6';
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, 60);
        ctx.stroke();

        // Month label
        ctx.fillStyle = '#212529';
        ctx.font = 'bold 12px sans-serif';
        ctx.fillText(
          currentDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' }),
          x + 30,
          15
        );
      }

      // Day label
      ctx.fillStyle = '#6c757d';
      ctx.font = '10px sans-serif';
      ctx.fillText(currentDate.getDate(), x + (this.canvas.pixelsPerDay / 2), 45);

      // Grid line
      ctx.strokeStyle = '#e9ecef';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, 30);
      ctx.lineTo(x, 60);
      ctx.stroke();

      currentDate.setDate(currentDate.getDate() + 1);
    }
  }

  /**
   * Render month scale - Phase 2.2: Grid every 28 days (4 weeks)
   */
  _renderMonthScale(ctx) {
    const startDate = new Date(this.dateRange.start);
    const endDate = new Date(this.dateRange.end);

    ctx.font = '11px sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';

    let currentDate = new Date(startDate);
    let monthCount = 0;

    while (currentDate <= endDate) {
      const x = this._dateToX(currentDate);

      // Grid line - every 28 days (4 weeks)
      ctx.strokeStyle = '#dee2e6';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, 60);
      ctx.stroke();

      // Month label (show actual month name for better UX)
      const monthLabel = currentDate.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
      ctx.fillStyle = '#6c757d';
      ctx.font = '12px sans-serif';
      ctx.fillText(monthLabel, x + 5, 30);

      // Move to next 4-week period (28 days)
      currentDate.setDate(currentDate.getDate() + 28);
      monthCount++;
    }
  }

  /**
   * Render week scale - Phase 2.2: Grid every 7 days (1 week)
   */
  _renderWeekScale(ctx) {
    const startDate = new Date(this.dateRange.start);
    const endDate = new Date(this.dateRange.end);

    ctx.font = '11px sans-serif';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';

    let currentDate = new Date(startDate);
    let weekNumber = 1;

    while (currentDate <= endDate) {
      const x = this._dateToX(currentDate);

      // Grid line - every 7 days (1 week)
      ctx.strokeStyle = '#dee2e6';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, 60);
      ctx.stroke();

      // Week label
      const weekLabel = `Week ${weekNumber}`;
      const dateLabel = currentDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

      ctx.fillStyle = '#6c757d';
      ctx.font = 'bold 11px sans-serif';
      ctx.fillText(weekLabel, x + 5, 20);

      ctx.font = '10px sans-serif';
      ctx.fillStyle = '#999';
      ctx.fillText(dateLabel, x + 5, 40);

      // Move to next week (7 days)
      currentDate.setDate(currentDate.getDate() + 7);
      weekNumber++;
    }
  }

  /**
   * Render quarter scale (simplified)
   */
  _renderQuarterScale(ctx) {
    this._renderMonthScale(ctx);
  }

  /**
   * Render milestones in scale
   */
  _renderMilestonesInScale(ctx) {
    this.dataModel.milestones.forEach(milestone => {
      const x = this._dateToX(milestone.date);
      const y = 20;

      // Draw marker
      ctx.fillStyle = milestone.color;
      ctx.beginPath();
      ctx.arc(x, y, 12, 0, Math.PI * 2);
      ctx.fill();

      // Draw icon
      ctx.fillStyle = 'white';
      ctx.font = '14px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(milestone.icon, x, y);
    });
  }

  /**
   * Render timeline (bars)
   */
  _renderTimeline() {
    const ctx = this.canvas.timelineCtx;
    const width = this.canvas.totalWidth;
    const height = this.canvas.totalHeight;

    // Clear
    ctx.clearRect(0, 0, width, height);

    // Draw grid
    if (this.options.showGrid) {
      this._renderGrid(ctx);
    }

    // Draw today marker
    if (this.options.showToday) {
      this._renderTodayMarker(ctx);
    }

    // Draw bars
    this.canvas.visibleNodes.forEach((node, index) => {
      const y = index * this.options.rowHeight;
      this._renderNodeBars(ctx, node, y);
    });
  }

  /**
   * Render grid lines
   */
  _renderGrid(ctx) {
    const startDate = new Date(this.dateRange.start);
    const endDate = new Date(this.dateRange.end);

    ctx.strokeStyle = this.colors.grid;
    ctx.lineWidth = 1;

    // Vertical lines (monthly)
    let currentDate = new Date(startDate);
    currentDate.setDate(1);

    while (currentDate <= endDate) {
      const x = this._dateToX(currentDate);

      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x, this.canvas.totalHeight);
      ctx.stroke();

      currentDate.setMonth(currentDate.getMonth() + 1);
    }

    // Horizontal lines (rows)
    for (let i = 0; i <= this.canvas.visibleNodes.length; i++) {
      const y = i * this.options.rowHeight;

      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(this.canvas.totalWidth, y);
      ctx.stroke();
    }
  }

  /**
   * Render today marker
   */
  _renderTodayMarker(ctx) {
    const today = new Date();
    const x = this._dateToX(today);

    ctx.strokeStyle = this.colors.today;
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);

    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, this.canvas.totalHeight);
    ctx.stroke();

    ctx.setLineDash([]);
  }

  /**
   * Render node bars
   */
  _renderNodeBars(ctx, node, y) {
    if (node.type !== 'pekerjaan') return;

    const barY = y + this.options.barPadding;

    // Render planned bar (background, transparent)
    if (node.planned.isValid()) {
      this._renderBar(ctx, node.planned, barY, this.colors.planned, 'planned');
    }

    // Render actual bar (foreground, solid, smaller)
    if (node.actual.isValid()) {
      this._renderBar(ctx, node.actual, barY + (this.options.barHeight / 2) - 6, this.colors.actual, 'actual', 12);
    }
  }

  /**
   * Render single bar
   */
  _renderBar(ctx, taskBar, y, colors, type, height = null) {
    if (!taskBar.isValid()) return;

    const startX = this._dateToX(taskBar.startDate);
    const endX = this._dateToX(taskBar.endDate);
    const width = endX - startX;
    const barHeight = height || this.options.barHeight;

    // Bar background
    ctx.fillStyle = colors.fill;
    ctx.fillRect(startX, y, width, barHeight);

    // Bar border - Phase 2.1: Increased lineWidth for better visibility
    ctx.strokeStyle = colors.stroke;
    ctx.lineWidth = 2;  // Increased from 1 to 2
    ctx.strokeRect(startX, y, width, barHeight);

    // Progress fill
    if (taskBar.progress > 0) {
      const progressWidth = (width * taskBar.progress) / 100;
      ctx.fillStyle = colors.progress;
      ctx.fillRect(startX, y, progressWidth, barHeight);
    }

    // Progress text
    if (type === 'planned' && width > 40) {
      ctx.fillStyle = this.colors.text;
      ctx.font = '11px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(`${taskBar.progress}%`, startX + width / 2, y + barHeight / 2);
    }
  }

  /**
   * Convert date to X coordinate
   */
  _dateToX(date) {
    const daysFromStart = Math.floor((date - this.dateRange.start) / (1000 * 60 * 60 * 24));
    return daysFromStart * this.canvas.pixelsPerDay;
  }

  /**
   * Convert X coordinate to date
   */
  _xToDate(x) {
    const daysFromStart = x / this.canvas.pixelsPerDay;
    const date = new Date(this.dateRange.start);
    date.setDate(date.getDate() + Math.floor(daysFromStart));
    return date;
  }

  /**
   * Update mode (planned/actual)
   */
  setMode(mode) {
    this.options.mode = mode;
    this._scheduleRender();
  }

  /**
   * Sync scroll with tree panel
   */
  syncScrollY(scrollTop) {
    this.elements.content.scrollTop = scrollTop;
  }

  /**
   * Get scroll state
   */
  getScrollState() {
    return this.scrollState;
  }

  /**
   * Destroy timeline panel
   */
  destroy() {
    if (this._animationFrameId) {
      cancelAnimationFrame(this._animationFrameId);
    }

    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }

    this.container.innerHTML = '';
    console.log('🗑️ Timeline Panel destroyed');
  }
}

export default GanttTimelinePanel;
