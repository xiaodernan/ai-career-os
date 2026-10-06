import { expect, test } from "./fixtures";

/**
 * Every signed-in route renders its own heading.
 *
 * The golden journey walks the PRD §35 flow, which reaches ten of the twenty-one
 * routes. The rest — companies, knowledge, settings, activity, and the resume detail
 * page — had no end-to-end coverage at all, so a page that broke on its own data would
 * only be discovered by clicking to it by hand.
 *
 * Asserting the heading, not just a 200, is the point: every route here is a client
 * component behind auth, so the server returns the same shell no matter what the page
 * does next. A 200 proves the route exists; the heading proves the page ran.
 *
 * One test rather than one per route, because the `authedPage` fixture registers a real
 * account per test and this suite already provisions one per journey step. A single pass
 * keeps that cost flat and still reports every route that failed.
 */

const ROUTES: { path: string; heading: string }[] = [
  { path: "/jobs", heading: "Jobs" },
  { path: "/companies", heading: "Companies" },
  { path: "/resumes", heading: "Resumes" },
  { path: "/knowledge", heading: "Knowledge Base" },
  { path: "/applications", heading: "Applications" },
  { path: "/interviews", heading: "Interviews" },
  { path: "/activity", heading: "AI Activity" },
  { path: "/settings", heading: "Settings" },
  { path: "/copilot", heading: "Ask your career agent" },
];

/** Next's default boundary text — the signal that a client component threw. */
const CRASH = "Application error";

test("every signed-in route renders its heading", async ({ authedPage }) => {
  const failures: string[] = [];

  for (const { path, heading } of ROUTES) {
    try {
      await authedPage.goto(path);

      // A redirect here means the session was rejected, not that the page is fine.
      if (/\/login/.test(authedPage.url())) {
        failures.push(`${path}: bounced to the login screen`);
        continue;
      }

      const body = authedPage.locator("body");
      if (await body.innerText().then((t) => t.includes(CRASH))) {
        failures.push(`${path}: rendered Next's error boundary ("${CRASH}")`);
        continue;
      }

      await expect(
        authedPage.getByRole("heading", { level: 1, name: heading })
      ).toBeVisible({ timeout: 20_000 });
    } catch (err) {
      failures.push(`${path}: ${err instanceof Error ? err.message.split("\n")[0] : String(err)}`);
    }
  }

  expect(
    failures,
    `${failures.length} of ${ROUTES.length} routes did not render:\n  ${failures.join("\n  ")}`
  ).toEqual([]);
});

test("an unknown route inside the app shell is a 404, not a crash", async ({ authedPage }) => {
  const res = await authedPage.goto("/this-route-does-not-exist");
  expect(res?.status()).toBe(404);
  expect(await authedPage.locator("body").innerText()).not.toContain(CRASH);
});
