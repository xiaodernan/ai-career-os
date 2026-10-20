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
  // The surfaces the forward bridges (11.3, 12.x, 13.x, 14.x, 15.x, 16.1) built.
  { path: "/growth", heading: "Growth report" },
  { path: "/networking", heading: "Contacts" },
  { path: "/analysis", heading: "Analysis" },
  { path: "/offers", heading: "Offers" },
  { path: "/ingestion", heading: "Job ingestion" },
  { path: "/data", heading: "Your data" },
  { path: "/monitoring", heading: "Monitoring" },
  { path: "/rate-limit", heading: "Rate limiting" },
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

/**
 * The public front door: the marketing page (18.2). It is the one route an
 * anonymous visitor can reach, so it is checked without an account — and the
 * check is that it renders its pitch rather than bouncing to the login screen.
 */
test("the landing page is public and renders the pitch", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("link", { name: /get started/i }).first()).toBeVisible();
  expect(await page.locator("body").innerText()).not.toContain(CRASH);
});

/**
 * The branded boundary is server-rendered for any unmatched path, session or
 * no session -- so an unauthenticated visit can prove it without provisioning
 * an account (and without spending one of the auth rate-limit slots).
 */
test("an unauthenticated visit to a bogus route gets the branded not-found", async ({ page }) => {
  const res = await page.goto("/definitely-not-a-route");
  expect(res?.status()).toBe(404);
  await expect(page).toHaveTitle(/Page not found/);
  await expect(
    page.getByRole("heading", { level: 1, name: "This page is not on the map." })
  ).toBeVisible();
  await expect(page.getByRole("link", { name: "Back to the dashboard" })).toBeVisible();
});

/**
 * The server ships the same shell for every (app) route regardless of session,
 * so the guard that keeps anonymous visitors out is the client-side one in the
 * (app) layout -- it runs after hydration and swaps the URL to /login. The
 * assertion is the URL change itself; a status code would always be 200. The
 * title check then proves the login screen actually mounted (its title comes
 * from the route segment's metadata, not from anything the form renders).
 */
test("an unauthenticated visit to a protected route lands on the login screen", async ({ page }) => {
  await page.goto("/dashboard");
  await page.waitForURL(/\/login/, { timeout: 15_000 });
  await expect(page).toHaveTitle(/Sign in/);
});
