import { cn } from "cn"

/** Skeleton with the shared shimmer band (see globals.css `@utility shimmer`). */
function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("shimmer rounded-lg", className)}
      {...props}
    />
  )
}

export { Skeleton }
