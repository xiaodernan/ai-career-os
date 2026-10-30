import { afterEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL } from "@/lib/api/endpoints";
import { fetchMailSettings } from "@/lib/hooks/mail-settings";

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

describe("fetchMailSettings", () => {
  it("asks the signed-in route rather than the page a letter carries", () => {
    mockFetch({ url: "https://careeros.example/api/v1/mail/preferences/1.abc", weekly: true, signals: true, reminders: true });

    return fetchMailSettings().then(() => {
      expect(urls).toEqual([`${API_BASE_URL}/me/mail/settings`]);
    });
  });

  it("keeps the signed address verbatim and every dial's own answer", () => {
    // The address is a credential, so it travels as one opaque string; and an "off"
    // dial must stay false rather than be filled in from the default.
    const signed =
      "https://careeros.example/api/v1/mail/preferences/11111111-1111-4111-8111-111111111111.Xyz_-9Q";
    mockFetch({ url: signed, weekly: false, signals: true, reminders: false });

    return expect(fetchMailSettings()).resolves.toEqual({
      url: signed,
      weekly: false,
      signals: true,
      reminders: false,
    });
  });
});
