import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({
    locale: "en",
    t: (key: string, vars?: Record<string, string | number>) =>
      vars && "count" in vars ? `${key}=${vars.count}` : key,
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: () => undefined }),
}));

vi.mock("@/lib/hooks/resources", () => ({
  useInterviewSessions: () => ({
    data: {
      items: [
        {
          id: "s1",
          status: "completed",
          mode: "technical",
          applicationId: "app-9",
          applicationStatus: "interview",
          jobTitle: "Staff Backend Engineer",
          questionCount: 3,
          finishedAt: "2026-11-02T10:00:00Z",
          overall: 72,
        },
      ],
      total: 1,
      page: 0,
      size: 20,
    },
    isPending: false,
    isError: false,
    isFetching: false,
    refetch: () => undefined,
  }),
}));

vi.mock("@/lib/hooks/actions", () => ({
  useCreateInterviewSession: () => ({ mutate: () => undefined, isPending: false }),
  // 66.1: the row's delete verb mounts on every row, so the page needs it too.
  useDeleteInterviewSession: () => ({ mutate: () => undefined, isPending: false }),
}));

import InterviewsPage from "./page";

describe("InterviewsPage application link", () => {
  it("sends a rehearsal back to the card it was started from", () => {
    // 56.3: the session names its application, so the list can point at that drawer.
    const html = renderToStaticMarkup(<InterviewsPage />);

    expect(html).toContain('href="/applications?application=app-9"');
    expect(html).toContain("interviews.openApplication");
    // 57.4: the row names the stage the card is in. The test's `t` echoes the
    // key, so `stageLabel` falls back to the stage's own English label.
    expect(html).toContain(">Interview<");
  });
});
