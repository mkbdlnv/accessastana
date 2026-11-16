import type { DictKey } from './dictionaries';
import { isDictKey } from './dictionaries';

type T = (key: DictKey) => string;

/**
 * Translated label for an enum value coming from the API (category, season).
 * Falls back to the API's own label (or the raw key) for values the
 * dictionaries do not know yet, so a new backend category never breaks the UI.
 */
export function enumLabel(t: T, prefix: 'category' | 'season', key: string, fallback?: string): string {
  const k = `${prefix}.${key}`;
  return isDictKey(k) ? t(k) : (fallback ?? key);
}
