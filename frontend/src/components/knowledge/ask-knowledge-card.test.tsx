import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/i18n/locale-context", () => ({
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
});
