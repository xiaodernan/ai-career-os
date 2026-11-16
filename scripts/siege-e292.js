// Epic 292 — the siege, widened: the newly-instrumented overseer surface joins the load table.
// GET only, no mutations to trip on. Two new public reads ride along with the original four:
//   /admin/attention   — the trailing-30-day counter that the attention spine feeds every session
//   /admin/funnel      — the matched-readers funnel the admin section drew this week
// k6 on this host, Docker on this host — the numbers describe this desktop's single-node
// topology, not production. Read side only: no auth can carry `X-Internal-Token` here.
//
// Run: k6 run scripts/siege-e292.js -e PHASE=baseline|spike|capacity -e ROUTE=health|adminStats|adminTrends|adminFreshness|attention|funnel|all -e TARGET=<origin>
import http from "k6/http";
import { sleep } from "k6";

const TARGET = __ENV.TARGET;
if (!TARGET) {
  throw new Error("pass -e TARGET=<origin>, e.g. the loopback origin your stack answers on");
}
const PHASE = (__ENV.PHASE ?? "baseline").toLowerCase();
const ONLY = (__ENV.ROUTE ?? "all").toLowerCase();

const ROUTES = [
  { name: "health", url: `${TARGET}/api/v1/health` },
  { name: "adminStats", url: `${TARGET}/api/v1/admin/stats` },
  { name: "adminTrends", url: `${TARGET}/api/v1/admin/trends?weeks=12` },
  { name: "adminFreshness", url: `${TARGET}/api/v1/admin/freshness` },
  { name: "attention", url: `${TARGET}/api/v1/admin/attention` },
  { name: "funnel", url: `${TARGET}/api/v1/admin/funnel` },
].filter((route) => ONLY === "all" || route.name.toLowerCase() === ONLY);

const STAGES = {
  baseline: [
    { duration: "15s", target: 10 },
    { duration: "30s", target: 10 },
    { duration: "5s", target: 0 },
  ],
  spike: [
    { duration: "10s", target: 25 },
    { duration: "15s", target: 100 },
    { duration: "30s", target: 100 },
    { duration: "10s", target: 0 },
  ],
  capacity: [
    { duration: "10s", target: 50 },
    { duration: "20s", target: 200 },
    { duration: "30s", target: 200 },
    { duration: "10s", target: 0 },
  ],
};

export const options = {
  scenarios: {
    siege: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: STAGES[PHASE] ?? STAGES.baseline,
      gracefulRampDown: "2s",
    },
  },
};

export default function () {
  const route = ROUTES[__ITER % ROUTES.length];
  http.get(route.url, { tags: { route: route.name }, timeout: "10s" });
  sleep(0.05);
}
