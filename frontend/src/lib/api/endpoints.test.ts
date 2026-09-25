import { describe, expect, it } from "vitest";
import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { endpoints } from "./endpoints";

/**
 * The browser's path map used to be checked against a list of backend routes typed into this file
 * by hand. Both sides of that comparison were written here, so deleting a mapping on the Java side
 * left the guard green and moved the failure to runtime. The route table now comes out of the
 * controllers, and the HTTP verb the client actually sends is compared against the verbs Spring
 * binds — a wrong verb is a 405, and nothing on either side used to look at it.
 */

const CONTROLLERS = new URL("../../../../backend/src/main/java/com/careeros/", import.meta.url);
const API_PREFIX = "/api/v1";
const SAMPLE_ID = "11111111-1111-1111-1111-111111111111";

function javaFiles(dir: URL): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const child = new URL(`${entry.name}/`, dir);
    if (entry.isDirectory()) found.push(...javaFiles(child));
    else if (entry.name.endsWith("Controller.java")) found.push(fileURLToPath(child));
  }
  return found.sort();
}

/** `@GetMapping`, `@PostMapping("/x")` and `@GetMapping(value = "/x", produces = …)` all spell one verb. */
const METHOD_MAPPING = /@(Get|Post|Put|Patch|Delete)Mapping\b\s*(?:\(\s*(?:value\s*=\s*|path\s*=\s*)?"([^"]*)")?/g;

function fold(pattern: string): string {
  return pattern.replaceAll(/\{[^}]*\}/g, "{}");
}

/** Every public route the backend serves: `{}`-folded path → the verbs bound to it. */
function servedRoutes(): Map<string, Set<string>> {
  const routes = new Map<string, Set<string>>();
  const files = javaFiles(CONTROLLERS);
  if (files.length < 15) {
    throw new Error(`only found ${files.length} controllers under ${fileURLToPath(CONTROLLERS)}`);
  }
  for (const file of files) {
    const source = readFileSync(file, "utf8");
    const start = source.indexOf("public class");
    const head = source.slice(0, start);
    const prefix = /@RequestMapping\(\s*(?:value\s*=\s*|path\s*=\s*)?"([^"]*)"/.exec(head)?.[1] ?? "";
    for (const match of source.slice(start).matchAll(METHOD_MAPPING)) {
      const raw = match[2] ?? "";
      const path = raw.startsWith("/api/") ? raw : `${prefix}${raw}`;
      if (!path.startsWith(API_PREFIX)) continue; // /api/internal/* is never a browser route
      const key = fold(path.slice(API_PREFIX.length));
      const bound = routes.get(key) ?? new Set<string>();
      bound.add(match[1].toUpperCase());
      routes.set(key, bound);
    }
  }
  return routes;
}

function toRegex(pattern: string): RegExp {
  const body = pattern
    .split("{}")
    .map((part) => part.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .join("[^/]+");
  return new RegExp(`^${body}$`);
}

/**
 * Spring resolves by specificity — the most literal pattern wins — so the verb check uses the same
 * rule instead of the union of everything that could match. Otherwise `/jobs/{id}` would bless a
 * verb sent to `/jobs/saved`.
 */
function mostSpecific(patterns: string[], path: string): string | undefined {
  const hits = patterns
    .map((p) => ({ p, wildcards: (p.match(/\{\}/g) ?? []).length }))
    .filter((c) => toRegex(c.p).test(path))
    .sort((a, b) => a.wildcards - b.wildcards || b.p.length - a.p.length);
  return hits[0]?.p;
}

function collectPaths(node: unknown, out: string[] = []): string[] {
  if (typeof node === "string") out.push(node);
  else if (typeof node === "function") out.push((node as (id: string) => string)(SAMPLE_ID));
  else if (node && typeof node === "object") for (const v of Object.values(node)) collectPaths(v, out);
  return out;
}

/** name → one concrete path, so a call site can be resolved by the endpoint it names. */
function endpointMap(): Map<string, string> {
  const out = new Map<string, string>();
  const walk = (prefix: string, node: unknown) => {
    if (typeof node === "string") out.set(prefix, node);
    else if (typeof node === "function") {
      out.set(prefix, (node as (id: string) => string)(SAMPLE_ID));
    } else if (node && typeof node === "object") {
      for (const [k, v] of Object.entries(node)) walk(prefix ? `${prefix}.${k}` : k, v);
    }
  };
  walk("", endpoints);
  return out;
}

/** The text between the parentheses that open at `open` (quotes and nesting respected). */
function argsOf(source: string, open: number): string {
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    const c = source[i];
    if (c === `"`) i = source.indexOf(`"`, i + 1);
    else if (c === "'" || c === "`") i = skipLiteral(source, i, c);
    else if (c === "(" || c === "[" || c === "{") depth += 1;
    else if (c === ")" || c === "]" || c === "}") {
      depth -= 1;
      if (depth === 0) return source.slice(open + 1, i);
    }
  }
  return source.slice(open + 1);
}

function skipLiteral(source: string, start: number, quote: string): number {
  const close = source.indexOf(quote, start + 1);
  return close < 0 ? source.length : close;
}

/** `request(path, { method: "POST" })` — the verb is in the options object, never in the path. */
function verbOf(args: string, fallback: string): string {
  const rest = args.slice(args.indexOf(",") + 1);
  return /method:\s*"([A-Z]+)"/.exec(rest)?.[1] ?? fallback;
}

/** How the client reaches the network: helper name or explicit `method:` — both carry a verb. */
const HELPER_VERB: Record<string, string> = {
  get: "GET",
  list: "GET",
  create: "POST",
  update: "PATCH",
  remove: "DELETE",
  upload: "POST",
};

function sourceFiles(): string[] {
  const src = new URL("../../", import.meta.url);
  const found: string[] = [];
  const walk = (dir: URL) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const child = new URL(`${entry.name}/`, dir);
      if (entry.isDirectory() && entry.name !== "node_modules") walk(child);
      else if (/\.tsx?$/.test(entry.name) && !/\.(test|spec)\.tsx?$/.test(entry.name)) {
        found.push(fileURLToPath(child));
      }
    }
  };
  walk(src);
  return found.sort();
}

interface CallSite {
  file: string;
  verb: string;
  path: string;
}

/** The `(concrete path, verb)` pair every request call site sends, resolved through the endpoint map. */
/** Every `endpoints.x` the app mentions anywhere, so reachability is not limited to request calls. */
function referencedEndpoints(): Set<string> {
  const names = new Set<string>();
  for (const file of sourceFiles()) {
    for (const m of readFileSync(file, "utf8").matchAll(/\bendpoints\.([A-Za-z0-9_.]+)/g)) names.add(m[1]);
  }
  return names;
}

function callSites(): CallSite[] {
  const paths = endpointMap();
  const resolve = (expr: string): string | undefined => {
    const named = /endpoints\.([A-Za-z0-9_.]+)/.exec(expr);
    if (named) return paths.get(named[1]);
    const literal = /^["'`](\/[^"'`]*)["'`]/.exec(expr.trim());
    return literal ? literal[1] : undefined;
  };

  const calls: CallSite[] = [];
  const seen = new Set<string>();
  for (const file of sourceFiles()) {
    const source = readFileSync(file, "utf8");
    const rel = file.replace(/\\/g, "/").split("/frontend/")[1] ?? file;
    const announce = (verb: string, args: string, index: number) => {
      const path = resolve(args);
      if (!path) return;
      const key = `${rel}:${index}`;
      if (seen.has(key)) return;
      seen.add(key);
      calls.push({ file: rel, verb, path });
    };

    for (const m of source.matchAll(/\bapi\.(get|list|create|update|remove|upload)\s*(?:<[^>]*>)?\s*\(/g)) {
      const verb = HELPER_VERB[m[1]];
      if (verb) announce(verb, argsOf(source, (m.index ?? 0) + m[0].length - 1), m.index ?? 0);
    }
    // `request(path, { method: "POST" })` and the raw `fetch` in the token refresh: the verb only
    // ever appears in the options object, so the argument list has to be read as far as it goes.
    for (const m of source.matchAll(/\b(?:api\.)?(request|fetch)\s*(?:<[^>]*>)?\s*\(/g)) {
      const args = argsOf(source, (m.index ?? 0) + m[0].length - 1);
      announce(verbOf(args, "GET"), args, m.index ?? 0);
    }
  }
  return calls;
}

describe("endpoints ↔ backend route parity", () => {
  const paths = collectPaths(endpoints);
  const routes = servedRoutes();

  it("reads the backend's real route table", () => {
    // 58 public routes, measured — the same floor the Java side puts on its own table, so a
    // controller walk that silently lost a file reddens here instead of narrowing the contract.
    expect(routes.size).toBeGreaterThanOrEqual(58);
    expect([...routes.keys()]).toContain("/jobs/{}");
    expect([...routes.keys()]).toContain("/resumes/{}/parse");
    expect(routes.get("/applications/{}")).toEqual(new Set(["GET", "PATCH", "DELETE"]));
  });

  it("discovers the full client surface", () => {
    expect(paths.length).toBeGreaterThan(30);
  });

  it("every declared endpoint resolves to a real backend route", () => {
    const patterns = [...routes.keys()];
    const orphans = paths.filter((p) => !mostSpecific(patterns, p));
    expect(orphans).toEqual([]);
  });

  it("every request the client sends uses a verb the route binds", () => {
    const patterns = [...routes.keys()];
    const mismatched = callSites()
      .filter((c) => !routes.get(mostSpecific(patterns, c.path) ?? "")?.has(c.verb))
      .map((c) => `${c.verb} ${c.path} (${c.file})`);
    expect(mismatched).toEqual([]);
  });

  it("reads the client's own call sites", () => {
    const sites = callSites();
    // 60 request call sites, measured: a scan that found nothing would satisfy the verb rule the
    // same way an unused endpoint map would, so the inventory itself has to be non-trivial.
    expect(sites.length).toBeGreaterThanOrEqual(50);
    const verbs = new Set(sites.map((s) => s.verb));
    expect(verbs).toEqual(new Set(["GET", "POST", "PUT", "PATCH", "DELETE"]));
  });

  /**
   * Routes Spring serves that no `endpoints.*` name in the app ever mentions. Measured, not
   * assumed: this is the working list of the backend's unwired surface, and it may only shrink --
   * adding to it means writing a reason, so a route nobody looked at cannot pass as "unused on
   * purpose". `/jobs/import` sat in the hand-copied table for months while nothing built it.
   */
  const NEVER_REFERENCED: Record<string, string> = {
    "/auth/password/forgot": "no password-reset flow in the UI; the endpoints exist for ops runbooks",
    "/auth/password/reset": "same as the forgot pair: documented, served, not a browser screen",
    "/conversations/{}": "chats are created and read, never renamed or deleted from the app",
    "/health": "liveness for the container probe, not something a page calls",
    "/jobs/import": "jobs arrive through POST /jobs and POST /jds; no import screen exists",
    "/knowledge/documents": "file ingest goes through /resumes/upload and /knowledge/text",
    "/knowledge/sources/{}": "the sources panel polls status and deletes notes, not sources",
    "/me": "MeController's alias of /users/me; the client spells every call through /users/...",
    "/resume-versions/{}": "the version panel reads the list form /resume-versions?resumeId=…",
    "/resumes/{}/versions": "superseded for the panel by GET /resume-versions?resumeId=…",
  };

  function unreferencedRoutes(): string[] {
    const names = referencedEndpoints();
    const reachable = [...endpointMap()]
      .filter(([n]) => names.has(n) || names.has(n.split(".")[0]))
      .map(([, path]) => path);
    return [...routes.keys()]
      .filter((pattern) => !reachable.some((path) => toRegex(pattern).test(path)))
      .sort();
  }

  it("the routes the browser never asks for are listed, with a reason each", () => {
    expect(unreferencedRoutes()).toEqual(Object.keys(NEVER_REFERENCED));
    Object.entries(NEVER_REFERENCED).forEach(([route, why]) =>
      expect(why, `${route} needs a reason, not a blank`).not.toBe(""));
  });

  it("no dead routes that the backend removed (regression guards)", () => {
    // These were live-only in the frontend and 404'd against the backend.
    expect(paths).not.toContain("/matches");
    expect(paths).not.toContain("/ai/tailor");
    expect(paths).not.toContain("/ai/cover-letter");
    expect(paths).not.toContain("/ai/suggestions");
    expect(paths.some((p) => p.endsWith("/events"))).toBe(false);
  });
});
