"""Contract gate for the forward growth/salary features (Epics 10.x / 12.x).

Four endpoints were added ahead of their backend bridge: gap-analysis, readiness,
salary-benchmark and negotiate. The backend does not call them yet, so nothing else
in the suite pins their shape -- `test_internal_contract.py` only reconciles paths
the backend *builds*, and the field-producer census keys off frontend receivers that
do not exist yet. That leaves a window where the shape could drift silently before
anyone wires it up.

This gate closes the window: the routes must exist as POSTs under `/internal/features`
and stay behind `require_internal` (never public), each request model's required
fields are fixed, and each engine's response key set is fixed. The point is that the
backend client and the frontend get written against a contract that is *held*, not
remembered -- the same reason the other census gates exist.
"""

import inspect

import pytest
from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.core.deps import require_internal
from app.features import (analytics, company, counter_offer, demand, gap_analysis,
                          growth, ingestion, interview_prep, learning, monitoring,
                          negotiation, offers, outreach, prioritize, progress,
                          progression, readiness, roles, salary, stories)
from app.main import app

# path -> (request model name, required field names)
FORWARD = {
    "/internal/features/gap-analysis": ("GapReq", {"target_role"}),
    "/internal/features/salary-benchmark": ("SalaryReq", {"role"}),
    "/internal/features/negotiate": ("NegotiateReq", {"role", "offer_base"}),
    "/internal/features/readiness": ("ReadinessReq", {"target_role"}),
    "/internal/features/learning-plan": ("LearningReq", {"target_role"}),
    "/internal/features/compare-offers": ("CompareOffersReq", {"role", "offers"}),
    "/internal/features/outreach": ("OutreachReq", {"name"}),
    "/internal/features/progress": ("ProgressReq", {"target_role"}),
    "/internal/features/growth-report": ("GrowthReportReq", {"target_role"}),
    "/internal/features/counter-offer": ("CounterOfferReq", {"role", "offer_base"}),
    "/internal/features/skill-demand": ("SkillDemandReq", {"role"}),
    "/internal/features/story-bank": ("StoryBankReq", set()),
    "/internal/features/role-suggestions": ("RoleSuggestReq", set()),
    "/internal/features/company-brief": ("CompanyBriefReq", {"company"}),
    "/internal/features/progression": ("ProgressionReq", {"aspirational_role"}),
    "/internal/features/learning-priority": ("LearningPriorityReq", {"target_role"}),
    "/internal/features/interview-prep": ("InterviewPrepReq", {"target_role"}),
    "/internal/features/pipeline-funnel": ("PipelineFunnelReq", {"applications"}),
    "/internal/features/response-rate": ("ResponseRateReq", {"applications"}),
    "/internal/features/insight-digest": ("InsightDigestReq", set()),
    "/internal/features/dedupe-jobs": ("DedupeJobsReq", {"postings"}),
    "/internal/features/freshness-sweep": ("FreshnessSweepReq", {"postings"}),
    # `plan_ingest` takes either an already-parsed list or the raw feed text, so
    # neither field is required on its own -- the route refuses a body that carries
    # both or neither. The required set is empty for that reason.
    "/internal/features/plan-ingest": ("PlanIngestReq", set()),
    "/internal/features/health-report": ("HealthReportReq", set()),
    "/internal/features/parse-board": ("ParseBoardReq", {"payload"}),
    "/internal/features/follow-ups": ("FollowUpsReq", set()),
    "/internal/features/export-bundle": ("ExportBundleReq", set()),
    "/internal/features/import-plan": ("ImportPlanReq", {"bundle"}),
    "/internal/features/redact-bundle": ("RedactBundleReq", {"bundle"}),
    "/internal/features/render-bundle": ("RenderBundleReq", {"bundle"}),
}


def _routes() -> dict[str, APIRoute]:
    return {r.path: r for r in app.routes
            if isinstance(r, APIRoute) and r.path.startswith("/internal/features/")}


def _model(route: APIRoute):
    for parameter in inspect.signature(route.endpoint).parameters.values():
        if isinstance(parameter.annotation, type) and issubclass(parameter.annotation, BaseModel):
            return parameter.annotation
    return None


def _depends_on(route: APIRoute, fn) -> bool:
    def walk(dep) -> bool:
        return dep.call is fn or any(walk(d) for d in dep.dependencies)
    return any(walk(d) for d in route.dependant.dependencies)


# ---------------- route shape ----------------


def test_forward_routes_exist_as_internal_posts():
    routes = _routes()
    for path in FORWARD:
        assert path in routes, f"{path} is not registered"
        assert "POST" in routes[path].methods, f"{path} is not a POST"


def test_forward_routes_require_internal_auth():
    routes = _routes()
    for path in FORWARD:
        assert _depends_on(routes[path], require_internal), \
            f"{path} no longer depends on require_internal -- it is reachable unauthenticated"


def test_forward_routes_have_no_public_twin():
    public = {r.path for r in app.routes if isinstance(r, APIRoute)
              and not r.path.startswith("/internal/")}
    for path in FORWARD:
        assert path not in public, f"{path} is exposed as a public route"


def test_forward_request_models_require_their_fields():
    routes = _routes()
    for path, (name, required) in FORWARD.items():
        model = _model(routes[path])
        assert model is not None, f"{path} has no request model"
        assert model.__name__ == name, f"{path} model is {model.__name__}, expected {name}"
        got = {n for n, f in model.model_fields.items() if f.is_required()}
        assert got == required, f"{path} required fields drifted: {got} != {required}"


async def test_the_ingest_plan_refuses_a_body_that_carries_neither_or_both():
    """14.3 -- the sweep plan takes EITHER an already-parsed list OR the raw feed.

    `plan_ingest` accepts both, so the route does too -- but exactly one. A body
    with neither is a plan with nothing to plan from, and a body with both is a
    request that says two different things about the same batch. Both are
    refused, and refused before the engine runs.
    """
    from fastapi import HTTPException

    route = _routes()["/internal/features/plan-ingest"]
    model = _model(route)

    with pytest.raises(HTTPException) as neither:
        await route.endpoint(model(), _ctx())
    assert neither.value.status_code == 400, "a body with neither is a 400"

    with pytest.raises(HTTPException) as both:
        await route.endpoint(
            model(postings=[{"title": "A"}], feed="<rss></rss>"), _ctx())
    assert both.value.status_code == 400, "a body with both is a 400"


def _ctx():
    from app.core.deps import Ctx

    return Ctx(user_id="11111111-1111-1111-1111-111111111111", run_id=None)


# ---------------- response shape (the contract the bridge will rely on) ----------------


async def test_gap_analysis_response_keys(monkeypatch):
    async def fake_ask_json(req, **kw):
        return {"expectedSkills": [{"name": "Java", "importance": "must"}]}

    monkeypatch.setattr(gap_analysis, "ask_json", fake_ask_json)
    out = await gap_analysis.analyze_gap("Senior Backend Engineer", None,
                                         {"skills": [{"name": "Java"}]}, "")
    assert set(out) == {
        "targetRole", "seniority", "expectedSkillCount", "coveredCount", "partialCount",
        "gapCount", "coverage", "covered", "partial", "gaps", "strengths",
        "responsibilities", "developmentPlan"}


def test_salary_benchmark_response_keys():
    out = salary.benchmark(
        [{"title": "Backend Engineer", "salary_min": 1, "salary_max": 2,
          "salary_currency": "CNY"}], role="Backend")
    assert set(out) == {"role", "location", "seniority", "currency", "sampleSize",
                        "percentiles", "evidence"}


def test_negotiation_plan_response_keys():
    report = {"sampleSize": 1, "percentiles": {"min": 1, "p25": 1, "p50": 1,
                                               "p75": 1, "max": 1}}
    out = negotiation.negotiation_plan(1, report)
    assert set(out) == {"offer", "currency", "assessment", "leverage", "talkingPoints",
                        "benchmark"}


def test_readiness_compose_response_keys():
    out = readiness.compose({"coverage": 0.5, "gaps": []})
    assert set(out) == {"targetRole", "seniority", "skillReadiness", "skillVerdict",
                        "salaryVerdict", "verdict", "coveredCount", "gapCount",
                        "mustGaps", "blockers", "actions", "salarySampleSize"}


def test_learning_plan_response_keys():
    out = learning.build_learning_plan({"targetRole": "X", "gaps": []})
    assert set(out) == {"targetRole", "totalItems", "phases"}


def test_compare_offers_response_keys():
    out = offers.compare_offers([{"label": "A", "base": 1}],
                                {"sampleSize": 0, "percentiles": {}})
    assert set(out) == {"currency", "sampleSize", "offers", "bestByComp", "notes"}
    assert set(out["offers"][0]) == {"label", "base", "bonus", "firstYearCash",
                                     "annualEquity", "totalComp", "assessment", "leverage"}


def test_outreach_response_keys():
    out = outreach.compose({"name": "X"}, "referral",
                           {"subject": "s", "body": "b", "evidenceUsed": []},
                           {"skills": [], "highlight": ""})
    assert set(out) == {"purpose", "contactName", "subject", "body", "evidenceUsed",
                        "allowedEvidence"}


def test_progress_response_keys():
    out = progress.diff_progress(None, {"coverage": 0.5, "gaps": []})
    assert set(out) == {"targetRole", "baseline", "closed", "improved", "opened",
                        "regressed", "stillOpen", "previousCoverage", "currentCoverage",
                        "delta", "closedCount", "openCount"}


def test_counter_offer_response_keys():
    out = counter_offer.compose(100, {"sampleSize": 0, "percentiles": {}},
                                {"subject": "s", "body": "b"})
    assert set(out) == {"currency", "currentOffer", "askAmount", "increasePct",
                        "assessment", "rationale", "subject", "body"}


def test_growth_report_response_keys():
    out = growth.build_growth_report({"coverage": 0.5, "gaps": []}, None)
    assert set(out) == {"readiness", "gap", "salary", "learningPlan", "progress"}


def test_skill_demand_response_keys():
    out = demand.skill_demand([{"title": "Backend Engineer", "skills": ["Java"]}],
                              role="Backend")
    assert set(out) == {"role", "location", "postings", "skills"}
    assert set(out["skills"][0]) == {"skill", "count", "share"}


def test_story_bank_response_keys():
    out = stories.build_story_bank({})
    assert set(out) == {"stories", "count", "quantifiedCount", "skillsCovered"}


def test_role_suggestions_response_keys():
    out = roles.suggest_roles([], [])
    assert set(out) == {"families"}
    out = roles.suggest_roles(
        [{"title": "Backend Engineer", "skills": ["Java", "Kubernetes"]}], ["Java"])
    assert set(out["families"][0]) == {"family", "postings", "coverage", "topDemands",
                                       "youHave", "missing"}


def test_company_brief_response_keys():
    out = company.company_brief([], "Acme")
    assert set(out) == {"company", "postings", "roles", "topSkills", "salaryBand"}


def test_progression_response_keys():
    fams = [{"family": "backend", "postings": 10, "coverage": 0.6,
             "topDemands": ["Java", "Kubernetes"], "youHave": ["Java"], "missing": ["Kubernetes"]}]
    stones = progression.build_stepping_stones(fams, ["Kubernetes"], ["Kubernetes"])
    assert set(stones[0]) == {"family", "currentCoverage", "postings", "buildsSkills",
                              "buildsMustCount", "buildsCount", "bridgeScore", "reason"}
    assert stones[0]["buildsSkills"] == ["Kubernetes"]
    assert stones[0]["buildsMustCount"] == 1

    plan = progression.build_advice(0.5, 1, ["Kubernetes"])
    assert isinstance(plan, list) and plan


def test_learning_priority_response_keys():
    gaps = [{"skill": "Kubernetes", "importance": "must", "category": "devops"},
            {"skill": "Docker", "importance": "nice", "category": "devops"}]
    demand_skills = [{"skill": "Kubernetes", "count": 68, "share": 0.68},
                     {"skill": "Docker", "count": 31, "share": 0.31}]
    ranked = prioritize.rank_gap_priorities(gaps, demand_skills, 100)
    assert len(ranked) == 2
    assert set(ranked[0]) == {"skill", "importance", "category", "marketShare",
                              "marketPostings", "marketRank", "priority"}
    # must + high share ranks before nice + lower share; a nice skill the market
    # wants a lot (>=0.3) still tiers as high on market pull alone
    assert ranked[0]["skill"] == "Kubernetes"
    assert ranked[0]["priority"] == "critical"
    assert ranked[1]["priority"] == "high"


def test_interview_prep_response_keys():
    gap = {"targetRole": "Backend Engineer", "coverage": 0.5,
           "covered": [{"skill": "Java", "evidence": "Declared skill: Java"}],
           "gaps": [{"skill": "Kubernetes", "importance": "must"},
                    {"skill": "Go", "importance": "nice"}],
           "responsibilities": ["Design APIs"]}
    bank = {"count": 1, "stories": [
        {"id": "exp-1", "title": "Java service", "skills": ["Java"], "quantified": True,
         "bullets": ["Built a Java service"], "kind": "experience"}]}
    out = interview_prep.build_prep_plan(gap, bank)
    assert set(out) == {"targetRole", "coverage", "weakAreaCount", "strengthStoryCount",
                        "weakAreas", "strengthStories", "likelyTopics", "storyBankSize"}
    assert set(out["weakAreas"][0]) == {"skill", "importance", "action"}
    # must-gap ranks before nice-gap
    assert out["weakAreas"][0]["skill"] == "Kubernetes"
    assert set(out["strengthStories"][0]) == {"skill", "evidence", "storyTitle",
                                              "storyId", "quantified"}
    assert out["strengthStories"][0]["storyId"] == "exp-1"
    assert out["likelyTopics"][0] == "Design APIs"


def test_pipeline_funnel_response_keys():
    out = analytics.pipeline_funnel([
        {"id": "a1", "status": "applied"},
        {"id": "a2", "status": "oa"},
        {"id": "a3", "status": "offer"},
        {"id": "a4", "status": "rejected"},
        {"id": "a5", "status": "saved"},
    ])
    assert set(out) == {"pipeline", "appliedCount", "savedCount", "rejectedCount",
                        "totalApplications"}
    assert set(out["pipeline"][0]) == {"stage", "count", "conversionFromApplied",
                                      "stepConversion"}


def test_response_rate_response_keys():
    out = analytics.response_rate([
        {"id": "a1", "status": "applied"},
        {"id": "a2", "status": "interview", "applied_at": "2026-01-01",
         "interview_at": "2026-01-10"},
        {"id": "a3", "status": "offer"},
        {"id": "a4", "status": "rejected"},
    ])
    assert set(out) == {"appliedCount", "respondedCount", "responseRate",
                        "offerCount", "offerRate", "interviewCount", "interviewRate",
                        "timeInStage"}


def test_insight_digest_response_keys():
    out = analytics.insight_digest(
        [{"id": "a1", "status": "applied", "applied_at": "2026-09-01"},
         {"id": "a2", "status": "offer"}], stale_days=14,
        growth_deltas=[{"closed": ["k8s"]}], top_matches=[{"title": "X", "score": 0.9}])
    assert set(out) == {"generatedAt", "windowDays", "totalApplications",
                        "activePipeline", "stageCounts", "responseRate", "offerRate",
                        "stalledCount", "stalled", "signals", "growthDeltas",
                        "topMatches"}


def test_dedupe_jobs_response_keys():
    out = ingestion.dedupe_postings([
        {"id": "a", "company": "C", "title": "T", "location": "L"},
        {"id": "b", "company": "C", "title": "T", "location": "L"},
    ])
    assert set(out) == {"unique", "duplicates", "inputCount", "uniqueCount",
                        "duplicateCount"}


def test_freshness_sweep_response_keys():
    out = ingestion.freshness_sweep([{"id": "a", "posted_at": "2026-01-01"}])
    assert set(out) == {"fresh", "stale", "expired", "undated", "counts"}
    assert set(out["counts"]) == {"fresh", "stale", "expired", "undated"}


def test_plan_ingest_response_keys():
    out = ingestion.plan_ingest([{"title": "T", "company": "C", "location": "L"}])
    assert set(out) == {"source", "create", "update", "close", "duplicates", "counts"}
    assert set(out["counts"]) == {"incoming", "create", "update", "close", "duplicates"}


def test_health_report_response_keys():
    out = monitoring.health_report([{"status": "completed", "latency_ms": 10}])
    assert set(out) == {"summary", "regressions", "alerts", "verdict"}
    assert set(out["summary"]) == {
        "totalRuns", "byStatus", "finished", "completed", "failed", "errorRate",
        "successRate", "latencyMs", "totalCostUsd", "avgCostUsd", "totalTokens"}


def test_parse_board_response_keys():
    out = ingestion.parse_json_board('[{"title": "T"}]')
    assert isinstance(out, list) and set(out[0]) == {"title", "source"}

