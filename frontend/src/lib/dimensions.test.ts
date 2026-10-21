import { describe, expect, it } from "vitest";

import {
  INTERVIEW_DIMENSIONS,
  MATCH_DIMENSIONS,
  RESUME_CRITERIA,
  RESUME_DIMENSIONS,
  dimensionLabel,
  interviewDimensionLabel,
  matchDimensionLabel,
  resumeCriterionLabel,
  resumeDimensionLabel,
} from "./dimensions";

/**
 * The dimension names, and the locale that names them.
 *
 * These are the words on the bars: the match panel's four, the interview
 * rubric's eight, the resume reviewer's five, and the rubric's unmet
 * criteria. They used to be English literals in the API mapper and in object
 * literals inside components -- places the copy census cannot read, because
 * it walks the copy-bearing *attributes* and the *text between the tags* of a
 * `.tsx` file and nothing else. A bar labelled "Technical" on a Chinese page
 * is a hole the gate did not know it had.
 *
 * So the vocabulary moved into one module, and this is the gate for it: every
 * key the wire can send has a name, every name has a Chinese one, and a
 * key nobody knows is still shown rather than dropped.
 */

/** A locale that answers the `dimensions.*` keys and nothing else. */
const english: (key: string) => string = (key) => {
  const table: Record<string, string> = {
    "dimensions.match.technical.label": "Technical",
    "dimensions.match.experience.label": "Experience",
    "dimensions.match.projects.label": "Projects",
    "dimensions.match.education.label": "Education",
    "dimensions.interview.technical_accuracy.label": "Technical accuracy",
    "dimensions.interview.communication.label": "Communication",
    "dimensions.interview.depth.label": "Depth",
    "dimensions.interview.structure.label": "Structure",
    "dimensions.interview.problem_solving.label": "Problem solving",
    "dimensions.interview.system_thinking.label": "System thinking",
    "dimensions.interview.ai_knowledge.label": "AI knowledge",
    "dimensions.interview.backend_knowledge.label": "Backend knowledge",
    "dimensions.resume.bullets.label": "Bullets & metric density",
    "dimensions.resume.structure.label": "Structure & scannability",
    "dimensions.resume.impact.label": "Impact wording",
    "dimensions.resume.clarity.label": "Clarity",
    "dimensions.resume.keywords.label": "Keyword coverage",
    "dimensions.criteria.has_contact.label": "Contact info (email / phone)",
    "dimensions.criteria.has_summary.label": "A summary section",
    "dimensions.criteria.has_experience.label": "Work experience",
    "dimensions.criteria.experience_has_bullets.label": "Bullets under your roles",
    "dimensions.criteria.quantified_impact.label": "Quantified impact (numbers or %)",
    "dimensions.criteria.has_projects.label": "Projects",
    "dimensions.criteria.has_education.label": "Education",
    "dimensions.criteria.has_skills.label": "Enough skills (5+)",
    "dimensions.criteria.years_experience_stated.label": "Stated years of experience",
    "dimensions.criteria.dates_present.label": "Start dates on all roles",
  };
  return table[key] ?? key;
};

const chinese: (key: string) => string = (key) => {
  const table: Record<string, string> = {
    "dimensions.match.technical.label": "技术",
    "dimensions.match.experience.label": "经验",
    "dimensions.match.projects.label": "项目",
    "dimensions.match.education.label": "教育",
    "dimensions.interview.technical_accuracy.label": "技术准确度",
    "dimensions.interview.communication.label": "表达",
    "dimensions.interview.depth.label": "深度",
    "dimensions.interview.structure.label": "结构",
    "dimensions.interview.problem_solving.label": "问题解决",
    "dimensions.interview.system_thinking.label": "系统思维",
    "dimensions.interview.ai_knowledge.label": "AI 知识",
    "dimensions.interview.backend_knowledge.label": "后端知识",
    "dimensions.resume.bullets.label": "要点与数据密度",
    "dimensions.resume.structure.label": "结构与可扫描性",
    "dimensions.resume.impact.label": "影响力措辞",
    "dimensions.resume.clarity.label": "清晰度",
    "dimensions.resume.keywords.label": "关键词覆盖",
    "dimensions.criteria.has_contact.label": "联系方式（邮箱 / 电话）",
    "dimensions.criteria.has_summary.label": "个人摘要",
    "dimensions.criteria.has_experience.label": "工作经历",
    "dimensions.criteria.experience_has_bullets.label": "每段经历下的要点",
    "dimensions.criteria.quantified_impact.label": "量化的成果（数字或百分比）",
    "dimensions.criteria.has_projects.label": "项目",
    "dimensions.criteria.has_education.label": "教育背景",
    "dimensions.criteria.has_skills.label": "足够的技能（5 项以上）",
    "dimensions.criteria.years_experience_stated.label": "写明工作年限",
    "dimensions.criteria.dates_present.label": "每段经历都有起始时间",
  };
  return table[key] ?? key;
};

describe("the dimension names", () => {
  it("names every dimension the wire can send", () => {
    // The interview rubric is the ai-service's `DIMENSIONS` in
    // `app/features/interview.py`; the match's four are the columns
    // `compute_match` writes. A key the table does not know is still shown,
    // but it shows in English, so a key that arrives should be named here.
    for (const key of [
      "technical_accuracy",
      "communication",
      "depth",
      "structure",
      "problem_solving",
      "system_thinking",
      "ai_knowledge",
      "backend_knowledge",
    ]) {
      expect(INTERVIEW_DIMENSIONS.map((d) => d.key)).toContain(key);
    }
    for (const key of ["technical", "experience", "projects", "education"]) {
      expect(MATCH_DIMENSIONS.map((d) => d.key)).toContain(key);
    }
  });

  it("reads a dimension in the reader's language", () => {
    expect(matchDimensionLabel(chinese, "technical")).toBe("技术");
    expect(matchDimensionLabel(english, "technical")).toBe("Technical");
    expect(interviewDimensionLabel(chinese, "technical_accuracy")).toBe("技术准确度");
    expect(interviewDimensionLabel(english, "problem_solving")).toBe("Problem solving");
    expect(resumeDimensionLabel(chinese, "bullets")).toBe("要点与数据密度");
    expect(resumeCriterionLabel(chinese, "has_skills")).toBe("足够的技能（5 项以上）");
  });

  it("keeps the English name when the locale has none", () => {
    // A locale that does not name a dimension must not blank the bar: the
    // product's own English name is the fallback, which is the same rule
    // `stageLabel` follows for the pipeline's seven stages.
    const bare = (key: string) => key;
    expect(matchDimensionLabel(bare, "technical")).toBe("Technical");
    expect(interviewDimensionLabel(bare, "technical_accuracy")).toBe("Technical accuracy");
    expect(resumeCriterionLabel(bare, "has_skills")).toBe("Enough skills (5+)");
  });

  it("shows a dimension nobody knows rather than hiding it", () => {
    // A bar the reader cannot see is worse than a bar with an ugly label.
    expect(matchDimensionLabel(english, "vibe")).toBe("vibe");
    expect(interviewDimensionLabel(english, "some_new_dimension")).toBe("some new dimension");
  });

  it("keeps a structure in an answer and a structure in a resume apart", () => {
    // The two vocabularies share a key, which is exactly why they have
    // separate namespaces: a reader looking at an answer's structure must
    // not be shown the resume's.
    expect(interviewDimensionLabel(english, "structure")).toBe("Structure");
    expect(resumeDimensionLabel(english, "structure")).toBe("Structure & scannability");
  });

  it("has a Chinese name for every dimension it knows", () => {
    for (const vocabulary of [MATCH_DIMENSIONS, INTERVIEW_DIMENSIONS, RESUME_DIMENSIONS, RESUME_CRITERIA]) {
      for (const d of vocabulary) {
        const namespace =
          vocabulary === MATCH_DIMENSIONS
            ? "match"
            : vocabulary === INTERVIEW_DIMENSIONS
              ? "interview"
              : vocabulary === RESUME_DIMENSIONS
                ? "resume"
                : "criteria";
        const key = `dimensions.${namespace}.${d.key}.label`;
        expect(chinese(key), `${key} has no Chinese name`).not.toBe(key);
        expect(english(key), `${key} has no English name`).not.toBe(key);
      }
    }
  });

  it("reads a dimension through one rule, whatever the namespace", () => {
    expect(dimensionLabel(english, "match", MATCH_DIMENSIONS, "technical")).toBe("Technical");
    expect(dimensionLabel(english, "match", MATCH_DIMENSIONS, "unknown")).toBe("unknown");
  });
});
