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
 *
 * The bodies those calls post are the other half of the same wire. A key the handler's request
 * record does not name is not an error: Spring Boot's Jackson ignores it, so the request succeeds
 * having asked for nothing — which is how a drag posted `order` and `index` to a record that binds
 * `position`, and how five AI actions once posted one field under two spellings and failed to bind
 * at all. Both edges are checked against the records themselves, read as source, not a copy.
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
  for (const [pattern, byVerb] of routeTable()) {
    routes.set(pattern, new Set(byVerb.keys()));
  }
  return routes;
}

/** Same table, but each verb also carries the `@RequestBody` type it binds, when the handler has one. */
function routeTable(): Map<string, Map<string, string | undefined>> {
  const routes = new Map<string, Map<string, string | undefined>>();
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
      const from = (match.index ?? 0) + start;
      const nameEnd = source.indexOf("Mapping", from) + "Mapping".length;
      const open = /^\s*\(/.exec(source.slice(nameEnd));
      const annotationEnd = open ? matchingClose(source, nameEnd + open[0].length - 1) + 1 : nameEnd;
      const signature = source.slice(annotationEnd, source.indexOf("{", annotationEnd));
      // `@RequestBody(required = false) TailorRequest` and `@RequestBody @Valid JdRequest` are the
      // same handler shape to Spring, so both have to yield the record name.
      const body = /@RequestBody\s*(?:\([^)]*\))?\s+(?:@[\w.]+(?:\s*\([^)]*\))?\s+)*(\w+)/.exec(signature)?.[1];
      const key = fold(path.slice(API_PREFIX.length));
      const byVerb = routes.get(key) ?? new Map<string, string | undefined>();
      byVerb.set(match[1].toUpperCase(), body);
      routes.set(key, byVerb);
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
  if (clientSourceFiles) return clientSourceFiles;
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
  clientSourceFiles = found.sort();
  return clientSourceFiles;
}

let clientSourceFiles: string[] | undefined;

/** The client's sources are re-read by every call-site scan, so the file text is cached once. */
const fileTexts = new Map<string, string>();

function readFile(file: string): string {
  const cached = fileTexts.get(file);
  if (cached !== undefined) return cached;
  const text = readFileSync(file, "utf8");
  fileTexts.set(file, text);
  return text;
}

interface CallSite {
  file: string;
  verb: string;
  path: string;
  body: string;
}

/** Split a call's argument list on the commas that are not inside anything. */
function topArgs(args: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let current = "";
  for (let i = 0; i < args.length; i += 1) {
    const c = args[i];
    if (c === `"` || c === `'` || c === "`") {
      const close = args.indexOf(c, i + 1);
      current += args.slice(i, close + 1);
      i = close;
      continue;
    }
    if (c === "(" || c === "[" || c === "{") depth += 1;
    else if (c === ")" || c === "]" || c === "}") depth -= 1;
    if (c === "," && depth === 0) {
      out.push(current.trim());
      current = "";
      continue;
    }
    current += c;
  }
  if (current.trim()) out.push(current.trim());
  return out;
}

/**
 * A request body the reader can name. `field("k", v)` puts `k` on the wire whether it stands alone
 * or is spread into a literal; an object literal contributes its top-level keys, spelled-out or
 * shorthand. Anything else — a variable, a builder call, a spread of an unknown value — is
 * reported as unresolved rather than silently checked as "no keys".
 */
interface BodyReading {
  keys: string[];
  unresolved: string[];
}

function readBody(raw: string): BodyReading {
  const text = unwrapStringify(raw.trim());
  const keys = new Set<string>();
  const unresolved: string[] = [];
  for (const m of text.matchAll(/\bfield\(\s*["']([\w]+)["']/g)) keys.add(m[1]);
  const literal = outerObject(text);
  if (literal === undefined) {
    // a lone `field("k", v)` is the whole body; `payload` is not readable here
    const alone = /^field\(/.test(text) && matchingClose(text, text.indexOf("(")) === text.length - 1;
    if (alone) return { keys: [...keys], unresolved: [] };
    const call = /^([A-Za-z_$][\w$]*)\s*\(/.exec(text);
    const returned = call ? helperReturn(call[1]) : undefined;
    if (returned !== undefined) return mergeReadings(readBody(returned), { keys: [...keys], unresolved: [] });
    return { keys: [...keys], unresolved: [text] };
  }
  for (const piece of topArgs(literal)) {
    if (piece.startsWith("...")) {
      if (!/\bfield\(/.test(piece)) unresolvedPush(piece, unresolved);
      continue;
    }
    const named = /^["']?([A-Za-z_$][\w$]*)["']?\s*:/.exec(piece);
    const shorthand = /^([A-Za-z_$][\w$]*)$/.exec(piece);
    if (named) keys.add(named[1]);
    else if (shorthand) keys.add(shorthand[1]);
    else unresolvedPush(piece, unresolved);
  }
  return { keys: [...keys], unresolved };
}

function mergeReadings(a: BodyReading, b: BodyReading): BodyReading {
  return { keys: [...new Set([...a.keys, ...b.keys])], unresolved: [...a.unresolved, ...b.unresolved] };
}

/**
 * A body built by a named helper is checked through the literal that helper returns, so the
 * assembler functions in lib/api do not become a blind spot of this gate.
 */
function helperReturn(name: string): string | undefined {
  for (const file of sourceFiles()) {
    const source = stripComments(readFile(file));
    const decl = new RegExp(`\\bfunction\\s+${name}\\s*\\(`).exec(source);
    if (!decl) continue;
    const returned = /\breturn\s+/.exec(source.slice(decl.index));
    if (!returned) continue;
    const start = decl.index + returned.index + returned[0].length;
    return balancedFrom(source, start) ?? source.slice(start, source.indexOf(";", start)).trim();
  }
  return undefined;
}

/** The bracketed expression starting at `at`, ending at its own matching close. */
function balancedFrom(text: string, at: number): string | undefined {
  const openPair: Record<string, string> = { "{": "}", "(": ")", "[": "]" };
  const close = openPair[text[at]];
  if (!close) return undefined;
  let depth = 0;
  for (let i = at; i < text.length; i += 1) {
    const c = text[i];
    if (c === `"` || c === `'` || c === "`") {
      i = text.indexOf(c, i + 1);
      continue;
    }
    if (c === text[at]) depth += 1;
    else if (c === close) {
      depth -= 1;
      if (depth === 0) return text.slice(at, i + 1);
    }
  }
  return undefined;
}

/** An empty string is not a body, so a missing piece must not read as "a body with no keys". */
function unresolvedPush(piece: string, out: string[]): void {
  if (piece.trim()) out.push(piece.trim());
}

/** `JSON.stringify({ … })` is the fetch path's wrapper around the same object the helpers post. */
function unwrapStringify(text: string): string {
  const open = /^JSON\.stringify\s*\(/.exec(text);
  return open ? argsOf(text, open[0].length - 1).trim() : text;
}

/** The inside of `{ … }`, but only when that literal is the whole expression. */
function outerObject(text: string): string | undefined {
  if (!text.startsWith("{")) return undefined;
  let depth = 0;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (c === `"` || c === `'` || c === "`") {
      i = text.indexOf(c, i + 1);
      continue;
    }
    if (c === "{") depth += 1;
    else if (c === "}") {
      depth -= 1;
      if (depth === 0) return i === text.length - 1 ? text.slice(1, -1) : undefined;
    }
  }
  return undefined;
}

/** Where the body is: the second argument for the helpers, the `body:` value of the options object. */
function bodyOf(kind: "helper" | "raw", args: string): string {
  const second = topArgs(args)[1] ?? "";
  return kind === "helper" ? second : optionValue(second, "body");
}

/** The value of one key in an object literal, read as a whole expression and nothing after it. */
function optionValue(literal: string, key: string): string {
  const inside = outerObject(literal.trim());
  if (inside === undefined) return "";
  for (const piece of topArgs(inside)) {
    const named = new RegExp(`^${key}\\s*:`).exec(piece);
    if (named) return piece.slice(named[0].length).trim();
  }
  return "";
}

/**
 * Comments are gone before anything is parsed. A `//` line inside the options object used to make
 * the `body:` piece start with prose instead of a name, so the whole call site dropped out of this
 * gate without a word — the most expensive kind of green.
 */
function stripComments(code: string): string {
  let out = "";
  for (let i = 0; i < code.length; i += 1) {
    const c = code[i];
    if (c === `"` || c === `'` || c === "`") {
      const close = code.indexOf(c, i + 1);
      const end = close < 0 ? code.length : close;
      out += code.slice(i, end + 1);
      i = end;
      continue;
    }
    if (c === "/" && code[i + 1] === "/") {
      const nl = code.indexOf("\n", i);
      i = nl < 0 ? code.length : nl - 1;
      out += "\n";
      continue;
    }
    if (c === "/" && code[i + 1] === "*") {
      const end = code.indexOf("*/", i + 2);
      const stop = end < 0 ? code.length : end + 1;
      out += code.slice(i, stop).replaceAll(/[^\n]/g, "");
      i = stop;
      continue;
    }
    out += c;
  }
  return out;
}

/** Every request call site, with the body text it offers when it offers one. */
/** Every `endpoints.x` the app mentions anywhere, so reachability is not limited to request calls. */
function referencedEndpoints(): Set<string> {
  const names = new Set<string>();
  for (const file of sourceFiles()) {
    for (const m of readFile(file).matchAll(/\bendpoints\.([A-Za-z0-9_.]+)/g)) names.add(m[1]);
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
    const announce = (verb: string, args: string, index: number, kind: "helper" | "raw") => {
      const path = resolve(args);
      if (!path) return;
      const key = `${rel}:${index}`;
      if (seen.has(key)) return;
      seen.add(key);
      calls.push({ file: rel, verb, path, body: bodyOf(kind, stripComments(args)) });
    };

    for (const m of source.matchAll(/\bapi\.(get|list|create|update|remove|upload)\s*(?:<[^>]*>)?\s*\(/g)) {
      const verb = HELPER_VERB[m[1]];
      // only the writing helpers carry a body; a GET's second argument is a query, not a payload
      const sendsBody = m[1] === "create" || m[1] === "update" || m[1] === "upload";
      if (verb) announce(verb, argsOf(source, (m.index ?? 0) + m[0].length - 1), m.index ?? 0, sendsBody ? "helper" : "raw");
    }
    // `request(path, { method: "POST" })` and the raw `fetch` in the token refresh: the verb only
    // ever appears in the options object, so the argument list has to be read as far as it goes.
    for (const m of source.matchAll(/\b(?:api\.)?(request|fetch)\s*(?:<[^>]*>)?\s*\(/g)) {
      const args = argsOf(source, (m.index ?? 0) + m[0].length - 1);
      announce(verbOf(args, "GET"), args, m.index ?? 0, "raw");
    }
  }
  return calls;
}

const DTO_SOURCES = new URL("../../../../backend/src/main/java/", import.meta.url);

function allJava(dir: URL): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const child = new URL(`${entry.name}/`, dir);
    if (entry.isDirectory()) found.push(...allJava(child));
    else if (entry.name.endsWith(".java")) found.push(fileURLToPath(child));
  }
  return found;
}

let dtoIndex: Map<string, string> | undefined;

/** What one request record accepts: every component under its own name and under each alias. */
interface RecordBindings {
  accepts: Set<string>;
  /** component name → the alias spellings that mean the same field */
  twins: Map<string, string[]>;
}

/** The request record the handler binds: its component names plus every `@JsonAlias` spelling. */
function recordBindings(type: string): RecordBindings {
  if (!dtoIndex) {
    dtoIndex = new Map<string, string>();
    for (const file of allJava(DTO_SOURCES)) {
      const source = readFileSync(file, "utf8");
      for (const m of source.matchAll(/\brecord\s+(\w+)\s*\(/g)) {
        const open = (m.index ?? 0) + m[0].length - 1;
        dtoIndex.set(m[1], source.slice(open + 1, matchingClose(source, open)));
      }
    }
  }
  const components = dtoIndex.get(type);
  if (components === undefined) throw new Error(`no record named ${type} in the backend sources`);
  const accepts = new Set<string>();
  const twins = new Map<string, string[]>();
  for (const piece of splitComponents(components)) {
    const aliases: string[] = [];
    for (const alias of piece.matchAll(/@JsonAlias\(([^)]*)\)/g)) {
      for (const quoted of alias[1].matchAll(/"([^"]+)"/g)) {
        aliases.push(quoted[1]);
        accepts.add(quoted[1]);
      }
    }
    const own = piece.replace(/@[\w.]+(\s*\([^)]*\))?/g, " ").trim().split(/\s+/).pop();
    if (own && /^[a-z]\w*$/.test(own)) {
      accepts.add(own);
      twins.set(own, aliases);
    }
  }
  return { accepts, twins };
}

function matchingClose(source: string, open: number): number {
  let depth = 0;
  for (let i = open; i < source.length; i += 1) {
    if (source[i] === "(") depth += 1;
    else if (source[i] === ")") {
      depth -= 1;
      if (depth === 0) return i;
    }
  }
  return source.length;
}

/**
 * A Java record's component list, split on the commas that separate components. `Map<String,
 * Object> tailored` is one component, so angle brackets count as nesting here in a way they
 * must not in a TypeScript argument list.
 */
function splitComponents(declaration: string): string[] {
  const out: string[] = [];
  let depth = 0;
  let current = "";
  for (let i = 0; i < declaration.length; i += 1) {
    const c = declaration[i];
    if (c === `"`) {
      const close = declaration.indexOf(`"`, i + 1);
      current += declaration.slice(i, close + 1);
      i = close;
      continue;
    }
    if (c === "(" || c === "{" || c === "<" || c === "[") depth += 1;
    else if (c === ")" || c === "}" || c === ">" || c === "]") depth -= 1;
    if (c === "," && depth === 0) {
      out.push(current.trim());
      current = "";
      continue;
    }
    current += c;
  }
  if (current.trim()) out.push(current.trim());
  return out;
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

  /**
   * A Spring record accepts a field under its own name *or* under a `@JsonAlias`, never both: the
   * two spellings resolve to one constructor parameter, a record has no setter to absorb the
   * second value, and Jackson then fails to bind the whole body. That is why the bodies posted
   * through `field()` name one spelling each (lib/api/body.ts) — and why this check is separate
   * from the "is the key bound at all" rule: both spellings pass that one.
   */
  function twinClash(keys: string[], twins: Map<string, string[]>): string[] {
    const sent = new Set(keys);
    const clash: string[] = [];
    for (const [own, aliases] of twins) {
      const hit = aliases.filter((a) => sent.has(a));
      if (sent.has(own) && hit.length) clash.push(`${own} + ${hit.join("/")}`);
    }
    return clash;
  }

  interface BodyRow {
    site: CallSite;
    pattern: string;
    dto: string | undefined;
    keys: string[];
    unresolved: string[];
    accepts: Set<string>;
    twins: Map<string, string[]>;
  }

  let bodyRows: BodyRow[] | undefined;

  function readBodies(): BodyRow[] {
    if (bodyRows) return bodyRows;
    const table = routeTable();
    bodyRows = callSites()
      .filter((c) => c.body)
      .map((c) => {
        const pattern = mostSpecific([...table.keys()], c.path) ?? "";
        const dto = table.get(pattern)?.get(c.verb);
        const reading = readBody(c.body);
        const bindings = dto ? recordBindings(dto) : { accepts: new Set<string>(), twins: new Map<string, string[]>() };
        return {
          site: c,
          pattern,
          dto,
          keys: reading.keys,
          unresolved: reading.unresolved,
          accepts: bindings.accepts,
          twins: bindings.twins,
        };
      });
    return bodyRows;
  }

  const label = (row: BodyRow, msg: string) => `${row.site.verb} ${row.pattern} ${msg} (${row.site.file})`;

  /**
   * Bodies the reader cannot name a key list for, each with the reason it stays quiet. This list
   * may only shrink: a body that becomes a variable, a spread of an unknown value or a helper this
   * file cannot follow has to be written down here before the gate stops looking at it.
   */
  const UNREADABLE_BODIES: Record<string, string> = {
    "POST /auth/login": "the raw fetch posts the caller's `payload` object verbatim; its fields are typed by client.ts, which this reader stops at",
    "POST /auth/register": "same raw fetch and same verbatim `payload` as login",
    "POST /applications": "mutationFn takes `body: Partial<Application> & { title }` and forwards it whole, so the key names are the caller's",
    "PATCH /applications/{}": "forwards the caller's `patch` object; the three names it documents are status/position/note",
    "POST /knowledge/notes": "forwards the note editor's `body`, which carries the whole note form",
    "POST /interview/sessions": "forwards the setup form's `body`",
    "PATCH /users/me/profile": "forwards the profile editor's `patch`, one key per form field the user edited",
    "PATCH /users/me": "forwards the account form's `patch`",
    "POST /resumes/upload": "a FormData part list, not a JSON body — Spring binds it through @RequestPart, so no record names these keys",
  };

  function unreadableKeys(): string[] {
    return readBodies()
      .filter((r) => r.unresolved.length > 0 || !r.dto)
      .map((r) => `${r.site.verb} ${r.pattern}`)
      .sort();
  }

  it("every key a request body sends is a field the handler binds", () => {
    const dropped = readBodies()
      .filter((r) => !r.unresolved.length && r.dto)
      .map((r) => ({ row: r, bad: r.keys.filter((k) => !r.accepts.has(k)) }))
      .filter((x) => x.bad.length)
      .map((x) => label(x.row, `sends ${JSON.stringify(x.bad)}, which Jackson drops`));
    expect(dropped).toEqual([]);
  });

  it("a body never names one field twice, under its own name and under an alias", () => {
    const clashes = readBodies()
      .filter((r) => !r.unresolved.length && r.dto)
      .map((r) => ({ row: r, both: twinClash(r.keys, r.twins) }))
      .filter((x) => x.both.length)
      .map((x) => label(x.row, `posts ${JSON.stringify(x.both)} — a record cannot bind two spellings`));
    expect(clashes).toEqual([]);
  });

  it("a body is never posted to a handler that binds none", () => {
    const stray = readBodies()
      .filter((r) => !r.unresolved.length && !r.dto)
      .map((r) => label(r, `sends ${JSON.stringify(r.keys)} to a handler with no @RequestBody`));
    expect(stray).toEqual([]);
  });

  it("the bodies this gate cannot read are written down, with a reason each", () => {
    expect(unreadableKeys()).toEqual(Object.keys(UNREADABLE_BODIES).sort());
    Object.entries(UNREADABLE_BODIES).forEach(([site, why]) =>
      expect(why, `${site} needs a reason, not a blank`).not.toBe(""));
  });

  it("reads the bodies it claims to read", () => {
    const rows = readBodies();
    // 24 call sites carry a body and 15 of them are checked name by name, measured. Without this
    // floor the gate could go vacuous in one edit: an unreadable reader passes every assertion
    // above exactly as quietly as a scanner that found no requests at all.
    expect(rows.length).toBeGreaterThanOrEqual(24);
    const checked = rows.filter((r) => !r.unresolved.length && r.dto);
    expect(checked.length).toBeGreaterThanOrEqual(15);
    // the AI actions are the flows whose bodies broke, so their presence is asserted, not assumed
    const paths = new Set(checked.map((r) => `${r.site.verb} ${r.pattern}`));
    ["POST /jobs/{}/match", "POST /jobs/{}/tailor", "POST /jobs/{}/cover-letter",
      "POST /jobs/{}/tailored-version", "POST /jds/suggestions"].forEach((p) => expect(paths).toContain(p));
    expect(new Set(checked.flatMap((r) => r.keys))).toContain("resumeVersionId");
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
