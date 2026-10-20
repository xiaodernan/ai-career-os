"use client";

import * as React from "react";
import { Filter, RotateCcw, Search, X } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";
import { salaryFromInput } from "@/lib/job-filter";
import { useLocale } from "@/lib/i18n/locale-context";
import type { JobFilters as Filters } from "@/lib/hooks/resources";

/**
 * Job filter sidebar. Purely controlled: the page owns the values in the URL so
 * a filtered board is shareable and survives a refresh.
 */
export interface JobFilterPanelProps extends React.ComponentProps<"div"> {
  value: Filters;
  onApply: (next: Filters) => void;
  /** Suggested skill values from the resume profile (undefined until known). */
  skillSuggestions?: string[];
  resultCount?: number;
  loading?: boolean;
}

const EMPTY: Filters = { q: "", skills: "", location: "", remote: undefined, company: "", min_salary: undefined, max_salary: undefined, page: 0 };

function JobFilterPanel({ value, onApply, skillSuggestions, resultCount, loading, className, ...props }: JobFilterPanelProps) {
  const { t } = useLocale();
  const [localQ, setLocalQ] = React.useState(value.q ?? "");
  const skills = React.useMemo(
    () => (value.skills ?? "").split(",").map((s) => s.trim()).filter(Boolean),
    [value.skills]
  );

  // keep the text field in sync when the URL changes (back / palette navigation)
  React.useEffect(() => setLocalQ(value.q ?? ""), [value.q]);

  // debounce the free-text query into the URL
  React.useEffect(() => {
    if (localQ === (value.q ?? "")) return;
    const t = setTimeout(() => onApply({ ...EMPTY, ...value, q: localQ, page: 0 }), 350);
    return () => clearTimeout(t);
  }, [localQ, value, onApply]);

  const set = (patch: Partial<Filters>) => onApply({ ...EMPTY, ...value, ...patch, page: 0 });
  const toggleSkill = (skill: string) => {
    const next = skills.includes(skill) ? skills.filter((s) => s !== skill) : [...skills, skill];
    set({ skills: next.join(",") });
  };
  const activeCount =
    (value.q ? 1 : 0) +
    skills.length +
    (value.location ? 1 : 0) +
    (value.company ? 1 : 0) +
    (value.remote ? 1 : 0) +
    (value.min_salary != null || value.max_salary != null ? 1 : 0);

  return (
    <div className={cn("flex flex-col gap-5", className)} {...props}>
      <div className="flex items-center justify-between">
        <h2 className="flex items-center gap-2 text-sm font-semibold">
          <Filter className="size-3.5 text-muted-foreground" aria-hidden />
          Filters
        </h2>
        {activeCount > 0 && (
          <Button
            variant="ghost"
            size="xs"
            onClick={() => {
              onApply(EMPTY);
              setLocalQ("");
              toast.success("Filters cleared.");
            }}
          >
            <RotateCcw aria-hidden />
            Clear {activeCount}
          </Button>
        )}
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="job-search">Keyword</Label>
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-muted-foreground" aria-hidden />
          <Input
            id="job-search"
            value={localQ}
            onChange={(e) => setLocalQ(e.target.value)}
            placeholder={t("jobs.filters.searchPlaceholder")}
            className="pl-8"
            autoComplete="off"
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="job-location">Location</Label>
        <Input
          id="job-location"
          value={value.location ?? ""}
          onChange={(e) => set({ location: e.target.value })}
          placeholder={t("jobs.filters.locationPlaceholder")}
          autoComplete="off"
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="job-company">Company</Label>
        <Input
          id="job-company"
          value={value.company ?? ""}
          onChange={(e) => set({ company: e.target.value })}
          placeholder={t("jobs.filters.companyPlaceholder")}
          autoComplete="off"
        />
      </div>

      <div className="space-y-2">
        <Label>Skills</Label>
        {skills.length > 0 && (
          <ul className="flex flex-wrap gap-1.5">
            {skills.map((s) => (
              <li key={s}>
                <button
                  type="button"
                  onClick={() => toggleSkill(s)}
                  className="inline-flex items-center gap-1 rounded-full border border-primary/25 bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary hover:bg-primary/20 focus-visible:ring-[3px] focus-visible:ring-primary/30"
                  aria-label={`Remove skill filter ${s}`}
                >
                  {s}
                  <X className="size-3" aria-hidden />
                </button>
              </li>
            ))}
          </ul>
        )}
        {skillSuggestions?.length ? (
          <div className="flex flex-wrap gap-1.5">
            {/* Every suggestion is rendered: these chips are the only way to set the skill
                filter, so a windowed list would leave part of the user's own profile
                unfilterable with nothing to say so. */}
            {skillSuggestions.map((s) => (
              <li key={s} className="list-none">
                <Badge
                  variant="outline"
                  asChild
                  className="cursor-pointer text-2xs font-normal hover:bg-accent"
                >
                  <button type="button" onClick={() => toggleSkill(s)} aria-pressed={skills.includes(s)}>
                    {s}
                  </button>
                </Badge>
              </li>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            Skill suggestions appear once your resume profile is parsed.
          </p>
        )}
      </div>

      <div className="space-y-2">
        <Label>Salary range</Label>
        <div className="flex items-center gap-2">
          <Input
            type="number"
            inputMode="numeric"
            min={0}
            value={value.min_salary ?? ""}
            onChange={(e) => set({ min_salary: salaryFromInput(e.target.value) })}
            placeholder={t("jobs.filters.minSalary")}
            aria-label={t("jobs.filters.minSalaryLabel")}
          />
          <span className="text-muted-foreground" aria-hidden>–</span>
          <Input
            type="number"
            inputMode="numeric"
            min={0}
            value={value.max_salary ?? ""}
            onChange={(e) => set({ max_salary: salaryFromInput(e.target.value) })}
            placeholder={t("jobs.filters.maxSalary")}
            aria-label={t("jobs.filters.maxSalaryLabel")}
          />
        </div>
      </div>

      <div className="flex items-center justify-between gap-3">
        <Label htmlFor="job-remote" className="cursor-pointer">
          Remote only
        </Label>
        <Switch
          id="job-remote"
          checked={Boolean(value.remote)}
          onCheckedChange={(checked) => set({ remote: checked || undefined })}
        />
      </div>

      <Separator />

      <p className="text-xs text-muted-foreground" aria-live="polite">
        {loading ? (
          <span className="shimmer-text">Filtering…</span>
        ) : resultCount != null ? (
          <>
            <span className="font-medium text-foreground tabular-nums">{resultCount}</span> matching{" "}
            {resultCount === 1 ? "role" : "roles"}
          </>
        ) : (
          "Results load from the live search endpoint."
        )}
      </p>
    </div>
  );
}

export { JobFilterPanel };
export const EMPTY_JOB_FILTERS = EMPTY;
