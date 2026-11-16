import en, { type Dict, type DictKey } from './en';
import ru from './ru';
import kk from './kk';
import type { Lang } from '../api/client';

export type { Dict, DictKey };

export const LANGS: readonly Lang[] = ['ru', 'kk', 'en'];
export const DEFAULT_LANG: Lang = 'ru';

export const dictionaries: Record<Lang, Dict> = { en, ru, kk };

/** BCP-47 locale used for number formatting. */
export const LOCALES: Record<Lang, string> = { en: 'en-GB', ru: 'ru-RU', kk: 'kk-KZ' };

export type Vars = Record<string, string | number>;

/** Replace {name} placeholders with values; unknown placeholders are kept. */
export function interpolate(template: string, vars?: Vars): string {
  if (!vars) return template;
  return template.replace(/\{(\w+)\}/g, (m, name: string) =>
    name in vars ? String(vars[name]) : m,
  );
}

export function translate(lang: Lang, key: DictKey, vars?: Vars): string {
  // Fall back to English if a key is somehow missing at runtime.
  return interpolate(dictionaries[lang][key] ?? en[key], vars);
}

export function isDictKey(key: string): key is DictKey {
  return key in en;
}
