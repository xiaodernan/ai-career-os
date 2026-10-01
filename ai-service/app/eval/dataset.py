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


# Tuned for the seeded dev corpus, which `scripts/smoke-fullstack.sh` writes: a resume
# covering PrivacyShield 脱敏, Java / Spring Boot, Redis caching and 缓存穿透, MySQL
# 索引 / 优化, Kafka / RabbitMQ 消息队列, Kubernetes scaling, 分布式 微服务, 并发, RAG,
# a security line, and -- since gs-03/gs-05 were otherwise never scored -- an education
# and an internship line. All fifteen cases score against it; a case whose keywords the
# corpus does not contain is *skipped* and listed by the runner (`no_ground_truth`)
# rather than scored -- see `run_eval.run`. Add cases per real corpus via
# `--dataset file.jsonl`.
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
    # Architecture, concurrency, caching, storage, deployment, messaging and security:
    # the topics the seeded corpus carries beyond the first eight cases, each of which is
    # answerable only because that corpus names it.
    EvalCase("gs-09", "分布式 系统 微服务", ["分布式", "微服务"],
             tags=["zh", "skills", "architecture"]),
    EvalCase("gs-10", "How did the candidate handle high concurrency?",
             ["并发", "concurrency"], tags=["en", "skills", "experience"]),
    EvalCase("gs-11", "Redis 缓存 策略 缓存穿透", ["Redis", "缓存穿透"],
             tags=["zh", "skills", "cache"]),
    EvalCase("gs-12", "Spring Boot configuration security",
             ["Spring Boot", "security"], tags=["en", "skills", "security"]),
    EvalCase("gs-13", "数据库 优化 索引 查询", ["数据库", "索引", "优化"],
             tags=["zh", "skills", "database"]),
    EvalCase("gs-14", "Kubernetes deployment scaling", ["Kubernetes", "scaling"],
             tags=["en", "skills", "devops"]),
    EvalCase("gs-15", "消息队列 Kafka RabbitMQ", ["Kafka", "RabbitMQ", "消息队列"],
             tags=["zh", "skills", "messaging"]),
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
