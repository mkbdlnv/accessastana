import { useState } from 'react';
import { api, errorMessage, type Category, type OptimizeMethod, type Season } from '../api/client';
import { useI18n } from '../i18n/context';
import { useAppState } from '../state/appState';
import { MetricsTable } from './MetricsTable';
import { Status } from './Status';
import { useCancellable } from './useCancellable';

interface Props {
  city: string;
  category: Category;
  season: Season;
}

const METHODS: OptimizeMethod[] = ['max_covering', 'p_median'];
const K_MIN = 1;
const K_MAX = 20;

/** Location-allocation: POST /optimize and show the k recommended sites. */
export function OptimizePanel({ city, category, season }: Props) {
  const { t, num } = useI18n();
  const { state, dispatch } = useAppState();
  const result = state.optimize;
  const [k, setK] = useState(5);
  const [method, setMethod] = useState<OptimizeMethod>('max_covering');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const startRequest = useCancellable([city, category, season]);

  const kValid = Number.isInteger(k) && k >= K_MIN && k <= K_MAX;

  const run = async () => {
    if (!kValid) return;
    const signal = startRequest();
    setBusy(true);
    setError(null);
    try {
      const res = await api.optimize({ city, category, season, k, method }, signal);
      dispatch({ type: 'optimizeResult', result: res });
    } catch (err) {
      if (!signal.aborted) setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="panel">
      <p className="hint">{t('optimize.help')}</p>
      <form
        className="form"
        onSubmit={(e) => {
          e.preventDefault();
          void run();
        }}
      >
        <label className="field">
          <span>{t('optimize.k')}</span>
          <input
            type="number"
            min={K_MIN}
            max={K_MAX}
            step={1}
            value={Number.isNaN(k) ? '' : k}
            onChange={(e) => setK(e.target.valueAsNumber)}
            aria-invalid={!kValid}
          />
        </label>
        <fieldset className="field">
          <legend>{t('optimize.method')}</legend>
          {METHODS.map((m) => (
            <label key={m} className="radio">
              <input type="radio" name="method" checked={method === m} onChange={() => setMethod(m)} />
              {t(`optimize.${m}`)}
            </label>
          ))}
        </fieldset>
        <div className="button-row">
          <button type="submit" className="primary" disabled={busy || !kValid}>
            {busy ? t('optimize.running') : t('optimize.run')}
          </button>
          <button
            type="button"
            disabled={busy || !result}
            onClick={() => dispatch({ type: 'optimizeResult', result: null })}
          >
            {t('optimize.clear')}
          </button>
        </div>
      </form>
      <Status error={error} />

      {result && (
        <>
          <p className="hint">{t('optimize.status', { s: result.status, t: num(result.solve_seconds, 2) })}</p>
          <MetricsTable before={result.before} after={result.after} />
          <h3>{t('optimize.locations')}</h3>
          <div className="table-scroll">
            <table className="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>H3</th>
                  <th className="num">{t('optimize.gain')}</th>
                </tr>
              </thead>
              <tbody>
                {result.locations.map((l, i) => (
                  <tr key={l.h3}>
                    <td>{i + 1}</td>
                    <td className="mono">{l.h3}</td>
                    <td className="num">{num(l.population_gain)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
