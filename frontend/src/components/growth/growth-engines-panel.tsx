"use client";

import * as React from "react";
import {
  BookOpen,
  Compass,
  ListOrdered,
  MessagesSquare,
  Route,
  TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState } from "@/components/common/empty-state";
import {
  useGapAnalysis,
  useInterviewPrep,
  useLearningPlan,
  useLearningPriority,
  useProgression,
  useRoleSuggestions,
  useSkillDemand,
  useSkillProgress,
  useStoryBank,
} from "@/lib/hooks/growth";
import type {
  GapReport,
  InterviewPrep,
  LearningPlan,
  LearningPriority,
  ProgressionPlan,
  RoleSuggestions,
  SkillDemand,
  SkillProgress,
  StoryBank,
} from "@/lib/api/types";
import { useLocale } from "@/lib/i18n/locale-context";
import { growthEngineLabel } from "@/lib/growth-engines";

/**
 * The granular growth engines, one at a time (10.1-10.13).
 *
 * The `/growth` page reads the 10.2 aggregate in one call; this panel asks the
 * same engines one at a time, so a card that only wants the learning priority
 * does not have to run the whole report to get it.
 *
 * Every answer is a deterministic read of the candidate's own resume and the
 * seeded corpus — the panel never states a fact the engine did not.
 */

const ENGINES = [
  { key: "gap", icon: TrendingUp },
  { key: "demand", icon: Compass },
  { key: "priority", icon: ListOrdered },
  { key: "plan", icon: BookOpen },
  { key: "prep", icon: MessagesSquare },
  { key: "progression", icon: Route },
  { key: "stories", icon: BookOpen },
  { key: "roles", icon: Compass },
  { key: "progress", icon: TrendingUp },
] as const;

type EngineKey = (typeof ENGINES)[number]["key"];

export function GrowthEnginesPanel() {
  const { t } = useLocale();
  const [role, setRole] = React.useState("");
  const [location, setLocation] = React.useState("");
  const [engine, setEngine] = React.useState<EngineKey>("gap");

  const gap = useGapAnalysis();
  const demand = useSkillDemand();
  const priority = useLearningPriority();
  const plan = useLearningPlan();
  const prep = useInterviewPrep();
  const progression = useProgression();
  const stories = useStoryBank();
  const roles = useRoleSuggestions();
  const progress = useSkillProgress();

  const roleOk = role.trim().length >= 10;
  const pending =
    gap.isPending ||
    demand.isPending ||
    priority.isPending ||
    plan.isPending ||
    prep.isPending ||
    progression.isPending ||
    stories.isPending ||
    roles.isPending ||
    progress.isPending;

  const run = React.useCallback(() => {
    const common = {
      targetRole: role.trim(),
      location: location.trim() || undefined,
    };
    switch (engine) {
      case "gap":
        gap.mutate(common);
        break;
      case "demand":
        demand.mutate(common);
        break;
      case "priority":
        priority.mutate(common);
        break;
      case "plan":
        plan.mutate(common);
        break;
      case "prep":
        prep.mutate(common);
        break;
      case "progression":
        progression.mutate(common);
        break;
      case "stories":
        stories.mutate({});
        break;
      case "roles":
        roles.mutate({});
        break;
      case "progress":
        progress.mutate({ targetRole: role.trim() });
        break;
    }
  }, [engine, role, location, gap, demand, priority, plan, prep, progression, stories, roles, progress]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("growthEngines.title")}</CardTitle>
        <CardDescription>{t("growthEngines.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-1.5">
          {ENGINES.map((e) => (
            <Button
              key={e.key}
              type="button"
              size="xs"
              variant={engine === e.key ? "ai" : "outline"}
              onClick={() => setEngine(e.key)}
              aria-pressed={engine === e.key}
            >
              <e.icon aria-hidden />
              {growthEngineLabel(t, e.key)}
            </Button>
          ))}
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="engine-role">{t("growthEngines.targetRole")}</Label>
            <Input
              id="engine-role"
              value={role}
              onChange={(e) => setRole(e.target.value)}
              placeholder="e.g. Senior Backend Engineer (Java)"
              autoComplete="off"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="engine-location">{t("growthEngines.locationOptional")}</Label>
            <Input
              id="engine-location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="e.g. Shanghai"
              autoComplete="off"
            />
          </div>
        </div>

        <Button
          variant="ai"
          size="sm"
          loading={pending}
          disabled={!roleOk && engine !== "stories" && engine !== "roles"}
          onClick={run}
        >
          {t("growthEngines.run")} {growthEngineLabel(t, engine)}
        </Button>

        <EngineResult engine={engine} state={resultFor(engine, {
          gap, demand, priority, plan, prep, progression, stories, roles, progress,
        })} />
      </CardContent>
    </Card>
  );
}

/** The mutation whose answer the chosen engine renders. */
function resultFor(
  engine: EngineKey,
  states: {
    gap: ReturnType<typeof useGapAnalysis>;
    demand: ReturnType<typeof useSkillDemand>;
    priority: ReturnType<typeof useLearningPriority>;
    plan: ReturnType<typeof useLearningPlan>;
    prep: ReturnType<typeof useInterviewPrep>;
    progression: ReturnType<typeof useProgression>;
    stories: ReturnType<typeof useStoryBank>;
    roles: ReturnType<typeof useRoleSuggestions>;
    progress: ReturnType<typeof useSkillProgress>;
  }
): { data: unknown; isPending: boolean; isError: boolean; error: unknown } {
  const s = states[engine];
  return { data: s.data, isPending: s.isPending, isError: s.isError, error: s.error };
}

function EngineResult({
  engine,
  state,
}: {
  engine: EngineKey;
  state: { data: unknown; isPending: boolean; isError: boolean; error: unknown };
}) {
  const { t } = useLocale();
  if (state.isPending) {
    return <p className="text-sm text-muted-foreground">{t("growthEngines.inFlight")}</p>;
  }
  if (state.isError) {
    return <p className="text-sm text-destructive">{t("growthEngines.failed")}</p>;
  }
  if (!state.data) {
    return (
      <EmptyState
        className="py-4"
        title={t("growthEngines.noAnswer")}
        description={t("growthEngines.noAnswerDescription")}
      />
    );
  }
  return <EngineAnswer engine={engine} data={state.data as Record<string, unknown>} />;
}

/**
 * Each engine's own answer, in its own shape.
 *
 * The names read here are the engines' -- the bridge passes their JSON through
 * without renaming a key, and nothing normalizes it on this side, so a field
 * spelled differently here is a row that silently renders empty while the
 * engine answered it fine. `types.ts` declares these shapes once; the cases
 * below read through those types so a rename trips the compiler and the gate.
 */
function EngineAnswer({ engine, data }: { engine: EngineKey; data: Record<string, unknown> }) {
  const { t } = useLocale();
  switch (engine) {
    case "gap": {
      const report = data as GapReport;
      return (
        <div className="space-y-2">
          <p className="text-sm">
            {t("growthEngines.coverage")} {Math.round((report.coverage ?? 0) * 100)}% ·{" "}
            {report.coveredCount ?? 0} {t("growthEngines.covered")},{" "}
            {report.partialCount ?? 0} {t("growthEngines.partial")},{" "}
            {report.expectedSkillCount ?? 0} {t("growthEngines.expected")}
          </p>
          <ul className="space-y-1">
            {(report.gaps ?? []).map((g, i) => (
              <li key={`${g.skill}-${i}`} className="flex items-center gap-2 text-sm">
                <Badge variant={g.importance === "must" ? "warning" : "outline"} className="text-2xs">
                  {g.importance ?? "gap"}
                </Badge>
                {g.skill}
              </li>
            ))}
          </ul>
        </div>
      );
    }
    case "demand": {
      const demand = data as SkillDemand;
      return (
        <ul className="space-y-1">
          {(demand.skills ?? []).map((s, i) => (
            <li key={`${s.skill}-${i}`} className="flex items-center justify-between text-sm">
              <span>{s.skill}</span>
              <span className="tabular-nums text-muted-foreground">{s.count ?? 0}</span>
            </li>
          ))}
        </ul>
      );
    }
    case "priority": {
      const priority = data as LearningPriority;
      return (
        <ul className="space-y-1">
          {(priority.prioritizedGaps ?? []).map((p, i) => (
            <li key={`${p.skill}-${i}`} className="flex items-center justify-between text-sm">
              <span>{p.skill}</span>
              <span className="text-xs text-muted-foreground">
                {p.priority} · demand {Math.round((p.marketShare ?? 0) * 100)}%
              </span>
            </li>
          ))}
        </ul>
      );
    }
    case "plan": {
      // The route answers {plan, gap}: the phases live inside the plan block.
      const plan = (data as LearningPlan).plan;
      return (
        <div className="space-y-3">
          {(plan?.phases ?? []).map((phase) => (
            <div key={phase.phase ?? phase.label}>
              <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                {phase.label ?? phase.phase}
              </p>
              <ul className="mt-1 space-y-1">
                {(phase.items ?? []).map((item, i) => (
                  <li key={`${item.topic}-${i}`} className="text-sm">
                    {item.topic}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      );
    }
    case "prep": {
      // "study" is the role's gaps, "rehearse" is the covered skills that already
      // carry a story -- the two lists the engine splits the checklist into.
      const prep = data as InterviewPrep;
      return (
        <div className="space-y-3">
          <div>
            <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              {t("growthEngines.study")}
            </p>
            <ul className="mt-1 space-y-1">
              {(prep.weakAreas ?? []).map((a, i) => (
                <li key={`${a.skill}-${i}`} className="text-sm">
                  {a.skill}
                  {a.action && <span className="text-xs text-muted-foreground"> — {a.action}</span>}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              {t("growthEngines.rehearse")}
            </p>
            <ul className="mt-1 space-y-1">
              {(prep.strengthStories ?? []).map((s, i) => (
                <li key={`${s.skill}-${i}`} className="text-sm">
                  {s.skill}
                  {s.storyTitle && (
                    <span className="text-xs text-muted-foreground"> — {s.storyTitle}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      );
    }
    case "progression": {
      const plan = data as ProgressionPlan;
      return (
        <div className="space-y-2">
          <ul className="space-y-1">
            {(plan.steppingStones ?? []).map((s, i) => (
              <li key={`${s.family}-${i}`} className="text-sm">
                {s.family}
                {s.reason && <span className="text-xs text-muted-foreground"> — {s.reason}</span>}
              </li>
            ))}
          </ul>
          {(plan.aspirationalMustGaps ?? []).length > 0 && (
            <p className="text-xs text-muted-foreground">
              {t("growthEngines.missingForDreamRole")}{" "}
              {(plan.aspirationalMustGaps ?? []).join(", ")}.
            </p>
          )}
        </div>
      );
    }
    case "stories": {
      const bank = data as StoryBank;
      return (
        <ul className="space-y-1">
          {(bank.stories ?? []).map((s, i) => (
            <li key={`${s.title}-${i}`} className="text-sm">
              <span className="font-medium">{s.title}</span>
              {(s.bullets ?? [])[0] && (
                <span className="text-muted-foreground"> — {(s.bullets ?? [])[0]}</span>
              )}
            </li>
          ))}
        </ul>
      );
    }
    case "roles": {
      const suggestions = data as RoleSuggestions;
      return (
        <ul className="space-y-1">
          {(suggestions.families ?? []).map((r, i) => (
            <li key={`${r.family}-${i}`} className="flex items-center justify-between text-sm">
              <span>{r.family}</span>
              <span className="tabular-nums text-muted-foreground">
                {Math.round((r.coverage ?? 0) * 100)}%
              </span>
            </li>
          ))}
        </ul>
      );
    }
    case "progress": {
      const progress = data as SkillProgress;
      return (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            {t("growthEngines.coverage")} {Math.round((progress.previousCoverage ?? 0) * 100)}% →{" "}
            {Math.round((progress.currentCoverage ?? 0) * 100)}%
          </p>
          {(
            [
              ["Closed", progress.closed, "text-success"],
              ["Improved", progress.improved, "text-primary"],
              ["Regressed", progress.regressed, "text-destructive"],
            ] as Array<[string, string[] | undefined, string]>
          ).map(([label, skills, tone]) => {
            if (!skills?.length) return null;
            return (
              <div key={label}>
                <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                  {label}
                </p>
                <ul className="mt-1 space-y-1">
                  {skills.map((s) => (
                    <li key={s} className={`text-sm ${tone}`}>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      );
    }
  }
}
