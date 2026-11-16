import { useI18n } from '../i18n/context';
import { legendItems, type LegendItem, type Metric } from '../lib/colors';

interface Props {
  metric: Metric;
  maxMinutes: number;
}

export function Legend({ metric, maxMinutes }: Props) {
  const { t, num } = useI18n();

  const label = ({ range }: LegendItem): string => {
    if (range === null) return metric === 'index' ? t('legend.noValue') : t('legend.noData');
    const [from, to] = range;
    if (to === null) return t('legend.more', { n: num(from, 1) });
    return `${num(from, 1)}–${num(to, 1)}`;
  };

  return (
    <div className="legend">
      <div className="legend-title">
        {metric === 'index' ? t('legend.index', { n: maxMinutes }) : t('legend.minutes')}
      </div>
      <ul>
        {legendItems(metric, maxMinutes).map((it) => (
          <li key={it.color}>
            <span className="swatch" style={{ background: it.color }} />
            {label(it)}
          </li>
        ))}
      </ul>
      <div className="legend-threshold">{t('legend.threshold', { n: maxMinutes })}</div>
    </div>
  );
}
