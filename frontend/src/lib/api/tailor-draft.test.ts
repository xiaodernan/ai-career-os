import { describe, expect, it } from "vitest";

import {
  normalizeTailor,
  normalizeTailorDiff,
  tailoredDict,
  tailorDiffDict,
} from "@/lib/api/normalize";

/**
 * What POST /jobs/{id}/tailor actually answers: the ai-service tailor output passed
 * through verbatim by the backend (app/features/tailor.py returns
 * {tailored, diff, notes, evidence, stats}).
 */
const RUN = {
  tailored: {
    profile: { name: "Ada", headline: "Backend engineer" },
    experience: [
      { company: "ACME", title: "Senior Eng", start: "2021-03", bullets: ["Cut p99 by 40%"] },
    ],
    projects: [{ name: "ledger", tech: ["Go", "Postgres"] }],
    skills: ["Kafka", "Go"],
  },
  diff: {
    accepted: [{ section: "experience", before: "Worked on APIs", after: "Cut p99 by 40%" }],
    rejected: [{ section: "experience", reason: "no evidence for 'led a team of 8'" }],
  },
  notes: ["dropped an unsupported claim"],
  evidence: [{ quote: "Cut p99 by 40%", source: "resume" }],
  stats: { accepted: 1, rejected: 1 },
};

describe("tailoredDict", () => {
  it("extracts the structured body the version is projected from", () => {
    // The server stores this dict and derives experience/project/skill rows from it.
    // Sending the rendered markdown or the whole envelope instead would save a version
    // whose body is empty while the panel still shows the draft.
    expect(tailoredDict(RUN)).toEqual(RUN.tailored);
  });

  it("agrees with what the panel rendered", () => {
    // normalizeTailor picks the draft with the same alias list; if the two drifted apart,
    // the user would review one thing and keep another.
    const shown = normalizeTailor(RUN);
    const stored = tailoredDict(RUN) as { experience: unknown[] };
    expect(shown.tailored?.markdown).toContain("Cut p99 by 40%");
    expect(stored.experience).toHaveLength(1);
  });

  it("treats an unwrapped draft as the draft, like the normalizer does", () => {
    expect(tailoredDict(RUN.tailored)).toEqual(RUN.tailored);
  });
});

describe("tailorDiffDict", () => {
  it("keeps the change list in the shape the diff renderer reads", () => {
    expect(tailorDiffDict(RUN)).toEqual(RUN.diff);
  });

  it("answers an empty object when the run carried no diff", () => {
    expect(tailorDiffDict({ tailored: {} })).toEqual({});
  });

  it("round-trips: the stored diff renders the same accept/reject split shown at review", () => {
    // changeFrom() minting a random React key per call is the one thing allowed to differ.
    const shape = (d: unknown) =>
      JSON.parse(JSON.stringify(d).replace(/"id":"chg-[^"]*",?/g, ""));
    expect(shape(normalizeTailorDiff(tailorDiffDict(RUN)))).toEqual(
      shape(normalizeTailorDiff(RUN))
    );
  });
});
