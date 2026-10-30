import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { fill, lookup } from "@/lib/i18n/locale-context";
import { translations, type Locale } from "@/lib/i18n/translations";
import { INTERVIEW_MODES } from "@/lib/interview-modes";
import { sourceKindLabel } from "@/lib/source-kinds";
import { TRACE_KINDS } from "@/lib/trace-kinds";
import {
  healthVerdictWord,
  interviewModeHint,
  interviewModeName,
  jobStatusWord,
  knowledgeSourceStatusWord,
  marketVerdictWord,
  memoryKindWord,
  readinessVerdictWord,
  remoteTypeWord,
  requirementPriorityWord,
  resumeStatusWord,
  runStatusWord,
  runTriggerWord,
  salaryBandWord,
  seniorityWord,
  traceKindWord,
  HEALTH_VERDICTS,
  JOB_STATUSES,
  KNOWLEDGE_SOURCE_STATUSES,
  MARKET_VERDICTS,
  MEMORY_KINDS,
  READINESS_VERDICTS,
  REMOTE_TYPES,
  REQUIREMENT_PRIORITIES,
  RESUME_STATUSES,
  RUN_STATUSES,
  RUN_TRIGGERS,
} from "@/lib/status-words";

/**
 * The enum words a page draws.
 *
 * A status is stored as a wire value and shown as a word. The word used to be assembled
 * at render time -- `titleCase(run.status)` -- so a Chinese reader saw "Completed", and
 * the copy census could not see the word at all because no literal sat in the file.
 *
 * The table is now the only source of the word, and these cases hold both halves of that
 * contract: every value a domain stores has a word in both languages, and a value the
 * domain does not know keeps its English spelling rather than becoming a raw key.
 */

function tFor(locale: Locale) {
  return (key: string, vars?: Record<string, string | number>): string => {
    const raw = lookup(translations[locale], key);
    return raw == null ? key : fill(raw, vars);
  };
}

const LOCALES: Locale[] = ["en", "zh"];

const ROSTERS: [string, readonly string[]][] = [
  ["activity.runStatus", RUN_STATUSES],
  ["activity.trigger", RUN_TRIGGERS],
  ["jobs.status", JOB_STATUSES],
  ["jobs.remoteTypes", REMOTE_TYPES],
  ["resumes.status", RESUME_STATUSES],
  ["monitoring.verdicts", HEALTH_VERDICTS],
  ["growth.verdicts", READINESS_VERDICTS],
  ["offers.verdicts", MARKET_VERDICTS],
  ["jobs.detail.priorities", REQUIREMENT_PRIORITIES],
  ["memory.kinds", MEMORY_KINDS],
  ["knowledge.sources.statuses", KNOWLEDGE_SOURCE_STATUSES],
  ["ai.agentTimeline.kinds", TRACE_KINDS],
];

describe("the enum words", () => {
  it("gives every stored value a word in both languages", () => {
    for (const [prefix, values] of ROSTERS) {
      for (const value of values) {
        for (const locale of LOCALES) {
          const word = lookup(translations[locale], `${prefix}.${value}`);
          expect(word, `${prefix}.${value} is missing from ${locale}`).toBeTruthy();
        }
      }
    }
    // The modes' roster is the picker's own list, so the words are pinned to it rather
    // than to a second copy that could drift when a mode is added.
    for (const mode of INTERVIEW_MODES) {
      for (const key of [`interviews.modeNames.${mode.value}`, `interviews.modeHints.${mode.value}`]) {
        for (const locale of LOCALES) {
          expect(lookup(translations[locale], key), `${key} is missing from ${locale}`).toBeTruthy();
        }
      }
    }
  });

  it("gives the seniority chip a sentence in both languages", () => {
    // The three keys are chosen inside `seniorityWord` by a ternary and a branch, so the
    // used-keys gate's literal `t("…")` scan cannot see them; this list is their census.
    for (const key of [
      "jobs.detail.entryLevel",
      "jobs.detail.experienceYear",
      "jobs.detail.experienceYears",
    ]) {
      for (const locale of LOCALES) {
        expect(lookup(translations[locale], key), `${key} is missing from ${locale}`).toBeTruthy();
      }
    }
  });

  it("keeps an unknown value's English spelling instead of a raw key", () => {
    const zh = tFor("zh");
    // A status the backend adds before this roster does is still readable; a missing
    // table entry degrades to the word the product used before it was translated.
    expect(runStatusWord(zh, "queued")).toBe("Queued");
    expect(runTriggerWord(zh, "eval_run")).toBe("Eval Run");
    expect(jobStatusWord(zh, "archived")).toBe("Archived");
    expect(remoteTypeWord(zh, "distributed")).toBe("Distributed");
    expect(resumeStatusWord(zh, "queued")).toBe("Queued");
    expect(healthVerdictWord(zh, "degraded")).toBe("Degraded");
    expect(readinessVerdictWord(zh, "almost")).toBe("Almost");
    expect(marketVerdictWord(zh, "at_market")).toBe("At Market");
    expect(requirementPriorityWord(zh, "urgent")).toBe("Urgent");
    expect(knowledgeSourceStatusWord(zh, "retired")).toBe("Retired");
    expect(traceKindWord(zh, "token")).toBe("Token");
    expect(memoryKindWord(zh, "secret")).toBe("Secret");
    expect(interviewModeName(zh, "pair_programming")).toBe("Pair Programming");
    expect(interviewModeHint(zh, "pair_programming")).toBe("");
  });

  it("reads the known words in the reader's language", () => {
    const en = tFor("en");
    const zh = tFor("zh");
    expect(runStatusWord(en, "completed")).toBe("Completed");
    expect(runStatusWord(zh, "completed")).toBe("已完成");
    expect(runTriggerWord(zh, "resume_parse")).toBe("简历解析");
    expect(jobStatusWord(zh, "closed")).toBe("已关闭");
    expect(remoteTypeWord(zh, "hybrid")).toBe("混合办公");
    expect(resumeStatusWord(zh, "parsed")).toBe(lookup(translations.zh, "resumes.status.parsed"));
    expect(healthVerdictWord(en, "healthy")).toBe("Healthy");
    expect(healthVerdictWord(zh, "regressed")).toBe("已退化");
    expect(readinessVerdictWord(en, "not_ready")).toBe("Not ready");
    expect(readinessVerdictWord(zh, "not_ready")).toBe("未就绪");
    expect(marketVerdictWord(en, "within_market")).toBe("Within market");
    expect(marketVerdictWord(zh, "below_market")).toBe("低于市场");
    // The requirement badge and the gap badge draw the JD's own priority word.
    expect(requirementPriorityWord(en, "must")).toBe("Must have");
    expect(requirementPriorityWord(zh, "must")).toBe("必备");
    expect(requirementPriorityWord(zh, "should")).toBe("优先考虑");
    expect(requirementPriorityWord(zh, "nice")).toBe("加分项");
    // The knowledge row's badge and the evidence card's kind draw the wire through the table.
    expect(knowledgeSourceStatusWord(en, "ready")).toBe("Ready");
    expect(knowledgeSourceStatusWord(zh, "pending")).toBe("待处理");
    expect(knowledgeSourceStatusWord(zh, "ingesting")).toBe("摄取中");
    expect(knowledgeSourceStatusWord(zh, "ready")).toBe("就绪");
    expect(knowledgeSourceStatusWord(zh, "failed")).toBe("失败");
    expect(sourceKindLabel(en, "interview_feedback")).toBe("Interview feedback");
    expect(sourceKindLabel(zh, "interview_feedback")).toBe("面试反馈");
    // The trace row's kind badge follows the reader's language too.
    expect(traceKindWord(en, "tool_call")).toBe("Tool call");
    expect(traceKindWord(zh, "tool_call")).toBe("工具调用");
    expect(traceKindWord(zh, "final")).toBe("最终");
    // The memory card's kind badge: the six kinds the extractor accepts.
    expect(memoryKindWord(en, "skill")).toBe("Skills");
    expect(memoryKindWord(zh, "skill")).toBe("技能");
    expect(memoryKindWord(zh, "interview")).toBe("面试记录");
    expect(interviewModeName(zh, "system_design")).toBe("系统设计");
    expect(interviewModeHint(zh, "rag")).toBe("检索、分块、重排、引用");
    // The seniority chip: the count keeps its plus, the word follows the reader.
    expect(seniorityWord(en, 0)).toBe("Entry level");
    expect(seniorityWord(en, 1)).toBe("1+ year experience");
    expect(seniorityWord(en, 3)).toBe("3+ years experience");
    expect(seniorityWord(zh, 0)).toBe("入门级");
    expect(seniorityWord(zh, 1)).toBe("1+ 年经验");
    expect(seniorityWord(zh, 3)).toBe("3+ 年经验");
  });

  it("fills a rendered title with the reader's word, not a key", () => {
    const en = tFor("en");
    const zh = tFor("zh");
    expect(
      en("activity.detail.triggerRun", { trigger: runTriggerWord(en, "resume_parse") }),
    ).toBe("Resume parse run");
    expect(
      zh("activity.detail.triggerRun", { trigger: runTriggerWord(zh, "resume_parse") }),
    ).toBe("简历解析运行");
    expect(
      en("interviews.modeReport", { mode: interviewModeName(en, "system_design") }),
    ).toBe("System design interview report");
    expect(zh("interviews.modeReport", { mode: interviewModeName(zh, "system_design") })).toBe(
      "系统设计报告",
    );
    expect(zh("dashboard.resumeReady", { status: resumeStatusWord(zh, "parsed") })).toBe(
      "已结构化 · 所有代理按这一版匹配",
    );
    expect(zh("dashboard.resumeAwaitingParse", { status: resumeStatusWord(zh, "uploaded") })).toBe(
      "已上传 · 结构化档案尚未就绪",
    );
  });
});

/**
 * The sentences that wrap a count.
 *
 * A count sentence is not assembled at render time any more: the table holds one string
 * with the value's holes in it, so each language puts the number where its grammar
 * wants it. These cases pin the word order both ways -- the number at the head of an
 * English clause, and the Chinese sentence that carries the total at its tail.
 */
describe("the count sentences around a value", () => {
  it("are whole sentences in the reader's word order", () => {
    const en = tFor("en");
    const zh = tFor("zh");
    expect(en("growth.skillCounts", { covered: 3, partial: 1, open: 4, expected: 8 })).toBe(
      "3 covered · 1 partial · 4 open of 8 expected skills"
    );
    expect(zh("growth.skillCounts", { covered: 3, partial: 1, open: 4, expected: 8 })).toBe(
      "已覆盖 3 · 部分覆盖 1 · 未覆盖 4，共 8 项预期技能"
    );
    expect(en("monitoring.runsAnalyzed", { count: 12 })).toBe("12 runs analyzed");
    expect(zh("monitoring.runsAnalyzed", { count: 12 })).toBe("已分析 12 次运行");
    expect(en("offers.matchingPostingsIn", { count: 5, location: "Shanghai" })).toBe(
      "5 matching postings in Shanghai."
    );
    expect(zh("offers.matchingPostingsIn", { count: 5, location: "上海" })).toBe(
      "共 5 个匹配职位，位于 上海。"
    );
    expect(en("growth.matchingPostings", { count: 7 })).toBe("7 matched postings");
    expect(zh("growth.matchingPostings", { count: 7 })).toBe("共 7 个匹配职位");
  });
});

const SRC = fileURLToPath(new URL("..", import.meta.url));
const STATUS_WORDS = "lib/status-words.ts";
const FORMAT = "lib/format.ts";

function assembleCalls(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) => f.path !== FORMAT && f.path !== STATUS_WORDS)
    .filter((f) => /titleCase\s*\(/.test(f.text))
    .map((f) => f.path);
}

function sources(): { path: string; text: string }[] {
  const out: { path: string; text: string }[] = [];
  const walk = (dir: string) => {
    for (const entry of readdirSync(dir)) {
      const full = join(dir, entry);
      if (statSync(full).isDirectory()) {
        walk(full);
        continue;
      }
      if (!/\.(ts|tsx)$/.test(entry) || entry.includes(".test.")) continue;
      out.push({
        path: relative(SRC, full).replace(/\\/g, "/"),
        text: readFileSync(full, "utf8"),
      });
    }
  };
  walk(join(SRC, "app"));
  walk(join(SRC, "components"));
  walk(join(SRC, "lib"));
  return out;
}

describe("the words a page assembles at render time", () => {
  it("does not rebuild an English enum word through titleCase", () => {
    const files = sources();
    // The walk is the thing that can quietly stop: a moved directory, a changed suffix.
    expect(files.length, "the scan read no files").toBeGreaterThan(150);
    expect(files.some((f) => f.path.endsWith("app/(app)/dashboard/page.tsx"))).toBe(true);
    expect(files.some((f) => f.path.endsWith("components/jobs/job-card.tsx"))).toBe(true);

    const offenders = assembleCalls(files);
    expect(
      offenders,
      `enum words assembled at render time:\n${offenders.join("\n")}`,
    ).toEqual([]);
  });

  it("would still see a call that came back", () => {
    // A gate that cannot fail is not a gate: the probe is the same shape the call sites
    // had, and it must come back as an offender.
    const probe = [{ path: "app/probe.tsx", text: '{titleCase(run.status)}' }];
    expect(assembleCalls(probe)).toEqual(["app/probe.tsx"]);
    // The definition and the fallback home are not offenders.
    const home = [
      { path: FORMAT, text: "export function titleCase(v) {" },
      { path: STATUS_WORDS, text: "return titleCase(value);" },
      { path: "app/clean.tsx", text: 'const word = t("jobs.status.open");' },
    ];
    expect(assembleCalls(home)).toEqual([]);
  });
});

const JOB_DETAIL = "app/(app)/jobs/[id]/page.tsx";

/**
 * The charge is the field, not the phrase: a surface reading `experienceLevel` is
 * reading words somebody else chose, before the reader's language was known. A comment
 * that names the retired field carries no dot, so it stays out of the list.
 */
function preWordedSeniority(files: { path: string; text: string }[]): string[] {
  return files.filter((f) => /\.experienceLevel\b/.test(f.text)).map((f) => f.path);
}

describe("the seniority chip", () => {
  it("draws the number the API sends through the table", () => {
    const files = sources();
    expect(files.length, "the scan read no files").toBeGreaterThan(150);
    const page = files.find((f) => f.path.endsWith(JOB_DETAIL));
    expect(page, "the job detail page is not in the walk").toBeTruthy();
    // The seam: without this call the chip loses its words entirely, and the unit
    // cases above would still be green.
    expect(page!.text).toContain("seniorityWord(t, job.experienceYears)");
    const offenders = preWordedSeniority(files);
    expect(
      offenders,
      `surfaces reading words the mapper chose:\n${offenders.join("\n")}`,
    ).toEqual([]);
  });

  it("would still see a page that came back to a pre-worded field", () => {
    expect(
      preWordedSeniority([{ path: "app/probe.tsx", text: "{job.experienceLevel}" }]),
    ).toEqual(["app/probe.tsx"]);
    expect(
      preWordedSeniority([{ path: "lib/api/normalize.ts", text: "// no experienceLevel here" }]),
    ).toEqual([]);
  });
});

const VERDICT_SURFACES: [string, string][] = [
  ["app/(app)/monitoring/page.tsx", 'healthVerdictWord(t, data.verdict ?? "unknown")'],
  ["app/(app)/growth/page.tsx", 'readinessVerdictWord(t, readiness.verdict ?? "unknown")'],
  ["app/(app)/offers/page.tsx", 'marketVerdictWord(t, plan.verdict ?? "unknown")'],
];

/**
 * The charge is the spelling, not the file: a surface building the badge's word from the
 * wire value draws English on every reader's page, and no unit case can see a page that
 * stopped calling the seam.
 */
function rawVerdictSurfaces(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) => f.path !== STATUS_WORDS)
    .filter((f) => /\.verdict[\s\S]{0,80}?\.replace\s*\(/.test(f.text))
    .map((f) => f.path);
}

describe("the verdict badges", () => {
  it("draw the wire value through the table", () => {
    const files = sources();
    expect(files.length, "the scan read no files").toBeGreaterThan(150);
    for (const [rel, seam] of VERDICT_SURFACES) {
      const file = files.find((f) => f.path.endsWith(rel));
      expect(file, `${rel} is not in the walk`).toBeTruthy();
      expect(file!.text).toContain(seam);
    }
    // The comparison's per-row detail reads the assessment through the same words.
    expect(files.find((f) => f.path.endsWith("app/(app)/offers/page.tsx"))!.text).toContain(
      "marketVerdictWord(t, row.assessment.verdict)"
    );
    const offenders = rawVerdictSurfaces(files);
    expect(
      offenders,
      `surfaces spelling a wire verdict themselves:\n${offenders.join("\n")}`
    ).toEqual([]);
  });

  it("would still see a surface that spelled the verdict itself", () => {
    expect(
      rawVerdictSurfaces([
        { path: "app/probe.tsx", text: '{(plan.verdict ?? "unknown").replace(/_/g, " ")}' },
      ])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawVerdictSurfaces([{ path: "app/clean.tsx", text: "{marketVerdictWord(t, v)}" }])
    ).toEqual([]);
  });
});

const PRIORITY_SURFACES: [string, string][] = [
  [
    "app/(app)/jobs/[id]/page.tsx",
    'requirementPriorityWord(t, r.priority ?? (r.required ? "must" : "nice"))',
  ],
  ["components/jobs/match-panel.tsx", "requirementPriorityWord(t, g.importance)"],
];

/**
 * The charge is the spelling, not the file: a badge that builds its word from
 * the wire value prints "must have" on a Chinese posting. The gap card's
 * importance is the requirement's own priority word (match.py copies it), so
 * one function serves both surfaces.
 */
function rawPrioritySurfaces(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) => f.path !== STATUS_WORDS)
    .filter((f) => /\.(?:priority|importance)\??\.replace\s*\(/.test(f.text))
    .map((f) => f.path);
}

describe("the requirement priority badges", () => {
  it("draw the wire priority through the table", () => {
    const files = sources();
    expect(files.length, "the scan read no files").toBeGreaterThan(150);
    for (const [rel, seam] of PRIORITY_SURFACES) {
      const file = files.find((f) => f.path.endsWith(rel));
      expect(file, `${rel} is not in the walk`).toBeTruthy();
      expect(file!.text, `${rel} no longer draws its priority through ${seam}`).toContain(seam);
    }
    const offenders = rawPrioritySurfaces(files);
    expect(
      offenders,
      `surfaces spelling a wire priority themselves:\n${offenders.join("\n")}`
    ).toEqual([]);
  });

  it("would still see a surface that spelled the priority itself", () => {
    expect(
      rawPrioritySurfaces([
        { path: "app/probe.tsx", text: '{r.priority?.replace(/_/g, " ")}' },
      ])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawPrioritySurfaces([{ path: "app/clean.tsx", text: "{requirementPriorityWord(t, p)}" }])
    ).toEqual([]);
  });
});

const KIND_SURFACES: [string, string][] = [
  ["app/(app)/knowledge/page.tsx", "sourceKindLabel(t, s.kind)"],
  ["components/ai/evidence-list.tsx", "sourceKindLabel(t, e.source.kind)"],
  ["components/ai/agent-timeline.tsx", "traceKindWord(t, event.kind)"],
  ["components/settings/memory-card.tsx", "memoryKindWord(t, m.kind)"],
];

const STATUS_SURFACES: [string, string][] = [
  ["app/(app)/knowledge/page.tsx", "knowledgeSourceStatusWord(t, s.status)"],
];

/**
 * The charge is the spelling, not the file: a badge that spells a wire kind itself
 * prints "interview feedback" on the knowledge row and "TOOL CALL" on a Chinese
 * trace, even though the table already names both vocabularies.
 */
function rawKindSurfaces(files: { path: string; text: string }[]): string[] {
  return files.filter((f) => /\.kind\s*\.replace\s*\(/.test(f.text)).map((f) => f.path);
}

/**
 * A status text node is a bare value between the open tag's `>` and the element's
 * close. An attribute (`status={r.status}`), a React key, and a wire comparison all
 * sit inside the tag and are not copy.
 */
function rawStatusSurfaces(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) =>
      />[ \t\r\n]*\{[ \t\r\n]*[A-Za-z_$][\w$]*(?:\.[\w$]+)*\.status[ \t\r\n]*\}/.test(f.text)
    )
    .map((f) => f.path);
}

/**
 * A kind text node is a bare value between the open tag's `>` and the element's
 * close. The memory card printed `{m.kind}` and let CSS capitalize it, which draws
 * the wire spelling on every reader's page; a prop (`kind={m.kind}`) is plumbing.
 */
function bareKindSurfaces(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) =>
      />[ \t\r\n]*\{[ \t\r\n]*[A-Za-z_$][\w$]*(?:\.[\w$]+)*\.kind[ \t\r\n]*\}/.test(f.text)
    )
    .map((f) => f.path);
}

describe("the kind and status badges", () => {
  it("draw the wire value through the table", () => {
    const files = sources();
    expect(files.length, "the scan read no files").toBeGreaterThan(150);
    for (const [rel, seam] of [...KIND_SURFACES, ...STATUS_SURFACES]) {
      const file = files.find((f) => f.path.endsWith(rel));
      expect(file, `${rel} is not in the walk`).toBeTruthy();
      expect(file!.text, `${rel} no longer draws its badge through ${seam}`).toContain(seam);
    }
    const kinds = rawKindSurfaces(files);
    expect(kinds, `surfaces spelling a wire kind themselves:\n${kinds.join("\n")}`).toEqual([]);
    const bare = bareKindSurfaces(files);
    expect(bare, `surfaces printing a wire kind:\n${bare.join("\n")}`).toEqual([]);
    const statuses = rawStatusSurfaces(files);
    expect(statuses, `surfaces printing a wire status itself:\n${statuses.join("\n")}`).toEqual([]);
  });

  it("would still see a surface that spelled the value itself", () => {
    expect(
      rawKindSurfaces([{ path: "app/probe.tsx", text: '{e.source.kind.replace(/_/g, " ")}' }])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawStatusSurfaces([{ path: "app/probe.tsx", text: "<Badge>{s.status}</Badge>" }])
    ).toEqual(["app/probe.tsx"]);
    // An attribute, a React key and a wire comparison are not a rendered word.
    expect(
      rawStatusSurfaces([
        {
          path: "app/ok.tsx",
          text: '<StatusPill key={r.status} status={r.status} variant={s.status === "ready" ? "success" : "secondary"} />',
        },
      ])
    ).toEqual([]);
    expect(
      rawKindSurfaces([
        { path: "app/ok.tsx", text: "<Badge>{sourceKindLabel(t, e.source.kind)}</Badge>" },
      ])
    ).toEqual([]);
    expect(
      bareKindSurfaces([{ path: "app/probe.tsx", text: "<Badge>\n{m.kind}\n</Badge>" }])
    ).toEqual(["app/probe.tsx"]);
    expect(
      bareKindSurfaces([
        { path: "app/ok.tsx", text: "<Badge>{memoryKindWord(t, m.kind)}</Badge>" },
      ])
    ).toEqual([]);
    expect(
      bareKindSurfaces([{ path: "app/ok.tsx", text: "<Row kind={m.kind} />" }])
    ).toEqual([]);
  });
});

/**
 * The roster's other half: `extract_and_store` drops a kind outside MEMORY_KINDS
 * before it reaches the database, so the prompt and the browser have to share one
 * set. A kind added to the prompt alone would be stored and drawn as a raw wire
 * word on every reader's page; a kind kept here but removed from the prompt would
 * be a word nothing can produce.
 */
const EXTRACTOR = new URL("../../../ai-service/app/agents/memory.py", import.meta.url);

describe("the memory kinds", () => {
  it("are the set the extractor accepts, not a second list", () => {
    const py = readFileSync(EXTRACTOR, "utf8");
    const declared = py.match(/MEMORY_KINDS\s*=\s*\{([^}]*)\}/);
    expect(declared, "MEMORY_KINDS is not declared in agents/memory.py").toBeTruthy();
    const words = [...declared![1].matchAll(/"([^"]+)"/g)].map((m) => m[1]).sort();
    expect(words.length, "the extractor's roster parsed empty").toBeGreaterThan(0);
    expect([...MEMORY_KINDS].sort()).toEqual(words);
  });
});

const SALARY_SURFACES = [
  "components/jobs/job-card.tsx",
  "app/(app)/jobs/[id]/page.tsx",
  "app/(app)/companies/[id]/page.tsx",
];

/**
 * The charge is the call, not the file: a surface formatting the stored band itself draws
 * a ceiling with no sentence for the reader. Every other call in the tree formats a point
 * estimate (`v, v`), which can never reach the ceiling branch.
 */
function rawBandCalls(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) => f.path !== FORMAT && f.path !== STATUS_WORDS)
    .filter((f) => /formatSalary\s*\(/.test(f.text) && /\.salary(?:Min|Max)\b/.test(f.text))
    .map((f) => f.path);
}

describe("the salary band", () => {
  it("puts the reader's sentence on a ceiling-only band", () => {
    const en = tFor("en");
    const zh = tFor("zh");
    expect(salaryBandWord(en, 40000, 60000, "USD")).toBe("$40k–$60k");
    expect(salaryBandWord(zh, 40000, 60000, "USD")).toBe("$40k–$60k");
    expect(salaryBandWord(en, 50000, null, "USD")).toBe("$50k+");
    expect(salaryBandWord(en, null, 20000, "USD")).toBe("Up to $20k");
    expect(salaryBandWord(zh, null, 20000, "USD")).toBe("最高 $20k");
    expect(salaryBandWord(zh, null, 300000, "CNY")).toBe("最高 30万");
    expect(salaryBandWord(zh, null, null, "USD")).toBeNull();
  });

  it("draws every job's stored band through the table", () => {
    const files = sources();
    expect(files.length, "the scan read no files").toBeGreaterThan(150);
    for (const rel of SALARY_SURFACES) {
      const file = files.find((f) => f.path.endsWith(rel));
      expect(file, `${rel} is not in the walk`).toBeTruthy();
      expect(file!.text).toContain(
        "salaryBandWord(t, job.salaryMin, job.salaryMax, job.salaryCurrency)",
      );
    }
    const offenders = rawBandCalls(files);
    expect(
      offenders,
      `surfaces formatting a stored band without the reader's sentence:\n${offenders.join("\n")}`,
    ).toEqual([]);
  });

  it("would still see a surface that formatted the band itself", () => {
    expect(
      rawBandCalls([
        {
          path: "app/probe.tsx",
          text: "const salary = formatSalary(job.salaryMin, job.salaryMax, job.salaryCurrency);",
        },
      ]),
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawBandCalls([{ path: "app/point.tsx", text: "formatSalary(v, v, currency)" }]),
    ).toEqual([]);
  });
});