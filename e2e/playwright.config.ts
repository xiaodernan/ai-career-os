import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright configuration for the AI Career OS golden journey (PRD §35).
 *
 * The suite drives the *real* stack: a running Spring Boot backend, a running
 * FastAPI ai-service and the Next.js frontend. It deliberately does not stub
 * the API — PRD §35 says the flow "必须真正跑通", and a mocked network would
 * prove nothing about the product. What makes this safe to run repeatedly is
 * that the backend runs with LLM_PROVIDER=mock / EMBEDDING_PROVIDER=hash, so
 * every AI call is deterministic and free while still going through the real
 * orchestrator, retrieval and persistence paths.
 *
 * Configured targets (override through env when your ports differ):
 *   E2E_BASE_URL   frontend origin            default http://localhost:3000
 *   E2E_API_URL    backend /api/v1 base       default http://127.0.0.1:8080/api/v1
 *
 * Note on hosts: the backend allows exactly the origins in APP_CORS_ORIGINS
 * (default `http://localhost:3000`). `localhost` and `127.0.0.1` are *different*
 * origins to a browser, so the frontend must be visited as `localhost` or CORS
 * will reject every call with "Invalid CORS request".
 */

const BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const API_URL = process.env.E2E_API_URL ?? "http://127.0.0.1:8080/api/v1";

export default defineConfig({
  testDir: "./tests",
  // One user journey mutates shared state (applications, interviews), so the
  // golden path runs serially. Specs that are independent opt into more
  // workers via their own project if needed.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  /**
   * The HTML reporter is opt-in (`E2E_HTML=1`).
   *
   * It rewrites a whole directory at teardown, which is one more bulk filesystem
   * operation going through this sandbox's delete shim. The list reporter is
   * enough to see pass/fail; ask for the report when you actually want to browse
   * traces.
   */
  reporter: process.env.E2E_HTML
    ? [["list"], ["html", { open: "never" }]]
    : [["list"]],
  /**
   * Where per-test artifacts land. Overridable so a run can be pointed at a
   * scratch directory and leave the repo untouched.
   *
   * Note the runner in this sandbox is slow to tear down (roughly 20s per test,
   * and the node process may outlive the summary line). The tests themselves are
   * what matter and the summary is the result — see README "Running it".
   */
  outputDir: process.env.E2E_OUTPUT_DIR ?? "test-results",
  use: {
    baseURL: BASE_URL,
    /**
     * Traces are the first knob to turn on when debugging a failure:
     * `E2E_TRACE=on npx playwright test`. Left off by default because every
     * written artifact is another bulk filesystem operation this sandbox's
     * delete shim has to arbitrate.
     */
    trace: process.env.E2E_TRACE === "on" ? "on" : "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    actionTimeout: 20_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 900 } },
    },
  ],
  metadata: { apiUrl: API_URL },
});

export const API_BASE = API_URL;
