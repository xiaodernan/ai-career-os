"use client";

import { useMutation } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { fail } from "@/lib/hooks/failure";
import type { ExportBundle, ImportPlan, RedactedBundle } from "@/lib/api/types";

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

/** 13.3 — redact sections from a bundle before sharing. */
export function useRedactBundle() {
  return useMutation({
    mutationFn: async (input: { bundle: unknown; drop?: string[] }) =>
      (await api.create<unknown>(endpoints.dataRedact, redactBody(input.bundle, input.drop))) as RedactedBundle,
    onError: fail("Couldn't redact the bundle."),
  });
}
