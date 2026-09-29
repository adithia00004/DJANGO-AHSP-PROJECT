function parseLocalDate(value) {
  if (value instanceof Date) {
    return Number.isNaN(value.getTime())
      ? null
      : new Date(value.getFullYear(), value.getMonth(), value.getDate());
  }
  const match = String(value || '').match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (!match) return null;
  const date = new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
  return Number.isNaN(date.getTime()) ? null : date;
}

function dayDifference(start, end) {
  return Math.round((end.getTime() - start.getTime()) / 86400000);
}

export function findWorkPeriodEndMarker(tableManager, cellRects = []) {
  const state = tableManager?.state || {};
  const workPeriod = state.workPeriodMeta || {};
  if (!workPeriod.additional_end || !workPeriod.contract_end) return null;

  const workEnd = parseLocalDate(workPeriod.contract_end);
  if (!workEnd) return null;

  const columns = (tableManager.currentColumns || [])
    .filter((column) => column?.meta?.timeColumn)
    .map((column) => column.meta.columnMeta)
    .filter(Boolean);
  const column = columns.find((candidate) => {
    const start = parseLocalDate(candidate.startDate || candidate.start_date);
    const end = parseLocalDate(candidate.endDate || candidate.end_date);
    return Boolean(start && end && start <= workEnd && workEnd <= end);
  });
  if (!column) return null;

  const columnId = String(column.fieldId || column.id || '');
  const rect = cellRects.find((candidate) => String(candidate.columnId) === columnId);
  if (!rect || !Number.isFinite(Number(rect.x)) || !Number.isFinite(Number(rect.width))) {
    return null;
  }

  const start = parseLocalDate(column.startDate || column.start_date);
  const end = parseLocalDate(column.endDate || column.end_date);
  const totalDays = Math.max(1, dayDifference(start, end) + 1);
  const daysThroughWorkEnd = Math.min(totalDays, Math.max(0, dayDifference(start, workEnd) + 1));
  const ratio = daysThroughWorkEnd / totalDays;
  return {
    x: Number(rect.x) + Number(rect.width) * ratio,
    columnId,
    label: 'Akhir Waktu Kerja',
  };
}

export function drawWorkPeriodEndMarker(ctx, tableManager, cellRects, options = {}) {
  if (!ctx) return null;
  const marker = findWorkPeriodEndMarker(tableManager, cellRects);
  if (!marker) return null;

  const x = marker.x - (Number(options.xOffset) || 0);
  const top = Number(options.top) || 0;
  const bottom = Number.isFinite(Number(options.bottom)) ? Number(options.bottom) : ctx.canvas.height;
  ctx.save();
  ctx.strokeStyle = options.color || '#dc3545';
  ctx.lineWidth = 2;
  ctx.setLineDash([6, 4]);
  ctx.beginPath();
  ctx.moveTo(x, top);
  ctx.lineTo(x, bottom);
  ctx.stroke();
  ctx.restore();
  return { ...marker, x };
}
