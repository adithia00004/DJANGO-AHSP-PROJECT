export class GanttCanvasOverlay {
  constructor(tableManager) {
    this.tableManager = tableManager;
    this.debug = Boolean(this.tableManager?.options?.debugUnifiedTable || this.tableManager?.state?.debugUnifiedTable);
    this.canvas = document.createElement('canvas');
    this.canvas.className = 'gantt-canvas-overlay';
    this.canvas.style.cssText = `
      position: absolute;
      top: 0;
      left: 0;
      pointer-events: auto;
      z-index: 10;
    `;
    this.ctx = this.canvas.getContext('2d');
    this.visible = false;
    this.barData = [];
    this.dependencies = [];
    this.barRects = [];
    this.tooltip = null;

    const scrollTarget = this.tableManager?.bodyScroll;
    if (scrollTarget) {
      scrollTarget.addEventListener('scroll', () => {
        if (this.visible) {
          this.syncWithTable();
        }
      }, { passive: true });
    }

    this._bindPointerEvents();
  }

  show() {
    if (this.visible) return;
    const scrollArea = this.tableManager?.bodyScroll;
    if (!scrollArea) return;
    scrollArea.style.position = scrollArea.style.position || 'relative';
    scrollArea.appendChild(this.canvas);
    this.visible = true;
    this._log('show');
    this.syncWithTable();
  }

  hide() {
    if (!this.visible) return;
    if (this.canvas.parentNode) {
      this.canvas.parentNode.removeChild(this.canvas);
    }
    this.visible = false;
    this._log('hide');
    this._hideTooltip();
  }

  syncWithTable() {
    const scrollArea = this.tableManager?.bodyScroll;
    if (!scrollArea) return;

    this.canvas.width = scrollArea.scrollWidth;
    this.canvas.height = scrollArea.scrollHeight;

    const cellRects = typeof this.tableManager.getCellBoundingRects === 'function'
      ? this.tableManager.getCellBoundingRects()
      : [];

    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    this.barRects = [];
    this._log('sync', {
      cells: cellRects.length,
      bars: this.barData.length,
      deps: this.dependencies.length,
      size: { w: this.canvas.width, h: this.canvas.height },
    });

    if (this.barData.length > 0 && cellRects.length === 0) {
      console.error('[GanttOverlay] Have bar data but no cell rects. Overlay cannot draw bars.', {
        bars: this.barData.length,
      });
    }

    // Skeleton visual aid: outline cells for alignment verification
    this.ctx.strokeStyle = '#e2e8f0';
    cellRects.forEach((rect) => {
      this.ctx.strokeRect(rect.x, rect.y, rect.width, rect.height);
    });

    this._drawBars(cellRects);
    this._drawDependencies(cellRects);
  }

  renderBars(barData) {
    this.barData = Array.isArray(barData) ? barData : [];
    this._log('renderBars', { bars: this.barData.length });
    if (this.visible) {
      this.syncWithTable();
    }
  }

  renderDependencies(dependencyData) {
    this.dependencies = Array.isArray(dependencyData) ? dependencyData : [];
    this._log('renderDependencies', { deps: this.dependencies.length });
    if (this.visible) {
      this.syncWithTable();
    }
  }

  _drawBars(cellRects) {
    if (!Array.isArray(cellRects) || cellRects.length === 0 || this.barData.length === 0) {
      return;
    }
    let barsDrawn = 0;
    let barsSkipped = 0;
    this.barData.forEach((bar) => {
      const rect = cellRects.find(
        (c) => String(c.pekerjaanId) === String(bar.pekerjaanId) && String(c.columnId) === String(bar.columnId),
      );
      if (!rect) {
        barsSkipped += 1;
        if (barsSkipped <= 3) {
          console.warn('[GanttOverlay] Missing rect for bar', {
            pekerjaanId: bar.pekerjaanId,
            columnId: bar.columnId,
          });
        }
        return;
      }

      const paddingX = 4;
      const paddingY = 6;
      const maxWidth = rect.width - paddingX * 2;
      const x = rect.x + paddingX;
      const y = rect.y + paddingY;
      const height = Math.max(6, rect.height - paddingY * 2);

      const plannedValue = Number.isFinite(bar.planned) ? Math.max(0, Math.min(100, bar.planned)) : null;
      const actualValue = Number.isFinite(bar.actual) ? Math.max(0, Math.min(100, bar.actual)) : Math.max(0, Math.min(100, bar.value || 0));

      if (plannedValue !== null) {
        const plannedWidth = (plannedValue / 100) * maxWidth;
        this.ctx.fillStyle = '#e2e8f0';
        this.ctx.fillRect(x, y, plannedWidth, height);
      }

      const actualWidth = (actualValue / 100) * maxWidth;
      const barColor = bar.color || this._resolveVarianceColor(bar.variance);
      this.ctx.fillStyle = barColor;
      this.ctx.fillRect(x, y, actualWidth, height);

      this.barRects.push({
        x,
        y,
        width: actualWidth,
        height,
        pekerjaanId: bar.pekerjaanId,
        columnId: bar.columnId,
        value: actualValue,
        planned: plannedValue,
        variance: bar.variance,
        label: bar.label,
        color: barColor,
      });
      barsDrawn += 1;
    });
    this._log('bars:drawn', { drawn: barsDrawn, skipped: barsSkipped, total: this.barData.length });
  }

  _drawDependencies(cellRects) {
    if (!Array.isArray(cellRects) || cellRects.length === 0 || this.dependencies.length === 0) {
      return;
    }

    this.dependencies.forEach((dep) => {
      const fromRect = cellRects.find(
        (c) => c.pekerjaanId === dep.fromPekerjaanId && c.columnId === dep.fromColumnId,
      );
      const toRect = cellRects.find(
        (c) => c.pekerjaanId === dep.toPekerjaanId && c.columnId === dep.toColumnId,
      );
      if (!fromRect || !toRect) return;

      const fromX = fromRect.x + fromRect.width;
      const fromY = fromRect.y + fromRect.height / 2;
      const toX = toRect.x;
      const toY = toRect.y + toRect.height / 2;

      this.ctx.strokeStyle = dep.color || '#94a3b8';
      this.ctx.lineWidth = 1.5;
      this.ctx.beginPath();
      this.ctx.moveTo(fromX, fromY);
      this.ctx.lineTo(toX, toY);
      this.ctx.stroke();

      const arrowSize = 5;
      const angle = Math.atan2(toY - fromY, toX - fromX);
      this.ctx.beginPath();
      this.ctx.moveTo(toX, toY);
      this.ctx.lineTo(toX - arrowSize * Math.cos(angle - Math.PI / 6), toY - arrowSize * Math.sin(angle - Math.PI / 6));
      this.ctx.lineTo(toX - arrowSize * Math.cos(angle + Math.PI / 6), toY - arrowSize * Math.sin(angle + Math.PI / 6));
      this.ctx.closePath();
      this.ctx.fillStyle = dep.color || '#94a3b8';
      this.ctx.fill();
    });
  }

  _resolveVarianceColor(variance) {
    if (!Number.isFinite(variance)) return '#3b82f6';
    if (variance < -0.1) return '#ef4444';
    if (variance > 0.1) return '#22c55e';
    return '#3b82f6';
  }

  _bindPointerEvents() {
    this.canvas.addEventListener('mousemove', (e) => {
      if (!this.visible || !this.barRects.length) return;
      const rect = this.canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const hit = this._hitTest(x, y);
      if (hit) {
        this._showTooltip(e.clientX, e.clientY, hit);
      } else {
        this._hideTooltip();
      }
    });

    this.canvas.addEventListener('mouseleave', () => {
      this._hideTooltip();
    });
  }

  _hitTest(x, y) {
    return this.barRects.find(
      (b) => x >= b.x && x <= b.x + b.width && y >= b.y && y <= b.y + b.height,
    );
  }

  _ensureTooltip() {
    if (this.tooltip) return this.tooltip;
    this.tooltip = document.createElement('div');
    this.tooltip.className = 'gantt-overlay-tooltip';
    this.tooltip.style.cssText = `
      position: fixed;
      padding: 4px 8px;
      background: rgba(17,24,39,0.85);
      color: #f8fafc;
      border-radius: 4px;
      font-size: 12px;
      pointer-events: none;
      z-index: 20;
      display: none;
      box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    `;
    document.body.appendChild(this.tooltip);
    return this.tooltip;
  }

  _showTooltip(clientX, clientY, hit) {
    const tip = this._ensureTooltip();
    const name = hit.label || hit.pekerjaanId;
    const planned = Number.isFinite(hit.planned) ? `${hit.planned}%` : '-';
    const actual = Number.isFinite(hit.value) ? `${hit.value}%` : '-';
    const variance = Number.isFinite(hit.variance) ? `${hit.variance}%` : '-';
    tip.innerHTML = `Pekerjaan: ${name}<br/>Kolom: ${hit.columnId}<br/>Planned: ${planned}<br/>Actual: ${actual}<br/>Variance: ${variance}`;
    tip.style.left = `${clientX + 10}px`;
    tip.style.top = `${clientY + 10}px`;
    tip.style.display = 'block';
  }

  _hideTooltip() {
    if (this.tooltip) {
      this.tooltip.style.display = 'none';
    }
  }

  _log(event, payload) {
    if (!this.debug) return;
    console.log(`[GanttOverlay] ${event}`, payload || {});
  }
}
