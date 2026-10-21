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
