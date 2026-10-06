"use client";

import * as React from "react";
import { Save } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useProfile, useUpdateProfileDetails } from "@/lib/hooks/actions";

/**
 * The career-profile editor for the settings page. `GET/PATCH /users/me/profile` have been served
 * since the start and the two hooks existed without a caller — this card is the screen that
 * finally reads and writes them, so the `["profile"]` invalidation in `useUpdateProfile`'s
 * success path lands on a mounted query too.
 *
 * `UpdateProfileRequest` validates headline ≤ 240, summary ≤ 5000, location ≤ 120,
 * yearsExperience 0–60, and both target lists at 20 entries of 80/120 chars. The PATCH is
 * "null leaves the field alone", so the form sends the fields it edits and never the maps
 * (links, workAuthorization, preferences) it has no UI for.
 */

const MAX_HEADLINE = 240;
const MAX_LOCATION = 120;
const MAX_SUMMARY = 5000;
const MAX_YEARS = 60;

/** `"a, b, c"` -> `["a","b","c"]`, trimmed, blanks dropped — the shape `@Size(max = 20)` guards. */
function splitList(raw: string): string[] {
  return raw.split(",").map((part) => part.trim()).filter(Boolean);
}

function listText(value: unknown): string {
  return Array.isArray(value) ? value.map(String).join(", ") : "";
}

function readString(source: Record<string, unknown> | null, key: string): string {
  const v = source?.[key];
  return typeof v === "string" ? v : "";
}

function readYears(source: Record<string, unknown> | null): string {
  const v = source?.["yearsExperience"];
  return typeof v === "number" ? String(v) : "";
}

export function CareerProfileCard() {
  const profile = useProfile();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Career profile</CardTitle>
        <CardDescription>
          What the agents assume about you — headline, targets and the story they tell recruiters.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {profile.isPending ? (
          <div className="space-y-3">
            <Skeleton className="h-4 w-1/3" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : profile.isError ? (
          <p className="text-sm text-muted-foreground">Profile could not be loaded.</p>
        ) : (
          <CareerProfileForm initial={(profile.data ?? null) as Record<string, unknown> | null} />
        )}
      </CardContent>
    </Card>
  );
}

function CareerProfileForm({ initial }: { initial: Record<string, unknown> | null }) {
  const update = useUpdateProfileDetails();
  const [headline, setHeadline] = React.useState(readString(initial, "headline"));
  const [location, setLocation] = React.useState(readString(initial, "location"));
  const [years, setYears] = React.useState(readYears(initial));
  const [summary, setSummary] = React.useState(readString(initial, "summary"));
  const [roles, setRoles] = React.useState(listText(initial?.["targetRoles"]));
  const [targetLocations, setTargetLocations] = React.useState(listText(initial?.["targetLocations"]));

  // An empty field means "leave it alone" server-side; anything else has to land in 0–60.
  const parsedYears = years.trim() === "" ? null : Number(years.trim());
  const yearsValid =
    parsedYears === null ||
    (Number.isFinite(parsedYears) && parsedYears >= 0 && parsedYears <= MAX_YEARS);
  const saveable = yearsValid;

  const save = React.useCallback(() => {
    if (!saveable || update.isPending) return;
    update.mutate({
      headline: headline.trim(),
      location: location.trim(),
      summary,
      yearsExperience: parsedYears,
      targetRoles: splitList(roles),
      targetLocations: splitList(targetLocations),
    });
  }, [headline, location, parsedYears, roles, saveable, summary, targetLocations, update, yearsValid]);

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="profile-headline">Headline</Label>
        <Input
          id="profile-headline"
          value={headline}
          maxLength={MAX_HEADLINE}
          onChange={(e) => setHeadline(e.target.value)}
          placeholder="e.g. Backend engineer moving into platform work"
          autoComplete="off"
        />
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="profile-location">Location</Label>
          <Input
            id="profile-location"
            value={location}
            maxLength={MAX_LOCATION}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. Hangzhou"
            autoComplete="off"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="profile-years">Years of experience (0–{MAX_YEARS})</Label>
          <Input
            id="profile-years"
            value={years}
            inputMode="decimal"
            onChange={(e) => setYears(e.target.value)}
            placeholder="e.g. 6"
            autoComplete="off"
            aria-invalid={!yearsValid}
          />
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="profile-roles">Target roles (comma separated)</Label>
          <Input
            id="profile-roles"
            value={roles}
            onChange={(e) => setRoles(e.target.value)}
            placeholder="e.g. Platform engineer, Staff engineer"
            autoComplete="off"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="profile-target-locations">Target locations (comma separated)</Label>
          <Input
            id="profile-target-locations"
            value={targetLocations}
            onChange={(e) => setTargetLocations(e.target.value)}
            placeholder="e.g. Hangzhou, Remote"
            autoComplete="off"
          />
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="profile-summary">Summary</Label>
        <Textarea
          id="profile-summary"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={4}
          placeholder="The short story a recruiter gets before the resume."
        />
      </div>
      {!yearsValid && (
        <p role="alert" className="text-xs text-destructive">
          Years of experience has to be a number between 0 and {MAX_YEARS}, or left blank.
        </p>
      )}
      <div className="flex justify-end">
        <Button variant="ai" size="sm" loading={update.isPending} disabled={!saveable || update.isPending} onClick={save}>
          <Save aria-hidden />
          Save profile
        </Button>
      </div>
    </div>
  );
}
