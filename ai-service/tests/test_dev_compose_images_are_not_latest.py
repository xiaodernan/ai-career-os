"""Dev compose pulled images should not use floating `:latest` (or untagged).

Same reproducibility expectation as prod for pulled `image:` references. Build
contexts are excluded.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEV = ROOT / "docker-compose.yml"


def test_dev_compose_pulled_images_are_pinned() -> None:
    text = DEV.read_text(encoding="utf-8")
    bad = []
    for i, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        m = re.match(r"image:\s*([^\s#]+)", stripped)
        if not m:
            continue
        image = m.group(1).strip('"').strip("'")
        if "@sha256:" in image:
            continue
        name_part = image.rsplit("/", 1)[-1]
        if ":" not in name_part:
            bad.append((i, image, "missing tag"))
        elif image.endswith(":latest"):
            bad.append((i, image, "uses :latest"))
    assert not bad, f"dev compose pulled images must use pinned tags: {bad}"
