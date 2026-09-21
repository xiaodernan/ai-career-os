import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { Slot } from "radix-ui";
import { Loader2 } from "lucide-react";

/**
 * AI Career OS button — customized from the shadcn base.
 * Variants: primary (deep indigo accent), secondary, ghost, outline, danger, ai.
 * Sizes: xs → lg, plus icon buttons. `loading` shows a spinner and disables.
 */
const buttonVariants = cva(
  "inline-flex shrink-0 cursor-pointer items-center justify-center gap-1.5 rounded-lg text-sm font-medium whitespace-nowrap outline-none transition-[background,color,box-shadow,transform] duration-150 focus-visible:ring-[3px] focus-visible:ring-ring/35 focus-visible:ring-offset-0 active:translate-y-px disabled:pointer-events-none disabled:opacity-55 data-[state=loading]:pointer-events-none [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        primary:
          "bg-primary text-primary-foreground shadow-soft hover:bg-primary/90 focus-visible:bg-primary dark:hover:bg-primary/90",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/70 dark:hover:bg-secondary/80",
        ghost:
          "text-muted-foreground hover:bg-accent hover:text-accent-foreground dark:hover:bg-accent/60",
        outline:
          "border border-input bg-card text-foreground shadow-[0_1px_0_0_var(--border)] hover:bg-accent hover:text-accent-foreground dark:bg-input/20 dark:hover:bg-input/40",
        danger:
          "bg-destructive text-destructive-foreground shadow-soft hover:bg-destructive/90 focus-visible:ring-destructive/30",
        /** AI CTAs: solid accent with a subtle inner highlight + indigo glow. */
        ai: "bg-primary text-primary-foreground shadow-[0_0_0_1px_inset_rgba(255,255,255,0.14),0_2px_12px_-2px_color-mix(in_oklch,var(--primary)_45%,transparent)] hover:brightness-[1.06]",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        xs: "h-6 gap-1 rounded-md px-2 text-xs has-[>svg]:px-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-8 gap-1.5 px-3 has-[>svg]:px-2.5",
        md: "h-9 px-4 py-2 has-[>svg]:px-3",
        lg: "h-10 rounded-lg px-5 text-[0.9375rem] has-[>svg]:px-4",
        icon: "size-9",
        "icon-sm": "size-8 rounded-md [&_svg:not([class*='size-'])]:size-4",
        "icon-xs": "size-6 rounded-md [&_svg:not([class*='size-'])]:size-3.5",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends React.ComponentProps<"button">,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean;
  /** Shows a spinner, sets aria-busy and blocks interaction. */
  loading?: boolean;
}

function Button({
  className,
  variant,
  size,
  asChild = false,
  loading = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  const Comp = asChild ? Slot.Root : "button";
  const isBusy = loading;

  return (
    <Comp
      data-slot="button"
      data-variant={variant}
      data-size={size}
      data-state={isBusy ? "loading" : undefined}
      aria-busy={isBusy || undefined}
      disabled={disabled || isBusy}
      className={cn(buttonVariants({ variant, size }), isBusy && "opacity-80", className)}
      {...props}
    >
      {isBusy && !asChild && (
        <Loader2 aria-hidden className="animate-spin [&_svg:not([class*='size-'])]:size-4" />
      )}
      {children}
    </Comp>
  );
}

export { Button, buttonVariants };
