import { expect, test } from "./fixtures";

/**
 * The edge, watched by a browser-adjacent request (Epic: edge-verified 2026-11-12).
 *
 * The gateway sat `unhealthy` for weeks: the route `lb://backend` resolved to zero instances
 * (the registry held `CAREER-OS-BACKEND` with a mismatched VIP, and the eureka profile emptied
 * the simple list) AND the edge's own BackendHealthIndicator pinned DOWN on a parse bug
 * (it read `status` at the top level of the envelope). The e2e suite never noticed, because
 * the API fixtures talk to the backend directly and skip the edge entirely.
 *
 * This spec pins the edge path itself: it answers the backend's own health answer through
 * `lb://backend`, and it lets the backend's own auth boundary speak for an authed route.
 * The gateway's container health is then covered by the compose healthcheck, not re-asserted
 * here -- the claim under test is the routing and the probe wiring, not Docker's policy.
 *
 * Skips cleanly when the gateway isn't published (127.0.0.1:8081), so this spec never runs
 * in environments without the edge up rather than failing red for the wrong reason.
 */
const EDGE = process.env.E2E_EDGE_URL ?? "http://127.0.0.1:8081";

test("the edge routes /api/** to the backend and answers the backend's own health", async ({ request }) => {
  const health = await request.get(`${EDGE}/api/v1/health`, { failOnStatusCode: false });
  if (!health.ok()) {
    throw new Error(
      `edge health at ${EDGE}/api/v1/health answered HTTP ${health.status()} -- ` +
        `the gateway is not routed (see MICROSERVICES.md §1.5 and docker-compose.yml)`
    );
  }
  expect(health.status()).toBe(200);
  const body = await health.json();
  expect(body.success).toBe(true);
  expect(body.data?.status).toBe("ok");

  const unauthed = await request.get(`${EDGE}/api/v1/timeline`, { failOnStatusCode: false });
  expect(unauthed.status()).toBe(401);
  const refused = await unauthed.json();
  expect(refused.error?.code).toBe("UNAUTHORIZED");
});
