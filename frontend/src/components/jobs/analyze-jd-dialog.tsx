"use client";

import * as React from "react";
import { ClipboardPaste, Sparkles } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { ProcessingSteps, type ProcessingStep } from "@/components/ai/processing-steps";
import { AIBadge } from "@/components/ai/ai-badge";
import { useAnalyzeJd, useResumeSuggestions, type JdAnalysis } from "@/lib/hooks/actions";
import { missingSkillGaps } from "@/lib/api/normalize";
import type { Suggestion } from "@/lib/api/types";
import { ApiError } from "@/lib/api/client";
import { missingEndpointMessage } from "@/lib/api/missing-endpoint";
import { jdTextIssue } from "@/lib/jd-text";

/**
 * JD intelligence (§9): paste raw text → required / preferred skills,
 * responsibilities, interview topics, skill gap, resume suggestions.
 * Progress is described by the request lifecycle, not invented timings.
 */
const STAGES: string[] = [
  "Reading the posting",
  "Extracting requirements",
  "Ranking priorities",
  "Comparing with your profile",
];

/** Local stage hints: the request lifecycle is real, its internal position isn't observable here. */
function stepsFor(pending: boolean, hasResult: boolean): ProcessingStep[] {
  return STAGES.map((label, i) => ({
    id: `jd-${i}`,
    label,
    status: hasResult ? "done" : pending ? (i === 0 ? "active" : "pending") : "pending",
  }));
}

export function AnalyzeJdDialog({ onUseText }: { onUseText?: (text: string) => void }) {
  const [open, setOpen] = React.useState(false);
  const [text, setText] = React.useState("");
  const [result, setResult] = React.useState<JdAnalysis | null>(null);
  const analyze = useAnalyzeJd();
  const suggest = useResumeSuggestions();

  React.useEffect(() => {
    if (!open) {
      setResult(null);
      analyze.reset();
      suggest.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const issue = jdTextIssue(text);

  const run = () => {
    if (issue) return;
    const value = text.trim();
    analyze.mutate(value, {
      onSuccess: (res) => {
        setResult(res);
        // /jds never returns suggestions; compare against the parsed resume via /jds/suggestions.
        suggest.mutate({ jdRaw: value });
      },
    });
  };

  const error = analyze.error;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <ClipboardPaste aria-hidden />
          Analyze a JD
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-base">JD intelligence</DialogTitle>
          <DialogDescription>
            Paste a job description. The JD analyst extracts requirements, priorities and the gap
            against your parsed resume.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <Label htmlFor="jd-raw">Job description text</Label>
          <Textarea
            id="jd-raw"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste the full posting — responsibilities, requirements, nice-to-haves…"
            rows={8}
            className="font-mono text-xs"
          />
          <p className="text-xs text-muted-foreground">
            {text.trim().length} characters ·{" "}
            {issue ?? "nothing is sent until you run the analysis."}
          </p>
        </div>

        {(analyze.isPending || result) && (
          <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
            {analyze.isPending && !result && (
              <ProcessingSteps steps={stepsFor(true, false)} />
            )}
            {result && (
              <div className="space-y-4">
                <ProcessingSteps steps={stepsFor(false, true)} className="mb-4" />
                <JdResult
                  result={result}
                  suggestions={suggest.data?.suggestions ?? []}
                  loading={suggest.isPending}
                />
              </div>
            )}
          </div>
        )}

        {error != null && (
          <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            {error instanceof ApiError && error.isNotFound
              ? missingEndpointMessage("POST /jds")
              : error instanceof Error
                ? error.message
                : "Analysis failed."}
          </div>
        )}

        <DialogFooter className="gap-2">
          {onUseText && result && (
            <Button variant="ghost" size="sm" onClick={() => onUseText(text)}>
              Keep this text
            </Button>
          )}
          <Button variant="ai" onClick={run} loading={analyze.isPending} disabled={issue !== undefined}>
            <Sparkles aria-hidden />
            Analyze
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function JdResult({
  result,
  suggestions,
  loading,
}: {
  result: JdAnalysis;
  suggestions: Suggestion[];
  loading?: boolean;
}) {
  // A gap is a comparison against this resume, so the analysis itself never carries one: the card is
  // built from the missing-required items /jds/suggestions derived (the contract gate checks that).
  const gap = missingSkillGaps(suggestions);
  const groups: { title: string; items: string[]; variant?: "ai" | "outline" | "warning" }[] = [
    { title: "Required skills", items: result.requiredSkills, variant: "ai" },
    { title: "Preferred skills", items: result.preferredSkills },
    { title: "Hidden requirements", items: result.hiddenRequirements, variant: "warning" },
    { title: "Interview topics", items: result.interviewTopics },
    { title: "Your skill gap", items: gap, variant: "warning" },
  ];
  const visible = groups.filter((g) => g.items.length > 0);
  const nothing =
    !visible.length && !result.responsibilities.length && !suggestions.length && !loading;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <AIBadge label="JD analysis" />
        <span className="text-xs text-muted-foreground">Structured output from /jds</span>
      </div>

      {result.responsibilities.length > 0 && (
        <section className="space-y-1.5">
          <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Responsibilities
          </h4>
          <ul className="ml-4 list-disc space-y-1 text-sm">
            {result.responsibilities.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </section>
      )}

      {visible.map((g) => (
        <section key={g.title} className="space-y-1.5">
          <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">{g.title}</h4>
          <ul className="flex flex-wrap gap-1.5">
            {g.items.map((item, i) => (
              <li key={`${item}-${i}`}>
                <Badge variant={g.variant ?? "outline"} className="font-normal">
                  {item}
                </Badge>
              </li>
            ))}
          </ul>
        </section>
      ))}

      {(suggestions.length > 0 || loading) && (
        <section className="space-y-2">
          <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
            Resume improvement suggestions
          </h4>
          {loading && !suggestions.length && (
            <p className="text-sm text-muted-foreground">Comparing with your resume…</p>
          )}
          <ul className="space-y-2">
            {suggestions.slice(0, 8).map((s, i) => (
              <li key={i} className="rounded-lg border border-border/70 bg-card p-3 text-sm">
                {s.title && <p className="font-medium">{s.title}</p>}
                <p className="text-muted-foreground">{s.text ?? s.body}</p>
              </li>
            ))}
          </ul>
        </section>
      )}

      {nothing && (
        <p className="text-sm text-muted-foreground">
          The analysis came back without structured fields. That usually means the posting text was
          too short — paste the full description and run it again.
        </p>
      )}
    </div>
  );
}
