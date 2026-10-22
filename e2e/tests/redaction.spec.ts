import { expect, test } from "./fixtures";
import { apiFor, registerUser, unwrap } from "./fixtures";

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

/**
 * The notes and the contacts the reader typed travel with them.
 *
 * The bundle used to carry every table the *engines* read and neither table
 * the reader wrote in -- so their own notes and the people they know were
 * the first things lost when they left. "Your data" that leaves out the two
 * tables a reader typed into is not their data.
 *
 * So the round trip is run for real: a note and a contact are written, the
 * bundle is exported, and the bundle is applied to a *different* account --
 * because a bundle that carries a note and then cannot put it anywhere is
 * a bundle that only carries it in the file.
 */
test("the notes and the contacts the reader typed travel in the bundle", async ({
  api,
  request,
}) => {
  // What the reader wrote down, in their own words.
  await unwrap(
    await api.post("/knowledge/notes", {
      title: "Salary research",
      content: "Hangzhou senior backend, 40-60w total.",
    })
  );
  await unwrap(
    await api.post("/contacts", {
      name: "Li Ming",
      company: "Acme",
      relation: "Mentor",
      notes: "Met at the conference; happy to review my design.",
    })
  );

  // The bundle.
  const bundle = await unwrap<{
    schema_version?: string;
    data?: { notes?: Array<Record<string, unknown>>; contacts?: Array<Record<string, unknown>> };
  }>(await api.post("/data-portability/export", {}));

  const notes = bundle.data?.notes ?? [];
  const contacts = bundle.data?.contacts ?? [];
  expect(notes.length, "the bundle carries no notes at all").toBeGreaterThan(0);
  expect(contacts.length, "the bundle carries no contacts at all").toBeGreaterThan(0);
  expect(
    notes.map((n) => n.content),
    "the bundle does not carry the note's own words"
  ).toContain("Hangzhou senior backend, 40-60w total.");
  expect(contacts.map((c) => c.name), "the bundle does not carry the contact").toContain(
    "Li Ming"
  );

  // And the restore, into an account that has never seen either.
  const other = await registerUser(request);
  const otherApi = apiFor(request, other);

  await unwrap(await otherApi.post("/data-portability/import-apply", { bundle }));

  const restoredNotes = await unwrap<{ items: Array<{ title: string; content: string }> }>(
    await otherApi.get("/knowledge/notes")
  );
  expect(
    restoredNotes.items.map((n) => n.content),
    "the note did not come back"
  ).toContain("Hangzhou senior backend, 40-60w total.");

  const restoredContacts = await unwrap<Array<{ name: string; relation: string }>>(
    await otherApi.get("/contacts")
  );
  expect(
    restoredContacts.map((c) => c.name),
    "the contact did not come back"
  ).toContain("Li Ming");
});

/**
 * The printable document is in the reader's language.
 *
 * The export has two faces: the JSON a machine reads and the document a
 * person reads. The document was written in Chinese and had no other
 * language, so an English reader's "printable document" was a Chinese
 * document -- and the copy census could not see it, because those words are
 * not on a screen at all: they are in a server-side module, in a document.
 *
 * It also left out two sections: the notes the reader typed and the people
 * they know. A section the bundle carries and the document does not is a
 * section the reader cannot read, and the counts still said it was there.
 */
test("the printable document is in the reader's language", async ({ api }) => {
  await unwrap(
    await api.post("/knowledge/notes", {
      title: "Salary research",
      content: "Hangzhou senior backend, 40-60w total.",
    })
  );
  await unwrap(
    await api.post("/contacts", { name: "Li Ming", company: "Acme", relation: "Mentor" })
  );

  const bundle = await unwrap<Record<string, unknown>>(
    await api.post("/data-portability/export", {})
  );

  const english = await unwrap<{ html?: string }>(
    await api.post("/data-portability/render", { bundle, format: "html", locale: "en" })
  );
  const chinese = await unwrap<{ html?: string }>(
    await api.post("/data-portability/render", { bundle, format: "html", locale: "zh" })
  );

  // The document says which language it is in.
  expect(english.html, "the document does not declare its language").toContain(
    '<html lang="en">'
  );
  expect(chinese.html, "the document does not declare its language").toContain(
    '<html lang="zh">'
  );

  // The two tables the reader wrote into are in the document -- in either
  // language, because the sections are the reader's, not the language's.
  for (const html of [english.html ?? "", chinese.html ?? ""]) {
    expect(html, "the document left out the reader's notes").toContain("Salary research");
    expect(html, "the document left out the people they know").toContain("Li Ming");
  }
});

/**
 * The anonymized export forgets the people.
 *
 * There are two ways to leave with your data. The **redaction** drops whole
 * sections; the **anonymized export** keeps the shape and takes the people
 * out of it, and the docs call it "the right-to-be-forgotten surface".
 *
 * It used to forget nobody. It blanked four field names on the profile --
 * `email`, `display_name`, `phone`, `address` -- and the profile has
 * carried none of them for as long as the export has existed. So the button
 * called "Export anonymized" exported the reader's own uuid, the links to
 * their profiles, their resume's plaintext, every answer they gave an
 * interviewer, and (since 1.2.0) the notes they typed and the people they
 * know, with their email.
 *
 * So the test writes a person -- a contact with a name and an address, a
 * note with a salary in it, a resume with a phone number in it -- and asks
 * for the anonymized export, and then looks for those words in the file.
 */
test("the anonymized export carries no people", async ({ api }) => {
  await unwrap(
    await api.post("/contacts", {
      name: "Li Ming",
      email: "liming@example.com",
      company: "Acme",
      relation: "Mentor",
      notes: "My mentor, from the conference.",
    })
  );
  await unwrap(
    await api.post("/knowledge/notes", {
      title: "My salary note",
      content: "I make 50w a year.",
    })
  );
  await unwrap(
    await api.post("/resumes", {
      title: "Li Ming's resume",
      plaintext: "Li Ming, 13800000000, li.ming@example.com",
    })
  );

  const plain = await unwrap<{ data?: Record<string, unknown> }>(
    await api.post("/data-portability/export", {})
  );
  const anonymous = await unwrap<{
    user?: { id?: string | null; anonymized?: boolean };
    manifest?: { counts?: Record<string, number> };
    data?: Record<string, unknown>;
  }>(await api.post("/data-portability/export", { anonymized: true }));

  // The file, as text: the words are what a person would recognise, and a
  // reader looking at the file is the reader the feature is for.
  const text = JSON.stringify(anonymous);
  for (const word of [
    "Li Ming",
    "liming@example.com",
    "13800000000",
    "I make 50w a year.",
    "My mentor, from the conference.",
  ]) {
    expect(text, `the anonymized export still carries "${word}"`).not.toContain(word);
  }

  // The reader's own id, which the profile carries and nobody thinks of as
  // a name.
  expect(anonymous.user?.id ?? null, "the anonymized export carries the reader's id").toBeNull();
  expect(anonymous.user?.anonymized).toBe(true);

  // And the shape is still there: the counts say what the file holds, so
  // the reader can tell an anonymized file from an empty one.
  const counts = anonymous.manifest?.counts;
  expect(counts?.contacts ?? 0, "the anonymized export lost the contact's row").toBe(1);
  expect(counts?.notes ?? 0, "the anonymized export lost the note's row").toBe(1);

  // The plain export still carries the people -- the anonymized one is a
  // choice, and the choice has to be the difference between the two.
  expect(JSON.stringify(plain), "the plain export lost the contact").toContain("Li Ming");
});


/** One row of the knowledge base's own listing. */
interface SourceItem {
  id: string;
  kind: string;
  refId?: string | null;
  title: string;
  status: string;
}

/**
 * Wait for something the product does asynchronously.
 *
 * The ingester chunks and embeds in the background, so the copy of a resume
 * the reader typed shows up a moment after the row does. Waiting for it is
 * not politeness: a test that reads the list once is a test that will fail
 * on a fast machine and pass on a slow one.
 */
async function waitFor<T>(
  probe: () => Promise<T | undefined>,
  what: string,
  timeoutMs = 30_000
): Promise<T> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const value = await probe();
    if (value !== undefined) return value;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`${what} (waited ${timeoutMs}ms)`);
}

/**
 * A resume the reader typed is material the agents can quote.
 *
 * The product says it: "Your resume, projects and notes become a searchable,
 * cited evidence layer". A resume the reader *uploaded* was always in it --
 * there the file is the document, and the document is chunked and embedded.
 * A resume the reader *typed* was a row in the resume list and nowhere else:
 * the copy the product promises was never made, and the delete path was
 * written for a copy that did not exist.
 *
 * So the claim here is not "the endpoint answers" but "the material is
 * there": the knowledge base holds a source for the typed resume, the source
 * points at the resume -- which is what lets a deleted resume take its copy
 * back -- and deleting the resume takes the copy with it.
 */
test("a resume the reader typed becomes material the agents can quote", async ({ api }) => {
  const resume = await unwrap<{ id?: string }>(
    await api.post("/resumes", {
      title: "My typed resume",
      plaintext: "Li Ming, 13800000000. Led a payments team for eight years.",
    })
  );
  expect(resume.id, "the resume was not created").toBeTruthy();

  const source = await waitFor(
    async () => {
      const page = await unwrap<{ items?: SourceItem[] }>(
        await api.get("/knowledge/sources", { size: 20 })
      );
      return (page.items ?? []).find((s) => s.kind === "resume" && s.refId === resume.id);
    },
    "the typed resume never became a source the agents can quote"
  );

  expect(source.title, "the source does not carry the resume's title").toBe("My typed resume");

  // And deleting the resume takes the copy back: the copy is retired, so the
  // assistant stops quoting a resume the reader can no longer see.
  const deleted = await api.delete(`/resumes/${resume.id}`);
  expect(deleted.status(), "the resume was not deleted").toBeLessThan(300);
  const after = await unwrap<{ items?: SourceItem[] }>(
    await api.get("/knowledge/sources", { size: 20 })
  );
  expect(
    (after.items ?? []).some((s) => s.refId === resume.id),
    "the deleted resume's copy is still in the knowledge base"
  ).toBe(false);
});
