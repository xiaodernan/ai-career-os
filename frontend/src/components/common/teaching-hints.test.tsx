import { describe, expect, it } from "vitest";
import type { UseQueryResult } from "@tanstack/react-query";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";
import { LocaleProvider, lookup } from "@/lib/i18n/locale-context";
import { translations } from "@/lib/i18n/translations";
import type { Page } from "@/lib/api/types";
import { ApiError } from "@/lib/api/client";
import { ErrorState } from "./error-state";
import { ModuleView } from "./module-view";
import { Pagination } from "./pagination";
import { DiffView } from "./diff-view";
import { AgentTimeline } from "@/components/ai/agent-timeline";

const HINT_KEYS = [
  "common.hintRetry", "common.hintCheckAgain", "common.hintCloseDialog",
  "common.hintCancelDialog", "common.hintConfirmDialog", "common.hintRefreshList",
  "common.hintOpenCopilot",
  "chrome.hintPreviousPage", "chrome.hintNextPage",
  "diffView.hintRejected", "ai.taskStream.hintAgentTrace", "ai.agentTimeline.hintPayload",
] as const;

function render(locale: "en" | "zh", children: React.ReactNode): string {
  return renderToStaticMarkup(
    <LocaleProvider initialLocale={locale} table={translations[locale]}>
      {children}
    </LocaleProvider>,
  );
}

function source(path: string): string {
  return readFileSync(new URL(path, import.meta.url), "utf8");
}

function moduleQuery(
  overrides: Partial<UseQueryResult<Page<{ id: string }>, unknown>> = {}
): UseQueryResult<Page<{ id: string }>, unknown> {
  return {
    data: { items: [{ id: "row-1" }], total: 1, page: 0, size: 20 },
    isPending: false,
    isError: false,
    isFetching: false,
    error: null,
    refetch: () => undefined,
    ...overrides,
  } as UseQueryResult<Page<{ id: string }>, unknown>;
}

function renderModule(
  query: UseQueryResult<Page<{ id: string }>, unknown>,
  ctaHref?: string
): string {
  return render("en", (
    <ModuleView
      title="Records"
      description="Stored records"
      query={query}
      emptyHint={{ title: "Nothing kept", description: "Keep a record to begin." }}
      ctaHref={ctaHref}
      renderItem={(item) => <p key={item.id}>{item.id}</p>}
    />
  ));
}

describe("shared teaching hints", () => {
  it("defines all twelve consequences in both languages", () => {
    expect(HINT_KEYS).toHaveLength(12);
    for (const locale of ["en", "zh"] as const) {
      for (const key of HINT_KEYS) {
        expect(lookup(translations[locale], key), `${locale}: ${key}`).toBeTruthy();
      }
    }
  });

  it("teaches retry, both page directions and the two disclosure controls", () => {
    for (const locale of ["en", "zh"] as const) {
      expect(render(locale, <ErrorState onRetry={() => undefined} />).match(/data-slot="tooltip-trigger"/g)).toHaveLength(1);
      expect(render(locale, <Pagination page={1} size={20} total={80} onPageChange={() => undefined} />).match(/data-slot="tooltip-trigger"/g)).toHaveLength(2);
      const diff = render(locale, <DiffView accepted={[]} rejected={[{ id: "r1", section: "Bullet", after: "A claim", reason: "No evidence" }]} />);
      expect(diff.match(/data-slot="tooltip-trigger"/g)).toHaveLength(1);
      expect(diff).toContain('aria-expanded="false"');
      const timeline = render(locale, <AgentTimeline events={[
        { id: "with", kind: "tool_result", label: "With payload", payload: { ok: true } },
        { id: "without", kind: "step_start", label: "Without payload" },
      ]} />);
      expect(timeline.match(/data-slot="tooltip-trigger"/g)).toHaveLength(1);
      expect(timeline).toContain("disabled");
    }
  });

  it("teaches module refresh, missing-route recovery and the default Copilot door", () => {
    expect(renderModule(moduleQuery()).match(/data-slot="tooltip-trigger"/g)).toHaveLength(1);
    const missing = renderModule(moduleQuery({
      isError: true,
      error: new ApiError("NOT_FOUND", "Missing route", 404),
    }));
    expect(missing.match(/data-slot="tooltip-trigger"/g)).toHaveLength(2);
    expect(missing).toContain("Check again");
    const empty = renderModule(moduleQuery({
      data: { items: [], total: 0, page: 0, size: 20 },
    }), "/copilot");
    expect(empty.match(/data-slot="tooltip-trigger"/g)).toHaveLength(2);
    expect(empty).toContain('href="/copilot"');
  });

  it("keeps loading, dialog and missing-route state on boxless anchors", () => {
    expect(source("./error-state.tsx")).toContain('<Hint anchor="span" label={t("common.hintRetry")}>');
    expect(source("./pagination.tsx")).toContain('<Hint anchor="span" label={t("chrome.hintPreviousPage")}>');
    expect(source("./pagination.tsx")).toContain('<Hint anchor="span" label={t("chrome.hintNextPage")}>');
    expect(source("./query-boundary.tsx")).toContain('<Hint anchor="span" label={t("common.hintCheckAgain")}>');
    const confirm = source("./confirm-dialog.tsx");
    expect(confirm).toContain('<Hint anchor="span" label={resolvedCancelHint}>');
    expect(confirm).toContain('<Hint anchor="span" label={resolvedConfirmHint}>');
    expect(source("../ui/dialog.tsx")).toContain('<Hint anchor="span" label={t("common.hintCloseDialog")}>');
    expect(source("../ai/task-stream.tsx")).toContain('label={t("ai.taskStream.hintAgentTrace")}');
    const moduleSource = source("./module-view.tsx");
    expect(moduleSource).toContain('<Hint anchor="span" label={t("common.hintRefreshList")}>');
    expect(moduleSource).toContain('<Hint anchor="span" label={t("common.hintCheckAgain")}>');
    expect(moduleSource).toContain('<Hint label={t("common.hintOpenCopilot")}>');
  });
});
