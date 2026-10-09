"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { FilePlus2, Sparkles } from "lucide-react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ProcessingSteps, type ProcessingStep } from "@/components/ai/processing-steps";
import { useImportJob } from "@/lib/hooks/actions";
import { ApiError } from "@/lib/api/client";
import { missingEndpointMessage } from "@/lib/api/missing-endpoint";
import { jdTextIssue } from "@/lib/jd-text";

/**
 * Paste a posting into the tracker (vs. AnalyzeJdDialog, which only previews the
 * analysis): one POST runs the JD analyst on the backend and lands the job —
 * company, skills, responsibilities, its own JD row — so on success the caller
 * jumps straight to the new job's page. The posting floor is the same one the
 * analyze dialog asks `@/lib/jd-text` for: below it the analyst returns an empty
 * structure for any posting, however the request was sent.
 */
const STAGES: string[] = [
  "Reading the posting",
  "Extracting the company and role",
  "Filing it in your tracker",
];

/** Local stage hints: the request lifecycle is real, its internal position isn't observable here. */
function stepsFor(pending: boolean, done: boolean): ProcessingStep[] {
  return STAGES.map((label, i) => ({
    id: `import-${i}`,
    label,
    status: done ? "done" : pending ? (i === 0 ? "active" : "pending") : "pending",
  }));
}

export function ImportJobDialog() {
  const [open, setOpen] = React.useState(false);
  const [text, setText] = React.useState("");
  const [url, setUrl] = React.useState("");
  const [done, setDone] = React.useState(false);
  const router = useRouter();
  const importJob = useImportJob();

  React.useEffect(() => {
    if (!open) {
      setText("");
      setUrl("");
      setDone(false);
      importJob.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const issue = jdTextIssue(text);

  const run = () => {
    if (issue) return;
    importJob.mutate(
      { rawText: text.trim(), url: url.trim() || undefined },
      {
        onSuccess: (res) => {
          setDone(true);
          if (res.id) {
            setOpen(false);
            router.push(`/jobs/${res.id}`);
          }
        },
      }
    );
  };

  const error = importJob.error;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <FilePlus2 aria-hidden />
          Paste a posting
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-xl">
        <DialogHeader>
          <DialogTitle className="text-base">Import a job posting</DialogTitle>
          <DialogDescription>
            Paste the full posting. The analyst fills in the company, skills and responsibilities
            and the role lands in your tracker.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-2">
          <Label htmlFor="import-raw">Job posting text</Label>
          <Textarea
            id="import-raw"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste the full posting — responsibilities, requirements, nice-to-haves…"
            rows={8}
            className="font-mono text-xs"
          />
          <p className="text-xs text-muted-foreground">
            {text.trim().length} characters ·{" "}
            {issue ?? "nothing is sent until you import."}
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="import-url">Source URL (optional)</Label>
          <Input
            id="import-url"
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://example.com/careers/123"
          />
        </div>

        {(importJob.isPending || done) && (
          <div className="rounded-lg border border-border/70 bg-muted/30 p-3">
            <ProcessingSteps steps={stepsFor(importJob.isPending, done)} />
          </div>
        )}

        {error != null && (
          <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            {error instanceof ApiError && error.isNotFound
              ? missingEndpointMessage("POST /jobs/import")
              : error instanceof Error
                ? error.message
                : "Import failed."}
          </div>
        )}

        <DialogFooter>
          <Button variant="ai" onClick={run} loading={importJob.isPending} disabled={issue !== undefined}>
            <Sparkles aria-hidden />
            Import
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
