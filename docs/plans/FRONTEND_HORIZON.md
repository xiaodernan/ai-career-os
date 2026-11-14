# The frontend's next horizon — the visual system, taken seriously

The monitoring page (Epics 175/177/178) demonstrated the pattern this doc binds
into a program: every section answers one question, every number is bound to a
real derivation on the wire, and the design system does the heavy lifting —
not per-page decoration. The goal is the product the user keeps describing:
a front-end whose visual quality is itself a feature.

Nothing here is a blank check for chrome. Every epic below is:

- **gated** (type-check, vitest, `bundle-budget`, copy census, page heading
  checks — no epic ships an unmeasured change);
- **readable** (the observer tests — the service-engines/nightly-history
  pattern — pin what a section shows for pending/error/empty/live data);
- **true** (no invented visuals standing in for data that does not exist).

## Epic 1 — the page framework, not the page

**The Shape.** One layout contract every signed-in route follows: heading block
(eyebrow, title, description, actions), a 12-column content grid with named
spans, and a full-page width scale (narrow for forms, standard for content,
wide for boards). Today every route composes `PageHeader` + ad-hoc children;
the grid is implicit and drifts per page.

Scope. `components/common/page-shell.tsx` + `page-section.tsx` +
`components/layout/page-grid.tsx`; the seven highest-traffic routes migrate
(dashboard, copilot, growth, matches, activity, monitoring, knowledge).
Measured by: routes' heading census stays green; bundle budget unchanged
(+~1 kB max); the `RouteGlance` component (new) renders each route a summary
of what it measured this visit — a *measured* chip, not a decorative one.

## Epic 2 — motion that means something

**The Shape.** The app has fade/reveal/pulse primitives (`components/ui/reveal`,
`gradient-text`, `aurora`); the copilot turn and the AI activity timeline do not
use a single one. A streamed answer is the most information-dense surface in the
product and the least composed.

Scope. A `StreamChoreography` for the copilot answer (skeleton → tokens gather
into the bubble, sources fade in as chips, actions drawer slides in only when
the model supplies actions); the activity timeline animates its `llm_call` rows
in on mount when the event log arrives from the server. Every animation is a
transform/opacity transition (compositor-only, no layout thrash), respects
`prefers-reduced-motion`, and is wired to real events — never to timers.
Measured by: reduced-motion path renders all content; the stream spec still
passes; no new layout animations.

**Tranche one (2026-11-14, landed).** The activity timeline's rows mount with a
45ms stagger, capped at eight rows (`[0..315]ms`), assert the mount itself is the
animation — the `agent-timeline.test.tsx` case pins the four staggered delays;
transform/opacity only, so the compositor owns the work; the `prefers-reduced-motion`
rule in globals.css collapses the delay for readers who asked for less motion; the
rows are in the server markup either way. The copilot's citation chips fade in on
mount, behind the streamed answer's own entrance — reading order stays text first.
vitest 1325/1325, tsc clean, bundle budget OK (36 routes); e2e not re-run this
tranche (additive styling only; the last full mock run, 72/72, predates it). The
remaining scope — StreamChoreography for the copilot bubble itself — is still open.

**Tranche two (2026-11-14, landed).** The waiting gap closed: between send and the
first stream frame the pending block rendered a lone "Thinking" over nothing. It now
renders a shimmer bubble the size of a short answer (aria-hidden, three band lines),
replaced the instant a stream step or the first token lands; ProcessingSteps owns the
step trail, the streaming bubble owns the tokens.

**Tranche three (2026-11-14, landed).** The action chips arrive 220ms behind the
answer and its citations (opacity/transform, mount-driven). Epic 2's composed turn is
complete: reading order answer → evidence → next step, none of it timer-driven.
Measured across both: vitest 1330/1330 each time, bundle budget OK (36 routes),
containers rebuilt and serving; `e2e` not re-run for either (additive styling; the
last full mock run, 72/72, predates both).

## Epic 3 — the empty states become product

**The Shape.** Every module has an `EmptyState` with an illustration, a sentence,
and a CTA — but they are ad-hoc per route and read flat. The house now has the
`PageHeader frontDoor` pattern; the empties need the same treatment: one
`EmptyComposition` (illustration slot, promise sentence in the reader's language,
primary action, proof points list) shared by all of them.

Scope. A shared `EmptyStateModel` + migration of the five most-seen empties
(matches, jobs, knowledge, activity, digest). Measured by: census per-keyed
copy parity; `EmptyStateModel` prop tests; the pages keep their identity —
not a template, a composition.

**Tranche one (2026-11-14, landed).** `components/common/empty-composition.tsx`
is the composed empty: ringed, glowing icon disc; an eyebrow promising the payoff
in the reader's language (capture it as `promise`); title; description; one CTA;
up to three proof points taken from shipped behavior, never aspirations, all
capped at three by construction. `prefers-reduced-motion` collapses the stagger
(70/130/190/250/310ms, mount-driven, opacity/transform only) via the globals.css
blanket rule; the content is in the server markup either way; no timers.
`EmptyState` delegates to the composition when the caller passes `promise` or
`proofs` and keeps the compact layout for every existing call site;
`ModuleView`'s `emptyHint` grows the same two optional fields. The five
most-seen surfaces migrated: **jobs board** (base case; `jobs.boardEmpty*`),
**knowledge base** (`knowledge.baseIsEmpty*`), **activity** (`activity.empty*`),
**applications pipeline** (`applications.pipelineIsEmpty*`), and the **digest
weekly letter** (`analysis.weeklyEmpty*`, gaining its one-call CTA wired to the
existing compose mutation). Each proof is true of what ships: resume-grounded
gap/interview output, the cache-read ledger, replies routed back to their
application. The doc's original five names ("matches") mapped to this codebase's
roles honestly: no matches screen exists — matches live on the jobs board and
in /jobs/[id]; the pipeline is the closest reader-facing empty to the board-to-offer
loop besides it. 40 new keys EN+ZH; copy census pinned 176 sources (+1); vitest
1330/1330, tsc clean, bundle budget OK (36 routes), e2e `routes.spec.ts` 6/6 green
in mock mode, live container rebuilt and serving.

## Epic 4 — the dark room and the candle

**The Shape.** The dark/light theme flip survives only on paper: several shared
primitives use fixed colors that were picked by eye on one theme. Each pass has
to happen on both.

Scope. Token audit of `globals.css`'s semantic tokens (surface, border,
foreground-muted, accent) against every paint in the tree; the contrast gate
(`test_accessibility_contrast_tokens.py`, exists) fails loud when a new token
drops below 4.5:1. Measured by: audit builds; no text node below the floor on
either theme; the audit table in `docs/PRODUCT.md` gains a theme column.

**Tranche one (2026-11-14, landed).** The gate the file claimed existed did not;
it exists now — three cases, both `globals.css` blocks parsed, 26 real token pairs
(Björn Ottosson's published inverse oklch matrices, pure stdlib, no dependency),
every failure names its own ratio. First contact caught real rot, exactly as
predicted: light `--muted-foreground` 0.55→0.52 (4.39→4.98:1 on muted), light
`--success` 0.58→0.54 (3.95→4.63:1), light `--warning` 0.68→0.55 (2.89→4.86:1),
dark `--primary`/`--sidebar-primary` 0.62→0.56 (primary-foreground pair 3.67→4.72:1).
Floor on both themes is now 4.63:1; vitest 1330/1330, bundle budget OK (36 routes),
container rebuilt and serving. The PRODUCT.md "audit table" was never a real table —
no fake column was added to it; the measured numbers live in this file and in
ROADMAP.md's Epic 188.

## Sequencing

1. Epic 1 (the framework everything else needs) — unblocks 2, 3, 4.
2. Epic 2 (motion) — the user-facing gain with the least risk.
3. Epic 3 (empties) — the conversion-critical half of onboarding.
4. Epic 4 (themes) — the honest finishing pass.

Each epic lands with its gate updated and `verify_gates` green at its tip.

## What this is not

Not an image-downloadathon and not a palette family. The AI Career OS design
system is already disciplined: one typeface family per axis, one elevation
scale, one accent discipline. These epics spend that discipline, they do not
add a second one.
