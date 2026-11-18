import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import type { InboundMail } from "@/lib/api/types";

/**
 * Epic 332 — the analyst's read of one letter.
 * The card renders ask-first; the parse appears only after the mutation keeps one,
 * and a decode with nothing grounded behind it is a quiet card, never a confident one.
 */
const decodeHook: {
  data: unknown;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  mutate: any;
  isPending: boolean;
  isError: boolean;
  error: unknown;
} = { data: undefined, mutate: vi.fn(), isPending: false, isError: false, error: undefined };

vi.mock("@/lib/hooks/replies", () => ({
  useDecodeReply: () => decodeHook,
}));

import { InboundDecode } from "./inbound-decode";
import { LocaleProvider } from "@/lib/i18n/locale-context";

const LETTER: InboundMail = {
  id: "m-1",
  fromAddress: "ada@example.com",
  subject: "Your interview",
  bodyText: "Hi, could you confirm 2026-11-27 works?",
  intent: "interview",
  company: "Acme",
  role: "Backend Engineer",
  suggestedStage: "interview",
  applicationId: null,
  applicationTitle: null,
  receivedAt: "2026-11-19T09:00:00Z",
  filedAt: null,
};

function render(locale: "en" | "zh"): string {
  vi.stubGlobal("window", {
    localStorage: { getItem: () => locale, setItem: () => {} },
  });
  try {
    return renderToStaticMarkup(
      <LocaleProvider>
        <InboundDecode mail={LETTER} />
      </LocaleProvider>
    );
  } finally {
    vi.unstubAllGlobals();
  }
}

describe("the analyst's read of one letter", () => {
  it("renders the ask-first CTA in both languages before the analyst speaks", () => {
    decodeHook.data = undefined;
    decodeHook.isPending = false;
    decodeHook.isError = false;
    const en = render("en");
    expect(en).toContain("Decode this letter");
    expect(en).not.toContain("Do next");

    const zh = render("zh");
    expect(zh).toContain("解读这封信");
    expect(zh).not.toContain("下一步");
  });

  it("shows the kept parse with its own facts — and nothing that was not in the letter", () => {
    decodeHook.data = {
      mailId: "m-1",
      decode: {
        intent: "interview",
        deadline: "2026-11-27",
        next_action: "Confirm 2026-11-27 works.",
        asks: ["Confirm 2026-11-27"],
        reply: "Hi — 2026-11-27 works for me.",
      },
    };
    decodeHook.isError = false;

    const en = render("en");
    expect(en).toContain("Confirm 2026-11-27 works.");
    expect(en).toContain("Confirm 2026-11-27");
    expect(en).toContain("Hi — 2026-11-27 works for me.");

    const zh = render("zh");
    expect(zh).toContain("下一步");
    expect(zh).toContain("2026");
  });

  it("stays quiet rather than inventing when the analyst had nothing grounded", () => {
    decodeHook.data = { mailId: "m-1" }; // no decode key at all
    const en = render("en");
    expect(en).toContain("stands still enough");
    expect(en).not.toContain("Do next");
  });

  it("announces its own failure instead of lying", () => {
    decodeHook.data = undefined;
    decodeHook.isError = true;
    expect(render("en")).toContain("could not finish");
    expect(render("zh")).toContain("解读没完成");
  });
});
