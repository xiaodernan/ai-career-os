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

A producer can also be code rather than a declaration. `normalizeChatActions` reads action rows
`_derive_actions` appends through a local `add(…)` closure -- no record, no model, no `Name.append` --
so `pyadd` walks that function's own AST for the literals, and the census pins them per literal because
`ChatActionItem` is the union of two shapes. And the last thing that reader reaches for is not a wire
field at all: `CHAT_ACTION_ROUTES[kind]` is keyed by a variable, so a fifth test checks the kinds the
producer writes against the routes the browser declares, and every route against a page that exists.

The same kind of read, one table over: `DIMENSION_LABELS[key]`. #150 found the shape's cost -- five of
its entries were reachable only through a `dimensions` map no match endpoint ever sent, and the reader
that probed for that map tried seventeen names of which sixteen had no author -- so a sixth test bounds
the label table by the two dimension vocabularies that key it, each parsed from the source that
declares it (`_overall`'s parameters on one side, ai-service's `DIMENSIONS` on the other). A
variable-keyed lookup of browser-owned data is not outside the contract; it is the part of it a
per-site rule cannot see.

`normalizeEvidence`, bound in #151, is the first reader whose rows have three authors and no single
envelope. A match's evidence is an `EvidenceItem` list, a retrieved-citation list is dicts
`to_evidence` appends, and the copilot's sources are literals appended to `out.sources` -- so two
machinery rules widened for it rather than the reader. `pyappend` now matches a dotted list receiver,
because `out.sources.append({…})` is an attribute chain, not a name (a bare local unparses to its own
identifier, so the older entries keep matching exactly as before); and `pathOf` joined `_ACCESSORS`,
since it takes a payload plus a list of names and splits whatever it finds, which made the reader's
`section` breadcrumb a real read instead of a blind spot. Measured the same pass: none of the other
26 readers gained or lost a site from either widening.

A seventh rule (#152) covers what every rule above is blind to by construction. A site is dead only when
*no* candidate names a real column, so a fourth "tolerant alias" beside a live one costs nothing here --
and it is not free: it is a second shape the mapper silently reinterprets. #152 deleted `citations` from
three such call sites and put the remaining claim where it can be checked, by reading which handler
actually returns the key and whether the app can reach that handler at all. Both ends are parsed from
code (the FastAPI route table, the handler's own `return`, the backend's call sites, the browser's
source), so the ban cannot be satisfied by a table this file wrote for itself -- and it fails as a
statement if the reason stops holding: a reachable route, a renamed key, or a browser read that came
back each says which of the three it is.

`normalizeArtifacts`, bound in #145a, is the first reader whose rows have **more than one shape**, so the
gate learned a consensus kind for it. `_collect_artifacts` appends five artifact literals and they do not
draw the same keys -- the match row adds `job_id` -- which `pyappend` refuses by design rather than
guessing at. `pycons` answers with what every row draws and the census names the difference, because a
union would let a read lean on `job_id` and stay green on the four cards that never carry it. The card's
own vocabulary is bound the same way it binds the action routes and the dimension labels: the
`case "…"` labels of its switch are compared with the `type` values the orchestrator appends, which is
how `skill_gap` -- a whole renderer no path through the producer can reach -- was found and deleted.

#155 wrote the other half of that blindness into a census. `normalizeMatch` has been bound since #122 and
its sites have been counted ever since, so its twenty-two *tolerant* aliases -- each beside a name an
author really fills -- were invisible by construction, and #127's four deletions were only the ones that
had no live sibling at all. Every one of its 18 sites is now pinned to the exact tuple it asks for, and
the envelope drill is asserted **per author**: `raw` is bound to a union of two envelopes, and #155's own
witness measured that renaming `match` on one of them leaves liveness and the declared-dead list green --
the union is what the per-site rule has to work with, so the per-author assert is what replaces it.
"""

import ast
import collections
import json
import re
from functools import lru_cache
from pathlib import Path

from tests.test_response_shape_contract import (
    JAVA_ROOT,
    NORMALIZE,
    ROOT_FRONTEND,
    _java_record_body,
    _record_components_at,
    _shape_of,
    _sole,
    _ts_function_body,
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
    # The list envelope every paged browser read unwraps: the backend's list routes answer this one
    # record rather than a Spring `Page`, which is what #159 bound `normalizePage` to.
    "PageDTO": ("java", "common/PageDTO.java"),
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
    # /jobs/{id}/tailor is a pass-through of the ai-service answer, so the reader's producer is that
    # answer's own literal -- not the `TailorResponse` record named in JobDtos, which no controller,
    # service or test anywhere in backend/src references (measured #145: zero hits). The two nested
    # maps come out of the same return statement, one key down.
    "TailorMap": ("pyfunc", "tailor"),
    "TailorDiffMap": ("pyretsub", ("tailor", "diff")),
    # The rows inside that diff are the LLM's own, drawn to the tailor prompt's `changes` item;
    # `verify_no_fabrication` then adds `verifier_reject` to the rows it refused, which no reader
    # names. #146 binds the private `changeFrom` mapper to this, so a sub-reader's aliases stop
    # being free of inspection just because the function is not exported.
    "TailorChangeItem": ("pyskel", ("app/features/tailor.py", "SYSTEM", ("changes",))),
    # The resume dict `tailored` carries is the parse answer with three edits, so every name the
    # markdown renderer can reach has to be drawn by this prompt. One producer per level, because a
    # union of the levels would let `role` pass for a project as easily as for an experience row.
    # `ParsedResumeMap.profile` is a drawn *object* rather than a list, which `_prompt_item_keys`
    # reads from the same parsed skeleton.
    "ParsedResumeMap": ("pyskel", ("app/features/resume_parse.py", "SYSTEM", ())),
    "ParsedProfileMap": ("pyskel", ("app/features/resume_parse.py", "SYSTEM", ("profile",))),
    "ParsedExperienceItem": ("pyskel", ("app/features/resume_parse.py", "SYSTEM", ("experience",))),
    "ParsedProjectItem": ("pyskel", ("app/features/resume_parse.py", "SYSTEM", ("projects",))),
    "ParsedEducationItem": ("pyskel", ("app/features/resume_parse.py", "SYSTEM", ("education",))),
    # A skill row is the one list whose author is code, not the prompt: `parse_resume` overwrites
    # `raw["skills"]` with `_merge_skills`, so what reaches the wire is that literal -- which is why
    # `proficiency` is a key a reader may name even though the renderer never does.
    "MergedSkillItem": ("pyappend", ("_merge_skills", "merged")),
    # The copilot's reply is the one conversation DTO whose action row has no record: `ChatResponse.
    # actions` is a `List<Object>` the backend fills from ai-service's answer, and each item is a
    # literal `add(…)` in `_derive_actions`. A helper call rather than an `append`, so `pyappend`
    # cannot see it -- and the row has two shapes (a job-located action and a session-located one),
    # which is why `_added_key_sets` returns the per-literal sets that CENSUS pins rather than
    # insisting on one the way `pyappend` does.
    "ChatResponse": ("java", "conversation/dto/ConversationDtos.java"),
    "ChatActionItem": ("pyadd", ("_derive_actions", "add")),
    # A citation row is the one item shape with three authors and no record for any of them, because
    # all three are Python code and the backend relays each list as a free `List<Object>`: a match's
    # own `EvidenceItem`, the retrieved rows `to_evidence` shapes for the tailor and cover-letter
    # answers, and the copilot's `out.sources` row. #151 binds the mapper that reads all three, and
    # the per-author sets its census pins are what keep the union from covering one author's rename
    # with another's live sibling.
    "EvidenceItem": ("pydantic",),
    "RetrievedEvidenceItem": ("pyappend", ("to_evidence", "evidence")),
    "CopilotSourceItem": ("pyappend", ("_collect_artifacts", "out.sources")),
    # ...and the two envelopes that hand those rows over: the tailor answer carries its list under
    # `evidence`, the cover-letter answer under `sources`, and the two key sets are disjoint, which is
    # why the mapper's two-name probe is a binding rather than a guess.
    "CoverLetterMap": ("pyfunc", "generate"),
    # A list with more than one shape. `_collect_artifacts` appends five artifact rows and they do not
    # draw the same keys: the match row carries `job_id` and the other four do not. `pycons` therefore
    # answers with what *every* row draws, and #145a's census names the difference as its own fact --
    # a union would let a read lean on `job_id` and stay green on four rows that never carry it.
    "ArtifactItem": ("pycons", ("_collect_artifacts", "out.artifacts")),
    # The follow-up question the answer endpoint proposes. `InterviewService.answer` relays this map
    # verbatim (`Json.obj(result.get("next"))`, declared as a free `Map`), so the only place its keys
    # are stated is the literal `decide_next` returns -- which is also where the whitelisted `action`
    # values come from, the ones the session page's badge branches on.
    "NextQuestionMap": ("pyfunc", "decide_next"),
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
#   elements   local -> parent receiver, when it is a `.map((local, i) …)` element; or
#              (parent, key) when a `for…of` walks a list the reader drilled out of that parent
#              under that key -- the key is what makes the claim checkable rather than anecdotal
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
        # `next` joined them in #162: the look-ahead row used to be read as `num(rows[j], …)`, and an
        # expression receiver reaches no binding at all, so the census held six sites while the file
        # held seven reads. Naming the row is what made the seventh countable.
        "record_of": {"t": "TrajectoryRow", "row": "TrajectoryRow", "next": "TrajectoryRow"},
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
    "normalizeTailor": {
        # `useTailorRun` posts /jobs/{id}/tailor and `TailorArtifact` hands over the copilot's
        # `tailored_resume` payload -- which is a *subset* of the same answer (`tailor`'s literal
        # minus `evidence`), so binding the reader to the full answer is the stronger side of the
        # pair and needs no union. #145 deleted what that left with no author at all: the
        # `markdown`/`md`/`text`/`content`/`plainText`/`plain_text`/`body` layer inside `tailored`
        # (the dict is the parsed resume, whose keys the parse prompt draws), a `resumeVersionId`
        # the pass-through response never carries, `sections`/`notes`/`comments`/`evidence` read one
        # level too deep, the `statistics`/`summary` twins, and `warnings` beside the real `notes`.
        "record_of": {"raw": "TailorMap"},
        "drilled": {},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeTailorDiff": {
        # Two callers, two shapes: `normalizeTailor` passes the whole answer and the reader drills
        # `diff`, while the versions panel and the save-body helper pass the diff map itself -- that
        # is what the `?? raw` fallback is for, and it is load-bearing, so `raw` is bound to both
        # authors. The deleted flat branch (`changes`/`items`/`edits` partitioned by
        # `status`/`state`/`decision`, plus `applied`/`kept`/`skipped`/`declined`) answered to a
        # response no producer writes, and its `?? raw` was a third name for `diff`.
        "record_of": {"raw": ["TailorMap", "TailorDiffMap"], "diff": "TailorDiffMap"},
        "drilled": {"diff": ("raw", "diff")},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "changeFrom": {
        # The one mapper in normalize.ts that is not exported -- and therefore was invisible to this
        # gate while it carried 19 names of which 4 had an author. It is the change row the tailor
        # panel crosses out, so every alias (`area`/`category`, `original`/`from`/`old`/`previous`,
        # `revised`/`to`/`new`/`proposed`, `why`/`explanation`/`rationale`) silently widened what a
        # row could claim, and its `evidence`/`citations` list belongs to no change shape: evidence
        # is attached to the *answer*, not to one bullet rewrite.
        "record_of": {"raw": "TailorChangeItem"},
        "drilled": {},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "tailoredDict": {
        # One name, and the fallback that hands back `raw` when it is missing: the save body is
        # built from the run, and the run always carries the dict.
        "record_of": {"raw": "TailorMap"},
        "drilled": {},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "tailorDiffDict": {
        "record_of": {"raw": "TailorMap"},
        "drilled": {},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "coverLetterText": {
        # Two callers, one dict: `useCoverLetter` relays POST /jobs/{id}/cover-letter untouched, and the
        # copilot's `cover_letter` artifact carries `generate`'s answer as its payload. #158 deleted the
        # seven names that had no author (`content`/`text`/`markdown`/`body` beside the real `letter`, and
        # the whole nested `coverLetter`/`cover_letter` drill) -- an answer that never carried the letter
        # used to be able to look like a letter that was empty.
        "record_of": {"raw": "CoverLetterMap"},
        "drilled": {},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "structuredResumeToMarkdown": {
        # The renderer of the tailor panel's document. Its one production caller is
        # `normalizeTailor`, which hands over `tailored` -- the parse answer with its bullets,
        # `profile.summary` and skill order edited -- so the parse prompt is the only author of
        # every name here. #147 deleted 27 of the 48 names this probed: the three `structured`
        # wrappers (no producer nests a resume under that key -- `ResumeVersionItem.structured` is
        # a DTO field, and this reader never receives a version), the snake_case twins beside every
        # live list, `endDate`/`startDate` (those belong to `ResumeDtos.ExperienceItem`, the
        # editable-rows API, which is where the aliases looked authored), `current` and with it the
        # unreachable "Present" branch, a project `description` line, top-level `name`/`headline`/
        # `summary`, and `technologies` -- the read #106 had already proved no service emits.
        "record_of": {"s": "ParsedResumeMap", "profile": "ParsedProfileMap",
                      "e": "ParsedExperienceItem", "p": "ParsedProjectItem",
                      "ed": "ParsedEducationItem",
                      # `bulletList` is a local helper called with an experience row and a project
                      # row and nothing else, so its parameter genuinely has two authors; both draw
                      # `bullets`, so the union still cannot excuse a name neither one carries.
                      "o": ["ParsedExperienceItem", "ParsedProjectItem"]},
        "drilled": {"profile": ("s", "profile")},
        "elements": {"e": ("s", "experience"), "p": ("s", "projects"),
                     "ed": ("s", "education")},
        "blind": {},
        "dynamic": {},
    },
    "groupSkillBuckets": {
        # Shared by the two resume readers, and fed the same `skills` list both of them reach
        # through `s`: `_merge_skills` overwrites the prompt's version, so its literal -- not the
        # prompt -- is what a row carries. #147 deleted the pre-grouped branch here, which asked for
        # `skills`/`items`/`group`/`level` on a row that only ever has `name`/`category`/
        # `proficiency`, and with it the `skill` and `group` twins of the two names that work.
        "record_of": {"s": "ParsedResumeMap", "g": "MergedSkillItem"},
        "drilled": {},
        "elements": {"g": ("s", "skills")},
        "blind": {},
        "dynamic": {},
    },
    "normalizeStructuredResume": {
        # The mapper both resume callers feed from `structured` -- the jsonb `ResumeService` persists
        # verbatim out of `parse_resume`, so the parse prompt is the only author of every name here,
        # exactly as it is for the renderer above. #148 measured this reader at 39 sites / 73 names
        # and its four slices (`8ccf945` wrapper, `d66faa0` 24 alias spellings, `596e0d9` 5 reads with
        # no author and the 4 page renders they made unreachable, `6aab196` 8 view-side alias fields
        # and the 7 fallback reads that named them) left the 33 sites below, every one of them a key
        # the prompt draws. Nothing in the reader now probes a spelling nobody writes.
        # The one name this entry used to leave unattributed is `links`: the call read
        # `list(profile ?? s, "links")`, and a receiver that is an expression rather than an identifier
        # has no binding to check. #162 measured the fallback as dead weight -- `links` is a key of the
        # profile map, which the parse prompt always draws, and the top-level skeleton has no such key,
        # so `?? s` could only ever answer `[]` -- and deleted it, which leaves the read on `profile`
        # where the census can see it.
        "record_of": {"s": "ParsedResumeMap", "profile": "ParsedProfileMap",
                      "e": "ParsedExperienceItem", "p": "ParsedProjectItem",
                      "ed": "ParsedEducationItem"},
        "drilled": {"profile": ("s", "profile")},
        # Three `.map` callbacks over lists drilled out of `s` -- the shape #148 taught
        # `_broken_links` to accept, since a row reached by `.map` is as much a record as one reached
        # by `for…of` and the plain form only proved the local was *some* callback parameter.
        "elements": {"e": ("s", "experience"), "p": ("s", "projects"),
                     "ed": ("s", "education")},
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
    "normalizeChatActions": {
        # The copilot's CTA row. `raw` has two authors because the mapper is shared by the two paths
        # that render an assistant turn: POST /copilot/chat answers with `ChatResponse`, and the
        # history path replays the persisted row as `MessageItem`. Both carry `actions`, which is why
        # #149 made this reader pick that name itself rather than receive a list its callers had
        # already picked -- as a pre-picked parameter the probe was consulted by nobody, so binding it
        # would have declared a dead read live.
        # `a` is one action row, and `pyadd` is what makes it a producer at all: `_derive_actions`
        # appends its literals through the `add(…)` closure, so no record, model or `Name.append`
        # states the shape. The kinds those literals carry are read off a table rather than a call
        # site (`CHAT_ACTION_ROUTES[kind]`), which is what `_route_problems` covers instead.
        "record_of": {"raw": ["ChatResponse", "MessageItem"], "a": "ChatActionItem"},
        "drilled": {},
        "elements": {"a": ("raw", "actions")},
        "blind": {},
        "dynamic": {},
    },
    "normalizeNextQuestion": {
        # The follow-up the answer endpoint proposes. #157 pulled this read out of `actions.ts`, where it
        # lived beside ten aliases and had no author to check against, because the page's badge branches
        # on the value: the wire calls it `action`, the reader asked for `kind`/`type`/`nextAction`/
        # `next_action`, so every question after the first wore the "Opening" badge. `raw` is the map
        # `InterviewService.answer` relays under `next`, whose keys only `decide_next` states.
        "record_of": {"raw": "NextQuestionMap"},
        "drilled": {},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeArtifacts": {
        # The cards under a copilot answer, bound by #145a. `raw` has the same two authors as the
        # action row above (the live reply and the persisted turn), and both carry `artifacts` -- which
        # is why the mapper picks that name itself now instead of taking a list its caller had picked,
        # the same correction #149 made for `actions`.
        #
        # `a` is where this entry differs from every other row here: its producer is a *consensus*.
        # `_collect_artifacts` appends five literals in two shapes, so the keys the reader may use are
        # the ones all five draw. The mapper used to ask for nine names on three sites -- `kind`,
        # `title`/`name`/`label`, `data`/`value` -- none of which any row carries, and each one came
        # with a fallback that turned the absence into a value (`?? "text"` for the type, `?? a` for
        # the payload), so the card silently rendered a kind no producer writes and a heading the
        # renderer had already decided on.
        "record_of": {"raw": ["ChatResponse", "MessageItem"], "a": "ArtifactItem"},
        "drilled": {},
        "elements": {"a": ("raw", "artifacts")},
        "blind": {},
        "dynamic": {},
    },
    "normalizeDimensions": {
        # The same map `normalizeMatch` drills, handed over by that mapper's own body
        # (`dimensions: normalizeDimensions(m)`), so it answers to the two authors of a match and to
        # nothing else. #150 is why this reader has four sites instead of six receivers' worth: the
        # `dimensions`/`dimension_scores`/`dimensionScores`/`breakdown`/`scores` probe it opened with
        # has no author on either service, and neither did anything it then read off the entries it
        # walked (`score`/`value`/`points`, `label`/`name`, `note`/`reason`/`comment`, `evidence`) or
        # the `${key}_score`/`${key}Score` aliases it tried beside each column. What is left is one
        # literal name per dimension, bounded by `_match_dimensions()` rather than by a candidate
        # list here -- and by the label-table rule, since the *labels* are a read no record answers.
        "record_of": {"raw": ["MatchResult", "MatchSummary"]},
        "drilled": {},
        "elements": {},
        "blind": {},
        "dynamic": {},
    },
    "normalizeEvidence": {
        # The citation list under an AI conclusion, and the widest fan-in of any reader here: six call
        # sites, three row authors, two envelopes. `raw` is the envelope only for the two callers that
        # hand the response over whole -- the tailor answer (`evidence`) and the cover-letter answer
        # (`sources`) -- while `normalizeMatch`, `normalizeMessages` and `useCopilotChat` drill the
        # list themselves first, which is what the `Array.isArray` branch is for. Those two envelopes
        # share no component, so the union below cannot cover a rename on either side.
        #
        # 49 names on 16 sites at entry, measured with this gate's own scanner; 14 remain, 12 of them on
        # the row. The deletion is not an alias diet but a shape: the reader drilled
        # `pick(e, "source", "doc", "document", "metadata")` into a local and tried eighteen names on
        # it (4 of its 16 sites), and **no producer on either service writes an object under any of
        # those keys** -- `EvidenceItem.source` is the string `compute_match` fills from the chunk's own
        # title. Every read through that local answered undefined, its `?? str(e, …)` fallbacks carried
        # the site, and the match's document title reached the card as nothing. `href`/`url` went the
        # same way: no row carries either, so `Evidence.href` was empty on every path and
        # `EvidenceList` linked only through its caller's `hrefFor`.
        "record_of": {"raw": ["TailorMap", "CoverLetterMap"],
                      "e": ["EvidenceItem", "RetrievedEvidenceItem", "CopilotSourceItem"]},
        "drilled": {},
        "elements": {"e": "items"},
        "blind": {},
        # `items` is the list itself, not a map with keys: either the caller handed it over already
        # drilled (so `Array.isArray` returns the argument) or `list(raw, "evidence", "sources")
        # drilled it here. Either way there is no name left to read off it, which is the one thing
        # `record_of` cannot express -- and the row it holds is bound above, where the reads are.
        "dynamic": {"items": "the evidence list this reader either receives pre-drilled or drills out"
                             " of its own argument: a list has no key to read, only the rows it holds, "
                             "and those are bound as `e`"},
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
    "normalizePage": {
        # The list envelope. `raw` is bound to the one record the backend answers for a paged route
        # (`common/PageDTO.java`, whose four components are the four names read here), and the mapper's
        # other branch is `GET /activity/runs`, which answers a bare JSON array and therefore carries
        # no name to bind. The sixteen names that went in #159 were Spring-`Page` spellings
        # (`content`/`totalElements`/`number`/`sizePerPage`…) and wrapper guesses (`data`/`results`/
        # `records`/`list`/`doc`/`document`/`metadata`) no controller in this repo returns: a payload
        # carrying them was never tolerated, it was read as an empty page.
        "record_of": {"raw": "PageDTO"},
        "drilled": {},
        "elements": {},
        "blind": {},
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

_ACCESSORS_HEAD = (r"\b(?:str|strOr|num|bool|list|pick|rec|int|pct|pathOf)"
                   # A typed accessor reads like any other call once the annotation is skipped:
                   # `pick<Record<string, unknown>>(raw, "company")` is a read of `company`, and
                   # skipping only the generic -- not the call -- is what keeps that site visible.
                   # `pathOf` joined in #151 for the reason the list already carries `pick`: it takes a
                   # payload and a list of names (`pathOf(e, "section")`) and splits whatever it finds,
                   # so excluding it left the breadcrumb read out of the site count entirely --
                   # invisible tolerance is still tolerance. Measured: adding it gives no other bound
                   # reader a single new site, because this reader is the only one that calls it.
                   )
# The generic in one constant instead of two copies: #162's oracle has to skip the same annotation the
# census does, and the group that took `[^<>]*` once walked straight past `pick<Record<string, …>>`,
# which is the miss #161 measured as ten names out of twenty-five.
_GENERIC = r"(?:<[^<>]*(?:<[^<>]*>[^<>]*)*>)?"
_ACCESSORS = _ACCESSORS_HEAD + _GENERIC + r"\(\s*"
_ID_OF = r"\bidOf\(\s*"
# The census's two finders, named so #162's agreement rule can audit the pattern the census actually
# uses. Written inline, the composition `accessor + (identifier) , (to-the-next-paren)` was readable
# only by re-typing it, and a re-typed copy is the thing this file bans (#160/#161).
SITE_RECEIVER = r"([A-Za-z_$][\w$.]*)\s*,([^)]*)\)"
CENSUS_SITE = re.compile(_ACCESSORS + SITE_RECEIVER)
ID_SITE = re.compile(_ID_OF + r"([A-Za-z_$][\w$.]*)\s*,")
# Helpers whose call sites the scanner above reads as part of their caller's census. `idOf` takes a
# row and tries six spellings of its identifier, so binding it separately would describe the same
# read twice -- and leaving it out of every census would be the blind spot #159's ban refuses.
FOLDED_ACCESSORS = {"idOf"}


@lru_cache(maxsize=None)
def _body(function_name: str) -> str:
    """One mapper's body in normalize.ts, through the shape gate's probe rather than a copy of it.

    The two copies differed only in whether `export ` was required, so a declaration could satisfy one
    opener and be invisible to the other; #159 made both tolerate a generic before the paren, and #160
    collapsed them into the one probe that does.
    """
    return _ts_function_body(function_name)


@lru_cache(maxsize=None)
def _id_of_keys() -> set[str]:
    """The names `idOf` reaches for, read out of its own body rather than copied here."""
    body = _body("idOf")
    return {key for group in re.findall(r'\(\s*raw\s*,([^)]*)\)', body) for key in _NAME.findall(group)}


def _sites(function_name: str) -> list[dict]:
    """Each accessor call: the variable it reads off, the names it tries, and where it sits."""
    body = _body(function_name)
    sites = []
    for finder, keys in ((CENSUS_SITE, None), (ID_SITE, _id_of_keys())):
        for match in finder.finditer(body):
            receiver = match.group(1)
            candidates = sorted(keys) if keys else _NAME.findall(match.group(2))
            if not candidates:
                continue  # an accessor with no name to try is not a read of a key
            line = body.count("\n", 0, match.start()) + 1
            sites.append({"receiver": receiver, "keys": tuple(candidates), "line": line,
                          "text": match.group(0).replace("\n", " ")[:90]})
    return sites


# The oracle's finder is the census's own head and generic, minus the `\s*` that follows the paren: two
# patterns written by hand would drift apart, and the drift is the defect this rule is looking for.
_CALL_OPEN = re.compile(_ACCESSORS_HEAD + _GENERIC + r"\(")
_BARE = re.compile(r"[A-Za-z_$][\w$.]*")
# The census pulls a name out of a call with `_NAME` below, which only recognises double quotes, so a
# read written `str(profile, 'headline')` is invisible to it *and* to an oracle that asks the same
# question the same way. #163 measured the shared blind spot at this plane -- 246 of normalize.ts's
# reads are double-quoted, 0 single-quoted, 0 template-literal, and actions.ts agrees -- so the gap is
# latent, and latent is exactly when a scanner should already be wide: recognising all three spellings
# TypeScript allows costs nothing today and turns the next one into a divergence this file reports.
_QUOTED = re.compile(r"(?:\"[^\"\n]*\"|'[^'\n]*'|`[^`\n]*`)")
_NAME = re.compile(r'"([^"\n]*)"')
_DECLARATION = re.compile(r"\bfunction\s+$")


def _blank_ts_noise(source: str) -> str:
    """Comments and string bodies as spaces, with length, line breaks and interpolations kept.

    The oracle has to find calls, and a call *inside* a doc comment -- normalize.ts carries three, one
    of them `list(e.g. a bare `List<TimelineEvent>`)`) -- is not a read of anything. Blank, do not
    delete: every offset in the result still lines up with the source, so a call found here can be
    reported with a real line number. A template literal's `${…}` is left alone because it is code, not
    text: `push("###", title, str(p, "period") ? `(${str(p, "period")})` : "")` reads `period` twice,
    and blanking the whole backtick string hid the second one from the oracle the first time it ran.
    """
    out, index, length = list(source), 0, len(source)
    while index < length:
        pair = source[index:index + 2]
        if pair == "//":
            end = source.index("\n", index)
        elif pair == "/*":
            end = source.index("*/", index) + 2
        elif source[index] in "\"'":
            end = _string_end(source, index)
            _fill(out, index + 1, end - 1)
            index = end
            continue
        elif source[index] == "`":
            index = _blank_template(source, out, index)
            continue
        else:
            end = index + 1
        if pair in ("//", "/*"):
            _fill(out, index, end)
        index = end
    return "".join(out)


def _fill(out: list, start: int, end: int) -> None:
    for position in range(start, end):
        if out[position] != "\n":
            out[position] = " "


def _string_end(source: str, start: int) -> int:
    """The index just past the quote that closes the literal opening at `start`."""
    quote, index = source[start], start + 1
    while index < len(source) and source[index] != quote:
        index += 2 if source[index] == "\\" else 1
    return index + 1


def _blank_template(source: str, out: list, start: int) -> int:
    """Blank one backtick string, skipping over every `${…}` it holds, and return the index past it."""
    index = start + 1
    while index < len(source):
        char = source[index]
        if char == "`":
            return index + 1
        if char == "\\":
            _fill(out, index, index + 2)
            index += 2
            continue
        if source.startswith("${", index):
            index = _interpolation_end(source, index)
            continue
        if char != "\n":
            out[index] = " "
        index += 1
    raise AssertionError("a template literal never closes: the file shape changed under this probe")


def _interpolation_end(source: str, start: int) -> int:
    """The index past the `}` that closes the `${` opening at `start`, literals and braces counted."""
    depth, index = 1, start + 2
    while index < len(source):
        char = source[index]
        if char in "\"'`":
            index = _string_end(source, index)
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    raise AssertionError("an interpolation never closes: the file shape changed under this probe")


def _ts_args(source: str, open_paren: int) -> tuple[str, int]:
    """The text between one call's parentheses, and the index just past its closing paren."""
    depth, index = 0, open_paren
    while index < len(source):
        char = source[index]
        if char in "\"'`":
            quote, index = char, index + 1
            while index < len(source) and source[index] != quote:
                index += 2 if source[index] == "\\" else 1
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return source[open_paren + 1:index], index + 1
        index += 1
    raise AssertionError("a call in normalize.ts never closes: the file shape changed under this probe")


def _ts_top_level(text: str) -> list[str]:
    """Split an argument list on the commas at this call's own depth, skipping nested brackets."""
    parts, chunk, index, depth = [], "", 0, 0
    while index < len(text):
        char = text[index]
        if char in "\"'`":
            quote, start = char, index
            index += 1
            while index < len(text) and text[index] != quote:
                index += 2 if text[index] == "\\" else 1
            index += 1
            chunk += text[start:index]
            continue
        if char in "([{":
            depth += 1
        elif char in ")]}":
            depth -= 1
        if char == "," and depth == 0:
            parts.append(chunk.strip())
            chunk = ""
        else:
            chunk += char
        index += 1
    parts.append(chunk.strip())
    return [part for part in parts if part != ""]


@lru_cache(maxsize=None)
def _key_read_calls(source: str) -> tuple[dict, ...]:
    """Every accessor call that tries a name, found by pairing parentheses instead of by a regex.

    `_sites` is the census every other rule here reads through, and it finds a call by matching
    `\\(\\s*(name)\\s*,([^)]*)\\)` -- so the shape of the *pattern* decides what counts as a read. Two
    shapes escape it: a receiver that is an expression rather than an identifier (`list<string>(profile
    ?? s, "links")`, `num(rows[j], "score", "value")`) never reaches the comma, and a name argument
    sitting past an inner `)` is cut off. A third escape is not in the finder at all but in the name
    extractor: `_NAME` knows only double quotes, so `str(profile, 'headline')` matches and then yields
    no candidates, which `_sites` drops -- invisible to census and oracle alike until #163 widened the
    oracle to every spelling TypeScript allows. This oracle asks the same question without those
    assumptions: find the call, pair its parentheses to get the whole argument
    list, and keep it as a key read exactly when every argument after the first is a quoted literal --
    which is what leaves
    `pct(num(row, "score"))` out on the outside (one argument, and not a name) while the inner `num`
    still counts, because the walk continues *into* a call rather than past it. `idOf` is folded here
    the way `_sites` folds it: its own call sites carry a fallback prefix, not a name, so the names it
    reaches for are the ones read out of its body.
    """
    clean = _blank_ts_noise(source)
    folded = tuple(sorted(_id_of_keys()))
    calls, index = [], 0
    while True:
        match = _CALL_OPEN.search(clean, index)
        if match is None:
            break
        index = open_paren = match.end() - 1
        if _DECLARATION.search(clean, 0, match.start()):
            continue
        _, end = _ts_args(clean, open_paren)
        parts = _ts_top_level(source[open_paren + 1:end - 1])
        names = parts[1:]
        if names and all(_QUOTED.fullmatch(part) for part in names):
            calls.append({"name": source[match.start():open_paren].strip(), "receiver": parts[0],
                          "keys": tuple(part[1:-1] for part in names),
                          "line": source.count("\n", 0, match.start()) + 1})
    for match in re.finditer(r"\bidOf\s*\(", clean):
        if _DECLARATION.search(clean, 0, match.start()):
            continue
        open_paren = clean.index("(", match.end() - 1)
        _, end = _ts_args(clean, open_paren)
        parts = _ts_top_level(source[open_paren + 1:end - 1])
        if parts:
            calls.append({"name": "idOf", "receiver": parts[0], "keys": folded,
                          "line": source.count("\n", 0, match.start()) + 1})
    return tuple(sorted(calls, key=lambda call: call["line"]))


def _search_group_keys() -> list[str]:
    """The list names `SEARCH_GROUPS` walks, read out of that table rather than repeated here."""
    source = NORMALIZE.read_text(encoding="utf-8")
    start = source.index("export const SEARCH_GROUPS")
    return re.findall(r'key:\s*"([^"]+)"', source[start:source.index("\n];", start)])


def _search_hits() -> dict[str, str]:
    """Which record answers for each group, off `SearchResponse`'s own declaration."""
    body = _java_record_body("search/dto/SearchDtos.java", "SearchResponse")
    return {key: record for record, key in re.findall(r"List<(\w+)>\s+(\w+)", body)}


def _dimension_labels() -> set[str]:
    """The keys of the browser's bar-label table, read out of the file that looks them up.

    `DIMENSION_LABELS[key]` is a read whose key is a variable and whose producer is neither service:
    the table is the browser's own copy of the dimension vocabularies, which is exactly why it needs
    a rule -- an entry no reader can key is a name the UI promises to label forever, and a name the
    readers produce with no entry draws a raw column name where a word belongs.
    """
    source = NORMALIZE.read_text(encoding="utf-8")
    if "const DIMENSION_LABELS" not in source:
        raise AssertionError("DIMENSION_LABELS is gone from normalize.ts: the rule that bounds the "
                             "bar labels has no table to read, so it would pass on an empty set")
    start = source.index("const DIMENSION_LABELS")
    block = source[start:source.index("\n};", start)]
    keys = set(re.findall(r'^\s*(\w+):\s*"[^"]*"', block, re.M))
    if not keys:
        raise AssertionError("DIMENSION_LABELS no longer declares one `name: \"Label\"` entry per "
                             "dimension: the reader of it would be guessing at the shape again")
    return keys


def _match_dimensions() -> tuple[str, ...]:
    """What a match score is made of, read out of the arithmetic that makes it.

    `_overall(technical, experience, projects, education)` weights its parameters by position against
    `_OVERALL_WEIGHTS`, and `compute_match` answers with a field per name -- so the signature is the
    producer's one statement of the dimension vocabulary. Copying those four words into the table
    that checks them would leave a rename on the service side with nothing to disagree with.
    """
    fn = _sole("_overall")
    if fn is None:
        raise AssertionError("_overall is not exactly one function under app/: the rule that bounds "
                             "the match's dimension bars reads a signature that has moved")
    names = tuple(argument.arg for argument in fn.args.args)
    if len(names) < 2:
        raise AssertionError(f"`_overall` weights {names or 'nothing'}: a one-dimensional overall "
                             "score is a different feature, and this reader's bars should follow")
    return names


def _interview_dimensions() -> set[str]:
    """ai-service's interview `DIMENSIONS`, the other vocabulary the bar-label table serves.

    The finalize and evaluate prompts interpolate it key by key (`", ".join(f'"{d}": 0.0-1.0' …)`),
    so the list is what the model is asked to return, and `normalizeInterviewDims` walks whatever
    comes back. Today none of those names carries a label -- the reader falls through to the
    snake-split -- which is copy rather than contract, and #141 left it alone for that reason.
    """
    path = Path(__file__).resolve().parents[1] / "app" / "features" / "interview.py"
    declared = re.search(r"^DIMENSIONS\s*=\s*\[([^\]]*)\]", path.read_text(encoding="utf-8"), re.M)
    if declared is None:
        raise AssertionError("interview.py no longer declares DIMENSIONS as one bracketed list: the "
                             "label table's other half would be checked against nothing")
    return set(re.findall(r'"([^"]+)"', declared.group(1)))


def _chat_routes() -> dict[str, str]:
    """The destinations `normalizeChatActions` builds, read out of the table it builds them with.

    Half of this reader's contract is not a record field at all: the wire carries a `kind` and the
    browser owns where it goes. Copying the keys into this file would let the gate stay green the
    moment a new kind forgot its route -- which is the exact defect #149 found on the page, so the
    table is parsed from `normalize.ts` instead of restated here.
    """
    source = NORMALIZE.read_text(encoding="utf-8")
    start = source.index("export const CHAT_ACTION_ROUTES")
    block = source[start:source.index("\n};", start)]
    pairs = re.findall(r'^\s*(\w+):\s*"([^"]+)"', block, re.M)
    if not pairs:
        raise AssertionError("CHAT_ACTION_ROUTES no longer declares a `kind: \"path\"` entry each: "
                             "the rule that bounds which kinds are routable has nothing to read")
    return dict(pairs)


def _page_file(route: str) -> Path | None:
    """The app-router page a URL path lands on. A `(group)` directory costs no path segment, and a
    `{slot}` in a template is served by a `[slot]` directory -- so this resolves the route the way
    Next does rather than the way the table's author hoped."""
    segments = [s for s in route.split("#")[0].strip("/").split("/") if s]

    def walk(directory: Path, rest: list[str]) -> Path | None:
        if not rest:
            page = directory / "page.tsx"
            return page if page.exists() else None
        head, *tail = rest
        for child in sorted(directory.iterdir()):
            if not child.is_dir():
                continue
            slot = (re.fullmatch(r"\[[^\]]+\]", child.name)
                    and re.fullmatch(r"\{[^}]+\}", head))
            if child.name.startswith("(") and child.name.endswith(")"):
                found = walk(child, rest)
            elif child.name == head or slot:
                found = walk(child, tail)
            else:
                continue
            if found is not None:
                return found
        return None

    return walk(ROOT_FRONTEND / "app", segments)


def _route_problems() -> list[str]:
    """Every kind the orchestrator can offer has to land on a page that exists, and every anchor it
    names has to be an id on that page. `MessageRow` filters a chip with no href out of the reply,
    so either gap is a call to action the user never sees -- not an error anyone could read."""
    routes, problems = _chat_routes(), []
    spec = PRODUCERS["ChatActionItem"]
    kinds = _added_values(*spec[1], "kind")
    if kinds != set(routes):
        problems.append(f"_derive_actions offers kinds {sorted(kinds)} while CHAT_ACTION_ROUTES "
                        f"routes {sorted(routes)}: an unrouted kind silently loses its chip, and a "
                        "route no producer writes is a destination the table only pretends to have")
    for kind, route in sorted(routes.items()):
        page = _page_file(route)
        if page is None:
            problems.append(f"{kind}: CHAT_ACTION_ROUTES points at {route!r}, which no page.tsx "
                            "under frontend/src/app serves")
            continue
        anchor = route.split("#")[1] if "#" in route else None
        if anchor and f'id="{anchor}"' not in page.read_text(encoding="utf-8"):
            problems.append(f"{kind}: {route!r} anchors at #{anchor}, which is not an id in "
                            f"{page.relative_to(ROOT_FRONTEND.parent)}")
    return problems


def _appended_shapes(func_name: str, list_name: str) -> list[set[str]]:
    """Every dict literal a function appends to one of its lists, as its key set.

    A list item has no record and no model to name it -- `compute_resume_score` loops over
    `detail.append({...})` -- but its shape is stated exactly once in the source, and that is as
    checkable as either.

    The list may be an attribute rather than a local: `orchestrator._collect_artifacts` fills the
    copilot's citations with `out.sources.append({...})`, onto a field of its own argument, and
    `ast.unparse` reads that as the name the table gives it. A bare local unparses to its own
    identifier, so every entry written before #151 matches exactly what it matched before.
    """
    fn = _sole(func_name)
    if fn is None:
        raise AssertionError(f"{func_name!r} is not exactly one function under app/: the table "
                             "names a producer that moved, so the rule it feeds compares nothing")
    found = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append" and node.args
                and isinstance(node.args[0], ast.Dict)
                and ast.unparse(node.func.value) == list_name):
            item = node.args[0]
            if any(not isinstance(k, ast.Constant) or not isinstance(k.value, str)
                   for k in item.keys):
                raise AssertionError(f"{func_name}.{list_name} appends a dict with a computed key")
            found.append({k.value for k in item.keys})
    if not found:
        raise AssertionError(f"{func_name}.{list_name} is never appended to from a dict literal: "
                             "the table names an item producer whose literal has stopped being one")
    return found


def _action_whitelist() -> set[str]:
    """The `action` values `decide_next` will pass through, read off its own membership test.

    The function whitelists the LLM's answer with `out.get("action") in (…)` and coerces everything
    else, so that tuple -- not a list kept here -- is what the browser can ever receive.
    """
    fn = _sole("decide_next")
    assert fn is not None, "decide_next moved; the follow-up whitelist has no source to read"
    for node in ast.walk(fn):
        if (isinstance(node, ast.Compare) and any(isinstance(op, ast.In) for op in node.ops)
                and isinstance(node.comparators[0], ast.Tuple)):
            values = {e.value for e in node.comparators[0].elts}
            assert values and all(isinstance(v, str) for v in values), values
            return set(values)
    raise AssertionError("decide_next no longer whitelists its action with a tuple of literals")


def _badge_kinds() -> set[str]:
    """The `question.kind === "…"` literals the interview session page branches its badge on."""
    source = (ROOT_FRONTEND / "app" / "(app)" / "interviews" / "[id]" / "page.tsx").read_text(
        encoding="utf-8")
    found = set(re.findall(r'question\.kind === "([\w-]+)"', source))
    assert found, "the session page no longer branches on question.kind; this rule has no consumer"
    return found


def _appended_keys(func_name: str, list_name: str) -> set[str]:
    """The keys of the dict literal a function appends -- when every literal draws the same set.

    Repetition is allowed only while the shape is one thing: `suggest_resume_improvements` appends
    three cards, and three identical contracts are still one. A list whose literals differ is the
    `pycons` case, whose reader may depend on the consensus only.
    """
    found = _appended_shapes(func_name, list_name)
    if any(shape != found[0] for shape in found[1:]):
        raise AssertionError(
            f"{func_name}.{list_name} appends {len(found)} different key sets "
            f"{sorted(tuple(sorted(s)) for s in found)}: the item has no single contract to check")
    return found[0]


def _appended_field_values(func_name: str, list_name: str, key: str) -> list[str]:
    """The string each appended literal puts under `key`, in source order.

    A heterogeneous list's discriminator is the one thing every row must answer with a literal the
    browser can switch on: `_collect_artifacts` writes `"type": "match"` and four siblings, and the
    card's `switch (artifact.type)` has to be a read of that set rather than of a list someone keeps
    next to it. A row that omits the key, or computes its value, is reported instead of guessed at.
    """
    fn = _sole(func_name)
    values = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr == "append" and node.args
                and isinstance(node.args[0], ast.Dict)
                and ast.unparse(node.func.value) == list_name):
            item = node.args[0]
            pairs = {k.value: v for k, v in zip(item.keys, item.values)
                     if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            if key not in pairs:
                raise AssertionError(f"{func_name}.{list_name} appends a row with no {key!r}: every "
                                     "row of a switched list has to name its own kind")
            if not (isinstance(pairs[key], ast.Constant) and isinstance(pairs[key].value, str)):
                raise AssertionError(f"{func_name}.{list_name} computes {key!r}, so no reader can be "
                                     "checked against a fixed set of values")
            values.append(pairs[key].value)
    assert values, f"{func_name}.{list_name} appends nothing"
    return values


def _helper_literals(func_name: str, helper_name: str) -> list:
    """The dict literals one local helper is called with inside a function.

    `_derive_actions` appends its action rows through a closure -- `add({...})`, which de-duplicates
    by json key before pushing onto `out.actions` -- so no `Name.append(dict)` appears in its body and
    `pyappend` cannot see the shape at all. A call with a computed key, or no literal call at all,
    means the item has no contract this gate can read, which is a statement about the source rather
    than a reason to skip the reader.
    """
    fn = _sole(func_name)
    if fn is None:
        raise AssertionError(f"{func_name!r} is not exactly one function under app/: the table names a "
                             "producer that moved, so the rule it feeds compares nothing")
    found = []
    for node in ast.walk(fn):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == helper_name and node.args
                and isinstance(node.args[0], ast.Dict)):
            item = node.args[0]
            if any(not isinstance(k, ast.Constant) or not isinstance(k.value, str)
                   for k in item.keys):
                raise AssertionError(f"{func_name}.{helper_name}(...) is called with a computed key")
            found.append(item)
    if not found:
        raise AssertionError(f"{func_name} never calls {helper_name}(...) with a dict literal: the "
                             "table names an item producer whose literal has stopped being one")
    return found


def _added_key_sets(func_name: str, helper_name: str) -> list[tuple[str, ...]]:
    """The key set of each such literal, one entry per call. The shapes stay separate because
    `_emitted` has to answer with their union -- CENSUS pins the per-literal sets so that union
    cannot cover one row's rename with another row's live sibling."""
    return [tuple(sorted(k.value for k in item.keys))
            for item in _helper_literals(func_name, helper_name)]


def _added_values(func_name: str, helper_name: str, key: str) -> set[str]:
    """What one string-literal field of those rows can hold: the action kinds the wire can carry.

    A value built at runtime (`f"open_{thing}"`) is refused rather than guessed at, because the rule
    that reads it compares a set of names against a table of routes.
    """
    values = set()
    for item in _helper_literals(func_name, helper_name):
        for k, v in zip(item.keys, item.values):
            if k.value == key:
                if not isinstance(v, ast.Constant) or not isinstance(v.value, str):
                    raise AssertionError(
                        f"{func_name}.{helper_name} writes {key!r} from {ast.unparse(v)!r}: the rule "
                        "that bounds which kinds exist would have to invent one")
                values.add(v.value)
    if not values:
        raise AssertionError(f"no {func_name}.{helper_name}(...) literal carries {key!r}: the table "
                             "reads a field the producer stopped writing")
    return values


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


def _return_branch_keys(func_name: str, key: str) -> set[str]:
    """The keys of the dict literal one answer carries under its own `key`, read off the return.

    `tailor` builds `{tailored, diff:{accepted,rejected}, notes, evidence, stats:{accepted,
    rejected}}` in a single statement, so a nested map's contract is in that source too. Transcribing
    `{accepted, rejected}` beside the reader would let a producer rename the key and keep the gate
    green, which is the drift this file exists to catch.
    """
    node = _sole(func_name)
    if node is None:
        raise AssertionError(f"{func_name} is gone: the table binds a producer the service no longer has")
    branches = [
        v for d in ast.walk(node)
        if isinstance(d, ast.Return) and isinstance(d.value, ast.Dict)
        for k, v in zip(d.value.keys, d.value.values)
        if isinstance(k, ast.Constant) and k.value == key and isinstance(v, ast.Dict)
    ]
    if not branches:
        raise AssertionError(f"{func_name} never returns a dict literal under {key!r}: the table names "
                             "a nested map whose author has stopped being one")
    shapes = [tuple(sorted(k.value for k in b.keys if isinstance(k, ast.Constant))) for b in branches]
    if len(set(shapes)) > 1:
        raise AssertionError(f"{func_name}.{key} returns {len(shapes)} different key sets {shapes}")
    return set(shapes[0])


def _prompt_item_keys(rel: str, const: str, member: tuple[str, ...]) -> set[str]:
    """The keys of one drawn map: the answer's own, a named list's item, or a named sub-object's.

    Both readings come from the same parse, so an item shape is checked against the prompt that asks
    for it rather than against a description of it. A prompt that drops the list, or draws it as
    strings, fails here instead of quietly leaving the reader's item reads unbound.
    """
    skeleton = _prompt_skeleton(rel, const)
    if not member:
        return set(skeleton)
    name = member[0]
    if name not in skeleton:
        raise AssertionError(f"{rel}::{const} draws no {name!r} member: the table names a shape "
                             "the prompt no longer asks for")
    rows = skeleton[name]
    if isinstance(rows, dict):
        return set(rows)  # a drawn sub-map (`profile`), not a list of rows
    if not isinstance(rows, list) or not rows or not isinstance(rows[0], dict):
        raise AssertionError(f"{rel}::{const}'s {name!r} is neither an object nor a list of objects, "
                             "so its items have no key set to check a reader's item reads against")
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
    if spec[0] == "pycons":
        # The keys *every* literal of a heterogeneous list draws, which is the only contract a reader
        # may lean on: `_collect_artifacts` appends five rows in two shapes, and a union would make
        # `job_id` look like something four of the five carry. CENSUS names the difference.
        return set.intersection(*_appended_shapes(*spec[1]))
    if spec[0] == "pyadd":
        # The union of the helper's literals, which is what a heterogeneous list really offers one
        # row: an action carries `job_id` or `session_id`, never both. CENSUS pins the per-literal
        # shapes so the union cannot cover one row's rename with another row's live sibling.
        return set().union(*(set(shape) for shape in _added_key_sets(*spec[1])))
    if spec[0] == "pyconst":
        return _py_const_keys(*spec[1])
    if spec[0] == "pyitem":
        return _returned_item_keys(spec[1])
    if spec[0] == "japut":
        return _java_put_keys(*spec[1])
    if spec[0] == "pyskel":
        return _prompt_item_keys(*spec[1])
    if spec[0] == "pyretsub":
        return _return_branch_keys(*spec[1])
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
        holder = parent[0] if isinstance(parent, tuple) else parent
        if holder not in (set(spec["record_of"]) | set(spec["blind"]) | set(spec["dynamic"])):
            problems.append(f"{reader}: {local!r} comes from {holder!r}, which the table neither "
                            "binds, declares blind, nor declares dynamic")
        if isinstance(parent, tuple):
            # An element row: the row has no accessor of its own to point at, so the link is stated
            # as (map, key) and both halves have to be findable -- the list drilled out of that map
            # under that key, and this local bound to the rows of exactly that list. Without the key
            # the claim is only "some element of some local", which a renamed list survives.
            key = parent[1]
            # One-way, and #147 measured the other direction free: emptying this reader's `elements`
            # of the `ed` binding left all four tests green, because nothing requires a `for…of`
            # receiver that `record_of` binds to appear here. A rule that only checks declared links
            # can be deleted link by link; closing that needs the reverse check, not this one.
            made = re.search(rf"(?:const|let)\s+([\w$]+)\s*=\s*[^;\n;]*\(\s*{re.escape(holder)}\s*,"
                             rf"[^)]*\"{re.escape(key)}\"", body)
            inline = re.search(rf"for\s*\(\s*(?:const|let)\s+{re.escape(local)}\s+of\s+[^;]*"
                               rf"\(\s*{re.escape(holder)}\s*,[^)]*\"{re.escape(key)}\"", body)
            named = made and re.search(rf"for\s*\(\s*(?:const|let)\s+{re.escape(local)}\s+of\s+"
                                       rf"{made.group(1)}\b", body)
            # #148: the same link reached by `.map` instead of `for…of`. A row written as
            # `list(s, "experience").map((e) => ({…}))` has no `for` header, and the plain-string
            # form below could not carry it either: it checks only that `e` is *a* `.map` callback
            # parameter, so renaming "experience" to a key no producer writes would have left the
            # gate green while every row of that section rendered blank. The `\s*` before `.map`
            # spans the line break a typed callback parameter forces the reader to write.
            mapped = re.search(rf"\(\s*{re.escape(holder)}\s*,[^)]*\"{re.escape(key)}\"\s*\)"
                               rf"(?:\s*\.\w+\([^)]*\))*\s*\.map\(\s*\(?\s*{re.escape(local)}\s*[,)]",
                               body)
            if not (inline or named or mapped):
                problems.append(f"{reader}: {local!r} is declared as an element of {holder!r}'s "
                                f"{key!r} list, but nothing iterates the rows drilled that way")
            continue
        if not re.search(rf"\.map\(\s*\(?\s*{re.escape(local)}\b", body):
            problems.append(f"{reader}: {local!r} is declared as an element of {parent!r}'s list "
                            "but is not a `.map` callback parameter")
    # The other direction, which #147 measured missing: emptying `elements` of the `ed` binding left
    # all four tests green, because nothing required a `for…of` element the reader actually reads from
    # to be declared at all. A row iterated by `for…of` is exactly as much a record as one reached by
    # `.map`, and the table is the only thing that says which one -- so an undeclared one is not a
    # missing annotation but a receiver whose every read is unchecked while the gate stays green.
    # #148 widened the walk to `.map`/`.flatMap` callbacks, which are the same row read reached the
    # other way: measured 0 violations over the readers bound before this unit, so it costs nothing
    # today and only closes the door a future reader can walk through.
    read = {site["receiver"] for site in _sites(reader)}
    walked = {found.group(1) for found in re.finditer(
        r"for\s*\(\s*(?:const|let)\s+([\w$]+)\s+of", body)}
    walked |= {found.group(1) for found in re.finditer(
        r"\.(?:map|flatMap)\(\s*\(?\s*([A-Za-z_$][\w$]*)\s*(?:,|\))", body)}
    for local in sorted(walked & read & set(spec["record_of"]) - set(spec["elements"])):
        problems.append(f"{reader}: {local!r} is walked by a for…of or a `.map` callback and read "
                        f"from, and the table binds it to {spec['record_of'][local]!r}, but "
                        f"{local!r} is declared in no `elements` -- so the list it walks is unnamed "
                        "and a rename of that key would cost nothing")
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


def test_no_mapper_is_left_unbound():
    """#159's ban, widened by #160. A reader that is not in READERS is a reader no rule in this file
    checks, which is how `coverLetterText` carried ten probes for four authored names until #158 had to
    go looking for it by hand: every mapper in normalize.ts whose own body asks for a literal name has
    to be bound, or be a helper this file's own scanner folds into its callers' sites.

    The first version enumerated `^export function`, and #160's probe audit found four module-private
    mappers it had never counted -- `pathOf`, `changeFrom`, `groupSkillBuckets`, `statusCountsToRows`.
    Two were bound readers anyway; the fourth read `count`/`total` off a value that `Kanban.statusCounts`
    types as `Map<String, Long>`, so the two names had no producer and the ban could not see them.
    """
    population = _mappers_that_read()
    unbound = sorted(set(population) - set(READERS) - FOLDED_ACCESSORS)
    assert unbound == [], (f"readers taking names with no producer declared: {unbound} -- "
                           "bind them in READERS, or make the scanner fold them and prove the fold")
    # The exemption is only real while the mechanism is: a folded helper is visible because _ID_OF
    # reads its call sites into every caller's census, not because this table says so.
    assert all(f"\\b{name}\\(" in _ID_OF for name in FOLDED_ACCESSORS), \
        f"{sorted(FOLDED_ACCESSORS)} claims a fold the site scanner does not perform"
    # Measured at this plane, so a new unbound reader cannot slip in under a stale count: the 30 the
    # exported census counted, plus the two module-private mappers that carry reads of their own.
    assert len(population) == 32, sorted(population)
    private = sorted(name for name, exported in _mapper_declarations() if not exported)
    assert private == ["changeFrom", "groupSkillBuckets", "pathOf", "statusCountsToRows"]
    assert sorted(n for n in private if n in population) == ["changeFrom", "groupSkillBuckets"], \
        "the private half of this census is what #160 added; if it reads empty, the ban is exported-only again"


# One enumeration for both halves of the census above, so the private-name pin cannot drift away from
# the population it claims to widen.
MAPPER_DECL = re.compile(r"^(export )?function (\w+)[<(]", re.M)


def _mapper_declarations() -> list[tuple[str, bool]]:
    """Every mapper declared in normalize.ts, with whether the module exports it."""
    return [(match.group(2), match.group(1) is not None)
            for match in MAPPER_DECL.finditer(NORMALIZE.read_text(encoding="utf-8"))]


def _mappers_that_read() -> dict[str, int]:
    """Every mapper in normalize.ts -- exported or module-private -- whose own body makes a named read.
    The two `export const` tables (SEARCH_GROUPS, CHAT_ACTION_ROUTES) hold data, not reads, so they are
    out of the population by construction rather than by exemption."""
    return {name: len(sites) for name, _ in _mapper_declarations()
            for sites in [_sites(name)] if sites}


def test_the_reads_are_actually_found():
    """Positive control: every rule above is satisfied by an empty reading, so the census itself is
    pinned -- real sites, at the receivers this gate claims to bind, against real components."""
    applications = _sites("normalizeApplication")
    assert len(applications) == 16
    assert {s["receiver"] for s in applications} == {"raw", "nested"}
    assert sum(1 for s in applications if s["receiver"] == "nested") == 3
    messages = _sites("normalizeMessages")
    # 6, down from the 7 #149 measured: `normalizeArtifacts(pick(m, "artifacts"))` became
    # `normalizeArtifacts(m)`, so the name is tried once, inside the mapper that owns the read -- the
    # same correction #149 made for `actions`, and for the same reason: as a pre-picked argument the
    # probe was consulted by nobody, so binding it there would have declared a dead read live.
    assert len(messages) == 6
    assert {s["receiver"] for s in messages} == {"m", "raw"}
    matches = _sites("normalizeMatch")
    assert len(matches) == 18
    assert {s["receiver"] for s in matches} == {"raw", "m"}
    assert sum(1 for s in matches if s["receiver"] == "m") == 17  # every payload read, incl. idOf
    # One name per site, in order -- the form #150 introduced for the dimension bars and #155 wrote
    # for the whole match map. #127 deleted four *dead* aliases from this reader and left twenty-two
    # *tolerant* ones, each beside a name an author really fills, so every site stayed live and the
    # census could only count them: 56 candidates on 18 sites, 55 distinct, against the 25 that are
    # answered somewhere. The two declared dead sites keep their pair, and `idOf` keeps the shared
    # table its own equality line already bounds.
    assert [s["keys"] for s in matches] == [
        ("match",), ("overall",), ("matchedSkills",), ("missingSkills",), ("evidence",),
        ("skillGaps",), ("jobId", "job_id"), ("resumeVersionId", "resume_version_id"),
        ("technical",), ("experience",), ("projects",), ("education",), ("whyMatch",),
        ("narrative",), ("interviewTopics",), ("preparation",), ("createdAt",),
        tuple(sorted(_id_of_keys())),
    ], [s["keys"] for s in matches]
    # Which author answers which name, per row rather than through the union: the stored projection
    # drops `interviewTopics` (so the interview card asks for a re-run instead of showing nothing) and
    # the fresh compute carries no `createdAt`, which only the persisted row can replay.
    assert "interviewTopics" in _emitted("MatchResult")
    assert "interviewTopics" not in _emitted("MatchSummary")
    assert "createdAt" in _emitted("MatchSummary")
    assert "createdAt" not in _emitted("MatchResult")
    # Both envelopes hand the map over under one key, and neither spells it any other way.
    assert [s["keys"] for s in matches if s["receiver"] == "raw"] == [("match",)]
    assert all("match" in _emitted(name) for name in READERS["normalizeMatch"]["record_of"]["raw"]), \
        "an envelope stopped carrying `match`, so the drill at the top of the mapper is a dead read"
    dims = _sites("normalizeDimensions")
    assert len(dims) == 4, dims
    assert {s["receiver"] for s in dims} == {"raw"}
    # One name per site, exactly. A fourth candidate beside a live one used to be invisible here --
    # the site stays live on the strength of its authored sibling -- so the per-site tuple is what
    # says `technical_score` cannot come back as a "tolerance" without this line noticing.
    assert [s["keys"] for s in dims] == [("technical",), ("experience",), ("projects",),
                                         ("education",)]
    # 4 sites, down from the 6 #150 measured, and the 17 candidate names those 6 tried were 16
    # unauthored. The 17th was `evidence`, read off a *dimension entry* -- a name the match map does
    # carry, one level up, where `normalizeMatch` already reads it. That is the shape this census is
    # for: a wrong receiver can still name a real column, and only the per-receiver binding sees it.
    assert {s["keys"][0] for s in dims} == set(_match_dimensions())
    # The table row itself, asserted rather than inferred from its effect. #149's reader could not
    # vanish quietly because `ChatActionItem` was its alone, and a producer no reader binds fails
    # `_producer_bookkeeping`; this one shares both of its authors with the caller that hands over
    # the map, so deleting the row would leave the four sites above read by nothing and the gate
    # green. The claim is the substantive one: a dimension reader is bound to exactly the two
    # authors of the map its own caller drills.
    assert READERS.get("normalizeDimensions", {}).get("record_of", {}).get("raw") == \
        READERS["normalizeMatch"]["record_of"]["m"], \
        "normalizeDimensions is not bound to the pair normalizeMatch binds `m` to"
    # Per author rather than through the union the liveness rule checks, because a bar that goes
    # missing after a refresh is the defect: the fresh answer and the stored row both project all
    # four columns today, and either stopping is a blank row on the job page, not a dead read.
    assert all(set(_match_dimensions()) <= _emitted(name)
               for name in ("MatchResult", "MatchSummary"))
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
    assert len(traj) == 7
    assert {s["receiver"] for s in traj} == {"t", "row", "next"}
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
    # The tailor answer is a pass-through, so its own return statement is the whole contract here --
    # including the two nested maps the reader drills, which `pyretsub` reads one key down. Before
    # #145 bound it, the reader asked for 20 names of which 5 had an author.
    tailor = _sites("normalizeTailor")
    assert len(tailor) == 2, f"the tailor reader holds {len(tailor)} sites, want the 2 that name a key"
    assert {s["receiver"] for s in tailor} == {"raw"}
    assert {k for s in tailor for k in s["keys"]} == {"stats", "notes"}
    tdiff = _sites("normalizeTailorDiff")
    assert len(tdiff) == 3, tdiff
    assert {s["receiver"] for s in tdiff} == {"raw", "diff"}
    assert {k for s in tdiff if s["receiver"] == "diff" for k in s["keys"]} == {"accepted", "rejected"}
    assert _emitted("TailorMap") == {"tailored", "diff", "notes", "evidence", "stats"}
    assert _emitted("TailorDiffMap") == {"accepted", "rejected"}
    # The change row the tailor panel crosses out. It is not exported, which is the only reason this
    # gate never saw it: it carried 19 names, of which the prompt's own `changes` item answers for 4,
    # and a fifth read (`idOf`) probed six spellings of an identifier no change row has ever carried.
    chg = _sites("changeFrom")
    assert len(chg) == 4, chg
    assert {s["receiver"] for s in chg} == {"raw"}
    assert {k for s in chg for k in s["keys"]} == {"section", "before", "after", "reason"}
    assert _emitted("TailorChangeItem") == {"section", "index", "before", "after", "reason"}
    # The two one-name helpers the save body is built from, now bound like any other reader.
    assert len(_sites("tailoredDict")) == 1
    assert len(_sites("tailorDiffDict")) == 1
    # The document a candidate copies or downloads, and the skill buckets the resume page renders off
    # it. #147 measured `structuredResumeToMarkdown` at 31 sites / 48 names and deleted 8 sites and 27
    # names; every one of them was a spelling no author of the `structured` jsonb ever wrote
    # (`workExperience`, `role`, `organization`, `endDate`/`startDate`, `techStack`, `institution`,
    # `major`, a top-level `name`/`headline`/`summary`, the `technologies` list #106 proved empty) or a
    # wrapper no caller unwraps. Both readers are bound to the parse skeleton because `ResumeService`
    # persists `parse_resume`'s answer unchanged -- the prompt, not a DTO, is their only author.
    md = _sites("structuredResumeToMarkdown")
    assert len(md) == 23, f"the markdown renderer holds {len(md)} sites, want the 23 that name a key"
    assert {s["receiver"] for s in md} == {"s", "profile", "e", "p", "ed", "o"}
    assert sum(1 for s in md if s["receiver"] == "s") == 5
    assert sum(1 for s in md if s["receiver"] == "profile") == 6
    assert sum(1 for s in md if s["receiver"] == "o") == 1
    # p and e carry one more site than names: a row's `name`/`title` is read twice in its heading.
    assert {k for s in md if s["receiver"] == "s" for k in s["keys"]} == \
        {"profile", "experience", "projects", "education", "achievements"}
    assert {k for s in md if s["receiver"] == "profile" for k in s["keys"]} == \
        {"name", "headline", "location", "email", "phone", "summary"}
    assert {k for s in md if s["receiver"] == "e" for k in s["keys"]} == \
        {"title", "company", "start", "end"}
    assert {k for s in md if s["receiver"] == "p" for k in s["keys"]} == {"name", "period", "tech"}
    assert {k for s in md if s["receiver"] == "ed" for k in s["keys"]} == {"degree", "field", "school"}
    assert {k for s in md if s["receiver"] == "o" for k in s["keys"]} == {"bullets"}
    # Per author, not as the union each receiver is checked against: `title` belongs to the experience
    # item alone, `name` to the project item alone, so a rename on either side has to cost something
    # instead of hiding behind the other's live sibling.
    assert _emitted("ParsedResumeMap") == {"profile", "experience", "projects", "education",
                                          "achievements", "skills", "languages", "careerGoals",
                                          "preferredRoles", "preferredLocations", "missingSections",
                                          "warnings"}
    assert _emitted("ParsedProfileMap") == {"name", "headline", "location", "email", "phone",
                                           "summary", "links", "yearsExperience"}
    assert _emitted("ParsedExperienceItem") == {"title", "company", "location", "start", "end",
                                                "summary", "bullets"}
    assert _emitted("ParsedProjectItem") == {"name", "role", "period", "tech", "url", "bullets"}
    assert _emitted("ParsedEducationItem") == {"degree", "field", "school", "startYear", "endYear",
                                               "gpa", "courses"}
    assert _emitted("MergedSkillItem") == {"name", "category", "proficiency"}
    # The prompt draws twelve sections and this renderer puts five of them in the document. The seven
    # others are listed so the gap stays a decision: `skills` reaches the page through the bucket
    # reader below, the other six are stored and never rendered.
    assert _emitted("ParsedResumeMap") - {k for s in md if s["receiver"] == "s"
                                          for k in s["keys"]} == {"skills", "languages", "careerGoals",
                                                                  "preferredRoles", "preferredLocations",
                                                                  "missingSections", "warnings"}
    # `technologies` has no author on either side of this contract, which is #106's fact restated from
    # the producer: the renderer's read of it went in #147, and the parse skeleton never had one.
    assert "technologies" not in _emitted("ParsedResumeMap")
    # Three of the four drawn row names the document drops: a candidate's links and years of
    # experience, an entry's own `summary`/`location`, a project's `role`/`url`, an education row's
    # `gpa`/`courses`/`startYear`/`endYear`. Parsed, persisted, and absent from the resume.
    assert _emitted("ParsedProfileMap") - {k for s in md if s["receiver"] == "profile"
                                           for k in s["keys"]} == {"links", "yearsExperience"}
    assert _emitted("ParsedExperienceItem") - {k for s in md if s["receiver"] == "e"
                                              for k in s["keys"]} == {"location", "summary", "bullets"}
    assert _emitted("ParsedProjectItem") - {k for s in md if s["receiver"] == "p"
                                            for k in s["keys"]} == {"role", "url", "bullets"}
    assert _emitted("ParsedEducationItem") - {k for s in md if s["receiver"] == "ed"
                                              for k in s["keys"]} == {"startYear", "endYear", "gpa",
                                                                      "courses"}
    buckets = _sites("groupSkillBuckets")
    assert len(buckets) == 3, buckets
    assert {s["receiver"] for s in buckets} == {"s", "g"}
    assert {k for s in buckets if s["receiver"] == "s" for k in s["keys"]} == {"skills"}
    assert {k for s in buckets if s["receiver"] == "g" for k in s["keys"]} == {"name", "category"}
    # 3 sites, down from 6 sites / 11 names: the pre-grouped carry-through branch (a nested `skills`
    # or `items` list inside the row, and `group`/`level` beside it) answered to a payload nobody
    # writes -- `raw["skills"]` is only ever `_merge_skills`' flat list. `proficiency`, the one
    # proficiency-shaped name the row does carry, is drawn and rendered nowhere: the page printed
    # `g.level`, a name with no author, so the field and that consumer went together in #147.
    assert _emitted("MergedSkillItem") - {k for s in buckets if s["receiver"] == "g"
                                          for k in s["keys"]} == {"proficiency"}
    # The mapper the resume page and the skill-suggestion panel both build their view model from.
    # 34 sites / 5 receivers, after #148 deleted the 6 sites and 40-odd probe names that had no
    # author; `s` is the jsonb itself, `profile` the one map drilled out of it, and `e`/`p`/`ed` the
    # three `.map` rows whose list-key links the entry has to keep honest.
    sr = _sites("normalizeStructuredResume")
    assert len(sr) == 34, f"the structured mapper holds {len(sr)} sites, want the 34 that name a key"
    assert {s["receiver"] for s in sr} == {"s", "profile", "e", "p", "ed"}
    assert sum(1 for s in sr if s["receiver"] == "s") == 8
    assert sum(1 for s in sr if s["receiver"] == "profile") == 7
    assert sum(1 for s in sr if s["receiver"] == "e") == 6
    assert sum(1 for s in sr if s["receiver"] == "p") == 6
    assert sum(1 for s in sr if s["receiver"] == "ed") == 7
    assert {k for s in sr if s["receiver"] == "s" for k in s["keys"]} == \
        {"profile", "experience", "projects", "education", "achievements", "careerGoals",
         "preferredRoles", "preferredLocations"}
    assert {k for s in sr if s["receiver"] == "profile" for k in s["keys"]} == \
        {"name", "headline", "email", "phone", "location", "summary", "links"}
    assert {k for s in sr if s["receiver"] == "e" for k in s["keys"]} == \
        {"company", "title", "location", "start", "end", "bullets"}
    assert {k for s in sr if s["receiver"] == "ed" for k in s["keys"]} == \
        {"school", "degree", "field", "startYear", "endYear", "gpa", "courses"}
    # A project row and an education row are read key for key -- every name the parse draws for them
    # is a slot in the view model, which is why these two can be stated as equality with the producer
    # instead of as a surplus set.
    assert {k for s in sr if s["receiver"] == "p" for k in s["keys"]} == _emitted("ParsedProjectItem")
    assert {k for s in sr if s["receiver"] == "ed" for k in s["keys"]} == \
        _emitted("ParsedEducationItem")
    # The sets it still leaves on the table, each named so a prompt that drops a key goes red here
    # rather than by shrinking a resume: an experience row's own `summary`; the profile's
    # `yearsExperience`, which no render asks for; and four top-level lists, of
    # which `skills` reaches the page through the bucket reader above and the other three are stored
    # and never rendered.
    assert _emitted("ParsedExperienceItem") - {k for s in sr if s["receiver"] == "e"
                                               for k in s["keys"]} == {"summary"}
    assert _emitted("ParsedProfileMap") - {k for s in sr if s["receiver"] == "profile"
                                           for k in s["keys"]} == {"yearsExperience"}
    assert _emitted("ParsedResumeMap") - {k for s in sr if s["receiver"] == "s"
                                          for k in s["keys"]} == {"skills", "languages",
                                                                  "missingSections", "warnings"}
    # The copilot's CTA row: four sites, and #149 measured that each one got an author only after the
    # invented names left. Before the trim this reader probed `href`/`url`/`link`/`path` beside a live
    # `payload`/`data`/`type`/`name`/`title` -- and the page filtered on `a.href`, so no wire shape
    # could ever produce a chip.
    chat = _sites("normalizeChatActions")
    assert len(chat) == 4, chat
    assert {s["receiver"] for s in chat} == {"raw", "a"}
    assert sum(1 for s in chat if s["receiver"] == "a") == 3
    assert {k for s in chat if s["receiver"] == "raw" for k in s["keys"]} == {"actions"}
    assert {k for s in chat if s["receiver"] == "a" for k in s["keys"]} == \
        {"kind", "label", "job_id", "session_id"}
    # Per author, not as the union the site is checked against: the live reply and the replayed row
    # agree on `actions`, so either one dropping the component would leave the other covering the
    # read -- and a chip row that vanishes after a refresh is exactly what this reader exists to stop.
    assert "actions" in _emitted("ChatResponse") and "actions" in _emitted("MessageItem")
    # Per literal, for the same reason: four job-located rows and one session-located row, so a rename
    # of `job_id` would have had `session_id` to cover for it inside the union `_emitted` answers with.
    assert collections.Counter(_added_key_sets("_derive_actions", "add")) == {
        ("job_id", "kind", "label"): 4,
        ("kind", "label", "session_id"): 1,
    }
    assert _emitted("ChatActionItem") == {"kind", "label", "job_id", "session_id"}
    # The follow-up question, #157. Four sites, one name each, against the map `decide_next` returns --
    # and the name the page's badge needs is one of them, which is the whole point of the move.
    nxt = _sites("normalizeNextQuestion")
    assert len(nxt) == 4, nxt
    assert {s["receiver"] for s in nxt} == {"raw"}
    assert [s["keys"] for s in nxt] == [("difficulty",), ("question",), ("topic",), ("action",)]
    assert _emitted("NextQuestionMap") - {k for s in nxt for k in s["keys"]} == {"reasoning"}
    # What the runner may answer with, and what the page has a badge for. `finish` is the one value that
    # never reaches a question at all: `InterviewService.answer` skips persisting a follow-up for it
    # (`!"finish".equals(Json.str(next, "action"))`), so the badge set is the whitelist minus that.
    actions = _action_whitelist()
    assert "followup" in actions and "next_topic" in actions and "finish" in actions, actions
    assert actions - {"finish"} <= _badge_kinds(), \
        f"a question kind the agent can ask for has no badge: {sorted(actions - {'finish'} - _badge_kinds())}"
    # Measured, not assumed: the page compares against exactly the two kinds that can reach a question.
    # "opening" is not one of them -- it is the fallback badge the ternary chain ends with, for the
    # first turn whose `questionMeta` carries a `phase` and no `action` at all.
    assert _badge_kinds() == actions - {"finish"}, \
        (f"the badge branches on {sorted(_badge_kinds())} while the decision can ask for "
         f"{sorted(actions)}: a kind with no branch renders as the fallback, which is how #157's "
         "follow-ups all wore the opening badge")
    # The cover letter, #158. One site, one name, against `generate`'s own four-key answer -- and the
    # artifact path the same reader serves is enumerated from the orchestrator's switch, so a renamed
    # artifact type would have to move this reader's producer with it.
    letter = _sites("coverLetterText")
    assert len(letter) == 1, letter
    assert letter[0]["receiver"] == "raw"
    assert [s["keys"] for s in letter] == [("letter",)]
    assert _emitted("CoverLetterMap") == {"letter", "mode", "model", "sources"}
    assert _emitted("CoverLetterMap") - {k for s in letter for k in s["keys"]} == {
        "mode", "model", "sources"}
    assert "cover_letter" in _artifact_switch(), \
        f"the copilot no longer appends a cover_letter artifact: {sorted(_artifact_switch())}"
    # The page envelope, made visible by the same fix that let the ban above see it: `normalizePage`
    # declares itself as `<T>(`, which a literal `function X(` probe walked straight past.
    page = _sites("normalizePage")
    assert len(page) == 4, page
    assert {s["receiver"] for s in page} == {"raw"}
    assert [s["keys"] for s in page] == [("items",), ("total",), ("page",), ("size",)]
    assert _emitted("PageDTO") == {"items", "total", "page", "size"}, \
        "the envelope the paged routes answer is no longer four names, so this reader is stale"
    # Dead, and named so: nothing imported the reader, so no rule but this line notices its return.
    assert "function jobDetailMatch" not in NORMALIZE.read_text(encoding="utf-8"), \
        "the dead export is back: no caller, and six names no job detail response carries"
    # The citation mapper. 10 sites and 14 names, down from the 16 sites and 49 names #151 measured with
    # this same scanner -- and the 35 that went were mostly the nested `source` object (`pick(e,
    # "source", "doc", "document", "metadata")` plus the eighteen names tried on its result), a shape no
    # author on either service writes: the only `source` any producer emits is `EvidenceItem`'s string
    # title, which the reader therefore discarded on its way to a card rendering `source.docTitle`.
    ev = _sites("normalizeEvidence")
    assert len(ev) == 10, ev
    assert {s["receiver"] for s in ev} == {"raw", "e"}
    assert sum(1 for s in ev if s["receiver"] == "raw") == 1
    assert sum(1 for s in ev if s["receiver"] == "e") == 9
    # The tenth of those nine-plus-one is `pathOf(e, "section")`, visible only because #151 added
    # `pathOf` to `_ACCESSORS`: a breadcrumb split is as much a read of `section` as a `str` is, and
    # this floor is what notices if the accessor list shrinks back and the site quietly vanishes.
    assert [s["keys"] for s in ev if s["receiver"] == "raw"] == [("evidence", "sources")]
    read_off_ev = {k for s in ev if s["receiver"] == "e" for k in s["keys"]}
    assert read_off_ev == {"criterion", "label", "score", "quote", "reasoning", "chunk_ids",
                           "chunk_id", "doc_title", "source", "document_id", "source_kind",
                           "section"}
    # Per author rather than per union. A match row is read key for key, so its surplus set is empty;
    # the retrieved row's `ref` numbers the prompt's citations and the card has no slot for it; the
    # copilot row's `type` is the literal "source" on every append.
    #
    # These three lines are the block's own work, and #151's witness measured that by subtraction: a
    # reader that probes `ref` reddens *only* CENSUS, because the name is authored, so neither the
    # liveness rule nor the global dead-site floor below has anything to say about it -- delete this
    # block and the surplus read is invisible to every rule in the gate. A fabricated name is the
    # easier world: the `len(dead) == 3` floor catches it independently, which is why the drop-the-rule
    # case had to be built on the surplus side to mean anything.
    assert _emitted("EvidenceItem") - read_off_ev == set()
    assert _emitted("RetrievedEvidenceItem") - read_off_ev == {"ref"}
    assert _emitted("CopilotSourceItem") - read_off_ev == {"type"}
    # Which of the three authors answers which read, in both directions -- the statement a union
    # cannot make. `quote` is the one name all three carry, and it is the only read that a rename of
    # any single author could hide behind: every other name here belongs to exactly one producer or
    # to a named pair.
    authors = ("EvidenceItem", "RetrievedEvidenceItem", "CopilotSourceItem")
    assert {name: sorted(a for a in authors if name in _emitted(a))
            for name in sorted(read_off_ev)} == {
        "chunk_id": ["CopilotSourceItem", "RetrievedEvidenceItem"],
        "chunk_ids": ["EvidenceItem"],
        "criterion": ["EvidenceItem"],
        "doc_title": ["RetrievedEvidenceItem"],
        "document_id": ["CopilotSourceItem", "RetrievedEvidenceItem"],
        "label": ["CopilotSourceItem"],
        "quote": ["CopilotSourceItem", "EvidenceItem", "RetrievedEvidenceItem"],
        "reasoning": ["EvidenceItem"],
        "score": ["EvidenceItem", "RetrievedEvidenceItem"],
        "section": ["EvidenceItem", "RetrievedEvidenceItem"],
        "source": ["EvidenceItem"],
        "source_kind": ["RetrievedEvidenceItem"],
    }
    # The same claim one level up, for the two envelopes: they share no component at all, which is
    # what makes the reader's two-name probe a binding rather than the blanket a union usually is.
    assert _emitted("TailorMap") & _emitted("CoverLetterMap") == set()
    # Deleting this reader's table row could not pass unnoticed: four of its five producers belong to
    # no other reader, so `_producer_bookkeeping` names them the moment the row goes (#150's silent
    # case needed an asserted row for that reason; this one needs no such line, and says so).
    assert READERS["normalizeEvidence"]["record_of"]["raw"] == ["TailorMap", "CoverLetterMap"]
    # The artifact cards, and the one list here whose rows do not all have the same shape. Both sides
    # are read out of `_collect_artifacts`: the five literals it appends, the keys every one of them
    # draws, and the remainder that distinguishes the match row.
    shapes = _appended_shapes("_collect_artifacts", "out.artifacts")
    consensus = set.intersection(*shapes)
    divergence = set.union(*shapes) - consensus
    assert len(shapes) == 5, [sorted(s) for s in shapes]
    assert consensus == {"type", "payload"}, [sorted(s) for s in shapes]
    # The divergence is a fact about the producer, not a free slot: a sixth shape, or a second
    # per-row key, has to be read here rather than absorbed into the union the reader was bound to.
    assert divergence == {"job_id"}, sorted(tuple(sorted(s)) for s in shapes)
    arts = _sites("normalizeArtifacts")
    assert len(arts) == 3, arts
    assert {s["receiver"] for s in arts} == {"raw", "a"}
    assert [s["keys"] for s in arts if s["receiver"] == "raw"] == [("artifacts",)]
    read_off_a = {k for s in arts if s["receiver"] == "a" for k in s["keys"]}
    assert read_off_a == {"type", "payload"}
    # The substantive claim, and the one the liveness rule cannot make: a reader of a heterogeneous
    # list may only name what every row draws. `job_id` is emitted, so a read of it would be live --
    # on one row out of five, and undefined on the four that follow it.
    assert read_off_a & divergence == set()
    assert read_off_a == consensus, (f"the artifact reader leans on {sorted(read_off_a)} while the rows "
                                     f"agree on {sorted(consensus)}: a name outside the consensus is a "
                                     "field four of the five cards cannot have")
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
    # The scan is not returning an empty list, which is the only way the two rules that consume it
    # (liveness, and the DECLARED reconciliation) could both go green on a broken reader. *Which*
    # sites are dead is stated once, keyed by the reader and the names it probes; the line number is
    # not an identity -- #152 added three comment lines above one of them and a line-keyed copy of
    # that table would have reddened CENSUS for a comment.
    assert len(_dead_read_sites()) == 3
    assert _structural_problems() == []


def test_every_action_kind_the_orchestrator_offers_lands_somewhere():
    """The half of this reader's contract no record can answer for.

    `CHAT_ACTION_ROUTES[kind]` is a read whose key is a variable and whose producer is Python code two
    services away, so `_sites` cannot attribute it and the liveness rule has nothing to say about it.
    What can still be checked is the pair of claims the reader makes: that every kind the orchestrator
    writes has a destination, and that the destination exists in the app. A kind with no route is not
    a broken link but a chip that never renders -- the defect #149 measured on a live page.
    """
    assert _route_problems() == []
    # Positive control on the rule itself, in the same shape as the census above: the table has the
    # five entries the orchestrator writes, so a `kinds != routes` assertion that compared two empty
    # sets would prove nothing.
    assert sorted(_chat_routes()) == sorted(_added_values(*PRODUCERS["ChatActionItem"][1], "kind")) \
        == ["cover_letter", "interview", "open_interview", "open_job", "tailor"]
    assert all(_page_file(route) is not None for route in _chat_routes().values())


def test_every_bar_label_belongs_to_a_dimension_somebody_scores():
    """The other half of #150, and the half no record can answer for.

    `DIMENSION_LABELS[key]` reads a table the browser owns, keyed by a variable, and both of this
    file's dimension readers look a name up in it -- `normalizeDimensions` with the four columns
    `_overall` weights, `normalizeInterviewDims` with whatever ai-service's `DIMENSIONS` list asked
    the model for. Neither lookup is a wire read, so the liveness rule cannot see either one, and a
    table entry no reader can reach is a label that will never render while the file keeps claiming
    the vocabulary. That is the mistake #150 deleted: five entries were reachable only through a
    `dimensions` map no endpoint ever sent.

    Every match dimension still has to be labelled, because the match reader has no fallback left to
    hide a missing entry behind -- it renders `undefined` where a word belongs. The interview names
    are allowed to have no entry, and today have none: that reader splits on `_`, which is copy, not
    contract.
    """
    labels, scored = _dimension_labels(), set(_match_dimensions())
    assert scored and labels and _interview_dimensions(), \
        "an empty side of this rule would satisfy every comparison below it"
    assert scored <= labels, f"a match bar with no label: {sorted(scored - labels)}"
    unreachable = labels - scored - _interview_dimensions()
    assert unreachable == set(), (f"labels no dimension reader can ask for: {sorted(unreachable)} -- "
                                  "either the reader that used them is gone, or the service renamed "
                                  "the dimension and this table is now covering for nothing")


# --------------------------------------------- a tolerated alias whose only author cannot be reached

# `citations` is the name #152 deleted, and it is the shape the per-site rule is structurally blind to:
# it sat beside a live `evidence`/`sources` in three mappers, so every one of those sites stayed live on
# its sibling's strength while the name itself answered nothing the browser can receive. What such a
# name claims is reachability, so that is what gets checked -- against the handler's own return
# statement and against the app's real call sites, not against a sentence written here.
REPLIED_ONLY_BY_UNREACHED_ROUTES = {
    "citations": ("POST", "/internal/rag/answer"),
}


def _browser_names(literal: str) -> list[str]:
    """Every browser source that spells `"literal"` as a string, as `file:line`.

    Deliberately wider than the accessor list: a ban on a name should not hinge on which helper the
    call used, and a false red costs one look at a line. Test files are excluded because #151 and #152
    both keep fixtures that put the forbidden spelling *in* a payload to prove it renders nothing.
    """
    files = [p for p in sorted(list(ROOT_FRONTEND.rglob("*.ts")) + list(ROOT_FRONTEND.rglob("*.tsx")))
             if ".test." not in p.name]
    assert len(files) >= 60, f"the browser scan saw {len(files)} files, not the whole app"
    needle = f'"{literal}"'
    return [f"{p.relative_to(ROOT_FRONTEND.parent)}:{i}"
            for p in files
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if needle in line]


def test_a_key_only_an_unreached_route_answers_is_read_by_nobody():
    """The reachability half of the contract: who answers this name, and can the app ask them?

    Two ends, both read out of code. The producer end is `doc._returned`, which parses the handler's
    own `return` statement in `app/api/rag.py`, so a rename there is caught here rather than
    remembered here. The consumer end is the browser's source. Between them sits the route table the
    #114 gate already derives: if the backend ever starts calling `/internal/rag/answer`, the ban has
    to be retired, and this test is where that becomes loud.
    """
    from tests import test_api_doc_contract as doc  # crosses back; safe at call time

    assert REPLIED_ONLY_BY_UNREACHED_ROUTES, "the ban table was emptied; the rule below proves nothing"
    routes, unreached = doc._routes(), doc.unreached_paths()
    for key, (verb, path) in REPLIED_ONLY_BY_UNREACHED_ROUTES.items():
        assert (verb, path) in routes, (f"{verb} {path} is not served any more, so this ban has no "
                                        "author left to reason about -- delete the entry with the route")
        assert path in unreached, (f"{verb} {path} became reachable, which makes `{key}` a real spelling "
                                   "again: this entry has to go and the mappers need the name back")
        shape = doc._returned(routes[(verb, path)]) or {}
        assert key in shape, (f"{verb} {path} no longer answers `{key}` (it returns {sorted(shape)}), so "
                              "this entry is now asserting a fact the service stopped writing")
        sites = _browser_names(key)
        assert sites == [], (f"`{key}` is answered only by {verb} {path}, which the app never calls, yet "
                             f"the browser still names it at {sites} -- those reads can only ever answer "
                             "undefined, and they hide the shape of the payload they are wrapped around")
    # Positive control on the consumer scan: a name the app really does receive has to be findable,
    # or every assertion above passes on a reader that reads nothing at all.
    seen = _browser_names("evidence")
    assert len(seen) >= 3, f"the browser scan found {seen}; it cannot see the reads it claims to bound"





def _artifact_switch() -> str:
    """The body of `ArtifactCard`'s `switch (artifact.type)`, read out of the component itself.

    A card's vocabulary is browser-owned data keyed by a value from the wire, exactly like the action
    routes and the dimension labels before it, so the names have to come from the source that uses
    them rather than from a list kept here.
    """
    source = (ROOT_FRONTEND / "components" / "copilot" / "artifacts.tsx").read_text(encoding="utf-8")
    body = re.search(r"switch \(artifact\.type\) \{(.*?)\n  \}", source, re.S)
    assert body, "ArtifactCard no longer switches on artifact.type: the claim this rule checks moved"
    return body.group(1)


def test_every_artifact_type_the_card_renders_is_one_the_orchestrator_appends():
    """#145a's other half: which kinds a copilot answer can carry is one list, not two.

    The producer is `_collect_artifacts`, whose five literals each name their own `type`; the consumer
    is the card's switch. Either side drifting is invisible to every per-site rule -- an unrendered
    kind is a message with no card, and a case no producer writes is markup that reads like a feature.
    The one #145a found and deleted was `skill_gap`: a whole renderer, unreachable from any path
    through the orchestrator, while the gaps the product really shows ride the persisted `skillGaps`
    column (#126) into the job page's own panel.
    """
    emitted = _appended_field_values("_collect_artifacts", "out.artifacts", "type")
    body = _artifact_switch()
    rendered = set(re.findall(r'case "([\w-]+)":', body))
    assert emitted and rendered, "both sides have to answer with names for this to mean anything"
    assert len(emitted) == len(set(emitted)), f"two rows append the same type: {sorted(emitted)}"
    assert set(emitted) == rendered, (
        f"the orchestrator appends {sorted(set(emitted) - rendered)}, which no case renders, and the "
        f"card offers {sorted(rendered - set(emitted))}, which no row is ever written with")
    # And an unknown kind is refused rather than rendered as raw JSON: without the default branch,
    # this equality would be the only thing standing between a new type and a blank card.
    assert "default:" in body, ("the switch lost its default branch, so a kind this equality has "
                                "not seen yet would fall through instead of rendering nothing")


def test_the_census_sees_every_read_the_mappers_hold():
    """#162: the scanner every rule above reads through is itself auditable, so it is audited.

    `_sites` finds a call by matching `accessor + (identifier) + ',' + (up to the next ')')`, which
    means the *pattern* decided what counted as a read for the whole gate. Two shapes escaped it, both
    measured over the repository first: a receiver that is an expression instead of an identifier never
    reaches the comma, and a name sitting past an inner `)` is cut off. `normalize.ts` held exactly two
    of the first and none of the second -- `list<string>(profile ?? s, "links")` and
    `num(rows[j], "score", "value")` -- so 250 of the 252 reads were attributed and one name, `links`,
    was read by no rule at all. `ResumeProfile.links` is its producer and the profile card renders it,
    which is why both were fixed in the mapper rather than tolerated here.

    The oracle answers the same question without those assumptions (find the call, pair its
    parentheses, keep it when every argument after the receiver is a bare literal), so agreement is
    evidence about the file, not about one parser echoing another. The last block is the control that
    keeps this from becoming an identity: on a planted expression receiver the census's own finder
    still sees nothing while the oracle names the read. If that ever flips, the two scanners have
    merged and this rule should be deleted rather than left proving equality with itself.
    """
    population = sorted(_mappers_that_read())
    assert len(population) == 32, f"the census population moved: {population}"

    diverged = []
    for name in population:
        oracle = collections.Counter(tuple(site["keys"])
                                      for site in _key_read_calls(_body(name)))
        census = collections.Counter(tuple(site["keys"]) for site in _sites(name))
        if oracle != census:
            diverged.append(f"{name}: oracle-only {sorted(oracle - census)} "
                            f"| census-only {sorted(census - oracle)}")
    assert diverged == [], (f"the census and the oracle disagree about {len(diverged)} of "
                            f"{len(population)} mappers -- each line is a read some rule here "
                            f"cannot see: {diverged}")

    whole = _key_read_calls(NORMALIZE.read_text(encoding="utf-8"))
    # Measured at this plane: the whole file and the sum over its mappers answer 252 each, which is
    # what says no read lives outside a body -- in a module-level table or a top-level statement --
    # where the per-reader floors would never be consulted. The number moves with every read added
    # or removed, so it is a restatement of the two totals below it, not a separate claim.
    assert len(whole) == 252, f"{len(whole)} reads by the oracle: recount both totals if this moved"
    assert len(whole) == sum(len(_sites(name)) for name in population), \
        "a named read lives outside every mapper the census walks"
    expressions = [site for site in whole if not _BARE.fullmatch(site["receiver"])]
    assert expressions == [], (f"reads taken off an expression, invisible to `SITE_RECEIVER`: "
                               f"{[(s['line'], s['name'], s['receiver']) for s in expressions]} -- "
                               "hoist the receiver into a local so a rule can bind it to a producer")

    # The same blind spot measured in the other browser file, which no `_sites` census walks because
    # its readers are bound by the shape gate instead. Counted loosely on purpose: `actions.ts` is
    # owned by a concurrent run, and the claim that matters is the shape, not the total.
    actions = _key_read_calls((ROOT_FRONTEND / "lib" / "hooks" / "actions.ts")
                              .read_text(encoding="utf-8"))
    assert len(actions) >= 20, f"the oracle found {len(actions)} reads in actions.ts: it stopped reading"
    assert [s for s in actions if not _BARE.fullmatch(s["receiver"])] == [], \
        "actions.ts took a read off an expression, which no rule here attributes to a producer"

    plant = 'const links = list<string>(profile ?? s, "plantedName");'
    assert [site["keys"] for site in _key_read_calls(plant)] == [("plantedName",)], \
        "the oracle no longer sees an expression receiver, so the agreement above is self-consistency"
    assert CENSUS_SITE.findall(plant) == [], \
        "the census learned to match an expression receiver; this rule now audits one scanner twice"
    # A third escape hides in the extractor rather than the finder: `_NAME` pulls a name out with double
    # quotes, so these two spellings match `CENSUS_SITE` and then yield no candidates, and `_sites` drops
    # the site. Measured: normalize.ts and actions.ts hold 0 of either today, which is why the rule above
    # is a widening rather than a fix -- and why the oracle, not the census, is the one that has to be wide.
    for hidden, spelled in (("const headline = str(profile, 'plantedHeadline');", "plantedHeadline"),
                            ("const email = str(profile, `plantedEmail`);", "plantedEmail")):
        assert [site["keys"] for site in _key_read_calls(hidden)] == [(spelled,)], \
            f"the oracle is blind to a name outside double quotes again: {hidden}"
        match = CENSUS_SITE.search(hidden)
        assert match is not None and _NAME.findall(match.group(2)) == [], \
            (f"the census now extracts {spelled!r} itself, so this spelling is no longer a divergence "
             "and the agreement above is one scanner reading itself")
