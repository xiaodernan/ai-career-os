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

vi.mock("@/lib/hooks/actions", () => ({
  useDeleteApplicationLetter: () => ({ isPending: false, mutate: () => undefined }),
  useUpdateApplicationLetter: () => ({ isPending: false, mutate: () => undefined }),
}));

import { ApplicationLettersPanel, LetterEditor } from "./application-letters";

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
    expect(html).toContain("applications.dialog.letterDelete");
    expect(html).toContain("applications.dialog.letterEdit");
    expect(html).toContain("applications.dialog.letterCopy");
    expect(html).toContain("applications.dialog.letterDownload");
    expect(html.match(/<details/g)?.length).toBe(1);
  });

  it("offers no way to take away a letter that has no text", () => {
    lettersState.value = { data: [{ id: "letter-1", body: "" }] };

    const html = render();

    expect(html).not.toContain("applications.dialog.letterCopy");
    expect(html).not.toContain("applications.dialog.letterDownload");
    expect(html).toContain("applications.dialog.letterEdit");
  });

  it("says a corrected letter was edited, not first kept", () => {
    lettersState.value = {
      data: [
        {
          id: "letter-1",
          body: "Corrected words",
          createdAt: "2026-11-03T09:00:00Z",
          updatedAt: "2026-11-04T09:00:00Z",
        },
      ],
    };

    const html = render();

    expect(html).toContain("applications.dialog.letterEdited");
    expect(html).not.toContain("applications.dialog.letterKept");
  });

  it("reports a failed read instead of drawing an empty shelf", () => {
    lettersState.value = { isError: true, error: new Error("nope") };

    const html = render();

    expect(html).toContain("applications.dialog.lettersFailed");
    expect(html).not.toContain("applications.dialog.lettersEmpty");
  });
});

describe("LetterEditor", () => {
  const editor = (letter: Record<string, unknown> = {}) =>
    renderToStaticMarkup(
      <LetterEditor
        letter={{ id: "letter-1", body: "Dear Ada,", tone: "warm", length: "short", ...letter }}
        saving={false}
        onCancel={() => undefined}
        onSave={() => undefined}
      />
    );

  it("opens with the letter's own words and both dials", () => {
    const html = editor();

    expect(html).toContain("Dear Ada,");
    expect(html).toContain("coverLetter.tone");
    expect(html).toContain("coverLetter.length");
    expect(html.match(/role="combobox"/g)).toHaveLength(2);
  });

  it("will not save a correction that only removes the words", () => {
    const html = editor({ body: "   " });

    const saveAt = html.indexOf("applications.dialog.letterSave");
    expect(saveAt).toBeGreaterThan(0);
    const saveButton = html.slice(html.lastIndexOf("<button", saveAt), saveAt);
    expect(saveButton).toContain("disabled");
  });
});
