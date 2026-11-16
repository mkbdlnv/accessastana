import { describe, expect, it } from 'vitest';
import { CATEGORIES, SEASONS } from '../api/client';
import { dictionaries, interpolate, translate } from './dictionaries';

const placeholders = (s: string) => [...s.matchAll(/\{(\w+)\}/g)].map((m) => m[1]).sort();

describe('i18n dictionaries', () => {
  const en = dictionaries.en;
  const enKeys = Object.keys(en).sort();

  for (const lang of ['ru', 'kk'] as const) {
    it(`${lang} has exactly the same keys as en`, () => {
      expect(Object.keys(dictionaries[lang]).sort()).toEqual(enKeys);
    });

    it(`${lang} has no empty strings and keeps all placeholders`, () => {
      for (const key of enKeys) {
        const value = dictionaries[lang][key as keyof typeof en];
        expect(value.trim(), key).not.toBe('');
        expect(placeholders(value), key).toEqual(placeholders(en[key as keyof typeof en]));
      }
    });
  }

  it('translates every API category and season', () => {
    for (const c of [...CATEGORIES, 'index']) expect(`category.${c}` in en).toBe(true);
    for (const s of SEASONS) expect(`season.${s}` in en).toBe(true);
  });

  it('uses the expected Kazakh terms', () => {
    expect(translate('kk', 'category.school')).toBe('Мектептер');
    expect(translate('kk', 'season.winter_severe')).toBe('Қатты аяз');
  });

  it('interpolates placeholders', () => {
    expect(interpolate('{n} min of {m}', { n: 5, m: 'x' })).toBe('5 min of x');
    expect(interpolate('{unknown}', { n: 1 })).toBe('{unknown}');
  });
});
