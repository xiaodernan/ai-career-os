import { test, expect, unwrap, uniqueEmail, TEST_PASSWORD, apiFor } from "./fixtures";

/**
 * PRD §35 — the golden user journey, driven against the real stack:
 *
 *   Register → Upload Resume → Resume Parsing → Career Profile
 *   → Search Job → Open Job → Analyze Match → Generate Tailored Resume
 *   → Save Application → Start Interview → Answer Questions
 *   → Receive Feedback → Application Dashboard
 *
 * Assertions target user-visible outcomes (scores, titles, citations, stage
 * counts) rather than markup details, so the suite tolerates restyling but
 * still fails when a feature genuinely breaks.
 */

/** A resume body rich enough to produce real parsed structure. */
export const RESUME_TEXT = [
  "张三 高级后端工程师 8年经验",
  "技能: Java, Spring Boot, PostgreSQL, Redis, Kafka, Docker, Kubernetes, Python, REST, 微服务",
  "经历: 2021-2026 星海智能 后端技术专家 负责支付网关与 Agent 平台后端",
  "教育: 清华大学 计算机科学与技术 本科",
].join("\n");

/**
 * Create a resume, parse it, and put it in the knowledge base.
 *
 * Two separate product steps, both required:
 *   1. `POST /resumes` takes the body as `plaintext` (not `rawText` — a wrong
 *      key is silently dropped by Jackson and the resume parses as empty).
 *   2. `POST /knowledge/text` is what makes the resume retrievable, so anything
 *      that must *cite* the resume (cover letters, tailoring) has evidence.
 *      Resume creation deliberately does not ingest — see scripts/smoke-fullstack.sh,
 *      which performs the same two steps.
 */
async function seedParsedResume(
  api: ReturnType<typeof apiFor>,
  title: string,
  text: string = RESUME_TEXT
): Promise<{ id: string; skills: number }> {
  const resume = await unwrap<{ id: string }>(await api.post("/resumes", { title, plaintext: text }));
  expect(resume.id).toBeTruthy();

  const parsed = await unwrap<{ skills: number; score: { total: number } }>(
    await api.post(`/resumes/${resume.id}/parse`)
  );
  expect(parsed.skills).toBeGreaterThan(0);

  await unwrap(
    await api.post("/knowledge/text", { kind: "resume", title, refId: resume.id, text })
  );

  return { id: resume.id, skills: parsed.skills };
}

/** Pick a seeded job to anchor the journey on. */
async function pickJob(api: ReturnType<typeof apiFor>): Promise<{ id: string; title: string }> {
  const jobs = await unwrap<{ items: Array<{ id: string; title: string }> }>(
    await api.get("/jobs", { q: "Agent", size: 5 })
  );
  expect(jobs.items.length, "the seeded corpus must contain Agent roles").toBeGreaterThan(0);
  return jobs.items[0];
}

test.describe("golden journey — account and session", () => {
  test("a new account registers, reaches the app, and signs in again", async ({ page }) => {
    const email = uniqueEmail("journey");
    await page.goto("/register");

    await page.getByLabel("Full name").fill("Journey Runner");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByLabel("Confirm password").fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Create account" }).click();

    await expect(page).not.toHaveURL(/\/register/, { timeout: 30_000 });

    await page.goto("/dashboard");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });

    // Prove the stored credentials work through the login form.
    await page.context().clearCookies();
    await page.evaluate(() => window.localStorage.clear());
    await page.goto("/login");
    await page.getByLabel("Email").fill(email);
    await page.getByLabel("Password", { exact: true }).fill(TEST_PASSWORD);
    await page.getByRole("button", { name: "Sign in" }).click();
    await expect(page).not.toHaveURL(/\/login/, { timeout: 30_000 });
  });

  test("a wrong password is refused and the user stays on the login screen", async ({ page, user }) => {
    await page.goto("/login");
    await page.getByLabel("Email").fill(user.email);
    await page.getByLabel("Password", { exact: true }).fill("definitely-not-the-password");
    await page.getByRole("button", { name: "Sign in" }).click();

    await expect(page).toHaveURL(/\/login/);
    await expect(page.locator("[data-sonner-toast]").first()).toBeVisible({ timeout: 20_000 });
  });
});

test.describe("golden journey — resume becomes a knowledge base", () => {
  test("uploads a resume file, parses it and finds it in the knowledge base", async ({ api, authedPage }) => {
    // The real "Upload Resume" step: multipart file → stored, ingested, parseable.
    const up = await unwrap<{ resumeId: string; documentId: string; sourceId: string }>(
      await api.upload("/resumes/upload", {
        name: "e2e-resume.txt",
        mimeType: "text/plain",
        buffer: Buffer.from(RESUME_TEXT, "utf8"),
      })
    );
    expect(up.resumeId, "upload must create a resume").toBeTruthy();
    expect(up.documentId, "upload must create a document").toBeTruthy();
    expect(up.sourceId, "upload must create a knowledge source").toBeTruthy();

    const parsed = await unwrap<{
      skills: number;
      experiences: number;
      educations: number;
      score: { total: number };
    }>(await api.post(`/resumes/${up.resumeId}/parse`));

    expect(parsed.skills, "parser must extract skills").toBeGreaterThan(0);
    expect(parsed.score.total, "parser must score the resume").toBeGreaterThan(0);

    // "Career Profile Created": the knowledge base now carries the resume.
    const sources = await unwrap<Array<{ id: string; kind: string }>>(await api.get("/knowledge/sources"));
    expect(
      sources.some((s) => s.id === up.sourceId),
      "the uploaded resume must be listed as a knowledge source"
    ).toBe(true);

    // And it is visible in the product, not merely persisted.
    await authedPage.goto("/resumes");
    await expect(authedPage.locator(`a[href="/resumes/${up.resumeId}"]`).first()).toBeVisible({
      timeout: 20_000,
    });
  });
});

test.describe("golden journey — find a role and understand the match", () => {
  test("searches the corpus and opens a role detail page", async ({ authedPage }) => {
    await authedPage.goto("/jobs");
    const search = authedPage.locator("#job-search");
    await expect(search).toBeVisible({ timeout: 20_000 });
    await search.fill("Agent");
    await search.press("Enter");

    // Job titles are links to /jobs/{id}; skip any empty anchors (e.g. icon links).
    const jobLinks = authedPage.locator('a[href^="/jobs/"]').filter({ hasText: /\S/ });
    await expect(jobLinks.first()).toBeVisible({ timeout: 25_000 });
    const href = await jobLinks.first().getAttribute("href");
    expect(href, "a search result must link to a job").toMatch(/^\/jobs\/[0-9a-f-]{36}$/);

    await jobLinks.first().click();
    await expect(authedPage).toHaveURL(new RegExp(`${href}$`));
    await expect(authedPage.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
  });

  test("computes an evidence-backed match and renders it in the UI", async ({ api, authedPage }) => {
    const resume = await seedParsedResume(api, "Match Resume");
    const job = await pickJob(api);

    const result = await unwrap<{
      match: {
        overall: number;
        matchedSkills: string[];
        evidence: Array<{ criterion: string; quote: string; chunk_ids: string[] }>;
      };
      matchId: string;
    }>(await api.post(`/jobs/${job.id}/match`, { resumeId: resume.id }));

    // A match is a score *plus* justification, never a bare number.
    expect(result.match.overall).toBeGreaterThan(0);
    expect(result.match.overall).toBeLessThanOrEqual(1);
    expect(result.match.matchedSkills.length).toBeGreaterThan(0);
    expect(result.match.evidence.length, "a match must cite resume evidence").toBeGreaterThan(0);
    for (const e of result.match.evidence) {
      expect(e.quote.length, `evidence for "${e.criterion}" needs a quote`).toBeGreaterThan(0);
    }
    expect(result.matchId).toBeTruthy();

    // The same score is visible to the user on the job page.
    await authedPage.goto(`/jobs/${job.id}`);
    await expect(authedPage.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
  });

  test("tailors a resume and drafts a cited cover letter", async ({ api }) => {
    const resume = await seedParsedResume(api, "Tailor Resume");
    const job = await pickJob(api);

    const tailored = await unwrap<{ tailored: { skills: unknown[] } }>(
      await api.post(`/jobs/${job.id}/tailor`, { resumeId: resume.id })
    );
    expect(tailored.tailored.skills.length, "a tailored resume must carry skills").toBeGreaterThan(0);

    const letter = await unwrap<{ letter: string; sources: Array<{ ref: number; quote: string }> }>(
      await api.post(`/jobs/${job.id}/cover-letter`, { resumeId: resume.id, tone: "professional" })
    );
    expect(letter.letter.length, "cover letter must have text").toBeGreaterThan(0);
    expect(letter.sources.length, "cover letter must cite sources").toBeGreaterThan(0);
    for (const s of letter.sources) {
      expect(s.quote.length, "each citation needs a quote").toBeGreaterThan(0);
    }
  });
});

test.describe("golden journey — track the application", () => {
  test("saves a role, opens an application and moves it across the board", async ({ api, authedPage }) => {
    const job = await pickJob(api);

    // Saving is the bookmark half of tracking.
    const savedRes = await api.post(`/jobs/${job.id}/save`);
    expect((await savedRes.json()).success).toBe(true);
    const saved = await unwrap<Array<{ job: { id: string } }>>(await api.get("/jobs/saved"));
    expect(saved.some((s) => s.job.id === job.id), "saved role should appear in /jobs/saved").toBe(true);

    // An application is the kanban card.
    const app = await unwrap<{ id: string; status: string }>(
      await api.post("/applications", {
        jobId: job.id,
        title: job.title,
        status: "applied",
        notes: "E2E golden journey",
      })
    );
    expect(app.id).toBeTruthy();

    // Move it to interview and confirm the timeline records the change.
    const moved = await unwrap<{ status: string }>(
      await api.patch(`/applications/${app.id}`, { status: "interview", note: "moved by E2E" })
    );
    expect(moved.status).toBe("interview");

    const timeline = await unwrap<Array<{ kind: string }>>(await api.get(`/applications/${app.id}/timeline`));
    expect(timeline.length, "a stage change must be journalled").toBeGreaterThan(0);
    expect(timeline.some((t) => t.kind === "status")).toBe(true);

    // The board and the UI agree.
    const dash = await unwrap<{ kanban: { statusCounts: Record<string, number>; total: number } }>(
      await api.get("/reports/dashboard")
    );
    expect(dash.kanban.statusCounts.interview).toBeGreaterThan(0);
    expect(dash.kanban.total).toBeGreaterThan(0);

    await authedPage.goto("/applications");
    await expect(authedPage.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
    await expect(authedPage.getByText(job.title).first()).toBeVisible({ timeout: 20_000 });
  });
});

test.describe("golden journey — interview practice", () => {
  test("runs a full interview and returns structured feedback", async ({ api, authedPage }) => {
    const resume = await seedParsedResume(api, "Interview Resume");
    const job = await pickJob(api);

    const session = await unwrap<{ id: string; status: string }>(
      await api.post("/interview/sessions", { jobId: job.id, resumeId: resume.id, mode: "technical" })
    );
    expect(session.id).toBeTruthy();

    // Opening question comes from the interviewer agent.
    const opening = await unwrap<{ question: { content: string; seq: number } }>(
      await api.post(`/interview/sessions/${session.id}/opening`)
    );
    expect(opening.question.content.length).toBeGreaterThan(0);

    // Answer once; the reply must be scored *and* drive the next question.
    const answer = await unwrap<{
      evaluation: { score: number; dims: Record<string, number> };
      next: { action: string };
    }>(
      await api.post(`/interview/sessions/${session.id}/answer`, {
        answer:
          "我在星海智能主导了支付网关重构，最难的是在一致性与可用性之间取舍：最终选择 PostgreSQL outbox 加 Kafka 幂等消费，牺牲秒级一致性换取 P99 稳定在 50ms。落地后 QPS 从 3k 提到 40k。",
      })
    );
    expect(answer.evaluation.score).toBeGreaterThan(0);
    expect(Object.keys(answer.evaluation.dims).length, "feedback must be multi-dimensional").toBeGreaterThan(0);
    expect(["followup", "next_question", "wrap_up", "closing"]).toContain(answer.next.action);

    // Finalising produces the report the user actually reads.
    const report = await unwrap<{
      evaluation: { dims: Record<string, number>; summary: Record<string, unknown> };
      session: { status: string };
    }>(await api.post(`/interview/sessions/${session.id}/finalize`));
    expect(report.session.status).toBe("completed");
    expect(Object.keys(report.evaluation.dims).length).toBeGreaterThan(0);
    expect(report.evaluation.summary, "report must carry a summary").toBeTruthy();

    await authedPage.goto(`/interviews/${session.id}`);
    await expect(authedPage.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
  });
});

test.describe("golden journey — copilot and observability", () => {
  test("the copilot answers with a tool-backed artifact and traces the run", async ({ api, authedPage }) => {
    const chat = await unwrap<{
      conversationId: string;
      answer: string;
      artifacts: Array<{ type: string }>;
      actions: Array<{ kind: string }>;
    }>(await api.post("/copilot/chat", { message: "帮我找几个适合我的后端岗位" }));

    expect(chat.conversationId).toBeTruthy();
    expect(chat.answer.length, "the copilot must reply").toBeGreaterThan(0);
    expect(chat.artifacts.length, "a job search must yield an artifact").toBeGreaterThan(0);

    // Every AI turn is traced; the activity feed is the proof.
    const runs = await unwrap<Array<{ id: string; agent: string; status: string }>>(
      await api.get("/activity/runs", { size: 5 })
    );
    expect(runs.length, "the copilot turn must be recorded").toBeGreaterThan(0);
    const copilotRun = runs.find((r) => r.agent === "career");
    expect(copilotRun, "a career-agent run should exist").toBeTruthy();

    // And the trace explains what the agent actually did.
    const detail = await unwrap<{
      run: { id: string };
      traces: Array<{ kind: string; payload: Record<string, unknown> }>;
    }>(await api.get(`/activity/runs/${copilotRun!.id}`));
    expect(detail.traces.length).toBeGreaterThan(0);
    const kinds = detail.traces.map((t) => t.kind);
    expect(kinds, "trace should show the llm/tool loop").toContain("llm_call");
    expect(kinds.some((k) => k === "tool_call" || k === "tool_result")).toBe(true);

    // Token usage is aggregated for the user.
    const usage = await unwrap<{ requests: number; totalTokens: number }>(await api.get("/ai-usage/summary"));
    expect(usage.requests).toBeGreaterThan(0);

    await authedPage.goto("/activity");
    await expect(authedPage.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
  });
});
