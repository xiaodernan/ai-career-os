import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { readFileSync } from "node:fs";
import { lookup } from "@/lib/i18n/locale-context";
import { translations } from "@/lib/i18n/translations";

vi.mock("@/lib/i18n/locale-context", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/i18n/locale-context")>()),
  useLocale: () => ({
    locale: "en",
    t: (key: string) => `[${key}]`,
    setLocale: () => undefined,
  }),
}));

vi.mock("@/lib/hooks/knowledge-answer", () => ({
  useRagAnswer: () => ({ mutate: () => undefined, isPending: false, isSuccess: false, isError: false, data: undefined }),
}));

import { AskKnowledgeCard } from "./ask-knowledge-card";

describe("AskKnowledgeCard", () => {
  it("renders the grounded-question form with locale-keyed copy", () => {
    const html = renderToStaticMarkup(<AskKnowledgeCard />);
    expect(html).toContain("[knowledge.ragAskTitle]");
    expect(html).toContain("[knowledge.ragAskAction]");
    expect(html).toContain("rag-query");
  });

  it("teaches the question box and the send action in both languages", () => {
    const source = readFileSync(new URL("./ask-knowledge-card.tsx", import.meta.url), "utf8");
    for (const locale of ["en", "zh"] as const) {
      for (const key of ["knowledge.ragQueryHint", "knowledge.ragAskHint"]) {
        expect(lookup(translations[locale], key), `${key} missing from ${locale}`).toBeTruthy();
        expect(source).toContain(`t("${key}")`);
      }
    }
    const html = renderToStaticMarkup(<AskKnowledgeCard />);
    expect(html.match(/data-slot="tooltip-trigger"/g)).toHaveLength(2);
    expect(html).toContain('id="rag-query"');
  });
});
