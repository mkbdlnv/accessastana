import { createContext, useContext } from 'react';
import type { Lang } from '../api/client';
import type { DictKey, Vars } from './dictionaries';

export interface I18nValue {
  lang: Lang;
  setLang: (lang: Lang) => void;
  t: (key: DictKey, vars?: Vars) => string;
  /** Locale-aware number formatting; null/undefined -> "—". */
  num: (value: number | null | undefined, maxDigits?: number) => string;
  /** Fraction in [0, 1] -> "42 %". */
  pct: (value: number | null | undefined, digits?: number) => string;
}

export const I18nContext = createContext<I18nValue | null>(null);

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error('useI18n must be used inside <I18nProvider>');
  return ctx;
}
