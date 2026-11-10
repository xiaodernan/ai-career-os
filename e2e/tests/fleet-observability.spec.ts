import { test, expect } from "./fixtures";

/**
 * The Spring Cloud surface, watched from the browser (Epics 100/105/108).
 *
 * The monitoring page's two fleet cards read what the backend's discovery client
 * and Resilience4j bridge actually answer -- not a second inventory -- so the page
 * cannot disagree with the routing table. This walk holds that end to end on the
 * live stack: the API's own answer names the registry mode and the services; the
 * screen shows the same badge, the same service names, and the resilience card
 * that reports the bridge's breaker states.
 */

interface Topology {
  registry: string;
  services: Array<{ name: string; instances: Array<unknown> }>;
}

test("the monitoring page names the fleet the backend serves", async ({ api, authedPage }) => {
  const topology = await unwrap<Topology>(await api.get("/system/topology"));
  expect(
    topology.services.length,
    "the discovery client must see at least one service (the engines it routes to)"
  ).toBeGreaterThan(0);
  const serviceNames = topology.services.map((s) => s.name);
  expect(
    serviceNames.some((name) => name.toLowerCase().includes("ai")),
    `the engine the backend routes to must be in the fleet's answer: ${serviceNames}`
  ).toBe(true);

  const resilience = await unwrap<{ breakers?: Array<{ name?: string; state?: string }> }>(
    await api.get("/system/resilience")
  );
  expect(
    resilience.breakers?.length ?? 0,
    "the bridge reports its circuit breakers even when all of them are closed"
  ).toBeGreaterThan(0);

  await authedPage.goto("/monitoring");

  // The topology card: the registry badge is the mode the API just named, and every
  // service row the client answers is on the screen.
  await expect(authedPage.getByText("Service topology")).toBeVisible({ timeout: 30_000 });
  const badge = topology.registry === "eureka" ? "Eureka" : "Configuration list";
  await expect(
    authedPage.getByText(badge, { exact: true }).first(),
    `the badge must name the registry mode the API answered (${topology.registry})`
  ).toBeVisible({ timeout: 20_000 });
  for (const name of serviceNames) {
    await expect(
      authedPage.getByText(name, { exact: true }).first(),
      `${name} is in the fleet the API named but not on the screen`
    ).toBeVisible({ timeout: 20_000 });
  }

  // The resilience card: the bridge's breaker states, served by the same answer.
  await expect(authedPage.getByText("Service resilience")).toBeVisible({ timeout: 20_000 });
});
