import * as React from "react";

/**
 * GradientText — animated gradient fill for an accent phrase.
 *
 * Uses the `.gradient-text` utility (moving sheen across a multi-hue gradient).
 * Decorative only; the text content is still real, selectable text.
 */
export function GradientText({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <span className={`gradient-text ${className}`.trim()}>{children}</span>;
}
