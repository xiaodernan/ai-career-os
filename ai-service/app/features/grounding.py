"""The shared verifier's digit discipline (Epic 323).

Every grounded-verify node in this service reads the same way: collect the
digit-runs in a text, keep a candidate only when at least one of them already
appears in the snapshot it was handed. Written once here so the three callers
(editorial, counsel, offer-narrative) cannot drift apart.

The normalization is deliberately generous about *glyphs* and strict about
*existence*: a number spelled with full-width digits (１个申请), a trailing
percent sign, or a thousands separator (300,000) is still the number the
snapshot carries (`1`, `0.0`, `300000`) -- an honest sentence must never be
dropped because of how it was typeset. What is never normalized: a digit that
the snapshot does not contain, or a digit smuggled in by reformatting a date.
"""

import json
import re
import unicodedata

_DIGITS = re.compile(r"\d+(?:[.,]\d+)*%?")


def digit_runs(text) -> set[str]:
    """Every digit-run in ``text``, Unicode-folded and separator-stripped."""
    raw = _DIGITS.findall(unicodedata.normalize("NFKC", str(text)))
    out: set[str] = set()
    for r in raw:
        if r.endswith("%"):
            r = r[:-1]
        r = r.replace(",", "")   # 300,000 -> 300000 (the snapshot spells money bare)
        if r:
            out.add(r)
    return out


def snapshot_digits(snapshot) -> set[str]:
    """Digit-runs present anywhere in the snapshot (as JSON bytes)."""
    return digit_runs(json.dumps(snapshot, ensure_ascii=False, default=str))


def grounded(candidate: str, digits: set[str]) -> bool:
    """True when the candidate cites at least one digit that exists in the snapshot."""
    runs = digit_runs(str(candidate or ""))
    return bool(runs) and any(r in digits for r in runs)
