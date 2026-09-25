import { test as base, expect, type APIRequestContext, type Page } from "@playwright/test";

/**
 * Shared fixtures for the golden-journey suite.
 *
 * Every run provisions a brand-new account through the real API so the suite is
 * idempotent and never depends on (or corrupts) an existing user's data. The
 * registered credentials are handed to the UI test so it can exercise the login
 * form for real rather than injecting a token into localStorage.
 */

export const API_URL = process.env.E2E_API_URL ?? "http://127.0.0.1:8080/api/v1";
export const AI_URL = process.env.E2E_AI_URL ?? "http://127.0.0.1:8000";

export interface E2EUser {
  id: string;
  email: string;
  password: string;
  displayName: string;
  accessToken: string;
  refreshToken: string;
}

/** Unique-ish email so parallel or repeated runs never collide. */
export function uniqueEmail(prefix = "e2e"): string {
  const stamp = Date.now().toString(36);
  const rand = Math.random().toString(36).slice(2, 8);
  return `${prefix}+${stamp}${rand}@careeros.test`;
}

export const TEST_PASSWORD = "Passw0rd!234";

/** Wait for a service to answer, so the suite fails with a clear message. */
export async function waitForService(
  request: APIRequestContext,
  url: string,
  { timeoutMs = 60_000, intervalMs = 1_000 } = {}
): Promise<void> {
  const deadline = Date.now() + timeoutMs;
  let lastErr = "no attempt made";
  while (Date.now() < deadline) {
    try {
      const res = await request.get(url, { timeout: 4_000, failOnStatusCode: false });
      if (res.status() < 500) return;
      lastErr = `HTTP ${res.status()}`;
    } catch (err) {
      lastErr = err instanceof Error ? err.message : String(err);
    }
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  throw new Error(`Service at ${url} did not become ready within ${timeoutMs}ms (last: ${lastErr})`);
}

/** Register a fresh user against the live API and return its tokens. */
export async function registerUser(
  request: APIRequestContext,
  overrides: Partial<Pick<E2EUser, "email" | "displayName">> = {}
): Promise<E2EUser> {
  const email = overrides.email ?? uniqueEmail();
  const displayName = overrides.displayName ?? "E2E Runner";
  const res = await request.post(`${API_URL}/auth/register`, {
    data: { email, password: TEST_PASSWORD, displayName },
  });

  // Every test provisions its own account for isolation, so a full run issues one
  // registration per test — more than the product's auth limit (10/min per IP).
  // Without this branch that arrives as a bare "expected 201" and looks like a
  // broken endpoint; say what actually happened and how to fix it.
  if (res.status() === 429) {
    throw new Error(
      `Registration was rate limited (429) after provisioning accounts for this run.\n` +
      `The suite creates one account per test, and /api/v1/auth/** allows ` +
      `${process.env.E2E_AUTH_LIMIT ?? "10"}/min per IP.\n` +
      `Start the backend with a higher limit for E2E runs, e.g.:\n` +
      `  RATELIMIT_AUTH_PER_MINUTE=100 bash scripts/mvn.sh spring-boot:run\n` +
      `Or wait ~60s for the window to slide.`
    );
  }
  expect(res.status(), `register ${email} -> ${await res.text()}`).toBe(201);
  const body = (await res.json()) as {
    data: { user: { id: string }; tokens: { accessToken: string; refreshToken: string } };
  };
  return {
    id: body.data.user.id,
    email,
    password: TEST_PASSWORD,
    displayName,
    accessToken: body.data.tokens.accessToken,
    refreshToken: body.data.tokens.refreshToken,
  };
}

/** An API client already authorised as `user`. */
export function apiFor(request: APIRequestContext, user: E2EUser) {
  const headers = { Authorization: `Bearer ${user.accessToken}` };
  return {
    get: (path: string, params?: Record<string, string | number | boolean | undefined>) =>
      request.get(`${API_URL}${path}`, { headers, params }),
    post: (path: string, data?: unknown) => request.post(`${API_URL}${path}`, { headers, data }),
    patch: (path: string, data?: unknown) => request.patch(`${API_URL}${path}`, { headers, data }),
    delete: (path: string) => request.delete(`${API_URL}${path}`, { headers }),
    /**
     * multipart/form-data upload — the real "Upload Resume" path (PRD §35).
     *
     * `multipart` is a map of *field name* → value, so the file has to be nested
     * under the form field the controller reads (`file`). Passing the file object
     * itself makes Playwright treat `name`/`mimeType`/`buffer` as three separate
     * fields, and the raw Buffer then fails with `stream.on is not a function`.
     */
    upload: (path: string, file: { name: string; mimeType: string; buffer: Buffer },
             field = "file") =>
      request.post(`${API_URL}${path}`, { headers, multipart: { [field]: file } }),
  };
}

/** Strip the {success,data,error} envelope, failing loudly on a bad response. */
export async function unwrap<T>(res: { status: () => number; json: () => Promise<unknown>; text: () => Promise<string> }): Promise<T> {
  const raw = await res.text();
  let parsed: { success: boolean; data: T; error: { code?: string; message?: string } | null };
  try {
    parsed = JSON.parse(raw);
  } catch {
    throw new Error(`Expected JSON envelope but got: ${raw.slice(0, 400)}`);
  }
  if (!parsed.success) {
    throw new Error(`API error ${parsed.error?.code}: ${parsed.error?.message} (status ${res.status()})`);
  }
  return parsed.data;
}

export type Fixtures = {
  user: E2EUser;
  api: ReturnType<typeof apiFor>;
  /** A page whose session is already established via the real login form. */
  authedPage: Page;
};

export const test = base.extend<Fixtures>({
  user: async ({ request }, use) => {
    await waitForService(request, `${AI_URL}/health`);
    await waitForService(request, `${API_URL}/health`);
    const user = await registerUser(request);
    await use(user);
  },

  api: async ({ request, user }, use) => {
    await use(apiFor(request, user));
  },

  authedPage: async ({ page, user }, use) => {
    // Log in through the real form so the JWT is stored exactly the way the app
    // stores it. This also covers the login screen itself on every run.
    await page.goto("/login");
    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Password", { exact: true }).fill(user.password);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).not.toHaveURL(/\/login/, { timeout: 30_000 });
    await use(page);
  },
});

export { expect };
