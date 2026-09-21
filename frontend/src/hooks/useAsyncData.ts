import { useCallback, useEffect, useState } from "react";

interface AsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

/** Small helper so every data page gets loading / error / retry + optional auto-polling for free. */
export function useAsyncData<T>(
  loader: () => Promise<T>,
  deps: unknown[] = [],
  pollIntervalMs?: number
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  // eslint-disable-next-line react-hooks/exhaustive-deps
  const run = useCallback(loader, deps);

  useEffect(() => {
    let cancelled = false;
    if (nonce > 0 || data === null) {
      setLoading(true);
    }
    setError(null);
    run()
      .then((result) => {
        if (!cancelled) setData(result);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Something went wrong.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    let intervalId: ReturnType<typeof setInterval> | null = null;
    if (pollIntervalMs && pollIntervalMs > 0) {
      intervalId = setInterval(() => {
        run()
          .then((result) => {
            if (!cancelled) setData(result);
          })
          .catch(() => {});
      }, pollIntervalMs);
    }

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
  }, [run, nonce, pollIntervalMs]);

  return { data, loading, error, reload: () => setNonce((n) => n + 1) };
}
