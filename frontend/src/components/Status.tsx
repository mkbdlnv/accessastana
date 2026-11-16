import { useI18n } from '../i18n/context';

interface Props {
  loading?: boolean;
  error?: string | null;
  onRetry?: () => void;
}

/** Uniform loading / error indicator for any request. Renders nothing when idle. */
export function Status({ loading, error, onRetry }: Props) {
  const { t } = useI18n();
  if (error) {
    return (
      <div className="status status-error" role="alert">
        <strong>{t('status.error')}:</strong> {error}
        {onRetry && (
          <button type="button" className="link-btn" onClick={onRetry}>
            {t('status.retry')}
          </button>
        )}
      </div>
    );
  }
  if (loading) {
    return (
      <div className="status status-loading" aria-live="polite">
        <span className="spinner" aria-hidden /> {t('status.loading')}
      </div>
    );
  }
  return null;
}
