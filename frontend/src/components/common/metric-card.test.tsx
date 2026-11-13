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

describe("MetricCard polish", () => {
  it("renders the final value server-side, never a count-up zero", () => {
    // The animation is an enhancement that runs after mount in a real browser;
    // the server's first paint -- and every test's static markup -- must already
    // carry the truth, because a KPI that flashes "0" is a lie to no-JS mode.
    const html = renderToStaticMarkup(
      <MetricCard icon={<Gauge className="size-4" aria-hidden />} label="Calls" value="1234" />
    );
    expect(html).toContain("1234");
    expect(html).not.toMatch(/>0</);
  });

  it("carries the trend chip with a sentence for the screen reader", () => {
    const up = renderToStaticMarkup(
      <MetricCard
        icon={<Gauge className="size-4" aria-hidden />}
        label="Cache hit rate"
        value="96%"
        delta={{ label: "+3%", direction: "up", goodWhenUp: true }}
      />
    );
    const down = renderToStaticMarkup(
      <MetricCard
        icon={<Gauge className="size-4" aria-hidden />}
        label="P95 latency"
        value="61230ms"
        delta={{ label: "+120ms", direction: "up", goodWhenUp: false }}
      />
    );

    expect(up).toContain("+3%");
    expect(up).toContain("rising");
    expect(up).toContain("text-success");
    // The word follows the DIRECTION; the color follows whether that direction is
    // good. Latency rising is bad news, so the arrow says up and the color says red.
    expect(down).toContain("+120ms");
    expect(down).toContain("text-destructive");
    expect(down).toContain("rising");
    const falling = renderToStaticMarkup(
      <MetricCard
        icon={<Gauge className="size-4" aria-hidden />}
        label="P95 latency"
        value="48000ms"
        delta={{ label: "-13s", direction: "down", goodWhenUp: false }}
      />
    );
    expect(falling).toContain("falling");
    expect(falling).toContain("text-success");
  });

  it("keeps a flat delta in the muted color with its own word", () => {
    const html = renderToStaticMarkup(
      <MetricCard
        icon={<Gauge className="size-4" aria-hidden />}
        label="Runs"
        value="12"
        delta={{ label: "0", direction: "flat" }}
      />
    );
    expect(html).toContain("unchanged");
    expect(html).toContain("text-muted-foreground");
  });

  it("renders the hint line when the caller gives one", () => {
    const html = renderToStaticMarkup(
      <MetricCard
        icon={<Gauge className="size-4" aria-hidden />}
        label="Spend"
        value="$4.10"
        hint="last 24 hours"
      />
    );
    expect(html).toContain("last 24 hours");
  });
});
