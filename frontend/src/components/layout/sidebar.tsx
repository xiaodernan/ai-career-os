"use client";

import * as React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Globe, PanelLeftClose, PanelLeftOpen, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { NAV_ITEMS } from "./nav";
import { useLocale } from "@/lib/i18n/locale-context";
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
  return (
    <TooltipProvider delayDuration={200}>
      <nav
        aria-label="Main navigation"
        className="flex min-h-0 flex-1 flex-col gap-0.5 overflow-y-auto px-2 py-2"
      >
        {NAV_ITEMS.map((item) => {
          const active = pathname === item.href || pathname.startsWith(`${item.href}/`);
          // The English label is the fallback: a key the table does not carry
          // answers the English name rather than the key itself.
          const label = item.labelKey ? t(item.labelKey) : item.label;
          const link = (
            <Link
              key={item.href}
              href={item.href}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={cn(
                "group flex h-9 w-full items-center gap-2.5 rounded-lg px-2.5 text-sm font-medium transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-ring/35",
                collapsed && "justify-center px-0",
                active
                  ? "bg-primary/10 text-primary dark:bg-primary/15"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <item.icon className="size-4 shrink-0" aria-hidden />
              {!collapsed && <span className="truncate">{label}</span>}
              {!collapsed && active && (
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
  return (
    <Link
      href="/dashboard"
      className="flex h-14 shrink-0 items-center gap-2 border-b border-sidebar-border px-4 outline-none focus-visible:ring-[3px] focus-visible:ring-ring/35 rounded-lg"
      aria-label="AI Career OS — go to dashboard"
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
  const { locale, setLocale } = useLocale();

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
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setLocale(locale === "en" ? "zh" : "en")}
          aria-label={locale === "en" ? "Switch to Chinese" : "Switch to English"}
          className={cn("w-full text-muted-foreground", collapsed && "px-0")}
        >
          <Globe aria-hidden />
          {!collapsed && <span>{locale === "en" ? "中文" : "EN"}</span>}
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={toggleCollapsed}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className={cn("w-full text-muted-foreground", collapsed && "px-0")}
        >
          {collapsed ? <PanelLeftOpen aria-hidden /> : <PanelLeftClose aria-hidden />}
          {!collapsed && <span>Collapse</span>}
        </Button>
      </div>
    </aside>
  );
}

export function MobileSidebar({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = React.useState(false);
  return (
    <Sheet open={open} onOpenChange={setOpen}>
      <SheetTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label="Open navigation menu" className="lg:hidden">
          <Menu aria-hidden />
        </Button>
      </SheetTrigger>
      <SheetContent side="left" className="w-64 gap-0 bg-sidebar p-0 text-sidebar-foreground">
        <SheetHeader className="border-b border-sidebar-border px-0">
          <SheetTitle asChild>
            <span className="sr-only">Navigation</span>
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
