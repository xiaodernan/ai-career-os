"""The export's readable half: the words, and the sections it has to cover.

13.1's *human-readable* export -- the print-ready document -- was written in
Chinese and had no other language, so an English reader's printable document
was a Chinese document. The words live in a server-side module, in a
document, so the copy census could not see them either: they are not on a
screen.

And the document left out two sections: the notes the reader typed and the
people they know. A section the bundle carries and the document does not is
a section the reader cannot read, and the counts still said it was there.

This gate holds three things:

* every language the readable half ships in has every word, and the
  languages agree with each other;
* the section names cover **every section the bundle carries** -- the
  document cannot quietly leave one out;
* the document says which language it is in, so a reader (and a test) can
  tell an English document from a Chinese one.
"""

from app.features import export as ex
from app.features import export_render as render_mod
from app.features import export_words as words_mod


def test_every_language_has_every_word() -> None:
    reference = words_mod.words(words_mod.LOCALES[0])
    for locale in words_mod.LOCALES:
        table = words_mod.words(locale)
        missing = sorted(set(reference) - set(table))
        assert missing == [], f"the {locale} document is missing these words: {missing}"
        extra = sorted(set(table) - set(reference))
        assert extra == [], f"the {locale} document has words no other language has: {extra}"
        for name, sentence in table.items():
            assert sentence.strip(), f"the {locale} word `{name}` is blank"


def test_every_language_names_every_section_the_bundle_carries() -> None:
    # The document that left out the notes and the contacts: the bundle
    # carried them and the readable export did not, so a reader could not
    # read the two tables they wrote into.
    for locale in words_mod.LOCALES:
        titles = words_mod.section_titles(locale)
        missing = sorted(set(ex.SECTIONS) - set(titles))
        assert missing == [], (
            f"the {locale} document has no name for these sections: {missing}. "
            "A section the bundle carries and the document does not is a section "
            "the reader cannot read"
        )


def test_the_two_languages_name_the_same_sections() -> None:
    reference = set(words_mod.section_titles(words_mod.LOCALES[0]))
    for locale in words_mod.LOCALES[1:]:
        titles = set(words_mod.section_titles(locale))
        assert titles == reference, (
            f"the {locale} document names {sorted(titles ^ reference)} differently "
            "from the others"
        )


def test_an_unknown_language_is_english_rather_than_a_guess() -> None:
    # The table is the product's account of itself: a language it does not
    # have is one it must not pretend to.
    assert words_mod.normalize_locale("zh-CN") == "zh"
    assert words_mod.normalize_locale("EN") == "en"
    assert words_mod.normalize_locale("fr") == "en"
    assert words_mod.normalize_locale(None) == "en"


def test_the_document_says_which_language_it_is_in() -> None:
    # The reader -- and the test -- has to be able to tell an English
    # document from a Chinese one without reading it.
    bundle = {"data": {}, "manifest": {"counts": {}}}
    english = render_mod.to_html(bundle, "en")
    chinese = render_mod.to_html(bundle, "zh")
    assert '<html lang="en">' in english
    assert '<html lang="zh">' in chinese
    assert words_mod.words("en")["title"] in english
    assert words_mod.words("zh")["title"] in chinese
    assert words_mod.words("en")["title"] not in chinese


async def test_the_render_route_answers(monkeypatch) -> None:
    """The route, not the function behind it.

    The render module was never imported by the module that serves the
    route, so the route raised a ``NameError`` on every call: the "Print
    view" button on the export page had never worked, and the only sign of
    it was an error toast. Nothing called the route -- the unit tests called
    the function -- so nothing knew.

    The route is called here the way the bridge calls it, because a route
    that cannot answer is a route that does not exist as far as the reader
    is concerned. The two bookkeeping steps are stubbed: they write a run
    row, and this is about whether the route answers at all.
    """
    from app.api import features

    async def fake_run(ctx, agent, trigger):
        return "run-1"

    async def fake_finish(run_id, status):
        return None

    monkeypatch.setattr(features, "_run", fake_run)
    monkeypatch.setattr(features.observability, "finish_run", fake_finish)

    ctx = features.Ctx(user_id="11111111-1111-1111-1111-111111111111", run_id=None)
    empty = {"data": {}, "manifest": {"counts": {}}, "user": {}}

    class Req:
        bundle = empty
        format = "html"
        locale = "en"

    answer = await features.render_bundle_ep(Req(), ctx)
    assert answer["format"] == "html"
    assert words_mod.words("en")["title"] in answer["html"]

    class ZhReq(Req):
        locale = "zh"

    answer = await features.render_bundle_ep(ZhReq(), ctx)
    assert words_mod.words("zh")["title"] in answer["html"]
