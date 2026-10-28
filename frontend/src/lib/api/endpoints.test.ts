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
 *
 * The query strings are the third edge, and the quietest: a parameter no `@RequestParam` declares
 * is dropped without a word, so `?size=5` on a feed that reads `?limit=` is a dashboard that asks
 * for five rows and gets the server's default thirty. Routes, bodies and parameters are all read
 * out of one pass over the controllers, so the three rules cannot disagree about a handler.
 */

const CONTROLLERS = new URL("../../../../backend/src/main/java/com/careeros/", import.meta.url);
const API_PREFIX = "/api/v1";
const SAMPLE_ID = "11111111-1111-1111-1111-111111111111";

function javaFiles(dir: URL): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      found.push(...javaFiles(new URL(`${entry.name}/`, dir)));
    } else if (entry.name.endsWith("Controller.java")) {
      // No trailing slash on file entries: fileURLToPath keeps it, Windows' open
      // strips it, and Linux answers ENOTDIR — the suite never collected there.
      found.push(fileURLToPath(new URL(entry.name, dir)));
    }
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
  for (const handler of javaHandlers()) {
    const byVerb = routes.get(handler.pattern) ?? new Map<string, string | undefined>();
    byVerb.set(handler.verb, handler.body);
    routes.set(handler.pattern, byVerb);
  }
  return routes;
}

/**
 * One `@RequestParam` in a handler's signature. `required` is Spring's own rule: an explicit
 * `required = false` or a `defaultValue` makes the parameter optional, and anything else makes a
 * request that omits it fail with a 400 before the handler runs.
 */
interface BoundParam {
  name: string;
  required: boolean;
  /** `MultipartFile` parameters ride in the multipart parts of the body, never in the query string */
  fromBody: boolean;
  /** the wire name was spelled out as `name = "…"`/`value = "…"`, so it is not simply the variable */
  spelledInAttribute: boolean;
}

/** One handler the controllers bind: its route, the record it asks for as a body, its query surface. */
interface Handler {
  verb: string;
  pattern: string;
  body: string | undefined;
  params: BoundParam[];
  /** a `@RequestParam` this reader could not name, kept verbatim so the gate says so out loud */
  unparsed: string[];
}

/**
 * The names a call site must put in the query string: required by Spring's rules (no
 * `required = false`, no `defaultValue`) and not a multipart part. A `MultipartFile` arrives in
 * the body's parts, so demanding it in the URL would indict every upload call site for a bug that
 * cannot exist. This is the only place that decision is made; the floor test pins its whole-table
 * answer, because no upload route is sent a query today and so the exclusion is otherwise
 * invisible to the rule that consumes it.
 */
function requiredInQuery(h: Handler): string[] {
  return h.params.filter((p) => p.required && !p.fromBody).map((p) => p.name);
}

/**
 * The one walk of the controller sources. The route table, the `@RequestBody` types and the
 * `@RequestParam` names all come out of the same pass over the same signature text, because a
 * second parser written beside this one would drift from it — and a gate that reads a route the
 * verb gate does not see reports an unbound parameter where the real handler binds it.
 */
function javaHandlers(): Handler[] {
  const handlers: Handler[] = [];
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
      const bindings = boundParams(signature);
      handlers.push({
        verb: match[1].toUpperCase(),
        pattern: fold(path.slice(API_PREFIX.length)),
        // `@RequestBody(required = false) TailorRequest` and `@RequestBody @Valid JdRequest` are
        // the same handler shape to Spring, so both have to yield the record name.
        body: /@RequestBody\s*(?:\([^)]*\))?\s+(?:@[\w.]+(?:\s*\([^)]*\))?\s+)*(\w+)/.exec(signature)?.[1],
        params: bindings.params,
        unparsed: bindings.unparsed,
      });
    }
  }
  return handlers;
}

/**
 * Every `@RequestParam` a handler signature declares, named the way Spring will match it. A
 * parameter this reader cannot name is reported, never guessed at: reading it as "a parameter
 * nobody binds" would blame the client for the handler's own shape.
 */
function boundParams(signature: string): { params: BoundParam[]; unparsed: string[] } {
  const marks = [...signature.matchAll(/@RequestParam\b/g)];
  const params: BoundParam[] = [];
  const unparsed: string[] = [];
  for (let i = 0; i < marks.length; i += 1) {
    const mark = marks[i];
    const after = (mark.index ?? 0) + mark[0].length;
    const until = i + 1 < marks.length ? (marks[i + 1].index ?? signature.length) : signature.length;
    const parens = /^\s*\(/.exec(signature.slice(after));
    const close = parens ? matchingClose(signature, after + parens[0].length - 1) : after;
    const attributes = parens ? signature.slice(after + parens[0].length, close) : "";
    // whatever follows the attribute list is the declaration itself: ` int limit`, ` String q`
    const declared = signature.slice(parens ? close + 1 : close, until);
    const attribute = /\b(?:name|value)\s*=\s*"([^"]+)"/.exec(attributes)?.[1];
    const quoted = attribute ?? /^\s*"([^"]+)"/.exec(attributes)?.[1];
    const variable = /([a-z]\w*)\s*$/.exec(declared.slice(0, topLevelParamEnd(declared)))?.[1];
    const name = quoted ?? variable;
    if (!name) {
      unparsed.push(declared.trim().replace(/\s+/g, " "));
      continue;
    }
    params.push({
      name,
      required: !/\brequired\s*=\s*false\b/.test(attributes) && !/\bdefaultValue\s*=/.test(attributes),
      fromBody: /\bMultipartFile\b/.test(declared),
      spelledInAttribute: quoted !== undefined,
    });
  }
  return { params, unparsed };
}

/** Where a parameter declaration ends: the first comma or closing paren that is not nested. */
function topLevelParamEnd(text: string): number {
  let depth = 0;
  for (let i = 0; i < text.length; i += 1) {
    const c = text[i];
    if (c === `"`) {
      i = text.indexOf(`"`, i + 1);
      continue;
    }
    if (c === "(" || c === "[" || c === "{" || c === "<") depth += 1;
    else if (c === ")" || c === "]" || c === "}" || c === ">") {
      if (depth === 0 && c === ")") return i;
      depth -= 1;
    } else if (c === "," && depth === 0) return i;
  }
  return text.length;
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

/**
 * How the client reaches the network. `request`/`fetch` carry the verb inside an options object, so
 * that object has to be read as far as it goes; the helpers all fix their verb, and what their
 * second argument holds differs by kind — `get`/`list` hand it to `buildUrl` as query parameters,
 * the writing helpers hand it to fetch as a body. Reading a query object as a body would report
 * "a body with no keys", the most comfortable kind of false green.
 */
type ArgShape = "params" | "body" | "options";

const HELPERS: Record<string, { verb: string; shape: ArgShape }> = {
  get: { verb: "GET", shape: "params" },
  list: { verb: "GET", shape: "params" },
  create: { verb: "POST", shape: "body" },
  update: { verb: "PATCH", shape: "body" },
  remove: { verb: "DELETE", shape: "options" },
  upload: { verb: "POST", shape: "body" },
};

function sourceFiles(): string[] {
  if (clientSourceFiles) return clientSourceFiles;
  const src = new URL("../../", import.meta.url);
  const found: string[] = [];
  const walk = (dir: URL) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      if (entry.isDirectory() && entry.name !== "node_modules") walk(new URL(`${entry.name}/`, dir));
      else if (/\.tsx?$/.test(entry.name) && !/\.(test|spec)\.tsx?$/.test(entry.name)) {
        found.push(fileURLToPath(new URL(entry.name, dir)));
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
  /** the same file as the scanner opened it, so a spread can be followed back to its declaration */
  abs: string;
  /** where the call starts in that file, which is how the enclosing function is found */
  index: number;
  verb: string;
  path: string;
  body: string;
  query: string;
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

/** Where the body is: the second argument for a writing helper, the `body:` value of an options object. */
function bodyOf(shape: ArgShape, args: string): string {
  if (shape === "params") return "";
  const second = topArgs(args)[1] ?? "";
  return shape === "body" ? second : optionValue(second, "body");
}

/** Where the query is: the whole second argument for `api.get`, the `params:` value for `request`. */
function queryOf(shape: ArgShape, args: string): string {
  if (shape === "body") return "";
  const second = topArgs(args)[1] ?? "";
  return shape === "params" ? second : optionValue(second, "params");
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
    const announce = (
      verb: string,
      args: string,
      index: number,
      shape: ArgShape,
      absolute: string
    ) => {
      const path = resolve(args);
      if (!path) return;
      const key = `${rel}:${index}`;
      if (seen.has(key)) return;
      seen.add(key);
      const stripped = stripComments(args);
      calls.push({
        file: rel,
        abs: absolute,
        index,
        verb,
        path,
        body: bodyOf(shape, stripped),
        query: queryOf(shape, stripped),
      });
    };

    for (const m of source.matchAll(/\bapi\.(get|list|create|update|remove|upload)\s*(?:<[^>]*>)?\s*\(/g)) {
      const helper = HELPERS[m[1]];
      if (helper) announce(helper.verb, argsOf(source, (m.index ?? 0) + m[0].length - 1), m.index ?? 0, helper.shape, file);
    }
    // `request(path, { method: "POST" })`, `postSSE(path, { method: "POST" }, handlers)` and the
    // raw `fetch` in the token refresh: the verb only ever appears in the options object, so the
    // argument list has to be read as far as it goes.
    for (const m of source.matchAll(/\b(?:api\.)?(request|fetch|postSSE)\s*(?:<[^>]*>)?\s*\(/g)) {
      const args = argsOf(source, (m.index ?? 0) + m[0].length - 1);
      announce(verbOf(args, "GET"), args, m.index ?? 0, "options", file);
    }
  }
  return calls;
}

const DTO_SOURCES = new URL("../../../../backend/src/main/java/", import.meta.url);

function allJava(dir: URL): string[] {
  const found: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) found.push(...allJava(new URL(`${entry.name}/`, dir)));
    else if (entry.name.endsWith(".java")) found.push(fileURLToPath(new URL(entry.name, dir)));
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

/**
 * The query object an `api.get` hands to `buildUrl`, read the same way as a request body: literal
 * keys and shorthand names count, and a spread of a parameter the enclosing function declares with
 * an inline object type counts through that declaration. Anything the reader cannot follow — a
 * builder's result, a type with an index signature, a variable from another module — is reported
 * as unresolved so the call site has to be written down rather than pass as "sends nothing".
 */
function readQuery(raw: string, abs: string, index: number): BodyReading {
  const text = raw.trim();
  const keys = new Set<string>();
  const unresolved: string[] = [];
  const literal = outerObject(text);
  if (literal === undefined) return { keys: [], unresolved: [text] };
  for (const piece of topArgs(literal)) {
    if (piece.startsWith("...")) {
      const spread = /^\.\.\.\s*\(?\s*([A-Za-z_$][\w$]*)/.exec(piece)?.[1];
      const declared = spread === undefined ? undefined : declaredKeys(abs, index, spread);
      if (declared) for (const key of declared) keys.add(key);
      else unresolvedPush(piece, unresolved);
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

/** The inline object type `name` is declared with in the function that encloses `index`. */
function declaredKeys(abs: string, index: number, name: string): string[] | undefined {
  const source = readFile(abs);
  const before = source.slice(0, index);
  const finder = /\bfunction\s+[A-Za-z_$][\w$]*\s*\(/g;
  let header = finder.exec(before);
  if (header) for (let next = finder.exec(before); next; next = finder.exec(before)) header = next;
  if (!header) return undefined;
  const params = balancedFrom(source, (header.index ?? 0) + header[0].length - 1);
  if (!params) return undefined;
  for (const piece of topArgs(stripComments(params).slice(1, -1))) {
    const colon = new RegExp(`^${name}\\??\\s*:\\s*`).exec(piece);
    if (colon) return typeKeys(piece.slice(colon[0].length));
  }
  return undefined;
}

/**
 * The keys of an inline object type literal, whose members separate with `;` — so the comma splitter
 * a value literal needs is the wrong tool here. An index signature (`[filter: string]: …`) means any
 * name can travel through the spread, which is the one answer this gate must not guess at, so it
 * comes back unresolvable.
 */
function typeKeys(text: string): string[] | undefined {
  const literal = outerObject(text.trim());
  if (literal === undefined) return undefined;
  if (/\[\s*[A-Za-z_$][\w$]*\s*:\s*(?:string|number|symbol)\s*\]\s*:/.test(literal)) return undefined;
  const parts: string[] = [];
  let depth = 0;
  let current = "";
  for (const c of literal) {
    if (c === "(" || c === "[" || c === "{" || c === "<") depth += 1;
    else if (c === ")" || c === "]" || c === "}" || c === ">") depth -= 1;
    if ((c === ";" || c === ",") && depth === 0) {
      parts.push(current);
      current = "";
      continue;
    }
    current += c;
  }
  parts.push(current);
  const keys: string[] = [];
  for (const part of parts) {
    const member = /^\s*(?:readonly\s+)?(["']?)([A-Za-z_$][\w$]*)\1\??\s*:/.exec(part);
    if (member) keys.push(member[2]);
  }
  return keys;
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
   * purpose". `/jobs/import` sat in the hand-copied table for months while nothing built it --
   * the paste-a-posting dialog finally wired it, and its entry left.
   */
  const NEVER_REFERENCED: Record<string, string> = {
    "/health": "liveness for the container probe, not something a page calls",
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
      // An alias that restates the field's own name (ImportJobRequest lists "rawText" beside
      // "raw_text") is one spelling, not two: posting the own name alone binds one value, so
      // only an alias spelled differently counts as a second one.
      const hit = aliases.filter((a) => a !== own && sent.has(a));
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
    "POST /contacts": "same registry form, same contactBody() — blanks stay absent",
    "POST /interview/sessions": "forwards the setup form's `body`",
    "PATCH /users/me/profile": "forwards the profile editor's `patch`, one key per form field the user edited",
    "PATCH /contacts/{}": "the registry form posts its current values through contactBody(), which builds the record key by key — blanks stay absent",
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

  /* ------------------------------ query strings ----------------------------- */

  interface QueryRow {
    site: CallSite;
    pattern: string;
    keys: string[];
    unresolved: string[];
    bound: Set<string>;
  }

  let queryRowsCache: QueryRow[] | undefined;

  function queryRows(): QueryRow[] {
    if (queryRowsCache) return queryRowsCache;
    const table = routeTable();
    const patterns = [...table.keys()];
    const handlers = new Map<string, Handler>();
    for (const h of javaHandlers()) handlers.set(`${h.verb} ${h.pattern}`, h);
    queryRowsCache = callSites()
      .filter((c) => c.query.trim() !== "")
      .map((c) => {
        const pattern = mostSpecific(patterns, c.path) ?? "";
        const handler = handlers.get(`${c.verb} ${pattern}`);
        const reading = readQuery(c.query, c.abs, c.index);
        return {
          site: c,
          pattern,
          keys: reading.keys,
          // a handler whose own parameter list the reader cannot finish makes the comparison
          // unanswerable from either side, so the call site goes to the written-down list
          unresolved: [
            ...reading.unresolved,
            ...(handler?.unparsed ?? []).map((u) => `handler binds @RequestParam(${u}) the reader cannot name`),
          ],
          bound: new Set((handler?.params ?? []).map((p) => p.name)),
        };
      });
    return queryRowsCache;
  }

  /**
   * A query the gate skips must be covered somewhere else, and that somewhere else has to still
   * say so: the reason below names the test file and the test, both of which are checked here, so
   * the exemption cannot outlive the gate that pays for it.
   */
  const COVERED_ELSEWHERE: Record<string, { file: URL; markers: string[] }> = {
    "GET /jobs": {
      file: new URL("../job-filter.test.ts", import.meta.url),
      markers: ["sends nothing the endpoint has not declared", "JobController.java"],
    },
  };

  /**
   * Query objects whose key list this reader cannot produce, each with the reason it stays quiet.
   * Shrink-only, like the body list above: `...clean` is the one entry today because the job
   * filters are gated by name in `job-filter.test.ts`.
   */
  const UNREADABLE_QUERIES: Record<string, string> = {
    "GET /jobs":
      "`...clean` is serializeJobFilters' own key list, and job-filter.test.ts gates those names against this handler's parameters",
  };

  function unreadableQueries(): string[] {
    return queryRows()
      .filter((r) => r.unresolved.length > 0)
      .map((r) => `${r.site.verb} ${r.pattern}`)
      .sort();
  }

  const queryLabel = (row: QueryRow, msg: string) =>
    `${row.site.verb} ${row.pattern} ${msg} (${row.site.file})`;

  it("every query parameter the browser appends is one the handler binds", () => {
    // Spring answers a parameter no `@RequestParam` declares by ignoring it: the request is a 200
    // whose rows were never trimmed or filtered. That is how the dashboard asked for its five
    // recent runs with `size=5` against a handler that binds `limit`, and shipped the thirty the
    // server defaults to — while `GET /jobs/saved` was sent a page size it does not read at all.
    const ignored = queryRows()
      .filter((r) => !r.unresolved.length)
      .map((r) => ({ row: r, bad: r.keys.filter((k) => !r.bound.has(k)) }))
      .filter((x) => x.bad.length)
      .map((x) => queryLabel(x.row, `appends ${JSON.stringify(x.bad)}, which Spring ignores`));
    expect(ignored).toEqual([]);
  });

  it("a parameter the handler cannot do without is sent by every call site on that route", () => {
    // The mirror of the rule above, and it has to be per call site: `@RequestParam String q` with
    // neither `required = false` nor a `defaultValue` is a 400 for *the caller that forgot it*, not
    // for the route. `GET /search` has two callers, the ⌘K palette and the global-search hook, and
    // an earlier version of this rule folded them into one set — so the hook could drop `q` and
    // still be green on the strength of the palette's query. A route nobody calls from the browser
    // has no caller to break; an unreadable query is reported rather than assumed to carry it.
    const byRoute = new Map<string, QueryRow[]>();
    for (const r of queryRows()) {
      const key = `${r.site.verb} ${r.pattern}`;
      byRoute.set(key, [...(byRoute.get(key) ?? []), r]);
    }
    const missing: string[] = [];
    for (const h of javaHandlers()) {
      const required = requiredInQuery(h);
      if (required.length === 0) continue;
      for (const row of byRoute.get(`${h.verb} ${h.pattern}`) ?? []) {
        for (const name of required) {
          if (row.keys.includes(name)) continue;
          missing.push(`${h.verb} ${h.pattern} binds ${name} as required and ${row.site.file} ${
            row.unresolved.length ? "sends a query this reader cannot follow" : "does not send it"}`);
        }
      }
    }
    expect(missing).toEqual([]);
  });

  it("the queries this gate cannot read are written down, with a reason each", () => {
    expect(unreadableQueries()).toEqual(["GET /jobs"].sort());
    Object.entries(UNREADABLE_QUERIES).forEach(([site, why]) =>
      expect(why, `${site} needs a reason, not a blank`).not.toBe(""));
    for (const [site, gate] of Object.entries(COVERED_ELSEWHERE)) {
      expect(UNREADABLE_QUERIES, `${site} is exempted without being unreadable`).toHaveProperty(site);
      const source = readFileSync(gate.file, "utf8");
      for (const marker of gate.markers) {
        expect(source, `${site} claims ${String(gate.file)} no longer covers it`).toContain(marker);
      }
    }
  });

  it("reads the queries it claims to read", () => {
    const rows = queryRows();
    // 13 call sites append a query and 15 distinct (route, parameter) pairs ride on them, measured.
    // A reader that stopped understanding `api.get`'s second argument would satisfy every rule
    // above by finding no queries at all, so the inventory itself has to be non-trivial.
    expect(rows.length).toBeGreaterThanOrEqual(12);
    const pairs = new Set(
      rows
        .filter((r) => !r.unresolved.length)
        .flatMap((r) => r.keys.map((k) => `${r.site.verb} ${r.pattern} ${k}`))
    );
    expect(pairs.size).toBeGreaterThanOrEqual(14);
    // Which routes more than one caller reaches, measured: the required-parameter rule is written
    // per call site, and that distinction only exists where a route has two of them. `GET /search`
    // is answered by both the ⌘K palette and the global-search hook, so a fold that merged the two
    // would still satisfy the rule with one caller's parameters while the other got a 400.
    const routes = rows.map((r) => `${r.site.verb} ${r.pattern}`);
    expect([...new Set(routes.filter((k, i) => routes.indexOf(k) !== i))].sort()).toEqual([
      "GET /search",
    ]);
    // one handler walk answers both gates, so a route cannot exist for one rule and not the other
    const handlers = javaHandlers();
    expect(new Set(handlers.map((h) => `${h.verb} ${h.pattern}`)).size).toBe(handlers.length);
    expect(handlers.flatMap((h) => h.unparsed)).toEqual([]);
    const bound = handlers.flatMap((h) => h.params);
    expect(bound.length).toBe(41);
    // 41 parameters in 19 distinct names, measured: the reader's whole answer rather than a spot
    // check, so a signature shape it stops understanding shrinks this set instead of passing quiet
    // (#225 retired `limit` from `/activity/runs`, which now pages like every other list route;
    // 19.2 brought the name back for `GET /ingestion/runs` as a newest-N history, and 19.5 retired
    // it again -- the runs panel pages, so the route binds page/size like every other list)
    expect(new Set(bound.map((p) => p.name))).toEqual(
      new Set([
        "agent", "company", "documentId", "file", "kind", "kinds", "locale",
        "location", "maxSalary", "minSalary", "page", "q", "remote", "resumeId", "size",
        "skills", "sort", "status", "title",
      ])
    );
    // six of them spell the name Spring matches on inside the annotation, so the reader's attribute
    // path is exercised by real source rather than by the variable name that happens to agree
    expect(bound.filter((p) => p.spelledInAttribute).map((p) => p.name).sort()).toEqual([
      "file", "file", "locale", "maxSalary", "minSalary", "resumeId",
    ]);
    // The whole answer of the helper the required-parameter rule consumes, route-qualified. Without
    // this the rule would be green because it found nothing to ask for — and the multipart
    // exclusion would be green because nothing exercises it, which is how a guard that stops
    // mattering would keep passing as if it did.
    expect(javaHandlers()
      .flatMap((h) => requiredInQuery(h).map((n) => `${h.verb} ${h.pattern} ${n}`))
      .sort())
      .toEqual(["GET /resume-versions resumeId", "GET /search q"]);
    expect(javaHandlers()
      .flatMap((h) => h.params.filter((p) => p.required && p.fromBody).map((p) => `${h.verb} ${h.pattern} ${p.name}`))
      .sort())
      .toEqual(["POST /knowledge/documents file", "POST /resumes/upload file"]);
    ["GET /activity/runs page", "GET /activity/runs size",
      "GET /applications status", "GET /applications page",
      "GET /companies q", "GET /resume-versions resumeId",
      // the citation deep link, named as a pair: the browser sends this key and this handler binds it
      "GET /knowledge/sources documentId"].forEach((p) => expect(pairs).toContain(p));
    // the bookmark list is not paged by the server, so it must not arrive here carrying a page size
    expect([...pairs].some((p) => p.startsWith("GET /jobs/saved"))).toBe(false);
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
