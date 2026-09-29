"""The ingestion pipeline's only network read: ai-service -> the backend's file download.

`_fetch_bytes` (app/ingestion/pipeline.py:18-28) is the whole of the ai-service -> backend direction
that carries a document's bytes: it builds a URL by string concatenation from two settings, sends the
shared internal token on the request, refuses an error answer, and reads `r.content`. Nothing in
`tests/` had ever mocked httpx at all (`grep -rln httpx ai-service/tests` named no file until this
one), so none of those four steps had a witness -- while the route it talks to had just got its own
(the backend's InternalFileControllerTest), which pins this file's URL literal from the other end.

Both ends of every pin below come from the shipped sources: the path prefix from
`InternalFileController.java`'s own `@RequestMapping`, the media-type reason from `EnvelopeAdvice`'s
exemption list, the token default from `application.yml`, and the settings from the `Settings` class
itself rather than a copy of what it currently holds.
"""

import re
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest

from app.core import config
from app.core.config import Settings
from app.ingestion import pipeline

ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / "backend" / "src" / "main" / "java" / "com" / "careeros"
CONTROLLER = JAVA / "knowledge" / "web" / "InternalFileController.java"
ADVICE = JAVA / "common" / "EnvelopeAdvice.java"
APP_YML = ROOT / "backend" / "src" / "main" / "resources" / "application.yml"
ENV_EXAMPLE = ROOT / ".env.example"
COMPOSE = ROOT / "docker-compose.yml"

KEY = "11111111-1111-4111-8111-111111111111/resumes/33333333-3333-4333-8333-333333333333.pdf"
PDF = b"%PDF-1.4\nnot a json document\n"
BASE = "http://backend.test:8080"
TOKEN = "tok-under-test"


def reads(path: Path) -> str:
    assert path.is_file(), f"expected {path} to exist for this cross-language pin"
    return path.read_text(encoding="utf-8")


def mapped_prefix() -> str:
    """The download route's own mapping plus the slash the controller strips, from its Java source."""
    found = re.findall(r'@RequestMapping\("([^"]+)"\)', reads(CONTROLLER))
    assert len(found) == 1, f"expected exactly one @RequestMapping, found {found}"
    return found[0] + "/"


def setting_value(path: Path, name: str) -> str:
    for line in reads(path).splitlines():
        stripped = line.strip()
        if stripped.startswith(f"{name}=") or stripped.startswith(f"{name}:"):
            return stripped.split(name, 1)[1].lstrip("=: ").strip()
    raise AssertionError(f"{name} is not spelled in {path}")


class RecordingResponse:
    """The three accessors this client could read, each recording that it was read."""

    def __init__(self, status_code: int = 200, content: bytes = PDF):
        self.status_code = status_code
        self._content = content
        self.reads: list[str] = []

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("refused", request=None, response=self)  # type: ignore[arg-type]

    @property
    def content(self) -> bytes:
        self.reads.append("content")
        return self._content

    @property
    def text(self) -> str:
        self.reads.append("text")
        return self._content.decode("utf-8", "replace")

    def json(self) -> dict:
        self.reads.append("json")
        return {}


class RecordingClient:
    """Stands in for httpx.AsyncClient and records what the shipped code asked it for."""

    def __init__(self, response: RecordingResponse):
        self.response = response
        self.client_kwargs: dict | None = None
        self.gets: list[tuple[str, dict | None]] = []

    def __call__(self, **kwargs):
        self.client_kwargs = kwargs
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get(self, url, headers=None):
        self.gets.append((str(url), headers))
        return self.response


def armed(monkeypatch, *, base: str = BASE, token: str = TOKEN,
          response: RecordingResponse | None = None) -> RecordingClient:
    """Route the shipped code through a recording client with the settings this file names.

    Both patches land where they do for different reasons, and the settings half is the fragile one.
    `_fetch_bytes` imports `get_settings` inside its body, so the call looks the name up on the
    `app.core.config` module and sees this replacement; the file's own module-level
    `from app.core.config import get_settings` (used by the caller) binds the function object once and
    would not. Measured: switching the body to that already-imported name leaves the four cases that
    read a setting answering with the real defaults (`http://localhost:8080`, the shipped token) while
    the three that never look at one stay green. So if a cleanup ever hoists that import, this helper
    stops injecting and the reds will name it.
    """
    client = RecordingClient(response or RecordingResponse())
    monkeypatch.setattr(httpx, "AsyncClient", client)
    settings = Settings(_env_file=None, backend_base_url=base, internal_api_token=token)
    monkeypatch.setattr(config, "get_settings", lambda: settings)
    return client


# ------------------------------------------------------------------ the URL the route answers on


async def test_the_url_is_the_java_mapping_plus_the_stored_key(monkeypatch):
    # The prefix is written in two languages: the Java controller maps it, the Python client pastes
    # it. Deriving it from the controller's own annotation is what makes a rename on one side a red
    # test rather than a 404 in a running ingestion job.
    client = armed(monkeypatch)

    assert await pipeline._fetch_bytes(KEY) == PDF
    assert client.gets == [(BASE + mapped_prefix() + KEY, {"X-Internal-Token": TOKEN})]


async def test_a_key_reaches_the_string_the_client_is_given_exactly_as_the_row_holds_it(monkeypatch):
    # No quoting, no escaping: the shipped code is an f-string, so whatever characters a file_key
    # column holds go into the URL as they are. Measured here on the string handed to the client --
    # what httpx then normalises on the wire is its own business -- and it matters because the route
    # decodes the tail of the URI before it checks its shape (the backend test names that ordering),
    # so a key stored with a percent sequence has to arrive carrying the same one.
    client = armed(monkeypatch)

    for odd_key in ("a/resumes/x%zz.pdf", "a/resumes/x y.pdf", "a/resumes/100%.pdf",
                    "a%2fresumes%2fb.pdf"):
        await pipeline._fetch_bytes(odd_key)

    assert [url for url, _ in client.gets] == [BASE + mapped_prefix() + k for k in
                                               ("a/resumes/x%zz.pdf", "a/resumes/x y.pdf",
                                                "a/resumes/100%.pdf", "a%2fresumes%2fb.pdf")]


# ------------------------------------------------------------------ what the answer is asked for


async def test_the_token_is_sent_on_the_request_and_read_from_the_settings(monkeypatch):
    # Two separate claims, because they break differently. The client is constructed with nothing but
    # a timeout, so the credential cannot be a client default some later request inherits silently;
    # and the header's value comes from the Settings instance, so rotating it stays one edit in one
    # place (docs/DEPLOYMENT.md:21 asks the same value to arm both services).
    client = armed(monkeypatch)

    await pipeline._fetch_bytes(KEY)

    assert client.client_kwargs == {"timeout": 60}, \
        "pipeline.py:25 names exactly one client argument; a second would apply to every request "\
        "this function makes"
    assert [headers for _, headers in client.gets] == [{"X-Internal-Token": TOKEN}]

    second = armed(monkeypatch, token="rotated")
    await pipeline._fetch_bytes(KEY)
    assert second.gets[0][1] == {"X-Internal-Token": "rotated"}


async def test_an_error_answer_is_refused_before_a_single_body_byte_is_read(monkeypatch):
    # The order is the whole story of a failed ingest: `raise_for_status()` and only then
    # `return r.content`. Reversed, a 404's JSON error body would be handed to `extract_text`, whose
    # first branch sniffs `%PDF-` and whose last resort decodes whatever arrives -- so the document
    # would be indexed as `{"error": ...}` prose instead of the job failing.
    refused = RecordingResponse(status_code=404)
    armed(monkeypatch, response=refused)

    with pytest.raises(httpx.HTTPStatusError):
        await pipeline._fetch_bytes(KEY)

    assert refused.reads == [], "the body was read despite the refusal, which is what this case names"


async def test_the_body_is_read_as_bytes_because_the_route_answers_with_the_file(monkeypatch):
    # The route's declared `ResponseEntity<byte[]>` is why the answer is the file itself: the shared
    # envelope advice exempts `byte[]`, and it must, because the converter for that declared type
    # casts the body to `[B -- wrap it and every download 500s. So this side may not read a text or
    # JSON view of the answer: a docx is a zip, and decoding it with replacement is how a document
    # becomes silently unrecoverable.
    raw = b"PK\x03\x04\xff\xfe not utf-8"
    response = RecordingResponse(content=raw)
    armed(monkeypatch, response=response)

    got = await pipeline._fetch_bytes(KEY)

    assert got == raw and isinstance(got, bytes)
    assert response.reads == ["content"]
    assert "body instanceof byte[]" in reads(ADVICE), \
        "the exemption this read depends on is gone from the advice"


# ------------------------------------------------------------------ the shared secret, both sides


def test_the_shared_tokens_default_is_the_same_string_in_both_languages():
    # Asked of the producers: the Python field's own declared default, and the Java property's own
    # `${NAME:default}` fallback. Two languages each write the same secret once so a developer can
    # start both services with no env file at all -- and if one of the two is rotated alone, every
    # internal call answers 401 while both services' logs look healthy.
    python_default = Settings.model_fields["internal_api_token"].default
    java = re.search(r"token: \$\{INTERNAL_API_TOKEN:([^}]*)\}", reads(APP_YML))
    assert java is not None, "expected application.yml to default the internal token inline"
    assert python_default == java.group(1)


async def test_a_base_url_that_ends_in_a_slash_costs_the_keys_first_segment(monkeypatch):
    # Characterization of a latent asymmetry, with its mechanism measured rather than asserted away.
    # The client concatenates, so a trailing slash survives as `//api/...` on the request target, and
    # the route's strip is arithmetic on its own mapping plus one slash -- it cuts a fixed 20
    # characters, whatever the URI begins with. Cut "//api/internal/files/<key>" that way and the
    # tail still carries a separator, while the key pattern is anchored on a UUID hex digit, so the
    # shape check refuses a key the database holds perfectly. Whether the servlet container
    # normalizes the doubled slash before it maps the request is not something an offline test can
    # read, so this case names only the two shipped strings and the cut.
    # None of the shipped spellings of the setting carries that slash, which is why this is a witness
    # and not a production fix; the guard is that if one ever does, the last lines say so first.
    client = armed(monkeypatch, base=BASE + "/")

    await pipeline._fetch_bytes(KEY)

    url = client.gets[0][0]
    assert url == BASE + "/" + mapped_prefix() + KEY
    path = urlsplit(url).path
    assert path == "/" + mapped_prefix() + KEY
    prefix = mapped_prefix()
    assert len(prefix) == 20, "the cut below is only the route's arithmetic while its prefix is this"
    tail = path[len(prefix):]
    assert tail.startswith("/") and tail.lstrip("/") == KEY
    assert '"^[0-9a-fA-F]{8}' in reads(CONTROLLER), \
        "the key pattern no longer anchors on the uuid, so this case's premise is stale"

    for label, value in ((".env.example", setting_value(ENV_EXAMPLE, "BACKEND_BASE_URL")),
                         ("docker-compose.yml", setting_value(COMPOSE, "BACKEND_BASE_URL"))):
        assert not value.endswith("/"), f"{label} would arm the mechanism this case characterizes"
