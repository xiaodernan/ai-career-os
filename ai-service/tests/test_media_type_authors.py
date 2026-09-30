"""`documents.media_type` has exactly two writers and three shipped values; the parser table is the reader.

The column is declared `text NOT NULL` with no CHECK anywhere in the migration set, so the database
narrows nothing. Two writers fill it: Java's `FileValidator.Type`, which every upload path funnels
through the single `Document.setMediaType` call in `FileIngestService.persistRows`, and one Python
literal on the inline-text path in `app/api/ingest.py`. Three readers then act on the string:
`extract_text` dispatches on substring/suffix tests, `InternalFileController` answers with
`MediaType.parseMediaType(doc.getMediaType())`, and `keyFor`'s switch decides the file-key suffix the
download route's own pattern must accept. Every claim here is read out of those files at run time --
add a fourth type, reword a literal, drop a switch arm or a dispatch term and a case moves with it.
"""

import ast
import re
from pathlib import Path

from app.ingestion import parsers

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "backend" / "src" / "main"
JAVA = MAIN / "java" / "com" / "careeros"
APP = ROOT / "ai-service" / "app"

VALIDATOR = JAVA / "storage" / "FileValidator.java"
INGEST_SERVICE = JAVA / "knowledge" / "service" / "FileIngestService.java"
CONTROLLER = JAVA / "knowledge" / "web" / "InternalFileController.java"
DDL = MAIN / "resources" / "db" / "migration" / "V1__init_schema.sql"
MIGRATIONS = MAIN / "resources" / "db" / "migration"
PY_INGEST = APP / "api" / "ingest.py"
PY_DOCS = APP / "db" / "documents.py"
PY_PARSERS = APP / "ingestion" / "parsers.py"
PY_PIPELINE = APP / "ingestion" / "pipeline.py"
SIBLING = ROOT / "ai-service" / "tests" / "test_ingestion.py"

ENUM_HEAD = "enum Type {"
INSERT_HEAD = "INSERT INTO documents("
SETTER_CALL = re.compile(r"\.setMediaType\(")
ENUM_ENTRY = re.compile(r'([A-Z][A-Z0-9_]*)\("([^"]*)"\)')
CASE_LABEL = re.compile(r'case\s+([A-Z][A-Z0-9_]*)\s*->\s*"([^"]*)"')
METHOD_HEAD = re.compile(r"^\s+(public|private|protected)\b.*\(")
FED_BY_ENUM = re.compile(r"persistRows\([^;]{0,200}?type\.mediaType\(\)", re.S)
MEDIA_COLUMN = re.compile(r"media_type\s+text\s+NOT NULL")
CHECK_ON_MEDIA = re.compile(r"CHECK\s*\([^)]*media_type", re.I)
STRING_LITERAL = re.compile(r'"((?:[^"\\]|\\.)*)"')
SUFFIX_GROUP = re.compile(r'\.\(([^)]*)\)\$')
CONTAINS_TERM = re.compile(r'" in mt\b')
SUFFIX_TERM = re.compile(r"mt\.endswith\(")


def reads(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def java_enum_entries() -> list[tuple[str, str]]:
    """The `(CONSTANT, media type)` pairs Java can write, out of the enum's own constant list."""
    body = reads(VALIDATOR).split(ENUM_HEAD, 1)[1].split(";", 1)[0]
    return ENUM_ENTRY.findall(body)


def params(source: str, name: str) -> list[str]:
    """The declared parameter names of a Python function, in order."""
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return [a.arg for a in node.args.posonlyargs + node.args.args]
    raise AssertionError(f"{name} is not declared")


def create_document_call(source: str) -> ast.Call:
    found = [n for n in ast.walk(ast.parse(source))
             if isinstance(n, ast.Call) and (
                 isinstance(n.func, ast.Attribute) and n.func.attr == "create_document"
                 or isinstance(n.func, ast.Name) and n.func.id == "create_document")]
    assert len(found) == 1, f"expected one Python author, found {len(found)}"
    return found[0]


def authored_literals() -> set[str]:
    """Every string that can reach the column: the Java enum's answers plus the inline writer."""
    return {v for _, v in java_enum_entries()} | {python_inline_literal()}


def python_inline_literal() -> str:
    """The media type the Python writer passes, found by the column's position, not by search."""
    docs = reads(PY_DOCS)
    columns = _insert_columns(docs)
    assert "media_type" in columns, f"the Python INSERT no longer writes the column: {columns}"
    index = columns.index("media_type")
    assert params(docs, "create_document")[index] == "media_type", (
        "the INSERT's column order no longer matches the function's parameter order")
    arg = create_document_call(reads(PY_INGEST)).args[index]
    assert isinstance(arg, ast.Constant) and isinstance(arg.value, str), (
        "the inline writer must hand the column a literal; it is the only Python author")
    return arg.value


def _insert_columns(source: str) -> list[str]:
    start = source.index(INSERT_HEAD)
    stop = source.index(")", start)
    return [c.strip() for c in source[start + len(INSERT_HEAD):stop].split(",")]


def _insert_placeholders(source: str) -> list[str]:
    start = source.index("VALUES (", source.index(INSERT_HEAD))
    stop = source.index(")", start)
    return [p.strip() for p in source[start + len("VALUES ("):stop].split(",")]


def _switch_block(source: str, subject: str) -> str:
    start = source.index(f"switch ({subject})")
    brace = source.index("{", start)
    depth = 0
    for i in range(brace, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[brace:i + 1]
    raise AssertionError("unbalanced switch")


def _java_pattern(source: str, name: str) -> str:
    start = source.index(name)
    stop = source.index(");", start)
    return "".join(STRING_LITERAL.findall(source[start:stop]))


def route(media_type: str, monkeypatch) -> str:
    """Which private handler the shipped dispatcher picks for this string, asked with sentinels."""
    taken: list[str] = []
    for name in ("_pdf", "_docx", "_txt"):
        def probe(data: bytes, _name: str = name) -> str:
            taken.append(_name)
            return _name
        monkeypatch.setattr(parsers, name, probe)
    parsers.extract_text(b"", media_type)
    assert len(taken) == 1, f"{media_type!r} reached {taken}, expected exactly one handler"
    return taken[0]


def extract_text_body() -> list[ast.stmt]:
    source = ast.parse(reads(PY_PARSERS))
    for node in ast.walk(source):
        if isinstance(node, ast.FunctionDef) and node.name == "extract_text":
            return node.body
    raise AssertionError("extract_text is not declared")


def _disjuncts(test: ast.expr) -> list[ast.expr]:
    if isinstance(test, ast.BoolOp) and isinstance(test.op, ast.Or):
        return list(test.values)
    return [test]


def _term_key(term: ast.expr) -> tuple:
    if (isinstance(term, ast.Compare) and isinstance(term.ops[0], ast.In)
            and isinstance(term.left, ast.Constant)):
        return ("contains", term.left.value)
    if (isinstance(term, ast.Call) and isinstance(term.func, ast.Attribute)
            and term.func.attr == "endswith" and isinstance(term.args[0], ast.Constant)):
        return ("suffix", term.args[0].value)
    raise AssertionError(f"unrecognised dispatch term: {ast.dump(term)}")


def type_driven_branches() -> list[tuple[list[tuple], str]]:
    """`[([terms], handler)]` for every `if` in the dispatcher that decides on the media type."""
    out = []
    for node in extract_text_body():
        if not isinstance(node, ast.If):
            continue
        names = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
        if "mt" not in names:
            continue
        handler = node.body[0]
        assert isinstance(handler, ast.Return) and isinstance(handler.value, ast.Call)
        out.append(([_term_key(t) for t in _disjuncts(node.test)], handler.value.func.id))
    return out


def sniff_branches() -> list[str]:
    """The branches that decide on the bytes instead of the declared type."""
    out = []
    for node in extract_text_body():
        if not isinstance(node, ast.If):
            continue
        names = {n.id for n in ast.walk(node.test) if isinstance(n, ast.Name)}
        if "mt" not in names:
            handler = node.body[0]
            assert isinstance(handler, ast.Return) and isinstance(handler.value, ast.Call)
            out.append(handler.value.func.id)
    return out


def header_reads(tree: ast.AST) -> list[str]:
    """Expressions that read a `headers` object -- an attribute of it or a subscript on it.

    A subscript is reported whole, not also as its own value, so one read counts once.
    """
    subscripts = [n for n in ast.walk(tree) if isinstance(n, ast.Subscript) and (
        isinstance(n.value, ast.Name) and n.value.id == "headers"
        or isinstance(n.value, ast.Attribute) and n.value.attr == "headers")]
    inner = {id(s.value) for s in subscripts}
    out = [ast.unparse(n) for n in subscripts]
    out += [ast.unparse(n) for n in ast.walk(tree)
            if isinstance(n, ast.Attribute) and n.attr == "headers" and id(n) not in inner]
    return out


def header_writes(tree: ast.AST) -> list[str]:
    """Expressions that hand a header mapping to something else -- a keyword or a binding."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == "headers":
            out.append(ast.unparse(node))
        elif (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == "headers"):
            out.append(ast.unparse(node))
    return out


def term_satisfied(key: tuple, media_type: str) -> bool:
    mt = media_type.lower()
    kind, value = key
    return value in mt if kind == "contains" else mt.endswith(value)


def test_the_column_has_exactly_two_writers_and_three_literals():
    main_java = list((MAIN / "java").rglob("*.java"))
    setters = [(f, len(SETTER_CALL.findall(reads(f)))) for f in main_java if SETTER_CALL.search(reads(f))]
    assert len(setters) == 1, f"the column has {setters}, expected one Java writer"
    assert setters[0][0] == INGEST_SERVICE, f"the Java writer moved to {setters[0][0]}"
    service = reads(INGEST_SERVICE)
    heads = [ln for ln in service[:service.index(".setMediaType(")].splitlines() if METHOD_HEAD.match(ln)]
    assert heads, "no method declaration precedes the setter, so the walk read nothing"
    assert "persistRows" in heads[-1], f"the setter left persistRows: {heads[-1]}"
    fed = [f.name for f in main_java for _ in FED_BY_ENUM.findall(reads(f))]
    assert len(fed) == 3, f"persistRows is fed type.mediaType() {fed}, expected three upload paths"
    obtainable = {f.name for f in main_java if "FileValidator.validate(" in reads(f)}
    assert set(fed) <= obtainable, (
        f"{sorted(set(fed))} feed the column without asking FileValidator for a Type ({sorted(obtainable)})")

    docs = reads(PY_DOCS)
    columns, placeholders = _insert_columns(docs), _insert_placeholders(docs)
    assert "media_type" in columns, f"the INSERT no longer writes the column: {columns}"
    index = columns.index("media_type")
    assert placeholders[index].startswith(f"${index + 1}"), (
        f"columns {columns} pair with {placeholders}: media_type must be ${index + 1}")

    entries = java_enum_entries()
    assert len(entries) == len({n for n, _ in entries}), "duplicate enum constant name"
    assert len(authored_literals()) == len(entries), (
        f"{len(entries)} Java constants but {sorted(authored_literals())} distinct values")
    assert python_inline_literal() in {v for _, v in entries}, (
        f"the inline writer emits {python_inline_literal()!r}, which no Java constant answers with")


def test_every_authored_literal_parses_for_the_reader_and_routes_to_its_own_handler(monkeypatch):
    assert "MediaType.parseMediaType(" in reads(CONTROLLER), (
        "the download route stopped answering with the row's media type; this pin speaks for its parser")
    for name, value in java_enum_entries():
        assert "/" in value, f"{name} writes {value!r}: parseMediaType needs a slash"
        assert route(value, monkeypatch) == f"_{name.lower()}", (
            f"{name} ({value!r}) must reach _{name.lower()}")


def test_the_extension_switch_is_exhaustive_and_carries_no_default():
    block = _switch_block(reads(INGEST_SERVICE), "type")
    labels = CASE_LABEL.findall(block)
    assert labels, "the switch scan found no labels, so the coverage claim below read nothing"
    names = [n for n, _ in java_enum_entries()]
    assert sorted(n for n, _ in labels) == sorted(names), (
        f"switch labels {sorted(n for n, _ in labels)} vs constants {sorted(names)}")
    assert "default" not in block, (
        "a default gives an unauthorised kind a file key; the switch must stay exhaustive")
    for name, ext in labels:
        assert ext == name.lower(), f"case {name} -> {ext!r}, expected the constant's own lower name"


def test_the_switch_extensions_are_the_suffixes_the_download_route_accepts():
    extensions = {ext for _, ext in CASE_LABEL.findall(_switch_block(reads(INGEST_SERVICE), "type"))}
    pattern = _java_pattern(reads(CONTROLLER), "FILE_KEY")
    group = SUFFIX_GROUP.search(pattern)
    assert group, f"no anchored suffix group in {pattern!r}"
    accepted = set(group.group(1).split("|"))
    assert accepted == extensions, (
        f"keyFor writes {sorted(extensions)} but the download route admits {sorted(accepted)}")


def test_the_database_declares_the_column_required_and_unconstrained():
    sql = reads(DDL)
    start = sql.index("CREATE TABLE documents (")
    block = sql[start:sql.index("\n);", start)]
    assert MEDIA_COLUMN.search(block), f"the column declaration moved: {block}"
    assert not CHECK_ON_MEDIA.search(block), "a CHECK now constrains media_type; update the claim"

    # The absence above is evidence only if this scanner notices a CHECK that exists.
    snippet = "media_type text NOT NULL CHECK (media_type IN ('application/pdf')),"
    assert CHECK_ON_MEDIA.search(snippet), (
        "the CHECK scanner reads nothing, so its silence about the real block proved nothing")

    spelling = [f.name for f in sorted(MIGRATIONS.glob("*.sql")) if "media_type" in reads(f)]
    assert spelling == ["V1__init_schema.sql"], f"media_type is declared in {spelling}; this pin reads V1"


def test_the_dispatch_terms_are_the_ones_the_dispatcher_holds(monkeypatch):
    branches = type_driven_branches()
    assert branches, "no type-driven branch was read, so the counts below prove nothing"
    source = reads(PY_PARSERS)
    terms = [t for branch_terms, _ in branches for t in branch_terms]
    counted = len(terms)
    independent = len(CONTAINS_TERM.findall(source)) + len(SUFFIX_TERM.findall(source))
    assert counted == independent, (
        f"the AST walk holds {counted} dispatch terms, the text scan {independent}: {terms}")
    assert sniff_branches() == ["_pdf", "_docx"], (
        f"the byte-sniffing tail is {sniff_branches()}")
    assert len(terms) == len(set(terms)), f"duplicate dispatch term in {terms}"


def test_each_authored_literal_reaches_the_handler_its_writer_means(monkeypatch):
    literals = authored_literals()
    for value in sorted(literals):
        hit = [handler for terms, handler in type_driven_branches()
               if any(term_satisfied(k, value) for k in terms)]
        assert len(hit) == 1, f"{value!r} is claimed by {len(hit)} type-driven branches: {hit}"
        assert route(value, monkeypatch) == hit[0], f"{value!r} routed away from {hit[0]}"

    reached = {k for terms, _ in type_driven_branches() for k in terms
               if any(term_satisfied(k, v) for v in literals)}
    leftovers = {k for terms, _ in type_driven_branches() for k in terms} - reached
    assert leftovers == {("suffix", ".docx"), ("contains", "markdown")}, (
        f"terms no author satisfies moved: {sorted(leftovers)}")

    docs = reads(PY_DOCS)
    call = create_document_call(reads(PY_INGEST))
    names = params(docs, "create_document")
    assert call.args[names.index("file_key")].value is None, (
        "the inline author must keep writing no file key; that is what bypasses the download")
    meta = ast.unparse(call.args[names.index("meta")])
    assert "inline_text" in meta, f"the inline author's payload is no longer text: {meta}"
    assert route(python_inline_literal(), monkeypatch) == "_txt", (
        "inline text is authored with a media type that routes away from the decoder")


def test_nobody_reads_the_media_type_the_download_declares():
    pipeline = ast.parse(reads(PY_PIPELINE))
    calls = [n for n in ast.walk(pipeline)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "extract_text"]
    assert len(calls) == 1, f"extract_text is called {len(calls)} times in pipeline.py"
    second = calls[0].args[1]
    assert (isinstance(second, ast.Subscript) and isinstance(second.slice, ast.Constant)
            and second.slice.value == "media_type"), (
        f"the parser is fed {ast.unparse(second)}, expected the row's media_type")

    population = sorted(APP.rglob("*.py"))
    assert population, "no Python module was read, so the census below read nothing"
    trees = [(f, ast.parse(reads(f))) for f in population]
    read_sites = [(f.name, s) for f, t in trees for s in header_reads(t)]
    write_sites = [(f.name, s) for f, t in trees for s in header_writes(t)]
    assert read_sites == [], f"the answer's declared type is now read: {read_sites}"
    assert write_sites, "the header scanner found no writer either, so it read nothing"

    # A read shaped like the one this guard forbids must be noticed by the same scanner.
    snippet = ast.parse("def f(response):\n"
                        "    declared = response.headers['content-type']\n"
                        "    return declared\n")
    assert header_reads(snippet) == ["response.headers['content-type']"], (
        "the read scanner is blind, so an empty census proved nothing")
    assert '"content-type"' not in reads(PY_PIPELINE), (
        "pipeline.py now spells the response's media type at all")


def test_the_sibling_ingestion_tests_route_values_no_writer_emits():
    """Two claims: the sibling covers every value a writer emits, and it holds extras none emits.

    The coverage half is the one that surprises a reader -- adding a constant to
    `FileValidator.Type` reddens this case until the matching feed exists in test_ingestion.py.
    """
    aliases = {}
    for node in ast.walk(ast.parse(reads(SIBLING))):
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)):
            aliases[node.targets[0].id] = node.value.value

    values = set()
    for node in ast.walk(ast.parse(reads(SIBLING))):
        if not (isinstance(node, ast.Call) and _is_extract_text(node.func)) or len(node.args) < 2:
            continue
        arg = node.args[1]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            values.add(arg.value)
        elif isinstance(arg, ast.Name) and arg.id in aliases:
            values.add(aliases[arg.id])
    assert values, "the sibling tests feed no media type, so the scan read nothing"
    missing = values - authored_literals()
    assert values > authored_literals() and len(missing) >= 4, (
        f"the sibling covers {sorted(values)}; authored {sorted(authored_literals())}")

    # The values no author emits are exactly what the leftover dispatch terms exist for.
    assert any(term_satisfied(("suffix", ".docx"), v) for v in missing), (
        f"no sibling value exercises the .docx suffix term: {sorted(missing)}")
    assert any(term_satisfied(("contains", "markdown"), v) for v in missing), (
        f"no sibling value exercises the markdown term: {sorted(missing)}")
    assert "" in missing, "the blank feed that reaches the sniff fallback is gone"


def _is_extract_text(func: ast.expr) -> bool:
    return (isinstance(func, ast.Name) and func.id == "extract_text"
            or isinstance(func, ast.Attribute) and func.attr == "extract_text")
