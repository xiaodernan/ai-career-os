"use client";

import { useLocale } from "@/lib/i18n/locale-context";
import { formatDateTime } from "@/lib/format";
import type { ExportBundle } from "@/lib/api/types";

/**
 * The export's identity, read from the bundle in hand: the content hash the server
 * computed and the instant it built the bundle.
 *
 * The instant is the server's; the clock is the reader's. The wire carries RFC3339,
 * which is a value, not a date anyone reads.
 */
export function BundleFacts({ bundle }: { bundle: ExportBundle }) {
  const { t, locale } = useLocale();
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <div>
        <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          {t("data.contentHash")}
        </p>
        <p className="mt-1 font-mono text-xs break-all">
          {bundle.manifest?.content_hash ?? "—"}
        </p>
      </div>
      <div>
        <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">
          {t("data.generated")}
        </p>
        <p className="mt-1 text-xs">{formatDateTime(bundle.generated_at, locale) || "—"}</p>
      </div>
    </div>
  );
}
