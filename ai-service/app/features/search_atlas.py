"""An atlas of the search, drawn only from the reader's own rows (Epic 438).

The product already has a ledger (the timeline) and a story (the chronicle). What
it lacks is a *map*: a finite set of territories a reader can recognise, each with
an honest population drawn from their own data. This module is that map, and it
is deliberately deterministic — no model call, no inference, no invented lore.

A region with zero rows is reported as **unexplored**, not as an error and not as
an absence in the output. The visitor can see the whole world and know which parts
are quiet; silence is a fact about their data, not something to paper over.

The input is the payload the timeline/knowledge screens already build. Nothing
here reaches the database or the network: the caller owns the reads, and this
engine only counts what it is handed.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

# The order is the reading order of the atlas: the board you work, the rooms you
# enter, the words you send, the people you know, the offers you weigh.
REGIONS: tuple[tuple[str, str, str, str], ...] = (
    ("board", "applications", "The board", "申请之板"),
    ("desk", "jobs", "The desk", "职位之案"),
    ("rooms", "interviews", "The rooms", "面试之间"),
    ("letters", "letters", "The letters", "书信之廊"),
    ("notes", "notes", "The notebook", "笔记之册"),
    ("people", "contacts", "The people", "人际之网"),
    ("table", "offers", "The table", "抉择之席"),
)

WORDS: dict[str, dict[str, tuple[str, str]]] = {
    "en": {
        "board": ("{count} applications are on the board — each one a door already knocked on.",
                  "The board is empty — no door has been knocked on in this search yet."),
        "desk": ("{count} saved postings are on the desk — the ground you have already surveyed.",
                 "The desk is clear — no posting has been kept for a closer look yet."),
        "rooms": ("{count} interviews are on record — the rooms you have actually entered.",
                  "No interview room has been entered in this search yet."),
        "letters": ("{count} letters are kept here — the words you sent in your own name.",
                    "No letter has been kept here yet."),
        "notes": ("{count} notes are filed — the small facts you chose to keep.",
                  "The notebook is empty — nothing has been filed here yet."),
        "people": ("{count} contacts are known — the people this search put on your map.",
                   "No contact has been saved in this search yet."),
        "table": ("{count} offers are on the table — the choices this search actually produced.",
                  "Nothing is on the table yet — no offer has been recorded in this search."),
    },
    "zh": {
        "board": ("职位板上有 {count} 条申请——每一扇门你都已经敲过。",
                  "职位板还是空的——这次求职尚未敲过任何一扇门。"),
        "desk": ("案头存着 {count} 条职位——都是你已经勘察过的地面。",
                 "案头是清的——还没有留下任何值得细看的职位。"),
        "rooms": ("已有 {count} 场面试记录在册——那是你真正走进过的房间。",
                  "这次求职还没有走进任何一间面试室。"),
        "letters": ("这里保存着 {count} 封信——都是你以自己的名义寄出的字句。",
                    "这里还没有保存任何信件。"),
        "notes": ("档案里有 {count} 条笔记——都是你选择留下来的小事实。",
                  "笔记本还是空的——这里尚未归档任何内容。"),
        "people": ("你认识 {count} 位联系人——这次求职把他们标在了地图上。",
                   "这次求职还没有保存任何联系人。"),
        "table": ("桌上有 {count} 份录用——这次求职真正产出的选择。",
                  "桌上还空着——这次求职尚未记录任何录用。"),
    },
}


def _count(rows: Any) -> int:
    """Count real rows only. A missing field is zero, not a crash or a guess."""
    if isinstance(rows, (list, tuple)):
        return len(rows)
    if isinstance(rows, Mapping):
        # Some callers send a page envelope; its own `items` is the population.
        items = rows.get("items")
        return len(items) if isinstance(items, (list, tuple)) else 0
    return 0


def search_atlas(payload: Any, *, locale: str = "en") -> dict[str, Any]:
    """Draw the atlas over the rows the caller hands in.

    Returns a dict with `regions` (one per territory, always), `total_evidence`
    (the sum of the real counts) and `locale`. A region is `explored` exactly when
    its own count is greater than zero. The two strings it carries — title and
    field note — come from one vocabulary in one language; nothing is mixed.
    """
    payload = payload if isinstance(payload, Mapping) else {}
    language = "zh" if str(locale or "en").strip().lower().startswith("zh") else "en"
    words = WORDS[language]
    regions: list[dict[str, Any]] = []
    total = 0
    for region_id, key, en_title, zh_title in REGIONS:
        count = _count(payload.get(key))
        total += count
        explored = count > 0
        template = words[region_id][0 if explored else 1]
        regions.append({
            "id": region_id,
            "title": zh_title if language == "zh" else en_title,
            "count": count,
            "explored": explored,
            "note": template.format(count=count) if explored else template,
        })
    return {"regions": regions, "total_evidence": total, "locale": language}
