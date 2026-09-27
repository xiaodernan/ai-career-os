import { describe, expect, it } from "vitest";

import { knowledgeFocus } from "@/lib/knowledge-focus";

/**
 * The judgment behind `/knowledge?src=`: the value is a document id, a blank is no filter. Both sides
 * carry a real value here — a normalizer that returned its argument untouched would still pass a test
 * that only ever compared two `undefined`s.
 */
describe("knowledgeFocus", () => {
  it("keeps the document id a citation linked", () => {
    expect(knowledgeFocus("6f1c0b3e-0000-4000-8000-000000000007")).toBe(
      "6f1c0b3e-0000-4000-8000-000000000007"
    );
  });

  it("turns a blank `?src=` into no filter at all", () => {
    expect(knowledgeFocus("")).toBeUndefined();
    expect(knowledgeFocus(undefined)).toBeUndefined();
  });
});
