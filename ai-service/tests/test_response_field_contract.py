"""Per-read-site liveness: every key a browser mapper tries off a Java record's answer.

`test_response_shape_contract.py` checks the DTO-backed readers coarsely -- "at least one of the
names this function mentions is a component of the record". That survives the mistake that matters
least (a record renamed or moved, which the coarse assertion names loudly) and not the one that
matters most (a field renamed inside a record nobody renames): `ApplicationItem` renaming `notes`
would leave every other name in the function alive, so the coarse gate stays green while the
pipeline card loses its note forever. TypeScript cannot see it either, because the wire shape is
typed by hand in `types.ts` rather than derived from the record.

So the rule here is per call site, and per map. A site is one accessor call -- `str(raw, "a", "b")`
-- and it is live when at least one name it tries is a component of the record that produced the
object it reads from. A site with no live name can only ever answer with its fallback value, which
renders as a blank, a zero or `undefined`, never as an error.

Which record a site reads against is decided by its receiver, so a reader that drills a nested map
gets that map's own record instead of having its reads merged into the parent's -- the mixing the
coarse gate warns about. The links (receiver -> record, and how the local was obtained) are the
only hand-authored part; both sides come from sources, and a receiver the table does not know is an
error rather than a skip.

`@JsonAlias` does not help on this direction: it steers deserialisation only, and the backend has no
snake_case naming strategy, so a `company_name` candidate against a record is dead weight that a
live sibling in the same list saves. Only a site with *no* live name is a defect, and those are a
declared, shrink-only list.

The producer on the other side is not always a Java record. `normalizeMatch` reads a map the backend
hands over from the AI service -- `MatchResult.model_dump()` -- so its class body is the wire shape,
and a model is as static as a record. One local can also answer to *two* producers when the endpoint
and the persisted row disagree about where the same score lives (`MatchResult` for a fresh match,
`MatchSummary` for the stored one the job detail replays); such a receiver is bound to both, and a
site is live if either one emits a name it tries. That is weaker than one record per map, so the
weaker binding is only used where the response really has two authors.
"""

import ast
import json
import re
from functools import lru_cache
from pathlib import Path

from tests.test_response_shape_contract import (
    JAVA_ROOT,
    NORMALIZE,
    _record_components_at,
    _shape_of,
    _sole,
    pydantic_fields,
)

# What puts keys on the wire for one map: a Java record (path given), or a Pydantic model, whose
# annotated fields `model_dump()` emits verbatim.
PRODUCERS = {
    "ApplicationItem": ("java", "application/dto/ApplicationDtos.java"),
    "CompanyItem": ("java", "job/dto/JobDtos.java"),
    "MessageItem": ("java", "conversation/dto/ConversationDtos.java"),
    "MatchResponse": ("java", "job/dto/JobDtos.java"),
    "JobDetail": ("java", "job/dto/JobDtos.java"),
    "JobListItem": ("java", "job/dto/JobDtos.java"),
    "SavedJobItem": ("java", "job/dto/JobDtos.java"),
    "MatchSummary": ("java", "job/dto/JobDtos.java"),
    "MatchResult": ("pydantic",),
    "SearchResponse": ("java", "search/dto/SearchDtos.java"),
    "JobHit": ("java", "search/dto/SearchDtos.java"),
    "CompanyHit": ("java", "search/dto/SearchDtos.java"),
    "ResumeHit": ("java", "search/dto/SearchDtos.java"),
    "NoteHit": ("java", "search/dto/SearchDtos.java"),
    "ConversationHit": ("java", "search/dto/SearchDtos.java"),
    "ApplicationHit": ("java", "search/dto/SearchDtos.java"),
    "DashboardResponse": ("java", "report/dto/DashboardDtos.java"),
    "Kanban": ("java", "report/dto/DashboardDtos.java"),
    "ResumeSummary": ("java", "report/dto/DashboardDtos.java"),
    "SkillGapDigest": ("java", "report/dto/DashboardDtos.java"),
    "SkillGap": ("pydantic",),
    "ResumeDetail": ("java", "resume/dto/ResumeDtos.java"),
    "ResumeVersionItem": ("java", "resume/dto/ResumeDtos.java"),
    # The resume score map has no model and no record: `compute_resume_score` answers with one
    # return literal and `ResumeService.persistParse` stores that dict verbatim into a jsonb column,
    # so the literal *is* the wire shape -- and `test_response_shape_contract` walks the very same
    # literal to learn what the parse endpoint carries. `RubricCheck` is one item of its `detail`
    # list, whose keys the function states once, in the `detail.append(...)` it loops over.
    "ResumeScoreMap": ("pyfunc", "compute_resume_score"),
    "RubricCheck": ("pyappend", ("compute_resume_score", "detail")),
    "RecentRun": ("java", "report/dto/DashboardDtos.java"),
    "RunItem": ("java", "activity/web/ActivityController.java"),
    # The interview report has no record for its body: `EvaluationItem.summary` is a
    # `Map<String, Object>` whose keys exist only because the finalize prompt asks for them, so
    # `FINALIZE_FIELDS` / `STUDY_ITEM_FIELDS` state them as data and this reads the declaration
    # rather than a list copied into the table.
    "SessionDetail": ("java", "interview/dto/InterviewDtos.java"),
    "FinalizeResponse": ("java", "interview/dto/InterviewDtos.java"),
    "EvaluationItem": ("java", "interview/dto/InterviewDtos.java"),
    "FinalizeReport": ("pyconst", ("app/features/interview.py", "FINALIZE_FIELDS")),
    "StudyItem": ("pyconst", ("app/features/interview.py", "STUDY_ITEM_FIELDS")),
    # `trajectory_detail` is written by `finalize` rather than asked of the model, and a trajectory
    # row is the dict literal `_trajectory_detail` builds -- neither has a record, and both are
    # stated exactly once in the source that produces them.
    "FinalizeComputed": ("pyconst", ("app/features/interview.py", "FINALIZE_COMPUTED_FIELDS")),
    "TrajectoryRow": ("pyitem", "_trajectory_detail"),
    # The current question is a turn row, and the one free map on it carries what the runner shows
    # beside the text. Two authors put keys into `interview_turns.question_meta` -- the follow-up
    # `meta` the answer handler builds, and the opening `meta` ai-service returns and the handler
    # stores verbatim -- so each is read from its own source and bound separately: a union of the
    # two would let either rename `topic` in silence (#133, #141).
    "TurnItem": ("java", "interview/dto/InterviewDtos.java"),
    "QuestionMetaFollowup": ("japut", ("interview/service/InterviewService.java", "answer")),
    "QuestionMetaOpening": ("pyfunc", "opening_meta"),
    # The JD analysis is one record wrapped around no record at all: `JdItem.parsed` is a `Map` the
    # backend fills verbatim from ai-service's answer (`JobService:244 jd.setParsed(...)`), and that
    # answer's keys exist because the analyze prompt draws them. The skeleton is valid JSON, so
    # `pyskel` parses the list out of the prompt instead of reading a tuple transcribed beside it --
    # a transcription is the drift this gate exists to catch, dressed up as a contract.
    "JdItem": ("java", "job/dto/JobDtos.java"),
    "JdAnalysisMap": ("pyskel", ("app/features/jd_analyze.py", "SYSTEM", ())),
    "JdRequiredItem": ("pyskel", ("app/features/jd_analyze.py", "SYSTEM", ("requiredSkills",))),
    "JdPreferredItem": ("pyskel", ("app/features/jd_analyze.py", "SYSTEM", ("preferredSkills",))),
    # ...and the deterministic second author of a skill item: the dictionary-extracted skills the
    # model missed, appended by `_backfill_skills` in the shape it asks the model for.
    "JdBackfilledItem": ("pyappend", ("_backfill_skills", "preferred")),
    # /jds/suggestions is relayed untouched by JobService: one handler author for the wrapper, one
    # rule-engine author for the cards inside it.
    "SuggestionEnvelope": ("pyfunc", "suggestions_ep"),
    "SuggestionItem": ("pyappend", ("suggest_resume_improvements", "out")),
}

# Readers whose producers are known per map. A reader with more producers than one is bound to their
# **union** -- weaker than one record per map, so it is only taken where the same mapper really is
# fed several endpoints (`normalizeJob` answers for JobListItem, JobDetail and SavedJobItem, which
# disagree about `match`/`matchOverall`/`company`), and a site then has to be missed by *every*
# author to count as dead.
#
#   record_of  receiver -> producer(s) it is read against; a list is the union of several
#   drilled    local -> (parent receiver, key drilled out of it). Every bound local the body builds
#              by drilling has to appear here: the link is what `_broken_links` re-checks and what
#              `_hollow_drills` compares to the parent record, so an undeclared one leaves the step
#              where a wrong key silently yields `{}` unverified.
#   elements   local -> parent receiver, when it is a `.map((local, i) …)` element
#   blind      receiver -> why no record can answer for it
#   dynamic    receiver -> why its names come from a variable rather than a call site, and which
#              source-derived rule checks them instead (an unexplained entry is not allowed)
READERS: dict[str, dict] = {
    "normalizeDashboard": {
        # One endpoint and one record: `useDashboard` calls `GET /reports/dashboard`, and `api.get`
        # unwraps the {success,data} envelope before the mapper sees the body, so `d` *is* the
        # DashboardResponse. The reader opened with `pick(raw, "dashboard", "data")` anyway and hung
        # a `metrics`/`stats`/`summary` layer off that -- 26 of its 41 sites had no author at all,
        # including five whole returned fields (`pipelineItems`, `suggestion`, `insights`,
        # `attention`, `empty`), the `normalizeResumeScore(d)` fallback (`d` has no `score`), and the
        # flat numeric aliases (`applicationCount`, `in_pipeline`, `offerCount`, `gapCount`, …).
        # `recentActivity` is the one component the mapper still never reads, and says so below.
        "record_of": {"d": "DashboardResponse", "kanban": "Kanban",
                      "currentResume": "ResumeSummary", "skillGapDigest": "SkillGapDigest"},
        "drilled": {"kanban": ("d", "kanban"),
                    "currentResume": ("d", "currentResume"),
                    "skillGapDigest": ("d", "skillGaps")},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizePipeline": {
        # The pipeline widget's own fetcher, and it is handed the same body twice:
        # `useDashboardPipeline` GETs /reports/dashboard, and `normalizeDashboard` passes on the
        # payload it already unwrapped. `DashboardResponse` has no `pipeline` component -- the
        # per-stage counts are `kanban.statusCounts` -- so the reader's array-of-stages branch and
        # the `pipeline`/`stages`/`applicationPipeline` probe feeding it, reachable only from a test
        # fixture, are #130's deletions. The stage names inside `statusCounts` are *data* (a
        # `Map<String, Long>` the service builds by iterating `ApplicationStatus`), not record
        # components, so `statusCountsToRows` walks `Object.entries` instead of naming one: that is
        # why this reader has two sites and not one per stage.
        "record_of": {"raw": "DashboardResponse", "kanban": "Kanban"},
        "drilled": {"kanban": ("raw", "kanban")},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeResumeScore": {
        # The rubric map the parsing run persisted, reached from three callers that all carry it:
        # the dashboard's `currentResume` is a `ResumeSummary`, `useResume` hands over a
        # `ResumeDetail`, and `mapResumeVersions` a `ResumeVersionItem`. The last of those is #134's
        # change -- the versions panel had been reading a per-version score off a DTO that never
        # projected the column, so the suffix had never rendered once. #132 deleted the rest of what
        # this reader used to ask for: the
        # `resumeScore`/`resume_score` twins, `overall`/`score` beside the real `total`, the
        # `checks`/`criteria`/`ok`/`passed`/`name`/`why` alternates, an explicit `gaps` list no
        # producer writes (the unmet criteria *are* the gaps), `suggestions`, `computedAt`, and the
        # `?? raw` + bare-number branches no caller could reach.
        "record_of": {"raw": ["ResumeDetail", "ResumeSummary", "ResumeVersionItem"],
                      "s": "ResumeScoreMap", "c": "RubricCheck"},
        "drilled": {"s": ("raw", "score")},
        "elements": {"c": "s"},
        "blind": {},
        "dynamic": {},
    },
    "normalizeRun": {
        # Two records, one reader: the dashboard's `recentRuns` are `RecentRun`s and
        # `GET /activity/runs` answers a bare `List<RunItem>`. Neither is snake_case (the backend has
        # no naming strategy on this direction), and neither carries `traces` -- those belong to
        # `RunDetail`, which the activity detail page hands to `activity-trace` after unwrapping
        # `run`. #133 deleted the four authorless reads that confusion left behind (`traces`,
        # `summary`, `createdAt`, `relatedHref`), the snake aliases beside every live name, and the
        # `useActivityRun` hook that passed `normalizeRun` the envelope instead of the run.
        "record_of": {"raw": ["RecentRun", "RunItem"]},
        "drilled": {},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeInterviewReport": {
        # The report page reads `EvaluationItem` (from `SessionDetail.evaluation` or the
        # `FinalizeResponse` the finalize POST returns), and `summary` is one of those Java
        # records' two free `Map<String, Object>` components -- so the scalar half of the report has
        # no record behind it at all. `FINALIZE_FIELDS` is that half made into data
        # (`#135`/`#136`), which is why `merged` -- the object spread of the item and its summary
        # map -- can be bound to both producers instead of excused. It is deliberately *not* in
        # `drilled`: a spread is not a `pick`, so the link rule would be checking a call that does
        # not exist. #137 trimmed the reader to these names first; this entry is what that trim is
        # checked against.
        "record_of": {"raw": ["SessionDetail", "FinalizeResponse"],
                      "ev": "EvaluationItem",
                      "merged": ["EvaluationItem", "FinalizeReport", "FinalizeComputed"],
                      "s": "StudyItem"},
        "drilled": {"ev": ("raw", "evaluation")},
        "elements": {"s": "merged"},
        "blind": {},
        "dynamic": {},
    },
    "normalizeTrajectory": {
        # The fold that turns the evaluator's per-turn rows into one point per question. Where its
        # list lives is named from a constant -- `list(source, ...TRAJECTORY_KEYS)` -- so the reach is
        # a dynamic receiver and `_trajectory_keys` is what ties that constant to the producers: the
        # rows arrive as `EvaluationItem.trajectory`, or as the `trajectory_detail` key `finalize`
        # writes into the report map. The rows themselves are `_trajectory_detail`'s literal.
        # `t`/`row` are deliberately not in `elements`: one is the parameter of an arrow assigned to
        # `plain`, the other of `rows.forEach`, and neither is a `.map` callback the link rule could
        # point at -- binding them to the row producer is what still checks every name they read.
        "record_of": {"t": "TrajectoryRow", "row": "TrajectoryRow"},
        "drilled": {},
        "elements": {},
        "blind": {},
        "dynamic": {
            "source": "`list(source, ...TRAJECTORY_KEYS)` spreads the candidate list names from a "
                      "module constant, so no literal name exists at the call site; "
                      "`_trajectory_keys` ties those names to the producers that carry them",
        },
    },
    "normalizeInterviewDims": {
        # `EvaluationItem.dims` is the jsonb copy of the report's dimension map, and the report map
        # itself carries the same key, so the two producers agree on the one name this reader
        # reaches for. #141: it used to spread that name over four candidates and walk an array form
        # plus an object-valued form that no producer emits -- six sites, one of them authored.
        "record_of": {"raw": ["EvaluationItem", "FinalizeReport"]},
        "drilled": {},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeQuestion": {
        # One shape reaches this reader: an interviewer `TurnItem`, from `OpeningResponse.question`
        # or as the last interviewer row of `SessionDetail.turns`. #142b deleted the two wrappers it
        # used to probe (`{question: …}`, `{next: …}`) and the `difficulty`/`content`-on-a-synthesis
        # reads: no endpoint hands a session mapper either wrapper, and the session path built its
        # object from `questionMeta` plus a `text` key of its own making -- which is also why it
        # never matched a real turn.
        "record_of": {"raw": "TurnItem",
                      "meta": ["QuestionMetaFollowup", "QuestionMetaOpening"]},
        "drilled": {"meta": ("raw", "questionMeta")},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeApplication": {
        "record_of": {"raw": "ApplicationItem", "nested": "CompanyItem"},
        "drilled": {"nested": ("raw", "company")},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeJob": {
        # `raw` is deliberately bound to all three job payloads: the saved-jobs list hands over a
        # SavedJobItem and the reader's first statement unwraps it (`raw = rec(pick(raw, "job", …))`),
        # so one local really does see three authors. `company` is the nested CompanyItem that only
        # JobDetail carries -- the list rows project the company through flat `companyId`/`companyName`
        # columns, which is why the reader reads both spellings.
        "record_of": {"raw": ["JobListItem", "JobDetail", "SavedJobItem"],
                      "company": "CompanyItem"},
        "drilled": {"company": ("raw", "company")},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeSuggestions": {
        # `POST /jds/suggestions` is relayed untouched by JobService, so the wrapper has exactly one
        # author (the handler's `return {…}`) and each card exactly one (the rule engine's append).
        # #144 deleted the eleven names neither of them writes -- `items`/`improvements`, `name`,
        # `kind`, `reason`/`why`, `title`, `text`/`body`, `id`, `priority` -- and with them the
        # "already-shaped Suggestion passes through" branch, which no endpoint can produce.
        "record_of": {"raw": "SuggestionEnvelope", "item": "SuggestionItem"},
        "drilled": {},
        "elements": {"item": "raw"},
        "blind": {},
        "dynamic": {},
    },
    "normalizeJdParsed": {
        # Both callers hand over the `JdItem` a JD endpoint answers with, and the analysis sits one
        # level down in `parsed`. #143 deleted four wrapper names (`jd`, `analysis`, `data`), the flat
        # `?? raw` fallback, three snake_case/camel twins per list and the `skillGap` field: no record
        # and no caller ever produced any of them, and they stayed invisible to the liveness rule
        # because `parsed` and `name` kept each site alive -- `_dead_read_sites` reports a site only
        # when *every* candidate is missing, so an alias beside a live name is free tolerance.
        # `skillGap` was the same claim one level up: gaps are a comparison against a resume, so they
        # come from the match or from `/jds/suggestions`, never from an analysis.
        # The five lists are the reader, and their names are arguments to its own `arr` helper rather
        # than literals at an accessor call, which is why `_jd_arr_names` reads them from the source
        # and the floor ties each one to the prompt's own key set.
        "record_of": {"raw": "JdItem", "body": "JdAnalysisMap",
                      "x": ["JdRequiredItem", "JdPreferredItem", "JdBackfilledItem"]},
        "drilled": {"body": ("raw", "parsed")},
        "elements": {"x": "body"},
        "blind": {},
        "dynamic": {
            "body": "each output names its list by passing it to the reader's own `arr(…)` helper, so "
                    "no accessor literal reaches `body` where `_sites` could see it; `_jd_arr_names()` "
                    "reads those arguments out of the reader and every one has to be a key the prompt "
                    "draws, which is the check this entry replaces rather than waives",
        },
    },
    "normalizeMessages": {
        "record_of": {"m": "MessageItem"},
        "drilled": {},
        "elements": {"m": "raw"},
        "blind": {"raw": "the list response envelope: `list(raw, \"messages\", …)` reads a page "
                          "wrapper built by the controller, not a record's fields"},
        "dynamic": {},
    },
    "normalizeMatch": {
        # `raw` is the envelope `pick(raw, "match", "latestMatch", …)` drills; the payload is the
        # union, because the score has two authors: POST /jobs/{id}/match answers with
        # `MatchResult.model_dump()` relayed through `MatchResponse`, while GET /jobs/{id} replays
        # the stored row as `MatchSummary`. Two of the five callers pre-unwrap
        # (`pick(raw, "match") ?? raw`), and one hands a copilot artifact blob -- that path reads
        # the same keys, and no site here is live only thanks to it.
        "record_of": {"raw": ["MatchResponse", "JobDetail"],
                      "m": ["MatchResult", "MatchSummary"]},
        "drilled": {"m": ("raw", "match")},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeSearch": {
        # One endpoint feeds this mapper (`GET /search` via `useGlobalSearch` and the palette), and
        # its answer is `SearchResponse`: seven flat components, six of them `List<*Hit>`. There is
        # no other shape. The reader also used to accept `{groups:[…]}` and a flat `{items:[…]}`;
        # nothing on either service emits either name for this route, so #128 deleted both paths along
        # with the two tests that fed them invented payloads -- a fallback a producer cannot reach is
        # a shape the mapper would silently reinterpret rather than a tolerance anyone needs.
        # `h` is a hit of whichever group is being rendered, which is why it is bound to the union of
        # the six records rather than to one of them: a name only `CompanyHit` carries is a real read
        # for companies and a blank for jobs, and the palette shows a blank subtitle by design.
        # `_search_hits` is what keeps that union honest rather than hand-picked.
        "record_of": {"raw": "SearchResponse",
                      "h": ["JobHit", "CompanyHit", "ResumeHit", "NoteHit",
                            "ConversationHit", "ApplicationHit"]},
        "drilled": {},
        "elements": {"h": "arr"},
        "blind": {},
        "dynamic": {
            "raw": "`const arr = list(raw, g.key)` asks for whichever list the group being rendered "
                   "names, so no literal name appears at the site; `_search_hits` ties those keys to "
                   "SearchResponse's components in both directions",
            "arr": "the per-group list itself, keyed by the same SEARCH_GROUPS variable -- it exists "
                   "to be `h`'s parent rather than to be read by name",
        },
    },
    "normalizeSkillGaps": {
        # The gap card's own reader, and the one whose ITEM shape is the contract: `g` is an item of
        # the `skillGaps` list that `arr` reads out of `raw`, and the only author of those items is
        # ai-service's SkillGap, persisted verbatim into `job_matches.skill_gaps` and projected back
        # by MatchSummary. `raw` cannot be bound: its two callers hand over two different shapes --
        # the list normalizeMatch already drilled, and a literal `{gaps: …}` the dashboard reader
        # builds from missingSkills -- so the shared name is checked where the risk actually is: on
        # the item.
        "record_of": {"g": "SkillGap"},
        "drilled": {"arr": ("raw", "skillGaps")},
        "elements": {"g": "raw"},
        "blind": {"raw": "the caller's payload, whatever shape it brings: `list(raw, \"skillGaps\", "
                         "…)` returns `raw` untouched when the caller already drilled the list, so "
                         "no single record owns the name"},
        "dynamic": {},
    },
}

# Sites that answer from their fallback on every response, declared rather than denied. The key is
# the reader plus that one call's candidate list *verbatim*, in source order -- so renaming or
# reordering the names in the reader has to come here and be thought about again.
DEAD_SITES = {
    ("normalizeApplication", ("matchScore", "match_score")):
        "ApplicationItem has matchId but no score column, and no page renders one today; the "
        "frontend's own test pins `matchScore` to null so the reader cannot invent a zero",
    ("normalizeMatch", ("jobId", "job_id")):
        "neither author carries it: job_matches has the column, but MatchSummary projects the "
        "scores and MatchResult is only what the AI service computed, so JobMatch.jobId stays "
        "undefined -- harmless, because every caller already knows the job from its own route",
    ("normalizeMatch", ("resumeVersionId", "resume_version_id")):
        "same column, same omission: jobs/[id]/page.tsx:103 sets it to null on purpose (the "
        "backend resolves the current version when the request omits it), so nothing reads it back",
}

# Drills whose key is not a component of the parent record, so the local can only ever be `{}`.
# Declared with the shape that would fill it in: `normalizeJob` guarantees `company` on a job and
# `ApplicationItem` does not, and a reader that copies that shape gets a logo no application
# response can supply.
HOLLOW_DRILLS = {
    ("normalizeApplication", "nested", "company"):
        "ApplicationItem names the company in flat columns (companyId + companyName) and never "
        "sends a nested object; the reader's own doc comment says so, and it projects the flat "
        "name into `company` because the row renders `app.company?.name`",
}

_ACCESSORS = (r"\b(?:str|strOr|num|bool|list|pick|rec|int|pct)"
              # A typed accessor reads like any other call once the annotation is skipped:
              # `pick<Record<string, unknown>>(raw, "company")` is a read of `company`, and
              # skipping only the generic -- not the call -- is what keeps that site visible.
              r"(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?\(\s*")
_ID_OF = r"\bidOf\(\s*"


@lru_cache(maxsize=None)
def _body(function_name: str) -> str:
    source = NORMALIZE.read_text(encoding="utf-8")
    opener = f"export function {function_name}("
    if opener not in source:
        raise AssertionError(
            f"{opener!r} is gone from normalize.ts: the table names a reader that moved, "
            "so this rule compares nothing")
    start = source.index(opener)
    return source[start:source.index("\n}\n", start)]


@lru_cache(maxsize=None)
def _id_of_keys() -> set[str]:
    """The names `idOf` reaches for, read out of its own body rather than copied here."""
    source = NORMALIZE.read_text(encoding="utf-8")
    start = source.index("export function idOf(")
    body = source[start:source.index("\n}\n", start)]
    return {key for group in re.findall(r'\(\s*raw\s*,([^)]*)\)', body)
            for key in re.findall(r'"([^"]+)"', group)}


def _sites(function_name: str) -> list[dict]:
    """Each accessor call: the variable it reads off, the names it tries, and where it sits."""
    body = _body(function_name)
    sites = []
    for pattern, keys in ((_ACCESSORS + r"([A-Za-z_$][\w$.]*)\s*,([^)]*)\)", None),
                          (_ID_OF + r"([A-Za-z_$][\w$.]*)\s*,", _id_of_keys())):
        for match in re.finditer(pattern, body):
            receiver = match.group(1)
            candidates = sorted(keys) if keys else re.findall(r'"([^"]+)"', match.group(2))
            if not candidates:
                continue  # an accessor with no name to try is not a read of a key
            line = body.count("\n", 0, match.start()) + 1
            sites.append({"receiver": receiver, "keys": tuple(candidates), "line": line,
                          "text": match.group(0).replace("\n", " ")[:90]})
    return sites


def _search_group_keys() -> list[str]:
    """The list names `SEARCH_GROUPS` walks, read out of that table rather than repeated here."""
    source = NORMALIZE.read_text(encoding="utf-8")
    start = source.index("export const SEARCH_GROUPS")
    return re.findall(r'key:\s*"([^"]+)"', source[start:source.index("\n];", start)])


def _search_hits() -> dict[str, str]:
    """Which record answers for each group, off `SearchResponse`'s own declaration."""
    source = (JAVA_ROOT / "com" / "careeros" / "search" / "dto" / "SearchDtos.java").read_text(
        encoding="utf-8")
    head = source[source.index("record SearchResponse("):]
    body = head[:head.index(") {")]
    return {key: record for record, key in re.findall(r"List<(\w+)>\s+(\w+)", body)}


def _appended_keys(func_name: str, list_name: str) -> set[str]:
    """The keys of the dict literal a function appends to one of its own lists.

    A list item has no record and no model to name it -- `compute_resume_score` loops over
    `detail.append({...})` -- but its shape is stated exactly once in the source, and that is as
    checkable as either. Repetition is allowed only while every literal draws the same key set:
    `suggest_resume_improvements` appends three cards, and three identical contracts are still one.
    A computed key, or two literals whose key sets differ, means the item contract is not one thing
    any more, which is a question for whoever reads it rather than for this gate to guess.
    """
    fn = _sole(func_name)
    if fn is None:
        raise AssertionError(f"{func_name!r} is not exactly one function under app/: the table "
                             "names a producer that moved, so the rule it feeds compares nothing")
    found = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append" and isinstance(node.func.value, ast.Name)
                and node.func.value.id == list_name and node.args
                and isinstance(node.args[0], ast.Dict)):
            item = node.args[0]
            if any(not isinstance(k, ast.Constant) or not isinstance(k.value, str)
                   for k in item.keys):
                raise AssertionError(f"{func_name}.{list_name} appends a dict with a computed key")
            found.append({k.value for k in item.keys})
    if not found:
        raise AssertionError(f"{func_name}.{list_name} is never appended to from a dict literal: "
                             "the table names an item producer whose literal has stopped being one")
    if any(shape != found[0] for shape in found[1:]):
        raise AssertionError(
            f"{func_name}.{list_name} appends {len(found)} different key sets "
            f"{sorted(tuple(sorted(s)) for s in found)}: the item has no single contract to check")
    return found[0]


def _py_const_keys(rel: str, name: str) -> set[str]:
    """The strings a module-level parenthesised tuple declares, read out of the source that states
    the contract. A prompt's JSON skeleton is prose; the tuple beside it is the same list made
    checkable, and copying it into this file instead would let the two drift apart silently."""
    path = Path(__file__).resolve().parents[1] / rel
    if not path.exists():
        raise AssertionError(f"{rel} is not where the contract table says: {name} compares nothing")
    source = path.read_text(encoding="utf-8")
    declared = re.search(rf"^{name}\s*=\s*\(([^)]*)\)", source, re.M | re.S)
    if declared is None:
        raise AssertionError(f"{rel}::{name} is not one parenthesised tuple literal -- the rule that "
                             "reads it would be guessing at the contract")
    keys = set(re.findall(r'"([^"]+)"', declared.group(1)))
    if not keys:
        raise AssertionError(f"{rel}::{name} declares no string keys at all")
    return keys


def _returned_item_keys(func_name: str) -> set[str]:
    """The keys of the one dict literal a function builds its rows from.

    A trajectory row has no record and no model: `_trajectory_detail` returns a comprehension over a
    literal. That literal states the row shape exactly once, which is as checkable as a class body
    -- and two literals, or a computed key, means there is no single row contract to check, which is
    a question for whoever reads it rather than for this gate to guess at.
    """
    fn = _sole(func_name)
    if fn is None:
        raise AssertionError(f"{func_name!r} is not exactly one function under app/: the table names "
                             "a producer that moved, so the rule it feeds compares nothing")
    items = [node for node in ast.walk(fn)
             if isinstance(node, ast.Dict) and node.keys]
    if len(items) != 1:
        raise AssertionError(f"{func_name} builds {len(items)} non-empty dict literals (want "
                             "exactly 1): the row it returns has no single shape to check reads "
                             "against")
    if any(not isinstance(k, ast.Constant) or not isinstance(k.value, str)
           for k in items[0].keys):
        raise AssertionError(f"{func_name}'s row literal carries a computed key")
    return {k.value for k in items[0].keys}


def _java_put_keys(rel: str, method: str) -> set[str]:
    """The keys one Java method puts into its free `Map<String, Object>`.

    A jsonb column projected through a `Map` has no record and no model: `InterviewService.answer`
    states its question meta with `meta.put("topic", …)` calls, and that method body is the only
    place those names exist. Read from the source, so a rename there moves the contract here.
    """
    path = JAVA_ROOT / "com" / "careeros" / rel
    if not path.exists():
        raise AssertionError(f"{rel} is not where the contract table says: {method} compares nothing")
    source = path.read_text(encoding="utf-8")
    opener = re.search(rf"\n[^\n]*\b{re.escape(method)}\(", source)
    if opener is None:
        raise AssertionError(f"{rel} declares no method named {method!r}: the table names a "
                             "producer that moved, so the rule it feeds compares nothing")
    body = source[opener.start():]
    end = body.index("\n    }\n")
    keys = set(re.findall(r'\.\s*put\(\s*"([^"]+)"', body[:end]))
    if not keys:
        raise AssertionError(f"{rel}::{method} puts no string keys into its map: the table binds a "
                             "producer whose literal has stopped being one")
    return keys


def _prompt_skeleton(rel: str, const: str) -> dict:
    """The JSON skeleton one prompt draws, parsed out of the string that states it.

    A passed-through AI answer has no record and no model behind it: `job_jds.parsed` carries these
    keys because the analyze prompt asks for them, so the prompt is the producer and reading it is
    the only way the contract has a source. The skeleton is written as valid JSON, which means the
    key list can be parsed rather than transcribed -- and a transcription beside the prompt is the
    drift this gate was built to catch.
    """
    path = Path(__file__).resolve().parents[1] / rel
    if not path.exists():
        raise AssertionError(f"{rel} is not where the contract table says: {const} declares nothing")
    source = path.read_text(encoding="utf-8")
    literal = re.search(rf'^{const}\s*=\s*"""(.*?)"""', source, re.M | re.S)
    if literal is None:
        raise AssertionError(f"{rel}::{const} is not one triple-quoted string -- the rule that reads "
                             "its skeleton would be guessing at the prompt")
    text = literal.group(1)
    if "{" not in text:
        raise AssertionError(f"{rel}::{const} draws no JSON skeleton: the answer's keys would be "
                             "prose, and nothing here could name them honestly")
    try:
        skeleton, _ = json.JSONDecoder().raw_decode(text[text.index("{"):])
    except json.JSONDecodeError as exc:
        raise AssertionError(f"{rel}::{const}'s skeleton stopped being valid JSON ({exc}), so the "
                             "answer keys can no longer be read from the prompt") from exc
    if not isinstance(skeleton, dict) or not skeleton:
        raise AssertionError(f"{rel}::{const}'s skeleton is not a non-empty JSON object")
    return skeleton


def _prompt_item_keys(rel: str, const: str, member: tuple[str, ...]) -> set[str]:
    """The keys of one drawn list's item, or the answer's own keys when no list is named.

    Both readings come from the same parse, so an item shape is checked against the prompt that asks
    for it rather than against a description of it. A prompt that drops the list, or draws it as
    strings, fails here instead of quietly leaving the reader's item reads unbound.
    """
    skeleton = _prompt_skeleton(rel, const)
    if not member:
        return set(skeleton)
    name = member[0]
    if name not in skeleton:
        raise AssertionError(f"{rel}::{const} draws no {name!r} list: the table names an item shape "
                             "the prompt no longer asks for")
    rows = skeleton[name]
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise AssertionError(f"{rel}::{const}'s {name!r} is not a list of objects, so its items have "
                             "no key set to check a reader's item reads against")
    return set(rows[0])


def _trajectory_keys() -> set[str]:
    """The four names the trajectory fold reaches for, read out of the constant it spreads -- the
    call site itself says `...TRAJECTORY_KEYS`, so no literal name exists where the read happens."""
    source = NORMALIZE.read_text(encoding="utf-8")
    start = source.index("const TRAJECTORY_KEYS")
    return set(re.findall(r'"([^"]+)"', source[start:source.index("];", start)]))


def _jd_arr_names() -> dict[str, tuple[str, ...]]:
    """Which names each output of `normalizeJdParsed` asks `body` for, read out of its own calls.

    The reader reaches its lists through a helper it declares locally, so the name is a parameter and
    `_sites` sees no literal at the read. Those arguments are this mapper's entire read contract,
    which makes them worth parsing off the source instead of restating in this file.
    """
    found = {field: tuple(re.findall(r'"([^"]+)"', args))
             for field, args in re.findall(r"\b(\w+):\s*arr\(([^)]*)\)", _body("normalizeJdParsed"))}
    if not found:
        raise AssertionError("normalizeJdParsed no longer builds its outputs with `arr(…)`: the rule "
                             "that checks which names it probes has nothing left to read")
    empty = sorted(field for field, names in found.items() if not names)
    if empty:
        raise AssertionError(f"{empty}: `arr()` is called with no name to try, so that output can "
                             "only ever be an empty list and no floor here could notice")
    return found


def _emitted(alias: str) -> set[str]:
    """The keys one producer puts on the wire, read from its own source either way."""
    if alias not in PRODUCERS:
        raise AssertionError(f"{alias!r} is bound to a receiver and PRODUCERS has no source for it: "
                             "the rule would compare its reads against nothing")
    spec = PRODUCERS[alias]
    if spec[0] == "java":
        return _record_components_at(spec[1], alias)
    if spec[0] == "pyfunc":
        fn = _sole(spec[1])
        shape = _shape_of(fn) if fn is not None else None
        if shape is None:
            raise AssertionError(f"{spec[1]} answers with a shape no walker can name: the table "
                                 "binds a producer whose literal has stopped being one")
        return set(shape)
    if spec[0] == "pyappend":
        return _appended_keys(*spec[1])
    if spec[0] == "pyconst":
        return _py_const_keys(*spec[1])
    if spec[0] == "pyitem":
        return _returned_item_keys(spec[1])
    if spec[0] == "japut":
        return _java_put_keys(*spec[1])
    if spec[0] == "pyskel":
        return _prompt_item_keys(*spec[1])
    return pydantic_fields(alias)


def _emitted_for(receiver: str | list[str]) -> set[str]:
    """What a map can hold: one producer's keys, or the union when the response has two authors.

    A union is the weaker binding -- a site survives if *either* producer emits the name -- so it
    is only taken where a real second endpoint exists, and `_emitted` keeps the per-producer count
    the positive control pins.
    """
    names = [receiver] if isinstance(receiver, str) else receiver
    if not names:
        raise AssertionError("a receiver bound to zero producers compares nothing")
    return set().union(*(_emitted(name) for name in names))


@lru_cache(maxsize=None)
def _spread_receivers(reader: str) -> set[str]:
    """Receivers reached through a spread name table -- `list(source, ...TRAJECTORY_KEYS)`.

    No literal key sits at such a call site, so `_sites` cannot see the read and the `dynamic` entry
    that excuses it is the only declaration covering it. That made deleting the entry free: the
    receiver never appears in `used`, so neither the missing-binding nor the vanished-name rule had
    anything to complain about.
    """
    return {match.group(1) for match in re.finditer(
        _ACCESSORS + r"([A-Za-z_$][\w$.]*)\s*,[^)]*\.\.\.", _body(reader))}


def _undeclared_receivers(reader: str) -> list[str]:
    """Receivers the reader reads from that no record answers for, and vice versa."""
    spec = READERS[reader]
    problems = []
    used = {site["receiver"] for site in _sites(reader)}
    known = set(spec["record_of"]) | set(spec["blind"]) | set(spec["dynamic"])
    for receiver in sorted(used - known):
        lines = [s["line"] for s in _sites(reader) if s["receiver"] == receiver]
        problems.append(f"{reader}: no record is bound for the receiver {receiver!r} read at "
                        f"L{lines}, while {sorted(known)} are the ones this gate knows")
    for receiver in sorted(known - used):
        if receiver in spec["dynamic"]:
            # Suppressing the complaint is allowed, vanishing with it is not: a dynamic receiver the
            # reader no longer names would leave the table excusing a local that moved.
            if not re.search(rf"\b{re.escape(receiver)}\b", _body(reader)):
                problems.append(f"{reader}: {receiver!r} is declared dynamic and appears nowhere in "
                                "the reader -- the entry excuses a name that moved")
            continue  # read under a name a variable supplies: no literal site can exist
        if not re.search(rf"\b{re.escape(receiver)}\b", _body(reader)):
            problems.append(f"{reader}: {receiver!r} is bound to a record and appears nowhere in "
                            "the reader -- the table links a name that moved")
        else:
            problems.append(f"{reader}: {receiver!r} is bound to a record no site reads from any "
                            "more -- a renamed local silently unchecks that record")
    for receiver in sorted(_spread_receivers(reader) - known):
        problems.append(f"{reader}: {receiver!r} is read through a spread name table, so a "
                        "declaration is the only thing that says what it reaches -- and it has none; "
                        "the liveness rule cannot see this call at all")
    for receiver in sorted(set(spec["record_of"]) & set(spec["blind"])):
        problems.append(f"{reader}: {receiver!r} is both bound to a record and declared blind")
    for receiver in sorted(set(spec["blind"]) & set(spec["dynamic"])):
        problems.append(f"{reader}: {receiver!r} is declared blind and dynamic at once -- the table "
                        "should say which of the two explains it")
    for receiver in sorted(set(spec["record_of"]) - set(spec["drilled"])):
        # `#130` adds a reader whose entire contract is one link: it reads two names, and the second
        # is only reachable through the map the first drills. A local the body builds with
        # `const x = pick(parent, …)` but the table never declares is a record bound directly to
        # that local -- so the drill itself, the one step where a wrong key yields `{}` and every
        # read below it silently answers null, goes unchecked while the gate stays green.
        made_by = re.search(rf"const\s+{re.escape(receiver)}\s*=\s*[^;\n]*\(\s*"
                            rf"([A-Za-z_$][\w$.]*)\s*,", _body(reader))
        if made_by is not None:
            problems.append(f"{reader}: {receiver!r} is bound to a record but the reader builds it "
                            f"by drilling {made_by.group(1)!r} -- `drilled` does not say so, so the "
                            "key it drills is unchecked and dropping the link later costs nothing")
    return problems


def _broken_links(reader: str) -> list[str]:
    """The hand-authored links, checked against the code they claim to describe."""
    spec, body = READERS[reader], _body(reader)
    problems = []
    for local, (parent, key) in spec["drilled"].items():
        bound = re.search(rf"const\s+{re.escape(local)}\s*=\s*[^;\n]*\(\s*{re.escape(parent)}\s*,"
                          rf"\s*(?:[\w$]+\s*,\s*)?" r'"([^"]+)"', body)
        if bound is None:
            problems.append(f"{reader}: {local!r} is declared as drilled out of {parent!r} but "
                            "nothing binds it that way")
            continue
        if bound.group(1) != key:
            problems.append(f"{reader}: {local!r} is drilled from {parent!r} under "
                            f"{bound.group(1)!r}, which the table calls {key!r}")
    for local, parent in spec["elements"].items():
        if not re.search(rf"\.map\(\s*\(?\s*{re.escape(local)}\b", body):
            problems.append(f"{reader}: {local!r} is declared as an element of {parent!r}'s list "
                            "but is not a `.map` callback parameter")
        if parent not in (set(spec["record_of"]) | set(spec["blind"]) | set(spec["dynamic"])):
            problems.append(f"{reader}: {local!r} comes from {parent!r}, which the table neither "
                            "binds, declares blind, nor declares dynamic")
    return problems


def _producer_bookkeeping() -> list[str]:
    """The producer table against the reader table, both ways. A name bound to nothing, or a
    producer nothing binds, both leave a rule comparing a set nobody reads."""
    problems = []
    named = {alias for spec in READERS.values() for value in spec["record_of"].values()
             for alias in ([value] if isinstance(value, str) else value)}
    for alias in sorted(named - set(PRODUCERS)):
        problems.append(f"{alias!r} is bound to a receiver but PRODUCERS has no source for it, so "
                        "the liveness rule has nothing to compare against")
    for alias in sorted(set(PRODUCERS) - named):
        problems.append(f"{alias!r} is registered as a producer and bound to no receiver -- the "
                        "reader that used it has moved, and its reads are now unchecked")
    for alias in sorted(named & set(PRODUCERS)):
        if not _emitted(alias):
            problems.append(f"{alias} emits no keys at all: the source it names no longer has a "
                            "record or model of that shape")
    return problems


_SPEC_KEYS = {"record_of", "drilled", "elements", "blind", "dynamic"}


def _spec_shape() -> list[str]:
    """A reader that stops declaring one link stops being checked by the rule that reads it, and a
    `dynamic` entry with a one-word reason is free tolerance rather than an explanation."""
    problems = []
    for reader, spec in READERS.items():
        if set(spec) != _SPEC_KEYS:
            problems.append(f"{reader}: declares {sorted(spec)}, not the five links "
                            f"{sorted(_SPEC_KEYS)} -- a rule now has nothing to read")
        for receiver, why in spec["dynamic"].items():
            if len(why) <= 40:
                problems.append(f"{reader}: {receiver!r} is excused by {why!r}, which is a label "
                                "and not a reason the next reader can act on")
    return problems


def _structural_problems() -> list[str]:
    """Everything wrong with the table itself, which would make the liveness rule check less than
    it claims rather than make it red."""
    problems = _spec_shape()
    if problems:
        # A spec missing one of the five links makes the rules below unreadable rather than wrong,
        # so say which key vanished before anything tries to index it.
        return problems
    return [p for reader in READERS
            for p in (*_undeclared_receivers(reader), *_broken_links(reader))] + \
        _producer_bookkeeping()


def _hollow_drills() -> set[tuple]:
    """(reader, local, key) where the local is drilled out of a record that lacks that key: the
    map can only ever be `{}`, so every read that goes through it answers from its fallback.
    Declared once per drill rather than per site, because the site names are fine -- the map is not."""
    out = set()
    for reader, spec in READERS.items():
        for local, (parent, key) in spec["drilled"].items():
            if parent in spec["record_of"] and key not in _emitted_for(spec["record_of"][parent]):
                out.add((reader, local, key))
    return out


def _hollow_drill_reads() -> set[tuple]:
    """The one-name read that *performs* a hollow drill, on its parent receiver.
    `pick(raw, "company")` on a record with no `company` component is the drill's own defect, which
    HOLLOW_DRILLS already carries with the reason; counting it a second time as a dead read site
    would let the two lists disagree about the same line without telling anyone more."""
    return {(reader, READERS[reader]["drilled"][local][0], (key,))
            for (reader, local, key) in _hollow_drills()}


def _dead_read_sites() -> list[dict]:
    """Sites whose every candidate name is absent from the producers behind their receiver."""
    out = []
    for reader, spec in READERS.items():
        hollow = {local for (r, local, _) in _hollow_drills() if r == reader}
        drill_reads = _hollow_drill_reads()
        for site in _sites(reader):
            receiver = site["receiver"]
            if receiver not in spec["record_of"]:
                continue  # unbound or blind: the structural rule has already named it
            if receiver in hollow:
                continue
            if (reader, receiver, site["keys"]) in drill_reads:
                continue
            if not set(site["keys"]) & _emitted_for(spec["record_of"][receiver]):
                out.append(dict(site, reader=reader))
    return out


# -------------------------------------------------------------- the reconciliations

def _keyed(sites: list[dict]) -> set[tuple]:
    return {(site["reader"], site["keys"]) for site in sites}


def test_every_read_site_hits_a_field_the_record_emits():
    """A site with no live name is a field the UI shows empty forever: `num` falls back to null,
    `str` to nothing, and no layer between the record and the component can tell the difference."""
    found = _keyed(_dead_read_sites()) - set(DEAD_SITES)
    assert found == set(), ("no record answers these reads: "
                            f"{[f'{reader} {list(keys)}' for reader, keys in sorted(found)]}")


def test_the_readers_this_gate_binds_are_the_ones_that_exist():
    """The table's own bookkeeping: an unbound receiver, a local that moved, or a declared
    receiver nothing reads from any more each mean the gate checks less than it claims."""
    assert _structural_problems() == []


def test_the_dead_reads_stay_declared():
    """Shrink-only, with a reason each: a new one is a field the browser cannot get, and an old
    one that came alive should leave this list rather than sit here as free tolerance."""
    found = _keyed(_dead_read_sites())
    assert found == set(DEAD_SITES), f"off the list: {sorted(found ^ set(DEAD_SITES))}"
    assert _hollow_drills() == set(HOLLOW_DRILLS), \
        f"off the list: {sorted(_hollow_drills() ^ set(HOLLOW_DRILLS))}"
    for key, why in (*DEAD_SITES.items(), *HOLLOW_DRILLS.items()):
        assert len(why) > 40, f"{key} needs a reason a reader can act on, not a label"


def test_the_reads_are_actually_found():
    """Positive control: every rule above is satisfied by an empty reading, so the census itself is
    pinned -- real sites, at the receivers this gate claims to bind, against real components."""
    applications = _sites("normalizeApplication")
    assert len(applications) == 16
    assert {s["receiver"] for s in applications} == {"raw", "nested"}
    assert sum(1 for s in applications if s["receiver"] == "nested") == 3
    messages = _sites("normalizeMessages")
    assert len(messages) == 8
    assert {s["receiver"] for s in messages} == {"m", "raw"}
    matches = _sites("normalizeMatch")
    assert len(matches) == 18
    assert {s["receiver"] for s in matches} == {"raw", "m"}
    assert sum(1 for s in matches if s["receiver"] == "m") == 17  # every payload read, incl. idOf
    gaps = _sites("normalizeSkillGaps")
    assert len(gaps) == 4
    assert {s["receiver"] for s in gaps} == {"raw", "g"}
    assert sum(1 for s in gaps if s["receiver"] == "g") == 3     # the three item reads
    jobs = _sites("normalizeJob")
    assert len(jobs) == 33
    assert {s["receiver"] for s in jobs} == {"raw", "company"}
    assert sum(1 for s in jobs if s["receiver"] == "company") == 5
    # 33, not the 37 this reader had before #127 bound it: `remote`, `salaryText`, a standalone
    # `tags` field and `whyMatch` had no author on any of the three job payloads, and the job card
    # had a fifth name on top of them -- `Job.match`, which no hook ever set. Each one read as a
    # nullable field the UI could only ever show as empty. `tags` still appears once, as a candidate
    # inside the `skills` site, where a live sibling carries the call.
    hits = _sites("normalizeSearch")
    assert len(hits) == 3
    assert {s["receiver"] for s in hits} == {"h"}
    # Three sites, all on a hit -- and the reader had 17 before #128 measured that its two fallback
    # paths answer to nothing: `/search` is the only caller's endpoint, `SearchResponse` has no
    # `groups` component and no `items`/`results`, so `{groups:[…]}` and flat `{items:[…]}` payloads
    # were shapes the mapper would silently reinterpret rather than shapes anyone served. The tests
    # that fed them invented a "People" entity with a `/people/:id` route the product does not have.
    # `list(raw, g.key)` is the one read of `raw` left, and it has no literal name to check, so the
    # two source-derived lists below are what make it live instead of a candidate table here.
    groups, records = _search_group_keys(), _search_hits()
    assert groups == ["jobs", "companies", "resumes", "notes", "conversations", "applications"]
    assert sorted(groups) == sorted(records)
    assert set(records.values()) == set(READERS["normalizeSearch"]["record_of"]["h"])
    assert set(groups) <= _emitted("SearchResponse")
    # Per group, which names the subtitle site actually answers from. Measured, because a group whose
    # record carries none of them renders a row with no second line in the palette.
    subtitle = next(s for s in hits if "industry" in s["keys"])
    assert {key: sorted(set(subtitle["keys"]) & _emitted(record))
            for key, record in records.items()} == {
        "jobs": ["companyName", "location", "status"],
        "companies": ["industry"],
        "resumes": ["status"],
        "notes": ["snippet"],
        "conversations": ["snippet"],
        "applications": ["companyName", "status"],
    }
    dash = _sites("normalizeDashboard")
    assert len(dash) == 16
    assert {s["receiver"] for s in dash} == {"d", "kanban", "currentResume", "skillGapDigest"}
    assert sum(1 for s in dash if s["receiver"] == "d") == 8
    assert sum(1 for s in dash if s["receiver"] == "kanban") == 3
    assert sum(1 for s in dash if s["receiver"] == "currentResume") == 4
    # 16, down from the 41 this reader had when #129 measured it: 26 sites had no author on
    # DashboardResponse / Kanban / ResumeSummary / SkillGapDigest -- the envelope pick, the whole
    # `metrics`/`stats`/`summary` layer (10 sites), five returned fields nobody produced, the
    # `normalizeResumeScore(d)` fallback and the flat numeric aliases.
    read_off_d = {k for s in dash if s["receiver"] == "d" for k in s["keys"]}
    assert _emitted("DashboardResponse") - read_off_d == {"recentActivity"}
    # The one component the mapper still never reads. `recentActivity` rows are an event log the
    # dashboard page renders from its own query, not off this payload, so the record carries it and
    # the browser ignores it; that is a producer-side surplus, not a dead read, and it stays listed
    # here so a future reader has to notice it rather than inherit a silently growing set.
    assert {k for s in dash if s["receiver"] == "kanban" for k in s["keys"]} & _emitted("Kanban") == \
        _emitted("Kanban")
    assert {key for s in dash if s["receiver"] == "currentResume" for key in s["keys"]} & \
        _emitted("ResumeSummary") == _emitted("ResumeSummary") - {"score"}
    pipe = _sites("normalizePipeline")
    assert len(pipe) == 2
    assert {s["receiver"] for s in pipe} == {"raw", "kanban"}
    # Down from 5. The three that went were the array-of-stages branch: the
    # `pick(raw, "pipeline", "stages", "applicationPipeline", "application_pipeline")` probe and the
    # two reads off its `row` element. `DashboardResponse` has no `pipeline` component, so that shape
    # existed only in the fixture that fed it.
    assert {k for s in pipe if s["receiver"] == "raw" for k in s["keys"]} & \
        _emitted("DashboardResponse") == {"kanban"}
    # One read of one component: the *stage* names are `Map` keys the service builds from
    # `ApplicationStatus`, so no literal for them can appear in this reader at all -- which is the
    # difference between this assertion and the dashboard's `== _emitted("Kanban")` coverage line.
    assert {k for s in pipe if s["receiver"] == "kanban" for k in s["keys"]} & \
        _emitted("Kanban") == {"statusCounts"}
    score = _sites("normalizeResumeScore")
    assert len(score) == 10
    assert {s["receiver"] for s in score} == {"raw", "s", "c"}
    assert sum(1 for s in score if s["receiver"] == "s") == 7
    # 10, down from the 13 this reader had when #132 measured it, and all ten now have an author:
    # what went was an explicit `gaps`/`issues`/`weaknesses` list (the unmet rubric criteria *are*
    # the gaps, and nothing writes the flat list), `suggestions`, and `computedAt`/`createdAt`.
    read_off_s = {k for s in score if s["receiver"] == "s" for k in s["keys"]}
    assert _emitted("ResumeScoreMap") == read_off_s
    # Key for key: the map this reader walks is the map `compute_resume_score` returns, so a
    # criterion the rubric stops emitting shows up here as an unread name rather than as a blank
    # card, and a new one is a name the reader has to be pointed at on purpose.
    assert _emitted("RubricCheck") - {k for s in score if s["receiver"] == "c"
                                     for k in s["keys"]} == {"points"}
    # The one item field no read of the reader consumes: the panel reports which criteria went
    # unmet, never what each was worth on its own.
    assert all("score" in _emitted(name) for name in ("ResumeDetail", "ResumeSummary",
                                                      "ResumeVersionItem"))
    # All three carriers project the column as of #134. The last one did not use to: the versions
    # panel had been reading `v.score?.overall` off a DTO that never sent the field, so the suffix
    # never appeared -- which is exactly the kind of silence a union can hide, so the fact each
    # author carries `score` is asserted per author rather than inferred from the site being live.
    report = _sites("normalizeInterviewReport")
    assert len(report) == 10
    assert {s["receiver"] for s in report} == {"ev", "merged", "raw", "s"}
    read_merged = {k for s in report if s["receiver"] == "merged" for k in s["keys"]}
    assert read_merged == {"overall", "what_you_did_well", "what_was_weak",
                           "recommended_study", "trajectory_note"}
    assert read_merged <= _emitted("FinalizeReport")
    # Every name the report body tries is one `FINALIZE_FIELDS` declares -- which is #137's trim
    # stated as a floor: a new read has to name a declared field, and a field the prompt stops
    # asking for goes red here before a card on the page goes blank.
    assert _emitted("FinalizeReport") - read_merged == {"dims", "missing_concepts",
                                                        "better_answers",
                                                        "follow_up_questions_to_prepare"}
    # The four declared and not read here: `dims` is the dimension reader's, `better_answers` and
    # `follow_up_questions_to_prepare` are rendered from the raw report elsewhere, and
    # `missing_concepts` has no consumer yet. Named so the set cannot grow by accident.
    assert {k for s in report if s["receiver"] == "s" for k in s["keys"]} == _emitted("StudyItem")
    # The study card reads exactly the three names of `STUDY_ITEM_FIELDS`, no more: after #137 there
    # is no undeclared name left in this reader, which is the whole reason it could be bound.
    idims = _sites("normalizeInterviewDims")
    assert len(idims) == 1
    assert {s["receiver"] for s in idims} == {"raw"}
    assert {k for s in idims for k in s["keys"]} == {"dims"}
    # One site, one name, and that name is a component of the DTO as well as a key of the report
    # map. The three other candidates (`dimensions`, `scores`, `evaluation`) and the two extra
    # branches were #141's deletions: six sites, only one of them authored.
    assert "dims" in _emitted("EvaluationItem") and "dims" in _emitted("FinalizeReport")
    traj = _sites("normalizeTrajectory")
    assert len(traj) == 6
    assert {s["receiver"] for s in traj} == {"t", "row"}
    carriers = ["EvaluationItem", "FinalizeReport", "FinalizeComputed"]
    assert _trajectory_keys() & _emitted_for(carriers) == {"trajectory", "trajectory_detail"}
    # The two list names that are real -- one a component of the DTO, one written by `finalize` --
    # and the two that are speculation, named here so a future reader notices the fold still tries
    # them rather than inheriting a quietly shrinking set:
    assert _trajectory_keys() - _emitted_for(carriers) == {"depth_trajectory", "depthTrajectory"}
    assert _emitted("TrajectoryRow") - {k for s in traj for k in s["keys"]} == {"seq", "role"}
    # The row's two bookkeeping columns. `seq` orders the rows server-side; `role` decides which rows
    # the fold keeps, but it is tested outside the accessor helpers (`row.role !== "interviewer"`),
    # so no read site exists for this gate to point at.
    assert _spread_receivers("normalizeTrajectory") == {"source"}
    assert _spread_receivers("normalizeSearch") == set()
    question = _sites("normalizeQuestion")
    assert len(question) == 5
    assert {s["receiver"] for s in question} == {"raw", "meta"}
    assert sum(1 for s in question if s["receiver"] == "meta") == 2
    # 5, down from 7, and this is the first time any of them had an author: the reader used to probe
    # `{question: …}` and `{next: …}` wrappers no endpoint hands a session mapper, and the session
    # path built its object from a `text` key of its own making after searching the turns for role
    # "assistant" -- a role the backend never writes, so `currentQuestion` was null on every load
    # and the runner re-fired an opening POST the service answers with 400.
    assert _emitted("QuestionMetaFollowup") == {"topic", "depth_level", "action", "reasoning"}
    assert _emitted("QuestionMetaOpening") == {"topic", "depth_level", "expected_points", "phase"}
    # Stated per author rather than as the union the site is checked against: the two maps agree on
    # `topic` and `depth_level`, so either one renaming `topic` leaves the other covering the read
    # (#133, #141). The asymmetry is the point -- `action`, the name the runner branches on, has
    # exactly one author.
    assert _emitted("QuestionMetaFollowup") ^ _emitted("QuestionMetaOpening") == \
        {"action", "reasoning", "expected_points", "phase"}
    meta_reads = {k for s in question if s["receiver"] == "meta" for k in s["keys"]}
    assert meta_reads <= _emitted("QuestionMetaFollowup")
    # Both names the meta receiver tries come from the follow-up handler alone, so the opening
    # handler's map is bound here for the fields it *does* carry, not to lend liveness.
    assert "questionMeta" in _emitted("TurnItem")
    jd = _sites("normalizeJdParsed")
    assert len(jd) == 2
    assert {s["receiver"] for s in jd} == {"raw", "x"}
    # Two sites, one name each, after #143. Before it the reader tried four wrappers on `raw` and
    # three item names on `x`; the extra ones were not dead *sites* (`parsed` and `name` answered for
    # each) but they were reads no producer ever wrote, which is the blind spot of a rule that only
    # reports a site when *every* candidate is missing.
    assert {k for s in jd if s["receiver"] == "raw" for k in s["keys"]} == {"parsed"}
    assert {k for s in jd if s["receiver"] == "x" for k in s["keys"]} == {"name"}
    assert "parsed" in _emitted("JdItem")
    arr_lists = _jd_arr_names()
    assert set(arr_lists) == {"requiredSkills", "preferredSkills", "responsibilities",
                              "interviewTopics", "hiddenRequirements"}
    # Each output asks for the one list the prompt draws, under the very spelling the output field
    # carries: no second spelling to keep honest, and a re-added `gaps` guess names itself here.
    assert {f: names for f, names in arr_lists.items() if names != (f,)} == {}
    probed = {name for names in arr_lists.values() for name in names}
    assert probed - _emitted("JdAnalysisMap") == set()
    assert len(_emitted("JdAnalysisMap")) == 13
    # The eight drawn keys no browser read: `title`/`company`/`location`/`experienceYears` reach the
    # page through `JobDetail`'s own columns, and `education`/`softSkills`/`priorityOrder`/
    # `domainKeywords` are stored and never rendered. Pinned as a surplus so a prompt that loses one
    # goes red here -- a dropped key would leave no read missing, because nothing reads it.
    assert _emitted("JdAnalysisMap") - probed == {"title", "company", "location", "experienceYears",
                                                  "education", "softSkills", "priorityOrder",
                                                  "domainKeywords"}
    # The item shape, stated per author rather than as the union `x` is checked against: the prompt
    # draws two skill lists and `_backfill_skills` appends items of its own, and all three agree
    # today -- which is precisely the state in which one author's rename hides behind the others.
    for author in ("JdRequiredItem", "JdPreferredItem", "JdBackfilledItem"):
        assert _emitted(author) == {"name", "priority", "evidence_phrase"}, author

    # normalizeSuggestions reads four names and every one of them is written by somebody. Before
    # this unit the same reader also probed items/improvements, name, kind, reason/why, title,
    # text/body, id and priority -- none of which any producer emits -- so a card whose skill name
    # changed would have rendered an empty bullet instead of failing here.
    sug = _sites("normalizeSuggestions")
    assert len(sug) == 4, f"the suggestions reader holds {len(sug)} sites, want the 4 they can name"
    assert {s["receiver"] for s in sug} == {"raw", "item"}
    assert {k for s in sug if s["receiver"] == "raw" for k in s["keys"]} == {"suggestions"}
    assert {k for s in sug if s["receiver"] == "item" for k in s["keys"]} == {"skill", "type",
                                                                             "advice"}
    assert _emitted("SuggestionItem") == {"skill", "type", "advice"}
    assert _emitted("SuggestionEnvelope") == {"suggestions", "jd"}
    # Two different ways a read stops naming its key in the call: `normalizeTrajectory` spreads a
    # name table, which this rule covers, and `normalizeSearch` reaches `g.key`, a member of a group
    # object, which `_search_hits` covers. Telling them apart is what keeps each rule honest about
    # the half it cannot see.
    runs = _sites("normalizeRun")
    assert len(runs) == 12
    assert {s["receiver"] for s in runs} == {"raw"}
    # 12, down from 16: `traces`, `summary`, `createdAt` and `relatedHref` named nothing either run
    # record has ever carried, and the snake aliases sat beside live names in the same lists.
    read_off_run = {k for s in runs for k in s["keys"]}
    assert (_emitted("RecentRun") | _emitted("RunItem")) - read_off_run == \
        {"cachedTokens", "conversationId", "rootRunId"}
    # The three columns `RunItem` sends that the browser has no place for: the cache-hit count, and
    # the two ids the copilot timeline resolves server-side. A producer surplus, named so it cannot
    # grow quietly -- and `RecentRun`, the smaller of the two, is read in full.
    assert _emitted("RecentRun") - read_off_run == set()
    assert len(_emitted("JobListItem")) == 18
    assert len(_emitted("SavedJobItem")) == 3
    assert len(_emitted("SearchResponse")) == 7
    assert len(_emitted("SkillGap")) == 3
    assert len(_emitted("ApplicationItem")) == 15
    assert len(_emitted("CompanyItem")) == 9
    assert len(_emitted("MessageItem")) == 8
    assert len(_emitted("MatchResponse")) == 3
    assert len(_emitted("JobDetail")) == 23
    assert len(_emitted("MatchSummary")) == 14
    assert len(_emitted("MatchResult")) == 14
    # ...and the union is not a restatement of one side: `id`/`createdAt` come only from the stored
    # row, `interviewTopics`/`model` only from the AI service's answer. `skillGaps` used to sit on
    # the second side too — #126 gave it a column, so both authors now emit it and the site that
    # reads it is live on every path rather than only after a fresh compute.
    assert _emitted("MatchSummary") - _emitted("MatchResult") == {"id", "createdAt"}
    assert _emitted("MatchResult") - _emitted("MatchSummary") == {"interviewTopics", "model"}
    assert _id_of_keys() == {"_id", "eventId", "event_id", "id", "key", "uuid"}
    dead = _dead_read_sites()
    assert len(dead) == 3
    assert {(s["reader"], s["line"]) for s in dead} == {
        ("normalizeApplication", 19), ("normalizeMatch", 12), ("normalizeMatch", 13)}
    assert _structural_problems() == []
