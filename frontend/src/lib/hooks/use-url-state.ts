"use client";

import * as React from "react";

/**
 * Rebuild list-screen state from a query string. Iterates the UNION of `initial`'s
 * keys and the declared `numericKeys`/`booleanKeys`: a filter may be optional in the
 * state type (so absent from `initial`) yet still URL-persistable, and reading only
 * `Object.keys(initial)` silently dropped such keys on reload/share.
 */
export function hydrateState<T extends Record<string, string | number | boolean | undefined>>(
  initial: T,
  search: string,
  opts?: { numericKeys?: (keyof T)[]; booleanKeys?: (keyof T)[] }
): T {
  const params = new URLSearchParams(search);
  if ([...params.keys()].length === 0) return initial;
  const numeric = new Set((opts?.numericKeys ?? []).map(String));
  const booleans = new Set((opts?.booleanKeys ?? []).map(String));
  const next = { ...initial } as Record<string, string | number | boolean>;
  const keys = new Set<string>([...Object.keys(initial), ...numeric, ...booleans]);
  for (const key of keys) {
    const raw = params.get(key);
    if (raw == null) continue;
    if (numeric.has(key)) next[key] = Number(raw);
    else if (booleans.has(key)) next[key] = raw === "1" || raw === "true";
    else next[key] = raw;
  }
  return next as T;
}

/**
 * URL-backed state for list screens without `useSearchParams` — keeps the
 * route statically renderable (no Suspense boundary needed) while making
 * filters shareable and reload-safe. The first paint uses the defaults, then
 * the real query string is adopted in an effect (client only).
 */
export function useUrlState<T extends Record<string, string | number | boolean | undefined>>(
  initial: T,
  opts?: { numericKeys?: (keyof T)[]; booleanKeys?: (keyof T)[] }
): [T, (patch: Partial<T>, opts?: { replaceAll?: boolean }) => void] {
  const [state, setState] = React.useState<T>(initial);
  const hydrated = React.useRef(false);

  React.useEffect(() => {
    if (hydrated.current) return;
    hydrated.current = true;
    setState(hydrateState(initial, window.location.search, opts));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const update = React.useCallback(
    (patch: Partial<T>, apply?: { replaceAll?: boolean }) => {
      setState((cur) => {
        const next = apply?.replaceAll ? ({ ...initial, ...patch } as T) : { ...cur, ...patch };
        const params = new URLSearchParams();
        for (const [k, v] of Object.entries(next)) {
          if (v === undefined || v === "" || v === false) continue;
          params.set(k, typeof v === "boolean" ? "1" : String(v));
        }
        const qs = params.toString();
        const url = `${window.location.pathname}${qs ? `?${qs}` : ""}`;
        window.history.replaceState(null, "", url);
        return next;
      });
    },
    [initial]
  );

  return [state, update];
}
