"""The dev edge and its registry tell the same story — and the prod edge does too.

The dev `docker-compose.yml` originally forced the gateway's `eureka` profile to
match prod. Eureka in the dev stack is one node with self-preservation OFF: it
cannot tell a dead service from a network hiccup, so a routine backend rebuild is
an unregister + re-register cycle the edge's Eureka client never picks up again
(no refresh interval in the dev config), and the `2026-11-12` experiment left the
edge answering `no servers available for service: backend` for 30+ minutes until
the gateway was recreated. The catalog/`cf6e873` merge called that a defect to fix
at the compose file; the 2026-11-12 recreation confirmed the cause, and the edge
reverted to the documented default single-node posture: the gateway simple
discovery client is the answer for `backend`, no registry involved.

That decision lives in the compose file, and nothing pinned it. A well-meaning
future merge that flips the dev edge back to `eureka` recreates the exact outage,
and only the incident report remembers why. A gate does not.

The pinned invariants, in both directions:
- the DEV edge carries NO profile (absence is the default single-node mode; any
  value opts into one) and DOES carry the documented `GATEWAY_BACKEND_URI`.
- the PROD edge and its backend carry `eureka` and agree on the registry zone —
  the shape prod actually offers: two long-lived registries with
  self-preservation ON.
- the lone dev registry evicts (self-preservation OFF) while the peer overlay
  preserves (true) — read straight off the two profile texts, not from memory.
- the dev edge's comment names the incident that forced the decision, so the
  reason cannot be accidentally deleted as "just clutter" without a citation.
"""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
DEV = ROOT / "docker-compose.yml"
PROD = ROOT / "docker-compose.prod.yml"
DEV_DISCOVERY = ROOT / "discovery" / "src" / "main" / "resources" / "application.yml"
DEV_DISCOVERY_PEER = ROOT / "discovery" / "src" / "main" / "resources" / "application-peer.yml"

DEV_TEXT = DEV.read_text(encoding="utf-8")
PROD_TEXT = PROD.read_text(encoding="utf-8")
BASE_TEXT = DEV_DISCOVERY.read_text(encoding="utf-8")
PEER_TEXT = DEV_DISCOVERY_PEER.read_text(encoding="utf-8")


def _services(path: Path) -> dict:
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict) and isinstance(doc.get("services"), dict), \
        f"{path.name} has no services mapping"
    return doc["services"]


def _env(service: dict) -> dict:
    env = service.get("environment", {})
    assert isinstance(env, dict), f"environment is not a mapping: {env!r}"
    return env


def _dev_gateway_section() -> str:
    """The comment block documents the posture; if the section exists but its prose is gone, the decision's reason is gone."""
    start = DEV_TEXT.index("gateway:")
    end = DEV_TEXT.index("\n  config-server:", start)
    return DEV_TEXT[start:end]


def test_the_files_are_readable_and_not_empty() -> None:
    for path in (DEV, PROD, DEV_DISCOVERY, DEV_DISCOVERY_PEER):
        text = path.read_text(encoding="utf-8")
        assert text.strip(), f"{path} is empty — this gate must not pass vacuously"
    assert "services:" in DEV_TEXT
    assert "services:" in PROD_TEXT


def test_the_dev_edge_runs_the_documented_single_node_posture() -> None:
    gateway = _services(DEV)["gateway"]
    env = _env(gateway)
    banned = ("SPRING_PROFILES_ACTIVE", "EUREKA_DEFAULT_ZONE")
    found = [key for key in banned if key in env]
    assert not found, (
        f"the dev gateway opts into {found}: any profile value re-locks the simple client out "
        "of the simple discovery answer, and this is the exact 2026-11-12 failure mode"
    )
    assert env.get("GATEWAY_BACKEND_URI") == "http://backend:8080", (
        "the dev edge's simple answer is the address the docs and the compose comment name "
        f"(backend:8080), got {env.get('GATEWAY_BACKEND_URI')!r}"
    )
    assert env.get("GATEWAY_HOSTNAME") == "gateway"


def test_the_dev_backend_still_registers_for_the_demo_but_the_edge_does_not_depend_on_it() -> None:
    # Deliberate asymmetry: the backend SHOWS UP in the dev two-node registry story
    # (it is the producer dashboard an operator opens), but the edge's routing must
    # never ask the registry for the backend. Pin that split so nobody "fixes" one
    # half of it into agreement by deleting the wrong one.
    backend = _services(DEV)["backend"]
    env = _env(backend)
    assert env.get("SPRING_PROFILES_ACTIVE") == "eureka", (
        "the dev backend registers in the demo registry; removing that is a product "
        "change, not a gate unblock -- report it rather than deleting the profile"
    )
    assert env.get("EUREKA_DEFAULT_ZONE") == "http://discovery:8761/eureka/"


def test_the_prod_edge_and_its_backend_answer_to_one_registry() -> None:
    for name in ("gateway", "backend"):
        env = _env(_services(PROD)[name])
        assert env.get("SPRING_PROFILES_ACTIVE") == "eureka", (
            f"the prod {name} must activate eureka — this is the shape the prod registry "
            "supports: two long-lived registries with self-preservation ON"
        )
        assert env.get("EUREKA_DEFAULT_ZONE") == "http://discovery:8761/eureka/", (
            f"the prod {name} points at a different zone than the prod discovery; a zone "
            "drift here is a routing-stays-down outage wearing a green health check"
        )
    prod_gateway = _services(PROD)["gateway"]
    assert "GATEWAY_BACKEND_URI" not in _env(prod_gateway), (
        "the prod edge must not carry the simple answer: under eureka the simple list is "
        "deliberately emptied by the profile, and shipping the variable alongside "
        "invites a merge to flip the profile while leaving the address behind"
    )


def test_the_lone_dev_registry_evicts_and_the_peer_preserves() -> None:
    # The base document keeps a lone registry client-off and evicting (a lone
    # registry cannot tell a dead service from a network hiccup); the peer
    # overlay brings the client on and restores self-preservation.
    assert "enable-self-preservation: ${EUREKA_SELF_PRESERVATION:false}" in BASE_TEXT, (
        "the default discovery profile lost self-preservation eviction — a stale dev node "
        "would be advertised forever"
    )
    assert "enable-self-preservation: ${EUREKA_SELF_PRESERVATION:true}" in PEER_TEXT, (
        "the peer profile lost self-preservation — the two-node registry would evict a "
        "healthy node on a network partition"
    )


def test_the_dev_edge_comment_records_the_forcing_incident() -> None:
    section = _dev_gateway_section()
    for needle in (
        "default single-node mode",
        "GATEWAY_BACKEND_URI",
        "self-preservation ON",
        "2026-11-12",
    ):
        assert needle in section, (
            f"the dev edge's posture comment lost {needle!r}; the reason a future merge "
            "must not 'standarize' this file to eureka is written there, not here"
        )
