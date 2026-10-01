"""`features/cover_letter._build_prompt` — the conditional assembly, in isolation.

The function is pure by design ("no LLM/DB ... unit-testable in isolation"), and it is
where the cover-letter flow broke: `company.get("overview", "")` returned `None` for a
company whose `overview` is present-and-null, which is every company created from a
pasted JD. The request died with `'NoneType' object has no attribute 'replace'` before
it ever reached a model.

Only the branches that can silently produce a wrong prompt, or no prompt at all, are
pinned here — the prompt text itself is a model's input, not a contract.
"""

from app.features.cover_letter import _build_prompt


def _prompt(**over):
    kwargs = dict(
        resume_structured={"profile": {"name": "Ada", "headline": "Backend engineer"}},
        jd={"title": "Backend Engineer", "company": "Fallback Co", "requiredSkills": []},
        company=None,
        goal="",
        context_block="EVIDENCE",
        tone="",
        length="",
        mode="default",
        previous="",
    )
    kwargs.update(over)
    return _build_prompt(**kwargs)


def test_a_present_null_overview_does_not_take_the_feature_down():
    """The regression: null is not the same as absent, and `.get(k, "")` cannot tell."""
    prompt = _prompt(company={"name": "Acme", "overview": None})
    assert "COMPANY: Acme" in prompt
    # Fenced as empty rather than omitted — the label still tells the model what is missing.
    assert "<<<BEGIN UNTRUSTED COMPANY>>>" in prompt
    assert "<<<END UNTRUSTED COMPANY>>>" in prompt


def test_an_absent_company_falls_back_to_the_job_description():
    assert "COMPANY: Fallback Co" in _prompt(company=None)
    # No company means no overview line at all, not an empty one.
    assert "COMPANY OVERVIEW" not in _prompt(company=None)


def test_empty_facts_are_dropped_rather_than_sent_blank():
    """A blank CAREER GOAL line reads as an instruction to invent one."""
    assert "CAREER GOAL" not in _prompt(goal="")
    assert "CAREER GOAL: switch to platform work" in _prompt(goal="switch to platform work")


def test_a_null_overview_still_yields_the_company_name():
    """Guards the ordering: the name line must not depend on the overview surviving."""
    prompt = _prompt(company={"name": "Acme", "overview": None})
    assert prompt.index("COMPANY: Acme") < prompt.index("COMPANY OVERVIEW")
