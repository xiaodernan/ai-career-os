import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import type * as React from "react";

vi.mock("@/lib/i18n/locale-context", () => ({
  useLocale: () => ({ locale: "en", t: (key: string) => key, setLocale: () => {} }),
}));

const lettersState = vi.hoisted(() => ({
  value: {} as {
    data?: unknown;
    isPending?: boolean;
    isError?: boolean;
    isFetching?: boolean;
    error?: unknown;
    refetch?: () => unknown;
  },
}));

vi.mock("@/lib/hooks/resources", () => ({
  useApplicationLetters: () => ({
    data: undefined,
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => undefined,
    ...lettersState.value,
  }),
}));

import { ApplicationLettersPanel } from "./application-letters";

const render = () =>
  renderToStaticMarkup(<ApplicationLettersPanel applicationId="app-1" />);

describe("ApplicationLettersPanel", () => {
  it("draws a loading skeleton without claiming there are no letters", () => {
    lettersState.value = { isPending: true };

    const html = render();

    expect(html).toContain('role="status"');
    expect(html).not.toContain("applications.dialog.lettersEmpty");
  });

  it("says the shelf is empty only after an empty list arrives", () => {
    lettersState.value = { data: [] };

    const html = render();

    expect(html).toContain("applications.dialog.lettersEmpty");
    expect(html).toContain("applications.dialog.lettersHint");
  });

  it("shows each kept letter's first line, dials and whole body", () => {
    lettersState.value = {
      data: [
        {
          id: "letter-1",
          body: "Dear hiring manager,\n\nI built the thing.",
          mode: "formal",
          tone: "warm",
          length: "short",
          createdAt: "2026-11-03T09:00:00Z",
        },
      ],
    };

    const html = render();

    expect(html).toContain("Dear hiring manager,");
    expect(html).toContain("I built the thing.");
    expect(html).toContain("formal · warm · short");
    expect(html).toContain("applications.dialog.letterKept");
    expect(html.match(/<details/g)?.length).toBe(1);
  });

  it("reports a failed read instead of drawing an empty shelf", () => {
    lettersState.value = { isError: true, error: new Error("nope") };

    const html = render();

    expect(html).toContain("applications.dialog.lettersFailed");
    expect(html).not.toContain("applications.dialog.lettersEmpty");
  });
});
