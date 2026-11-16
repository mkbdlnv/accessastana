import { useState } from 'react';
import { api, errorMessage, type Category, type Season } from '../api/client';
import { useI18n } from '../i18n/context';
import { useAppState } from '../state/appState';
import type { ApiState } from '../state/useApi';
import { MetricsTable } from './MetricsTable';
import { Status } from './Status';
import { useCancellable } from './useCancellable';

interface Props {
  city: string;
  category: Category;
  season: Season;
  /** state of the GET /pois request (made in App because the map needs the points) */
  pois: Pick<ApiState<unknown>, 'loading' | 'error' | 'retry'>;
}

/**
 * "What-if" scenario: the user adds proposed facilities (map clicks) and marks
 * existing ones for removal; POST /scenarios recomputes accessibility.
 */
export function ScenarioPanel({ city, category, season, pois }: Props) {
  const { t } = useI18n();
  const { state, dispatch } = useAppState();
  const { editing, add, remove, result } = state.scenario;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startRequest = useCancellable([city, category, season]);

  const compute = async () => {
    const signal = startRequest();
    setBusy(true);
    setError(null);
    try {
      const res = await api.scenario(
        {
          city,
          category,
          season,
          add: add.map(({ lon, lat, name }) => ({ lon, lat, name })),
          remove,
          save: false,
          name: null,
        },
        signal,
      );
      dispatch({ type: 'scenarioResult', result: res });
    } catch (e) {
      if (!signal.aborted) setError(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const empty = add.length === 0 && remove.length === 0;

  return (
    <section className="panel">
      <p className="hint">{t('scenario.help')}</p>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={editing}
          onChange={(e) => dispatch({ type: 'setEditing', value: e.target.checked })}
        />
        {t('scenario.editMode')}
      </label>
      <Status loading={pois.loading} error={pois.error} onRetry={pois.retry} />

      <ul className="map-key">
        <li><span className="dot dot-existing" /> {t('scenario.existing')}</li>
        <li><span className="dot dot-proposed" /> {t('scenario.proposed')}</li>
        <li><span className="dot dot-remove" /> {t('scenario.toRemove')}</li>
      </ul>
      <p>
        {t('scenario.added', { n: add.length })}
        <br />
        {t('scenario.removed', { n: remove.length })}
      </p>

      <div className="button-row">
        <button type="button" className="primary" disabled={busy || empty} onClick={compute}>
          {busy ? t('scenario.computing') : t('scenario.compute')}
        </button>
        <button
          type="button"
          disabled={busy || (empty && !result)}
          onClick={() => {
            setError(null);
            dispatch({ type: 'resetScenario' });
          }}
        >
          {t('scenario.reset')}
        </button>
      </div>
      {empty && !result && <p className="hint">{t('scenario.nothing')}</p>}
      <Status error={error} />

      {result && (
        <>
          <MetricsTable before={result.before} after={result.after} />
          <p className="hint">{t('scenario.changed', { n: result.changed_cells.length })}</p>
        </>
      )}
    </section>
  );
}
