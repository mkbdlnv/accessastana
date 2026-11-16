/**
 * Colour scales for the choropleth.
 *
 * We use 5 classes of the (reversed) viridis palette: it is sequential,
 * perceptually uniform and readable for colour-blind users. Bright yellow is
 * always "good" (short walk / high index), dark purple is "bad".
 *
 * Minutes are classified with breaks derived from the season's threshold T
 * (`max_minutes`, normally 15): T/3, 2T/3, T, 2T  ->  0–5, 5–10, 10–15, 15–30, >30.
 * So the boundary between the 3rd and 4th class is exactly the 15-minute rule.
 */

export type RGBA = [number, number, number, number];

/** viridis, from good (index 0) to bad (index 4) */
export const PALETTE: readonly string[] = ['#fde725', '#5ec962', '#21918c', '#3b528b', '#440154'];

/** Grey used for cells without a value (unreachable within 60 minutes). */
export const NULL_COLOR = '#9e9e9e';

export function hexToRgba(hex: string, alpha = 255): RGBA {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255, alpha];
}

/** Upper class limits (in minutes) for a given threshold. */
export function minuteBreaks(maxMinutes: number): number[] {
  return [maxMinutes / 3, (2 * maxMinutes) / 3, maxMinutes, 2 * maxMinutes];
}

/**
 * Class index 0..4 for a walking time, or -1 for null.
 * A value equal to a break belongs to the lower (better) class, i.e. exactly
 * 15 minutes still counts as "within 15 minutes".
 */
export function minutesClass(value: number | null, maxMinutes: number): number {
  if (value === null || !Number.isFinite(value)) return -1;
  const breaks = minuteBreaks(maxMinutes);
  const i = breaks.findIndex((b) => value <= b);
  return i === -1 ? breaks.length : i;
}

/** Class index 0..4 for the 15-minute index in [0, 1] (1 = best = class 0). */
export function indexClass(value: number | null): number {
  if (value === null || !Number.isFinite(value)) return -1;
  const v = Math.min(1, Math.max(0, value));
  // 1.0–0.8 -> 0, 0.8–0.6 -> 1, ..., 0.2–0 -> 4
  return Math.min(4, Math.floor((1 - v) * 5));
}

export type Metric = 'minutes' | 'index';

export function colorFor(value: number | null, metric: Metric, maxMinutes: number, alpha = 200): RGBA {
  const cls = metric === 'index' ? indexClass(value) : minutesClass(value, maxMinutes);
  // Unreachable cells are drawn more transparent so they don't dominate the map.
  if (cls < 0) return hexToRgba(NULL_COLOR, Math.round(alpha * 0.6));
  return hexToRgba(PALETTE[cls] ?? NULL_COLOR, alpha);
}

export interface LegendItem {
  color: string;
  /** [from, to]; `to` = null means "more than from" */
  range: [number, number | null] | null;
}

/** Legend rows (best first), plus a final grey "no data" row. */
export function legendItems(metric: Metric, maxMinutes: number): LegendItem[] {
  if (metric === 'index') {
    const items: LegendItem[] = PALETTE.map((color, i) => ({
      color,
      range: [Math.round((1 - (i + 1) * 0.2) * 10) / 10, Math.round((1 - i * 0.2) * 10) / 10],
    }));
    return [...items, { color: NULL_COLOR, range: null }];
  }
  const b = minuteBreaks(maxMinutes).map((x) => Math.round(x * 10) / 10);
  const items: LegendItem[] = PALETTE.map((color, i) => ({
    color,
    range: i < b.length ? [i === 0 ? 0 : (b[i - 1] ?? 0), b[i] ?? null] : [b[b.length - 1] ?? 0, null],
  }));
  return [...items, { color: NULL_COLOR, range: null }];
}
