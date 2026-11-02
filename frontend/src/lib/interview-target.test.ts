import { describe, expect, it } from "vitest";

import { interviewApplicationHref } from "./interview-target";

describe("interviewApplicationHref", () => {
  it("opens the drawer of the card the rehearsal belongs to", () => {
    expect(interviewApplicationHref("app-1")).toBe("/applications?application=app-1");
  });

  it("answers null for a free rehearsal, so no screen draws a dead link", () => {
    expect(interviewApplicationHref(null)).toBeNull();
    expect(interviewApplicationHref(undefined)).toBeNull();
    expect(interviewApplicationHref("")).toBeNull();
  });
});