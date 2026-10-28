"use client";

import * as React from "react";
import { Bookmark, BookmarkPlus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useLocale } from "@/lib/i18n/locale-context";
import { useCreateSavedSearch, useDeleteSavedSearch } from "@/lib/hooks/actions";
import { useSavedSearches } from "@/lib/hooks/resources";
import {
  criteriaFromFilters,
  filtersFromCriteria,
  suggestedName,
  type SavedSearchFilterState,
} from "@/lib/saved-search";
import type { SavedSearch } from "@/lib/api/types";

/**
 * The board's current question, kept under a name (roadmap 19.1).
 *
 * The panel sits beside the filters and speaks the same vocabulary the URL
 * does: saving reads the live filter values, applying writes them back --
 * through the page's `replaceAll`, so a search replaces the previous one
 * instead of adding to it. The criteria themselves are translated to the
 * board's own names in `lib/saved-search.ts`, which is also the one place
 * that decides an empty board is not a search worth keeping.
 */
export interface SavedSearchPanelProps {
  value: SavedSearchFilterState;
  onApply: (next: SavedSearchFilterState) => void;
}

export function SavedSearchPanel({ value, onApply }: SavedSearchPanelProps) {
  const { t } = useLocale();
  const searches = useSavedSearches();
  const create = useCreateSavedSearch();
  const remove = useDeleteSavedSearch();

  const criteria = criteriaFromFilters(value);
  const [saveOpen, setSaveOpen] = React.useState(false);
  const [name, setName] = React.useState("");
  const [pendingDelete, setPendingDelete] = React.useState<SavedSearch | null>(null);

  const openSave = () => {
    if (!criteria) return;
    setName(suggestedName(criteria, t));
    setSaveOpen(true);
  };

  const save = () => {
    if (!criteria) return;
    const trimmed = name.trim();
    if (!trimmed || create.isPending) return;
    create.mutate(
      { name: trimmed, criteria },
      {
        onSuccess: () => {
          setSaveOpen(false);
          setName("");
        },
      }
    );
  };

  const rows = searches.data ?? [];

  return (
    <section className="mb-5 space-y-2 border-b border-border/70 pb-5">
      <h2 className="flex items-center gap-2 text-sm font-semibold">
        <Bookmark className="size-3.5 text-muted-foreground" aria-hidden />
        {t("savedSearches.heading")}
      </h2>

      <Button
        variant="outline"
        size="sm"
        className="w-full"
        onClick={openSave}
        disabled={!criteria}
      >
        <BookmarkPlus aria-hidden />
        {t("savedSearches.saveAction")}
      </Button>

      {rows.length > 0 ? (
        <ul className="flex flex-wrap gap-1.5">
          {rows.map((search) => (
            <li
              key={search.id}
              className="flex items-center rounded-full border border-border/70 bg-card"
            >
              <button
                type="button"
                onClick={() => onApply(filtersFromCriteria(search.criteria))}
                className="rounded-l-full py-0.5 ps-2.5 pe-1.5 text-xs font-medium hover:text-primary focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:outline-none"
              >
                {search.name}
              </button>
              <button
                type="button"
                onClick={() => setPendingDelete(search)}
                aria-label={t("savedSearches.deleteAria", { name: search.name })}
                className="rounded-r-full py-0.5 pe-1.5 ps-1 text-muted-foreground hover:text-danger focus-visible:ring-2 focus-visible:ring-primary/30 focus-visible:outline-none"
              >
                <Trash2 className="size-3" aria-hidden />
              </button>
            </li>
          ))}
        </ul>
      ) : searches.isSuccess ? (
        <p className="text-xs text-muted-foreground">{t("savedSearches.empty")}</p>
      ) : null}

      <Dialog
        open={saveOpen}
        onOpenChange={(open) => {
          setSaveOpen(open);
          if (!open) create.reset();
        }}
      >
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-base">{t("savedSearches.saveTitle")}</DialogTitle>
            <DialogDescription>{t("savedSearches.saveDescription")}</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="saved-search-name">{t("savedSearches.nameLabel")}</Label>
            <Input
              id="saved-search-name"
              value={name}
              maxLength={80}
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") save();
              }}
              placeholder={t("savedSearches.namePlaceholder")}
              autoComplete="off"
            />
          </div>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button
              variant="outline"
              onClick={() => setSaveOpen(false)}
              disabled={create.isPending}
            >
              {t("common.cancel")}
            </Button>
            <Button onClick={save} loading={create.isPending} disabled={!name.trim()}>
              {t("common.save")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={pendingDelete != null}
        onOpenChange={(open) => {
          if (!open) setPendingDelete(null);
        }}
        title={t("savedSearches.deleteTitle")}
        description={
          pendingDelete
            ? t("savedSearches.deleteDescription", { name: pendingDelete.name })
            : undefined
        }
        confirmLabel={t("savedSearches.deleteConfirm")}
        cancelLabel={t("common.cancel")}
        destructive
        loading={remove.isPending}
        onConfirm={() => {
          if (!pendingDelete) return;
          remove.mutate(pendingDelete.id, {
            onSuccess: () => setPendingDelete(null),
          });
        }}
      />
    </section>
  );
}
