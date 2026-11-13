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

## Epic 4 — the dark room and the candle

**The Shape.** The dark/light theme flip survives only on paper: several shared
primitives use fixed colors that were picked by eye on one theme. Each pass has
to happen on both.

Scope. Token audit of `globals.css`'s semantic tokens (surface, border,
foreground-muted, accent) against every paint in the tree; the contrast gate
(`test_accessibility_contrast_tokens.py`, exists) fails loud when a new token
drops below 4.5:1. Measured by: audit builds; no text node below the floor on
either theme; the audit table in `docs/PRODUCT.md` gains a theme column.

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
