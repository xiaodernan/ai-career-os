"""The kinds a knowledge source can be, in one place.

The list used to be written twice -- as a literal in the query-understanding prompt
and as a comment on `knowledge_sources.kind` in the migration -- and nowhere the
model could see it. So a `search_knowledge_base` call could only guess, and a guess
that misses (`notes` for `note`) is dropped by `_clean_kinds`, which turns a scoped
search into an unscoped one without saying so: the answer then cites a job
description when the user asked about their notes.

This tuple is the source of truth. The prompt and the tool schema both derive from
it, and a census test ties it to the migration comment so a new kind cannot appear
in the database alone.
"""

KNOWLEDGE_KINDS: tuple[str, ...] = (
    "resume",
    "project",
    "note",
    "jd",
    "company",
    "interview_feedback",
    "certificate",
    "course",
    "goal",
)

KINDS_INLINE = "|".join(KNOWLEDGE_KINDS)
