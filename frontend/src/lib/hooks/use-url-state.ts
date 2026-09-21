"use client";

import * as React from "react";

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
  const numeric = new Set((opts?.numericKeys ?? []).map(String));
  const booleans = new Set((opts?.booleanKeys ?? []).map(String));

  React.useEffect(() => {
    if (hydrated.current) return;
    hydrated.current = true;
    const params = new URLSearchParams(window.location.search);
    if ([...params.keys()].length === 0) return;
    const next = { ...initial };
    for (const key of Object.keys(initial) as (keyof T)[]) {
      const raw = params.get(String(key));
      if (raw == null) continue;
      if (numeric.has(String(key))) (next[key] as number) = Number(raw);
      else if (booleans.has(String(key))) (next[key] as boolean) = raw === "1" || raw === "true";
      else (next[key] as string) = raw;
    }
    setState(next);
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
