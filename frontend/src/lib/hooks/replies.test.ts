import { afterEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL, endpoints } from "@/lib/api/endpoints";
import {
  fetchInboundIntentCounts,
  fetchInboundMails,
  mapInboundMail,
  mapIntentCounts,
} from "./replies";

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

/**
 * The counts answer carries two kinds of number: the per-reading counts the chips print and
 * the waiting pile's size. Reading only the items would leave the switch unable to say how
 * much waits, and inventing a zero for a missing `unfiled` would turn "not answered" into
 * "nothing waits" -- the opposite of what the reader needs to know.
 */
describe("mapIntentCounts", () => {
  it("copies every reading the server counted and the waiting number beside them", () => {
    const answer = mapIntentCounts({
      items: [
        { intent: "unread", count: 2 },
        { intent: "rejection", count: 1 },
        { intent: "interview", count: 0 },
      ],
      unfiled: 3,
    });

    expect(answer.counts).toEqual({ unread: 2, rejection: 1, interview: 0 });
    expect(answer.unfiled).toBe(3);
  });

  it("keeps a missing waiting number missing instead of claiming an empty pile", () => {
    const answer = mapIntentCounts({ items: [] });

    expect(answer.counts).toEqual({});
    expect(answer.unfiled).toBeUndefined();
  });
});

const okEnv = (data: unknown) => ({ success: true, data, error: null });

let urls: string[] = [];
function mockFetch(data: unknown) {
  urls = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      urls.push(url);
      return { status: 200, ok: true, json: async () => okEnv(data) };
    })
  );
}

afterEach(() => vi.unstubAllGlobals());

const basePath = new URL(API_BASE_URL).pathname.replace(/\/$/, "");

/**
 * The page tests mock this module, and the endpoint gate grades names but not presence --
 * so a hook that quietly stopped sending `unfiled` would leave every other gate green.
 * These call the wire readers directly and read the URL the client built.
 */
describe("fetchInboundMails", () => {
  it("sends the waiting scope beside the trimmed words and the reading", async () => {
    mockFetch({ items: [], total: 0, page: 1, size: 20 });

    await fetchInboundMails({
      q: " acme ",
      intent: "rejection",
      unfiled: true,
      page: 1,
      size: 20,
    });

    const url = new URL(urls[0]);
    expect(url.pathname).toBe(`${basePath}${endpoints.inboundMails}`);
    expect(url.searchParams.get("q")).toBe("acme");
    expect(url.searchParams.get("intent")).toBe("rejection");
    expect(url.searchParams.get("unfiled")).toBe("true");
    expect(url.searchParams.get("page")).toBe("1");
    expect(url.searchParams.get("size")).toBe("20");
  });

  it("leaves the unpressed scope and the missing page off the wire entirely", async () => {
    mockFetch({ items: [], total: 0, page: 0, size: 50 });

    await fetchInboundMails({ q: "acme", unfiled: false });

    const url = new URL(urls[0]);
    expect(url.searchParams.has("unfiled")).toBe(false);
    expect(url.searchParams.has("page")).toBe(false);
    expect(url.searchParams.get("size")).toBe("50");
  });
});

describe("fetchInboundIntentCounts", () => {
  it("asks the counts under the same words and waiting scope, and reads both numbers", async () => {
    mockFetch({ items: [{ intent: "unread", count: 2 }], unfiled: 2 });

    const answer = await fetchInboundIntentCounts({ q: " acme ", unfiled: true });

    const url = new URL(urls[0]);
    expect(url.pathname).toBe(`${basePath}${endpoints.inboundIntentCounts}`);
    expect(url.searchParams.get("q")).toBe("acme");
    expect(url.searchParams.get("unfiled")).toBe("true");
    expect(answer).toEqual({ counts: { unread: 2 }, unfiled: 2 });
  });
});
