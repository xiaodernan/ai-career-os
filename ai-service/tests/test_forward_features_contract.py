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

from fastapi.routing import APIRoute
from pydantic import BaseModel

from app.core.deps import require_internal
from app.features import (company, counter_offer, demand, gap_analysis, growth,
                          learning, negotiation, offers, outreach, prioritize, progress,
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

