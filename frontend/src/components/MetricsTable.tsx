import type { Metrics } from '../api/client';
import { useI18n } from '../i18n/context';

/** Before/after comparison used by both the scenario and the optimisation panels. */
export function MetricsTable({ before, after }: { before: Metrics; after: Metrics }) {
  const { t, num, pct } = useI18n();
  const diff = (a: number | null, b: number | null) => (a === null || b === null ? null : b - a);
  const signed = (s: string, d: number | null) => (d !== null && d > 0 ? `+${s}` : s);

  const dPop = diff(before.population_reachable, after.population_reachable);
  const dShare = diff(before.share_reachable, after.share_reachable);
  const dMean = diff(before.mean_minutes, after.mean_minutes);

  return (
    <table className="data-table metrics">
      <thead>
        <tr>
          <th>{t('metrics.metric')}</th>
          <th className="num">{t('metrics.before')}</th>
          <th className="num">{t('metrics.after')}</th>
          <th className="num">{t('metrics.delta')}</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>{t('metrics.population')}</td>
          <td className="num">{num(before.population_reachable)}</td>
          <td className="num">{num(after.population_reachable)}</td>
          <td className={`num ${dPop !== null && dPop > 0 ? 'good' : ''}`}>{signed(num(dPop), dPop)}</td>
        </tr>
        <tr>
          <td>{t('metrics.share')}</td>
          <td className="num">{pct(before.share_reachable, 1)}</td>
          <td className="num">{pct(after.share_reachable, 1)}</td>
          {/* change in percentage points */}
          <td className={`num ${dShare !== null && dShare > 0 ? 'good' : ''}`}>
            {dShare === null ? '—' : `${signed(num(dShare * 100, 1), dShare)} ${t('metrics.pp')}`}
          </td>
        </tr>
        <tr>
          <td>{t('metrics.mean')}</td>
          <td className="num">{num(before.mean_minutes, 1)}</td>
          <td className="num">{num(after.mean_minutes, 1)}</td>
          {/* for time, a decrease is the improvement */}
          <td className={`num ${dMean !== null && dMean < 0 ? 'good' : ''}`}>{signed(num(dMean, 1), dMean)}</td>
        </tr>
      </tbody>
    </table>
  );
}
