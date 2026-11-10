"""The resilience card must read the breaker state the backend writes (Epic 105).

`/api/v1/system/resilience` is answered by `ResilienceStatusService.report()` as a map
built with `put`, and the browser draws it through `ServiceResilience` / `CircuitBreakerStatus`
in `frontend/src/lib/api/types.ts`. A renamed key would render as undefined while both sides'
own tests stayed green. This gate compares the vocabulary across the wire.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SERVICE = ROOT / "backend/src/main/java/com/careeros/system/ResilienceStatusService.java"
FRONTEND_TYPES = ROOT / "frontend/src/lib/api/types.ts"


def _backend_put_keys() -> set[str]:
    source = BACKEND_SERVICE.read_text(encoding="utf-8")
    assert "Map<String, Object> report()" in source, (
        "ResilienceStatusService no longer declares report(); this gate is reading a file "
        "that stopped answering the resilience endpoint"
    )
    keys = set(re.findall(r'\.put\("([^"]+)"', source))
    assert keys, "no put() key found in ResilienceStatusService; the parse matched nothing"
    return keys


def _frontend_interface_fields(name: str) -> set[str]:
    source = FRONTEND_TYPES.read_text(encoding="utf-8")
    block = re.search(rf"export interface {re.escape(name)} \{{(.*?)\n\}}", source, re.DOTALL)
    assert block, f"types.ts no longer declares a {name} interface"
    fields = set(re.findall(r"(\w+)\??:", block.group(1)))
    assert fields, f"no field found in the {name} interface; the parse matched nothing"
    return fields


def test_the_resilience_answer_and_page_agree_on_vocabulary():
    backend = _backend_put_keys()
    frontend = _frontend_interface_fields("ServiceResilience") | _frontend_interface_fields("CircuitBreakerStatus")
    assert backend == frontend, (
        "the resilience answer and the page disagree on their vocabulary: "
        f"the backend writes {sorted(backend - frontend)} that the page never declares, "
        f"and the page reads {sorted(frontend - backend)} that the backend never puts"
    )
