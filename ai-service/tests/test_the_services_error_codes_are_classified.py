"""The services' error codes are classified: a sentence, or a named gap.

A failed write answers with a toast, and the toast says what the server said
-- in English. The obvious fix is to translate by the **code**, because the
code is the contract ("never rename an emitted code") and the code is what
crosses the wire.

But the codes are **coarser than the messages**. Measured against the throw
sites, a code that answers with more than one sentence is a code that
answers for more than one situation -- and one sentence for it would tell a
reader whose request was refused for one reason that it was refused for
another. So the fix is not a translation, it is a finer vocabulary, and until
the vocabulary is fine enough the codes that mean several things keep the
server's own words.

The vocabulary is being made finer one code at a time. The resume's
not-found code is six codes now, the request bucket that answered with twelve
sentences is thirteen, the session codes are one meaning each, the not-found
code is five, the storage errors are split, the validation bucket is four, the
version code is three, the assistant's own errors are two, and the sign-in
bucket is two -- a failed sign-in and a signed-in reader's mistyped current
password, which are different sentences to different readers -- with the
buckets themselves gone, because a name that means nothing is not a
contract.

This gate holds the classification, and it *measures* it rather than
remembering it:

* every code the services can send is either translated (the browser's table
  has a sentence for it) or named as a gap -- a new code has to be one or
  the other, so it cannot arrive unclassified;
* a code that is translated carries **one** meaning, read off the throw
  sites: a code that answers with several sentences cannot be given one
  sentence without the sentence being wrong about half of them;
* a code that is named as a gap really is one: either it carries several
  meanings, or its wording cannot be read at all -- and the gate measures
  which, so the list of gaps cannot rot into a list of excuses;
* the table's codes are real -- the services' own, or the browser's.

The throw sites are read out of the backend's source and the table out of
the browser's, because a gate that keeps its own copy of either goes green
the moment the two drift apart.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
ENUM_SOURCE = (
    ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros" / "common"
    / "ApiErrorCode.java"
)
BACKEND_MAIN = ROOT / "backend" / "src" / "main"
TRANSLATIONS = ROOT / "frontend" / "src" / "lib" / "i18n" / "translations.ts"
CLIENT = ROOT / "frontend" / "src" / "lib" / "api" / "client.ts"

# The codes that mean several things -- or whose wording is not a literal,
# so it cannot be measured -- so one sentence would mislead. Every one of
# them is on the road map's queue: one code per distinct wording, and the
# throw sites changed to name them.
# The codes that mean several things: one sentence would be wrong about
# most of them, so they keep the server's own words until the throw sites
# name them properly. This list is the road map's queue.
SEVERAL_MEANINGS: frozenset[str] = frozenset({
    # "Resource not found" is the route catch-all, "Session not found" is a
    # login-session row a reader asked to close, and the mail-settings page
    # answers its three refusals with one constant the scan cannot read.
    # One sentence for all three would be wrong about two; the queue item is
    # a session-row code and a mail-link code, and until then the reader
    # keeps the server's own words.
    "NOT_FOUND",
})

# The codes whose wording cannot be measured at all: the upstream's own
# sentence, which varies with the request. A sentence for such a code would
# be wrong about most of the requests, so it keeps the server's own words --
# and the reason it is still here is written down rather than implied.
UNMEASURABLE: frozenset[str] = frozenset({
    "AI_SERVICE_BAD_REQUEST",
})

COARSE: frozenset[str] = SEVERAL_MEANINGS | UNMEASURABLE


# The codes whose several wordings are **one thing**, so one sentence covers
# them. The access token expiring and the refresh token expiring are the same
# event -- the session is gone -- and the sentence says so.
#
# A human decided that; the gate holds the list against the measurement, so
# an entry that no longer needs to be there (the code grew a second meaning,
# and the sentence is now wrong about one of them) is removed rather than
# left to rot.
SAME_MEANING: frozenset[str] = frozenset({
    # The access token and the refresh token both expiring are the same
    # event -- the session is gone.
    "TOKEN_EXPIRED",
    # "No parsed resume available for matching" and "no plaintext or ingested
    # document for this resume" are the same thing: the resume has no parsed
    # version, and the reader's answer to both is to parse it.
    "RESUME_NOT_PARSED",
    # The reader-facing "authentication required" and the services' own
    # "invalid internal token" are one thing *to the reader*: they are the
    # one thing the reader can do about either. The internal one is a
    # service-to-service error the reader never sees, and the sentence
    # names what the reader does.
    "UNAUTHORIZED",
    # "Invalid access token" and "Unknown refresh token" are one thing to
    # the reader: the session is not valid, and the answer is to sign in
    # again. Which of the two tokens was the dead one changes nothing the
    # reader can do.
    "TOKEN_INVALID",
    # "Not an access token" and "Malformed token subject" are one thing
    # too: the token is not one of ours, so the session cannot be read.
    "TOKEN_MALFORMED",
    # "Invalid reset token" answers for a link that is unknown and for one
    # that was already spent or has expired. The reader's answer is the
    # same for both: ask for another link.
    "RESET_TOKEN_INVALID",
    # "AI service returned empty body" and "The renderer answered no
    # document" are the same event at two call sites: the upstream answered,
    # and the answer carried no payload. The sentence -- "The AI service
    # answered with nothing." -- is true of both, and the reader's next step
    # is the same either way: try again.
    "AI_SERVICE_EMPTY_RESPONSE",
    # "Invalid email change token" and "Email change token used or expired"
    # are one refusal on purpose: the controller's own doc comment says the
    # public route must not tell a forger which half of a guess was right,
    # so the reader is told the link is not valid or has expired, which is
    # true of every one of the four cases.
    "EMAIL_CHANGE_INVALID",
})


def enum_codes() -> set[str]:
    """The codes the services' enum declares."""
    source = ENUM_SOURCE.read_text(encoding="utf-8")
    return set(re.findall(r"^\s{4}([A-Z_]+)\(HttpStatus", source, re.M))


def throw_sites() -> tuple[dict[str, set[str]], set[str]]:
    """The wording each code carries, and the codes whose wording is unknown.

    There are **three** ways a code reaches the reader, and the measurement
    has to see all of them: a throw (`new ApiException`), the envelope
    builder (`ApiError.of`), and the exception handler's own edges (the
    401, the 403, the 404, the 429). A measurement that only read the
    throws would have called `RATE_LIMITED` and `FORBIDDEN` silent, and
    "silent" is not the same as "one meaning".

    A code whose message is not a literal cannot be measured here -- and a
    code whose wording cannot be measured cannot be given one sentence, so
    it is treated as a gap.
    """
    wordings: dict[str, set[str]] = {}
    unmeasured: set[str] = set()
    for path in BACKEND_MAIN.rglob("*.java"):
        text = path.read_text(encoding="utf-8", errors="replace")
        patterns = (
            r"new ApiException\(\s*ApiErrorCode\.([A-Z_]+)\s*,\s*",
            r"ApiError\.of\(\s*ApiErrorCode\.([A-Z_]+)\s*,\s*",
            # GlobalExceptionHandler.badRequest(code, message, details)
            r"badRequest\(\s*ApiErrorCode\.([A-Z_]+)\s*,\s*",
        )
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                code = match.group(1)
                rest = text[match.end():].lstrip()
                if rest.startswith('"'):
                    end = rest.find('"', 1)
                    wordings.setdefault(code, set()).add(rest[1:end])
                else:
                    unmeasured.add(code)
    return wordings, unmeasured


def error_sentences() -> list[dict[str, str]]:
    """The table's code -> sentence, one dict per language."""
    source = TRANSLATIONS.read_text(encoding="utf-8")
    blocks = []
    for match in re.finditer(r"errorCodes:\s*\{", source):
        start = match.end()
        depth = 1
        index = start
        while index < len(source) and depth:
            if source[index] == "{":
                depth += 1
            elif source[index] == "}":
                depth -= 1
            index += 1
        blocks.append(source[start:index])
    assert len(blocks) == 2, f"the table has {len(blocks)} error-code blocks, not two"
    return [dict(re.findall(r'^\s*([A-Z_]+):\s*"((?:[^"\\]|\\.)*)"', block, re.M)) for block in blocks]


def error_tables() -> tuple[set[str], set[str]]:
    """The codes the browser's table answers, per language."""
    tables = error_sentences()
    return set(tables[0]), set(tables[1])


def browser_codes() -> set[str]:
    """The codes the browser raises itself."""
    source = CLIENT.read_text(encoding="utf-8")
    return set(re.findall(r"new ApiError\(\s*\"([A-Z_]+)\"", source))


def test_every_code_the_services_can_send_is_classified() -> None:
    """A code nobody classified is a code nobody thought about.

    A new code has to be translated or named as a gap -- and the road map's
    queue is the list of gaps, so a code that arrives without a decision
    reddens here instead of arriving in the reader's face in English.
    """
    english, _chinese = error_tables()
    known = enum_codes()
    for code in sorted(known):
        assert code in english or code in COARSE, (
            f"the services can send `{code}` and nobody said what to do with "
            "it: give it a sentence in the browser's table, or name it as a "
            "gap (the road map's queue)"
        )


def test_two_codes_may_share_a_sentence_only_if_a_person_said_they_are_one_thing() -> None:
    """A split that keeps the same sentence is not a split.

    Two codes that answer with one sentence tell the reader the same thing
    whichever happened: the code is finer, and the reader's experience is
    not. That is allowed only where a person judged the two to be one
    thing -- which is what the same-meaning list is for, and what a
    measurement cannot decide.
    """
    for table in error_sentences():
        by_sentence: dict[str, list[str]] = {}
        for code, sentence in table.items():
            by_sentence.setdefault(sentence, []).append(code)
        for sentence, codes in sorted(by_sentence.items()):
            if len(codes) < 2:
                continue
            for code in codes:
                assert code in SAME_MEANING, (
                    f"`{code}` and {sorted(set(codes) - {code})} answer with the same "
                    f"sentence ({sentence!r}), so the reader is told the same thing "
                    "whichever happened -- either the two mean one thing (the "
                    "same-meaning list) or their sentences have to differ"
                )


def test_the_table_only_names_codes_that_exist() -> None:
    """A sentence for a code nobody sends is a sentence nobody reads."""
    english, _chinese = error_tables()
    real = enum_codes() | browser_codes()
    invented = sorted(english - real)
    assert invented == [], (
        f"the browser's table answers codes nobody sends: {invented}. Either "
        "the code is invented, or the services renamed it -- and an emitted "
        "code is never renamed"
    )


def test_the_two_languages_answer_the_same_codes() -> None:
    english, chinese = error_tables()
    assert english == chinese, (
        f"the languages answer different codes: {sorted(english ^ chinese)}"
    )


def test_a_translated_code_means_one_thing() -> None:
    """The rule the whole table rests on.

    A code that answers with several sentences cannot be given one sentence:
    the sentence would be wrong about half of them, and a reader whose
    resume has no parsed version would be told their resume is gone.
    """
    wordings, unmeasured = throw_sites()
    english, _chinese = error_tables()
    for code in sorted(english):
        if code in COARSE:
            continue
        assert code not in unmeasured, (
            f"`{code}` is translated, but its message is not a literal, so "
            "the gate cannot tell what it means -- a code whose wording "
            "cannot be measured cannot be given one sentence"
        )
        said = wordings.get(code, set())
        assert len(said) <= 1 or code in SAME_MEANING, (
            f"`{code}` answers with {len(said)} different sentences "
            f"({sorted(said)}), so one sentence would be wrong about most of "
            "them -- it belongs in the gaps until the code is finer, unless "
            "they are the same thing, which is what the same-meaning list is "
            "for"
        )


def test_the_same_meaning_list_is_honest() -> None:
    """The list of "these wordings are one thing" cannot rot."""
    wordings, _unmeasured = throw_sites()
    english, _chinese = error_tables()
    for code in sorted(SAME_MEANING):
        assert code in english, (
            f"`{code}` is on the same-meaning list but the browser's table "
            "has no sentence for it -- the list is of codes that are "
            "translated"
        )
        said = wordings.get(code, set())
        assert len(said) > 1, (
            f"`{code}` is on the same-meaning list, but it answers with "
            f"{len(said)} sentence(s) ({sorted(said)}) -- it means one thing "
            "now, so it needs no exception"
        )


def test_a_named_gap_really_is_a_gap() -> None:
    """The list of gaps cannot rot into a list of excuses.

    There are two reasons a code can be a gap, and they are different work:
    a code that means several things is waiting to be split into codes, and
    a code whose wording cannot be read is waiting for a vocabulary that
    does not exist yet. The gate measures which one it is -- the list says
    the reason, and the source has to agree.
    """
    wordings, unmeasured = throw_sites()
    known = enum_codes()
    for code in sorted(COARSE):
        assert code in known, (
            f"the gaps name `{code}`, which the services do not have: the "
            "list is of codes that exist"
        )
        said = wordings.get(code, set())
        if code in SEVERAL_MEANINGS:
            assert len(said) > 1, (
                f"`{code}` is named as a gap because it means several things, but it answers with "
                f"{len(said)} sentence(s) ({sorted(said)}) -- it can be translated now, so it "
                "should not be waiting"
            )
        else:
            assert code in unmeasured, (
                f"`{code}` is named as a gap because its wording cannot be read, but its wording "
                "is a literal after all -- it can be translated now, so it should not be waiting"
            )
