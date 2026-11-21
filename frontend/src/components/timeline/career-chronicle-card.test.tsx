import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string) => `[${key}]`, setLocale: () => undefined }),
}));
vi.mock("@/lib/hooks/timeline", () => ({
  useCareerChronicle: () => ({ mutate: () => undefined, isPending: false, isSuccess: false, isError: false, data: undefined }),
}));

import { CareerChronicleCard } from "./career-chronicle-card";

describe("CareerChronicleCard", () => {
  it("renders the locked chronicle with locale-keyed copy", () => {
    const html = renderToStaticMarkup(
      <CareerChronicleCard
        events={[{ at: "", kind: "application", title: "t", refId: "", summary: "" }]}
        milestones={{ milestones: [], counters: { applications: 1, interviewsCompleted: 0, offers: 0, letters: 0, matches: 0, currentStreak: 0, offersOnShelf: 0 } }}
      />
    );
    expect(html).toContain("[timeline.chronicleTitle]");
    expect(html).toContain("[timeline.chronicleLocked]");
    expect(html).toContain("[timeline.chronicleAction]");
  });
});
