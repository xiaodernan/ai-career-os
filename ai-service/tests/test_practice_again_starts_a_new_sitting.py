"""68.1: "Practice again" must start a sitting, not reopen the finished one.

The report's button linked to ``/interviews/{this id}`` -- the very session the
report is about. That session is completed, so the runner answers with a
"finished" card and a link back to the report the reader just came from: a loop
with no rehearsal in it. The verb the button needs is the create route every
other start surface already spends, carrying the card the report was rehearsed
for (or the role, for a free rehearsal), and the reader lands on the new
sitting's id.
"""

import re
from pathlib import Path

TESTS = Path(__file__).resolve().parent
ROOT = TESTS.parent.parent
PAGE = ROOT / "frontend" / "src" / "app" / "(app)" / "interviews" / "[id]" / "report" / "page.tsx"


def test_the_button_no_longer_links_back_to_the_session_it_reports_on():
    page = PAGE.read_text(encoding="utf-8")
    at = page.index('t("interviews.report.practiceAgain")')
    before = page[max(0, at - 420):at]
    assert "onClick={practiceAgain}" in before, (
        "the practice button no longer runs the create handler, so it can only send the reader "
        "back to the finished sitting")
    assert "Link href={`/interviews/${data.id}`}" not in before, (
        "the practice button links back to the completed session again")
    assert "useCreateInterviewSession()" in page, (
        "the report no longer spends the create route, so 'practice again' has no new sitting")


def test_the_new_sitting_carries_the_card_or_the_role_and_opens_its_id():
    page = PAGE.read_text(encoding="utf-8")
    start = page.index("const practiceAgain")
    body = page[start:page.index("if (!hasReport)", start)]
    assert re.search(r"mode: data\.mode", body), (
        "the new sitting no longer keeps the report's mode")
    assert "applicationId: data.applicationId" in body, (
        "a card's retry no longer names the card, so it would inherit nothing")
    assert "positionTitle: data.jobTitle" in body, (
        "a free retry no longer carries the role the report was practised for")
    assert re.search(r"router\.push\(`/interviews/\$\{nextId\}`\)", body), (
        "the button no longer opens the sitting it created")
