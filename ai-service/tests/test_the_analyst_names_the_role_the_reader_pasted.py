"""The role a paste names itself: the analyst's blank title must not become an invented one.

Measured on the running stack on 2026-10-25, against the database the product is actually serving:
80 jobs sit in `jobs` titled **"Imported job"**, every one of them under the same company row
**"Unknown company"**, one per user, and every one of them made from the *same* 328-character paste.
That paste begins:

    Senior Backend Engineer - Agent Platform

so the role the reader pasted was there, in the first line, and the tracker filed it under a name the
software made up. `job_jds.parsed` says how: **not one of the 171 stored analyst answers carries a
`title` key at all**.

Two declarations make a blank the normal answer rather than a failure. The analyze prompt's own
skeleton draws `"title":""`, and `JDAnalysis` defaults `title: str = ""` — so "I found no role here"
is schema-conformant, and the case that reached the database (the mock provider's JD branch, the
offline stack `docker compose --profile app` starts) simply left the key out. `Json.strOr(parsed,
"title", "Imported job")` then folds absent, null and blank into the same fabricated name, and
`JobService.persistImport` writes it as a row the reader will keep.

So the capture moves next to the one this module already performs for skills. `_backfill_skills`
recovers from `raw_text` whatever the model missed; `_backfill_identity` recovers the role from the
same text the reader pasted, which is not a guess about their posting but a line of it. It is
deliberately one-sided: a **company is never recovered**, because nothing in a posting's shape names
an employer reliably, and inventing one files a real person's application under a business that does
not exist. That half stays the caller's decision, and this file's fourth case holds the producer to
its side of the line.
"""

from __future__ import annotations

import ast
import asyncio
import json
import re
from pathlib import Path

from app.core.ai import wrap_untrusted
from app.features.jd_analyze import (
    SYSTEM,
    TITLE_MAX_CHARS,
    _backfill_identity,
    _backfill_skills,
)
from app.features.schemas import JDAnalysis
from app.providers.base import LLMMessage, LLMRequest
from app.providers.llm.mock import MockProvider

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parents[1]

ANALYST_CALLER = "backend/src/main/java/com/careeros/job/service/JobService.java"

# The paste every one of the 80 rows was made from, copied out of `job_jds.raw_text` verbatim.
MEASURED_PASTE = (
    "Senior Backend Engineer - Agent Platform\n"
    "We are hiring a senior backend engineer to build our agent platform.\n"
    "Requirements: 5+ years of Java or Python, Spring Boot, PostgreSQL, Redis,\n"
    "Kafka, Kubernetes. Experience with LLM applications is a strong plus.\n"
    "Responsibilities: design and ship APIs, own the matching pipeline, mentor.\n"
)
MEASURED_ROLE = "Senior Backend Engineer - Agent Platform"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8").replace("\r\n", "\n")


def analyst_answer(raw_text: str) -> dict:
    """One JD analysis through the seam the endpoint uses: the mock provider, the real prompt.

    Not a call to `analyze_jd`, because that goes through `ask_json` and the configured provider --
    which is a real API in this environment and a network call in CI. This is the same request the
    feature builds, answered by the provider the offline stack starts, and then held to the same two
    backfills, so it grades the bytes that shipped rather than a stub of my own.
    """
    req = LLMRequest(
        messages=[LLMMessage("system", SYSTEM),
                  LLMMessage("user", wrap_untrusted("JOB_DESCRIPTION", raw_text[:20000]))],
        temperature=0.0, max_tokens=3000)
    reply = asyncio.run(MockProvider().complete(req)).text
    out = json.loads(reply)
    return _backfill_identity(_backfill_skills(out, raw_text), raw_text)


def _module_strings(rel: str) -> set[str]:
    """Every string literal a module carries, its own documentation aside.

    The docstrings here quote the fabricated names to explain what they are refusing, so a plain text
    search over the file would report the prose as if it were behaviour -- and an absence claim has to
    name the spelling it looked for, not the whole file.
    """
    tree = ast.parse(read(rel), filename=rel)
    docstrings = set()
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        body = getattr(node, "body", [])
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            docstrings.add(id(body[0].value))
    return {n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings}


def test_the_measured_paste_names_its_own_role():
    """The 80 rows, undone: the reader's first line is the title, and nothing is invented."""
    assert MEASURED_PASTE.splitlines()[0] == MEASURED_ROLE, \
        "the fixture stopped being the paste that was measured; re-read `job_jds.raw_text`"
    assert _backfill_identity({}, MEASURED_PASTE)["title"] == MEASURED_ROLE

    # The names the caller fabricates are not strings this module can produce at all.
    invented = _module_strings("ai-service/app/features/jd_analyze.py")
    assert "Imported job" not in invented and "Unknown company" not in invented, \
        ("the recovery is producing a fabricated row name itself, which is the defect this file "
         "exists for")


def test_a_role_the_model_found_is_never_rewritten():
    """The capture fills a blank; it does not second-guess an answer that already named the job."""
    out = _backfill_identity({"title": "Staff Platform Engineer"}, MEASURED_PASTE)
    assert out["title"] == "Staff Platform Engineer", \
        "the model's own answer was replaced by a line of the paste"
    # A named title that merely needs trimming is still the model's answer, not a blank to fill.
    assert _backfill_identity({"title": "  Backend Engineer  "}, MEASURED_PASTE)["title"] == \
        "  Backend Engineer  "


def test_absent_null_and_blank_are_the_same_answer():
    """Three spellings of "the analyst named nothing", one recovery.

    `parsed` comes out of jsonb and a key there can be present and null, which is the shape that has
    crashed a caller before (`wrap_untrusted`'s own docstring names it). A recovery that read only the
    missing key would leave the null and the blank landing as "Imported job", and the fold in
    `Json.strOr` treats all three alike.
    """
    recovered = MEASURED_ROLE
    assert _backfill_identity({}, MEASURED_PASTE)["title"] == recovered
    assert _backfill_identity({"title": None}, MEASURED_PASTE)["title"] == recovered
    assert _backfill_identity({"title": "   "}, MEASURED_PASTE)["title"] == recovered
    assert _backfill_identity({"title": ""}, MEASURED_PASTE)["title"] == recovered


def test_no_employer_is_invented():
    """The other half of the row, refused on purpose.

    A company name has no shape to recover -- it is not the first line of a posting -- and a wrong
    one is worse than a blank: it files the reader's application under a business that does not exist,
    and `companies.name` is `NOT NULL UNIQUE` and not user-scoped, so every paste this happened to
    converges onto one shared row (measured: 80 jobs, one company).
    """
    for out in ({}, {"company": ""}, {"company": None}):
        filled = _backfill_identity(dict(out), MEASURED_PASTE)
        assert not filled.get("company"), \
            f"an employer was written where the analyst named none: {filled}"
        assert filled.get("title") == MEASURED_ROLE, \
            "the role stopped being recovered while the employer was being left alone"
    assert "Unknown company" not in read("ai-service/app/features/jd_analyze.py")


def test_the_line_is_cleaned_and_bounded():
    """Decoration is not part of a role's name, and one line is not a heading paragraph.

    A paste carried into the box from a job board arrives with markdown and the wrapping the reader
    copied, so the marks come off and the whitespace collapses; a first line longer than the bound is
    cut at a word rather than mid-word, because the row's title is read by a person.
    """
    assert _backfill_identity({}, "#  Senior Engineer \nrest")["title"] == "Senior Engineer"
    assert _backfill_identity({}, "* Backend Engineer |\n")["title"] == "Backend Engineer"
    assert _backfill_identity({}, "Two   lines\tabout\none role")["title"] == "Two lines about"

    long = "Senior Site Reliability Engineer " + "platform " * 20
    title = _backfill_identity({}, long)["title"]
    assert len(title) <= TITLE_MAX_CHARS, f"the row's title is {len(title)} characters long"
    assert title == "Senior Site Reliability Engineer platform platform platform platform platform", \
        ("a title over the bound was cut mid-word instead of at the last space, which is how a row "
         "ends up called 'platfor'")


def test_a_paste_with_no_role_line_is_left_to_the_caller():
    """No recovery is the honest answer when the text says nothing -- and it must not crash either.

    The floor here is what keeps the capture from becoming its own fabricated name: a paste of rules,
    digits and blank lines has no role in it, the key stays as it was, and the caller's fallback is
    still the thing that decides.
    """
    junk = "\n\n===\n----\n1234567890\n   \n"
    assert _backfill_identity({}, junk) == {}, "a title was invented out of decoration"
    assert _backfill_identity({"title": ""}, junk)["title"] == ""
    # Hostile and empty inputs: the caller's shape, not an exception. An answer that was not a mapping
    # at all becomes one carrying the recovered role, which is what `_backfill_skills` already does
    # with `rawTextLength` for the same input.
    assert _backfill_identity(None, MEASURED_PASTE) == {"title": MEASURED_ROLE}
    assert _backfill_identity(None, junk) == {}
    assert _backfill_identity({}, "") == {}
    assert _backfill_identity({}, None) == {}


def test_a_decoration_first_line_does_not_end_the_scan():
    """The scan takes the first line that says something, not line zero.

    A copy of a posting often opens with a rule or a repeated heading, and a capture that stopped at
    the first newline would leave that paste landing as "Imported job" for the reader who did paste a
    role. A line of punctuation carries no letter in any script, which is what the scan looks for.
    """
    assert _backfill_identity({}, "=========\n# Product Engineer\nBody")["title"] == "Product Engineer"
    # A Chinese posting is a posting: a role with no ASCII letter is still a role.
    assert _backfill_identity({}, "后端高级工程师 - 智能平台\n更多")["title"] == "后端高级工程师 - 智能平台"


def test_the_offline_stack_that_landed_the_80_rows_now_lands_a_named_one():
    """The whole path, not the helper: prompt, provider, both backfills, one paste.

    This is the case that grades the deployment that produced the defect. The container the product
    is running in answers `{"llm_provider": "mock"}`, and the mock's JD branch left out `title` and
    `company` while its own prompt declares both -- which is why every paste on the offline stack
    became the same two fabricated names. The mock names the employer (as its resume branch already
    names "Mock Corp"), leaves the role blank for the capture above, and the capture fills it from the
    paste, so neither fabricated string is what a reader's row carries now.
    """
    out = analyst_answer(MEASURED_PASTE)
    assert out["title"] == MEASURED_ROLE, \
        f"the offline stack still lands a paste under something other than its own role: {out['title']!r}"
    assert out["company"] == "Mock Corp", \
        ("an unnamed employer folds into the caller's placeholder, and 80 users share one company row")
    assert out["title"] != "Imported job" and out["company"] != "Unknown company"
    # The skills capture is still doing its job beside the identity one: the two backfills compose.
    assert {"requiredSkills", "preferredSkills"} <= set(out) and out["rawTextLength"] == \
        len(MEASURED_PASTE)


def test_a_blank_title_is_still_what_the_analyst_is_asked_to_return():
    """The premise, held to the two artifacts that state it.

    Nothing here is a fix of the prompt: the capture exists *because* a blank title is conformant, and
    it is the fold in `Json.strOr` that turns it into a name. If the prompt or the model stops
    declaring the key the premise has moved and this file has to be re-read rather than deleted.
    """
    assert re.search(r'"title"\s*:\s*""', SYSTEM), \
        "the analyze prompt no longer draws a blank title, so an empty answer is a failure to report"
    field = JDAnalysis.model_fields["title"]
    assert field.default == "", \
        f"`JDAnalysis.title` no longer defaults to blank (it defaults to {field.default!r})"
    caller = read(ANALYST_CALLER)
    assert re.search(r'Json\.strOr\(parsed,\s*"title",\s*"Imported job"\)', caller), \
        ("the caller stopped folding the blank -- which is good news, and this file's claims about "
         "what a blank becomes need re-reading")
