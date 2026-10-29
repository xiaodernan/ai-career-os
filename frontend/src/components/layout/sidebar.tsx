"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PanelLeftClose, PanelLeftOpen, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "./nav";
import { useLocale } from "@/lib/i18n/locale-context";
import { LocaleSwitcher } from "@/components/common/locale-switcher";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Menu } from "lucide-react";
import { useNotifications } from "@/lib/hooks/resources";

const COLLAPSE_KEY = "careeros.sidebarCollapsed";

function useCollapsed() {
  const [collapsed, setCollapsed] = React.useState(false);
  React.useEffect(() => {
    try {
      setCollapsed(window.localStorage.getItem(COLLAPSE_KEY) === "1");
    } catch {
      /* ignore */
    }
  }, []);
  const toggle = React.useCallback(() => {
    setCollapsed((c) => {
      try {
        window.localStorage.setItem(COLLAPSE_KEY, c ? "0" : "1");
      } catch {
        /* ignore */
      }
      return !c;
    });
  }, []);
  return [collapsed, toggle] as const;
}

/**
 * The navigation list. Exported so a test can render it outside the shell.
 *
 * The collapsed rail shows each label in a tooltip, and Radix throws when a
 * tooltip is rendered outside a provider — so the provider lives here rather
 * than somewhere up the tree. The list is then self-contained: rendered
 * anywhere, it works.
 *
 * The notifications row carries the inbox's unread count (roadmap 29.3): the
 * inbox is synthesized from clocks, so the count is the one place the reader
 * learns a reminder came due without opening the page. In the rail the badge
 * rides the icon, and the link gets an aria-label -- with the label hidden and
 * the icon aria-hidden, the link would otherwise have no name at all.
 */
export function NavLinks({
  collapsed,
  onNavigate,
}: {
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const { t } = useLocale();
  const { data: inbox } = useNotifications();
  const unread = inbox?.unread ?? 0;
  return (
    <TooltipProvider delayDuration={200}>
      <nav
        aria-label={t("chrome.mainNavigation")}
        className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-2"
      >
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          // The English label is the fallback: a key the table does not carry
          // answers the English name rather than the key itself.
          const label = item.labelKey ? t(item.labelKey) : item.label;
          const unreadHere = item.href === "/notifications" ? unread : 0;
          const unreadText =
            unreadHere > 0 ? t("notifications.unreadBadge", { count: unreadHere }) : "";
          const link = (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              aria-label={
                collapsed ? (unreadText ? `${label}, ${unreadText}` : label) : undefined
              }
              className={cn(
                "group flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-sm font-medium transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-ring/35",
                collapsed && "justify-center px-0",
                active
                  ? "bg-primary/10 text-primary dark:bg-primary/15"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <span className="relative flex shrink-0 items-center">
                <item.icon className="size-4 shrink-0" aria-hidden />
                {collapsed && unreadHere > 0 && (
                  <span
                    aria-hidden
                    className="absolute -right-2 -top-1.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-semibold leading-none text-primary-foreground tabular-nums"
                  >
                    {unreadHere}
                  </span>
                )}
              </span>
              {!collapsed && <span className="truncate">{label}</span>}
              {!collapsed && unreadHere > 0 && (
                <span
                  aria-hidden
                  className="ml-auto flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-2xs font-semibold text-primary-foreground tabular-nums"
                >
                  {unreadHere}
                </span>
              )}
              {!collapsed && unreadText !== "" && <span className="sr-only">{unreadText}</span>}
              {!collapsed && active && unreadHere === 0 && (
                <span aria-hidden className="ml-auto size-1.5 rounded-full bg-primary" />
              )}
            </Link>
          );
          return collapsed ? (
            <Tooltip key={item.href}>
              <TooltipTrigger asChild>{link}</TooltipTrigger>
              <TooltipContent side="right">{label}</TooltipContent>
            </Tooltip>
          ) : (
            link
          );
        })}
      </nav>
    </TooltipProvider>
  );
}

function Brand({ collapsed }: { collapsed?: boolean }) {
  const { t } = useLocale();
  return (
    <Link
      href="/dashboard"
      className="flex h-14 shrink-0 items-center gap-2 border-b border-sidebar-border px-4 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/35 rounded-lg"
      aria-label={t("chrome.goToDashboard")}
    >
      <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-soft">
        <Sparkles className="size-4" aria-hidden />
      </span>
      {!collapsed && (
        <span className="font-serif text-[15px] font-semibold tracking-tight whitespace-nowrap">
          Career<span className="text-primary">OS</span>
        </span>
      )}
    </Link>
  );
}

export function Sidebar() {
  const [collapsed, toggleCollapsed] = useCollapsed();
  const { t } = useLocale();

  return (
    <aside
      className={cn(
        "sticky top-0 hidden h-dvh shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-[width] duration-200 lg:flex",
        collapsed ? "w-16" : "w-60"
      )}
    >
      <div className={cn("flex items-center", collapsed && "justify-center")}>
        <div className="min-w-0 flex-1">{collapsed ? <Brand collapsed /> : <Brand />}</div>
      </div>
      <NavLinks collapsed={collapsed} />
      <div className="border-t border-sidebar-border p-2 space-y-2">
        <LocaleSwitcher
          className={cn("w-full", collapsed && "px-0")}
          showLabel={!collapsed}
        />
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleCollapsed}
          aria-label={collapsed ? t("chrome.expandSidebar") : t("chrome.collapseSidebar")}
          className={cn("w-full text-muted-foreground", collapsed && "px-0")}
        >
          {collapsed ? <PanelLeftOpen aria-hidden /> : <PanelLeftClose aria-hidden />}
          {!collapsed && <span>{t("chrome.collapse")}</span>}
        </Button>
      </div>
    </aside>
  );
}

export function MobileSidebar({ children }: { children: React.ReactNode }) {
  const { t } = useLocale();
  const [open, setOpen] = React.useState(false);
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={t("chrome.openNavigationMenu")}
          className="lg:hidden"
        >
          <Menu aria-hidden />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64 gap-0 bg-sidebar p-0 text-sidebar-foreground">
        <SheetHeader className="border-b border-sidebar-border px-0">
          <SheetTitle asChild>
            <span className="sr-only">{t("chrome.mainNavigation")}</span>
          </SheetTitle>
          <Brand />
        </SheetHeader>
        <div className="flex min-h-0 flex-1 flex-col">
          <NavLinks onNavigate={() => setOpen(false)} />
          {children}
        </div>
      </SheetContent>
    </Sheet>
  );
}
