"""The compose files must parse — the gate the unparseable-build-args defect needed.

Commit cbbb90f (`feat(observability): bake build SHA into health`) wrote a literal
`\\n` into both compose files' build-arg blocks: four lines were joined into one
(`APP_BUILD_SHA: \\n    container_name: careeros-ai`), so every `docker compose`
invocation died at YAML parse — `build`, `config`, `up`, everything. Nothing in
CI noticed: the deploy-doc censuses read ports, variables and image tags, not
syntax, and the containers were already running under old images, so the broken
file executed for who knows how long. This file is that missing check.

What it holds, on both files (dev + prod):

* both parse as YAML to a mapping carrying `services`;
* every service's `build.args` (env interpolated or folded) is a mapping of
  well-formed scalar entries — an entry whose value contains a literal newline
  is the exact defect this gate was born from, each backlash respected;
* every build-arg key exists in the service's Dockerfile as an `ARG`, so an arg
  cannot name a variable the image never bakes (a silent no-op the Epic 78
  bake-its-own-SHA path could otherwise regress into);
* the services that the dev stack validates end-to-end (`ai-service`, `backend`,
  `frontend`) keep carrying the `APP_BUILD_SHA` arg.

The parser is deliberately PyYAML, not a hand-written reader: the defect was a
valid-looking file shape, and a real YAML round trip is what separates "looks raw
enough to pass" from "actually composes".
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "docker-compose.yml"
PROD = ROOT / "docker-compose.prod.yml"


def _args_map(compose_path: Path) -> dict[str, dict[str, str]]:
    doc = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    assert isinstance(doc, dict), f"{compose_path.name} does not parse to a mapping"
    services = doc.get("services")
    assert isinstance(services, dict), f"{compose_path.name} has no services map"
    out: dict[str, dict[str, str]] = {}
    for name, service in services.items():
        if not isinstance(service, dict):
            continue
        build = service.get("build")
        if not isinstance(build, dict):
            continue
        args = build.get("args")
        if args is None:
            continue
        assert isinstance(args, dict), f"{compose_path.name}:{name} build.args is not a mapping: {args!r}"
        out[name] = args
    return out


def _arg_values_well_formed(name: str, args: dict[str, object]) -> None:
    for key, value in args.items():
        assert isinstance(value, (str, int, float, bool)) or value is None, (
            f"service {name}: build arg {key!r} carries a non-scalar value {value!r}")
        text = "" if value is None else str(value)
        assert "\\n" not in text, f"service {name}: build arg {key!r} carries a literal newline: {text!r}"
        assert "\n" not in text, f"service {name}: build arg {key!r} contains an actual newline (must be single-line YAML)"


def _dockerfile_args(service_name: str) -> set[str]:
    rel = {"ai-service": "ai-service", "backend": "backend", "frontend": "frontend"}.get(service_name)
    dockerfile = ROOT / rel / "Dockerfile"
    text = dockerfile.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*ARG\s+(\w+)", text, re.M)), text


def test_both_compose_files_parse_to_a_services_mapping() -> None:
    services_dev = yaml.safe_load(DEV.read_text(encoding="utf-8"))
    services_prod = yaml.safe_load(PROD.read_text(encoding="utf-8"))
    for name, doc in (("docker-compose.yml", services_dev), ("docker-compose.prod.yml", services_prod)):
        assert isinstance(doc, dict), f"{name} did not parse to a YAML mapping"
        assert isinstance(doc.get("services"), dict) and doc["services"], (
            f"{name} has no services map — compose would refuse or silently do nothing")


def test_every_build_arg_is_a_well_formed_scalar() -> None:
    for compose_path in (DEV, PROD):
        for service_name, args in _args_map(compose_path).items():
            _arg_values_well_formed(service_name, args)


def test_every_arg_it_declares_is_baked_by_the_dockerfile() -> None:
    # The exact regression Epic 78 shipped: an arg named by compose that no Dockerfile bakes.
    for compose_path in (DEV, PROD):
        for service_name, args in _args_map(compose_path).items():
            if service_name not in ("ai-service", "backend", "frontend"):
                continue
            declared, _ = _dockerfile_args(service_name)
            for key in args:
                assert key in declared, (
                    f"{compose_path.name}:{service_name} bakes build arg {key!r} the Dockerfile never declares: "
                    f"{sorted(declared)}")


def test_the_two_app_services_carry_app_build_sha() -> None:
    for compose_path in (DEV, PROD):
        args_by_service = _args_map(compose_path)
        # The frontend image does not bake a build SHA (no ARG for it in its Dockerfile); the
        # backend and ai-service images do, and both must keep declaring it (Epic 78).
        for service in ("ai-service", "backend"):
            if service not in args_by_service:
                continue  # a compose without a build section cannot declare the arg either
            assert "APP_BUILD_SHA" in args_by_service[service], (
                f"{compose_path.name}:{service} lost APP_BUILD_SHA — the Epic 78 "
                "deploy transparency contract is empty for this service")
