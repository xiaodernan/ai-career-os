"use client";

import { Briefcase, MapPin } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useJobs } from "@/lib/hooks/resources";

export default function JobsPage() {
  const jobs = useJobs();
  return (
    <ModuleView
      title="Jobs"
      description="Discovered and pasted roles — scored against your resume with evidence, not vibes."
      query={jobs}
      emptyHint={{
        title: "The job board is quiet",
        description: "Paste a JD or let the research agent surface roles that fit your target.",
      }}
      renderItem={(job) => (
        <Card key={job.id}>
          <CardContent className="flex flex-wrap items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
              <Briefcase className="size-4.5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{job.title}</p>
              <p className="flex items-center gap-1 truncate text-xs text-muted-foreground">
                {job.company?.name ?? job.companyId}
                {job.location && (
                  <>
                    <span aria-hidden>·</span>
                    <MapPin className="size-3" aria-hidden />
                    {job.location}
                  </>
                )}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {(job.skills ?? []).slice(0, 4).map((s) => (
                <Badge key={s} variant="outline" className="text-2xs">
                  {s}
                </Badge>
              ))}
              <Badge variant={job.status === "open" ? "success" : "secondary"}>{job.status}</Badge>
            </div>
          </CardContent>
        </Card>
      )}
    />
  );
}
