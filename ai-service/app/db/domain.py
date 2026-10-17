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


async def list_memories(user_id: str, kinds: list[str] | None = None,
                        limit: int = 100) -> list[dict]:
    """Every memory the user carries, including the id needed to edit it.

    `get_memories` reads what the prompt needs and stops at 20. This is the other job —
    the surface a user reads to find the sentence the model got wrong — so it returns the
    row's own id and carries a limit the default list is allowed to be bigger than.
    """
    rows = await db.fetch(
        """SELECT id, kind, key, content, importance, source, created_at, updated_at
             FROM user_memories
            WHERE user_id=$1::uuid AND ($2::text[] IS NULL OR kind = ANY($2))
            ORDER BY updated_at DESC, importance DESC LIMIT $3""",
        user_id, kinds, limit)
    return [dict(r) for r in rows]


async def update_memory(user_id: str, memory_id: str, *, content: str | None = None,
                        importance: float | None = None) -> dict | None:
    """Re-write one memory's content and/or its weight. Returns the row, or None.

    Both fields are optional because they are corrected independently: a wrong fact needs
    the text fixed, while a fact the user is tired of being reminded about only needs its
    importance lowered. An empty patch is a no-op that still returns the current row, so
    the caller never has to tell "nothing changed" from "it is gone".

    `user_id` in the WHERE is the whole ownership rule: an id belonging to somebody else
    does not update, it returns None.
    """
    sets: list[str] = []
    args: list = [memory_id, user_id]
    if content is not None:
        sets.append(f"content=${len(args) + 1}")
        args.append(content)
    if importance is not None:
        sets.append(f"importance=${len(args) + 1}")
        args.append(importance)
    returning = ("SELECT id, kind, key, content, importance, source, "
                 "created_at, updated_at FROM user_memories")
    if not sets:
        row = await db.fetchrow(returning + " WHERE id=$1::uuid AND user_id=$2::uuid",
                                memory_id, user_id)
        return dict(row) if row else None
    sql = (f"UPDATE user_memories SET {', '.join(sets)} "
           "WHERE id=$1::uuid AND user_id=$2::uuid "
           "RETURNING id, kind, key, content, importance, source, "
           "created_at, updated_at")
    row = await db.fetchrow(sql, *args)
    return dict(row) if row else None


async def delete_memory(user_id: str, memory_id: str) -> bool:
    """Forget one memory. Returns whether a row was actually the caller's.

    The only way out of a wrong fact: the extraction path only ever adds, so a sentence
    the model invented would otherwise be quoted back at the user on every later turn.

    `RETURNING` rather than `db.execute`'s status string: asyncpg's `execute` answers
    "DELETE 0" for a row that was not there, which is a non-empty string and therefore
    truthy — an existence question answered by a truthiness check on prose.
    """
    row = await db.fetchrow(
        "DELETE FROM user_memories WHERE id=$1::uuid AND user_id=$2::uuid RETURNING id",
        memory_id, user_id)
    return row is not None


async def upsert_memory(user_id: str, kind: str, key: str, content: str, source: str,
                        importance: float = 0.6) -> None:
    await db.execute(
        """INSERT INTO user_memories(user_id, kind, key, content, source, importance)
           VALUES ($1::uuid,$2,$3,$4,$5,$6)
           ON CONFLICT (user_id, kind, key) DO UPDATE
             SET content = EXCLUDED.content, importance = GREATEST(user_memories.importance,
                 EXCLUDED.importance), source = EXCLUDED.source""",
        user_id, kind, key[:100], content[:4000], source, importance)


# ---------------- contacts (Epic 11.1, written by the backend's /api/v1/contacts) ----------------

# The fields every contact reader hands on. `id` is what links a row back to the registry
# page and `name/company/relation` are the only three things a follow-up draft may cite, so
# a narrower select answers with rows a caller can neither draft from nor address.
#
# `notes` is left out on purpose. It is the user's free text about a person, and a contact
# read also feeds a model prompt -- where a stray "their brother works at X" becomes
# something the agent may repeat back.
CONTACT_COLUMNS = "id, name, role, company, relation, email, last_touch_at"


def contact_row(row) -> dict:
    """One contacts row in the shape its readers pass on: string id, ISO touch stamp.

    asyncpg gives back a `uuid` and a `TIMESTAMPTZ`. The first is not JSON-serialisable and
    the second is handed straight to `reminders._parse`, which reads text -- so a reader that
    skips this normaliser either breaks the response or makes every contact look
    never-touched, which the cadence engine then reports as overdue.
    """
    d = dict(row)
    d["id"] = str(d["id"])
    touched = d.get("last_touch_at")
    d["last_touch_at"] = touched.isoformat() if hasattr(touched, "isoformat") else touched
    return d


async def list_contacts_for_follow_ups(user_id: str, limit: int) -> list[dict]:
    """The caller's contacts, most-neglected first -- the order a *capped* read needs.

    The registry page lists newest touch first, which is right when the whole list is shown
    and wrong when it is cut: the neglected people sit at the far end of `last_touch_at`, so
    copying the page's ordering would discard exactly the rows a follow-up surface exists to
    return. `NULLS FIRST` because a contact with no recorded touch is the most neglected one
    in the registry, not the least datable.
    """
    rows = await db.fetch(
        f"""SELECT {CONTACT_COLUMNS} FROM contacts
            WHERE user_id=$1::uuid
            ORDER BY last_touch_at ASC NULLS FIRST, updated_at ASC LIMIT $2""",
        user_id, max(1, min(int(limit), 50)))
    return [contact_row(r) for r in rows]
