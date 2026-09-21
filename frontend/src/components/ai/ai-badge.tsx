import { Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";

/**
 * AIBadge — the quiet pill marking any AI-generated surface.
 * Never shouty: indigo tint, sparkle glyph, optional label.
 */
export function AIBadge({
  label = "AI",
  className,
  ...props
}: { label?: string } & React.ComponentProps<"span">) {
  return (
    <Badge variant="ai" className={cn("px-1.5 text-2xs font-medium tracking-wide uppercase", className)} {...props}>
      <Sparkles aria-hidden />
      {label}
      <span className="sr-only">: AI generated</span>
    </Badge>
  );
}
