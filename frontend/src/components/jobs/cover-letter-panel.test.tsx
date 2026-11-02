import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, unknown>) =>
      vars ? `${key}${JSON.stringify(vars)}` : key,
    setLocale: () => undefined,
  }),
}));

const keptState = vi.hoisted(() => ({ value: [] as unknown[] }));

vi.mock("@/lib/hooks/resources", () => ({
  useApplicationLetters: () => ({ data: keptState.value }),
}));

vi.mock("@/lib/hooks/actions", () => ({
  useCoverLetter: () => ({
    isPending: false,
    isSuccess: false,
    error: null,
    mutate: () => undefined,
    reset: () => undefined,
  }),
  useSaveApplicationLetter: () => ({
    isPending: false,
    isSuccess: false,
    mutate: () => undefined,
    reset: () => undefined,
  }),
}));

import { CoverLetterPanel } from "./cover-letter-panel";

const render = (applicationId: string | null = "app-1") =>
  renderToStaticMarkup(<CoverLetterPanel jobId="job-1" applicationId={applicationId} />);

describe("CoverLetterPanel", () => {
  it("says nothing about the shelf until something is on it", () => {
    keptState.value = [];

    expect(render()).not.toContain("coverLetter.keptHere");
  });

  it("tells the writer how many letters this posting already has", () => {
    keptState.value = [{ id: "l1", body: "Dear" }, { id: "l2", body: "Hi" }];

    const html = render();

    expect(html).toContain("coverLetter.keptHere");
    expect(html).toContain("&quot;count&quot;:2");
    // The same deep link the attention rows and the pipeline chip use: the reader lands with
    // that application's drawer already open, not on a board they have to search again.
    expect(html).toContain('href="/applications?application=app-1"');
  });
});
