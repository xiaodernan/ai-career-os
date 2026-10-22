"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { fail } from "@/lib/hooks/failure";
import { useLocale } from "@/lib/i18n/locale-context";
import type {
  ExportBundle,
  ImportApplied,
  ImportPlan,
  RedactedBundle,
  RenderedBundle,
} from "@/lib/api/types";

/**
 * Data portability (13.1-13.3): export a bundle, plan an idempotent re-import,
 * redact sections before sharing. Every call is a POST — the bodies carry
 * bundles, not query strings.
 *
 * The bodies are built by named helpers so the wire shape is written down in
 * one place per route instead of being spread across the call sites.
 */

/** 13.1 — the export request: one flag, and the bundle comes back whole. */
function exportBody(anonymized: boolean): { anonymized: boolean } {
  return { anonymized };
}

/** 13.2 — the import plan request: the bundle, and optionally the current state. */
function importPlanBody(bundle: unknown, existing?: unknown): { bundle: unknown; existing?: unknown } {
  return { bundle, existing };
}

/** 13.3 — the redact request: the bundle and the sections to drop. */
function redactBody(bundle: unknown, drop?: string[]): { bundle: unknown; drop?: string[] } {
  return { bundle, drop };
}

/** 13.1 — export all user data as a versioned, hashed bundle. */
export function useExportBundle() {
  return useMutation({
    mutationFn: async (anonymized: boolean) =>
      (await api.create<unknown>(endpoints.dataExport, exportBody(anonymized))) as ExportBundle,
    onError: fail("Couldn't export your data."),
  });
}

/** 13.2 — plan an idempotent re-import from a bundle. */
export function useImportPlan() {
  return useMutation({
    mutationFn: async (input: { bundle: unknown; existing?: unknown }) =>
      (await api.create<unknown>(endpoints.dataImportPlan, importPlanBody(input.bundle, input.existing))) as ImportPlan,
    onError: fail("Couldn't build the import plan."),
  });
}

/**
 * 13.2 — apply a re-import. The answer says what each section wrote and which
 * ones were left alone, so a partial restore is visible rather than reported as
 * a success.
 */
export function useImportApply() {
  return useMutation({
    mutationFn: async (bundle: unknown) =>
      (await api.create<unknown>(endpoints.dataImportApply, { bundle })) as ImportApplied,
    onError: fail("Couldn't apply the import."),
  });
}

/** 13.3 — redact sections from a bundle before sharing. */
export function useRedactBundle() {
  return useMutation({
    mutationFn: async (input: { bundle: unknown; drop?: string[] }) =>
      (await api.create<unknown>(endpoints.dataRedact, redactBody(input.bundle, input.drop))) as RedactedBundle,
    onError: fail("Couldn't redact the bundle."),
  });
}

/**
 * 13.1 — the human-readable half: a print-ready document of the bundle. The
 * HTML is self-contained, so the browser can print it straight to PDF.
 *
 * The document is written in the reader's language, so the request carries
 * it: the document is a view of the bundle, and the view is the reader's,
 * not the server's.
 */
export function useRenderBundle() {
  const { locale } = useLocale();
  return useMutation({
    mutationFn: async (input: { bundle: unknown; format?: "html" | "pdf" }) =>
      (await api.create<unknown>(endpoints.dataRender, {
        bundle: input.bundle,
        format: input.format ?? "html",
        locale,
      })) as RenderedBundle,
    onError: fail("Couldn't render the bundle."),
  });
}
