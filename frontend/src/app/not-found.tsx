import type { Metadata } from "next";
import Link from "next/link";
import { Compass } from "lucide-react";
import { Button } from "@/components/ui/button";

export const metadata: Metadata = { title: "Page not found" };

export default function NotFound() {
  return (
    <div className="flex min-h-dvh flex-col items-center justify-center gap-6 px-6 text-center">
      <span className="flex size-12 items-center justify-center rounded-xl bg-primary/10 text-primary shadow-soft">
        <Compass className="size-6" aria-hidden />
      </span>
      <div className="max-w-md space-y-2">
        <h1 className="font-serif text-display-lg font-medium tracking-tight text-balance">
          This page is not on the map.
        </h1>
        <p className="text-sm leading-relaxed text-muted-foreground">
          The route you followed does not exist. It may have moved, or the link
          was mistyped.
        </p>
      </div>
      <Button asChild>
        <Link href="/dashboard">Back to the dashboard</Link>
      </Button>
    </div>
  );
}
