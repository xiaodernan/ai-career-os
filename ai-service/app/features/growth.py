"""Growth report (forward Epic 10.8): the composed view for the growth page.

One call that returns everything the growth screen needs -- readiness verdict, the
raw gap report, the salary benchmark, the learning plan, and the progress delta --
so the bridge and the frontend need a single endpoint instead of five.

The composition lives here as a pure function (not inline in the route) so its shape
is pinned by a test and by the forward-features contract gate: this is the object the
backend client and the frontend will be written against, so it must not drift
silently while it is still unwired.
"""

from app.features.learning import build_learning_plan
from app.features.progress import diff_progress
from app.features.readiness import compose as compose_readiness


def build_growth_report(gap: dict, salary: dict | None = None,
                        previous: dict | None = None) -> dict:
    return {
        "readiness": compose_readiness(gap, salary),
        "gap": gap,
        "salary": salary,
        "learningPlan": build_learning_plan(gap),
        "progress": diff_progress(previous, gap),
    }
