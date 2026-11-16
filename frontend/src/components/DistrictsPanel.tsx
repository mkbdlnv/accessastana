import { api, type AccessCategory, type DistrictSummary, type Season } from '../api/client';
import { useI18n } from '../i18n/context';
import { useApi } from '../state/useApi';
import { useAppState } from '../state/appState';
import { Status } from './Status';

interface Props {
  city: string;
  season: Season;
  category: AccessCategory;
  maxMinutes: number;
}

/**
 * Table from /districts/summary: population, composite index and, for the
 * selected category, the population share within the threshold and mean time.
 */
export function DistrictsPanel({ city, season, category, maxMinutes }: Props) {
  const { t, num, pct } = useI18n();
  const { state, dispatch } = useAppState();
  const summary = useApi(`districts-summary:${city}:${season}`, (s) => api.districtsSummary(city, season, s));
  const data = summary.data;

  // Which share_within key to show: the season threshold if the backend
  // provides it, otherwise the largest available threshold.
  const thresholds = data?.thresholds ?? [];
  const thr = thresholds.includes(maxMinutes) ? maxMinutes : Math.max(...thresholds, maxMinutes);
  const showCategory = category !== 'index';

  const row = (d: DistrictSummary, isTotal = false) => {
    const stats = showCategory ? d.categories[category] : undefined;
    return (
      <tr key={isTotal ? 'total' : (d.id ?? d.name)} className={isTotal ? 'total' : undefined}>
        <td>{isTotal ? t('districts.cityTotal') : d.name}</td>
        <td className="num">{num(d.population)}</td>
        <td className="num">{num(d.index, 2)}</td>
        {showCategory && (
          <>
            <td className="num">{pct(stats?.share_within[String(thr)])}</td>
            <td className="num">{num(stats?.mean_minutes, 1)}</td>
          </>
        )}
      </tr>
    );
  };

  return (
    <section className="panel">
      <h2>{t('districts.title')}</h2>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={state.showDistricts}
          onChange={(e) => dispatch({ type: 'setShowDistricts', value: e.target.checked })}
        />
        {t('districts.showOutlines')}
      </label>
      <Status loading={summary.loading} error={summary.error} onRetry={summary.retry} />
      {data && (
        <div className="table-scroll">
          <table className="data-table">
            <thead>
              <tr>
                <th>{t('districts.name')}</th>
                <th className="num">{t('districts.population')}</th>
                <th className="num">{t('districts.index')}</th>
                {showCategory && (
                  <>
                    <th className="num">{t('districts.within', { n: thr })}</th>
                    <th className="num">{t('districts.mean')}</th>
                  </>
                )}
              </tr>
            </thead>
            <tbody>
              {data.districts.map((d) => row(d))}
              {row(data.city_total, true)}
            </tbody>
          </table>
        </div>
      )}
      {data && !showCategory && <p className="hint">{t('districts.indexHint')}</p>}
    </section>
  );
}
