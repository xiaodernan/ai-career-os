"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Sparkles } from "lucide-react";
import { Sidebar } from "@/components/layout/sidebar";
import { Topbar } from "@/components/layout/topbar";
import { CommandPaletteProvider } from "@/components/common/command-palette";
import { SkipLink } from "@/components/layout/skip-link";
import { tokenStore } from "@/lib/api/token-store";
import { useUser } from "@/lib/hooks/auth";
import { readStoredLocale, useLocale } from "@/lib/i18n/locale-context";
import { decideLocale, saveLocalePreference } from "@/lib/i18n/locale-preference";

function Splash() {
  const { t } = useLocale();
  return (
    <div className="flex h-dvh flex-col items-center justify-center gap-4 bg-background">
      <span className="flex size-12 animate-pulse-dot items-center justify-center rounded-xl bg-primary text-primary-foreground">
        <Sparkles className="size-6" aria-hidden />
      </span>
      <p className="font-serif text-display-sm text-muted-foreground italic">
        {t("loading.workspace")}
      </p>
    </div>
  );
}

/**
 * The browser and the account agreeing on one language (roadmap 21.4).
 *
 * The cookie paints this browser; the account is what the nightly letter can read.
 * This effect keeps the two honest: an explicit switch here is pushed to the account,
 * and a browser that never chose adopts the account's language. The rules live in
 * `decideLocale`; this is only the effect that applies one.
 */
function AccountLocale() {
  const { locale, adoptLocale } = useLocale();
  const { data: user } = useUser();
  // The /me answer carries the account's language; the shared account type predates it,
  // so the one name this effect reads is named here rather than widened everywhere.
  const account = (user as { locale?: unknown } | undefined)?.locale;

  React.useEffect(() => {
    const decision = decideLocale(account, locale, readStoredLocale());
    if (decision.action === "adopt") {
      adoptLocale(decision.locale);
    } else if (decision.action === "save") {
      void saveLocalePreference(decision.locale).catch(() => {
        /* the cookie still speaks for this browser; the next switch tries again */
      });
    }
  }, [account, locale, adoptLocale]);

  return null;
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
      <AccountLocale />
      <CommandPaletteProvider>
        <SkipLink />
        <div className="flex min-h-dvh">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <Topbar />
            <main
              id="main"
              tabIndex={-1}
              className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8"
            >
              <div className="animate-fade-up">{children}</div>
            </main>
          </div>
        </div>
      </CommandPaletteProvider>
    </AuthGuard>
  );
}
