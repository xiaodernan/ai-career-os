import { describe, expect, it } from "vitest";
import * as React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { LocaleProvider, translate, useLocale } from "./locale-context";
import { installedTable } from "./installed-tables";

/**
 * 358: the reader's language ships with the HTML, not with the JavaScript.
 *
 * The bilingual tables rode in the client bundle for every route, whatever language it
 * painted -- ~152 kB gzip of the two, and the reason six routes crossed the bundle
 * budget on shared table alone. The server now hands the reader's own table to the
 * provider, and the other one is a chunk only a reader who switches ever downloads.
 *
 * These are the claims that keep it honest:
 *
 * - a table handed in is the table that renders (the seam works at all);
 * - a provider with no table falls back to the installed ones rather than printing keys,
 *   because a test renders the provider directly with no server behind it;
 * - no shipped module imports a table statically, which is the whole point -- the gate
 *   is a walk of the source, not a measurement of a build;
 * - `translate` outside a render still answers in the language the cookie names.
 */

function Probe() {
  const { locale, t } = useLocale();
  return <span>{`${locale}|${t("nav.dashboard")}|${t("nav.nope")}`}</span>;
}

const en = installedTable("en");
const zh = installedTable("zh");

describe("the table the server hands down is the table that renders", () => {
  it("renders Chinese from the Chinese table, without reading any store", () => {
    const html = renderToStaticMarkup(
      <LocaleProvider initialLocale="zh" table={zh}>
        <Probe />
      </LocaleProvider>
    );
    expect(html).toContain("zh|仪表盘");
    expect(html).not.toContain("en|Dashboard");
  });

  it("renders English from the English table", () => {
    const html = renderToStaticMarkup(
      <LocaleProvider initialLocale="en" table={en}>
        <Probe />
      </LocaleProvider>
    );
    expect(html).toContain("en|Dashboard");
  });

  it("still answers the key itself for a name the table does not carry", () => {
    const html = renderToStaticMarkup(
      <LocaleProvider initialLocale="en" table={en}>
        <Probe />
      </LocaleProvider>
    );
    expect(html).toContain("nav.nope");
  });
});

describe("a provider with no table answers from the installed ones", () => {
  it("renders the reader's language from the tables a test installs", () => {
    // A browser always receives a table with the HTML. A test renders the provider
    // directly, so the seam has to have somewhere else to stand -- and that somewhere
    // must never be a shipped module, or the tables are back in the bundle.
    const html = renderToStaticMarkup(
      <LocaleProvider initialLocale="zh">
        <Probe />
      </LocaleProvider>
    );
    expect(html).toContain("zh|仪表盘");
  });
});

describe("no shipped module imports a table", () => {
  const here = fileURLToPath(new URL(".", import.meta.url));
  const lib = join(here, "..");
  const components = join(here, "..", "..", "components");

  const valueImport = /import\s+(?!type\b)[^;]*from\s+["'`][\./]*(en|zh)["'`]/;

  it("keeps the static import out of the client's own source", () => {
    // The claim this epic rests on, stated as a walk rather than a build measurement:
    // if a component ever imports a table again, the split is silently undone and the
    // budget gate is the only thing that would notice -- two epics later.
    const offenders: string[] = [];
    const walk = (dir: string) => {
      for (const entry of readdirSync(dir, { withFileTypes: true })) {
        const at = join(dir, entry.name);
        if (entry.isDirectory()) {
          walk(at);
          continue;
        }
        if (!/\.(ts|tsx)$/.test(entry.name)) continue;
        // `translations.ts` is the seam: the server imports both tables through it, and it
        // exports them as a type for the browser. Every other file must not name them.
        if (entry.name === "translations.ts") continue;
        if (valueImport.test(readFileSync(at, "utf8"))) offenders.push(entry.name);
      }
    };
    walk(components);
    walk(lib);

    expect(offenders, "a shipped module imports a locale table again").toEqual([]);
  });

  it("asks for the other table dynamically, which is what makes it a separate chunk", () => {
    const provider = readFileSync(join(here, "locale-context.tsx"), "utf8");
    expect(provider).toContain('import("./en")');
    expect(provider).toContain('import("./zh")');
    expect(provider).not.toMatch(/^import \{[^}]*\btranslations\b/m);
  });
});

describe("translate outside a render", () => {
  it("answers in the language the cookie names", () => {
    const scope = globalThis as unknown as { document?: { cookie: string } };
    const real = scope.document;
    scope.document = { cookie: "theme=dark; careeros.locale=zh" };
    try {
      expect(translate("errorCodes.CURRENT_PASSWORD_INCORRECT")).toBe("你输入的当前密码不对。");
    } finally {
      if (real === undefined) delete scope.document;
      else scope.document = real;
    }
  });
});
