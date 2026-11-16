import type { PickingInfo } from '@deck.gl/core';
import type { AccessibilityCell, ChangedCell, OptimizeLocation } from '../api/client';
import type { Metric } from '../lib/colors';
import { useI18n } from '../i18n/context';
import { enumLabel } from '../i18n/labels';
import type { ProposedFacility } from '../state/appState';
import type { PoiFeature } from './mapLayers';

interface Props {
  info: PickingInfo;
  metric: Metric;
  canRemove: boolean;
}

/** Content of the hover tooltip; what is shown depends on the layer under the cursor. */
export function Tooltip({ info, metric, canRemove }: Props) {
  const { t, num } = useI18n();
  const minutes = (v: number | null) => (v === null ? t('legend.noData') : t('tooltip.minutes', { n: num(v, 1) }));

  switch (info.layer?.id) {
    case 'access': {
      const c = info.object as AccessibilityCell;
      return (
        <>
          <div className="mono">{c.h3}</div>
          <div>
            {t('tooltip.value')}:{' '}
            <b>{metric === 'index' ? (c.value === null ? t('legend.noValue') : num(c.value, 2)) : minutes(c.value)}</b>
          </div>
          <div>
            {t('tooltip.population')}: {num(c.population)}
          </div>
        </>
      );
    }
    case 'changed': {
      const c = info.object as ChangedCell;
      return (
        <>
          <div className="mono">{c.h3}</div>
          <div>
            {t('tooltip.before')}: {minutes(c.before)}
          </div>
          <div>
            {t('tooltip.after')}: <b>{minutes(c.after)}</b>
          </div>
        </>
      );
    }
    case 'pois': {
      const p = (info.object as PoiFeature).properties;
      return (
        <>
          <div>
            <b>{p.name || `${t('tooltip.facility')} #${p.id}`}</b>
          </div>
          <div>{enumLabel(t, 'category', p.category)}</div>
          {canRemove && <div className="hint">{t('tooltip.removeHint')}</div>}
        </>
      );
    }
    case 'proposed':
      return <b>{(info.object as ProposedFacility).name}</b>;
    case 'optimized': {
      const o = info.object as OptimizeLocation;
      return (
        <>
          <div className="mono">{o.h3}</div>
          <div>
            {t('tooltip.gain')}: <b>{num(o.population_gain)}</b>
          </div>
        </>
      );
    }
    default:
      return null;
  }
}
