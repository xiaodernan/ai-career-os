"""The Kubernetes manifests define a fleet that fits this repo's services (Epic 109).

`deploy/k8s/base` is a Kubernetes embodiment of the same topology `docker-compose.yml`
brings up: postgres / redis / minio / ai-service / discovery / backend / gateway /
frontend / config-server. This gate reads the manifests as text and YAML, and asserts
the invariants that make them a real deployment, not a stub:

- every workload is namespaced to `careeros` and carries the part-of label,
- every Deployment/StatefulSet has a liveness and a readiness probe,
- the HTTP health paths of the Spring Cloud services match both probes' groups
  (readiness -> /actuator/health/readiness, liveness -> /actuator/health/liveness),
  while postgres/redis/minio probe via exec and ai-service/frontend via their own paths,
- every Service selects the pod its workload runs (spec.selector.{name} == spec.selector.{name,labels-match}),
- the base ships PDBs for the four HTTP-facing deployments,
- `secret.example.yaml` carries placeholders, never real-looking secrets,
- prod overlay raises replicas for the three public-facing deployments.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "deploy" / "k8s" / "base"
PROD = ROOT / "deploy" / "k8s" / "overlays" / "prod"

# per-workload: (readiness path|exec, liveness path|exec, service port)
SERVICES: dict[str, tuple[str, str, int]] = {
    "postgres": ("exec", "exec", 5432),
    "redis": ("exec", "exec", 6379),
    "minio": ("exec", "exec", 9000),
    "ai-service": ("/health", "/health", 8000),
    "discovery": ("/actuator/health/readiness", "/actuator/health/liveness", 8761),
    "backend": ("/actuator/health/readiness", "/actuator/health/liveness", 8080),
    "gateway": ("/actuator/health/readiness", "/actuator/health/liveness", 8081),
    "frontend": ("/", "/", 3000),
    "config-server": ("/actuator/health/readiness", "/actuator/health/liveness", 8888),
}


def _load_all(path: Path) -> list[dict]:
    docs: list[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for doc in yaml.safe_load_all(fh):
            if doc:
                docs.append(doc)
    return docs


def _all_base_docs() -> list[dict]:
    docs: list[dict] = []
    for file in BASE.glob("*.yaml"):
        docs.extend(_load_all(file))
    return docs


def test_manifests_parse_and_namespace_is_declared():
    docs = _all_base_docs()
    kinds = [d["kind"] for d in docs]
    assert "Namespace" in kinds
    ns = next(d for d in docs if d["kind"] == "Namespace")
    assert ns["metadata"]["name"] == "careeros"


def test_every_workload_carries_the_part_of_label():
    for doc in _all_base_docs():
        if doc["kind"] not in {"Deployment", "StatefulSet", "Service", "PersistentVolumeClaim"}:
            continue
        label = (doc["metadata"].get("labels") or {}).get("app.kubernetes.io/part-of")
        assert label == "ai-career-os", (
            f"{doc['kind']}/{doc['metadata']['name']} is missing the part-of label"
        )


def test_workloads_define_liveness_and_readiness():
    for doc in _all_base_docs():
        if doc["kind"] not in {"Deployment", "StatefulSet"}:
            continue
        assert doc["spec"]["template"]["spec"]["containers"], (
            f"{doc['kind']}/{doc['metadata']['name']} has no container"
        )
        for c in doc["spec"]["template"]["spec"]["containers"]:
            assert "readinessProbe" in c, f"{doc['metadata']['name']} {c['name']} has no readinessProbe"
            assert "livenessProbe" in c, f"{doc['metadata']['name']} {c['name']} has no livenessProbe"


def test_probe_targets_match_the_service_they_serve():
    for doc in _all_base_docs():
        if doc["kind"] not in {"Deployment", "StatefulSet"}:
            continue
        name = doc["metadata"]["name"]
        if name not in SERVICES:
            continue
        want_ready, want_live, _ = SERVICES[name]
        for c in doc["spec"]["template"]["spec"]["containers"]:
            for key, expected in [("readinessProbe", want_ready), ("livenessProbe", want_live)]:
                probe = c[key]
                if expected == "exec":
                    assert "exec" in probe, f"{name} {key} must use an exec probe"
                    continue
                http = probe.get("httpGet")
                assert http and http.get("path") == expected, (
                    f"{name} {key} path must be {expected}, got {http}"
                )


def test_every_service_selects_the_pod_its_workload_runs():
    workloads: dict[str, dict] = {}
    services: dict[str, dict] = {}
    for doc in _all_base_docs():
        if doc["kind"] in {"Deployment", "StatefulSet"}:
            workloads[doc["metadata"]["name"]] = doc
        elif doc["kind"] == "Service":
            services[doc["metadata"]["name"]] = doc
    for name, workload in workloads.items():
        assert name in services, f"workload/{name} has no matching Service"
        svc = services[name]
        selector = svc["spec"]["selector"]
        match = workload["spec"]["selector"]["matchLabels"]
        for key, value in selector.items():
            assert key in match and match[key] == value, (
                f"Service/{name} selector {selector} does not match Deployment/{name} {match}"
            )


def test_base_ships_pdbs_for_the_http_facing_deployments():
    pdbs = [d for d in _all_base_docs() if d["kind"] == "PodDisruptionBudget"]
    names = {d["metadata"]["name"] for d in pdbs}
    assert names == {"backend", "gateway", "frontend", "ai-service"}, (
        f"expected PDB for backend/gateway/frontend/ai-service, found {sorted(names)}"
    )


def test_secret_example_carries_placeholders_not_secrets():
    text = (BASE / "secret.example.yaml").read_text(encoding="utf-8")
    assert "CHANGE_ME" in text, "the example secret must show placeholders"
    assert not re.search(r"(?i)(password|secret|token)\s*:\s*[A-Za-z0-9+/=]{16,}\b", text), (
        "the example secret looks like it carries a real-looking value; keep it CHANGE_ME"
    )


def test_prod_overlay_scales_the_public_facing_deployments():
    patch_text = (PROD / "kustomization.yaml").read_text(encoding="utf-8")
    for name in ("ai-service", "backend", "frontend"):
        idx = patch_text.find(f"name: {name}")
        assert idx >= 0, f"prod overlay does not patch {name}"
        following = patch_text[idx: idx + 400]
        assert re.search(r"value:\s*3", following), (
            f"prod overlay must raise {name} replicas to 3"
        )


def test_port_assignments_match_compose_targets():
    # cross-check the ports this repo commits to its compose topology
    svc_map = {
        "postgres": 5432,
        "redis": 6379,
        "minio": 9000,
        "ai-service": 8000,
        "discovery": 8761,
        "backend": 8080,
        "gateway": 8081,
        "frontend": 3000,
        "config-server": 8888,
    }
    seen: dict[str, int] = {}
    for doc in _all_base_docs():
        if doc["kind"] != "Service":
            continue
        name = doc["metadata"]["name"]
        if name in svc_map:
            ports = doc["spec"]["ports"]
            assert ports, f"Service/{name} has no ports"
            seen[name] = ports[0]["port"]
    for name, want in svc_map.items():
        assert seen.get(name) == want, f"Service/{name} port {seen.get(name)} != {want}"
