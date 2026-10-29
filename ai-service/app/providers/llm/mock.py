"""Deterministic mock provider — TEST INFRASTRUCTURE ONLY.

Produces schema-valid, content-appropriate responses so the full pipeline can be
exercised in CI without external services. Refused at startup when APP_ENV=prod.
It is NOT a product feature: the product requires a real LLM provider.
"""

import asyncio
import hashlib
import json
import re
from collections.abc import AsyncIterator

from app.providers.base import LLMRequest, LLMResponse, StreamDelta, Usage


def _prompt_skills(prompt: str) -> list[str]:
    """The candidate's own skills, as the prompt lists them.

    The mock cites what the prompt gave it, because the evidence validator
    strips anything the profile does not support: a mock that invented a
    skill would answer with an empty message, and the offline stack would
    be exercising a path the product never takes.
    """
    match = re.search(r"CANDIDATE SKILLS:\s*(.+)", prompt)
    if not match:
        return []
    line = match.group(1).strip()
    if not line or line.startswith("("):
        return []
    return [s.strip() for s in line.split(",") if s.strip()]


class MockProvider:
    name = "mock"

    def __init__(self, default_model: str = "mock-model"):
        self.model = default_model

    def _system(self, req: LLMRequest) -> str:
        return " ".join(m.content for m in req.messages if m.role == "system")[:4000]

    def _last_user(self, req: LLMRequest) -> str:
        for m in reversed(req.messages):
            if m.role == "user":
                return m.content
        return ""

    async def complete(self, req: LLMRequest) -> LLMResponse:
        await asyncio.sleep(0.01)
        prompt = self._system(req) + "\n" + self._last_user(req)
        text = self._respond(req, prompt)
        tool_calls = []
        tc = self._maybe_tool_call(req)
        if tc:
            text, tool_calls = "", [tc]
        h = hashlib.sha256(prompt.encode()).hexdigest()
        in_tok = max(1, len(prompt) // 4)
        out_tok = max(1, len(text) // 4)
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            usage=Usage(in_tok, out_tok, cached_tokens=in_tok if h[:4] == "0000" else 0),
            model=req.model or self.model,
            latency_ms=15,
        )

    # --- deterministic tool-call emulation so the agent loop runs in CI ---

    TOOL_HINTS = [
        (("job", "岗位", "职位", "position", "hiring"), "search_jobs",
         lambda low: {"query": "backend", "limit": 5}),
        (("resume", "简历"), "search_resume",
         lambda low: {"query": "experience projects skills"}),
        (("profile", "档案", "背景"), "get_user_profile", lambda low: {}),
    ]

    def _maybe_tool_call(self, req: LLMRequest):
        if not req.tools:
            return None
        available = {t.name for t in req.tools}
        if any(m.role == "tool" for m in req.messages):
            # Tools already ran: summarize their payload instead of looping.
            return None
        low = self._last_user(req).lower()
        for keywords, name, args_fn in self.TOOL_HINTS:
            if name in available and any(k in low for k in keywords):
                from app.providers.base import ToolCall

                return ToolCall(id="call_mock_1", name=name, arguments=args_fn(low))
        return None

    def _respond(self, req: LLMRequest, prompt: str) -> str:
        low = prompt.lower()
        tool_msgs = [m for m in req.messages if m.role == "tool"]
        if tool_msgs and not req.json_mode and "return json" not in low:
            preview = tool_msgs[-1].content[:280]
            return (f"Done. Tool results ({len(tool_msgs)} call(s)); latest output: "
                    f"{preview}")
        if req.json_mode or "return json" in low or "json only" in low:
            return self._json_response(low, prompt)
        if "interviewer" in low or "interview" in low:
            return "Tell me about a system you built and the hardest technical decision in it."
        return (
            "Based on the retrieved evidence, your profile aligns well with the "
            "requirement. See cited sources for the supporting resume excerpt."
        )

    def _json_response(self, low: str, prompt: str) -> str:
        if "classify one recruiter reply" in low:
            # 37.2: the reply reader. The intent the words settle never reaches this
            # branch -- `reply_classify` asks only for what its cue passes left open --
            # so the fixed answer is the neutral reading plus the two names a letter
            # may not carry. A fixed answer is what keeps the offline stack stable.
            return json.dumps({"intent": "other", "company": "Mock Corp",
                               "role": "Backend Engineer"})
        if "resume" in low and ("parse" in low or "profile" in low):
            return json.dumps({
                "profile": {"name": "Mock Candidate", "headline": "Backend Engineer",
                            "yearsExperience": 2, "location": "Mock City"},
                "education": [{"school": "Mock University", "degree": "BSc",
                               "field": "Computer Science", "endYear": 2023}],
                "experience": [{"company": "Mock Corp", "title": "Backend Engineer",
                                "start": "2023-07", "end": "present",
                                "bullets": ["Built REST APIs with Java and Spring Boot"]}],
                "projects": [{"name": "MockProject", "tech": ["Java", "Redis"],
                              "bullets": ["Reduced p99 latency by 30%"]}],
                "skills": [{"name": "Java", "category": "language"},
                           {"name": "Spring Boot", "category": "framework"},
                           {"name": "Redis", "category": "tool"}],
                "achievements": [], "careerGoals": ["Senior Backend Engineer"],
                "preferredRoles": ["Backend Engineer"], "preferredLocations": ["Remote"],
            })
        if "jd" in low or "job description" in low:
            # The two names a tracker files a job under. `title` is left blank on purpose: reading a
            # role out of a posting is the analyst's job, and `jd_analyze._backfill_identity` does it
            # deterministically from the pasted text — a mock that invented one would speak for the
            # reader's own words. `company` the mock does name, because nothing else on the offline
            # stack can, and an unnamed paste otherwise lands under the fabricated business
            # "Unknown company", which every user's failed import then shares.
            return json.dumps({
                "title": "", "company": "Mock Corp",
                "requiredSkills": [{"name": "Java", "priority": "must"}],
                "preferredSkills": [{"name": "Kubernetes", "priority": "nice"}],
                "responsibilities": ["Design backend services"],
                "experienceYears": 3, "education": {"minDegree": "Bachelor"},
                "softSkills": ["Communication"], "hiddenRequirements": ["On-call rotation"],
                "interviewTopics": ["Java concurrency", "Caching", "System design"],
                "priorityOrder": ["Java", "System design"],
            })
        if "match" in low and "score" in low:
            return json.dumps({"overall": 0.8, "technical": 0.85, "experience": 0.75,
                               "projects": 0.8, "education": 0.7,
                               "matchedSkills": ["Java"], "missingSkills": ["Kubernetes"],
                               "evidence": [{"criterion": "Java", "score": 0.9,
                                             "quote": "Built REST APIs with Java",
                                             "reasoning": "direct overlap"}]})
        if "grade one interview answer" in low:
            return json.dumps({
                "score": 0.72, "dims": {"technical_accuracy": 0.8,
                                        "communication": 0.7, "depth": 0.6,
                                        "structure": 0.7},
                "strengths": ["named a concrete system"], "weaknesses": ["no numbers"],
                "missing_concepts": ["cache invalidation"],
                "better_answer": "Describe problem, your decision, trade-offs, result.",
                "question_was_answered": True})
        if "interview director" in low:
            return json.dumps({
                "action": "followup",
                "question": "Why did you choose Redis over a local in-process cache?",
                "topic": "caching", "difficulty": 0.65,
                "reasoning": "answer named a tool without justification"})
        if "interview report" in low:
            return json.dumps({
                "dims": {d: 0.65 for d in ["technical_accuracy", "communication",
                                           "depth", "structure", "problem_solving",
                                           "system_thinking", "ai_knowledge",
                                           "backend_knowledge"]},
                "overall": 0.66, "what_you_did_well": ["concrete example"],
                "what_was_weak": ["shallow trade-off analysis"],
                "missing_concepts": ["cache stampede"],
                "better_answers": [{"question": "Why Redis?", "model_answer": "..."}],
                "follow_up_questions_to_prepare": ["How would you handle 100k QPS?"],
                "recommended_study": [{"topic": "caching", "why": "gap",
                                       "resource_hint": "DDIA ch.1"}],
                "trajectory_note": "depth rose from naming to failure modes"})
        if "outreach" in low and "evidenceused" in low:
            # The outreach engine's own shape: a subject, a body, and the
            # evidence the message cites. The evidence the mock cites is the
            # candidate's own skills from the prompt, because the validator
            # strips anything else -- so a mock that cited something else
            # would answer with an empty message and teach the wrong thing.
            skills = _prompt_skills(prompt)
            cite = skills[:2]
            body = (
                "Hi — I am a backend engineer working mostly in Java and Spring, "
                "and I came across your work while looking at the team. "
                "I am after a backend role and wondered whether you would be "
                "open to pointing me at one, or to an introduction to the "
                "person who hires for it. Happy to send a short write-up of "
                "what I have built. And entirely fine if this is not "
                "something you can help with."
            )
            return json.dumps({
                "subject": "A quick question about a backend role",
                "body": body,
                "evidenceUsed": cite,
            })
        if "relevance" in low or "rerank" in low:
            nums = re.findall(r"\[(\d+)\]", prompt)
            scores = {n: max(0.1, 1.0 - i * 0.1) for i, n in enumerate(nums)}
            return json.dumps({"scores": scores})
        return json.dumps({"answer": "mock structured answer", "confidence": 0.8})

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamDelta]:
        resp = await self.complete(req)
        for i in range(0, len(resp.text), 24):
            yield StreamDelta(text=resp.text[i:i + 24])
        yield StreamDelta(usage=resp.usage, done=True, tool_calls=resp.tool_calls)
