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
import { useLocale } from "@/lib/i18n/locale-context";

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
  { key: "gap", label: "Gap analysis", icon: TrendingUp, epic: "10.1" },
  { key: "demand", label: "Market demand", icon: Compass, epic: "10.9" },
  { key: "priority", label: "Learning priority", icon: ListOrdered, epic: "10.12" },
  { key: "plan", label: "Learning plan", icon: BookOpen, epic: "10.5" },
  { key: "prep", label: "Interview prep", icon: MessagesSquare, epic: "10.13" },
  { key: "progression", label: "Progression", icon: Route, epic: "10.11" },
  { key: "stories", label: "Story bank", icon: BookOpen, epic: "6.5" },
  { key: "roles", label: "Role suggestions", icon: Compass, epic: "10.10" },
  { key: "progress", label: "Progress", icon: TrendingUp, epic: "10.6" },
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
              {e.label}
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
            <Label htmlFor="engine-location">Location (optional)</Label>
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
          Run {ENGINES.find((e) => e.key === engine)?.label}
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

/** Each engine's own answer, in its own shape. */
function EngineAnswer({ engine, data }: { engine: EngineKey; data: Record<string, unknown> }) {
  switch (engine) {
    case "gap":
      return (
        <div className="space-y-2">
          <p className="text-sm">
            Coverage {Math.round(Number(data.coverage ?? 0) * 100)}% ·{" "}
            {String(data.coveredCount ?? 0)} covered, {String(data.partialCount ?? 0)} partial,{" "}
            {String(data.expectedSkillCount ?? 0)} expected
          </p>
          <ul className="space-y-1">
            {((data.gaps ?? []) as Array<{ name?: string; importance?: string }>).map((g, i) => (
              <li key={`${g.name}-${i}`} className="flex items-center gap-2 text-sm">
                <Badge variant={g.importance === "must" ? "warning" : "outline"} className="text-2xs">
                  {g.importance ?? "gap"}
                </Badge>
                {g.name}
              </li>
            ))}
          </ul>
        </div>
      );
    case "demand":
      return (
        <ul className="space-y-1">
          {((data.skills ?? []) as Array<{ name?: string; count?: number }>).map((s, i) => (
            <li key={`${s.name}-${i}`} className="flex items-center justify-between text-sm">
              <span>{s.name}</span>
              <span className="tabular-nums text-muted-foreground">{s.count ?? 0}</span>
            </li>
          ))}
        </ul>
      );
    case "priority":
      return (
        <ul className="space-y-1">
          {((data.priorities ?? []) as Array<{ skill?: string; priority?: string; marketDemand?: number }>).map(
            (p, i) => (
              <li key={`${p.skill}-${i}`} className="flex items-center justify-between text-sm">
                <span>{p.skill}</span>
                <span className="text-xs text-muted-foreground">
                  {p.priority} · demand {p.marketDemand ?? 0}
                </span>
              </li>
            )
          )}
        </ul>
      );
    case "plan":
      return (
        <div className="space-y-3">
          {((data.phases ?? []) as Array<{ label?: string; phase?: string; items?: Array<{ topic?: string; priority?: string }> }>).map(
            (phase) => (
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
            )
          )}
        </div>
      );
    case "prep":
      return (
        <div className="space-y-3">
          <div>
            <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Study
            </p>
            <ul className="mt-1 space-y-1">
              {((data.study ?? []) as Array<{ topic?: string }>).map((s, i) => (
                <li key={`${s.topic}-${i}`} className="text-sm">
                  {s.topic}
                </li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
              Rehearse
            </p>
            <ul className="mt-1 space-y-1">
              {((data.rehearse ?? []) as Array<{ topic?: string }>).map((s, i) => (
                <li key={`${s.topic}-${i}`} className="text-sm">
                  {s.topic}
                </li>
              ))}
            </ul>
          </div>
        </div>
      );
    case "progression":
      return (
        <div className="space-y-2">
          <ul className="space-y-1">
            {((data.steps ?? []) as Array<{ role?: string; reachable?: boolean }>).map((s, i) => (
              <li key={`${s.role}-${i}`} className="flex items-center gap-2 text-sm">
                <Badge variant={s.reachable ? "success" : "secondary"} className="text-2xs">
                  {s.reachable ? "reachable" : "gated"}
                </Badge>
                {s.role}
              </li>
            ))}
          </ul>
          {((data.missing ?? []) as string[]).length > 0 && (
            <p className="text-xs text-muted-foreground">
              Missing for the dream role: {((data.missing ?? []) as string[]).join(", ")}.
            </p>
          )}
        </div>
      );
    case "stories":
      return (
        <ul className="space-y-1">
          {((data.stories ?? []) as Array<{ title?: string; evidence?: string }>).map((s, i) => (
            <li key={`${s.title}-${i}`} className="text-sm">
              <span className="font-medium">{s.title}</span>
              {s.evidence && (
                <span className="text-muted-foreground"> — {s.evidence}</span>
              )}
            </li>
          ))}
        </ul>
      );
    case "roles":
      return (
        <ul className="space-y-1">
          {((data.roles ?? []) as Array<{ role?: string; score?: number }>).map((r, i) => (
            <li key={`${r.role}-${i}`} className="flex items-center justify-between text-sm">
              <span>{r.role}</span>
              <span className="tabular-nums text-muted-foreground">
                {Math.round(Number(r.score ?? 0) * 100)}%
              </span>
            </li>
          ))}
        </ul>
      );
    case "progress":
      return (
        <div className="space-y-2">
          <p className="text-sm text-muted-foreground">
            Coverage{" "}
            {Math.round(Number(data.previousCoverage ?? 0) * 100)}% →{" "}
            {Math.round(Number(data.currentCoverage ?? 0) * 100)}%
          </p>
          {(
            [
              ["Closed", data.closed, "text-success"],
              ["Improved", data.improved, "text-primary"],
              ["Regressed", data.regressed, "text-destructive"],
            ] as Array<[string, unknown, string]>
          ).map(([label, list, tone]) => {
            const skills = (list ?? []) as string[];
            if (!skills.length) return null;
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
