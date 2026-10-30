import { afterEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL } from "@/lib/api/endpoints";
import { fetchMailSettings, setMailDial } from "@/lib/hooks/mail-settings";

const okEnv = (data: unknown) => ({ success: true, data, error: null });

let urls: string[] = [];
let inits: RequestInit[] = [];
function mockFetch(data: unknown) {
  urls = [];
  inits = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      urls.push(url);
      inits.push(init ?? {});
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

describe("setMailDial", () => {
  it("writes the dial in the path and the state in the body", () => {
    // The path names *which* dial and the body says what it becomes: a dial sent
    // in the body would read as the whole settings page, and a state in the path
    // would be a second spelling of a boolean the backend already has.
    mockFetch({ url: "https://careeros.example/x", weekly: false, signals: true, reminders: true });

    return setMailDial("weekly", false).then(() => {
      expect(urls).toEqual([`${API_BASE_URL}/me/mail/settings/weekly`]);
      expect(inits[0].method).toBe("PUT");
      expect(inits[0].body).toBe(JSON.stringify({ enabled: false }));
    });
  });

  it("answers with every dial rather than the one it wrote", () => {
    // The screen replaces its state with the answer, so a dial a sweep turned off
    // between the read and this press has to come back with it -- otherwise the
    // switch for that dial would keep showing the stale read until a refetch.
    const fresh = {
      url: "https://careeros.example/x",
      weekly: true,
      signals: true,
      reminders: false,
    };
    mockFetch(fresh);

    return expect(setMailDial("reminders", false)).resolves.toEqual(fresh);
  });
});
