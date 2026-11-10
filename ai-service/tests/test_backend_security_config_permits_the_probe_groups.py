"""The Spring Cloud probes are public for the orchestrator (Epic 112).

Kubernetes probes cannot carry a user JWT, so `/actuator/health/liveness` and
`/actuator/health/readiness` must be permitAll in the backend's security chain, like
`/actuator/health` and `/actuator/prometheus`. The split also depends on the backend's
`probes.enabled` flag being set and the groups mapping readiness to the readinessState
(not the availability of dependencies). This gate reads the config as text and holds the
contract in place.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECURITY = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "config" / "SecurityConfig.java"
APP = ROOT / "backend" / "src" / "main" / "resources" / "application.yml"


def test_backend_security_config_permits_the_probe_groups():
    src = SECURITY.read_text(encoding="utf-8")
    assert "/actuator/health/liveness" in src, (
        "backend must permit the liveness probe path for the orchestrator, like it permits "
        "/actuator/health itself"
    )
    assert "/actuator/health/readiness" in src, (
        "backend must permit the readiness probe path for the orchestrator, like it permits "
        "/actuator/health itself"
    )


def test_backend_enables_probes_and_splits_the_groups():
    text = APP.read_text(encoding="utf-8")
    assert "probes:" in text and "enabled: true" in text, (
        "backend must enable the liveness/readiness probe groups"
    )
    assert "readiness:" in text and "readinessState" in text, (
        "readiness group must track readinessState (application lifecycle), not dependency reachability — "
        "dependency checks live in /api/v1/health"
    )
    assert "liveness:" in text and "livenessState" in text, (
        "liveness group must track livenessState (application lifecycle)"
    )


def test_probe_paths_match_kubernetes_manifests():
    # the K8s backend probes use /actuator/health/{readiness,liveness}; the security chain
    # permits those paths and the groups report on the application lifecycle, not the DB.
    k8s = ROOT / "deploy" / "k8s" / "base" / "backend.yaml"
    manifest = k8s.read_text(encoding="utf-8")
    assert "/actuator/health/liveness" in manifest
    assert "/actuator/health/readiness" in manifest
