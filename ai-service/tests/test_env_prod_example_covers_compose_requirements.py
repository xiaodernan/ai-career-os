""".env.prod.example must define every variable docker-compose.prod.yml requires.

docker-compose.prod.yml fails fast with `${VAR:?message}` when a required variable
is missing from the `--env-file`. If `.env.prod.example` omits one of those names,
an operator following the example cannot produce a working `.env.prod`. This gate
reads the compose file's required (`${VAR:?}`) and optional-default (`${VAR:-}`)
variables and asserts the example defines each name (presence, not value).

Duplicates in the example are tolerated (it documents sections); we only require
that every compose variable appears at least once.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PROD = ROOT / "docker-compose.prod.yml"
EXAMPLE = ROOT / ".env.prod.example"


def _compose_vars(text: str) -> tuple[set[str], set[str]]:
    # Strip full-line YAML comments so documentation examples (e.g. ${VAR:?message})
    # are not mistaken for real variables.
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    body = "\n".join(lines)
    # ${NAME:?msg} => required; ${NAME:-default} => optional with default.
    required = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)\:\?", body))
    optional = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)\:-", body))
    # A var can appear in both forms across services; treat "ever required" as required.
    optional -= required
    return required, optional


def _example_keys(text: str) -> set[str]:
    keys = set()
    for line in text.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if m:
            keys.add(m.group(1))
    return keys


def test_env_prod_example_defines_all_compose_prod_variables() -> None:
    compose = COMPOSE_PROD.read_text(encoding="utf-8")
    example = EXAMPLE.read_text(encoding="utf-8")
    required, optional = _compose_vars(compose)
    keys = _example_keys(example)
    assert required, "compose prod must declare required vars (sanity)"
    missing_required = sorted(required - keys)
    missing_optional = sorted(optional - keys)
    assert not missing_required, (
        f".env.prod.example missing compose-required vars: {missing_required}"
    )
    assert not missing_optional, (
        f".env.prod.example missing compose vars (have defaults but must be documentable): {missing_optional}"
    )
