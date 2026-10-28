/**
 * The free-form profile maps' data contract: `links`, `workAuthorization` and
 * `preferences` are `Map<String, Object>`s the backend replaces wholesale on PATCH,
 * so the editor always sends all three complete — and a map whose rows were all
 * deleted goes out as `{}`, the clear.
 *
 * Values round-trip through a lenient JSON read: anything that already parses as
 * JSON keeps its type, anything else stays a string — the way an env-var editor
 * behaves. That round trip is the whole reason this file is extracted from
 * `profile-cards.tsx`: a typed value that survived the render→edit→save cycle
 * unmangled is invisible on screen ("a string that looks like JSON is the same
 * string"), so only a test can hold it.
 */

export type MapName = "links" | "workAuthorization" | "preferences";

export const MAP_SECTIONS: { name: MapName; labelKey: string; keyPlaceholderKey: string }[] = [
  { name: "links", labelKey: "profile.maps.links", keyPlaceholderKey: "profile.maps.linksPlaceholder" },
  {
    name: "workAuthorization",
    labelKey: "profile.maps.workAuthorization",
    keyPlaceholderKey: "profile.maps.workAuthorizationPlaceholder",
  },
  {
    name: "preferences",
    labelKey: "profile.maps.preferences",
    keyPlaceholderKey: "profile.maps.preferencesPlaceholder",
  },
];

export interface MapRow {
  key: string;
  value: string;
}

/** A server list as the editor's comma text; anything that is not a list is nothing. */
export function listText(value: unknown): string {
  return Array.isArray(value) ? value.map(String).join(", ") : "";
}

/** A typed string read: a missing key, a null, or a number all read as the empty field. */
export function readString(source: Record<string, unknown> | null, key: string): string {
  const v = source?.[key];
  return typeof v === "string" ? v : "";
}

/** `yearsExperience` arrives as a number; a string spelling of one is not a number. */
export function readYears(source: Record<string, unknown> | null): string {
  const v = source?.["yearsExperience"];
  return typeof v === "number" ? String(v) : "";
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

/** Server map → editor rows. A row's value is the JSON spelling of the stored value. */
export function mapRows(source: Record<string, unknown> | null, name: MapName): MapRow[] {
  return Object.entries(rawMap(source, name)).map(([key, v]) => ({ key, value: valueText(v) }));
}

/** Editor rows → server map, with the lenient read applied per value. */
export function rowsToMap(rows: MapRow[]): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const row of rows) {
    const key = row.key.trim();
    if (key) out[key] = lenientJson(row.value);
  }
  return out;
}

export { lenientJson, valueText, rawMap };
