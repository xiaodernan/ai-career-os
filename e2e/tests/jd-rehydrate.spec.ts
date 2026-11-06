import { test, expect } from "./fixtures";

/**
 * 71.3's stored read, driven through the screen.
 *
 * `POST /jds` persists the analysis, and the dialog that made it may close before
 * its reader is done reading -- until 71.3 the close threw the whole result away
 * and reopening meant paying a second analyst run for text the service already
 * holds. The claim here is the rehydrate path end to end: close the dialog,
 * reopen it, the analysis comes back from `GET /jds/{id}` -- marked as restored,
 * the paste box refilled -- and the request log shows one POST and the stored
 * read where a second POST would have been.
 */

const POSTING =
  "Senior Backend Engineer. Required: Java, Spring Boot, PostgreSQL, Kubernetes, Kafka. " +
  "Preferred: Redis, gRPC, OpenAPI. Responsibilities: design payment services, mentor engineers.";

test("the closed analysis comes back from the stored row, not a second run", async ({
  authedPage,
}) => {
  const page = authedPage;
  const jdsPosts: string[] = [];
  const jdsStoredReads: string[] = [];
  page.on("request", (req) => {
    const pathname = new URL(req.url()).pathname;
    if (pathname === "/api/v1/jds" && req.method() === "POST") jdsPosts.push("POST");
    if (/\/api\/v1\/jds\/[\w-]+$/.test(pathname) && req.method() === "GET")
      jdsStoredReads.push("GET");
  });

  await page.goto("/jobs");
  await page.getByRole("button", { name: "Analyze a JD" }).click();
  const textarea = page.getByLabel("Job description text");
  await textarea.fill(POSTING);
  await page.getByRole("button", { name: "Analyze", exact: true }).click();

  // The analysis answered: the result card names its source endpoint (jd.structuredOutput).
  await expect(page.getByText("Structured output from /jds")).toBeVisible({ timeout: 30_000 });

  // Close the dialog, then reopen it: an accidental close must not cost a second run.
  await page.keyboard.press("Escape");
  await expect(page.getByText("Structured output from /jds")).toBeHidden();
  await page.getByRole("button", { name: "Analyze a JD" }).click();

  // The stored row came back: the restored note only renders on the rehydrate path
  // (a fresh run hides it, because the mutation that made it is a success).
  await expect(
    page.getByText("Restored from your last analysis", { exact: false })
  ).toBeVisible({ timeout: 15_000 });
  await expect(textarea).toHaveValue(POSTING);

  // And the network says what happened: one POST for the analysis itself, and the
  // stored read where a second POST would have been.
  expect(jdsPosts).toEqual(["POST"]);
  expect(jdsStoredReads).toEqual(["GET"]);
});
