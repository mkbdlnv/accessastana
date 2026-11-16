import type { AccessCategory, CategoryInfo, City, Season, SeasonInfo } from '../api/client';
import { useI18n } from '../i18n/context';
import { enumLabel } from '../i18n/labels';
import { useAppState } from '../state/appState';

interface Props {
  cities: City[];
  citySlug: string | null;
  categories: CategoryInfo[];
  seasons: SeasonInfo[];
}

/** City / category / season selectors. */
export function Controls({ cities, citySlug, categories, seasons }: Props) {
  const { t, lang, num } = useI18n();
  const { state, dispatch } = useAppState();

  return (
    <div className="controls">
      <label className="field">
        <span>{t('controls.city')}</span>
        <select
          value={citySlug ?? ''}
          disabled={cities.length === 0}
          onChange={(e) => dispatch({ type: 'setCity', city: e.target.value })}
        >
          {cities.map((c) => (
            <option key={c.slug} value={c.slug}>
              {c.name[lang] || c.name.en || c.slug}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>{t('controls.category')}</span>
        <select
          value={state.category}
          onChange={(e) => dispatch({ type: 'setCategory', category: e.target.value as AccessCategory })}
        >
          <option value="index">{t('category.index')}</option>
          {categories.map((c) => (
            <option key={c.key} value={c.key}>
              {enumLabel(t, 'category', c.key, c.label)}
            </option>
          ))}
        </select>
      </label>

      <fieldset className="field">
        <legend>{t('controls.season')}</legend>
        <div className="segmented" role="radiogroup">
          {seasons.map((s) => (
            <button
              key={s.key}
              type="button"
              role="radio"
              aria-checked={state.season === s.key}
              className={state.season === s.key ? 'active' : ''}
              // Show the model parameters of the season on hover: walking speed and time threshold.
              title={t('season.hint', { v: num(s.speed_mps * 3.6, 1), n: s.max_minutes })}
              onClick={() => dispatch({ type: 'setSeason', season: s.key as Season })}
            >
              {enumLabel(t, 'season', s.key, s.label)}
            </button>
          ))}
        </div>
      </fieldset>
    </div>
  );
}
