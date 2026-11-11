"use client";

import * as React from "react";

/**
 * AuroraBackground — a decorative, animated gradient field.
 *
 * Three blurred radial blobs drift on independent slow loops over a faint
 * masked grid, behind the hero. Pure CSS animation (no JS, no images), so it
 * costs nothing on the main thread and is disabled under `prefers-reduced-motion`.
 * Marked `aria-hidden`; it carries no information.
 */
export function AuroraBackground({ className = "" }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={`aurora-bg pointer-events-none absolute inset-0 -z-10 overflow-hidden ${className}`.trim()}
    >
      <span className="aurora-blob aurora-blob-1" />
      <span className="aurora-blob aurora-blob-2" />
      <span className="aurora-blob aurora-blob-3" />
      <div className="aurora-grid" />
    </div>
  );
}
