"""Read-only access to domain tables (rows are written by the backend)."""

from app.core import db


async def get_resume_version(rv_id: str, user_id: str) -> dict | None:
    row = await db.fetchrow(
        """SELECT rv.*, r.title AS resume_title FROM resume_versions rv
           JOIN resumes r ON r.id = rv.resume_id
           WHERE rv.id=$1::uuid AND rv.user_id=$2::uuid""", rv_id, user_id)
    return dict(row) if row else None


async def get_current_resume_version(user_id: str) -> dict | None:
    row = await db.fetchrow(
        """SELECT rv.* FROM resume_versions rv
           JOIN resumes r ON r.id = rv.resume_id
           WHERE rv.user_id=$1::uuid AND (r.current_version_id = rv.id OR TRUE)
           ORDER BY (r.current_version_id = rv.id) DESC, rv.created_at DESC LIMIT 1""",
        user_id)
    return dict(row) if row else None


async def get_job(job_id: str) -> dict | None:
    row = await db.fetchrow(
        """SELECT j.*, c.name AS company_name, c.tech_stack AS company_tech_stack,
                  c.overview AS company_overview, c.industry
           FROM jobs j JOIN companies c ON c.id = j.company_id WHERE j.id=$1::uuid""",
        job_id)
    return dict(row) if row else None


async def get_jd(jd_id: str, user_id: str) -> dict | None:
    row = await db.fetchrow("SELECT * FROM job_jds WHERE id=$1::uuid AND user_id=$2::uuid",
                            jd_id, user_id)
    return dict(row) if row else None


async def get_profile(user_id: str) -> dict | None:
    row = await db.fetchrow("SELECT * FROM user_profiles WHERE user_id=$1::uuid", user_id)
    return dict(row) if row else None


async def get_user(user_id: str) -> dict | None:
    row = await db.fetchrow("SELECT id, email, display_name FROM users WHERE id=$1::uuid",
                            user_id)
    return dict(row) if row else None


async def get_interview_session(session_id: str, user_id: str) -> dict | None:
    row = await db.fetchrow(
        """SELECT s.*, j.title AS job_title, c.name AS company_name, c.tech_stack,
                  c.interview_process
           FROM interview_sessions s
           LEFT JOIN jobs j ON j.id = s.job_id
           LEFT JOIN companies c ON c.id = j.company_id
           WHERE s.id=$1::uuid AND s.user_id=$2::uuid""", session_id, user_id)
    return dict(row) if row else None


async def list_turns(session_id: str) -> list[dict]:
    rows = await db.fetch(
        "SELECT * FROM interview_turns WHERE session_id=$1::uuid ORDER BY seq", session_id)
    return [dict(r) for r in rows]


async def get_memories(user_id: str, kinds: list[str] | None = None, limit: int = 20) -> list[dict]:
    rows = await db.fetch(
        """SELECT kind, key, content, importance FROM user_memories
           WHERE user_id=$1::uuid AND ($2::text[] IS NULL OR kind = ANY($2))
           ORDER BY importance DESC, updated_at DESC LIMIT $3""",
        user_id, kinds, limit)
    return [dict(r) for r in rows]


async def upsert_memory(user_id: str, kind: str, key: str, content: str, source: str,
                        importance: float = 0.6) -> None:
    await db.execute(
        """INSERT INTO user_memories(user_id, kind, key, content, source, importance)
           VALUES ($1::uuid,$2,$3,$4,$5,$6)
           ON CONFLICT (user_id, kind, key) DO UPDATE
             SET content = EXCLUDED.content, importance = GREATEST(user_memories.importance,
                 EXCLUDED.importance), source = EXCLUDED.source""",
        user_id, kind, key[:100], content[:4000], source, importance)
