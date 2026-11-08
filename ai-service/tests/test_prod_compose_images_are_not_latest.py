"""Production compose must not use floating `:latest` (or untagged) images.

`docker-compose.prod.yml` should reference reproducible image tags for pulled
images. `:latest` and missing tags make deployments non-deterministic. Services
that use `build:` (not `image:`) are excluded.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROD = ROOT / "docker-compose.prod.yml"


def test_prod_compose_pulled_images_are_pinned() -> None:
    text = PROD.read_text(encoding="utf-8")
    # Match `image: <name>` lines (ignore comments).
    bad = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        m = re.match(r"image:\s*([^\s#]+)", stripped)
        if not m:
            continue
        image = m.group(1).strip('"').strip("'")
        # Allow digests (name@sha256:...). Otherwise require an explicit tag.
        if "@sha256:" in image:
            continue
        if ":" not in image.rsplit("/", 1)[-1]:
            bad.append((i, image, "missing tag"))
        elif image.endswith(":latest"):
            bad.append((i, image, "uses :latest"))
    assert not bad, f"prod compose pulled images must use pinned tags (not :latest/untagged): {bad}"
