"""Unit tests for the Learning Plan (forward Epic 10.5).

The plan is deterministic: it orders gaps by learning dependency (foundation ->
core stack -> applied) and attaches a category-aware starting point. These tests
pin the ordering, the phase grouping and the resource hints -- and that the plan
stays honest (a hint is a *kind* of exercise, never an invented URL or hour count).
"""

from app.features.learning import (PHASES, RESOURCE_HINTS, build_learning_plan,
                                   phase_of)


# ---------------- phase_of ----------------


def test_phase_of_maps_categories_to_phases():
    assert phase_of("language") == "foundation"
    assert phase_of("cs_fundamentals") == "foundation"
    assert phase_of("framework") == "core"
    assert phase_of("data") == "core"
    assert phase_of("devops") == "applied"
    assert phase_of("ai") == "applied"


def test_phase_of_unknown_defaults_to_applied():
    assert phase_of("weird") == "applied"
    assert phase_of("") == "applied"


# ---------------- build_learning_plan ----------------


GAP = {
    "targetRole": "Senior Backend Engineer",
    "gaps": [
        {"skill": "Kubernetes", "category": "devops", "importance": "must"},
        {"skill": "Go", "category": "language", "importance": "nice"},
        {"skill": "Spring Boot", "category": "framework", "importance": "should"},
        {"skill": "System Design", "category": "method", "importance": "must"},
    ],
    "partial": [
        {"skill": "Redis", "category": "data", "importance": "should"},
    ],
}


def test_plan_orders_by_dependency_phase():
    plan = build_learning_plan(GAP)
    assert plan["totalItems"] == 5
    assert [p["phase"] for p in plan["phases"]] == ["foundation", "core", "applied"]
    assert [i["topic"] for i in plan["phases"][0]["items"]] == ["Go"]
    assert [i["topic"] for i in plan["phases"][1]["items"]] == ["Redis", "Spring Boot"]
    assert [i["topic"] for i in plan["phases"][2]["items"]] == ["Kubernetes", "System Design"]


def test_plan_labels_each_phase():
    plan = build_learning_plan(GAP)
    assert [p["label"] for p in plan["phases"]] == [
        PHASES["foundation"]["label"], PHASES["core"]["label"], PHASES["applied"]["label"]]


def test_plan_attaches_category_aware_resource_hints():
    plan = build_learning_plan(GAP)
    foundation = {i["topic"]: i for i in plan["phases"][0]["items"]}
    assert foundation["Go"]["resource_hint"] == RESOURCE_HINTS["language"]
    core = {i["topic"]: i for i in plan["phases"][1]["items"]}
    assert core["Spring Boot"]["resource_hint"] == RESOURCE_HINTS["framework"]


def test_plan_marks_partials_as_promote_to_declared_skill():
    plan = build_learning_plan(GAP)
    redis = next(i for p in plan["phases"] for i in p["items"] if i["topic"] == "Redis")
    assert "quantifies" in redis["resource_hint"]
    assert redis.get("note")


def test_plan_unknown_category_gets_the_default_hint():
    plan = build_learning_plan({"gaps": [{"skill": "X", "category": "weird",
                                          "importance": "should"}]})
    assert plan["phases"][0]["phase"] == "applied"
    assert plan["phases"][0]["items"][0]["resource_hint"] == RESOURCE_HINTS["other"]


def test_plan_within_phase_orders_must_before_should_before_nice():
    gap = {"gaps": [{"skill": "A", "category": "framework", "importance": "nice"},
                    {"skill": "B", "category": "framework", "importance": "must"},
                    {"skill": "C", "category": "framework", "importance": "should"}]}
    items = build_learning_plan(gap)["phases"][0]["items"]
    assert [i["topic"] for i in items] == ["B", "C", "A"]


def test_plan_empty_is_empty():
    assert build_learning_plan({}) == {"targetRole": "", "totalItems": 0, "phases": []}


def test_plan_never_invents_hours_or_urls():
    # The honesty rule: a hint describes a kind of exercise, never a number of hours
    # or a link the service cannot stand behind.
    plan = build_learning_plan(GAP)
    for phase in plan["phases"]:
        for item in phase["items"]:
            assert "http" not in item["resource_hint"]
            assert not any(ch.isdigit() for ch in item["resource_hint"])
