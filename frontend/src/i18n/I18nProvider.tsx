import { useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Lang } from '../api/client';
import { I18nContext, type I18nValue } from './context';
import { DEFAULT_LANG, LANGS, numberLocale, translate } from './dictionaries';

const STORAGE_KEY = 'accessastana.lang';

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved && (LANGS as readonly string[]).includes(saved)) return saved as Lang;
  } catch {
    /* storage may be unavailable (private mode) */
  }
  return DEFAULT_LANG;
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(initialLang);

  // Remember the choice and keep <html lang> in sync (screen readers, hyphenation).
  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      /* ignore */
    }
  }, [lang]);

  const value = useMemo<I18nValue>(() => {
    const locale = numberLocale(lang);
    return {
      lang,
      setLang,
      t: (key, vars) => translate(lang, key, vars),
      num: (v, maxDigits = 0) =>
        v === null || v === undefined || !Number.isFinite(v)
          ? '—'
          : new Intl.NumberFormat(locale, { maximumFractionDigits: maxDigits }).format(v),
      pct: (v, digits = 0) =>
        v === null || v === undefined || !Number.isFinite(v)
          ? '—'
          : new Intl.NumberFormat(locale, {
              style: 'percent',
              maximumFractionDigits: digits,
            }).format(v),
    };
  }, [lang]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
