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

  /**
   * The recovery pair, driven through the screens that call it.
   *
   * The happy path needs the token from the reset email, which only the backend's dev
   * transport can see, so the pass through the API lives in `AuthFlowIT`. What is left for a
   * browser to prove is that the screens reach the endpoints at all, that the client refuses
   * what it can refuse locally, and that `RESET_TOKEN_INVALID` arrives as advice rather than
   * as a status code. No `user` fixture: this test wants no account.
   */
  test("the password-recovery screens reach their endpoints", async ({ page }) => {
    const email = uniqueEmail("recover");

    await page.goto("/login");
    await page.getByRole("link", { name: "Forgot your password?" }).click();
    await expect(page).toHaveURL(/\/forgot-password/);

    // `/auth/password/forgot` answers 200 for an address with no account, so the screen can
    // only promise conditionally — inventing a stronger confirmation would undo that.
    await page.getByLabel("Email").fill(email);
    await page.getByRole("button", { name: "Send reset token" }).click();
    await expect(page.getByRole("heading", { name: "Check your email" })).toBeVisible({
      timeout: 20_000,
    });
    await expect(page.getByText(email)).toBeVisible();

    // A link that arrived without its token -- truncated by a mail client, or a token copied
    // out of the message by hand -- still gets a way in rather than a dead end.
    await page.goto("/reset-password");
    await expect(page.getByLabel("Reset token")).toBeVisible();

    // And that way in reaches the API: a token the server does not know comes back as advice.
    await page.getByLabel("Reset token").fill("not-a-real-token");
    await page.getByLabel("New password", { exact: true }).fill("Br4ndNewPassphrase");
    await page.getByLabel("Confirm new password").fill("Br4ndNewPassphrase");
    await page.getByRole("button", { name: "Save new password" }).click();
    await expect(page.locator("[data-sonner-toast]").first()).toContainText("invalid or has expired", {
      timeout: 20_000,
    });

    // A mismatch is refused locally, with no request spent on it.
    await page.goto("/reset-password?token=not-a-real-token");
    await page.getByLabel("New password", { exact: true }).fill("Br4ndNewPassphrase");
    await page.getByLabel("Confirm new password").fill("Br4ndNewPassphras");
    await page.getByRole("button", { name: "Save new password" }).click();
    await expect(page.getByText("Passwords do not match")).toBeVisible();

    // A token the API does not know comes back as what to do next, not as a code.
    await expect(page.getByLabel("Reset token")).toHaveCount(0);
    await page.getByLabel("Confirm new password").fill("Br4ndNewPassphrase");
    await page.getByRole("button", { name: "Save new password" }).click();
    await expect(page.locator("[data-sonner-toast]").first()).toContainText("invalid or has expired", {
      timeout: 20_000,
    });
    // The form is still there to retype into — a rejected attempt must not look like a success.
    await expect(page.getByRole("heading", { name: "Set a new password" })).toBeVisible();
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
    // `/knowledge/sources` is paginated ({items,total,page,size}), not a bare array.
    const sources = await unwrap<{ items: Array<{ id: string; kind: string }>; total: number }>(
      await api.get("/knowledge/sources")
    );
    expect(
      sources.items.some((s) => s.id === up.sourceId),
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

    // The filter panel renders "<n> matching roles" once the query has settled
    // (it shows "Filtering…" while in flight).
    await expect(authedPage.getByText(/\d+\s+matching\s+roles?/)).toBeVisible({ timeout: 25_000 });

    // Submitting the search issues more than one router.replace (q, then page/size),
    // and each one re-renders the list. Waiting for the final URL means the churn is
    // over — otherwise the click can land on an anchor that is being replaced, which
    // silently does nothing.
    await expect(authedPage).toHaveURL(/[?&]q=Agent\b/);
    await expect(authedPage).toHaveURL(/[?&]size=\d+/);

    // Job titles are links to /jobs/{id}; skip any empty anchors (e.g. icon links).
    const jobLinks = authedPage.locator('a[href^="/jobs/"]').filter({ hasText: /\S/ });
    await expect(jobLinks.first()).toBeVisible({ timeout: 25_000 });
    const href = await jobLinks.first().getAttribute("href");
    expect(href, "a search result must link to a job").toMatch(/^\/jobs\/[0-9a-f-]{36}$/);
    const title = (await jobLinks.first().innerText()).trim();

    await Promise.all([
      authedPage.waitForURL(new RegExp(`${href}$`), { timeout: 30_000 }),
      jobLinks.first().click(),
    ]);

    // Asserting the destination heading carries the title we clicked is stronger than
    // "some h1 exists": it proves the card we clicked is the role that opened.
    await expect(authedPage.getByRole("heading", { level: 1, name: title })).toBeVisible({
      timeout: 20_000,
    });
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

    // The card's fields are editable from the board: clicking its title opens the editor the
    // drag handle deliberately is not. Notes and reminders had no writing surface at all
    // before this, so the UI half is what this step is here to prove.
    await authedPage.getByRole("button", { name: job.title }).first().click();
    const editor = authedPage.getByRole("dialog");
    await expect(editor).toBeVisible({ timeout: 20_000 });

    await editor.getByLabel("Notes").fill("recruiter call booked");
    await editor.getByLabel("Reminder").fill("2026-10-05T09:00");
    await editor.getByRole("button", { name: "Save changes" }).click();
    await expect(editor).toBeHidden({ timeout: 20_000 });

    // The board re-reads the row, so what the dialog wrote is what the card now shows.
    await expect(authedPage.getByText("recruiter call booked")).toBeVisible({ timeout: 20_000 });

    // The row answers under `notes` while PATCH accepts `note` — the DTO names really do
    // differ per verb, which is why this read is spelled out rather than inferred.
    const persisted = await unwrap<{ notes: string; reminderAt: string | null }>(
      await api.get(`/applications/${app.id}`)
    );
    expect(persisted.notes).toBe("recruiter call booked");
    expect(persisted.reminderAt, "the reminder must survive the round trip").toBeTruthy();

    // Clearing it is the half a set-only API could not express; the flag is what makes the
    // reminder removable rather than permanent dashboard noise.
    const cleared = await unwrap<{ reminderAt: string | null }>(
      await api.patch(`/applications/${app.id}`, { clearReminderAt: true })
    );
    expect(cleared.reminderAt).toBeNull();
  });

  test("pastes a posting into the tracker through the import dialog", async ({ api, authedPage }) => {
    // The importer is the write half of JD intelligence: the dialog posts once, the backend
    // runs the analyst and lands the job, and the user lands on the new detail page. The
    // seeded corpus is irrelevant here -- the posting is whatever the user brings.
    const posting = [
      "Senior Backend Engineer - Agent Platform",
      "We are hiring a senior backend engineer to build our agent platform.",
      "Requirements: 5+ years of Java or Python, Spring Boot, PostgreSQL, Redis,",
      "Kafka, Kubernetes. Experience with LLM applications is a strong plus.",
      "Responsibilities: design and ship APIs, own the matching pipeline, mentor.",
    ].join("\n");

    await authedPage.goto("/jobs");
    await authedPage.getByRole("button", { name: "Paste a posting" }).click();
    const dialog = authedPage.getByRole("dialog");
    await expect(dialog).toBeVisible({ timeout: 20_000 });

    await dialog.getByLabel("Job posting text").fill(posting);
    await dialog.getByRole("button", { name: "Import" }).click();

    // Success is the navigation: the dialog closes and the app lands on the new job's page.
    await expect(authedPage).toHaveURL(/\/jobs\/[0-9a-fA-F-]{8,}/, { timeout: 30_000 });
    await expect(authedPage.getByRole("heading", { level: 1 })).toBeVisible({ timeout: 20_000 });
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

    // A finalised session deliberately opens on a summary, not the live runner —
    // the runner's <h1> only exists while the session is active.
    await authedPage.goto(`/interviews/${session.id}`);
    await expect(
      authedPage.getByRole("heading", { name: /interview is finished/i })
    ).toBeVisible({ timeout: 20_000 });

    // "Receive feedback" (PRD §35) is the report itself.
    await authedPage.getByRole("link", { name: "Open report" }).click();
    await expect(authedPage).toHaveURL(new RegExp(`/interviews/${session.id}/report$`));
    await expect(authedPage.getByText("Dimension scores")).toBeVisible({ timeout: 20_000 });
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
      await api.get("/activity/runs", { limit: 5 })
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
