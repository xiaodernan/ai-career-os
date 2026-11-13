import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `[${key}|${Object.values(vars).join(",")}]` : `[${key}]`,
    setLocale: () => undefined,
  }),
}));

vi.mock("@/lib/hooks/actions", () => ({
  useAnalyzeJd: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

import StudioPage from "./page";

describe("StudioPage", () => {
  it("renders the job input and the analyze action", () => {
    const html = renderToStaticMarkup(<StudioPage />);
    expect(html).toContain("[studio.title]");
    expect(html).toContain("[studio.analyze]");
    expect(html).toContain("[studio.jdLabel]");
    expect(html).toContain("[studio.jdPlaceholder]");
  });

  it("disables analyze until a job description is present", () => {
    const html = renderToStaticMarkup(<StudioPage />);
    const button = html.match(/<button[^>]*>\[studio\.analyze\]<\/button>/)?.[0] ?? "";
    expect(button).toContain("disabled");
  });
});
