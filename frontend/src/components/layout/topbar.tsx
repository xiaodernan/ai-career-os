"use client";

import * as React from "react";
import { LogOut, Search, Settings as SettingsIcon, User as UserIcon } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ThemeToggle } from "@/components/common/theme-toggle";
import { useCommandPalette } from "@/components/common/command-palette";
import { MobileSidebar } from "./sidebar";
import { useLogout, useUser } from "@/lib/hooks/auth";
import { useLocale } from "@/lib/i18n/locale-context";
import { titleForPath } from "./nav";
import { usePathname } from "next/navigation";

function PlatformKeyHint() {
  const [isMac, setIsMac] = React.useState(true);
  React.useEffect(() => {
    setIsMac(/Mac|iPhone|iPad/i.test(navigator.platform || navigator.userAgent));
  }, []);
  return <kbd aria-hidden className="font-sans">{isMac ? "⌘" : "Ctrl "}</kbd>;
}

export function Topbar() {
  const pathname = usePathname();
  const { t } = useLocale();
  const { open } = useCommandPalette();
  const { data: user } = useUser();
  const logout = useLogout();

  const initials = (user?.displayName || user?.email || "?")
    .split(/[\s@._-]+/)
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <header className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b border-border/70 bg-background/80 px-4 backdrop-blur-md supports-[backdrop-filter]:bg-background/65 sm:px-6">
      <MobileSidebar>
        <div className="border-t border-sidebar-border p-3">
          <ThemeToggle className="w-full justify-start gap-2" />
        </div>
      </MobileSidebar>
      <div className="min-w-0 flex-1">
        <h2 className="truncate text-sm font-semibold">{titleForPath(pathname, t)}</h2>
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={open}
        aria-label={t("chrome.openCommandPalette")}
        className="hidden h-8 w-52 items-center justify-between px-2.5 text-muted-foreground sm:flex lg:w-60"
      >
        <span className="flex items-center gap-2">
          <Search className="size-3.5" aria-hidden />
          <span className="text-xs">{t("chrome.commandPalettePlaceholder")}</span>
        </span>
        <span className="rounded-md border border-border bg-muted px-1.5 text-2xs text-muted-foreground">
          <PlatformKeyHint />K
        </span>
      </Button>
      <Button
        variant="ghost"
        size="icon-sm"
        onClick={open}
        aria-label={t("chrome.openCommandPalette")}
        className="sm:hidden"
      >
        <Search aria-hidden />
      </Button>

      <ThemeToggle />

      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            aria-label={t("chrome.accountMenu")}
            className="rounded-lg outline-none focus-visible:ring-[3px] focus-visible:ring-ring/35"
          >
            <Avatar className="size-8 ring-1 ring-border">
              {user?.avatarUrl && <AvatarImage src={user.avatarUrl} alt="" />}
              <AvatarFallback className="bg-primary/10 text-xs font-semibold text-primary">
                {initials}
              </AvatarFallback>
            </Avatar>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" sideOffset={8} className="w-60">
          <DropdownMenuLabel className="font-normal">
            <p className="truncate text-sm font-medium">{user?.displayName ?? "Signed in"}</p>
            <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem asChild>
            <Link href="/settings" className="flex items-center gap-2">
              <UserIcon aria-hidden />
              {t("chrome.profileAndPreferences")}
            </Link>
          </DropdownMenuItem>
          <DropdownMenuItem asChild>
            <Link href="/settings" className="flex items-center gap-2">
              <SettingsIcon aria-hidden />
              {t("chrome.settings")}
            </Link>
          </DropdownMenuItem>
          <Separator className="my-1" />
          <DropdownMenuItem
            variant="destructive"
            disabled={logout.isPending}
            onSelect={() => logout.mutate()}
            className="gap-2"
          >
            <LogOut aria-hidden />
            {logout.isPending ? "Signing out…" : "Log out"}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
