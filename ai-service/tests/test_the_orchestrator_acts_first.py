"""The orchestrator's system prompt answers the real-model baseline it was measured against.

The first real-provider run (qwen2.5:7b on Ollama,
vals/reports/20261008-010504_real-agent.md) scored tool_precision 0.93 and
tool_recall 0.30, and the failure was not a wrong tool -- it was no tool. On
s-01 ("help me find AI Agent roles for me") and s-02 ("which remote backend
roles are there?") the orchestrator answered with a question -- it asked for a resume
before searching, because CAREER_SYSTEM's rule 2 told it to name the next step
whenever "required data is missing", and nothing marked search_jobs as needing
no personal data at all. A request the search route can serve in full was answered
with homework.

The prompt now says the opposite in the same two slots, and a prompt is exactly the
kind of edit that regresses silently -- no test failed before the change, and none
would fail if someone later "tidied" the rules back toward caution. These cases
pin the behaviour the baseline asked for, per rule, so a regression here is red
before the next real run rather than after it:

* rule 2 leads with *act first* -- a vague request is a call, and only a datum the
  tool genuinely requires may be asked for (matching/tailoring need a resume; job
  search does not);
* rule 3 puts search_jobs ahead of every other step for role requests, including
  personalised ones ("jobs that suit me"), because the list beats the question;
* the properties the baseline scored well stay: grounding (rule 1, no invented
  experience/companies/results), delegation (rule 4), style (rule 5), and the
  UNTRUSTED data-not-instructions rule (rule 6);
* the rules stay numbered 1..6 in order -- the fix rewrote rules 2 and 3 in place
  rather than appending, and a renumber or a dropped rule is a re-edit nobody
  reviewed.

What is NOT here: any claim about model behaviour. Whether these words move
	ool_recall is the next real-provider run's verdict, not a unit test's.
"""

import re

from app.agents.orchestrator import CAREER_SYSTEM


def _rules() -> dict[int, str]:
    """Split the prompt's numbered rules; only a N. at line start opens a rule."""
    rules: dict[int, str] = {}
    current = None
    for line in CAREER_SYSTEM.splitlines():
        m = re.match(r"^(\d+)\.\s+(.*)$", line.strip())
        if m:
            current = int(m.group(1))
            rules[current] = m.group(2)
        elif current is not None:
            rules[current] += " " + line.strip()
    return rules


def test_rule_2_demands_acting_before_asking_and_names_the_only_askable_datum():
    """The under-act fix, first half: default to a call, ask only for what a tool requires."""
    rule = _rules()[2]
    assert "Act first" in rule, (
        f"rule 2 stopped telling the model to act first, so the 0.30-recall way of "
        f"answering with a question is back: {rule!r}")
    assert "call, not a" in rule and "question" in rule, (
        f"rule 2 no longer frames a vague request as a call rather than a question: {rule!r}")
    assert "matching and" in rule.lower() and "resume" in rule, (
        f"rule 2 lost the boundary between tools that need a resume and search that does not: {rule!r}")


def test_rule_3_puts_search_jobs_first_for_role_requests_even_personalised_ones():
    """The under-act fix, second half: 'jobs that suit me' searches before it personalises."""
    rule = _rules()[3]
    assert "search_jobs" in rule, (
        f"rule 3 no longer names the tool a role request must start with: {rule!r}")
    assert "before" in rule, (
        f"rule 3 lost the ordering -- search first, refine after: {rule!r}")
    assert "suit me" in rule, (
        f"rule 3 dropped the personalised-request case the baseline failed on (as-01): {rule!r}")


def test_the_rules_the_baseline_scored_well_survive_the_rewrite():
    """Precision came from grounding and delegation; losing them trades recall for trust."""
    rules = _rules()
    assert "Never invent" in rules[1] and "experience" in rules[1] and "results" in rules[1], (
        f"the no-fabrication rule lost its teeth: {rules[1]!r}")
    assert "transfer_to" in rules[4] and "responsible for the final answer" in rules[4], (
        f"the delegation rule lost the handoff or the ownership clause: {rules[4]!r}")
    assert "Answer in concise" in rules[5], (
        f"the style rule vanished: {rules[5]!r}")
    assert "UNTRUSTED" in rules[6] and "never instructions" in rules[6], (
        f"the untrusted-data rule vanished: {rules[6]!r}")


def test_the_rules_stay_numbered_one_through_six_in_order():
    """The fix edited rules 2 and 3 in place; a renumber or a dropped rule is an unreviewed edit."""
    assert sorted(_rules()) == list(range(1, 7)), (
        f"CAREER_SYSTEM's rules are not 1..6 in order: {sorted(_rules())}")
