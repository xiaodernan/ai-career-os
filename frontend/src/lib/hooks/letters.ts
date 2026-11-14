import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { LetterCatalogItem } from "@/lib/api/types";

/** One letter from the gallery, read under the names `LetterCatalogItem` spells. */
export function mapLetterCatalogItem(raw: unknown): LetterCatalogItem {
  const r = (raw ?? {}) as Record<string, unknown>;
  const str = (v: unknown): string | undefined =>
    typeof v === "string" ? v : undefined;
  const num = (v: unknown): number | undefined =>
    typeof v === "number" && Number.isFinite(v) ? v : undefined;
  return {
    id: str(r.id) ?? "",
    applicationId: str(r.applicationId) ?? "",
    applicationTitle: str(r.applicationTitle) ?? "",
    companyName: str(r.companyName) ?? "",
    jobId: str(r.jobId),
    resumeVersionId: str(r.resumeVersionId),
    mode: str(r.mode),
    tone: str(r.tone),
    length: str(r.length),
    body: str(r.body) ?? "",
    createdAt: str(r.createdAt),
    updatedAt: str(r.updatedAt),
  };
}

export interface LetterCatalog {
  items: LetterCatalogItem[];
  total: number;
}

export async function fetchLetterCatalog(): Promise<LetterCatalog> {
  const body = await api.get<unknown>(endpoints.letterFile);
  const raw = (body ?? {}) as Record<string, unknown>;
  const itemsRaw = Array.isArray(raw.items) ? raw.items : [];
  const items = itemsRaw.map(mapLetterCatalogItem);
  const total = numField(raw.total) ?? items.length;
  return { items, total };
}

function numField(v: unknown): number | undefined {
  return typeof v === "number" && Number.isFinite(v) ? v : undefined;
}

export function useLetters() {
  return useQuery({
    queryKey: ["letters"],
    queryFn: fetchLetterCatalog,
  });
}
