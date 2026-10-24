"""Agent tool system (PRD §18). Each tool = JSON schema + async handler.

Tools read domain data directly from Postgres (user-scoped) and call feature
modules; writes are minimal and always carry user_id (ownership).
"""

from typing import Any, Callable, Awaitable

from app.core import db
from app.db import domain
from app.providers.base import ToolSpec
from app.providers.registry import embed_text


class Tool:
    def __init__(self, name: str, description: str, parameters: dict,
                 handler: Callable[..., Awaitable[Any]],
                 artifact: str | None = None, agent: str = "career"):
        self.name = name
        self.description = description
        self.parameters = parameters
        self.handler = handler
        self.artifact = artifact  # artifact type emitted from result, if any
        self.agent = agent

    def spec(self) -> ToolSpec:
        return ToolSpec(name=self.name, description=self.description,
                        parameters=self.parameters)


# ---------------- handlers ----------------

# The columns every job search returns, so both retrieval passes agree on shape.
_JOB_COLS = """j.id, j.title, c.name AS company, j.location, j.remote_type,
               j.salary_min, j.salary_max, j.skills, j.posted_at"""

# Reciprocal-rank-fusion constant. 60 is the value from the original RRF paper and
# what the RAG pipeline uses; it flattens the top of each list so a single
# strong-but-unsupported hit cannot outrank agreement between the two retrievers.
_RRF_K = 60


def _filter_fragments(*, skills: list[str] | None = None, location: str = "",
                      remote: str = "", company: str = "", min_salary: int | None = None
                      ) -> list[tuple[str, Any]]:
    """The non-text filters as ``(sql, value)`` with a ``{n}`` placeholder marker.

    Kept separate from the text query so the same filters can be re-numbered for a
    second retrieval pass (the semantic one) without hand-tracking ``$N`` offsets,
    which is how placeholder/value misalignment bugs start.
    """
    out: list[tuple[str, Any]] = []
    # Only iterate a real sequence; a scalar/None handed by a malformed tool call
    # must not raise on `for s in skills` and must not leak a non-array into the
    # `&& ::text[]` bind. The presence check already short-circuits None.
    if isinstance(skills, (list, tuple, set)):
        out.append(("j.skills && ${n}::text[]", [s for s in skills if s]))
    if location:
        out.append(("j.location ILIKE ${n} ESCAPE '!'", db.like_contains(location)))
    if remote:
        out.append(("j.remote_type = ${n}", remote))
    if company:
        out.append(("c.name ILIKE ${n} ESCAPE '!'", db.like_contains(company)))
    # Only a numeric salary floors the query; a string/None stays out of the
    # `>=` bind rather than producing a type-mismatch error at execution time.
    if isinstance(min_salary, (int, float)):
        out.append(("j.salary_max >= ${n}", min_salary))
    return out


def _apply_fragments(where: list[str], args: list, fragments: list[tuple[str, Any]]) -> None:
    """Bind each fragment's value and record its placeholder index in the SQL."""
    for sql, value in fragments:
        args.append(value)
        where.append(sql.replace("{n}", str(len(args))))


def _clamp_limit(value, default: int, cap: int = 25) -> int:
    """A sane page size from a model-supplied value.

    `limit` / `max_questions` arrive as JSON and the model sometimes sends a string,
    a float, or null. `int(...)` on those raises inside the handler, which the
    orchestrator turns into a tool error the model then has to retry; clamping here
    degrades to the default window instead.
    """
    try:
        n = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, min(n, cap))


def _clean_kinds(kinds) -> list[str] | None:
    """A usable source-`kinds` filter, or None.

    The tool schema asks for an array of strings, but JSON can hand a bare string
    ("resume"), a number, or a list with holes. Binding any of those to
    `$N::text[]` fails at execution time and takes every retrieval channel down with
    it, so the filter is normalised here: a lone string becomes a one-element list,
    non-string entries are dropped, and an empty result means "no filter" rather
    than "match nothing".
    """
    if not kinds:
        return None
    raw = [kinds] if isinstance(kinds, str) else kinds
    if not isinstance(raw, (list, tuple, set)):
        return None
    cleaned = [k.strip() for k in raw if isinstance(k, str) and k.strip()]
    return cleaned or None


def validate_tool_args(name: str, schema: dict, args: dict) -> str | None:
    """A human-readable reason `args` violates the tool's schema, or None.

    Only structural violations are rejected -- a missing required property, an
    unknown property, or a container of the wrong shape. Scalar types are left to
    the handler's own coercion: `limit: "5"` is a value the handler knows how to
    read, and rejecting it would turn a usable call into an error.

    The point is the message, not the rejection. Python's own TypeError for a
    missing kwarg names no property the model can add back, and for an unknown one
    it names no property the model may keep. Naming both turns a failed call into
    one the model can correct on the next step instead of repeating.
    """
    if not isinstance(schema, dict):
        return None
    props = schema.get("properties") or {}
    for key in schema.get("required") or []:
        if key not in args:
            return f"missing required property {key!r}"
    if schema.get("additionalProperties") is False:
        unknown = sorted(k for k in args if k not in props)
        if unknown:
            allowed = f" (allowed: {', '.join(sorted(props))})" if props else ""
            return f"unexpected property {unknown[0]!r}{allowed}"
    for key, spec in props.items():
        if key not in args or not isinstance(spec, dict):
            continue
        value, want = args[key], spec.get("type")
        if want == "array" and not isinstance(value, list):
            return f"property {key!r} must be an array"
        if want == "object" and not isinstance(value, dict):
            return f"property {key!r} must be an object"
        if want == "string" and isinstance(value, (list, dict)):
            return f"property {key!r} must be a string"
        if want == "boolean" and not isinstance(value, bool):
            return f"property {key!r} must be a boolean"
    return None


def _search_params(*, query: str = "", skills: list[str] | None = None,
                   location: str = "", remote: str = "", company: str = "",
                   min_salary: int | None = None, limit: int = 10) -> tuple[list[str], list]:
    """Build the WHERE clauses + positional ($N) args for the keyword pass.

    Only integer placeholder indices are ever interpolated into the SQL; every user
    value is returned in ``args`` for asyncpg to bind. The last arg is the clamped
    LIMIT (referenced by the caller's ``LIMIT $len(args)``).

    ``query`` is bound twice: raw for the tsquery/rank side and escaped for the LIKE
    side, which is a distinct placeholder — one value cannot serve both.
    """
    args: list[Any] = [query or ""]  # $1 always bound (used by ts_rank)
    where = ["j.status = 'open'"]
    if query:
        args.append(db.like_contains(query))
        where.append("(j.tsv @@ plainto_tsquery('simple', $1) "
                     f"OR j.title ILIKE ${len(args)} ESCAPE '!')")
    _apply_fragments(where, args, _filter_fragments(
        skills=skills, location=location, remote=remote, company=company,
        min_salary=min_salary))
    # `limit` arrives from the model/peer as JSON and may be a string, None, or a
    # float; clamp so a bad value degrades to the default window instead of raising.
    args.append(_clamp_limit(limit, 10))
    return where, args


async def _embed_query(query: str) -> list[float] | None:
    """Embed a search query, or None when that is not possible.

    Semantic search is an enhancement: if no embedding provider is configured, the
    provider errors, or `jobs.embedding` was never backfilled, the caller must still
    answer with keyword results rather than fail the tool call. The rule itself lives
    in `app.providers.registry.embed_text`, which is what the backend's `/internal/rag/embeddings`
    route hands to the `/jobs` search -- one degradation policy for both callers.
    """
    return await embed_text(query)


async def _semantic_jobs(query: str, fragments: list[tuple[str, Any]], limit: int) -> list:
    """Vector pass over `jobs.embedding`, honouring the same filters as keyword search.

    Reusing `fragments` matters: without the filters this would happily return roles
    that the user's location/salary/skill constraints exclude, and fusion would then
    rank them above matching ones.
    """
    vector = await _embed_query(query)
    if not vector:
        return []
    args: list[Any] = [db.vec(vector)]
    where = ["j.status = 'open'", "j.embedding IS NOT NULL"]
    _apply_fragments(where, args, fragments)
    args.append(limit)
    return await db.fetch(
        f"""SELECT {_JOB_COLS}
            FROM jobs j JOIN companies c ON c.id = j.company_id
            WHERE {' AND '.join(where)}
            ORDER BY j.embedding <=> $1::vector LIMIT ${len(args)}""",
        *args)


def _row_id(row: Any) -> str | None:
    """The job id regardless of whether the row is a dict or a DB Record.

    `db.fetch` returns asyncpg Records, which support ``row["id"]`` and *not*
    attribute access -- ``getattr(row, "id")`` answers None for every real row,
    which silently emptied the fusion and every search the copilot runs. Cached
    rows are dicts. A malformed entry with no id is skipped rather than raising
    mid-fuse.
    """
    if isinstance(row, dict):
        rid = row.get("id")
    else:
        try:
            rid = row["id"]
        except (KeyError, TypeError, IndexError):
            rid = getattr(row, "id", None)
    return str(rid) if rid is not None else None


def _fuse_rrf(keyword_rows: list, semantic_rows: list, limit: int) -> list:
    """Merge the two ranked lists by reciprocal rank, then cut to `limit`.

    Score is Σ 1/(k + rank) across lists, so a job both retrievers found outranks one
    only a single retriever liked — which is the whole point of running two. With an
    empty semantic list the order is exactly the keyword order, so behaviour is
    unchanged wherever embeddings are unavailable.
    """
    scores: dict[str, float] = {}
    rows_by_id: dict[str, Any] = {}
    for rows in (keyword_rows or [], semantic_rows or []):
        for rank, row in enumerate(rows):
            job_id = _row_id(row)
            if job_id is None:
                continue
            rows_by_id.setdefault(job_id, row)
            scores[job_id] = scores.get(job_id, 0.0) + 1.0 / (_RRF_K + rank)
    ordered = sorted(scores, key=lambda j: -scores[j])
    return [rows_by_id[j] for j in ordered[:limit]]


async def search_jobs(user_id: str, *, query: str = "", skills: list[str] | None = None,
                      location: str = "", remote: str = "", company: str = "",
                      min_salary: int | None = None, limit: int = 10) -> dict:
    """Hybrid job search: keyword/tsv fused with vector similarity.

    Keyword alone misses paraphrase ("支付平台" vs "payments platform"); vectors alone
    miss exact tokens (a skill literally named "Go"). Both are filtered identically,
    then fused by reciprocal rank. `user_id` is accepted for the tool contract but
    jobs are a shared catalogue, so it does not scope this query.
    """
    fragments = _filter_fragments(skills=skills, location=location, remote=remote,
                                  company=company, min_salary=min_salary)
    capped = _clamp_limit(limit, 10)

    where, args = _search_params(query=query, skills=skills, location=location,
                                 remote=remote, company=company, min_salary=min_salary,
                                 limit=limit)
    keyword_rows = await db.fetch(
        f"""SELECT {_JOB_COLS}, ts_rank(j.tsv, plainto_tsquery('simple', $1)) AS rank
            FROM jobs j JOIN companies c ON c.id = j.company_id
            WHERE {' AND '.join(where)}
            ORDER BY rank DESC, j.posted_at DESC LIMIT ${len(args)}""",
        *args)

    semantic_rows = await _semantic_jobs(query, fragments, capped) if query.strip() else []
    rows = _fuse_rrf(keyword_rows, semantic_rows, capped)

    return {"jobs": [{"id": str(r["id"]), "title": r["title"], "company": r["company"],
                      "location": r["location"], "remote": r["remote_type"],
                      "salary": [r["salary_min"], r["salary_max"]], "skills": r["skills"]}
                     for r in rows]}


async def get_job(user_id: str, *, job_id: str) -> dict:
    job = await domain.get_job(job_id)
    if not job:
        return {"error": "job not found"}
    match = await db.fetchrow(
        """SELECT * FROM job_matches WHERE user_id=$1::uuid AND job_id=$2::uuid
           ORDER BY created_at DESC LIMIT 1""", user_id, job_id)
    return {"job": {k: (str(v) if k == "id" else v) for k, v in dict(job).items()},
            "cached_match": dict(match) if match else None}


async def get_company(user_id: str, *, company_id: str = "", name: str = "") -> dict:
    if company_id:
        row = await db.fetchrow("SELECT * FROM companies WHERE id=$1::uuid", company_id)
    elif name.strip():
        row = await db.fetchrow(
            "SELECT * FROM companies WHERE name ILIKE $1 ESCAPE '!' LIMIT 1",
            db.like_contains(name))
    else:
        # No term to match on: `ILIKE '%%'` would answer with an unrelated company.
        return {"error": "company lookup needs company_id or name"}
    if not row:
        return {"error": "company not found"}
    open_roles = await db.fetch(
        "SELECT id, title FROM jobs WHERE company_id=$1::uuid AND status='open' LIMIT 10",
        row["id"])
    d = dict(row)
    d["id"] = str(d["id"])
    return {"company": d, "open_roles": [dict(r) for r in open_roles]}


async def parse_resume(user_id: str, *, text: str) -> dict:
    from app.features.resume_parse import compute_resume_score, parse_resume

    parsed = await parse_resume(text, user_id=user_id)
    return {"parsed": parsed, "score": compute_resume_score(parsed)}


async def search_resume(user_id: str, *, query: str, top_k: int = 6) -> dict:
    from app.rag.pipeline import retrieve

    r = await retrieve(query, user_id=user_id, top_k=_clamp_limit(top_k, 6),
                       kinds=["resume", "project"])
    return {"evidence": r["evidence"]}


async def search_knowledge_base(user_id: str, *, query: str, top_k: int = 8,
                                kinds: list[str] | None = None) -> dict:
    from app.rag.pipeline import retrieve

    r = await retrieve(query, user_id=user_id, top_k=_clamp_limit(top_k, 8),
                       kinds=_clean_kinds(kinds))
    return {"evidence": r["evidence"], "context": r.get("context_block", "")[:6000]}


async def analyze_jd(user_id: str, *, raw_text: str) -> dict:
    from app.features.jd_analyze import analyze_jd as _a

    return {"jd": await _a(raw_text, user_id=user_id)}


async def calculate_match(user_id: str, *, job_id: str, resume_version_id: str = "") -> dict:
    job = await domain.get_job(job_id)
    if not job:
        return {"error": "job not found"}
    from app.features.jd_analyze import analyze_jd
    from app.features.match import compute_match, persist_match

    rv = (await domain.get_resume_version(resume_version_id, user_id)
          if resume_version_id
          else await domain.get_current_resume_version(user_id))
    structured = (rv or {}).get("structured")
    import json as _j

    if isinstance(structured, str):
        structured = _j.loads(structured)
    if not rv or not structured:
        return {"error": "no parsed resume; ask the user to upload one"}
    jd = await analyze_jd(job["description"], user_id=user_id)
    result = await compute_match(structured, jd, user_id=user_id, job_id=job_id)
    await persist_match(user_id, job_id, str(rv["id"]), result)
    return {"match": result, "job": {"id": job_id, "title": job["title"],
                                     "company": job.get("company_name")}}


async def generate_resume(user_id: str, *, job_id: str) -> dict:
    from app.features.tailor import tailor

    job = await domain.get_job(job_id)
    if not job:
        return {"error": "job not found"}
    rv = await domain.get_current_resume_version(user_id)
    if not rv:
        return {"error": "no resume"}
    import json as _j

    structured = rv["structured"]
    if isinstance(structured, str):
        structured = _j.loads(structured)
    from app.features.jd_analyze import analyze_jd

    jd = await analyze_jd(job["description"], user_id=user_id)
    out = await tailor(structured, rv.get("plaintext") or "", jd, user_id=user_id,
                       job_title=job["title"])
    return {"tailored": out["tailored"], "diff": out["diff"], "notes": out["notes"],
            "stats": out["stats"], "job_id": job_id}


async def generate_cover_letter(user_id: str, *, job_id: str) -> dict:
    from app.features.cover_letter import generate

    job = await domain.get_job(job_id)
    if not job:
        return {"error": "job not found"}
    rv = await domain.get_current_resume_version(user_id)
    if not rv:
        return {"error": "no resume"}
    import json as _j

    structured = rv["structured"]
    if isinstance(structured, str):
        structured = _j.loads(structured)
    from app.features.jd_analyze import analyze_jd

    jd = await analyze_jd(job["description"], user_id=user_id)
    return await generate(structured, rv.get("plaintext") or "", jd,
                          {"name": job.get("company_name"),
                           "overview": job.get("company_overview")}, "",
                          user_id=user_id)


async def create_interview(user_id: str, *, job_id: str, mode: str = "mixed",
                           max_questions: int = 6) -> dict:
    job = await domain.get_job(job_id)
    if not job:
        return {"error": "job not found"}
    rv = await domain.get_current_resume_version(user_id)
    row = await db.fetchrow(
        """INSERT INTO interview_sessions(user_id, job_id, resume_version_id, company_name,
               position_title, mode, config)
           VALUES ($1::uuid,$2::uuid,$3::uuid,$4,$5,$6,$7::jsonb) RETURNING id""",
        user_id, job_id, str(rv["id"]) if rv else None, job.get("company_name"),
        job.get("title"), mode, db.jsonb({"max_questions": _clamp_limit(max_questions, 6, 50)}))
    return {"session_id": str(row["id"]), "job": job["title"],
            "company": job.get("company_name")}


async def evaluate_answer(user_id: str, *, question: str, answer: str, mode: str =
                          "technical") -> dict:
    from app.features.interview import evaluate_answer as _e

    return {"evaluation": await _e(mode=mode, question=question, answer=answer,
                                   resume_ctx="", user_id=user_id)}


async def save_job(user_id: str, *, job_id: str, note: str = "") -> dict:
    await db.execute(
        """INSERT INTO saved_jobs(user_id, job_id, note) VALUES ($1::uuid,$2::uuid,$3)
           ON CONFLICT DO NOTHING""", user_id, job_id, note)
    await db.execute(
        """INSERT INTO applications(user_id, job_id, title, status, company_name,
               company_id)
           SELECT $1::uuid, j.id, j.title, 'saved', c.name, c.id FROM jobs j
           JOIN companies c ON c.id = j.company_id WHERE j.id = $2::uuid
           AND NOT EXISTS (SELECT 1 FROM applications a WHERE a.user_id=$1::uuid
                           AND a.job_id=$2::uuid AND a.status='saved')""", user_id, job_id)
    return {"saved": True, "job_id": job_id}


async def update_application_status(user_id: str, *, job_id: str = "",
                                    application_id: str = "", status: str) -> dict:
    if status not in ("saved", "applied", "oa", "interview", "final_round", "offer",
                      "rejected"):
        return {"error": "invalid status"}
    if application_id:
        row = await db.fetchrow(
            """UPDATE applications SET status=$3, applied_at=CASE WHEN $3='applied'
                       AND applied_at IS NULL THEN now() ELSE applied_at END
               WHERE id=$1::uuid AND user_id=$2::uuid RETURNING id""",
            application_id, user_id, status)
    elif job_id:
        row = await db.fetchrow(
            """UPDATE applications SET status=$3 WHERE id = (
                 SELECT id FROM applications WHERE user_id=$2::uuid AND job_id=$1::uuid
                 ORDER BY updated_at DESC LIMIT 1) RETURNING id""", job_id, user_id, status)
    else:
        return {"error": "need job_id or application_id"}
    return {"updated": bool(row), "status": status}


# ---------------- networking (Epic 11.4) ----------------

# The columns and the row shape are `domain.CONTACT_COLUMNS` / `domain.contact_row`: the
# follow-up route (#241) reads the same rows for the dashboard tile, and a per-user note
# column is deliberately absent from both -- see the comment on the constant.


async def search_contacts(user_id: str, *, name: str = "", company: str = "",
                          relation: str = "", limit: int = 10) -> dict:
    """Look the user's own contacts up by any of the three ways a person is remembered."""
    args: list[Any] = [user_id]
    where = ["user_id = $1::uuid"]
    if name.strip():
        args.append(db.like_contains(name))
        where.append(f"name ILIKE ${len(args)} ESCAPE '!'")
    if company.strip():
        args.append(db.like_contains(company))
        where.append(f"company ILIKE ${len(args)} ESCAPE '!'")
    if relation.strip():
        args.append(db.like_contains(relation))
        where.append(f"relation ILIKE ${len(args)} ESCAPE '!'")
    args.append(_clamp_limit(limit, 10))
    rows = await db.fetch(
        f"""SELECT {domain.CONTACT_COLUMNS} FROM contacts
            WHERE {' AND '.join(where)}
            ORDER BY last_touch_at DESC NULLS LAST, updated_at DESC
            LIMIT ${len(args)}""", *args)
    return {"contacts": [domain.contact_row(r) for r in rows]}


async def get_follow_ups(user_id: str, *, include_fresh: bool = False,
                         limit: int = 15) -> dict:
    """The contacts that have gone cold, ranked most-neglected first, each with a draft.

    `app/features/reminders.follow_ups_for` owns the ranking and the drafting and
    `domain.list_contacts_for_follow_ups` owns the read -- including why it is ordered
    oldest-touch-first, which is the part a capped follow-up list lives or dies by. This
    handler only carries the agent's own limit through and says whether fresh contacts count.
    """
    from app.features.reminders import follow_ups_for

    contacts = await domain.list_contacts_for_follow_ups(
        user_id, _clamp_limit(limit, 15, 50))
    return {"follow_ups": follow_ups_for(contacts, include_fresh=include_fresh)}


async def draft_outreach(user_id: str, *, contact_id: str, purpose: str = "referral",
                         context: str = "") -> dict:
    """Draft an outreach message for a saved contact, citing only the user's own evidence."""
    import json as _j

    from app.features.outreach import PURPOSES, draft_message

    if purpose not in PURPOSES:
        return {"error": f"unknown purpose {purpose!r}; use one of {sorted(PURPOSES)}"}
    row = await db.fetchrow(
        """SELECT name, role, company, relation FROM contacts
           WHERE id=$1::uuid AND user_id=$2::uuid""", contact_id, user_id)
    if not row:
        return {"error": "contact not found"}
    rv = await domain.get_current_resume_version(user_id)
    structured = (rv or {}).get("structured")
    if isinstance(structured, str):
        structured = _j.loads(structured)
    message = await draft_message(dict(row), purpose, structured or {},
                                  context=context, user_id=user_id)
    return {"contact": dict(row), "message": message}


async def log_contact_touch(user_id: str, *, contact_id: str, note: str = "") -> dict:
    """Stamp a contact as touched now, optionally appending what happened.

    This is the write that keeps `get_follow_ups` honest: a cadence engine that nobody
    can acknowledge goes back to reporting the same person as stale after every chat.
    """
    row = await db.fetchrow(
        """UPDATE contacts
               SET last_touch_at = now(),
                   notes = CASE WHEN $3 = '' THEN notes
                                WHEN notes IS NULL OR notes = '' THEN $3
                                ELSE notes || chr(10) || $3 END,
                   updated_at = now()
             WHERE id = $1::uuid AND user_id = $2::uuid
           RETURNING id, name, last_touch_at""", contact_id, user_id, note)
    if not row:
        return {"error": "contact not found"}
    return {"logged": True, "contact": domain.contact_row(row)}


async def analyze_gap(user_id: str, *, target_role: str, location: str = "",
                     seniority: str | None = None,
                     resume_version_id: str | None = None) -> dict:
    """The distance between the user's profile and a target role.

    The engine (`app/features/gap_analysis.py`) owns the comparison and the
    verdict; this handler only carries the request through. The result is the
    evidence the answer rests on: the coverage, the gaps and the skills the
    profile already covers.
    """
    from app.features.gap_analysis import analyze_gap as _analyze

    structured, plaintext = await _resume_payload(user_id, resume_version_id)
    if structured is None:
        return {"error": "no parsed resume yet -- upload and parse one first"}
    return await _analyze(target_role, seniority, structured, plaintext,
                           user_id=user_id)


async def benchmark_salary(user_id: str, *, role: str, location: str = "",
                           seniority: str | None = None,
                           target_salary: int | None = None,
                           currency: str = "CNY") -> dict:
    """What the seeded corpus pays for a role, by band and location."""
    from app.features.salary import benchmark

    samples = await _job_samples()
    return benchmark(samples, role=role, location=location, seniority=seniority,
                     target_salary=target_salary, currency=currency)


async def compare_offers(user_id: str, *, role: str, offers: list[dict],
                         location: str = "", seniority: str | None = None,
                         match_score: float | None = None,
                         currency: str = "CNY") -> dict:
    """Rank several offers against the market, by total compensation.

    The engine owns the arithmetic: the ranking is by first-year cash plus the
    grant annualized over its vest, while the market verdict compares base to
    the benchmark -- mixing equity into that comparison would be comparing
    unlike quantities.
    """
    from app.features.offers import compare_offers as _compare

    if not offers:
        return {"error": "no offers to compare"}
    samples = await _job_samples()
    report = benchmark(samples, role=role, location=location, seniority=seniority,
                       currency=currency)
    return _compare(offers, report, match_score=match_score)


async def learning_priority(user_id: str, *, target_role: str,
                            location: str = "", seniority: str | None = None,
                            resume_version_id: str | None = None) -> dict:
    """The gaps ranked by importance and by what the market asks for.

    The learning order the engine produces is the one worth acting on: a gap
 * that is both important and in demand comes first.
    """
    from app.features.prioritize import plan_learning_priority

    structured, plaintext = await _resume_payload(user_id, resume_version_id)
    if structured is None:
        return {"error": "no parsed resume yet -- upload and parse one first"}
    samples = await _job_skill_samples()
    return await plan_learning_priority(
        target_role=target_role, resume_structured=structured, samples=samples,
        seniority=seniority, user_id=user_id)


async def _resume_payload(user_id: str, resume_version_id: str | None) -> tuple[dict | None, str]:
    """The user's structured resume and its plaintext, or (None, "") when there is none.

    Shared by the growth tools, so every one of them answers the same way when
    the user has not uploaded a resume: an error the model can read, not a crash.
    """
    import json as _j

    rv = (await domain.get_resume_version(resume_version_id, user_id)
          if resume_version_id else await domain.get_current_resume_version(user_id))
    if not rv:
        return None, ""
    structured = rv.get("structured")
    if isinstance(structured, str):
        structured = _j.loads(structured)
    return structured or {}, rv.get("plaintext") or ""


async def _job_samples() -> list[dict]:
    """The corpus rows the salary benchmark reads."""
    from app.features.salary import load_job_samples

    return await load_job_samples()


async def _job_skill_samples() -> list[dict]:
    """The corpus rows the market-demand engine reads."""
    from app.features.demand import load_job_skill_samples

    return await load_job_skill_samples()


async def get_user_profile(user_id: str) -> dict:
    p = await domain.get_profile(user_id)
    u = await domain.get_user(user_id)
    memories = await domain.get_memories(user_id, limit=15)
    rv = await domain.get_current_resume_version(user_id)
    import json as _j

    structured = (rv or {}).get("structured")
    if isinstance(structured, str):
        structured = _j.loads(structured)
    return {"user": u, "profile": p, "memories": memories,
            "resume_headline": ((structured or {}).get("profile") or {}).get("headline"),
            "skills": [s.get("name") for s in ((structured or {}).get("skills") or [])
                       if isinstance(s, dict)][:30]}


# ---------------- registry ----------------

# Read at registry-build time, not inside the handler, because the schema the model is
# handed must offer the same purposes the handler accepts -- a list the handler checks
# and the schema does not advertise is a tool the model cannot find the right shape for.
from app.features.outreach import PURPOSES as _OUTREACH_PURPOSES


def _t(name, desc, params, fn, artifact=None, agent="career"):
    return Tool(name, desc, params, fn, artifact, agent)


ALL_TOOLS: list[Tool] = [
    _t("search_jobs", "Search open jobs by keyword/skills/location/company/remote/salary.",
       {"type": "object", "properties": {
           "query": {"type": "string"}, "skills": {"type": "array", "items": {"type": "string"}},
           "location": {"type": "string"}, "remote": {"type": "string",
                                                      "enum": ["onsite", "hybrid", "remote"]},
           "company": {"type": "string"}, "min_salary": {"type": "integer"},
           "limit": {"type": "integer", "default": 10}}, "additionalProperties": False},
       search_jobs),
    _t("get_job", "Get full job detail incl. cached match if any.",
       {"type": "object", "properties": {"job_id": {"type": "string"}},
        "required": ["job_id"], "additionalProperties": False}, get_job),
    _t("get_company", "Company intelligence by id or name.",
       {"type": "object", "properties": {"company_id": {"type": "string"},
                                         "name": {"type": "string"}},
        "additionalProperties": False}, get_company),
    _t("parse_resume", "Parse raw resume text into structured profile JSON.",
       {"type": "object", "properties": {"text": {"type": "string"}},
        "required": ["text"], "additionalProperties": False}, parse_resume),
    _t("search_resume", "Semantic search over the user's resume chunks (evidence).",
       {"type": "object", "properties": {"query": {"type": "string"},
                                         "top_k": {"type": "integer", "default": 6}},
        "required": ["query"], "additionalProperties": False}, search_resume),
    _t("search_knowledge_base", "Hybrid RAG retrieval over the career knowledge base.",
       {"type": "object", "properties": {"query": {"type": "string"},
                                         "top_k": {"type": "integer", "default": 8},
                                         "kinds": {"type": "array",
                                                   "items": {"type": "string"}}},
        "required": ["query"], "additionalProperties": False}, search_knowledge_base),
    _t("analyze_jd", "Analyze a pasted job description into structured requirements.",
       {"type": "object", "properties": {"raw_text": {"type": "string"}},
        "required": ["raw_text"], "additionalProperties": False}, analyze_jd),
    _t("calculate_match", "Compute evidence-backed match score for user's resume vs a job.",
       {"type": "object", "properties": {"job_id": {"type": "string"},
                                         "resume_version_id": {"type": "string"}},
        "required": ["job_id"], "additionalProperties": False},
       calculate_match, artifact="match"),
    _t("generate_resume", "Tailor resume for a job (no fabrication; returns diff).",
       {"type": "object", "properties": {"job_id": {"type": "string"}},
        "required": ["job_id"], "additionalProperties": False},
       generate_resume, artifact="tailored_resume", agent="resume"),
    _t("generate_cover_letter", "Generate a cover letter for a job.",
       {"type": "object", "properties": {"job_id": {"type": "string"}},
        "required": ["job_id"], "additionalProperties": False},
       generate_cover_letter, artifact="cover_letter", agent="resume"),
    _t("create_interview", "Start a mock interview session for a job.",
       {"type": "object", "properties": {"job_id": {"type": "string"},
                                         "mode": {"type": "string", "enum":
                                                  ["behavioral", "technical",
                                                   "system_design", "ai_llm", "rag",
                                                   "agent", "backend", "mixed"]},
                                         "max_questions": {"type": "integer",
                                                           "default": 6}},
        "required": ["job_id"], "additionalProperties": False}, create_interview,
       artifact="interview_session"),
    _t("evaluate_answer", "Evaluate one interview answer against a question.",
       {"type": "object", "properties": {"question": {"type": "string"},
                                         "answer": {"type": "string"},
                                         "mode": {"type": "string"}},
        "required": ["question", "answer"], "additionalProperties": False},
       evaluate_answer, agent="interview"),
    _t("save_job", "Bookmark a job and add to Applications(saved) pipeline.",
       {"type": "object", "properties": {"job_id": {"type": "string"},
                                         "note": {"type": "string"}},
        "required": ["job_id"], "additionalProperties": False}, save_job),
    _t("update_application_status", "Move an application between pipeline stages.",
       {"type": "object", "properties": {"job_id": {"type": "string"},
                                         "application_id": {"type": "string"},
                                         "status": {"type": "string", "enum":
                                                    ["saved", "applied", "oa",
                                                     "interview", "final_round",
                                                     "offer", "rejected"]}},
        "required": ["status"], "additionalProperties": False},
       update_application_status, agent="tracker"),
    _t("get_user_profile", "User's profile, goals, memories and resume headline.",
       {"type": "object", "properties": {}, "additionalProperties": False},
       get_user_profile),
    _t("search_contacts", "Look up the user's saved contacts by name, company or relation.",
       {"type": "object", "properties": {"name": {"type": "string"},
                                         "company": {"type": "string"},
                                         "relation": {"type": "string"},
                                         "limit": {"type": "integer", "default": 10}},
        "additionalProperties": False}, search_contacts, agent="networking"),
    _t("get_follow_ups", "Contacts gone cold against their relation's cadence, ranked, "
       "each with a draft follow-up.",
       {"type": "object", "properties": {"include_fresh": {"type": "boolean",
                                                           "default": False},
                                         "limit": {"type": "integer", "default": 15}},
        "additionalProperties": False}, get_follow_ups, agent="networking"),
    _t("draft_outreach", "Draft an outreach message for a saved contact, citing only "
       "the user's own evidence.",
       {"type": "object", "properties": {"contact_id": {"type": "string"},
                                         "purpose": {"type": "string",
                                                     "enum": sorted(_OUTREACH_PURPOSES)},
                                         "context": {"type": "string"}},
        "required": ["contact_id"], "additionalProperties": False},
       draft_outreach, agent="networking"),
    _t("log_contact_touch", "Mark a contact as touched now; optionally append what happened.",
       {"type": "object", "properties": {"contact_id": {"type": "string"},
                                         "note": {"type": "string"}},
        "required": ["contact_id"], "additionalProperties": False},
       log_contact_touch, agent="networking"),
    _t("analyze_gap", "The distance between the user's profile and a target role: the "
       "coverage, the gaps and the skills already covered.",
       {"type": "object", "properties": {"target_role": {"type": "string"},
                                         "location": {"type": "string"},
                                         "seniority": {"type": "string"},
                                         "resume_version_id": {"type": "string"}},
        "required": ["target_role"], "additionalProperties": False},
       analyze_gap, artifact="gap_report", agent="learning"),
    _t("benchmark_salary", "What the job corpus pays for a role, by band and location.",
       {"type": "object", "properties": {"role": {"type": "string"},
                                         "location": {"type": "string"},
                                         "seniority": {"type": "string"},
                                         "target_salary": {"type": "integer"},
                                         "currency": {"type": "string", "default": "CNY"}},
        "required": ["role"], "additionalProperties": False},
       benchmark_salary, artifact="salary_band", agent="learning"),
    _t("compare_offers", "Rank several offers against the market by total compensation.",
       {"type": "object", "properties": {
           "role": {"type": "string"},
           "location": {"type": "string"},
           "seniority": {"type": "string"},
           "match_score": {"type": "number"},
           "currency": {"type": "string", "default": "CNY"},
           "offers": {"type": "array", "items": {
               "type": "object",
               "properties": {
                   "label": {"type": "string"},
                   "base": {"type": "integer"},
                   "bonus": {"type": "integer", "default": 0},
                   "equity": {"type": "object", "properties": {
                       "shares": {"type": "integer"},
                       "strike_price": {"type": "number"},
                       "current_price": {"type": "number"},
                       "vest_years": {"type": "integer"}}}}}}},
        "required": ["role", "offers"], "additionalProperties": False},
       compare_offers, artifact="offer_comparison", agent="learning"),
    _t("learning_priority", "The user's gaps ranked by importance and by what the "
       "market asks for -- the order to learn them in.",
       {"type": "object", "properties": {"target_role": {"type": "string"},
                                         "location": {"type": "string"},
                                         "seniority": {"type": "string"},
                                         "resume_version_id": {"type": "string"}},
        "required": ["target_role"], "additionalProperties": False},
       learning_priority, artifact="learning_priority", agent="learning"),
]

TOOL_INDEX = {t.name: t for t in ALL_TOOLS}

SUBAGENT_TOOLS: dict[str, list[str]] = {
    "resume": ["parse_resume", "search_resume", "generate_resume",
               "generate_cover_letter", "search_knowledge_base", "get_user_profile"],
    "job_research": ["search_jobs", "get_job", "get_company", "search_knowledge_base",
                     "get_user_profile"],
    "jd_analyst": ["analyze_jd", "calculate_match", "get_job", "search_resume"],
    "rag": ["search_knowledge_base", "search_resume"],
    "interview": ["create_interview", "evaluate_answer", "get_job", "search_resume"],
    # The learning subagent also holds the deterministic growth engines (Epics
    # 10.x, 12.x): the gap the profile has, what the market pays, which offer
    # leads, and the order to learn the gaps in. All four read the corpus and the
    # user's own resume -- no writes, and no other surface's data.
    "learning": ["search_knowledge_base", "get_user_profile", "get_job",
                 "analyze_gap", "benchmark_salary", "compare_offers",
                 "learning_priority"],
    "tracker": ["save_job", "update_application_status", "search_jobs", "get_job"],
    "networking": ["search_contacts", "get_follow_ups", "draft_outreach",
                   "log_contact_touch", "get_user_profile"],
}
