"use client";

import * as React from "react";
import { Check, Copy, Download } from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Button, type ButtonProps } from "@/components/ui/button";
import { copyText, downloadText } from "@/lib/format";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * Copy / download affordances for AI artifacts. Both operate on real text the
 * backend returned — never on a placeholder.
 */

export function CopyButton({
  text,
  label = "Copy",
  size = "sm",
  variant = "outline",
  className,
}: {
  text: string;
  label?: string;
  size?: ButtonProps["size"];
  variant?: ButtonProps["variant"];
  className?: string;
}) {
  const { t } = useLocale();
  const [copied, setCopied] = React.useState(false);
  if (!text) return null;
  return (
    <Button
      type="button"
      variant={variant}
      size={size}
      className={className}
      onClick={async () => {
        const ok = await copyText(text);
        if (ok) {
          setCopied(true);
          toast.success(t("common.copiedToClipboard"));
          setTimeout(() => setCopied(false), 1600);
        } else {
          toast.error(t("common.clipboardBlocked"));
        }
      }}
      aria-label={copied ? t("common.copied") : label}
    >
      {copied ? <Check aria-hidden className="text-success" /> : <Copy aria-hidden />}
      {copied ? t("common.copied") : label}
    </Button>
  );
}

export function DownloadButton({
  text,
  filename,
  label = "Download",
  mime,
  size = "sm",
  variant = "outline",
  className,
}: {
  text: string;
  filename?: string;
  label?: string;
  mime?: string;
  size?: ButtonProps["size"];
  variant?: ButtonProps["variant"];
  className?: string;
}) {
  const { t } = useLocale();
  if (!text) return null;
  const isMarkdown = Boolean(mime?.includes("markdown")) || filename?.endsWith(".md");
  const name = filename ?? `careeros-${isMarkdown ? "document.md" : "document.txt"}`;
  return (
    <Button
      type="button"
      variant={variant}
      size={size}
      className={className}
      onClick={() => {
        downloadText(name, text, mime ?? (isMarkdown ? "text/markdown;charset=utf-8" : "text/plain;charset=utf-8"));
        toast.success(t("common.fileSaved"));
      }}
      aria-label={label}
    >
      <Download aria-hidden />
      {label}
    </Button>
  );
}

/* ------------------------------------------------------------------ */
/* SectionHeading — consistent eyebrow + title + action inside cards    */
/* ------------------------------------------------------------------ */

export function SectionHeading({
  eyebrow,
  title,
  description,
  action,
  icon,
  className,
}: {
  eyebrow?: React.ReactNode;
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-3", className)}>
      <div className="min-w-0 space-y-0.5">
        {eyebrow && (
          <p className="text-2xs font-medium tracking-wide text-muted-foreground uppercase">{eyebrow}</p>
        )}
        <h3 className="flex items-center gap-2 text-sm font-semibold text-foreground">
          {icon && <span className="text-muted-foreground [&_svg]:size-4">{icon}</span>}
          {title}
        </h3>
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </div>
      {action && <div className="flex shrink-0 items-center gap-1.5">{action}</div>}
    </div>
  );
}
