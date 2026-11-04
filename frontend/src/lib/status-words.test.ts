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
  followUpPriorityWord,
  healthVerdictWord,
  interviewModeHint,
  interviewModeName,
  jobStatusWord,
  knowledgeSourceStatusWord,
  marketPriorityWord,
  marketVerdictWord,
  memoryKindWord,
  nightlyStatusWord,
  readinessVerdictWord,
  remoteTypeWord,
  requirementPriorityWord,
  resumeStatusWord,
  resumeVersionKindWord,
  runStatusWord,
  runTriggerWord,
  salaryBandWord,
  seniorityWord,
  traceKindWord,
  userRoleWord,
  FOLLOW_UP_PRIORITIES,
  HEALTH_VERDICTS,
  JOB_STATUSES,
  KNOWLEDGE_SOURCE_STATUSES,
  MARKET_PRIORITIES,
  MARKET_VERDICTS,
  MEMORY_KINDS,
  NIGHTLY_STATUSES,
  READINESS_VERDICTS,
  REMOTE_TYPES,
  REQUIREMENT_PRIORITIES,
  RESUME_STATUSES,
  RESUME_VERSION_KINDS,
  RUN_STATUSES,
  RUN_TRIGGERS,
  USER_ROLES,
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
  ["resumes.versionKinds", RESUME_VERSION_KINDS],
  ["monitoring.verdicts", HEALTH_VERDICTS],
  ["growth.verdicts", READINESS_VERDICTS],
  ["offers.verdicts", MARKET_VERDICTS],
  ["jobs.detail.priorities", REQUIREMENT_PRIORITIES],
  ["growthEngines.priorities", MARKET_PRIORITIES],
  ["dashboard.followUpPriorities", FOLLOW_UP_PRIORITIES],
  ["memory.kinds", MEMORY_KINDS],
  ["knowledge.sources.statuses", KNOWLEDGE_SOURCE_STATUSES],
  ["monitoring.nightlyStatuses", NIGHTLY_STATUSES],
  ["ai.agentTimeline.kinds", TRACE_KINDS],
  ["settings.roles", USER_ROLES],
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
    expect(marketPriorityWord(zh, "severe")).toBe("Severe");
    expect(followUpPriorityWord(zh, "someday")).toBe("Someday");
    // `users.role` is the schema's pair; a role a later deployment adds still reads.
    expect(userRoleWord(zh, "owner")).toBe("Owner");
    // `resume_versions.kind` is the schema's pair too; a kind a later migration adds still reads.
    expect(resumeVersionKindWord(zh, "imported")).toBe("Imported");
    // `retired` and `indexing` reached the table in this unit; a status the ingest has
    // never written is what this case still has to degrade.
    expect(knowledgeSourceStatusWord(zh, "archiving")).toBe("Archiving");
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
    // The same field name carries two other bands, and each has its own words:
    // the ranked gap's market tier, and a follow-up's cadence bucket.
    expect(marketPriorityWord(en, "critical")).toBe("Critical");
    expect(marketPriorityWord(zh, "critical")).toBe("关键");
    expect(marketPriorityWord(zh, "medium")).toBe("中");
    expect(followUpPriorityWord(en, "soon")).toBe("Due soon");
    expect(followUpPriorityWord(zh, "overdue")).toBe("已逾期");
    expect(followUpPriorityWord(zh, "fresh")).toBe("节奏正常");
    // The account badge draws the row's authorization word: the schema's two roles.
    expect(userRoleWord(en, "admin")).toBe("Admin");
    expect(userRoleWord(en, "user")).toBe("User");
    expect(userRoleWord(zh, "admin")).toBe("管理员");
    expect(userRoleWord(zh, "user")).toBe("用户");
    // The version line's origin word: the schema's `kind`, mapped onto the row's `source`.
    expect(resumeVersionKindWord(en, "original")).toBe("Original parse");
    expect(resumeVersionKindWord(zh, "original")).toBe("原始解析");
    expect(resumeVersionKindWord(zh, "tailored")).toBe("定制草稿");
    // The knowledge row's badge and the evidence card's kind draw the wire through the table.
    expect(knowledgeSourceStatusWord(en, "ready")).toBe("Ready");
    expect(knowledgeSourceStatusWord(zh, "pending")).toBe("待处理");
    expect(knowledgeSourceStatusWord(zh, "ingesting")).toBe("摄取中");
    expect(knowledgeSourceStatusWord(zh, "ready")).toBe("就绪");
    expect(knowledgeSourceStatusWord(zh, "failed")).toBe("失败");
    // The two words the `/status` route brings from the documents table, which the
    // source column never used: the ingest's own middle stage and the delete's end.
    expect(knowledgeSourceStatusWord(en, "indexing")).toBe("Indexing");
    expect(knowledgeSourceStatusWord(zh, "indexing")).toBe("索引中");
    expect(knowledgeSourceStatusWord(en, "retired")).toBe("Retired");
    expect(knowledgeSourceStatusWord(zh, "retired")).toBe("已退役");
    // The nightly record's badge kept the runner's own two words in the table's voice.
    expect(nightlyStatusWord(en, "passed")).toBe("Passed");
    expect(nightlyStatusWord(zh, "passed")).toBe("通过");
    expect(nightlyStatusWord(zh, "failed")).toBe("失败");
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
  // The two cards on the match screen: the gap badge and the preparation item.
  ["components/jobs/match-panel.tsx", "requirementPriorityWord(t, g.importance)"],
  ["components/jobs/match-panel.tsx", "requirementPriorityWord(t, item.priority)"],
  // The dashboard's copies of the same two cards the match screen fixed first.
  ["app/(app)/dashboard/page.tsx", "requirementPriorityWord(t, g.importance)"],
  ["app/(app)/dashboard/page.tsx", "followUpPriorityWord(t, f.priority)"],
  // The growth screen's plan item and its two gap lists.
  ["app/(app)/growth/page.tsx", "requirementPriorityWord(t, item.priority)"],
  ["components/growth/growth-engines-panel.tsx", "requirementPriorityWord(t, g.importance)"],
  // The ranked-gap row carries the market band, which is a different vocabulary.
  ["components/growth/growth-engines-panel.tsx", 'marketPriorityWord(t, p.priority ?? "")'],
];

/**
 * The charge is the print, not the spelling.
 *
 * `priority` and `importance` are enum-only names in this product: every producer sends
 * one of three closed bands (the JD's word, the market tier, the cadence bucket). The
 * first rule only charged a priority it had seen humanised -- `.replace(/_/g, " ")` --
 * so a badge that printed the bare identifier walked past it and the preparation card
 * guessed the field was free text. The same walk that reads `{s.status}` reads these
 * fields, whatever shape the node has.
 */
function rawPrioritySurfaces(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) => f.path !== STATUS_WORDS)
    .filter(
      (f) =>
        // The humanised spelling anywhere in the file -- a mapper can build the word
        // outside a text node, and the old rule stays as that net.
        /\.(?:priority|importance)\??\.replace\s*\(/.test(f.text) ||
        textNodeBodies(f.text).some((b) => printsEnum(b, "priority") || printsEnum(b, "importance"))
    )
    .map((f) => f.path);
}

/**
 * A chart slice labelled with the wire field itself puts the wire word in the legend:
 * the follow-up chart reduced the rows to `{priority: count}` and handed the key to
 * `label`, so the ring's caption stayed English on a Chinese page.
 */
function rawPriorityLabels(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) => f.path !== STATUS_WORDS)
    .filter((f) => /\blabel:\s*(?:[A-Za-z_$][\w$]*\.)?(?:priority|importance)\b/.test(f.text))
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
    const labels = rawPriorityLabels(files);
    expect(labels, `charts labelling a slice with the wire value:\n${labels.join("\n")}`).toEqual(
      []
    );
  });

  it("would still see a surface that spelled the priority itself", () => {
    expect(
      rawPrioritySurfaces([
        { path: "app/probe.tsx", text: '{r.priority?.replace(/_/g, " ")}' },
      ])
    ).toEqual(["app/probe.tsx"]);
    // The badge that printed the bare identifier: the shape the first rule could not see.
    expect(
      rawPrioritySurfaces([{ path: "app/probe.tsx", text: "<Badge>{item.priority}</Badge>" }])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawPrioritySurfaces([{ path: "app/probe.tsx", text: "<Badge>{g.importance ?? 'gap'}</Badge>" }])
    ).toEqual(["app/probe.tsx"]);
    // A comparison asks about the value and prints something else.
    expect(
      rawPrioritySurfaces([
        { path: "app/clean.tsx", text: '<span>{g.importance === "must" ? "a" : "b"}</span>' },
      ])
    ).toEqual([]);
    expect(
      rawPrioritySurfaces([{ path: "app/clean.tsx", text: "{requirementPriorityWord(t, p)}" }])
    ).toEqual([]);
  });

  it("would still see a legend labelled with the wire key", () => {
    expect(rawPriorityLabels([{ path: "app/probe.tsx", text: "label: priority," }])).toEqual([
      "app/probe.tsx",
    ]);
    expect(rawPriorityLabels([{ path: "app/probe.tsx", text: "label: row.importance," }])).toEqual([
      "app/probe.tsx",
    ]);
    expect(
      rawPriorityLabels([{ path: "app/clean.tsx", text: "label: followUpPriorityWord(t, priority)," }])
    ).toEqual([]);
  });
});

const ROLE_SURFACES: [string, string][] = [
  ["app/(app)/settings/page.tsx", 'userRoleWord(t, user.role?.toLowerCase?.() ?? "user")'],
];

/**
 * The charge is the print of `user.role`, not every `.role`.
 *
 * A contact's `role` in networking and a posting's `role` in a letter are free text --
 * data the user typed or the sender wrote -- and stay off this walk. The account badge
 * is the one surface that prints an authorization word; the field it reads is the one
 * `MeResponse` carries. A bare `role` from the login principal would also pass the
 * roster, which is why the charge is the row's field and not the word.
 */
function rawRoleSurfaces(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) => f.path !== STATUS_WORDS)
    .filter((f) => textNodeBodies(f.text).some((b) => printsEnum(b, "user\\.role")))
    .map((f) => f.path);
}

const SCHEMA_V1 = new URL(
  "../../../backend/src/main/resources/db/migration/V1__init_schema.sql",
  import.meta.url
);

/** The words `users.role`'s own column comment declares: `-- user | admin`. */
function roleWordsInSchema(sql: string): string[] {
  const table = sql.match(/CREATE TABLE users[\s\S]*?\n\s*\);/)?.[0] ?? "";
  const comment = table.match(/^\s*role\s+text[^\n]*?--\s*([a-z_ |]+)$/m)?.[1] ?? "";
  return comment
    .split("|")
    .map((w) => w.trim())
    .filter(Boolean)
    .sort();
}

describe("the account role badge", () => {
  it("draws the row's role through the table", () => {
    const files = sources();
    expect(files.length, "the scan read no files").toBeGreaterThan(150);
    // The charge runs before the seams: a name in this list says which page prints the
    // wire word, and a missing seam only says which call the gate expected.
    const offenders = rawRoleSurfaces(files);
    expect(
      offenders,
      `surfaces printing the account's wire role:\n${offenders.join("\n")}`
    ).toEqual([]);
    for (const [rel, seam] of ROLE_SURFACES) {
      const file = files.find((f) => f.path.endsWith(rel));
      expect(file, `${rel} is not in the walk`).toBeTruthy();
      expect(file!.text, `${rel} no longer draws the badge through ${seam}`).toContain(seam);
    }
  });

  it("would still see a surface that printed the role itself", () => {
    // The pre-fix shape: the field the response never carried, drawn with a CSS
    // capitalization and a fallback that made every account look like the default.
    expect(
      rawRoleSurfaces([
        {
          path: "app/probe.tsx",
          text: '<Badge variant="outline" className="capitalize">{user.role?.toLowerCase?.() ?? "user"}</Badge>',
        },
      ])
    ).toEqual(["app/probe.tsx"]);
    expect(rawRoleSurfaces([{ path: "app/probe.tsx", text: "<Badge>{user.role}</Badge>" }])).toEqual(
      ["app/probe.tsx"]
    );
    // A contact's role and a posting's role are data, not authorization words.
    expect(rawRoleSurfaces([{ path: "app/ok.tsx", text: "<span>{c.role}</span>" }])).toEqual([]);
    expect(
      rawRoleSurfaces([
        { path: "app/ok.tsx", text: "<Badge>{userRoleWord(t, user.role)}</Badge>" },
      ])
    ).toEqual([]);
    // A comparison asks about the role and draws something else.
    expect(
      rawRoleSurfaces([
        { path: "app/ok.tsx", text: '{user.role === "admin" && <Badge>{t("a.admin")}</Badge>}' },
      ])
    ).toEqual([]);
  });

  it("are the words the users table declares", () => {
    const words = roleWordsInSchema(readFileSync(fileURLToPath(SCHEMA_V1), "utf8"));
    expect(words.length, "the schema's role comment parsed empty").toBeGreaterThan(1);
    expect([...USER_ROLES].sort()).toEqual(words);
  });

  it("would still see a schema that declares a third role", () => {
    const planted =
      "CREATE TABLE users (\n  role          text   NOT NULL DEFAULT 'user',        -- user | admin | owner\n);";
    expect(roleWordsInSchema(planted)).toEqual(["admin", "owner", "user"]);
    expect(USER_ROLES).not.toContain("owner");
    // A file with no users table is an empty reading, not a pass dressed as one.
    expect(roleWordsInSchema("CREATE TABLE jobs (id uuid);")).toEqual([]);
  });
});

const VERSION_ORIGIN_SURFACES: [string, string][] = [
  ["app/(app)/resumes/[id]/page.tsx", "resumeVersionKindWord(t, v.source)"],
];

/**
 * The mapper's own line is a carrier too: the page can only draw the origin word while
 * `mapResumeVersions` still fills `source` from the wire's `kind`. A row that stopped
 * carrying it would make the line silently vanish, not print a wrong word.
 */
const VERSION_ORIGIN_MAPS: [string, string][] = [
  ["lib/hooks/resources.ts", 'source: str(v, "kind", "source", "origin")'],
];

/**
 * The charge is the drawn origin word, not every `.source`.
 *
 * `mapResumeVersions` maps `resume_versions.kind` onto the view model's `source`, which
 * is why the kind charges below never saw this line: they spell `.kind`. Evidence rows
 * read a nested document (`e.source?.docTitle`), and a dotted tail is plumbing; a
 * version row's `source` is the schema's two words, and drawing it raw is the charge.
 */
function rawVersionOriginSurfaces(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) => f.path !== STATUS_WORDS)
    .filter((f) => textNodeBodies(f.text).some((b) => printsEnum(b, "[A-Za-z_$][\\w$]*\\.source")))
    .map((f) => f.path);
}

/** The words `resume_versions.kind`'s own column comment declares: `-- original | tailored`. */
function versionKindWordsInSchema(sql: string): string[] {
  const table = sql.match(/CREATE TABLE resume_versions[\s\S]*?\n\s*\);/)?.[0] ?? "";
  const comment = table.match(/^\s*kind\s+text[^\n]*?--\s*([a-z_ |]+)$/m)?.[1] ?? "";
  return comment
    .split("|")
    .map((w) => w.trim())
    .filter(Boolean)
    .sort();
}

describe("the resume version's origin word", () => {
  it("draws the mapped kind through the table", () => {
    const files = sources();
    expect(files.length, "the scan read no files").toBeGreaterThan(150);
    // The charge runs before the seams: a name in this list says which page prints the
    // wire word, and a missing seam only says which call the gate expected.
    const offenders = rawVersionOriginSurfaces(files);
    expect(
      offenders,
      `surfaces printing a version's wire origin:\n${offenders.join("\n")}`
    ).toEqual([]);
    for (const [rel, seam] of VERSION_ORIGIN_SURFACES) {
      const file = files.find((f) => f.path.endsWith(rel));
      expect(file, `${rel} is not in the walk`).toBeTruthy();
      expect(file!.text, `${rel} no longer draws the origin word through ${seam}`).toContain(seam);
    }
    for (const [rel, seam] of VERSION_ORIGIN_MAPS) {
      const file = files.find((f) => f.path.endsWith(rel));
      expect(file, `${rel} is not in the walk`).toBeTruthy();
      expect(file!.text, `${rel} no longer carries the origin through ${seam}`).toContain(seam);
    }
  });

  it("would still see a version line that drew the wire origin", () => {
    // The pre-fix line: the mapper's field, lowercased by the page, inside a template
    // literal. The kind charges spell `.kind`, and the string blanker used to swallow
    // interpolations, so both read past it.
    expect(
      rawVersionOriginSurfaces([
        {
          path: "app/probe.tsx",
          text: '<p>{v.source ? `${v.source.replace(/_/g, " ")} · ` : ""}{v.createdAt}</p>',
        },
      ])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawVersionOriginSurfaces([{ path: "app/probe.tsx", text: "<span>{v.source}</span>" }])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawVersionOriginSurfaces([{ path: "app/probe.tsx", text: "<span>{`${version.source}`}</span>" }])
    ).toEqual(["app/probe.tsx"]);
    // A nested document is not the enum: the card draws the document's own title.
    expect(
      rawVersionOriginSurfaces([{ path: "app/ok.tsx", text: "<span>{e.source?.docTitle}</span>" }])
    ).toEqual([]);
    // ...and the mapped word through the table, or tested for a comparison, is plumbing.
    expect(
      rawVersionOriginSurfaces([
        { path: "app/ok.tsx", text: "<span>{resumeVersionKindWord(t, v.source)}</span>" },
      ])
    ).toEqual([]);
    expect(
      rawVersionOriginSurfaces([
        {
          path: "app/ok.tsx",
          text: '<span>{v.source === "tailored" ? t("a.t") : t("a.o")}</span>',
        },
      ])
    ).toEqual([]);
  });

  it("are the words the resume_versions table declares", () => {
    const words = versionKindWordsInSchema(readFileSync(fileURLToPath(SCHEMA_V1), "utf8"));
    expect(words.length, "the schema's kind comment parsed empty").toBeGreaterThan(1);
    expect([...RESUME_VERSION_KINDS].sort()).toEqual(words);
  });

  it("would still see a schema that declares a third version kind", () => {
    const planted =
      "CREATE TABLE resume_versions (\n  kind        text NOT NULL DEFAULT 'original',  -- original | tailored | imported\n);";
    expect(versionKindWordsInSchema(planted)).toEqual(["imported", "original", "tailored"]);
    expect(RESUME_VERSION_KINDS).not.toContain("imported");
    // A file with no resume_versions table is an empty reading, not a pass dressed as one.
    expect(versionKindWordsInSchema("CREATE TABLE jobs (id uuid);")).toEqual([]);
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
  // The upload panel's own line: the polled value is a status, and the row drew it raw.
  // The `?? "pending"` is the panel's own answer for a poll that has not replied yet.
  ["components/knowledge/source-actions.tsx", 'knowledgeSourceStatusWord(t, status ?? "pending")'],
  // Two copies of the same badge, both of which let CSS speak for the word.
  ["app/(app)/resumes/[id]/page.tsx", "resumeStatusWord(t, status)"],
  ["app/(app)/dashboard/page.tsx", "resumeStatusWord(t, status)"],
  // The nightly record's own badge, whose fall-through arm printed what the runner sent.
  ["components/monitoring/nightly-history.tsx", "nightlyStatusWord(t, row.status)"],
];

/**
 * A label a mapper assembles from a stored kind, rather than a badge that prints it.
 *
 * The run trace's step line falls back to the kind's word when the payload carries no
 * text; the mapper used to return its own English phrase there, and the copy census
 * cannot see it because the phrase sits in a `.ts` module the census does not read.
 */
const LABEL_SURFACES: [string, string][] = [
  ["lib/activity-trace.ts", "traceKindWord(t, kind)"],
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
 * The word every text node draws, read with its nesting.
 *
 * The first rule looked for `{x.status}` between the tag's `>` and the close, which is
 * the shape one page happened to use. Five more surfaces printed the same field in
 * shapes that scan could not reach: a badge whose value is the bare identifier `{status}`
 * -- the field arrived from the hook already named -- a value behind a `??` fallback,
 * where a `[^{}]*` scan stops at the first brace of the call the fallback guards
 * against, the last arm of a chain whose other arms ask the table, and a badge the
 * panel builds one level down inside `.map()`, where the outer node's braces hold the
 * whole subtree and the call-blanking erases it. So the walk keeps going *through* a
 * node it has read instead of jumping past it: every `>` gets its own look.
 */
function textNodeBodies(text: string): string[] {
  const bodies: string[] = [];
  for (let i = 0; i < text.length; i++) {
    if (text[i] !== ">") continue;
    // An arrow's `=>` opens a block of code, not a child list; every plain `{` in a
    // module would read as a rendered expression otherwise.
    if (text[i - 1] === "=") continue;
    let j = i + 1;
    while (j < text.length && /[ \t\r\n]/.test(text[j])) j++;
    if (text[j] !== "{") continue;
    const end = skipBalanced(text, j);
    if (end < 0) continue;
    const body = text.slice(j + 1, end);
    if (/^\s*\/\*[\s\S]*\*\/\s*$/.test(body)) continue; // `{/* a comment */}` renders nothing
    bodies.push(body);
  }
  return bodies;
}

/**
 * Index of the delimiter that closes the one at `open`, past quotes, comments and inner pairs.
 *
 * A comment is not code. The apostrophe in a JSX comment that says "the card's own fields"
 * opens no string, so without this the quote scanner swallows everything up to the next
 * apostrophe in the file, and the comment-only node is read as a live expression.
 */
function skipBalanced(text: string, open: number): number {
  const pairs: Record<string, string> = { "{": "}", "(": ")", "[": "]" };
  const close = pairs[text[open]];
  if (!close) return -1;
  let depth = 0;
  let quote = "";
  for (let i = open; i < text.length; i++) {
    const c = text[i];
    if (quote) {
      if (c === "\\") i++;
      else if (c === quote) quote = "";
      continue;
    }
    if (c === "/" && (text[i + 1] === "/" || text[i + 1] === "*")) {
      const line = text[i + 1] === "/";
      const end = line ? text.indexOf("\n", i) : text.indexOf("*/", i + 2);
      i = end < 0 ? text.length : line ? end : end + 1;
      continue;
    }
    if (c === '"' || c === "'" || c === "`") quote = c;
    else if (c === text[open]) depth++;
    else if (c === close) {
      depth--;
      if (depth === 0) return i;
    }
  }
  return -1;
}

/**
 * What the text node could put on the page, with the plumbing blanked out.
 *
 * Three things are not the field's own spelling: a call that asks the table for the word
 * (`t("…")`, `…Word(t, status)`, `…Short(t, row.status)`) goes whole; a call that asks for
 * something else keeps its name and loses its arguments, because
 * `statusVariant(run.status)` hands the badge a variant and `status.replace(…)` does draw
 * the word; and an open tag's attributes are plumbing (`<StatusPill status={r.status} />`),
 * so the tag is blanked up to its `>` and only its children are read.
 */
function printableResidue(body: string): string {
  const tableCall = /^(t|[A-Za-z_$][\w$]*(Word|Short|Label|Name|Hint))$/;
  const out: string[] = [];
  let ident = "";
  let i = 0;
  while (i < body.length) {
    const c = body[i];
    if (/[A-Za-z_$0-9]/.test(c)) {
      ident += c;
      out.push(c);
      i++;
      continue;
    }
    if (c === "." && /[A-Za-z_$0-9]$/.test(ident)) {
      ident += c;
      out.push(c);
      i++;
      continue;
    }
    if (c === "(") {
      const callee = (ident.match(/[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*$/) ?? [""])[0];
      const isCall = callee !== "";
      const end = skipBalanced(body, i);
      const last = callee.split(".").pop() ?? "";
      if (isCall && tableCall.test(last)) {
        // Drop the callee too: the call's own name is not the field's spelling.
        out.splice(out.length - callee.length, callee.length, " ");
        out.push(" ");
        i = end + 1;
        ident = "";
        continue;
      }
      if (isCall) {
        out.push("()");
        i = end + 1;
        ident = "";
        continue;
      }
      out.push(c);
      ident = "";
      i++;
      continue;
    }
    if (c === "<" && /^[A-Za-z!/]/.test(body[i + 1] ?? "")) {
      let k = i + 1;
      let depth = 0;
      let quote = "";
      for (; k < body.length; k++) {
        const d = body[k];
        if (quote) {
          if (d === "\\") k++;
          else if (d === quote) quote = "";
          continue;
        }
        if (d === '"' || d === "'" || d === "`") quote = d;
        else if (d === "{" || d === "(" || d === "[") depth++;
        else if (d === "}" || d === ")" || d === "]") depth--;
        else if (d === ">" && depth === 0) break;
      }
      out.push(" ");
      i = k + 1;
      ident = "";
      continue;
    }
    if (c === '"' || c === "'") {
      const end = body.indexOf(c, i + 1);
      out.push(" ");
      i = end < 0 ? i + 1 : end + 1;
      ident = "";
      continue;
    }
    // A template literal's prose is not a word the node draws, but each `${…}` is:
    // the metadata line this gate grew up around prints its value inside one, and
    // blanking the whole literal read the interpolation as a string and missed it.
    if (c === "`") {
      let k = i + 1;
      while (k < body.length && body[k] !== "`") {
        if (body[k] === "\\") {
          k += 2;
          continue;
        }
        if (body[k] === "$" && body[k + 1] === "{") {
          const end = skipBalanced(body, k + 1);
          if (end < 0) {
            k = body.length;
            break;
          }
          out.push(printableResidue(body.slice(k + 2, end)));
          k = end + 1;
          continue;
        }
        k++;
      }
      out.push(" ");
      i = k + 1;
      ident = "";
      continue;
    }
    // A comment says nothing about what the node draws: the prose inside it is for the
    // reader of the source, and `status frame` in a docstring is not a rendered word.
    if (c === "/" && (body[i + 1] === "/" || body[i + 1] === "*")) {
      const line = body[i + 1] === "/";
      const end = line ? body.indexOf("\n", i) : body.indexOf("*/", i + 2);
      out.push(" ");
      i = end < 0 ? body.length : line ? end : end + 2;
      ident = "";
      continue;
    }
    if (c !== "}" && c !== ")" && c !== "]") ident = "";
    out.push(c);
    i++;
  }
  return out.join("");
}

/**
 * A value is charged when it is drawn rather than tested.
 *
 * `status === "ready"`, `status && <Badge>` and `status ? a : b` ask about the value and
 * print something else, so they stay plumbing; `{status}`, `(status ?? …)` and
 * `{status.replace(…)}` put the wire spelling on the page. A dotted tail is plumbing too
 * unless it spells the word out: `status.isPending` is the query's own object, while
 * `status.replace(/_/g, " ")` is the stored value with its underscore still in it.
 */
const SPELLING_VERB = /^(replace|toLowerCase|toUpperCase|trim|split|charAt|substring|slice)/;

function printsEnum(body: string, field: string): boolean {
  const residue = printableResidue(body);
  const re = new RegExp(`(^|[^\\w$.])(?:[A-Za-z_$][\\w$]*\\.)*${field}\\b`, "g");
  for (const m of residue.matchAll(re)) {
    const after = residue.slice((m.index ?? 0) + m[0].length).match(/^\s*(\S*)/)?.[1] ?? "";
    if (/^(===|!==|==|!=|<=|>=|&&|=)/.test(after)) continue;
    // `e.source?.docTitle` draws the nested document's title, not the enum; only an
    // optional spelling verb (`status?.replace(…)`) puts the value's own letters out.
    if (after.startsWith("?.")) {
      if (SPELLING_VERB.test(after.slice(2))) return true;
      continue;
    }
    if (after.startsWith("?") && !after.startsWith("??")) continue;
    if (after.startsWith(".") && !SPELLING_VERB.test(after.slice(1))) continue;
    return true;
  }
  return false;
}

function printsStatus(body: string): boolean {
  return printsEnum(body, "status");
}

function rawStatusSurfaces(files: { path: string; text: string }[]): string[] {
  return files
    .filter((f) => f.path !== STATUS_WORDS)
    .filter((f) => textNodeBodies(f.text).some(printsStatus))
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
    // The charge runs before the seams: a name in this list says which page prints the
    // wire word, and a missing seam only says which call the gate expected.
    const statuses = rawStatusSurfaces(files);
    expect(statuses, `surfaces printing a wire status itself:\n${statuses.join("\n")}`).toEqual(
      []
    );
    for (const [rel, seam] of [...KIND_SURFACES, ...STATUS_SURFACES]) {
      const file = files.find((f) => f.path.endsWith(rel));
      expect(file, `${rel} is not in the walk`).toBeTruthy();
      expect(file!.text, `${rel} no longer draws its badge through ${seam}`).toContain(seam);
    }
    for (const [rel, seam] of LABEL_SURFACES) {
      const file = files.find((f) => f.path.endsWith(rel));
      expect(file, `${rel} is not in the walk`).toBeTruthy();
      expect(file!.text, `${rel} no longer draws its step's word through ${seam}`).toContain(seam);
    }
    const kinds = rawKindSurfaces(files);
    expect(kinds, `surfaces spelling a wire kind themselves:\n${kinds.join("\n")}`).toEqual([]);
    const bare = bareKindSurfaces(files);
    expect(bare, `surfaces printing a wire kind:\n${bare.join("\n")}`).toEqual([]);
  });

  it("would still see a surface that spelled the value itself", () => {
    expect(
      rawKindSurfaces([{ path: "app/probe.tsx", text: '{e.source.kind.replace(/_/g, " ")}' }])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawStatusSurfaces([{ path: "app/probe.tsx", text: "<Badge>{s.status}</Badge>" }])
    ).toEqual(["app/probe.tsx"]);
    // The two shapes the old scan could not reach: the identifier the hook named, and
    // the fallback whose own call puts a brace inside the text node.
    expect(
      rawStatusSurfaces([{ path: "app/probe.tsx", text: "<Badge className=\"cap\">{status}</Badge>" }])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawStatusSurfaces([
        {
          path: "app/probe.tsx",
          text: '<span>{failure\n  ? t("a.failed", { reason: failure })\n  : (status ?? t("a.pending"))}</span>',
        },
      ])
    ).toEqual(["app/probe.tsx"]);
    expect(
      rawStatusSurfaces([{ path: "app/probe.tsx", text: "<Badge>{status.replace(/_/g, \" \")}</Badge>" }])
    ).toEqual(["app/probe.tsx"]);
    // ...and the same field drawn through the table, tested for a variant, or kept as a
    // guard, is plumbing.
    expect(
      rawStatusSurfaces([
        { path: "app/ok.tsx", text: "<Badge>{knowledgeSourceStatusWord(t, status)}</Badge>" },
      ])
    ).toEqual([]);
    expect(
      rawStatusSurfaces([
        {
          path: "app/ok.tsx",
          text: '<div>{run.status && <Badge variant={statusVariant(run.status)}>{runStatusWord(t, run.status)}</Badge>}</div>',
        },
      ])
    ).toEqual([]);
    expect(
      rawStatusSurfaces([
        { path: "app/ok.tsx", text: "<span>{stageShort(t, row.status ?? \"\")}</span>" },
      ])
    ).toEqual([]);
    // The third shape is the fall-through arm of a chain whose other arms ask the table:
    // the badge drew "passed" and "failed" from the reader's words and the wire spelling
    // for anything else, which is the same printing right wearing a different shape.
    expect(
      rawStatusSurfaces([
        {
          path: "app/blind.tsx",
          text: '<Badge>{row.status === "passed" ? t("a") : row.status === "failed" ? t("b") : row.status}</Badge>',
        },
      ])
    ).toEqual(["app/blind.tsx"]);
    // ...and so is one level deeper: a panel that builds its rows inside `.map()` keeps
    // the badge under the call's own parentheses, which the scan used to blank whole.
    expect(
      rawStatusSurfaces([
        {
          path: "app/blind.tsx",
          text: '<ul>{rows.map((row) => (\n  <li key={row.id}><Badge>{row.status}</Badge></li>\n))}</ul>',
        },
      ])
    ).toEqual(["app/blind.tsx"]);
    // A JSX comment is prose, and the apostrophe inside it opens no string: the kanban
    // card's own note used to read as a rendered expression because the quote scanner
    // ran on past the comment to the next `'` in the file.
    expect(
      rawStatusSurfaces([
        {
          path: "app/ok.tsx",
          text: "<div>{/* the card's own fields open the editor, so a click is never a move */}</div>",
        },
      ])
    ).toEqual([]);
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

/**
 * Two vocabularies answer one status field.
 *
 * `GET /knowledge/sources/{id}/status` reads `documents.status` whenever the source names
 * a document and `knowledge_sources.status` when it does not (`KnowledgeService.sourceStatus`),
 * so the badge the upload panel draws sees both tables' words through one wire field. The
 * ingest spends most of its life in `indexing`, which only the documents table ever says,
 * and a deleted source's copy answers `retired` -- neither was in the roster, so a Chinese
 * reader watched the panel poll an English word it had no right to print.
 *
 * The scan takes the writes from the two stacks rather than from a list kept here: the
 * knowledge package's own assignments and defaults, the ai-service's `status='…'` clauses
 * and `set_status(…, "…")` calls. A value outside them is this field's honest unknown and
 * keeps its English spelling; a value inside them has to have a word.
 */
const KNOWLEDGE_JAVA = new URL("../../../backend/src/main/java/com/careeros/knowledge", import.meta.url);
const AI_SERVICE = new URL("../../../ai-service/app", import.meta.url);

function javaFilesUnder(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...javaFilesUnder(full));
    else if (entry.endsWith(".java")) out.push(full);
  }
  return out;
}

function pythonFilesUnder(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir)) {
    const full = join(dir, entry);
    if (statSync(full).isDirectory()) out.push(...pythonFilesUnder(full));
    else if (entry.endsWith(".py")) out.push(full);
  }
  return out;
}

function statusesWrittenIn(files: { path: string; text: string }[]): string[] {
  const written = new Set<string>();
  for (const f of files) {
    if (!f.path.endsWith(".java") && !f.path.endsWith(".py")) continue;
    for (const m of f.text.matchAll(/setStatus\(\s*"([a-z_]+)"/g)) written.add(m[1]);
    for (const m of f.text.matchAll(/STATUS_[A-Z_]+\s*=\s*"([a-z_]+)"/g)) written.add(m[1]);
    for (const m of f.text.matchAll(/String status\s*=\s*"([a-z_]+)"/g)) written.add(m[1]);
    for (const m of
      f.text.matchAll(/UPDATE\s+(?:knowledge_sources|documents)\s+SET\s+status\s*=\s*'([a-z_]+)'/g))
      written.add(m[1]);
    for (const m of f.text.matchAll(/set_status\(\s*[A-Za-z_]\w*\s*,\s*"([a-z_]+)"/g)) written.add(m[1]);
  }
  return [...written].sort();
}

function backendStatusWrites(): { path: string; text: string }[] {
  const files: { path: string; text: string }[] = [];
  for (const file of javaFilesUnder(fileURLToPath(KNOWLEDGE_JAVA)))
    files.push({ path: file, text: readFileSync(file, "utf8") });
  for (const file of pythonFilesUnder(fileURLToPath(AI_SERVICE)))
    files.push({ path: file, text: readFileSync(file, "utf8") });
  return files;
}

describe("the knowledge status vocabulary", () => {
  it("covers every status the two stacks write into the field the panel reads", () => {
    const written = statusesWrittenIn(backendStatusWrites());
    expect(written.length, "the write-scan read no status at all").toBeGreaterThan(3);
    const missing = written.filter((s) => !KNOWLEDGE_SOURCE_STATUSES.includes(s as never));
    expect(
      missing,
      `statuses the backends write but the table cannot say: ${missing.join(", ")}`
    ).toEqual([]);
  });

  it("would still see a status the roster has no word for", () => {
    const planted = [
      { path: "app/KnowledgeService.java", text: `private String status = "schematised";` },
      {
        path: "app/documents.py",
        text: `await db.execute("UPDATE documents SET status='schematised' WHERE id=$1")`,
      },
      { path: "app/pipeline.py", text: `await docs_repo.set_status(doc_id, "schematised")` },
      // A write through a named constant is caught at the constant, which is where the
      // spelling lives -- `KnowledgeService` retires its documents that way.
      {
        path: "app/RetiredEvidencePurger.java",
        text: `private static final String STATUS_RETIRED = "schematised";\n doc.setStatus(STATUS_RETIRED);`,
      },
    ];
    expect(statusesWrittenIn(planted)).toEqual(["schematised"]);
    expect(KNOWLEDGE_SOURCE_STATUSES).not.toContain("schematised");
    // The scan reads only the two tables' own writes: an application's status is a
    // different field, and folding it in would charge a word this badge never draws.
    expect(statusesWrittenIn([{ path: "x.py", text: `UPDATE jobs SET status='closed'` }])).toEqual(
      []
    );
  });
});

/**
 * The nightly record says one of two words, and the backend says so in code:
 * `NightlyReportService` refuses a report whose status is neither `passed` nor `failed`,
 * and the two strings are the entity's own constants. The badge's roster is that pair --
 * a third copy of the vocabulary would be the drift this arc keeps paying down.
 */
const NIGHTLY_ENTITY = new URL(
  "../../../backend/src/main/java/com/careeros/report/entity/NightlyReport.java",
  import.meta.url
);

describe("the nightly verdict words", () => {
  it("are the pair the record's own constants declare", () => {
    const src = readFileSync(NIGHTLY_ENTITY, "utf8");
    const declared = [...src.matchAll(/STATUS_([A-Z_]+)\s*=\s*"([a-z_]+)"/g)].map((m) => m[2]).sort();
    expect(declared.length, "NightlyReport declares no status constant").toBeGreaterThan(0);
    expect([...NIGHTLY_STATUSES].sort()).toEqual(declared);
  });
});

/**
 * Two more priority bands, each declared by the engine that emits it.
 *
 * The market tier is `prioritize.py`'s `_priority_label` -- the four words a ranked gap
 * can carry -- and the cadence bucket is `reminders.py`'s `_PRIORITY_ORDER`, which ranks
 * exactly the words `priority_for` returns. The panel and the dashboard drew both raw,
 * so the roster is the engines' own list: a fifth tier added there reddens this case
 * instead of shipping as an English word.
 */
const PRIORITIZE = new URL("../../../ai-service/app/features/prioritize.py", import.meta.url);
const REMINDERS = new URL("../../../ai-service/app/features/reminders.py", import.meta.url);

function marketBandWords(source: string): string[] {
  const body = source.match(/def _priority_label[\s\S]*?(?=\ndef |$)/)?.[0] ?? "";
  return [...body.matchAll(/return "([a-z_]+)"/g)].map((m) => m[1]).sort();
}

function cadenceBuckets(source: string): string[] {
  const order = source.match(/_PRIORITY_ORDER\s*=\s*\{([^}]*)\}/)?.[1] ?? "";
  return [...order.matchAll(/"([a-z_]+)"/g)].map((m) => m[1]).sort();
}

describe("the two priority bands", () => {
  it("are the words their engines return", () => {
    const band = marketBandWords(readFileSync(fileURLToPath(PRIORITIZE), "utf8"));
    expect(band.length, "the band scan read no return").toBeGreaterThan(2);
    expect([...MARKET_PRIORITIES].sort()).toEqual(band);

    const buckets = cadenceBuckets(readFileSync(fileURLToPath(REMINDERS), "utf8"));
    expect(buckets.length, "the cadence scan read no bucket").toBeGreaterThan(2);
    expect([...FOLLOW_UP_PRIORITIES].sort()).toEqual(buckets);
  });

  it("would still see a band the roster has no word for", () => {
    const band = marketBandWords('def _priority_label(importance, share):\n    return "urgent"\n');
    expect(band).toEqual(["urgent"]);
    expect(MARKET_PRIORITIES).not.toContain("urgent");
    const buckets = cadenceBuckets('_PRIORITY_ORDER = {"overdue": 0, "someday": 1}');
    expect(buckets).toEqual(["overdue", "someday"]);
    expect(FOLLOW_UP_PRIORITIES).not.toContain("someday");
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