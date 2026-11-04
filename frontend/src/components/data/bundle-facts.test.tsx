import { describe, expect, it, vi } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";

// The reader the card renders for; hoisted so the locale mock below can close over it.
const reader = vi.hoisted(() => ({ locale: "en" as "en" | "zh" }));

// The stub resolves keys off the real table, like the provider: a missing key falls back
// to its own name (and makes the label-presence check below meaningful).
vi.mock("@/lib/i18n/locale-context", async () => {
  const actual = await vi.importActual<typeof import("@/lib/i18n/locale-context")>(
    "@/lib/i18n/locale-context"
  );
  const { translations } = await import("@/lib/i18n/translations");
  return {
    ...actual,
    useLocale: () => ({
      locale: reader.locale,
      setLocale: () => {},
      t: (key: string, vars?: Record<string, string | number>) => {
        const value = actual.lookup(translations[reader.locale], key);
        return value === undefined ? key : actual.fill(value, vars);
      },
    }),
  };
});

import { BundleFacts } from "./bundle-facts";
import type { ExportBundle } from "@/lib/api/types";

/**
 * The "Generated" fact under an export's content hash.
 *
 * The bundle carries the server's build instant as an RFC3339 string, and the card used
 * to print it verbatim: "Generated" above "2026-10-28T06:05:00.000Z". Every other clock
 * in the product goes through formatDateTime, so the one machine-format stamp read as a
 * wire value on an otherwise translated card. The instant stays the server's; the clock
 * is the reader's.
 */

const built = new Date(2026, 9, 28, 14, 5).toISOString();

function render(bundle: ExportBundle): string {
  return renderToStaticMarkup(<BundleFacts bundle={bundle} />);
}

const exportWith = (generatedAt?: string): ExportBundle => ({
  generated_at: generatedAt,
  manifest: { content_hash: "sha256:abc123" },
});

describe("the export facts card's build instant", () => {
  it("draws the stamp in an English reader's clock, not the wire format", () => {
    const html = render(exportWith(built));
    expect(html, "the card still shows the hash it was rendered beside").toContain("sha256:abc123");
    expect(html, "the build instant is the date formatDateTime draws").toMatch(/Oct 28, 02:05\sPM/);
    expect(html, "an en reader got the server's raw RFC3339 string").not.toContain(built);
  });

  it("draws it in a Chinese reader's clock", () => {
    reader.locale = "zh";
    try {
      const html = render(exportWith(built));
      expect(html, "a zh reader got the machine's stamp").toContain("10月28日 14:05");
      expect(html, "a zh reader got the raw RFC3339 string").not.toContain(built);
      expect(html, "a zh reader got the English clock").not.toContain("Oct 28");
    } finally {
      reader.locale = "en";
    }
  });

  it("keeps the em dash when the bundle names no instant", () => {
    const html = render(exportWith(undefined));
    expect(html, "a bundle with no stamp is not a reason to lose the label").not.toContain("data.generated");
    expect(html, "the placeholder is the page's em dash").toContain("—");
    expect(html, "an absent stamp drew a date").not.toMatch(/Oct 28|10月28日/);
  });
});
