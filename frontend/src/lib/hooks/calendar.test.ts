import { afterEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL } from "@/lib/api/endpoints";
import { fetchCalendarLink } from "@/lib/hooks/calendar";

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

describe("fetchCalendarLink", () => {
  it("asks the one route the backend signs addresses on", () => {
    mockFetch({ url: "https://careeros.example/api/v1/calendar.ics?token=abc" });

    return fetchCalendarLink().then(() => {
      expect(urls).toEqual([`${API_BASE_URL}/calendar/link`]);
    });
  });

  it("hands back the signed address verbatim, punctuation and all", () => {
    // The URL is the credential, so it travels as one opaque string: no trimming,
    // no re-encoding of the token's base64url alphabet, no rebuilding from parts.
    const signed =
      "https://careeros.example/api/v1/calendar.ics?token=11111111-1111-4111-8111-111111111111.Xyz_-9Q";
    mockFetch({ url: signed });

    return expect(fetchCalendarLink()).resolves.toEqual({ url: signed });
  });
});
