import { expect, test } from "./fixtures";
import { unwrap } from "./fixtures";

/**
 * The redaction, driven through the screen.
 *
 * "Redact before sharing" is the last thing a reader does before handing
 * their career to somebody else, and it is the one feature whose failure
 * is invisible: a redaction that quietly does nothing leaves the reader
 * believing their interview transcripts and their salary notes are gone
 * when they are in the file, one click from being sent.
 *
 * So the claim here is not "the button exists" but "the data is gone" --
 * read three ways: the screen's own counts, the bundle the server handed
 * back, and the file the reader would hand over. And the last one is the
 * claim the product owes its own users: a redacted bundle has to still be
 * restorable, because the reader redacted it so that somebody *else*
 * could import it.
 */

/** The bundle, as far as this spec cares about it. */
interface Bundle {
  schema_version?: string;
  manifest?: {
    content_hash?: string;
    counts?: Record<string, number>;
    redacted_sections?: string[];
  };
  data?: Record<string, unknown>;
}

/** The envelope the backend wraps every answer in. */
interface Envelope<T> {
  success: boolean;
  data: T;
  error: { code?: string; message?: string } | null;
}

/** The plan's own shape: a section's worth of write operations. */
interface Plan {
  sections?: Record<string, Array<{ op: string; id?: string }>>;
  op_counts?: { create: number; update: number; delete: number; total: number };
}

test("a section the reader withholds is gone from the bundle, and the bundle still restores", async ({
  api,
  authedPage,
}) => {
  // Something to withhold. An application, so the section that carries it is
  // one the *backend* owns -- the bundle's applications section is written
  // by the bridge, not by the ai-service, and a redaction that missed it
  // would leave the reader's pipeline in the file they are about to share.
  const jobs = await unwrap<{ items: Array<{ id: string; title: string }> }>(
    await api.get("/jobs", { q: "Agent", size: 1 })
  );
  expect(jobs.items.length, "the seeded corpus must contain Agent roles").toBeGreaterThan(0);
  await unwrap(
    await api.post("/applications", {
      jobId: jobs.items[0].id,
      title: jobs.items[0].title,
      status: "applied",
      notes: "withheld from the shared file",
    })
  );

  await authedPage.goto("/data");

  // Export from the screen. The counts are the bundle's own summary, shown
  // as badges -- "applications: 1" is the bundle saying it carries one
  // application, and it is the number a reader would check before sharing.
  const exportedReply = authedPage.waitForResponse(
    (r) =>
      r.url().includes("/data-portability/export") && r.request().method() === "POST"
  );
  await authedPage.getByRole("button", { name: "Export everything" }).click();
  const exported = ((await (await exportedReply).json()) as Envelope<Bundle>).data;

  await expect(
    authedPage.getByText("applications: 1", { exact: true }).first(),
    "the export does not count the application the bundle carries"
  ).toBeVisible({ timeout: 30_000 });

  // Tick the applications section's box and redact.
  await authedPage.getByRole("checkbox", { name: "Applications" }).check();

  const redactedReply = authedPage.waitForResponse(
    (r) =>
      r.url().includes("/data-portability/redact") && r.request().method() === "POST"
  );
  await authedPage.getByRole("button", { name: "Redact selected sections" }).click();
  const redacted = ((await (await redactedReply).json()) as Envelope<Bundle>).data;

  // 1. The section is really gone -- not renamed, not emptied, not moved.
  expect(
    redacted.data,
    "the redacted bundle still carries the applications the reader withheld"
  ).not.toHaveProperty("applications");
  expect(
    redacted.manifest?.redacted_sections,
    "the bundle does not say which section was withheld"
  ).toEqual(["applications"]);

  // 2. The manifest stops claiming the rows the bundle no longer carries.
  //    This is the one a reader sees: the badge under the hash, and the
  //    last line of the printable document. A count that still says
  //    "applications: 1" tells the reader their pipeline is in the file
  //    they are about to hand over -- the opposite of what they asked for.
  expect(
    redacted.manifest?.counts?.applications,
    "the manifest still counts the rows the bundle dropped"
  ).toBe(0);
  await expect(
    authedPage.getByText("applications: 0", { exact: true }).first(),
    "the screen's counts still claim the dropped rows"
  ).toBeVisible({ timeout: 20_000 });
  await expect(
    authedPage.getByText("applications: 1", { exact: true }),
    "the screen's counts still claim the dropped rows"
  ).toHaveCount(0);

  // 3. The hash moved, because the data moved.
  expect(
    redacted.manifest?.content_hash,
    "the content hash was not recomputed over the redacted data"
  ).not.toBe(exported.manifest?.content_hash);

  // 4. And the screen says what it did.
  await expect(
    authedPage.getByText(/Removed so far:/),
    "the screen does not say which sections it removed"
  ).toBeVisible({ timeout: 20_000 });

  // 5. The file the reader would hand over still restores. This is the
  //    product's own sake: the reader redacted the bundle so that somebody
  //    *else* could import it, and a bundle the import path rejects is a
  //    file nobody can use.
  await authedPage.locator("#import-bundle").fill(JSON.stringify(redacted));
  await authedPage.getByRole("button", { name: "Build the plan" }).click();
  await expect(
    authedPage.getByText("Plan", { exact: true }).first(),
    "the redacted bundle cannot be planned: the file the reader would share is unusable"
  ).toBeVisible({ timeout: 30_000 });
});

test("a withheld section does not delete the reader's own rows at the target", async ({
  api,
  authedPage,
}) => {
  const jobs = await unwrap<{ items: Array<{ id: string; title: string }> }>(
    await api.get("/jobs", { q: "Agent", size: 1 })
  );
  expect(jobs.items.length, "the seeded corpus must contain Agent roles").toBeGreaterThan(0);
  await unwrap(
    await api.post("/applications", {
      jobId: jobs.items[0].id,
      title: jobs.items[0].title,
      status: "applied",
      notes: "kept out of the shared file",
    })
  );

  const bundle = await unwrap<Bundle>(await api.post("/data-portability/export", {}));
  const redacted = await unwrap<Bundle>(
    await api.post("/data-portability/redact", { bundle, drop: ["applications"] })
  );

  // The target is an account that already has an application of its own --
  // say the reader is restoring into the account they left, or a colleague
  // is restoring into theirs.
  const existing = { data: { applications: [{ id: "the-target-own-application" }] } };

  const plan = await unwrap<Plan>(
    await api.post("/data-portability/import-plan", { bundle: redacted, existing })
  );

  const deletes = Object.values(plan.sections ?? {})
    .flat()
    .filter((op) => op.op === "delete")
    .map((op) => op.id);

  expect(
    deletes,
    "the plan deletes the target's own applications because the sharer withheld theirs"
  ).not.toContain("the-target-own-application");
});
