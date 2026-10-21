import { expect, test } from "./fixtures";
import { unwrap } from "./fixtures";

/**
 * The forward bridges' answers reach the screen.
 *
 * The golden journey checks the bridges at the API: the funnel has a stage
 * per pipeline step, the export bundle has a content hash, the health
 * report has a verdict. It then checks that each of those pages renders its
 * heading. A heading is not an answer, though -- a page can show
 * "Analysis" perfectly well while the number the engine computed sits in
 * a variable nobody read.
 *
 * So this drives the surfaces and checks the answer itself: the stage
 * names the funnel returned are the stage names on the page, and the
 * verdict the health report returned is the verdict on the page.
 *
 * It is the same class of bug the export bundle had, one level up: the
 * bridge works, the engine works, and the screen shows nothing. Nothing
 * in the unit tests can see that -- the page's rendering is the browser's
 * job, and the browser's job is the end-to-end suite's.
 */

/**
 * The ladder the funnel walks.
 *
 * Five stages, not the pipeline's seven: `saved` is pre-pipeline interest
 * and is reported separately as `savedCount`, and `rejected` counts as
 * having reached `applied` and no further. The funnel's own definition is
 * the one the screen has to match, and it is the ai-service's
 * `features/analytics.py` `PIPELINE`.
 */
const STAGE_LABELS = ["applied", "oa", "interview", "final round", "offer"];

test("the funnel the API computed is the funnel on the screen", async ({ api, authedPage }) => {
  const funnel = await unwrap<{ pipeline: Array<{ stage: string; count: number }> }>(
    await api.get("/analysis/pipeline-funnel")
  );
  expect(funnel.pipeline.length, "the funnel must have a stage per pipeline step").toBeGreaterThan(0);

  await authedPage.goto("/analysis");

  // Every stage the engine answered with is on the page, spelled the way
  // the page spells it.
  for (const stage of funnel.pipeline.map((s) => s.stage.replace(/_/g, " "))) {
    await expect(
      authedPage.getByText(stage, { exact: true }).first(),
      `${stage} is on the funnel's answer but not on the screen`
    ).toBeVisible({ timeout: 20_000 });
  }

  // And the whole ladder the product names is there, so a page that
  // dropped a stage cannot pass by showing the ones it kept.
  for (const label of STAGE_LABELS) {
    await expect(
      authedPage.getByText(label, { exact: true }).first(),
      `${label} is missing from the funnel on the screen`
    ).toBeVisible({ timeout: 20_000 });
  }
});

test("the health verdict the report computed is the verdict on the screen", async ({
  api,
  authedPage,
}) => {
  const report = await unwrap<{ verdict: string; totalRuns: number }>(
    await api.get("/monitoring/health-report")
  );
  expect(report.verdict, "the health report must carry a verdict").toBeTruthy();

  await authedPage.goto("/monitoring");
  await expect(
    authedPage.getByText(report.verdict, { exact: true }).first(),
    `the report says "${report.verdict}" but the screen does not show it`
  ).toBeVisible({ timeout: 20_000 });
});

test("the pipeline the board draws is the one the applications carry", async ({
  api,
  authedPage,
}) => {
  // One application, applied. The board and the funnel are two readings of
  // the same rows, and a disagreement between them is the kind of bug that
  // only shows up when both are on the screen at once.
  const job = await unwrap<{ items: Array<{ id: string; title: string }> }>(
    await api.get("/jobs", { q: "Agent", size: 1 })
  );
  expect(job.items.length, "the seeded corpus must contain Agent roles").toBeGreaterThan(0);

  const app = await unwrap<{ id: string }>(
    await api.post("/applications", {
      jobId: job.items[0].id,
      title: job.items[0].title,
      status: "applied",
    })
  );
  expect(app.id).toBeTruthy();

  const funnel = await unwrap<{ pipeline: Array<{ stage: string; count: number }> }>(
    await api.get("/analysis/pipeline-funnel")
  );
  const applied = funnel.pipeline.find((s) => s.stage === "applied");
  expect(applied, "the funnel must have an applied stage").toBeTruthy();
  expect(applied!.count, "the application must be counted").toBeGreaterThan(0);

  // The board shows the same rows the funnel counted.
  await authedPage.goto("/applications");
  await expect(
    authedPage.getByText(job.items[0].title).first(),
    "the application is on the board"
  ).toBeVisible({ timeout: 20_000 });
});

/**
 * The growth report, built by the screen.
 *
 * The report is the product's flagship answer -- five engines composed in
 * one call -- and it is the one a reader reaches for by typing a role into
 * a form. The golden journey never drives that form: it calls the route.
 *
 * So this does what a reader does. It names a role, presses the button,
 * and checks that the report the engines answered with is the report on
 * the screen: the role it was built for, the verdict, the coverage, and
 * the salary band the corpus pays.
 */
test("the growth report is built by the screen, from a named role", async ({
  api,
  authedPage,
}) => {
  // A parsed resume is what the report is built from, so the engine has
  // something to measure the role against.
  const seeded = await unwrap<{ id: string }>(
    await api.post("/resumes", {
      title: "Growth Resume",
      plaintext:
        "Backend engineer with six years of Java and Spring. Built payment " +
        "services at scale, cut p99 latency by 40%. Led a team of four.",
    })
  );
  await unwrap(await api.post(`/resumes/${seeded.id}/parse`));

  const role = "Senior Backend Engineer (Java)";
  const report = await unwrap<{
    readiness: { verdict: string; targetRole?: string };
    gap: { targetRole: string; coverage: number };
    salary: { percentiles: Record<string, number>; sampleSize: number };
  }>(await api.post("/growth-report", { targetRole: role }));
  expect(report.gap.targetRole, "the gap engine must name the role it was built for").toBeTruthy();

  await authedPage.goto("/growth");
  // The report's own field, not the per-engine panel's -- the page has two
  // "Target role" inputs, and the report is the one that composes.
  await authedPage.locator("#growth-role").fill(role);
  await authedPage.getByRole("button", { name: "Analyze" }).click();

  // The role the engines were given is the role on the screen.
  await expect(
    authedPage.getByText(report.gap.targetRole).first(),
    "the role the engines answered with is not the role on the screen"
  ).toBeVisible({ timeout: 30_000 });

  // And the verdict and the coverage are there, as the numbers the engine
  // computed rather than as a placeholder.
  await expect(
    authedPage.getByText((report.readiness.verdict ?? "").replace("_", " ")).first(),
    "the verdict is not on the screen"
  ).toBeVisible({ timeout: 30_000 });

  const coverage = Math.round(report.gap.coverage * 100);
  await expect(
    authedPage.getByText(`${coverage}%`).first(),
    `the coverage (${coverage}%) is not on the screen`
  ).toBeVisible({ timeout: 30_000 });

  // The salary band is the corpus's own answer, so it is a real figure --
  // and the screen spells it as a salary, not as the raw number, so the
  // count behind it is the figure that can be compared.
  const sampleSize = report.salary.sampleSize ?? 0;
  expect(sampleSize, "the market band must count its samples").toBeGreaterThan(0);
  await expect(
    authedPage.getByText("Salary band").first(),
    "the market band is not on the screen"
  ).toBeVisible({ timeout: 30_000 });
  await expect(
    authedPage.getByText(new RegExp(`${sampleSize}\\s+matched postings`)).first(),
    `the market band's sample size (${sampleSize}) is not on the screen`
  ).toBeVisible({ timeout: 30_000 });
});

/**
 * The offers workbench, answered by the screen.
 *
 * The twelve-x engines are the ones a reader reaches at the worst moment
 * of a search -- when there is an offer on the table and the question is
 * what it is worth against the market and what to say back. The golden
 * journey calls the routes; this drives the form.
 *
 * Two answers are checked, because they are two different engines: the
 * market's band (what the corpus pays for the role) and the negotiation
 * plan (what to say about the offer on the table).
 */
test("the market band and the negotiation plan come from the screen", async ({
  api,
  authedPage,
}) => {
  const role = "Backend Engineer";
  const offerBase = 400000;

  // The same two answers, from the API, so the screen has something to
  // be compared against.
  const benchmark = await unwrap<{
    sampleSize: number;
    percentiles: Record<string, number>;
    currency?: string;
  }>(await api.post("/offers/salary-benchmark", { role }));
  expect(benchmark.sampleSize, "the market band must count its samples").toBeGreaterThan(0);

  const plan = await unwrap<{ marketMedian?: number; notes?: string[] }>(
    await api.post("/offers/negotiate", { role, offerBase })
  );
  expect(plan, "the negotiation plan must answer").toBeTruthy();

  await authedPage.goto("/offers");
  await authedPage.locator("#offer-role").fill(role);
  await authedPage.locator("#offer-base").fill(String(offerBase));

  // The market's band first.
  await authedPage.getByRole("button", { name: "Benchmark" }).click();
  await expect(
    authedPage.getByText("What the market pays").first(),
    "the market band is not on the screen"
  ).toBeVisible({ timeout: 30_000 });
  await expect(
    authedPage.getByText(new RegExp(`${benchmark.sampleSize}\\s+matching postings`)).first(),
    `the market band's sample size (${benchmark.sampleSize}) is not on the screen`
  ).toBeVisible({ timeout: 30_000 });

  // And then the plan, which is the answer the reader is here for.
  await authedPage.getByRole("button", { name: "Coach me" }).click();
  await expect(
    authedPage.getByText("Negotiation plan").first(),
    "the negotiation plan is not on the screen"
  ).toBeVisible({ timeout: 30_000 });
});

/**
 * The portability round trip, through the screen.
 *
 * Export, paste it back, and see what would change before anything is
 * written -- then write it. The golden journey does the same round trip
 * through the API, which proves the endpoints agree; this proves the
 * screen does, and it is the screen a reader uses when they want to
 * take their data somewhere else.
 */
test("a bundle exported by the screen is planned and applied by the screen", async ({
  api,
  authedPage,
}) => {
  // Something to carry: a note, so the bundle has a section with content.
  await unwrap(
    await api.post("/knowledge/notes", { title: "Portability note", content: "Kept." })
  );

  const bundle = await unwrap<{ manifest: { content_hash: string } }>(
    await api.post("/data-portability/export", {})
  );
  expect(bundle.manifest.content_hash.length, "the bundle must be hashed").toBeGreaterThan(0);

  await authedPage.goto("/data");

  // The screen's own export answers with the same bundle the API did. The
  // hash is the fingerprint -- it covers the data, not the moment -- so the
  // two can be compared, and a screen that exported something else would
  // show a different one.
  await authedPage.getByRole("button", { name: "Export everything" }).click();
  await expect(
    authedPage.getByText(bundle.manifest.content_hash).first(),
    "the screen exported a different bundle than the API did"
  ).toBeVisible({ timeout: 30_000 });

  // Paste the bundle into the restore box and ask what would change.
  await authedPage
    .locator("#import-bundle")
    .fill(JSON.stringify(bundle));
  await authedPage.getByRole("button", { name: "Build the plan" }).click();
  await expect(
    authedPage.getByText("Plan").first(),
    "the import plan is not on the screen"
  ).toBeVisible({ timeout: 30_000 });

  // And then apply it, which is the write.
  await authedPage.getByRole("button", { name: "Apply the restore" }).click();
  await expect(
    authedPage.getByText(/What was written|The restore was applied/).first(),
    "the restore's result is not on the screen"
  ).toBeVisible({ timeout: 30_000 });
});

/**
 * The ingestion screen, fed a feed.
 *
 * The fourteen-x engines are the only ones a reader runs against their
 * own material rather than the corpus -- a feed pasted from somewhere
 * else, parsed, de-duplicated and swept for freshness before anything is
 * written. The golden journey covers the import dialog (one posting, by
 * hand); this covers the feed path, which is the one with the real
 * arithmetic in it.
 */
test("a pasted feed is parsed and planned by the screen", async ({ api, authedPage }) => {
  // A feed with two postings and one duplicate of the first, so the plan
  // has something to say.
  const feed = JSON.stringify({
    jobs: [
      {
        id: "e2e-ingest-1",
        title: "Platform Engineer",
        company: "Acme",
        location: "Shanghai",
        description: "Build the platform. Kubernetes, Go, and a lot of YAML.",
        postedAt: "2026-10-01T00:00:00Z",
      },
      {
        id: "e2e-ingest-2",
        title: "Data Engineer",
        company: "Globex",
        location: "Remote",
        description: "Own the warehouse. Python, dbt, and patience.",
        postedAt: "2026-10-02T00:00:00Z",
      },
      {
        id: "e2e-ingest-1",
        title: "Platform Engineer",
        company: "Acme",
        location: "Shanghai",
        description: "Build the platform. Kubernetes, Go, and a lot of YAML.",
        postedAt: "2026-10-01T00:00:00Z",
      },
    ],
  });

  // The same feed, parsed by the route, so the screen has something to be
  // compared against.
  const parsed = await unwrap<{ postings?: unknown[]; count?: number; format?: string }>(
    await api.post("/jobs/ingest/parse", { feed, source: "board" })
  );
  const parsedCount = parsed.count ?? parsed.postings?.length ?? 0;
  expect(parsedCount, "the feed must parse into postings").toBeGreaterThan(0);

  await authedPage.goto("/ingestion");
  await authedPage.locator("#feed").fill(feed);
  await authedPage.getByRole("button", { name: "Parse" }).click();

  // The parsed postings are on the screen, with the engine's own count.
  await expect(
    authedPage.getByText("Parsed postings").first(),
    "the parsed postings are not on the screen"
  ).toBeVisible({ timeout: 30_000 });
  await expect(
    authedPage.getByText(new RegExp(`${parsedCount}\\s+postings parsed from the feed`)).first(),
    `the parsed count (${parsedCount}) is not on the screen`
  ).toBeVisible({ timeout: 30_000 });

  // And the plan, which is the sweep the ingestion would make.
  await authedPage.getByRole("button", { name: "Build the plan" }).click();
  await expect(
    authedPage.getByText("Ingestion plan").first(),
    "the ingestion plan is not on the screen"
  ).toBeVisible({ timeout: 30_000 });
});

/**
 * The other shape of feed.
 *
 * The ingestion page says it takes "RSS 2.0 / Atom XML, or a board-API
 * JSON payload" and its own placeholder offers both. The XML half was
 * broken: the bridge only ever reached the JSON parser, so an RSS feed --
 * the first thing the copy offers -- failed with a parse error. The
 * engine now detects the shape from the text, and this is the case that
 * says so.
 */
test("an RSS feed is parsed as readily as a board payload", async ({ api, authedPage }) => {
  const xml = `<?xml version="1.0"?><rss version="2.0"><channel><title>Jobs</title>
    <item><title>Platform Engineer</title><link>https://acme.test/jobs/1</link>
    <description>Kubernetes and Go.</description>
    <pubDate>Mon, 01 Oct 2026 00:00:00 GMT</pubDate></item>
    <item><title>Data Engineer</title><link>https://globex.test/jobs/2</link>
    <description>The warehouse. Python and patience.</description>
    <pubDate>Tue, 02 Oct 2026 00:00:00 GMT</pubDate></item>
  </channel></rss>`;

  const parsed = await unwrap<{ count?: number; format?: string }>(
    await api.post("/jobs/ingest/parse", { feed: xml, source: "rss" })
  );
  expect(parsed.format, "the engine must see an RSS feed as one").toBe("rss");
  expect(parsed.count, "the feed must parse into postings").toBe(2);

  await authedPage.goto("/ingestion");
  await authedPage.locator("#feed").fill(xml);
  await authedPage.getByRole("button", { name: "Parse" }).click();
  await expect(
    authedPage.getByText(new RegExp(`${parsed.count}\\s+postings parsed from the feed`)).first(),
    "the parsed count is not on the screen"
  ).toBeVisible({ timeout: 30_000 });
});

/**
 * The outreach draft, written by the screen.
 *
 * Eleven-two is the one engine on this page that is a model call rather
 * than an arithmetic one, and it is the one a reader is most likely to be
 * looking at: a message to a person. The screen is where it is asked for
 * -- the contact's own fields are the request -- so the screen is where it
 * has to be checked.
 */
test("a message to a contact is drafted by the screen", async ({ api, authedPage }) => {
  // A contact to write to.
  const contact = await unwrap<{ id: string; name: string }>(
    await api.post("/contacts", {
      name: "Ada Lovelace",
      role: "Engineering Manager",
      company: "Acme",
      relation: "mentor",
    })
  );
  expect(contact.id, "the contact must exist").toBeTruthy();

  // The same draft, from the route, so the screen has something to be
  // compared against.
  const draft = await unwrap<{ subject?: string; body?: string }>(
    await api.post("/outreach/draft", {
      name: contact.name,
      role: "Engineering Manager",
      company: "Acme",
      purpose: "referral",
    })
  );
  expect(draft.body, "the outreach engine must write a message").toBeTruthy();
  expect(draft.body!.length, "the drafted message is empty").toBeGreaterThan(0);

  await authedPage.goto("/networking");
  await expect(
    authedPage.getByText(contact.name).first(),
    "the contact is not on the screen"
  ).toBeVisible({ timeout: 20_000 });
  // The draft is the contact's own button -- the one that says "Draft".
  // The name opens the editor, so the button is the thing to press.
  await authedPage.getByRole("button", { name: "Draft" }).first().click();

  // The draft the engine wrote is in the page's own box, for the reader
  // to take or leave.
  const drafted = await authedPage
    .getByRole("textbox", { name: "Draft message" })
    .inputValue();
  expect(drafted.length, "the screen's draft is empty").toBeGreaterThan(0);
});

/**
 * The corpus's own read of a company.
 *
 * This one is not a model call and not an arithmetic engine either: it is
 * a question about the seeded corpus -- "what do this company's postings
 * actually ask for" -- and the answer is the company's own rows. The
 * company page asks for it the way a reader does, by pressing the button,
 * and the skills it names are the skills the postings carry.
 */
test("the corpus's read of a company comes from the screen", async ({ api, authedPage }) => {
  // A company from the seeded corpus, so the brief has rows to read.
  const companies = await unwrap<{ items: Array<{ id: string; name: string }> }>(
    await api.get("/companies", { size: 1 })
  );
  expect(companies.items.length, "the seeded corpus must contain companies").toBeGreaterThan(0);
  const company = companies.items[0];

  // The same read, from the route.
  const brief = await unwrap<{ skills?: Array<{ name: string; count: number }> }>(
    await api.post("/companies/brief", { company: company.name })
  );

  await authedPage.goto(`/companies/${company.id}`);
  await authedPage.getByRole("button", { name: "Read the corpus" }).click();

  await expect(
    authedPage.getByText("What the postings say").first(),
    "the brief is not on the screen"
  ).toBeVisible({ timeout: 30_000 });

  // And the skills the engine named are on the screen, spelled the way it
  // spelled them.
  for (const skill of (brief.skills ?? []).slice(0, 3)) {
    await expect(
      authedPage.getByText(skill.name).first(),
      `${skill.name} is on the brief's answer but not on the screen`
    ).toBeVisible({ timeout: 20_000 });
  }
});

/**
 * A turn of the copilot's, in the browser.
 *
 * The golden journey asks the copilot through the API, which is the
 * blocking pair: a request, an answer, a run recorded. The browser does
 * something else -- it posts to the streaming route and reads the turn as
 * SSE frames, with a fallback to the blocking pair if the stream route
 * answers 404. That is the most intricate path in the product: the task
 * bus, the relay, the frame parser on each side, and a client that has to
 * notice a stream is not coming.
 *
 * So the composer is driven, the way a reader drives it, and the answer
 * has to arrive on the screen.
 */
test("the copilot's answer arrives in the browser", async ({ api, authedPage }) => {
  // The browser's own network log, so the claim is about the route and not
  // about the fallback: the client falls back to the blocking pair when the
  // stream cannot be had, and a fallback that always happens looks exactly
  // like a stream that always works.
  const streamed: { url: string; status: number }[] = [];
  const frames: string[] = [];
  // The frames the page itself received.
  //
  // The network log cannot show them: by the time a test reads a response
  // body, the page's own fetch has consumed the stream. So the page's fetch
  // is wrapped, and the clone of the streaming response is read here --
  // which is the same bytes the page saw.
  await authedPage.addInitScript(() => {
    const w = window as unknown as { __sseBodies?: string[]; fetch: typeof fetch };
    w.__sseBodies = [];
    const original = w.fetch;
    w.fetch = async (...args: Parameters<typeof fetch>) => {
      const res = await original(...args);
      const url = String(
        typeof args[0] === "string" ? args[0] : (args[0] as Request | undefined)?.url ?? ""
      );
      if (url.includes("/copilot/chat/stream")) {
        res
          .clone()
          .text()
          .then((body) => w.__sseBodies?.push(body))
          .catch(() => w.__sseBodies?.push(""));
      }
      return res;
    };
  });
  authedPage.on("request", (request) => {
    if (request.url().includes("/copilot/chat")) {
      streamed.push({ url: request.url(), status: 0 });
    }
  });
  authedPage.on("response", (response) => {
    const row = streamed.find((r) => r.url === response.url() && r.status === 0);
    if (row) row.status = response.status();
  });

  await authedPage.goto("/copilot");

  // The composer, filled and sent the way a reader fills and sends it.
  const composer = authedPage.getByRole("textbox", { name: "First message to Copilot" });
  await expect(composer).toBeVisible({ timeout: 20_000 });
  const asked = "Which of my projects best shows ownership?";
  await composer.fill(asked);
  await authedPage.getByRole("button", { name: "Start chat" }).click();

  // The turn runs and finishes. There is no assertion on the pending
  // line: a streamed turn can finish before a watcher looks, and the
  // transcript below is the claim that matters.
  //
  // The wait is a poll, not a sleep: the conversation is created first and
  // the question is its title, so the question is on the screen before the
  // turn has been sent. Waiting for the request is what proves the turn
  // went out the streaming way.
  await expect
    .poll(() => streamed.length, { timeout: 30_000, message: "the browser never asked for the stream" })
    .toBeGreaterThan(0);

  await expect(
    authedPage.getByText(asked).first(),
    "the question never reached the transcript"
  ).toBeVisible({ timeout: 60_000 });

  // The answer is longer than the question and is not the page's own
  // chrome, so a transcript that rendered only the question cannot pass.
  //
  // The wait is a poll, not a sleep, and it is the answer that is waited
  // for. The question is on the screen the moment it is sent -- it is the
  // conversation's title as well as the user's own message -- while the
  // answer streams in afterwards. So reading the transcript as soon as the
  // question is there reads it mid-answer, and the assertion below is
  // looking at a half-written page. It failed about one run in four.
  const transcript = await expect
    .poll(
      async () => (await authedPage.locator("main").first().innerText()).length,
      { timeout: 60_000, message: "the answer never reached the transcript" }
    )
    .toBeGreaterThan(asked.length + 40);

  // And the turn was streamed, not answered by the fallback. This is the
  // claim the whole SSE architecture exists for: the browser gets the turn
  // as it happens. A 403 here means the async dispatch was denied by the
  // security chain, and the screen still looked right because the client
  // fell back.
  expect(
    streamed.some((r) => r.url.includes("/copilot/chat/stream")),
    `the browser did not ask the streaming route: ${JSON.stringify(streamed)}`
  ).toBe(true);
  expect(
    streamed.every((r) => r.status === 0 || r.status === 200),
    `the stream route did not answer 2xx: ${JSON.stringify(streamed)}`
  ).toBe(true);

  // And the frames arrived. A 200 with an empty body is what a denied
  // async dispatch looks like from here: the headers came, and then
  // nothing did. The turn still finished -- the backend runs it and
  // stores it either way -- so the transcript fills in from a refetch and
  // the screen looks perfect. The frames are the only evidence that the
  // answer was *streamed*, which is the thing the whole SSE path is for.
  await expect
    .poll(
      () => authedPage.evaluate(() => (window as unknown as { __sseBodies?: string[] }).__sseBodies?.length ?? 0),
      { timeout: 30_000, message: "the stream carried no frames" }
    )
    .toBeGreaterThan(0);
  frames.push(
    ...(await authedPage.evaluate(
      () => (window as unknown as { __sseBodies?: string[] }).__sseBodies ?? []
    ))
  );
  expect(
    frames.join("\n"),
    "the stream carried no frames: the turn was answered, but not streamed"
  ).toContain("event:");

  // The run is recorded either way, so the activity feed has it.
  const runs = await unwrap<{ items: Array<{ id: string; agent?: string }> }>(
    await api.get("/activity/runs", { size: 20 })
  );
  expect(runs.items.length, "the turn must be recorded").toBeGreaterThan(0);
});
