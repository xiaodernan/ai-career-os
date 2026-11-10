"""The topology page must read the fleet the backend writes (Epic 101).

`/api/v1/system/topology` is answered by `ServiceTopologyService.report()` as a nest of
`Map`s built with `put`, and the browser draws it through the `ServiceTopology` interface
in `lib/api/types.ts`. Neither side imports the other: the backend is Java, the page is
TypeScript, and the wire between them is JSON with no shared schema. A key renamed on
either side -- `instanceId` becoming `id`, `registry` becoming `mode` -- would leave the
card rendering `undefined` while both modules' own tests stayed green, because each test
asserts against the side it lives on.

This gate is the noticing, in the same shape as `test_the_two_doors_agree.py`: it reads
both sources as text and compares the vocabulary they actually use. The set of keys the
backend puts must equal the set of fields the page declares, and the registry-mode words
the backend writes must be the words the page branches on. It deliberately compares sets
rather than order: the answer is a map, and the contract is which names travel, not the
order a `LinkedHashMap` happened to insert them.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SERVICE = ROOT / "backend/src/main/java/com/careeros/system/ServiceTopologyService.java"
FRONTEND_TYPES = ROOT / "frontend/src/lib/api/types.ts"
FRONTEND_CARD = ROOT / "frontend/src/components/monitoring/service-topology.tsx"


def _backend_put_keys() -> set[str]:
    source = BACKEND_SERVICE.read_text(encoding="utf-8")
    assert "Map<String, Object> report()" in source, (
        "ServiceTopologyService no longer declares report(); this gate is reading a file "
        "that stopped answering the topology endpoint"
    )
    keys = set(re.findall(r'\.put\("([^"]+)"', source))
    assert keys, "no put() key found in ServiceTopologyService; the parse matched nothing"
    return keys


def _frontend_topology_fields() -> set[str]:
    source = FRONTEND_TYPES.read_text(encoding="utf-8")
    block = re.search(r"export interface ServiceTopology \{(.*?)\n\}", source, re.DOTALL)
    assert block, "types.ts no longer declares a ServiceTopology interface"
    fields = set(re.findall(r"(\w+):", block.group(1)))
    assert fields, "no field found in the ServiceTopology interface; the parse matched nothing"
    return fields


def test_the_page_reads_exactly_the_keys_the_backend_writes():
    backend = _backend_put_keys()
    frontend = _frontend_topology_fields()
    assert backend == frontend, (
        "the topology answer and the page disagree on their vocabulary: "
        f"the backend writes {sorted(backend - frontend)} that the page never declares, "
        f"and the page reads {sorted(frontend - backend)} that the backend never puts; "
        "a renamed key renders as undefined while both sides' own tests stay green"
    )


def test_the_topology_carries_instance_metadata_for_build_identity():
    source = BACKEND_SERVICE.read_text(encoding="utf-8")
    assert 'row.put("metadata"' in source, (
        "the topology report stopped publishing instance metadata; the operator loses "
        "build-sha at the registry without noticing"
    )
    page = FRONTEND_TYPES.read_text(encoding="utf-8")
    assert "metadata: Record<string, string>;" in page, (
        "the page's ServiceTopology no longer declares metadata; the backend's "
        "build-shas would cross the wire with no type to receive them"
    )


def test_the_registry_words_the_page_branches_on_are_the_words_the_backend_writes():
    source = BACKEND_SERVICE.read_text(encoding="utf-8")
    # The mode is the ternary `acceptsProfiles(...) ? "eureka" : "configuration"`.
    written = set(re.findall(r'\?\s*"([^"]+)"\s*:\s*"([^"]+)"', source))
    assert written, "ServiceTopologyService no longer chooses the registry mode with a ternary"
    backend_words = {word for pair in written for word in pair}

    card = FRONTEND_CARD.read_text(encoding="utf-8")
    branched = set(re.findall(r'data\.registry\s*===\s*"([^"]+)"', card))
    assert branched, "the card no longer branches on data.registry; this gate is now vacuous"
    assert branched <= backend_words, (
        f"the card branches on registry words {sorted(branched - backend_words)} the backend "
        f"never writes (it writes {sorted(backend_words)}); the badge would fall through to "
        "the wrong label for a mode the deployment can actually be in"
    )