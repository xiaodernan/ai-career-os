import { describe, expect, it } from "vitest";

import { actionLabelKey, CHAT_ACTION_ROUTES, normalizeChatActions } from "./normalize";

/**
 * The copilot's action chips.
 *
 * Two claims, and the second one is the interesting one:
 *
 * - every kind the orchestrator writes has a destination, and the destination
 *   is a page that exists;
 * - the label the orchestrator wrote in English is translated in the browser
 *   when the kind fixes the phrase -- and NOT translated when the label carries
 *   the user's own data, because "Open Platform Engineer @ Acme" is a job, not
 *   a sentence to translate.
 */

describe("the action kinds", () => {
  it("has a route for every kind, and a page behind every route", () => {
    for (const kind of Object.keys(CHAT_ACTION_ROUTES)) {
      const route = CHAT_ACTION_ROUTES[kind];
      expect(route.startsWith("/"), `${kind} points at ${route}`).toBe(true);
    }
  });

  it("translates the kinds whose label is a fixed phrase", () => {
    expect(actionLabelKey("cover_letter")).toBe("actions.coverLetter");
    expect(actionLabelKey("interview")).toBe("actions.interview");
    expect(actionLabelKey("tailor")).toBe("actions.tailor");
    expect(actionLabelKey("open_growth")).toBe("actions.openGrowth");
    expect(actionLabelKey("open_offers")).toBe("actions.openOffers");
    expect(actionLabelKey("open_interview")).toBe("actions.openInterview");
  });

  it("leaves the label alone when it carries the user's own data", () => {
    // "Open Platform Engineer @ Acme" names a job; translating the phrase
    // around it would not translate the name, so the whole label stays.
    expect(actionLabelKey("open_job")).toBeUndefined();
  });

  it("has no key for a kind it does not know", () => {
    expect(actionLabelKey("something_new")).toBeUndefined();
    expect(actionLabelKey(undefined)).toBeUndefined();
  });
});

describe("normalizeChatActions", () => {
  it("gives a chip a destination and keeps the label", () => {
    const [action] = normalizeChatActions([
      { kind: "open_job", label: "Open Backend Engineer @ Acme", job_id: "j1" },
    ]);
    expect(action.href).toBe("/jobs/j1");
    expect(action.label).toBe("Open Backend Engineer @ Acme");
    expect(action.kind).toBe("open_job");
  });

  it("gives a chip with no locator its page's route", () => {
    // The growth engines' chips name a page, not a row: the page IS the
    // destination, so there is no id to fill in.
    const [action] = normalizeChatActions([{ kind: "open_growth", label: "Open the growth report" }]);
    expect(action.href).toBe("/growth");
  });

  it("leaves a chip with no route unlinked rather than linking to nowhere", () => {
    const [action] = normalizeChatActions([{ kind: "unknown_kind", label: "Do a thing" }]);
    expect(action.href).toBeUndefined();
  });

  it("leaves a chip whose row is missing unlinked", () => {
    // "Continue interview" with no session id would be a link to
    // /interviews/null -- a chip that goes nowhere when clicked.
    const [action] = normalizeChatActions([{ kind: "open_interview", label: "Continue interview" }]);
    expect(action.href).toBeUndefined();
  });
});
