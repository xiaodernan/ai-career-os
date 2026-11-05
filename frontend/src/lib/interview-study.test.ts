import { describe, expect, it } from "vitest";
import {
  betterAnswerNoteDraft,
  gapNoteDraft,
  prepareNoteDraft,
  studyNoteDraft,
} from "./interview-study";

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

describe("betterAnswerNoteDraft", () => {
  it("titles the note with the question and keeps the rewrite and its origin as the body", () => {
    const draft = betterAnswerNoteDraft(
      { question: "Why Redis?", answer: "Name the failure mode first." },
      "Model answer",
      "From your rehearsal for Staff Backend Engineer."
    );
    expect(draft.title).toBe("Why Redis?");
    expect(draft.content).toBe(
      "Name the failure mode first.\n\nFrom your rehearsal for Staff Backend Engineer."
    );
    expect(draft.tags).toEqual(["interview", "answer"]);
  });

  it("falls back to the caller's title when the rewrite has no question", () => {
    const draft = betterAnswerNoteDraft({ answer: "Say what breaks first." }, "Model answer");
    expect(draft.title).toBe("Model answer");
    expect(draft.content).toBe("Say what breaks first.");
  });
});

describe("gapNoteDraft", () => {
  it("keeps a one-line gap as the title and the origin as the body", () => {
    const draft = gapNoteDraft(
      "  Why a B-tree keeps its leaves linked  ",
      "Gap from a rehearsal",
      "From your rehearsal for Backend Engineer"
    );

    expect(draft.title).toBe("Why a B-tree keeps its leaves linked");
    expect(draft.content).toBe(
      "Why a B-tree keeps its leaves linked\n\nFrom your rehearsal for Backend Engineer"
    );
    expect(draft.tags).toEqual(["interview", "gap"]);
  });

  it("still writes a body when there is no origin", () => {
    const draft = gapNoteDraft("Sharding vs partitioning", "Gap from a rehearsal");
    expect(draft.content).toBe("Sharding vs partitioning");
  });

  it("falls back rather than saving a note with an empty title", () => {
    const draft = gapNoteDraft("   ", "Gap from a rehearsal");
    expect(draft.title).toBe("Gap from a rehearsal");
    expect(draft.content).toBe("Gap from a rehearsal");
  });
});

describe("prepareNoteDraft", () => {
  it("titles the note with the question and keeps the origin in the body", () => {
    const draft = prepareNoteDraft(
      "  How would you shard a write-heavy table?  ",
      "Question to prepare",
      "From your rehearsal for Backend Engineer"
    );

    expect(draft.title).toBe("How would you shard a write-heavy table?");
    expect(draft.content).toBe(
      "How would you shard a write-heavy table?\n\nFrom your rehearsal for Backend Engineer"
    );
    expect(draft.tags).toEqual(["interview", "prepare"]);
  });

  it("falls back when the question is blank and still writes a body", () => {
    const draft = prepareNoteDraft("", "Question to prepare");
    expect(draft.title).toBe("Question to prepare");
    expect(draft.content).toBe("Question to prepare");
  });
});
