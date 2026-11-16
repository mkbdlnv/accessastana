import { useEffect, useRef, useState } from 'react';
import { errorMessage } from '../api/client';

export interface ApiState<T> {
  data: T | undefined;
  error: string | null;
  loading: boolean;
  retry: () => void;
}

interface Stored<T> {
  /** request key the stored result belongs to */
  key: string | null;
  data?: T;
  error?: string;
}

/**
 * Minimal data-fetching hook for GET requests.
 *
 * `key` identifies the request (e.g. "accessibility:astana:school:winter");
 * whenever it changes the request is re-run and the previous one is aborted.
 * `key = null` means "do not fetch" (e.g. city not known yet).
 *
 * Trick: instead of a separate `loading` flag (which would require calling
 * setState synchronously inside the effect) we remember which key the stored
 * result belongs to; we are loading exactly when it differs from the current key.
 */
export function useApi<T>(key: string | null, fetcher: (signal: AbortSignal) => Promise<T>): ApiState<T> {
  const [stored, setStored] = useState<Stored<T>>({ key: null });
  const [attempt, setAttempt] = useState(0);

  // Keep the latest fetcher without making it an effect dependency
  // (it is a new closure on every render; `key` already captures its inputs).
  const fetcherRef = useRef(fetcher);
  useEffect(() => {
    fetcherRef.current = fetcher;
  });

  const fullKey = key === null ? null : `${key}#${attempt}`;

  useEffect(() => {
    if (fullKey === null) return;
    const ctrl = new AbortController();
    fetcherRef.current(ctrl.signal).then(
      (data) => setStored({ key: fullKey, data }),
      (e: unknown) => {
        // An aborted request is superseded by a newer one: ignore it.
        if (!ctrl.signal.aborted) setStored({ key: fullKey, error: errorMessage(e) });
      },
    );
    return () => ctrl.abort();
  }, [fullKey]);

  const current = fullKey !== null && stored.key === fullKey;
  return {
    data: current ? stored.data : undefined,
    error: current ? (stored.error ?? null) : null,
    loading: fullKey !== null && !current,
    retry: () => setAttempt((a) => a + 1),
  };
}
