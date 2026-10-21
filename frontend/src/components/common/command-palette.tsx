"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from "@/components/ui/command";
import { NAV_ITEMS } from "@/components/layout/nav";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import { normalizeSearch, searchGroupNames } from "@/lib/api/normalize";
import { useLocale } from "@/lib/i18n/locale-context";
import type { SearchResults } from "@/lib/api/types";
import { FileText, Briefcase, Building2, MessageSquare, LayoutDashboard, CornerDownLeft, Loader2, type LucideIcon } from "lucide-react";

/**
 * CommandPalette — global ⌘K shell (architecture.md §3 search module).
 * Navigation group is always available; content results call the real
 * /search endpoint (debounced) and degrade gracefully when it 404s.
 * Hybrid search: gets query embedding from ai-service, then uses hybrid search
 * on /search endpoint (keyword + vector fusion via RRF).
 */

interface PaletteContextValue {
  open: () => void;
  close: () => void;
}

const CommandPaletteContext = React.createContext<PaletteContextValue | null>(null);

export function useCommandPalette(): PaletteContextValue {
  const ctx = React.useContext(CommandPaletteContext);
  if (!ctx) throw new Error("useCommandPalette must be used within <CommandPaletteProvider>");
  return ctx;
}

const RESULT_ICONS: Record<string, LucideIcon> = {
  resume: FileText,
  job: Briefcase,
  company: Building2,
  conversation: MessageSquare,
};

type SearchFn = (q: string) => Promise<SearchResults>;

// /search binds exactly one parameter; the per-group cap is the server's own.
const defaultSearch: SearchFn = async (q) =>
  normalizeSearch(await api.get<unknown>(endpoints.search, { q }));

export function CommandPaletteProvider({
  children,
  search = defaultSearch,
}: {
  children: React.ReactNode;
  /** Pluggable search implementation — swap for tests/alternate backends. */
  search?: SearchFn;
}) {
  const [isOpen, setIsOpen] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const router = useRouter();
  const { t } = useLocale();

  React.useEffect(() => {
    const down = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setIsOpen((o) => !o);
      }
    };
    window.addEventListener("keydown", down);
    return () => window.removeEventListener("keydown", down);
  }, []);

  // Debounce the query sent to the API
  const [debounced, setDebounced] = React.useState("");
  React.useEffect(() => {
    const t = setTimeout(() => setDebounced(query.trim()), 250);
    return () => clearTimeout(t);
  }, [query]);

  const enabled = isOpen && debounced.length >= 2;
  const results = useQuery({
    queryKey: ["command-search", debounced],
    queryFn: () => search(debounced),
    enabled,
  });

  const navigate = React.useCallback((href: string) => {
    setIsOpen(false);
    router.push(href);
  }, [router]);

  // Rendered as-is: the response is already the filtered set, and `shouldFilter={false}`
  // stops cmdk from filtering again. A local title match here used to delete every hit
  // that matched outside its title — jobs match the full-text index and the company name,
  // companies match industry, notes match content, conversations match message bodies,
  // applications match company_name — so the palette printed "No results." over rows the
  // server had actually returned.
  const apiGroups = results.data?.groups ?? [];

  // The navigation group, named in the reader's language.
  //
  // The palette filters on what it *shows*, so the names it filters on have
  // to be the names the reader sees: a Chinese reader typing "简历" was
  // searching the English labels and finding nothing, because the filter
  // read `item.label` while the list beside it read the same English. The
  // description is matched too, for the same reason -- and it is the
  // description that says what a page is *for*, so it is the line a reader
  // is most likely to search for.
  const navItems = React.useMemo(
    () =>
      NAV_ITEMS.map((item) => ({
        ...item,
        label: item.labelKey ? t(item.labelKey) : item.label,
        description: item.descriptionKey ? t(item.descriptionKey) : item.description,
      })),
    [t]
  );

  const navMatches = React.useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return navItems;
    return navItems.filter(
      (n) => n.label.toLowerCase().includes(q) || n.description.toLowerCase().includes(q)
    );
  }, [navItems, query]);

  const searchFailed = enabled && results.isError;

  const value = React.useMemo(
    () => ({ open: () => setIsOpen(true), close: () => setIsOpen(false) }),
    []
  );

  return (
    <CommandPaletteContext.Provider value={value}>
      {children}
      <CommandDialog
        open={isOpen}
        onOpenChange={setIsOpen}
        title={t("chrome.commandPaletteTitle")}
        description={t("chrome.commandPaletteDescription")}
        className="top-[20%] translate-y-0"
        showCloseButton={false}
      >
        <Command shouldFilter={false}>
          <CommandInput
            placeholder={t("chrome.commandPalettePlaceholder")}
            value={query}
            onValueChange={setQuery}
          />
          <CommandList>
            {results.isPending && (
              <div className="flex items-center gap-2 px-4 py-3 text-xs text-muted-foreground" role="status">
                <Loader2 className="size-3.5 animate-spin" aria-hidden />
                <span className="sr-only">{t("chrome.searching")}</span>
                {t("chrome.searching")}
              </div>
            )}
            {!results.isPending && !searchFailed && (
              <CommandEmpty>{t("chrome.noResults")}</CommandEmpty>
            )}

            {apiGroups.map((group) => (
              <CommandGroup key={group.label} heading={group.label}>
                {group.items.map((item) => {
                  const Icon = RESULT_ICONS[item.type] ?? FileText;
                  return (
                    <CommandItem
                      key={`${item.type}-${item.id}`}
                      value={item.id}
                      onSelect={() => navigate(item.href)}
                    >
                      <Icon aria-hidden />
                      <span className="min-w-0 flex-1 truncate">{item.title}</span>
                      {item.subtitle && (
                        <span className="truncate text-xs text-muted-foreground">{item.subtitle}</span>
                      )}
                      <CornerDownLeft className="size-3.5 text-muted-foreground opacity-0 group-data-[selected=true]/command-item:opacity-100" aria-hidden />
                    </CommandItem>
                  );
                })}
              </CommandGroup>
            ))}

            {apiGroups.length > 0 && <CommandSeparator />}

            <CommandGroup heading={t("chrome.goTo")}>
              {navMatches.map((item) => (
                <CommandItem
                  key={item.href}
                  value={item.href}
                  keywords={[item.description]}
                  onSelect={() => navigate(item.href)}
                >
                  <item.icon aria-hidden />
                  <span className="min-w-0 flex-1 truncate">{item.label}</span>
                  <span className="hidden truncate text-xs text-muted-foreground sm:inline">
                    {item.description}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>

            {searchFailed && (
              <div className="flex items-center justify-between gap-2 px-4 py-2 text-xs">
                <span className="text-muted-foreground">
                  {t("chrome.searchFailed")}
                </span>
                <Button variant="ghost" size="xs" onClick={() => void results.refetch()} loading={results.isFetching}>
                  {t("common.retry")}
                </Button>
              </div>
            )}
            {!debounced && (
              <div className="flex items-center gap-1.5 border-t border-border/60 px-4 py-2.5 text-xs text-muted-foreground">
                <LayoutDashboard className="size-3.5" aria-hidden />
                {t("chrome.search")} {searchGroupNames()} — {t("chrome.resultsStreamIn")}
              </div>
            )}
          </CommandList>
        </Command>
      </CommandDialog>
    </CommandPaletteContext.Provider>
  );
}
