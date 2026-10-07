"use client";

import * as React from "react";
import { Plus, Save, X } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useProfile, useUpdateProfileDetails } from "@/lib/hooks/actions";
import { splitList, targetLocationsIssue, targetRolesIssue } from "@/lib/profile-targets";

/**
 * The career-profile editor for the settings page. `GET/PATCH /users/me/profile` have been served
 * since the start and the two hooks existed without a caller — this card is the screen that
 * finally reads and writes them, so the `["profile"]` invalidation in `useUpdateProfile`'s
 * success path lands on a mounted query too.
 *
 * `UpdateProfileRequest` validates headline ≤ 240, summary ≤ 5000, location ≤ 120,
 * yearsExperience 0–60, and both target lists at 20 entries of 80/120 chars — the lists are
 * guarded on this screen through `profile-targets.ts`, not by clipping a paste. The PATCH is
 * "null leaves the field alone", so each card sends only the fields it edits — the free-form
 * maps get their own editor below (`CareerProfileMapsCard`), which replaces them wholesale.
 */

const MAX_HEADLINE = 240;
const MAX_LOCATION = 120;
const MAX_SUMMARY = 5000;
const MAX_YEARS = 60;

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
  // The two list guards judge exactly the items the payload below sends.
  const roleItems = splitList(roles);
  const locationItems = splitList(targetLocations);
  const rolesProblem = targetRolesIssue(roleItems);
  const locationsProblem = targetLocationsIssue(locationItems);
  const saveable = yearsValid && !rolesProblem && !locationsProblem;

  const save = React.useCallback(() => {
    if (!saveable || update.isPending) return;
    update.mutate({
      headline: headline.trim(),
      location: location.trim(),
      summary,
      yearsExperience: parsedYears,
      targetRoles: roleItems,
      targetLocations: locationItems,
    });
  }, [headline, location, locationItems, parsedYears, roleItems, saveable, summary, update]);

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
          {rolesProblem && (
            <p role="alert" className="text-xs text-destructive">
              {rolesProblem}
            </p>
          )}
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
          {locationsProblem && (
            <p role="alert" className="text-xs text-destructive">
              {locationsProblem}
            </p>
          )}
        </div>
      </div>
      <div className="space-y-2">
        <Label htmlFor="profile-summary">Summary</Label>
        <Textarea
          id="profile-summary"
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          rows={4}
          maxLength={MAX_SUMMARY}
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

/* --- the three free-form maps --------------------------------------------------- */

/**
 * `links`, `workAuthorization` and `preferences` are free-form `Map<String, Object>`s the
 * backend replaces wholesale on PATCH, so the editor always sends all three complete — a map
 * whose rows were all deleted goes out as `{}`, which is the clear. Values round-trip through
 * a lenient JSON read: anything that already parses as JSON keeps its type, anything else
 * stays a string, the way an env-var editor behaves.
 */

type MapName = "links" | "workAuthorization" | "preferences";

const MAP_SECTIONS: { name: MapName; label: string; keyPlaceholder: string }[] = [
  { name: "links", label: "Links", keyPlaceholder: "e.g. github" },
  { name: "workAuthorization", label: "Work authorization", keyPlaceholder: "e.g. status" },
  { name: "preferences", label: "Preferences", keyPlaceholder: "e.g. remote" },
];

interface MapRow {
  key: string;
  value: string;
}

function lenientJson(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return raw;
  }
}

function valueText(value: unknown): string {
  return typeof value === "string" ? value : JSON.stringify(value);
}

function rawMap(source: Record<string, unknown> | null, name: MapName): Record<string, unknown> {
  const value = source?.[name];
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function mapRows(source: Record<string, unknown> | null, name: MapName): MapRow[] {
  return Object.entries(rawMap(source, name)).map(([key, v]) => ({ key, value: valueText(v) }));
}

function rowsToMap(rows: MapRow[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const row of rows) {
    const key = row.key.trim();
    if (key) out[key] = lenientJson(row.value);
  }
  return out;
}

export function CareerProfileMapsCard() {
  const profile = useProfile();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Links & extras</CardTitle>
        <CardDescription>
          Free-form maps the agents read — links, work authorization, preferences. Values that
          parse as JSON keep their type; everything else is saved as a string.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {profile.isPending ? (
          <Skeleton className="h-20 w-full" />
        ) : profile.isError ? (
          <p className="text-sm text-muted-foreground">Profile could not be loaded.</p>
        ) : (
          <CareerProfileMapsForm initial={(profile.data ?? null) as Record<string, unknown> | null} />
        )}
      </CardContent>
    </Card>
  );
}

function CareerProfileMapsForm({ initial }: { initial: Record<string, unknown> | null }) {
  const update = useUpdateProfileDetails();
  const [maps, setMaps] = React.useState<Record<MapName, MapRow[]>>(() => ({
    links: mapRows(initial, "links"),
    workAuthorization: mapRows(initial, "workAuthorization"),
    preferences: mapRows(initial, "preferences"),
  }));

  const setRow = (name: MapName, index: number, row: MapRow) =>
    setMaps((m) => ({ ...m, [name]: m[name].map((r, i) => (i === index ? row : r)) }));
  const addRow = (name: MapName) =>
    setMaps((m) => ({ ...m, [name]: [...m[name], { key: "", value: "" }] }));
  const removeRow = (name: MapName, index: number) =>
    setMaps((m) => ({ ...m, [name]: m[name].filter((_, i) => i !== index) }));

  // Key order survives the round trip (Object.entries preserves insertion order), so a
  // serialized comparison is enough to say whether anything changed.
  const dirty = MAP_SECTIONS.some(
    ({ name }) => JSON.stringify(rowsToMap(maps[name])) !== JSON.stringify(rawMap(initial, name))
  );

  const save = React.useCallback(() => {
    if (!dirty || update.isPending) return;
    update.mutate(
      Object.fromEntries(MAP_SECTIONS.map(({ name }) => [name, rowsToMap(maps[name])]))
    );
  }, [dirty, maps, update]);

  return (
    <div className="space-y-5">
      {MAP_SECTIONS.map(({ name, label, keyPlaceholder }) => (
        <div key={name} className="space-y-2">
          <Label>{label}</Label>
          {maps[name].map((row, index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                value={row.key}
                placeholder={keyPlaceholder}
                aria-label={`${label} key ${index + 1}`}
                onChange={(e) => setRow(name, index, { ...row, key: e.target.value })}
                autoComplete="off"
              />
              <Input
                value={row.value}
                placeholder="value — JSON or plain text"
                aria-label={`${label} value ${index + 1}`}
                onChange={(e) => setRow(name, index, { ...row, value: e.target.value })}
                autoComplete="off"
              />
              <Button
                variant="ghost"
                size="icon"
                aria-label={`Remove ${label} row ${index + 1}`}
                onClick={() => removeRow(name, index)}
              >
                <X aria-hidden />
              </Button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={() => addRow(name)}>
            <Plus aria-hidden />
            Add row
          </Button>
        </div>
      ))}
      <div className="flex justify-end">
        <Button variant="ai" size="sm" loading={update.isPending} disabled={!dirty || update.isPending} onClick={save}>
          <Save aria-hidden />
          Save maps
        </Button>
      </div>
    </div>
  );
}
