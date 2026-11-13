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

import { FitBreakdown } from "./fit-breakdown";
import type { JobMatch } from "@/lib/api/types";

const match: JobMatch = {
  id: "m1",
  jobId: "j1",
  overall: 82,
  technical: 88,
  experience: 70,
  projects: 65,
  education: 90,
  matchedSkills: ["Java", "Kafka"],
  missingSkills: ["Kubernetes"],
  whyMatch: ["Strong systems background", "Owns payments at scale"],
  evidence: [
    {
      criterion: "jd-alignment",
      quote: "Built a payment gateway that held up under peak load",
      source: { docTitle: "Resume", path: ["Resume", "Experience"] },
    },
  ],
  skillGaps: [{ skill: "Kubernetes", importance: "nice", reason: "Used in the platform's infra" }],
  interviewTopics: ["System design", "Scaling under load"],
};

describe("FitBreakdown", () => {
  it("renders the fit report with dimensions, skills, evidence and topics", () => {
    const html = renderToStaticMarkup(<FitBreakdown match={match} />);
    expect(html).toContain("[studio.fitReport]");
    expect(html).toContain("[studio.strongFit]");
    expect(html).toContain("[studio.technical]");
    expect(html).toContain("Java");
    expect(html).toContain("Kubernetes");
    expect(html).toContain("Strong systems background");
    expect(html).toContain("Built a payment gateway that held up under peak load");
    expect(html).toContain("System design");
    expect(html).toContain("[studio.skillGapsTitle]");
  });

  it("omits sections with no data", () => {
    const html = renderToStaticMarkup(
      <FitBreakdown match={{ id: "x", overall: 40 }} />,
    );
    expect(html).toContain("[studio.fitReport]");
    expect(html).not.toContain("[studio.skillGapsTitle]");
    expect(html).not.toContain("System design");
  });
});
