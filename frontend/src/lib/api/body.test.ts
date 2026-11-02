import { describe, expect, it } from "vitest";
import { dial, field } from "./body";
import { tailorSaveBody } from "./normalize";

/**
 * `field` is the only writer of request bodies, so the rule that keeps the backend from aborting
 * on a duplicate constructor property has to hold for every body built from it.
 */
describe("field", () => {
  it("emits the name it was given, once", () => {
    expect(field("resumeVersionId", "v-1")).toEqual({ resumeVersionId: "v-1" });
    expect(Object.keys(field("versionId", "abc")).length).toBe(1);
  });

  it("leaves the key out when there is no value, so the server applies its own default", () => {
    // An explicit null would read as "this draft has no base version" — a different request.
    expect(field("conversationId", null)).toEqual({});
    expect(field("conversationId", undefined)).toEqual({});
    expect(field("tone", "")).toEqual({});
  });

  it("never adds the snake_case twin a @JsonAlias would also accept", () => {
    const body = { ...field("resumeVersionId", "v-1"), ...field("conversationId", "c-1") };
    expect(body).not.toHaveProperty("resume_version_id");
    expect(body).not.toHaveProperty("conversation_id");
  });

  it("keeps composed bodies free of two names for one field", () => {
    // Jackson binds an alias pair to the same record component and then has nowhere to put the
    // second value, so a twin in a body fails the request before the handler runs.
    const canonical = (k: string) => k.replace(/_([a-z0-9])/g, (_, c: string) => c.toUpperCase());
    const body = tailorSaveBody({
      raw: { tailored: { profile: {} }, diff: { accepted: [] } },
      plaintext: "# Ada",
      resumeVersionId: "v-1",
    });
    const names = Object.keys(body).map(canonical);
    expect(new Set(names).size).toBe(names.length);
  });
});

/**
 * A dial is the one field where the empty string is a value rather than an absence: it is how a
 * correction says "clear this" while a missing key says "leave it alone" (50.4).
 */
describe("dial", () => {
  it("carries the empty string, which `field` would have dropped", () => {
    expect(dial("tone", "")).toEqual({ tone: "" });
    expect(field("tone", "")).toEqual({});
  });

  it("still leaves the key out when the caller has no opinion at all", () => {
    expect(dial("tone", null)).toEqual({});
    expect(dial("tone", undefined)).toEqual({});
  });

  it("passes a chosen value through", () => {
    expect(dial("length", "short")).toEqual({ length: "short" });
  });
});
