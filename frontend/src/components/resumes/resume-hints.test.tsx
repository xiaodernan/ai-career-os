import { describe, expect, it, vi } from "vitest";
import { readFileSync } from "node:fs";
import { renderToStaticMarkup } from "react-dom/server";

vi.mock("@/lib/hooks/actions", () => ({
  RESUME_ACCEPT: [".pdf", ".docx", ".txt"],
  RESUME_MAX_BYTES: 10 * 1024 * 1024,
  validateResumeFile: () => null,
  useUploadResume: () => ({ mutate: vi.fn(), isPending: false }),
  useResumeImpression: () => ({ mutate: vi.fn(), isPending: false, isSuccess: false, isError: false }),
}));

import { LocaleProvider, lookup } from "@/lib/i18n/locale-context";
import { translations } from "@/lib/i18n/translations";
import { UploadDropzone } from "./upload-dropzone";
import { ResumeImpressionCard } from "./resume-impression-card";

const HINT_KEYS = [
  "resumes.hintOpen", "resumes.hintDelete", "resumes.hintDeleteConfirm", "resumes.hintDeleteCancel",
  "resumes.detail.hintBack", "resumes.detail.hintOriginalFile", "resumes.detail.hintParseNow",
  "resumes.detail.hintReParse", "resumes.detail.hintPrint", "resumes.detail.hintSetCurrent",
  "resumes.detail.hintKnowledge", "resumes.detail.hintExportJson", "resumes.detail.hintProfileLink",
  "resumes.detail.hintRepo", "resumes.detail.hintImpression", "upload.hintDropzone",
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

describe("resume teaching hints", () => {
  it("defines all sixteen consequences in both languages", () => {
    expect(HINT_KEYS).toHaveLength(16);
    for (const locale of ["en", "zh"] as const) {
      for (const key of HINT_KEYS) {
        expect(lookup(translations[locale], key), `${locale}: ${key}`).toBeTruthy();
      }
    }
  });

  it("attaches one teaching trigger to upload and the grounded impression", () => {
    for (const locale of ["en", "zh"] as const) {
      const upload = render(locale, <UploadDropzone />);
      expect(upload.match(/data-slot="tooltip-trigger"/g)).toHaveLength(1);
      expect(upload).toContain('role="button"');
      expect(upload).toContain('type="file"');
      const impression = render(locale, <ResumeImpressionCard resumeId="r1" hasScore />);
      expect(impression.match(/data-slot="tooltip-trigger"/g)).toHaveLength(1);
      expect(impression).toContain('class="contents"');
    }
  });

  it("keeps loading and version controls outside Tooltip state ownership", () => {
    const detail = source("../../app/(app)/resumes/[id]/page.tsx");
    for (const key of ["hintOriginalFile", "hintPrint", "hintSetCurrent"]) {
      expect(detail).toMatch(new RegExp(`<Hint anchor="span"[^>]*label=\\{t\\("resumes\\.detail\\.${key}"\\)\\}>`));
    }
    expect(detail).toContain('<Hint anchor="span" label={t(structured ? "resumes.detail.hintReParse" : "resumes.detail.hintParseNow")}>');
    for (const key of ["hintBack", "hintKnowledge", "hintExportJson", "hintProfileLink", "hintRepo"]) {
      expect(detail).toContain(`t("resumes.detail.${key}")`);
    }
    expect(source("./resume-impression-card.tsx")).toContain('<Hint anchor="span" label={t("resumes.detail.hintImpression")}>');
  });

  it("names the exact resume deletion consequence in the list and confirmation", () => {
    const page = source("../../app/(app)/resumes/page.tsx");
    expect(page).toContain('label={t("resumes.hintDelete")}');
    expect(page).toContain('cancelHint={t("resumes.hintDeleteCancel")}');
    expect(page).toContain('confirmHint={t("resumes.hintDeleteConfirm")}');
    expect(page).not.toContain("chrome.deleteHint");
  });
});
