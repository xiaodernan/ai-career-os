import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

const state = vi.hoisted(() => ({ impression: null as string | null | undefined, pending: false }));

vi.mock("@/lib/hooks/actions", () => ({
  useResumeImpression: () => ({
    isPending: state.pending,
    mutate: (_: unknown, opts?: { onSuccess?: (d: unknown) => void }) =>
      opts?.onSuccess?.({ impression: state.impression }),
  }),
}));

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string) => `[${key}]`, setLocale: () => undefined }),
}));

import { ResumeImpressionCard } from "./resume-impression-card";

describe("ResumeImpressionCard", () => {
  it("renders the action from locale keys and stays quiet before a request", () => {
    state.impression = undefined;
    const html = renderToStaticMarkup(<ResumeImpressionCard resumeId="r1" hasScore={true} />);
    expect(html).toContain("[resumes.detail.impressionTitle]");
    expect(html).toContain("[resumes.detail.impressionAction]");
    expect(html).not.toContain("[resumes.detail.impressionEmpty]");
  });

  it("disables the action until a score exists", () => {
    const html = renderToStaticMarkup(<ResumeImpressionCard resumeId="r1" hasScore={false} />);
    expect(html).toContain("disabled");
  });
});
