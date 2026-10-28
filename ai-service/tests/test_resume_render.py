"""The single-version print view (19.5): one resume, in the reader's words.

The bundle's printable half renders every resume as one clipped bullet --
that is a record of the search, not a resume to send. This renders a saved
version's structured body section by section, through the same print chrome,
so "tailor -> print/PDF" never needs the whole export.

What this gate holds, each case born from a way the document could lie:

* the headings are the reader's language, not the resume body's -- the
  tailoring prompt writes English keys, and a Chinese reader's printable
  resume must not inherit them;
* every field is escaped: the body is user data and is untrusted on render,
  exactly like the bundle's;
* a blank row is dropped rather than printed as an empty heading, because an
  empty <h3> reads as a section the reader omitted on purpose;
* a version with no structured body prints its stored plaintext, and one
  with neither says so with a dash rather than pretending;
* the route answers -- the function alone proves nothing about the surface
  the backend reaches.
"""

from app.features import export_render as rnd
from app.features import export_words as words_mod


def _resume() -> dict:
    return {
        "profile": {
            "name": "Ada Lovelace",
            "headline": "Backend engineer",
            "email": "ada@example.com",
            "phone": "+44 20 0000 0000",
            "location": "London",
            "summary": "Eight years of payments infrastructure.",
        },
        "experience": [
            {"company": "Acme", "title": "Senior Engineer", "start": "2021-03",
             "end": "present", "location": "Remote",
             "bullets": ["Cut p99 latency by 40%", "Led the ledger migration"]},
        ],
        "projects": [
            {"name": "ledger", "role": "Author", "period": "2023",
             "bullets": ["A double-entry ledger"], "tech": ["Go", "Postgres"]},
        ],
        "education": [
            {"school": "Cambridge", "degree": "BSc", "field": "CS",
             "startYear": 2010, "endYear": 2013, "gpa": "3.9",
             "courses": ["Algorithms"]},
        ],
        "skills": [
            {"name": "Go", "category": "Languages"},
            {"name": "Postgres", "category": "Databases"},
        ],
        "achievements": ["Open-source maintainer"],
    }


def test_every_language_names_every_resume_section() -> None:
    reference = words_mod.resume_titles(words_mod.LOCALES[0])
    for locale in words_mod.LOCALES:
        table = words_mod.resume_titles(locale)
        assert set(table) == set(reference), (
            f"the {locale} print view names {sorted(set(table) ^ set(reference))} "
            "differently from the others"
        )
        for key, word in table.items():
            assert word.strip(), f"the {locale} heading `{key}` is blank"


def test_the_document_speaks_the_readers_language() -> None:
    # The headings must come from the table, not from the body or the prompt:
    # an English document says "Experience", a Chinese one says "工作经历",
    # and neither borrows the other's word.
    english = rnd.resume_to_html(_resume(), "en")
    chinese = rnd.resume_to_html(_resume(), "zh")
    en_titles = words_mod.resume_titles("en")
    zh_titles = words_mod.resume_titles("zh")
    for section in ("summary", "experience", "projects", "education", "skills",
                    "achievements"):
        assert f"<h2>{en_titles[section]}</h2>" in english, (
            f"the English document has no {section} heading"
        )
        assert f"<h2>{zh_titles[section]}</h2>" in chinese, (
            f"the Chinese document has no {section} heading"
        )
    assert '<html lang="en">' in english
    assert '<html lang="zh">' in chinese
    assert "工作经历" not in english
    assert "<h2>Experience</h2>" not in chinese


def test_the_document_escapes_user_content() -> None:
    resume = _resume()
    resume["profile"]["name"] = "<script>alert(1)</script>"
    resume["profile"]["summary"] = "Built <b>things</b>"
    resume["experience"][0]["bullets"] = ["<img src=x onerror=alert(1)>"]
    document = rnd.resume_to_html(resume, "en")
    assert "<script>alert(1)</script>" not in document
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in document
    assert "<b>things</b>" not in document
    assert "<img src=x" not in document


def test_the_document_carries_every_section_the_body_holds() -> None:
    document = rnd.resume_to_html(_resume(), "en")
    assert "Ada Lovelace" in document
    assert "Backend engineer" in document
    assert "Cut p99 latency by 40%" in document
    assert "ledger" in document
    assert "Cambridge" in document
    assert "Languages: Go" in document
    assert "Open-source maintainer" in document


def test_blank_rows_are_dropped_rather_than_printed_empty() -> None:
    # An empty <h3> reads as a role the candidate left blank on purpose; the
    # honest document leaves the row out.
    resume = {
        "profile": {"name": "Ada"},
        "experience": [
            {"company": "", "title": "", "bullets": []},
            {"company": "Acme", "title": "Engineer", "bullets": ["Did work"]},
        ],
        "projects": [{"name": "", "bullets": [], "tech": []}],
        "education": [{"school": "", "courses": []}],
        "skills": [{"name": "", "category": ""}],
        "achievements": ["", "  "],
    }
    document = rnd.resume_to_html(resume, "en")
    assert document.count("<h3>") == 1
    assert "Did work" in document
    assert "<h2>Projects</h2>" not in document
    assert "<h2>Education</h2>" not in document
    assert "<h2>Skills</h2>" not in document
    assert "<h2>Achievements</h2>" not in document


def test_a_version_with_no_structured_body_prints_its_stored_text() -> None:
    # An upload that was never parsed still has a printable document: the
    # text the server stored, whitespace preserved.
    document = rnd.resume_to_html({}, "en", text="Ada Lovelace\nBackend engineer")
    assert '<div class="plain">Ada Lovelace\nBackend engineer</div>' in document
    assert "<h2>" not in document


def test_a_version_with_neither_says_so_with_a_dash() -> None:
    # Neither body nor text is not a document; the page says so rather than
    # shipping a blank sheet that looks like a rendering failure.
    document = rnd.resume_to_html({}, "en")
    assert "<p>—</p>" in document


def test_the_title_is_the_name_then_the_version_label() -> None:
    # The heading names the person; a version with no name in its body is
    # introduced by what the version list calls it, and then by its subtitle.
    assert "<h1>Ada Lovelace</h1>" in rnd.resume_to_html(_resume(), "en")
    unnamed = {"profile": {}}
    assert "<h1>Main</h1>" in rnd.resume_to_html(unnamed, "en", title="Main")
    assert "<h1>v2 tailored</h1>" in rnd.resume_to_html(
        unnamed, "en", title="", subtitle="v2 tailored")
    assert "<h1>Resume</h1>" in rnd.resume_to_html(unnamed, "en")


def test_skills_print_whether_rows_or_bare_strings() -> None:
    # The parse schema writes rows; a model-written or hand-edited body
    # sometimes carries bare strings. Both are the same skill list to the
    # reader, so neither may vanish.
    rows = rnd.resume_to_html({"skills": [{"name": "Go", "category": "Languages"}]})
    bare = rnd.resume_to_html({"skills": ["Go", "Postgres"]})
    assert "Languages: Go" in rows
    assert "Go, Postgres" in bare
    assert "<h2>Skills</h2>" in bare


async def test_the_route_answers(monkeypatch) -> None:
    """The route, not the function behind it -- the lesson of 13.1's NameError.

    The backend reaches this path, so a route that cannot answer is a route
    that does not exist as far as the print button is concerned. The two
    bookkeeping steps are stubbed: they write a run row.
    """
    from app.api import features

    async def fake_run(ctx, agent, trigger):
        return "run-1"

    async def fake_finish(run_id, status):
        return None

    monkeypatch.setattr(features, "_run", fake_run)
    monkeypatch.setattr(features.observability, "finish_run", fake_finish)

    ctx = features.Ctx(user_id="11111111-1111-1111-1111-111111111111", run_id=None)
    req = features.ResumeRenderReq(
        resume=_resume(), text="", title="Main", subtitle="v2", locale="zh")
    answer = await features.render_resume_ep(req, ctx)
    assert answer["format"] == "html"
    assert "工作经历" in answer["html"]
    assert "Ada Lovelace" in answer["html"]

    empty = await features.render_resume_ep(features.ResumeRenderReq(locale="en"), ctx)
    assert "<p>—</p>" in empty["html"]
