"use client";

import * as React from "react";

/**
 * Reveal — a scroll-triggered entrance wrapper.
 *
 * The element lifts + fades in the first time it enters the viewport. The
 * animation is purely additive: the visible state is `opacity: 1` and the
 * hidden state is set in CSS (`.reveal-in`), so a reader with reduced motion or
 * no IntersectionObserver support sees the content immediately — the
 * `prefers-reduced-motion` rule in globals.css forces `.reveal-in` visible.
 *
 * `delay` staggers siblings: pass 0/80/160… to cascade a row of cards.
 */
type RevealProps = React.HTMLAttributes<HTMLDivElement> & {
  as?: keyof React.JSX.IntrinsicElements;
  delay?: number;
  once?: boolean;
};

export function Reveal({
  as: Tag = "div",
  delay = 0,
  once = true,
  className = "",
  children,
  style,
  ...rest
}: RevealProps) {
  const ref = React.useRef<HTMLElement | null>(null) as React.MutableRefObject<HTMLElement | null>;
  const [visible, setVisible] = React.useState(false);

  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduce || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }

    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setVisible(true);
            if (once) io.disconnect();
          } else if (!once) {
            setVisible(false);
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" }
    );
    io.observe(el);
    return () => io.disconnect();
  }, [once]);

  const Component = Tag as React.ElementType;
  return (
    <Component
      ref={ref}
      className={`reveal-in ${visible ? "is-visible" : ""} ${className}`.trim()}
      style={delay ? ({ ["--reveal-delay" as string]: `${delay}ms`, ...style } as React.CSSProperties) : style}
      {...rest}
    >
      {children}
    </Component>
  );
}
