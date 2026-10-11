"""Learning Plan (forward Epic 10.5).

Turn a gap report (Epic 10.1) into a *phased* study plan. The gap report already
says which skills are missing; this adds the two things a plan needs to be usable:
an order that respects learning dependency (foundations before the framework that
sits on them, the framework before the deployment tooling), and a category-aware
starting point for each item.

Deterministic and honest: resource hints describe a *kind* of exercise, never an
invented URL, price or number of hours -- the service knows what is missing and
what it is worth, not how long it takes someone to learn it.
"""

# Learning phases, in dependency order. A skill's category decides its phase.
PHASES: dict[str, dict] = {
    "foundation": {"order": 0, "label": "Foundation",
                   "categories": {"cs_fundamentals", "language"}},
    "core": {"order": 1, "label": "Core stack",
             "categories": {"framework", "library", "data"}},
    "applied": {"order": 2, "label": "Applied & scale",
                "categories": {"devops", "cloud", "ai", "method", "tool"}},
}

RESOURCE_HINTS: dict[str, str] = {
    "language": "the language's official docs plus a few small exercises",
    "framework": "the framework's official tutorial and one small service you ship",
    "library": "the library's docs and a reproduction of its headline example",
    "data": "the store's own docs and one schema/indexing exercise on real data",
    "devops": "containerize an existing project and add a CI pipeline",
    "cloud": "deploy the project on the cloud's free tier and write the runbook",
    "ai": "read the primary paper and reproduce a minimal result",
    "cs_fundamentals": "a standard textbook chapter plus a set of practice problems",
    "method": "apply the method on the next project and write a one-page retro",
    "tool": "use the tool daily for a week on real work",
    "other": "the official docs and a small hands-on exercise",
}
_DEFAULT_HINT = RESOURCE_HINTS["other"]

_PRIORITY_ORDER = {"must": 0, "should": 1, "nice": 2}


def phase_of(category: str) -> str:
    for key, spec in PHASES.items():
        if category in spec["categories"]:
            return key
    return "applied"


def _item(skill: str, category: str, priority: str, resource_hint: str,
          note: str | None = None) -> dict:
    item = {"topic": skill, "category": category, "phase": phase_of(category),
            "priority": priority, "resource_hint": resource_hint}
    if note:
        item["note"] = note
    return item


def build_learning_plan(gap_report: dict) -> dict:
    items: list[dict] = []
    for g in gap_report.get("gaps") or []:
        cat = g.get("category") or "other"
        items.append(_item(g.get("skill", ""), cat, g.get("importance", "should"),
                           RESOURCE_HINTS.get(cat, _DEFAULT_HINT)))
    for p in gap_report.get("partial") or []:
        cat = p.get("category") or "other"
        items.append(_item(
            p.get("skill", ""), cat, p.get("importance", "should"),
            "write a project bullet that quantifies this skill",
            note="already evidenced in prose; make it a declared skill"))

    items.sort(key=lambda i: (PHASES[i["phase"]]["order"],
                              _PRIORITY_ORDER.get(i["priority"], 1),
                              i["topic"].lower()))
    phases = []
    for key, spec in sorted(PHASES.items(), key=lambda kv: kv[1]["order"]):
        group = [i for i in items if i["phase"] == key]
        if group:
            phases.append({"phase": key, "label": spec["label"], "items": group})
    return {"targetRole": gap_report.get("targetRole", ""),
            "totalItems": len(items), "phases": phases}
