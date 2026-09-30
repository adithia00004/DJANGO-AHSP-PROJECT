/**
 * Layout helpers for the full-page PNG download of Kurva S and Gantt.
 *
 * The PNG is drawn on an offscreen canvas, not captured from the page, so it
 * must follow the same rules as the web overlay (KurvaSCanvasOverlay):
 * - curve values come from the overlay's own curve data (bobot-weighted,
 *   weekly/monthly, progress/cost), never recomputed here;
 * - 0% sits `marginY` px above the bottom of the table body, 100% sits
 *   `marginY` px below its top, with dashed guide lines every 10%;
 * - week 0 is drawn at the left edge, each period at its column's right edge.
 */

export const KURVA_PNG_MARGIN_Y = 40;
export const KURVA_PNG_MIN_BODY_HEIGHT = 240;

/**
 * Wrap text to a pixel width using the caller's measure function
 * (normally `(s) => ctx.measureText(s).width`). Words longer than the width
 * are broken by character so no line ever overflows the label column.
 */
export function wrapTextToWidth(text, maxWidth, measure) {
  const source = String(text ?? '').replace(/\s+/g, ' ').trim();
  if (!source) return [''];
  if (!(maxWidth > 0)) return [source];

  const lines = [];
  let current = '';

  const pushLongWord = (word) => {
    let chunk = '';
    for (const char of word) {
      if (chunk && measure(chunk + char) > maxWidth) {
        lines.push(chunk);
        chunk = char;
      } else {
        chunk += char;
      }
    }
    return chunk;
  };

  source.split(' ').forEach((word) => {
    const candidate = current ? `${current} ${word}` : word;
    if (measure(candidate) <= maxWidth) {
      current = candidate;
      return;
    }
    if (current) lines.push(current);
    current = measure(word) > maxWidth ? pushLongWord(word) : word;
  });
  if (current) lines.push(current);
  return lines.length ? lines : [''];
}

function toNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : 0;
}

function pointKey(point, index) {
  if (point?.columnId !== undefined && point?.columnId !== null && point.columnId !== '') {
    return String(point.columnId);
  }
  return `idx_${index}`;
}

function isOrigin(point) {
  return Number(point?.weekNumber) === 0
    && (!point?.columnId || String(point.columnId) === 'week_0');
}

/**
 * Turn the overlay's curve data into PNG columns.
 *
 * Returns `{ columns, planned, actual }` where `columns` are the periods in
 * display order (week 0 excluded — it is the origin at the left edge) and
 * `planned`/`actual` are cumulative percentages aligned to `columns`
 * (`null` when a series has no value for that period).
 */
export function buildKurvaSPngSeries(curveData) {
  const plannedPoints = Array.isArray(curveData?.planned) ? curveData.planned : [];
  const actualPoints = Array.isArray(curveData?.actual) ? curveData.actual : [];

  const columns = [];
  const indexByKey = new Map();
  const register = (point, index) => {
    if (isOrigin(point)) return null;
    const key = pointKey(point, index);
    if (!indexByKey.has(key)) {
      indexByKey.set(key, columns.length);
      columns.push({
        key,
        label: point?.label || `W${point?.weekNumber ?? columns.length + 1}`,
      });
    }
    return indexByKey.get(key);
  };

  plannedPoints.forEach(register);
  actualPoints.forEach(register);

  const align = (points) => {
    const values = new Array(columns.length).fill(null);
    points.forEach((point, index) => {
      if (isOrigin(point)) return;
      const column = indexByKey.get(pointKey(point, index));
      if (column === undefined) return;
      values[column] = toNumber(point?.cumulativeProgress ?? point?.progress);
    });
    return values;
  };

  return { columns, planned: align(plannedPoints), actual: align(actualPoints) };
}

/** Same Y mapping (and 0–100 clamp) as KurvaSCanvasOverlay._interpolateY. */
export function progressToY(percent, bodyTop, bodyHeight, marginY = KURVA_PNG_MARGIN_Y) {
  const margin = Math.min(marginY, bodyHeight / 4);
  const y0 = bodyTop + bodyHeight - margin;
  const y100 = bodyTop + margin;
  const clamped = Math.max(0, Math.min(100, toNumber(percent)));
  return y0 - (clamped / 100) * (y0 - y100);
}
