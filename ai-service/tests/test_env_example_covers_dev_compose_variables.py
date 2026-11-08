""".env.example must define variables referenced by docker-compose.yml.

Dev compose interpolates `${VAR:-...}` / `${VAR}` from the environment (and
`.env` when used). If `.env.example` omits a referenced name, the example no
longer documents a working dev configuration. This gate reads docker-compose.yml
(ignoring full-line comments) and asserts every interpolated variable appears in
`.env.example` at least once.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSE_DEV = ROOT / "docker-compose.yml"
EXAMPLE = ROOT / ".env.example"


def _compose_vars(text: str) -> set[str]:
    lines = [ln for ln in text.splitlines() if not ln.lstrip().startswith("#")]
    body = "\n".join(lines)
    # Match ${NAME} / ${NAME:-...} / ${NAME:?...}; ignore escaped $$ (compose pass-through).
    return set(re.findall(r"(?<!\$)\$\{([A-Z][A-Z0-9_]*)[:}]", body))


def _example_keys(text: str) -> set[str]:
    keys = set()
    for line in text.splitlines():
        m = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if m:
            keys.add(m.group(1))
    return keys


def test_env_example_defines_all_dev_compose_variables() -> None:
    compose = COMPOSE_DEV.read_text(encoding="utf-8")
    example = EXAMPLE.read_text(encoding="utf-8")
    vars_ = _compose_vars(compose)
    keys = _example_keys(example)
    assert vars_, "dev compose must interpolate vars (sanity)"
    missing = sorted(vars_ - keys)
    assert not missing, f".env.example missing docker-compose.yml variables: {missing}"
