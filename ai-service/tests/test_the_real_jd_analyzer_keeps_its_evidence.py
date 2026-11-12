"""A real gateway keeps the JD analyzer's evidence contract, not just its transport (Epic 158).

Epic 155 proves the project's own provider factory reaches a real model (PONG + a cover
letter). Epic 156 proves structured output, streaming and tool calls survive the wire. This
file closes the remaining gap: a *model-as-product* path the reader actually depends on --
`jd_analyze.analyze_jd` -- still produces a shape the deterministic post-processing and the
UI can consume when a real `gpt-6-sol` answers, not only the offline mock.

What is at stake is the JD analyzer's honesty rule, not prose quality. Every required skill
must carry an `evidence_phrase` copied verbatim from the posting: the product shows that quote
next to the skill so a candidate can see the model did not invent a requirement. A provider
that returns `requiredSkills` as strings, drops `evidence_phrase`, or paraphrases the quote
would break the screen while every transport-level test stayed green. That is the drift this
file pins, measured on 2026-11-12 against `gpt-6-sol` @`wkapi.pro/v1`.

Inert by default, like its siblings: a plain `pytest` / CI / pre-commit run skips the whole
module before any socket opens. It bills only when an operator opts in:

    CAREEROS_REAL_LLM=1 LLM_PROVIDER=openai_compat \
        LLM_BASE_URL=https://<gateway>/v1 LLM_MODEL=<id> \
        pytest tests/test_the_real_jd_analyzer_keeps_its_evidence.py -q

No key literal lives here; `Settings` resolves it from the process environment or the
gitignored `.env`, the same way production does. One async test on one loop on purpose: the
registry's cached client binds to the first loop that uses it (Epic 155's trap).
"""

from __future__ import annotations

import os

import pytest

_OPT_IN = os.environ.get("CAREEROS_REAL_LLM") == "1"

pytestmark = pytest.mark.skipif(
    not _OPT_IN,
    reason="opt-in only: set CAREEROS_REAL_LLM=1 with a real LLM_PROVIDER/LLM_API_KEY",
)

# A posting whose requirements are each a distinct, quotable line. The evidence check below is
# only meaningful when the model has real phrases to copy, so the fixture spells them out.
JD = """Senior Backend Engineer - Agent Platform
Acme Corp | Remote (EU) | Full-time

We are building the agent orchestration platform. You will:
- Design and ship high-throughput Python services (FastAPI, asyncio).
- Model data in PostgreSQL and cache hot paths in Redis.
- Own Kubernetes deployments and observability (Prometheus, OpenTelemetry).

Requirements:
- 5+ years building production backend services in Python.
- Strong experience with PostgreSQL, including query optimization and indexes.
- Hands-on Redis (caching, streams, rate limiting).
- Experience with container orchestration (Kubernetes or Docker Swarm).
Nice to have:
- Familiarity with LLM serving and prompt engineering.
- Exposure to event-driven architectures (Kafka, NATS).
We work in a fast-paced, on-call rotation and expect fluent English."""


def _real_settings():
    """Lazy, env-only config; every refusal is a skip, never a failure."""
    from app.core.config import Settings

    s = Settings()
    if s.llm_provider != "openai_compat":
        pytest.skip(f"LLM_PROVIDER is {s.llm_provider!r}, not 'openai_compat'")
    if not s.llm_api_key:
        pytest.skip("no LLM_API_KEY in the environment / gitignored .env")
    if "/v1" not in s.llm_base_url:
        pytest.skip("LLM_BASE_URL must include the /v1 protocol prefix for this gateway")
    return s


async def test_a_real_model_answers_the_full_jd_analyzer_contract():
    """The production `analyze_jd` seam returns a UI-consumable shape on a real model.

    Assertions are structural and honesty-bearing, never about the model's exact wording: the
    post-processing must have run, the required skills must each quote the posting verbatim,
    and the list-valued sections the screen maps over must still be lists.
    """
    from app.features.jd_analyze import analyze_jd

    s = _real_settings()
    out = await analyze_jd(JD, user_id="real-jd-probe")

    # The deterministic post-processing ran on the model's answer, not a raw passthrough.
    assert isinstance(out, dict)
    assert out.get("rawTextLength") == len(JD)
    assert isinstance(out.get("title"), str) and out["title"].strip()
    assert out["title"] == "Senior Backend Engineer - Agent Platform"

    # The core honesty rule: every required skill carries a verbatim quote from the posting.
    required = out.get("requiredSkills")
    assert isinstance(required, list) and required, "a real JD must yield required skills"
    for skill in required:
        assert isinstance(skill, dict), f"requiredSkills entry is not an object: {skill!r}"
        assert isinstance(skill.get("name"), str) and skill["name"].strip()
        quote = skill.get("evidence_phrase")
        assert isinstance(quote, str) and quote.strip(), (
            f"required skill {skill.get('name')!r} lost its evidence_phrase on a real model")
        # The quote must actually be copied from the posting, not paraphrased or invented.
        assert quote in JD, (
            f"evidence_phrase for {skill['name']!r} is not verbatim from the JD: {quote!r}")

    # Sections the UI iterates over survive the wire as lists, and the model read the posting.
    for key in ("preferredSkills", "hiddenRequirements", "interviewTopics",
                "responsibilities", "softSkills", "priorityOrder", "domainKeywords"):
        assert isinstance(out.get(key), list), f"{key} drifted off a list on a real model"
    assert out["interviewTopics"], "a real JD must yield interview topics"
    assert out["hiddenRequirements"], "a real JD must infer plausible hidden requirements"
