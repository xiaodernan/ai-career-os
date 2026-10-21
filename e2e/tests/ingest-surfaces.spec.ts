import { expect, test } from "./fixtures";
import { unwrap } from "./fixtures";

/**
 * The three surfaces the golden journey reaches only through the API.
 *
 * The suite so far drives the copilot, the growth report, the offers
 * form, the ingestion screen, the company brief and the portability round
 * trip -- the ones a reader reaches for by typing something into a form.
 * Three were left: the knowledge base's own uploader, the resume
 * dropzone, and the interview runner.
 *
 * They are the three that *take a file or an answer*, and a file and an
 * answer are the two things a browser cannot fake. A form that posts a
 * string is a form; a form that reads a file is a form that has to work
 * with the file the reader actually chose. So these drive the real file
 * input and the real answer box, and then check the thing the reader
 * came for: the document in the knowledge base, the resume in the list,
 * and the evaluation of the answer.
 *
 * The claim in each is the same shape, and it is the shape the whole
 * suite is built on: the thing the backend computed is the thing on the
 * screen. A source that reached "ready" on the server and "pending" on the
 * screen is a source nobody can cite, and the row that says "ready" is
 * the row the reader believes.
 */

/** A resume body rich enough to produce real parsed structure. */
const RESUME_TEXT = [
  "李明 高级后端工程师 8年经验",
  "技能: Java, Spring Boot, PostgreSQL, Redis, Kafka, Docker, Kubernetes, Python, REST, 微服务",
  "经历: 2021-2026 星海智能 后端技术专家 负责支付网关与 Agent 平台后端",
  "教育: 清华大学 计算机科学与技术 本科",
].join("\n");

/** A document for the knowledge base -- a note a reader would keep. */
const NOTE_TEXT = [
  "薪资调研：杭州高级后端 40-60w 总包。",
  "强项：支付网关重构、消息一致性、团队带教。",
].join("\n");

/** A score the engine answers in 0..1, as a percentage. */
function asPercent(value: number): number {
  return value <= 1 ? Math.round(value * 100) : Math.round(value);
}

test("a document chosen in the browser is ingested and citable", async ({
  api,
  authedPage,
}) => {
  const title = `E2E source ${Date.now().toString(36)}`;

  await authedPage.goto("/knowledge");

  // The title first, because the upload starts the moment the file is
  // chosen -- the title applies to the batch, and a reader types it
  // before they pick the file, exactly as here.
  await authedPage.locator("#kb-title").fill(title);

  // The file input the button opens -- the same element, addressed
  // directly, because a file dialog cannot be driven and the input can.
  await authedPage.locator("#kb-file").setInputFiles({
    name: "e2e-source.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(NOTE_TEXT, "utf8"),
  });

  // The row settles. "ready" is the word the panel shows when the
  // chunks are parsed, embedded and indexed -- not when the bytes were
  // stored, which is the receipt rather than the outcome.
  await expect(
    authedPage.getByText("ready", { exact: true }),
    "the source never reached ready on the screen"
  ).toBeVisible({ timeout: 60_000 });

  // And the server agrees: the source is in the knowledge base, and it is
  // ready there too.
  const sources = await unwrap<{
    items: Array<{ id: string; title: string; status: string }>;
    total: number;
  }>(await api.get("/knowledge/sources", { size: 50 }));
  const mine = sources.items.find((s) => s.title === title);
  expect(mine, "the source is not in the knowledge base").toBeTruthy();
  expect(mine!.status, "the source is not ready on the server").toBe("ready");

  // And it is on the screen, in the list beside the uploader -- the list
  // polls while anything is ingesting, so a source that arrived is
  // visible without a reload.
  await expect(
    authedPage.getByText(title).first(),
    "the source is not on the knowledge page"
  ).toBeVisible({ timeout: 30_000 });
});

test("a resume chosen in the browser is parsed and lands in the list", async ({
  api,
  authedPage,
}) => {
  await authedPage.goto("/resumes");

  // The dropzone's own file input. The dropzone is a button that opens a
  // file dialog; the input inside it is what actually carries the file,
  // and a browser test cannot open a dialog -- so the input is addressed
  // directly, which is the same path the dialog would take.
  const fileInput = authedPage.locator('input[type="file"]').first();
  await fileInput.setInputFiles({
    name: "e2e-dropzone.txt",
    mimeType: "text/plain",
    buffer: Buffer.from(RESUME_TEXT, "utf8"),
  });

  // The upload's receipt is a resume id, and the page goes to that
  // resume's own page -- the reader's next question is "what did it make
  // of my file", and the answer is on that page.
  await expect(
    authedPage,
    "the dropzone never took the reader to the new resume"
  ).toHaveURL(/\/resumes\/[0-9a-fA-F-]{8,}/, { timeout: 60_000 });

  const resumeId = authedPage.url().split("/resumes/")[1];

  // The server has it, and the parser made something of it.
  const parsed = await unwrap<{ skills: number; score: { total: number } }>(
    await api.post(`/resumes/${resumeId}/parse`)
  );
  expect(parsed.skills, "the parser extracted no skills").toBeGreaterThan(0);
  expect(parsed.score.total, "the parser scored nothing").toBeGreaterThan(0);

  // And the list shows it -- the reader's own list, not the API's.
  await authedPage.goto("/resumes");
  await expect(
    authedPage.locator(`a[href="/resumes/${resumeId}"]`).first(),
    "the uploaded resume is not in the list"
  ).toBeVisible({ timeout: 30_000 });
});

test("an answer typed in the browser is evaluated, and the report shows it", async ({
  api,
  authedPage,
}) => {
  // A session to answer in, and one to anchor it on.
  const resume = await unwrap<{ id: string }>(
    await api.post("/resumes", { title: "Answer Resume", plaintext: RESUME_TEXT })
  );
  await unwrap(await api.post(`/resumes/${resume.id}/parse`));
  const jobs = await unwrap<{ items: Array<{ id: string; title: string }> }>(
    await api.get("/jobs", { q: "Agent", size: 1 })
  );
  expect(jobs.items.length, "the seeded corpus must contain Agent roles").toBeGreaterThan(0);

  const session = await unwrap<{ id: string }>(
    await api.post("/interview/sessions", {
      jobId: jobs.items[0].id,
      resumeId: resume.id,
      mode: "technical",
    })
  );
  await unwrap(await api.post(`/interview/sessions/${session.id}/opening`));

  await authedPage.goto(`/interviews/${session.id}`);

  // The answer box, the way a reader finds it.
  const answer = authedPage.getByRole("textbox", { name: "Your answer" });
  await expect(answer).toBeVisible({ timeout: 20_000 });
  const said =
    "我在星海智能主导了支付网关重构：选 PostgreSQL outbox 加 Kafka 幂等消费，牺牲秒级一致性换取 P99 稳定在 50ms，QPS 从 3k 提到 40k。";
  await answer.fill(said);

  // And the button that sends it.
  await authedPage.getByRole("button", { name: "Submit answer" }).click();

  // The evaluation is the answer's own: a score out of a hundred, and
  // the dimensions the evaluator graded.
  await expect(
    authedPage.getByText("Answer evaluation"),
    "the evaluation never reached the screen"
  ).toBeVisible({ timeout: 60_000 });

  // The server's own answer to the same question, so the screen has
  // something to be compared against. The score and the dimensions live on
  // the candidate's turn -- the evaluator's verdict about that turn, not
  // about the session.
  const detail = await unwrap<{
    turns: Array<{
      role: string;
      evaluation?: { score?: number; dims?: Record<string, number> };
    }>;
  }>(await api.get(`/interview/sessions/${session.id}`));
  const turn = detail.turns.find((t) => t.role === "candidate" && t.evaluation);
  expect(turn, "the turn carries no evaluation").toBeTruthy();
  const score = turn!.evaluation!.score;
  const dims = turn!.evaluation!.dims ?? {};
  expect(typeof score, "the turn has no score").toBe("number");

  // The score on the screen is the score the evaluator gave: out of a
  // hundred, and the same hundred.
  await expect(
    authedPage.getByText(`${asPercent(score!)}/100`),
    "the screen's score is not the evaluator's score"
  ).toBeVisible({ timeout: 20_000 });

  // And the dimensions, which is the part a placeholder would pass: the
  // label is the product's own, and the number beside it is the
  // evaluator's.
  for (const [key, value] of Object.entries(dims).slice(0, 3)) {
    const label = key.replace(/_/g, " ");
    await expect(
      authedPage.getByText(new RegExp(`^${label}\\s*:?\\s*${asPercent(value)}$`, "i")).first(),
      `the screen does not carry ${label}'s score`
    ).toBeVisible({ timeout: 20_000 });
  }

  // Finish the session from the screen -- the reader's own button -- and
  // the report is where the reader lands.
  //
  // Which button depends on what the agent proposed. With a follow-up
  // pending the panel offers "Finish early" beside "Next question";
  // without one it offers "Finish & get report" outright. Both end the
  // session, and a reader takes whichever is there.
  const finishEarly = authedPage.getByRole("button", { name: "Finish early" });
  if (await finishEarly.isVisible().catch(() => false)) {
    await finishEarly.click();
  } else {
    await authedPage
      .getByRole("button", { name: "Finish & get report" })
      .first()
      .click();
  }
  await expect(authedPage).toHaveURL(
    new RegExp(`/interviews/${session.id}/report$`),
    { timeout: 60_000 }
  );

  // The report's dimension scores, as the numbers the evaluator gave.
  await expect(
    authedPage.getByText("Dimension scores"),
    "the report has no dimension scores"
  ).toBeVisible({ timeout: 30_000 });

  // The bars carry the score, not a placeholder: each dimension the
  // server graded is a meter, and the meter's value is the evaluator's
  // own number. A report whose bars were all zero would pass a check
  // that only looked for the heading.
  const report = await unwrap<{ evaluation: { dims: Record<string, number> } }>(
    await api.get(`/interview/sessions/${session.id}`)
  );
  const graded = Object.entries(report.evaluation.dims ?? {});
  expect(graded.length, "the report graded no dimensions").toBeGreaterThan(0);

  for (const [key, value] of graded.slice(0, 3)) {
    const label = key.replace(/_/g, " ");
    const meter = authedPage.getByRole("meter", { name: new RegExp(label, "i") }).first();
    await expect(meter, `the report has no bar for ${label}`).toBeVisible({
      timeout: 20_000,
    });
    await expect(meter).toHaveAttribute("aria-valuenow", String(asPercent(value)));
  }
});
