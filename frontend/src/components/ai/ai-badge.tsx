import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * AIBadge — the quiet pill marking any AI-generated surface.
 * Never shouty: indigo tint, sparkle glyph, optional label.
 */
export function AIBadge({
  label = "AI",
  className,
  ...props
}: { label?: string } & React.ComponentProps<"span">) {
  const { t } = useLocale();
  return (
    <Badge variant="ai" className={cn("px-1.5 text-2xs font-medium tracking-wide uppercase", className)} {...props}>
      <Sparkles aria-hidden />
      {label}
      <span className="sr-only">: {t("ai.generated")}</span>
    </Badge>
  );
}
