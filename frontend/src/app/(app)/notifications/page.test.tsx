import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

const state = vi.hoisted(() => ({
  inbox: {
    data: undefined as
      | {
          items: unknown[];
          unread: number;
          generatedAt?: string;
        }
      | undefined,
    isSuccess: false,
    isError: false,
  },
}));

vi.mock("@/lib/hooks/resources", () => ({
  useNotifications: () => state.inbox,
}));

vi.mock("@/lib/hooks/notifications", () => ({
  useMarkNotificationsRead: () => ({ mutate: () => {}, isPending: false }),
  useMarkAllNotificationsRead: () => ({ mutate: () => {}, isPending: false }),
  useDismissNotification: () => ({ mutate: () => {}, isPending: false }),
}));

// The reminder's two answers share the application write hook; the page only reads
// `mutate` and `isPending` from it, and the test presses nothing.
vi.mock("@/lib/hooks/actions", () => ({
  useUpdateApplication: () => ({ mutate: () => {}, isPending: false }),
}));

import NotificationsPage from "./page";
import { LocaleProvider } from "@/lib/i18n/locale-context";

/**
 * The inbox is the browser's half of 19.3, and its promise is that a signal
 * says what happened and where to look: the sentence is composed here, in the
 * reader's language, from the kind and the holes the server sent -- never from
 * a prose string the server would have had to translate.
 *
 * The rows are rendered through the real locale provider, because that is how
 * they render in the product: a page that only works with a mocked translator
 * is a page that throws on the screen.
 */

const APP_ID = "3f2b8c1e-6a4d-4f9b-8e2c-1d5a7b9c0e3f";

const ITEMS = [
  {
    key: `reminder:${APP_ID}:1761600000`,
    kind: "reminder",
    title: "Backend engineer",
    subject: "Acme",
    status: "applied",
    count: null,
    note: null,
    link: `/applications?application=${APP_ID}`,
    at: "2026-10-27T09:00:00Z",
    read: false,
  },
  {
    key: "stale:app-2:1761500000",
    kind: "stale",
    title: "Data engineer",
    subject: "Globex",
    status: "interviewing",
    count: null,
    note: null,
    link: "/applications?application=app-2",
    at: "2026-10-26T09:00:00Z",
    read: true,
  },
  {
    key: "ingestion:run-1",
    kind: "ingestion_failed",
    title: "HN hiring",
    subject: "",
    status: "failed",
    count: null,
    note: "Feed answered HTTP 503",
    link: "/ingestion",
    at: "2026-10-25T03:20:00Z",
    read: false,
  },
  {
    key: "ingestion:run-2",
    kind: "ingestion_created",
    title: "Boards",
    subject: "",
    status: "completed",
    count: 3,
    note: null,
    link: "/ingestion",
    at: "2026-10-24T03:20:00Z",
    read: false,
  },
  {
    key: "saved_search:6a1d7c2e-9b3f-4a8d-b0c5-2e4f6a8b0c1d:1761400000",
    kind: "saved_search",
    title: "Remote Rust",
    subject: "",
    status: "",
    count: 4,
    note: null,
    link: "/jobs?q=rust",
    at: "2026-10-23T09:00:00Z",
    read: false,
  },
  {
    key: "reply:0b9e4d1a-7c2f-4e6b-9a3d-5f8c1b2e4a6d",
    kind: "reply",
    title: "Initech",
    subject: "Re: interview",
    status: "interview_request",
    count: null,
    note: null,
    link: "/replies?mail=0b9e4d1a-7c2f-4e6b-9a3d-5f8c1b2e4a6d",
    at: "2026-10-22T09:00:00Z",
    read: true,
  },
];

function render(locale: "en" | "zh" = "en"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <NotificationsPage />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

beforeEach(() => {
  state.inbox = { data: undefined, isSuccess: false, isError: false };
});

describe("the notifications page", () => {
  it("composes each kind's sentence from the item, in English", () => {
    state.inbox = {
      data: { items: ITEMS, unread: 4, generatedAt: "2026-10-28T10:00:00Z" },
      isSuccess: true,
      isError: false,
    };
    const html = render();
    expect(html).toContain("Notifications");
    expect(html).toContain("Your reminder for Backend engineer is due.");
    expect(html).toContain("Acme");
    expect(html).toContain("No movement on Data engineer — it has gone quiet.");
    expect(html).toContain("The last pull of HN hiring failed.");
    // The reason is the server's record of the failure, shown as it was written.
    expect(html).toContain("Feed answered HTTP 503");
    expect(html).toContain("New postings from Boards: 3.");
    // A saved search names itself and its count; it has no feed or reminder behind it.
    expect(html).toContain("New postings match your saved search Remote Rust: 4.");
    expect(html).toContain("Saved search");
    // A forward lands on someone else's mail: the reply says whose it is and opens there.
    expect(html).toContain("A recruiter replied about your application — Initech.");
    expect(html).toContain("Recruiter reply");
    expect(html).toContain("Re: interview");
    expect(html).toContain('href="/replies?mail=0b9e4d1a-7c2f-4e6b-9a3d-5f8c1b2e4a6d"');
    expect(html).toContain("4 unread");
    expect(html).toContain("Mark all read");
    expect(html).toContain(`href="/applications?application=${APP_ID}"`);
    expect(html).toContain('aria-label="Mark Backend engineer read"');
    expect(html).toContain('aria-label="Dismiss Backend engineer"');
    expect(html).toContain('aria-label="Open Backend engineer"');
    // A read row has nothing to mark read; it can still be dismissed.
    expect(html).not.toContain('aria-label="Mark Data engineer read"');
    expect(html).toContain('aria-label="Dismiss Data engineer"');
    // Only a reminder is answerable: one snooze and one clear, on the reminder row alone.
    expect(html.match(/Snooze to tomorrow/g)).toHaveLength(1);
    expect(html.match(/>Clear</g)).toHaveLength(1);
    expect(html).not.toContain("Nothing needs your attention right now.");
  });

  it("offers the two answers only where the key names a reminder's application", () => {
    state.inbox = {
      data: {
        items: [
          { ...ITEMS[0], key: "reminder:not-an-id:1761600000" },
          { ...ITEMS[1], key: `reminder:3f2b8c1e-6a4d-4f9b-8e2c-1d5a7b9c0e3f:1761600000` },
        ],
        unread: 0,
      },
      isSuccess: true,
      isError: false,
    };
    const html = render();
    // The malformed reminder keeps its sentence but gets no press that could 404.
    expect(html).toContain("Your reminder for Backend engineer is due.");
    expect(html).not.toContain("Snooze to tomorrow");
    // A stale row is not a reminder even when its key carries a reminder's spelling.
    expect(html).toContain("No movement on Data engineer — it has gone quiet.");
  });

  it("says the same sentences in the reader's language", () => {
    state.inbox = {
      data: {
        items: [
          { ...ITEMS[0], title: "后端工程师", subject: "Acme" },
          { ...ITEMS[2], note: "订阅源返回 HTTP 503" },
          { ...ITEMS[4], title: "远程 Rust", read: true },
          { ...ITEMS[5], subject: "Re: 面试" },
        ],
        unread: 2,
      },
      isSuccess: true,
      isError: false,
    };
    const html = render("zh");
    expect(html).toContain("通知");
    expect(html).toContain("你对 后端工程师 的提醒已到期。");
    expect(html).toContain("HN hiring 的上一次拉取失败了。");
    expect(html).toContain("订阅源返回 HTTP 503");
    expect(html).toContain("你的已保存搜索「远程 Rust」有 4 个新职位。");
    expect(html).toContain("已保存搜索");
    expect(html).toContain("招聘方回复了你的投递 —— Initech。");
    expect(html).toContain("招聘方回复");
    expect(html).toContain("Re: 面试");
    expect(html).toContain("2 条未读");
    expect(html).toContain("全部标为已读");
    expect(html).toContain("推迟到明早");
    expect(html).toContain("清除");
    expect(html).not.toContain("Your reminder for");
  });

  it("holds the empty copy until the inbox has actually answered", () => {
    const pending = render();
    expect(pending).not.toContain("Nothing needs your attention right now.");
    expect(pending).not.toContain("The inbox couldn't be loaded.");
    // Nothing is claimed about unread rows before the answer arrives.
    expect(pending).not.toContain("Everything here is read.");

    state.inbox = { data: { items: [], unread: 0 }, isSuccess: true, isError: false };
    const empty = render();
    expect(empty).toContain("Nothing needs your attention right now.");
    expect(empty).toContain(
      "A reminder that comes due, an application that goes quiet, or a failed feed pull will appear here."
    );
    expect(empty).toContain("Everything here is read.");
  });

  it("names a failed read rather than pretending the inbox is empty", () => {
    state.inbox = { data: undefined, isSuccess: false, isError: true };
    const html = render();
    // React escapes the apostrophe in the static markup.
    expect(html).toContain("The inbox couldn&#x27;t be loaded.");
    expect(html).not.toContain("Nothing needs your attention right now.");
    // The badge and the bulk action wait for an answer too.
    expect(html).not.toContain("Everything here is read.");
    expect(html).not.toContain("Mark all read");
  });
});
