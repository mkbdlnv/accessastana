import { useEffect, useRef } from 'react';

/**
 * For user-triggered POST requests: returns `start()`, which creates a fresh
 * AbortController (aborting the previous one). Any pending request is also
 * aborted when one of `deps` changes (e.g. another city/category/season is
 * selected) or the component unmounts, so a late answer for an old selection
 * can never overwrite the current state.
 */
export function useCancellable(deps: readonly unknown[]): () => AbortSignal {
  const ctrlRef = useRef<AbortController | null>(null);
  const depsKey = JSON.stringify(deps);
  useEffect(() => () => ctrlRef.current?.abort(), [depsKey]);
  return () => {
    ctrlRef.current?.abort();
    ctrlRef.current = new AbortController();
    return ctrlRef.current.signal;
  };
}
