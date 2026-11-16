import { useI18n } from '../i18n/context';

/** Data attribution required by the licences (ODbL for OpenStreetMap etc.). */
export function Footer({ attribution }: { attribution: string[] }) {
  const { t } = useI18n();
  return (
    <footer className="footer">
      {attribution.length > 0 && (
        <span>
          {t('footer.sources')}: {attribution.join(' · ')}
        </span>
      )}
      <span>
        {t('footer.basemap')}: © OpenStreetMap contributors · © OpenFreeMap · MapLibre · deck.gl
      </span>
    </footer>
  );
}
