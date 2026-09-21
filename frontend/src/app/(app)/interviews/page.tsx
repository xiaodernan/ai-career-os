"use client";

import { MessageCircle } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useInterviewSessions } from "@/lib/hooks/resources";

export default function InterviewsPage() {
  const sessions = useInterviewSessions();
  return (
    <ModuleView
      title="Interviews"
      description="Adaptive mock interviews: ask → evaluate → follow-up, with per-answer scoring across dimensions."
      query={sessions}
      emptyHint={{
        title: "No interview sessions yet",
        description: "Start one from Copilot with a target role — the interviewer adapts difficulty to your answers.",
      }}
      ctaHref="/copilot"
      ctaLabel="Start with Copilot"
      renderItem={(s) => (
        <Card key={s.id}>
          <CardContent className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <MessageCircle className="size-4.5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium capitalize">{s.mode.replace("_", " ")} interview</p>
              <p className="text-xs text-muted-foreground">
                {s.startedAt ? new Date(s.startedAt).toLocaleString() : "Not started"}
                {typeof s.difficulty === "number" && ` · depth ${s.difficulty.toFixed(1)}`}
              </p>
            </div>
            <Badge
              variant={s.status === "completed" ? "success" : s.status === "active" ? "ai" : "secondary"}
              className="capitalize"
            >
              {s.status}
            </Badge>
          </CardContent>
        </Card>
      )}
    />
  );
}
