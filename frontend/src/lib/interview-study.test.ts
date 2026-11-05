import { describe, expect, it } from "vitest";
import { studyNoteDraft } from "./interview-study";

describe("studyNoteDraft", () => {
  it("keeps the topic as the title and moves the reason and resource into the body", () => {
    const draft = studyNoteDraft(
      {
        title: "  Consistent hashing  ",
        why: "the follow-up asked how keys rebalance",
        url: "https://example.invalid/consistent-hashing",
      },
      "Interview study item"
    );

    expect(draft.title).toBe("Consistent hashing");
    expect(draft.content).toBe(
      "the follow-up asked how keys rebalance\n\nhttps://example.invalid/consistent-hashing"
    );
    expect(draft.tags).toEqual(["interview", "study"]);
  });

  it("falls back to the caller's title, and uses it as the body when the item says nothing else", () => {
    const draft = studyNoteDraft({}, "Interview study item");
    expect(draft.title).toBe("Interview study item");
    expect(draft.content).toBe("Interview study item");
  });

  it("never sends a title longer than the endpoint accepts", () => {
    const draft = studyNoteDraft({ title: "x".repeat(240) }, "fallback");
    expect(draft.title).toHaveLength(200);
  });

  it("keeps the rehearsal it came from as the last paragraph", () => {
    const draft = studyNoteDraft(
      { title: "Consistent hashing", why: "asked twice" },
      "Interview study item",
      "From your rehearsal for Staff Backend Engineer."
    );
    expect(draft.content).toBe(
      "asked twice\n\nFrom your rehearsal for Staff Backend Engineer."
    );
  });

  it("draws no origin paragraph when the caller has nothing to say", () => {
    const draft = studyNoteDraft({ why: "asked twice" }, "fallback", "   ");
    expect(draft.content).toBe("asked twice");
  });
});
