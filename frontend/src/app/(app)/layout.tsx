"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { CommandPaletteProvider } from "@/components/common/command-palette";
import { tokenStore } from "@/lib/api/token-store";
import { useUser } from "@/lib/hooks/auth";

function Splash() {
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 bg-background">
      <span className="flex size-12 animate-pulse-dot items-center justify-center rounded-xl bg-primary text-primary-foreground">
        <Sparkles className="size-6" aria-hidden />
      </span>
      <p className="font-serif text-display-sm text-muted-foreground italic">Loading your workspace…</p>
    </div>
  );
}

/**
 * Client-side route guard: v1 keeps the access token client-side
 * (architecture.md §7), so the server middleware cannot see it.
 * No session → /login; session → verify /users/me (client auto-refreshes 401).
 */
function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [hasToken, setHasToken] = React.useState<boolean | null>(null);
  const { isPending, isError } = useUser();

  React.useEffect(() => {
    const session = tokenStore.hasSession();
    setHasToken(session);
    if (!session) router.replace("/login");
  }, [router]);

  React.useEffect(() => {
    if (isError && tokenStore.hasSession() === false) router.replace("/login");
  }, [isError, router]);

  if (hasToken === null || (hasToken && isPending && !isError)) return <Splash />;
  if (!hasToken || isError) return <Splash />;
  return <>{children}</>;
}

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <CommandPaletteProvider>
        <div className="flex min-h-dvh">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <Topbar />
            <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
              <div className="animate-fade-up">{children}</div>
            </main>
          </div>
        </div>
      </CommandPaletteProvider>
    </AuthGuard>
  );
}
