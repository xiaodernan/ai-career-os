"""Agent tool system (PRD §18). Each tool = JSON schema + async handler.

Tools read domain data directly from Postgres (user-scoped) and call feature
modules; writes are minimal and always carry user_id (ownership).
"""

from typing import Any, Callable, Awaitable

from app.core import db
from app.db import domain
from app.providers.base import ToolSpec


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

def _search_params(*, query: str = "", skills: list[str] | None = None,
                   location: str = "", remote: str = "", company: str = "",
                   min_salary: int | None = None, limit: int = 10) -> tuple[list[str], list]:
    """Build the WHERE clauses + positional ($N) args for search_jobs.

    Only integer placeholder indices are ever interpolated into the SQL; every user
    value is returned in ``args`` for asyncpg to bind. The last arg is the clamped
    LIMIT (referenced by the caller's ``LIMIT $len(args)``).
    """
    args: list[Any] = [query or ""]  # $1 always bound (used by ts_rank)
    where = ["j.status = 'open'"]
    if query:
        where.append("(j.tsv @@ plainto_tsquery('simple', $1) "
                     "OR j.title ILIKE '%'||$1||'%')")
    if skills:
        args.append([s for s in skills if s])
        where.append(f"j.skills && ${len(args)}::text[]")
    if location:
        args.append(location)
        where.append(f"j.location ILIKE '%'||${len(args)}||'%'")
    if remote:
        args.append(remote)
        where.append(f"j.remote_type = ${len(args)}")
    if company:
        args.append(company)
        where.append(f"c.name ILIKE '%'||${len(args)}||'%'")
    if min_salary:
        args.append(min_salary)
        where.append(f"j.salary_max >= ${len(args)}")
    args.append(max(1, min(int(limit), 25)))
    return where, args


async def search_jobs(user_id: str, *, query: str = "", skills: list[str] | None = None,
                      location: str = "", remote: str = "", company: str = "",
                      min_salary: int | None = None, limit: int = 10) -> dict:
    where, args = _search_params(query=query, skills=skills, location=location,
                                 remote=remote, company=company, min_salary=min_salary,
                                 limit=limit)
    rows = await db.fetch(
        f"""SELECT j.id, j.title, c.name AS company, j.location, j.remote_type,
                   j.salary_min, j.salary_max, j.skills, j.posted_at,
                   ts_rank(j.tsv, plainto_tsquery('simple', $1)) AS rank
            FROM jobs j JOIN companies c ON c.id = j.company_id
            WHERE {' AND '.join(where)}
            ORDER BY rank DESC, j.posted_at DESC LIMIT ${len(args)}""",
        *args)
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
    else:
        row = await db.fetchrow("SELECT * FROM companies WHERE name ILIKE $1 LIMIT 1",
                                f"%{name}%")
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

    r = await retrieve(query, user_id=user_id, top_k=top_k, kinds=["resume", "project"])
    return {"evidence": r["evidence"]}


async def search_knowledge_base(user_id: str, *, query: str, top_k: int = 8,
                                kinds: list[str] | None = None) -> dict:
    from app.rag.pipeline import retrieve

    r = await retrieve(query, user_id=user_id, top_k=top_k, kinds=kinds)
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
        job.get("title"), mode, db.jsonb({"max_questions": int(max_questions)}))
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
    "learning": ["search_knowledge_base", "get_user_profile", "get_job"],
    "tracker": ["save_job", "update_application_status", "search_jobs", "get_job"],
}
