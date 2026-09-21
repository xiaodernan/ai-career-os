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
        h = hashlib.sha256(prompt.encode()).hexdigest()
        in_tok = max(1, len(prompt) // 4)
        out_tok = max(1, len(text) // 4)
        return LLMResponse(
            text=text,
            usage=Usage(in_tok, out_tok, cached_tokens=in_tok if h[:4] == "0000" else 0),
            model=req.model or self.model,
            latency_ms=15,
        )

    def _respond(self, req: LLMRequest, prompt: str) -> str:
        low = prompt.lower()
        if req.json_mode or "return json" in low or "json only" in low:
            return self._json_response(low, prompt)
        if "interviewer" in low or "interview" in low:
            return "Tell me about a system you built and the hardest technical decision in it."
        return (
            "Based on the retrieved evidence, your profile aligns well with the "
            "requirement. See cited sources for the supporting resume excerpt."
        )

    def _json_response(self, low: str, prompt: str) -> str:
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
            return json.dumps({
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
        if "relevance" in low or "rerank" in low:
            nums = re.findall(r"\[(\d+)\]", prompt)
            scores = {n: max(0.1, 1.0 - i * 0.1) for i, n in enumerate(nums)}
            return json.dumps({"scores": scores})
        return json.dumps({"answer": "mock structured answer", "confidence": 0.8})

    async def stream(self, req: LLMRequest) -> AsyncIterator[StreamDelta]:
        resp = await self.complete(req)
        for i in range(0, len(resp.text), 24):
            yield StreamDelta(text=resp.text[i:i + 24])
        yield StreamDelta(usage=resp.usage, done=True)
