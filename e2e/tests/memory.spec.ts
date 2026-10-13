import { expect, test, unwrap } from "./fixtures";

/**
 * The memory-correction surface, end to end (AGENTS.md §6).
 *
 * A fresh account has no memories: the extraction path runs after a copilot turn or an
 * interview finalize, and this suite provisions a new user per test. So the journey here
 * is the honest one for that user -- the proxy answers with an empty list rather than an
 * error, and the settings card says "nothing remembered yet" rather than spinning or
 * failing. The correction flows (edit, forget) need a row to act on, which is unit- and
 * integration-tested on both planes; what only E2E can prove is that the card mounts on
 * the real page, talks to the real proxy, and renders the empty answer as an empty state.
 *
 * Two tests rather than one: the API half fails with a stack trace naming the route, the
 * UI half with the page that stopped rendering it -- different owners, different fixes.
 */

test("the memories proxy answers a fresh user with an empty list, not an error", async ({ api }) => {
  const res = await api.get("/memories");
  expect(res.status(), `GET /memories -> ${await res.text()}`).toBe(200);
  const data = await unwrap<unknown[]>(res);
  // The backend controller returns a bare list; the ai-service's `{items}` spelling is
  // the other shape this route may carry, and both are an empty answer for a new user.
  expect(Array.isArray(data) ? data : (data as { items?: unknown[] }).items).toEqual([]);
});

test("the settings page renders the memory card with its honest empty state", async ({ authedPage }) => {
  await authedPage.goto("/settings");
  await expect(
    authedPage.getByText("What the agents remember")
  ).toBeVisible({ timeout: 20_000 });
  await expect(
    authedPage.getByText("Nothing remembered yet")
  ).toBeVisible({ timeout: 20_000 });
});
