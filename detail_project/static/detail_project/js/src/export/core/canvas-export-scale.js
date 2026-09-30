const MAX_CANVAS_DIMENSION = 16384;
const MAX_CANVAS_PIXELS = 64 * 1024 * 1024;

/** Pick the sharpest export scale that stays within practical canvas limits. */
export function getSafeCanvasScale(width, height, requestedScale = 3) {
  const logicalWidth = Number(width);
  const logicalHeight = Number(height);
  const requested = Number(requestedScale);
  if (
    !Number.isFinite(logicalWidth) || logicalWidth <= 0
    || !Number.isFinite(logicalHeight) || logicalHeight <= 0
  ) return 1;

  const targetScale = Number.isFinite(requested) && requested > 0 ? Math.max(1, requested) : 1;
  const dimensionScale = Math.min(
    MAX_CANVAS_DIMENSION / logicalWidth,
    MAX_CANVAS_DIMENSION / logicalHeight,
  );
  const pixelScale = Math.sqrt(MAX_CANVAS_PIXELS / (logicalWidth * logicalHeight));
  let scale = Math.min(targetScale, dimensionScale, pixelScale);
  for (let attempt = 0; attempt < 5; attempt += 1) {
    const outputWidth = Math.round(logicalWidth * scale);
    const outputHeight = Math.round(logicalHeight * scale);
    const correction = Math.min(
      1,
      MAX_CANVAS_DIMENSION / outputWidth,
      MAX_CANVAS_DIMENSION / outputHeight,
      Math.sqrt(MAX_CANVAS_PIXELS / (outputWidth * outputHeight)),
    );
    if (correction >= 1) break;
    scale = Math.max(Number.EPSILON, scale * correction * 0.999999);
  }
  return scale;
}

export function getCanvasPixelSize(width, height, scale) {
  const safeScale = Number.isFinite(Number(scale)) && Number(scale) > 0 ? Number(scale) : 1;
  return {
    width: Math.max(1, Math.round(Number(width) * safeScale)),
    height: Math.max(1, Math.round(Number(height) * safeScale)),
    scale: safeScale,
  };
}
