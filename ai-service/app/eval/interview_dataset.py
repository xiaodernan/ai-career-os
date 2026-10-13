"""Scripted interview transcripts for the interview evaluation harness (PRD §15, §34).

Each fixture is a *shape* an interviewer can legitimately produce, plus the report it
would have produced. They are the interview path's equivalent of `agent_dataset.py`:
the scorer in `interview_metrics.py` is worthless without transcripts to score, and a
transcript set with only the happy path cannot prove the harness discriminates.

`iv-strong` / `iv-weak` are the discrimination pair: the same ladder, two reports that
measure a genuinely different candidate. `iv-flat` is the defect the metric exists for.
"""

from __future__ import annotations

from app.eval.interview_metrics import InterviewTranscript


def _turns(pairs: list[tuple[str, str]]) -> list[dict]:
    return [{"seq": i, "role": role, "content": text}
            for i, (role, text) in enumerate(pairs)]


def _move(seq: int, action: str, difficulty: float, topic: str,
          question: str = "") -> dict:
    return {"seq": seq, "action": action, "difficulty": difficulty,
            "topic": topic, "question": question}


STRONG_TURNS = _turns([
    ("interviewer", "Tell me about a caching layer you designed."),
    ("candidate", "I designed a write-through cache for the payments service. I chose "
                  "Redis with a 200ms TTL and a circuit breaker, and measured a 40% "
                  "latency drop on the read path."),
    ("interviewer", "What happened the first time the cache went down?"),
    ("candidate", "Every request fell through to Postgres and the p95 spiked to 4 "
                  "seconds. I added a stale-while-revalidate path so stale data "
                  "served while the backend recovered."),
    ("interviewer", "How would you scale that to ten times the traffic?"),
    ("candidate", "I would shard by customer id, add a read replica for warm reads, "
                  "and move the eviction policy to LRU-K to cut thrash."),
])

STRONG_MOVES = [
    _move(1, "next_topic", 0.3, "caching", "Tell me about a caching layer you designed."),
    _move(2, "followup", 0.45, "caching",
          "What happened the first time the cache went down?"),
    _move(3, "followup", 0.6, "scaling",
          "How would you scale that to ten times the traffic?"),
]

# Eight distinct scores: the candidate was strong on depth and system design, weaker
# on communication. This is what a discriminating report looks like.
STRONG_REPORT = {
    "dims": {
        "technical_accuracy": 0.85, "communication": 0.6, "depth": 0.9,
        "structure": 0.7, "problem_solving": 0.8, "system_thinking": 0.88,
        "ai_knowledge": 0.82, "backend_knowledge": 0.86,
    },
    "overall": 0.8,
    "what_you_did_well": ["Named concrete trade-offs and quantified the latency drop."],
    "what_was_weak": ["The \"stale-while-revalidate\" path was asserted as the fix "
                      "without a measurement."],
    "missing_concepts": ["warm-standby replicas"],
    "better_answers": [{"question": "How would you scale it?", "model_answer": "Shard, "
                          "then warm with a replica, then re-tune eviction."}],
    "follow_up_questions_to_prepare": ["How does LRU-K behave under burst?"],
    "recommended_study": [{"topic": "eviction policies", "why": "trade-off depth",
                           "resource_hint": "Redis docs"}],
    "trajectory_note": "Depth increased steadily across three questions.",
}


WEAK_TURNS = _turns([
    ("interviewer", "Tell me about a caching layer you designed."),
    ("candidate", "I mostly used the framework's built-in cache."),
    ("interviewer", "What did you do when it failed?"),
    ("candidate", "I am not sure, I think someone else handled that part."),
    ("interviewer", "How would you scale it?"),
    ("candidate", "Probably put it in the cloud."),
])

WEAK_MOVES = STRONG_MOVES

# The same dimensions, scored for a candidate who did not answer: accuracy and depth
# collapse while structure stays moderate.
WEAK_REPORT = {
    "dims": {
        "technical_accuracy": 0.2, "communication": 0.45, "depth": 0.15,
        "structure": 0.35, "problem_solving": 0.25, "system_thinking": 0.2,
        "ai_knowledge": 0.1, "backend_knowledge": 0.3,
    },
    "overall": 0.25,
    "what_you_did_well": ["Stayed honest about not owning the failure path."],
    "what_was_weak": [
        "The cache answer stayed generic — the framework's built-in cache was used "
        "with no design of its own.",
        "The failure path was never investigated: \"someone else handled that part\".",
        "The scaling answer named no mechanism — \"probably put it in the cloud\".",
    ],
    "missing_concepts": ["stable-while-revalidate", "sharding"],
    "better_answers": [{"question": "Tell me about the caching layer.",
                        "model_answer": "Start with the failure mode, then the design."}],
    "follow_up_questions_to_prepare": ["What is a stale-while-revalidate path?"],
    "recommended_study": [{"topic": "cache failure modes", "why": "no mechanism proposed",
                           "resource_hint": "any distributed-systems text"}],
    "trajectory_note": "Depth stayed low and never recovered.",
}


# The defect: eight identical scores. Complete, plausible, and says nothing.
FLAT_TURNS = STRONG_TURNS
FLAT_MOVES = STRONG_MOVES
FLAT_REPORT = {
    "dims": {d: 0.7 for d in (
        "technical_accuracy", "communication", "depth", "structure",
        "problem_solving", "system_thinking", "ai_knowledge", "backend_knowledge")},
    "overall": 0.7,
    "what_you_did_well": ["A steady interview."],
    "what_was_weak": ["Nothing stood out."],
    "missing_concepts": [],
    "better_answers": [],
    "follow_up_questions_to_prepare": [],
    "recommended_study": [],
    "trajectory_note": "Depth did not vary.",
}


# The label defect: the action says follow-up, so the report's depth trajectory counts
# it as one, but no question was ever asked.
MISSING_QUESTION_MOVES = [
    _move(1, "next_topic", 0.3, "caching", "Tell me about a caching layer you designed."),
    _move(2, "followup", 0.45, "caching", ""),
    _move(3, "followup", 0.6, "scaling", ""),
]


# The clamp defect: a session that walked itself out of the band.
OUT_OF_BAND_MOVES = [
    _move(1, "next_topic", 0.3, "caching", "Tell me about a caching layer."),
    _move(2, "followup", 1.7, "caching", "Walk me through every failure mode."),
    _move(3, "followup", 2.4, "scaling", "Now scale it to Google."),
]


# The fabrication defect: a weakness that names nothing the candidate ever said.
FABRICATED_WEAKNESS_REPORT = dict(FLAT_REPORT)
FABRICATED_WEAKNESS_REPORT = {
    **STRONG_REPORT,
    "what_was_weak": ["You struggled with the distributed consensus question about Raft "
                      "and the quorum rollback protocol, which you never answered."],
}


# ------------------------- the CJK pair: zh grounding -------------------------
# Chinese is half the product's traffic (the RAG golden set scores zh cases), but the
# grounding metric tokenized a whole CJK clause as one unmatchable lexeme, so an honest
# Chinese weakness shared no distinctive tokens with its own transcript and scored as
# fabricated. The pair pins both directions after `_tokens` learned CJK bigrams.

ZH_TURNS = _turns([
    ("interviewer", "讲一个你处理缓存穿透的经历。"),
    ("candidate", "我在订单服务里遇到了缓存穿透：大量不存在的 key 打到 MySQL。"
                  "我先加了布隆过滤器挡住不存在的 key，再对空结果做短期降级缓存，"
                  "QPS 峰值从 8k 降到 1.2k。"),
    ("interviewer", "布隆过滤器误判怎么办？"),
    ("candidate", "误判会挡住存在的 key，所以我们对高价值 key 走白名单旁路，"
                  "并且监控误判率超过千分之五就扩容位图。"),
])

# The honest report: the weakness quotes the candidate's own words (布隆过滤器 /
# 误判率 / 位图 all appear in the transcript), and the eight dims use the names the
# product prompt emits.
ZH_HONEST_REPORT = {
    "dims": {
        "technical_accuracy": 0.85, "communication": 0.7, "depth": 0.88,
        "structure": 0.75, "problem_solving": 0.8, "system_thinking": 0.86,
        "ai_knowledge": 0.5, "backend_knowledge": 0.9,
    },
    "overall": 0.78,
    "what_you_did_well": ["把缓存穿透的量级和效果都给了数字。"],
    "what_was_weak": ["布隆过滤器的误判率只说了扩容位图，没给出误判率公式和位数估算。"],
    "missing_concepts": ["空值缓存的 TTL 策略"],
    "better_answers": [{"question": "布隆过滤器误判怎么办？",
                        "model_answer": "先给误判率公式，再反推位数 m 和哈希函数个数 k。"}],
    "follow_up_questions_to_prepare": ["缓存雪崩和穿透的治理差异？"],
    "recommended_study": [{"topic": "布隆过滤器容量估算", "why": "误判率估算缺失",
                           "resource_hint": "Redis 官方文档"}],
    "trajectory_note": "对缓存失效路径的追问回答稳定。",
}

# The fabricated report: same transcript, a weakness naming Raft consensus machinery
# the candidate never mentioned.
ZH_FABRICATED_REPORT = {
    **ZH_HONEST_REPORT,
    "what_was_weak": ["你在 Raft 选举中的任期投票问题上表现很差，二次幂投票流程完全没答上来。"],
}


GOLDEN_INTERVIEWS: list[InterviewTranscript] = [
    InterviewTranscript(id="strong", turns=STRONG_TURNS, moves=STRONG_MOVES,
                        report=STRONG_REPORT),
    InterviewTranscript(id="weak", turns=WEAK_TURNS, moves=WEAK_MOVES,
                        report=WEAK_REPORT),
    InterviewTranscript(id="flat", turns=FLAT_TURNS, moves=FLAT_MOVES,
                        report=FLAT_REPORT),
    InterviewTranscript(id="missing_question", turns=STRONG_TURNS,
                        moves=MISSING_QUESTION_MOVES, report=STRONG_REPORT),
    InterviewTranscript(id="out_of_band", turns=STRONG_TURNS, moves=OUT_OF_BAND_MOVES,
                        report=STRONG_REPORT),
    InterviewTranscript(id="fabricated", turns=STRONG_TURNS, moves=STRONG_MOVES,
                        report=FABRICATED_WEAKNESS_REPORT),
    # The CJK pair: the same zh transcript with an honest and a fabricated weakness.
    InterviewTranscript(id="zh_honest", turns=ZH_TURNS, moves=STRONG_MOVES,
                        report=ZH_HONEST_REPORT),
    InterviewTranscript(id="zh_fabricated", turns=ZH_TURNS, moves=STRONG_MOVES,
                        report=ZH_FABRICATED_REPORT),
]


def load_interviews() -> list[InterviewTranscript]:
    """The golden set the harness scores. Mirrors `agent_dataset.load_scenarios`."""
    return GOLDEN_INTERVIEWS
