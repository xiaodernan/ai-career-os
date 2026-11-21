"use client";

import * as React from "react";
import { BookOpenText, Search } from "lucide-react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { SectionHeading } from "@/components/common/export-buttons";
import { SourceChip } from "@/components/ai/source-chip";
import { useRagAnswer } from "@/lib/hooks/knowledge-answer";
import type { Evidence } from "@/lib/api/types";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * Ask your evidence (the grounded-answer bridge).
 *
 * The ai-service runs a bounded StateGraph — retrieve → answer (LLM) → verify
 * (deterministic citation check) → render. This card is the missing FRONT DOOR to
 * that engine: until now it was a fully-built capability no screen reached. The
 * answer's inline [n] markers are rendered as SourceChips whose title comes from
 * the verified citation list; the app never invents a citation the engine did not
 * return. An empty/quiet engine renders the honest empty sentence, not a guess.
 */
const MARKER = /\[(\d+)\]/g;

function AnswerWithMarkers({
  text,
  citations,
  unknownLabel,
}: {
  text: string;
  citations: readonly Evidence[];
  unknownLabel: string;
}) {
  const nodes: React.ReactNode[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  MARKER.lastIndex = 0;
  while ((m = MARKER.exec(text)) !== null) {
    if (m.index > last) nodes.push(text.slice(last, m.index));
    const n = Number(m[1]);
    const ev = citations[n - 1];
    nodes.push(
      <SourceChip
        key={`${m.index}-${m[1]}`}
        index={n}
        docTitle={ev?.source?.docTitle ?? unknownLabel}
        section={ev?.source?.path?.slice(-1)[0]}
      />
    );
    last = m.index + m[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return <p className="whitespace-pre-wrap text-sm leading-relaxed text-foreground/90">{nodes}</p>;
}

export function AskKnowledgeCard() {
  const { t } = useLocale();
  const rag = useRagAnswer();
  const [query, setQuery] = React.useState("");

  const submit = React.useCallback(() => {
    const q = query.trim();
    if (!q || rag.isPending) return;
    rag.mutate({ query: q, contextSummary: "knowledge page" });
  }, [query, rag]);

  const result = rag.data;
  const citations = result?.citations ?? [];
  const asked = rag.isSuccess || rag.isError;

  return (
    <Card>
      <CardHeader className="pb-3">
        <SectionHeading
          eyebrow={t("eyebrows.reviewerAgent")}
          icon={<BookOpenText className="size-4" aria-hidden />}
          title={t("knowledge.ragAskTitle")}
          description={t("knowledge.ragAskDescription")}
        />
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label htmlFor="rag-query">{t("knowledge.ragAskLabel")}</Label>
          <Textarea
            id="rag-query"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t("knowledge.ragAskPlaceholder")}
            rows={2}
            maxLength={4000}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                submit();
              }
            }}
          />
        </div>
        <Button
          type="button"
          size="sm"
          variant="ai"
          onClick={submit}
          disabled={!query.trim() || rag.isPending}
          aria-label={t("knowledge.ragAskAction")}
          title={t("knowledge.ragAskAction")}
        >
          <Search aria-hidden className="size-4" />
          {rag.isPending ? t("knowledge.ragAskWorking") : t("knowledge.ragAskAction")}
        </Button>

        {rag.isPending && (
          <p className="text-xs text-muted-foreground">{t("knowledge.ragAskWorking")}</p>
        )}
        {asked && !rag.isPending && result?.answer && (
          <div className="space-y-3 rounded-xl border border-primary/15 bg-primary/[0.04] p-4">
            <AnswerWithMarkers
              text={result.answer}
              citations={citations}
              unknownLabel={t("knowledge.ragCitationUnknown")}
            />
            {citations.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-2xs font-semibold uppercase tracking-widest text-muted-foreground">
                  {t("knowledge.ragCitationsLabel")}
                </p>
                <ul className="space-y-1">
                  {citations.map((ev, i) => (
                    <li key={`${ev.chunkIds?.[0] ?? i}`} className="flex gap-2 text-xs">
                      <span className="font-mono text-primary">[{i + 1}]</span>
                      <span className="min-w-0 text-muted-foreground">
                        <span className="font-medium text-foreground/80">
                          {ev.source?.docTitle ?? t("knowledge.ragCitationUnknown")}
                        </span>
                        {" — "}
                        <span className="line-clamp-2">{ev.quote}</span>
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
        {asked && !rag.isPending && !result?.answer && (
          <p className="text-xs leading-relaxed text-muted-foreground">
            {t("knowledge.ragAskEmpty")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
