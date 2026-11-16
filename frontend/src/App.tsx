import { useCallback, useMemo } from 'react';
import type { PickingInfo } from '@deck.gl/core';
import {
  api,
  CATEGORIES,
  reportUrl,
  SEASONS,
  type CategoryInfo,
  type Category,
  type SeasonInfo,
} from './api/client';
import { Controls } from './components/Controls';
import { DistrictsPanel } from './components/DistrictsPanel';
import { Footer } from './components/Footer';
import { Legend } from './components/Legend';
import { buildLayers, type PoiFeature } from './components/mapLayers';
import { MapView } from './components/MapView';
import { OptimizePanel } from './components/OptimizePanel';
import { ScenarioPanel } from './components/ScenarioPanel';
import { Status } from './components/Status';
import { Tooltip } from './components/Tooltip';
import { useI18n } from './i18n/context';
import { LANGS } from './i18n/dictionaries';
import { TABS, useAppState } from './state/appState';
import { useApi } from './state/useApi';

// Fallbacks so the selectors stay usable if /categories or /seasons fail.
const FALLBACK_CATEGORIES: CategoryInfo[] = CATEGORIES.map((key) => ({ key, label: key }));
const FALLBACK_SEASONS: SeasonInfo[] = SEASONS.map((key) => ({
  key,
  label: key,
  speed_mps: Number.NaN,
  max_minutes: 15,
  share_of_days: null,
}));

export default function App() {
  const { t, lang, setLang } = useI18n();
  const { state, dispatch } = useAppState();
  const { category, season, tab, scenario } = state;

  // ------------------------------------------------------------ reference data
  const cities = useApi('cities', (s) => api.cities(s));
  const categories = useApi('categories', (s) => api.categories(s));

  const city = cities.data?.find((c) => c.slug === state.city) ?? cities.data?.[0] ?? null;
  const slug = city?.slug ?? null;

  const seasons = useApi(slug && `seasons:${slug}`, (s) => api.seasons(slug ?? '', s));

  // ------------------------------------------------------------ map data
  const access = useApi(slug && `access:${slug}:${category}:${season}`, (s) =>
    api.accessibility(slug ?? '', category, season, s),
  );

  const districts = useApi(state.showDistricts ? slug && `districts:${slug}` : null, (s) =>
    api.districts(slug ?? '', s),
  );

  // Scenario/optimisation need a real facility category, not the composite index.
  const facilityCategory: Category | null = category === 'index' ? null : category;

  // Existing facilities are only needed (and only fetched) in the scenario tab.
  // These are the OSM facilities the routing model uses; their ids go to `remove`.
  const pois = useApi(
    tab === 'scenario' && slug && facilityCategory ? `pois:${slug}:${facilityCategory}` : null,
    (s) => api.pois(slug ?? '', facilityCategory ?? 'school', s),
  );


  const seasonList = seasons.data ?? FALLBACK_SEASONS;
  const maxMinutes =
    access.data?.max_minutes ?? seasonList.find((s) => s.key === season)?.max_minutes ?? 15;
  const metric = access.data?.metric ?? (category === 'index' ? 'index' : 'minutes');

  // ------------------------------------------------------------ layers
  const layers = useMemo(
    () =>
      buildLayers({
        accessibility: access.data,
        districts: districts.data,
        pois: tab === 'scenario' ? pois.data : undefined,
        removeIds: scenario.remove,
        proposed: tab === 'scenario' ? scenario.add : undefined,
        changedCells: tab === 'scenario' ? scenario.result?.changed_cells : undefined,
        optimized: tab === 'optimize' ? state.optimize?.locations : undefined,
      }),
    [access.data, districts.data, pois.data, scenario, state.optimize, tab],
  );

  const editing = tab === 'scenario' && scenario.editing && facilityCategory !== null;

  // Scenario editing: click on an existing facility toggles its removal,
  // a click anywhere else adds a proposed facility at that coordinate.
  const handleMapClick = useCallback(
    (info: PickingInfo) => {
      if (!editing) return;
      if (info.layer?.id === 'pois' && info.object) {
        dispatch({ type: 'toggleRemove', id: (info.object as PoiFeature).properties.id });
        return;
      }
      if (info.layer?.id === 'proposed') return; // ignore clicks on own markers
      if (info.coordinate) {
        const [lon, lat] = info.coordinate as [number, number];
        dispatch({
          type: 'addFacility',
          lon,
          lat,
          name: t('scenario.newFacility', { n: scenario.add.length + 1 }),
        });
      }
    },
    [editing, dispatch, t, scenario.add.length],
  );

  const renderTooltip = useCallback(
    (info: PickingInfo) => <Tooltip info={info} metric={metric} canRemove={editing} />,
    [metric, editing],
  );

  // ------------------------------------------------------------ render
  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <h1>{t('app.title')}</h1>
          <span className="subtitle">{t('app.subtitle')}</span>
        </div>
        <div className="header-actions">
          {slug && (
            <a className="button" href={reportUrl(slug)} target="_blank" rel="noopener" download>
              {t('report.download')}
            </a>
          )}
          <div className="segmented" role="radiogroup" aria-label={t('lang.label')}>
            {LANGS.map((l) => (
              <button
                key={l}
                type="button"
                role="radio"
                aria-checked={lang === l}
                className={lang === l ? 'active' : ''}
                onClick={() => setLang(l)}
              >
                {l.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
      </header>

      <aside className="sidebar">
        <Status loading={cities.loading} error={cities.error} onRetry={cities.retry} />
        <Controls
          cities={cities.data ?? []}
          citySlug={slug}
          categories={categories.data ?? FALLBACK_CATEGORIES}
          seasons={seasonList}
        />
        <Status error={categories.error} onRetry={categories.retry} />
        <Status error={seasons.error} onRetry={seasons.retry} />

        <nav className="tabs" role="tablist">
          {TABS.map((id) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={tab === id}
              className={tab === id ? 'active' : ''}
              onClick={() => dispatch({ type: 'setTab', tab: id })}
            >
              {t(`tabs.${id}`)}
            </button>
          ))}
        </nav>

        {slug && tab === 'overview' && (
          <DistrictsPanel city={slug} season={season} category={category} maxMinutes={maxMinutes} />
        )}
        {slug && (tab === 'scenario' || tab === 'optimize') && !facilityCategory && (
          <p className="notice">{t('scenario.needCategory')}</p>
        )}
        {slug && tab === 'scenario' && facilityCategory && (
          <ScenarioPanel city={slug} category={facilityCategory} season={season} pois={pois} />
        )}
        {slug && tab === 'optimize' && facilityCategory && (
          <OptimizePanel city={slug} category={facilityCategory} season={season} />
        )}
      </aside>

      <main className="main">
        <MapView
          center={city?.center ?? null}
          layers={layers}
          onClick={handleMapClick}
          renderTooltip={renderTooltip}
          cursor={editing ? 'crosshair' : undefined}
        >
          <div className="map-status">
            <Status loading={access.loading} error={access.error} onRetry={access.retry} />
            <Status error={districts.error} onRetry={districts.retry} />
            {access.data && access.data.cells.length === 0 && (
              <div className="status">{t('status.noCells')}</div>
            )}
          </div>
          <Legend metric={metric} maxMinutes={maxMinutes} />
        </MapView>
      </main>

      <Footer attribution={city?.attribution ?? []} />
    </div>
  );
}
