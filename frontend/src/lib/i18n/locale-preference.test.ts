import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api/client", () => ({ request: vi.fn() }));
vi.mock("@/lib/api/token-store", () => ({ tokenStore: { hasSession: vi.fn() } }));

import { request } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { tokenStore } from "@/lib/api/token-store";

import { asLocale, decideLocale, saveLocalePreference } from "./locale-preference";

/**
 * The account/browser reconciliation (roadmap 21.4).
 *
 * The account's language is what the nightly letter reads; the cookie is what this
 * browser paints. The rules worth pinning: a known account language never erases an
 * explicit choice made here (the choice is pushed instead), a browser that never
 * chose follows the account without claiming a choice of its own, and an unknown
 * account language means no action at all.
 */

describe("asLocale", () => {
  it("accepts exactly the two languages the product speaks", () => {
    expect(asLocale("en")).toBe("en");
    expect(asLocale("zh")).toBe("zh");
  });

  it("answers null for anything else, including near misses", () => {
    for (const value of ["EN", "zh-CN", "", " fr", null, undefined, 1, {}, ["zh"]]) {
      expect(asLocale(value)).toBeNull();
    }
  });
});

describe("decideLocale", () => {
  it("does nothing when the account names no known language", () => {
    // An older backend, a payload still in flight, or a language this build cannot paint.
    for (const account of [undefined, null, "fr", ""]) {
      expect(decideLocale(account, "en", null)).toEqual({ action: "none" });
      expect(decideLocale(account, "zh", "en")).toEqual({ action: "none" });
    }
  });

  it("a browser with no choice adopts the account's language when they differ", () => {
    expect(decideLocale("zh", "en", null)).toEqual({ action: "adopt", locale: "zh" });
    expect(decideLocale("en", "zh", null)).toEqual({ action: "adopt", locale: "en" });
  });

  it("a browser with no choice and the account's language already on screen does nothing", () => {
    expect(decideLocale("zh", "zh", null)).toEqual({ action: "none" });
    expect(decideLocale("en", "en", null)).toEqual({ action: "none" });
  });

  it("an explicit choice in this browser is pushed to the account when they differ", () => {
    // The switch is the reader's most recent instruction; this is how it reaches the letter.
    expect(decideLocale("zh", "en", "en")).toEqual({ action: "save", locale: "en" });
    expect(decideLocale("en", "zh", "zh")).toEqual({ action: "save", locale: "zh" });
  });

  it("an explicit choice that agrees with the account is not rewritten", () => {
    expect(decideLocale("zh", "zh", "zh")).toEqual({ action: "none" });
    expect(decideLocale("en", "en", "en")).toEqual({ action: "none" });
  });

  it("never pushes a language taken from the screen alone", () => {
    // Whatever the screen shows, the only thing worth writing is the reader's own choice.
    expect(decideLocale("zh", "zh", "en")).toEqual({ action: "save", locale: "en" });
  });
});

describe("saveLocalePreference", () => {
  beforeEach(() => {
    vi.mocked(request).mockReset();
    vi.mocked(tokenStore.hasSession).mockReset();
  });

  it("writes the language onto the account through the same PATCH the settings use", async () => {
    vi.mocked(tokenStore.hasSession).mockReturnValue(true);
    vi.mocked(request).mockResolvedValue({});

    await saveLocalePreference("zh");

    expect(request).toHaveBeenCalledTimes(1);
    expect(request).toHaveBeenCalledWith(endpoints.auth.me, {
      method: "PATCH",
      body: { locale: "zh" },
    });
  });

  it("a signed-out reader has only the cookie, so nothing is sent", async () => {
    vi.mocked(tokenStore.hasSession).mockReturnValue(false);

    await saveLocalePreference("en");

    expect(request).not.toHaveBeenCalled();
  });
});
