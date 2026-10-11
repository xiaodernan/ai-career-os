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
from app.features import (gap_analysis, learning, negotiation, offers, readiness,
                          salary)
from app.main import app

# path -> (request model name, required field names)
FORWARD = {
    "/internal/features/gap-analysis": ("GapReq", {"target_role"}),
    "/internal/features/salary-benchmark": ("SalaryReq", {"role"}),
    "/internal/features/negotiate": ("NegotiateReq", {"role", "offer_base"}),
    "/internal/features/readiness": ("ReadinessReq", {"target_role"}),
    "/internal/features/learning-plan": ("LearningReq", {"target_role"}),
    "/internal/features/compare-offers": ("CompareOffersReq", {"role", "offers"}),
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
    assert set(out) == {"currency", "sampleSize", "offers", "bestByCash", "notes"}
