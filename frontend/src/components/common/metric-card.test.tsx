import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `[${key}|${Object.values(vars).join(",")}]` : `[${key}]`,
    setLocale: () => {},
  }),
}));

import { Gauge } from "lucide-react";
import { MetricCard } from "./metric-card";

describe("MetricCard", () => {
  it("renders the label, the value and the glyph", () => {
    const html = renderToStaticMarkup(
      <MetricCard icon={<Gauge className="size-4" aria-hidden />} label="P95 latency" value="61230ms" />
    );

    expect(html).toContain("P95 latency");
    expect(html).toContain("61230ms");
    expect(html).toContain("tabular-nums");
  });

  it("lights the value in the warning tone only when the caller asks for it", () => {
    const warning = renderToStaticMarkup(
      <MetricCard icon={<Gauge className="size-4" aria-hidden />} label="Cache hit rate" value="4%" tone="warning" />
    );
    const plain = renderToStaticMarkup(
      <MetricCard icon={<Gauge className="size-4" aria-hidden />} label="Calls" value="9" />
    );

    expect(warning).toContain("text-warning");
    expect(plain).not.toContain("text-warning");
  });
});
