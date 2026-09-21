"use client";

import { Building2, Globe } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { useCompanies } from "@/lib/hooks/resources";

export default function CompaniesPage() {
  const companies = useCompanies();
  return (
    <ModuleView
      title="Companies"
      description="Research profiles built from job postings and web sources — external facts always carry their source."
      query={companies}
      emptyHint={{
        title: "No companies researched",
        description: "The research agent builds company profiles when you save a job or ask about one.",
      }}
      ctaHref="/copilot"
      ctaLabel="Research a company"
      renderItem={(c) => (
        <Card key={c.id}>
          <CardContent className="flex items-center gap-3">
            {c.logoUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={c.logoUrl} alt="" className="size-9 rounded-lg border border-border object-contain p-1" />
            ) : (
              <span className="flex size-9 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <Building2 className="size-4.5" aria-hidden />
              </span>
            )}
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{c.name}</p>
              <p className="truncate text-xs text-muted-foreground">
                {[c.industry, c.size].filter(Boolean).join(" · ") || "Profile pending"}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-1.5">
              {(c.techStack ?? []).slice(0, 3).map((t) => (
                <Badge key={t} variant="outline" className="text-2xs">
                  {t}
                </Badge>
              ))}
              {c.website && (
                <a
                  href={c.website}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={`${c.name} website`}
                  className="rounded-md p-1 text-muted-foreground hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring/35"
                >
                  <Globe className="size-4" aria-hidden />
                </a>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    />
  );
}
