import { describe, expect, it } from "vitest";

import { mapInboundMail } from "./replies";

/**
 * The mapper is the only place a letter's wire names become the page's fields, so these
 * tests pin the distinction the page leans on: a reading the server has not made yet is
 * `null` ("unread", not "other"), and a name this file invented would show as an empty
 * badge rather than fail. A body that arrived with nothing in it still yields a letter,
 * because the server stores the letter before it tries to read it (37.2).
 */
describe("mapInboundMail", () => {
  it("keeps an unread letter's holes null instead of inventing a reading", () => {
    const mail = mapInboundMail({
      id: "mail-1",
      fromAddress: "recruiter@acme.test",
      subject: "Thanks for applying",
      bodyText: "We will be in touch.",
      intent: null,
      company: null,
      role: null,
      suggestedStage: null,
      applicationId: null,
      applicationTitle: null,
      receivedAt: "2026-10-27T09:00:00Z",
      filedAt: null,
    });

    expect(mail.id).toBe("mail-1");
    expect(mail.intent).toBeNull();
    expect(mail.suggestedStage).toBeNull();
    expect(mail.applicationId).toBeNull();
    expect(mail.filedAt).toBeNull();
    expect(mail.receivedAt).toBe("2026-10-27T09:00:00Z");
  });

  it("reads the names InboundMailItem spells and ignores anything else", () => {
    const mail = mapInboundMail({
      id: "mail-2",
      fromAddress: "talent@globex.test",
      subject: "Interview invitation",
      bodyText: "Can you talk on Thursday?",
      intent: "interview",
      company: "Globex",
      role: "Data engineer",
      suggestedStage: "interview",
      applicationId: "app-7",
      applicationTitle: "Data engineer",
      receivedAt: "2026-10-26T09:00:00Z",
      filedAt: "2026-10-26T09:05:00Z",
      // The backend never sends these; they must not shadow or leak into the mapped row.
      from: "someone@elsewhere.test",
      stage: "offer",
      title: "A different name",
    });

    expect(mail.intent).toBe("interview");
    expect(mail.company).toBe("Globex");
    expect(mail.role).toBe("Data engineer");
    expect(mail.suggestedStage).toBe("interview");
    expect(mail.applicationId).toBe("app-7");
    expect(mail.applicationTitle).toBe("Data engineer");
    expect(mail.filedAt).toBe("2026-10-26T09:05:00Z");
    expect(mail.fromAddress).toBe("talent@globex.test");
  });

  it("answers blanks for a letter that arrived with nothing in it", () => {
    const mail = mapInboundMail({});

    expect(mail.id).toBe("");
    expect(mail.fromAddress).toBe("");
    expect(mail.subject).toBe("");
    expect(mail.bodyText).toBe("");
    expect(mail.intent).toBeNull();
  });
});
