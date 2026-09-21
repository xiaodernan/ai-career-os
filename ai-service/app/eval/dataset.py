"""Evaluation golden set.

Ground truth is defined by keyword sets: at eval time every chunk of the user
whose text contains one of the keywords is marked relevant (weak but honest
supervision — replace/augment with hand-labeled chunk ids when productizing).
"""

from dataclasses import dataclass, field


@dataclass
class EvalCase:
    id: str
    query: str
    keywords: list[str]                       # chunks containing these are relevant
    kinds: list[str] | None = None            # metadata filter under test
    expects_answer: bool = True
    notes: str = ""
    tags: list[str] = field(default_factory=list)


# Tuned for the seeded dev corpus (smoke resume: PrivacyShield / Java / Spring
# Boot / Redis internships, projects, education). Add cases per real user corpus
# via --dataset file.jsonl override for production eval runs.
GOLDEN_SET: list[EvalCase] = [
    EvalCase("gs-01", "隐私盾 数据脱敏 项目 用了什么技术", ["PrivacyShield", "脱敏"],
             tags=["zh", "projects"]),
    EvalCase("gs-02", "What backend frameworks does the candidate know?",
             ["Spring Boot"], tags=["en", "skills"]),
    EvalCase("gs-03", "实习经历 internship experience", ["实习", "Internship"],
             kinds=["resume"], tags=["experience"]),
    EvalCase("gs-04", "Redis 缓存 的使用经验", ["Redis"], tags=["zh", "skills"]),
    EvalCase("gs-05", "教育背景 学校 专业", ["大学", "University", "Bachelor"],
             kinds=["resume"], tags=["education"]),
    EvalCase("gs-06", "How does the candidate describe system design work?",
             ["设计", "design"], tags=["en", "projects"]),
    EvalCase("gs-07", "数据脱敏 隐私", ["隐私"], tags=["zh"]),
    EvalCase("gs-08", "Java performance optimization latency", ["Java"],
             tags=["en", "skills"]),
]


def load_dataset(path: str) -> list[EvalCase]:
    import json

    cases: list[EvalCase] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            cases.append(EvalCase(**d))
    return cases
