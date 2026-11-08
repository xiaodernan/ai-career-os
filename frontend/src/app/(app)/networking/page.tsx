"use client";

import * as React from "react";
import { Search, Users } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Pagination } from "@/components/common/pagination";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import {
  useCreateContact,
  useDeleteContact,
  useUpdateContact,
} from "@/lib/hooks/actions";
import { useContacts, useContactRelations } from "@/lib/hooks/resources";
import { useOutreachDraft } from "@/lib/hooks/growth";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDate } from "@/lib/format";
import { lastPageOf } from "@/lib/page-window";
import type { Contact } from "@/lib/api/types";

/**
 * The networking registry (roadmap 11.1): the people a search actually touches, so the
 * outreach generator drafts for a real name and the follow-up cadence (11.3) has a
 * last-touched date to go stale against.
 *
 * The form is one row, full replace on edit — the PATCH carries the form's current
 * values, so a field the caller blanked is cleared on purpose. `lastTouchAt` is the
 * user's own claim ("I talked to her yesterday"), typed as a date and sent as the
 * day's midnight; the server does not guess it from request arrival.
 */
// Module-level so `setUrl` (a `useCallback` keyed on this object) is stable across renders.
// `q`, `relation` and `page` are declared here even though they are usually absent/zero:
// `useUrlState` hydrates by walking these keys, so a key left out of the defaults is a
// question or a window a pasted link cannot restore (70.2's rule, now the registry's too).
const PAGE_DEFAULTS: { page: number; q?: string; relation?: string } = { page: 0, q: undefined, relation: undefined };
/** The window this board asks the route with, restated for the pager it feeds. */
const PAGE_SIZE = 50;

export default function NetworkingPage() {
  const { t, locale } = useLocale();
  // The word and the window both live in the URL, so a reload or a shared link opens the same
  // page of the same question — the rule the replies (49.1), company (58.2) and pipeline (70.2)
  // boards follow. 72.1 gave the registry a real server window, so `page` restores people
  // rather than being a number the client invented over a bare list.
  const [state, setUrl] = useUrlState<{ page: number; q?: string; relation?: string }>(
    PAGE_DEFAULTS,
    { numericKeys: ["page"] }
  );
  // The box holds what the reader is typing; the URL holds what was asked. Binding the box
  // straight to the URL would make every character a new question: six keystrokes would be six
  // requests and six cache entries, and the registry would answer a word nobody had finished.
  const [word, setWord] = React.useState(state.q ?? "");
  React.useEffect(() => setWord(state.q ?? ""), [state.q]);
  // Asking a new question starts at its first page: a word typed on page 4 must not leave the
  // reader on a page the new, narrower answer does not have.
  const ask = (value: string) => setUrl({ q: value.trim() || undefined, page: 0 });
  const pickRelation = (relation: string | undefined) =>
    setUrl({ relation: relation === state.relation ? undefined : relation, page: 0 });
  const contacts = useContacts({
    q: state.q,
    relation: state.relation,
    page: state.page,
    size: PAGE_SIZE,
  });
  const relations = useContactRelations();
  const total = contacts.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total, not an empty registry: the
  // answer's own window is the divisor and `lastPageOf` is that rule in one place, the same
  // correction the company, pipeline and replies boards make. A layout effect, because the
  // stale commit would otherwise paint the wrong empty copy first.
  const lastPage = contacts.data ? lastPageOf(total, contacts.data.size) : 0;
  React.useLayoutEffect(() => {
    if (contacts.data && state.page > lastPage) setUrl({ page: lastPage });
  }, [contacts.data, state.page, lastPage, setUrl]);
  const [editing, setEditing] = React.useState<Contact | null>(null);
  const [open, setOpen] = React.useState(false);
  // 11.2 — the outreach draft. The contact's own fields are the request, so
  // the draft can only cite what the profile actually supports.
  const draft = useOutreachDraft();
  const [draftFor, setDraftFor] = React.useState<Contact | null>(null);

  const startCreate = () => {
    setEditing(null);
    setOpen(true);
  };
  const startEdit = (c: Contact) => {
    setEditing(c);
    setOpen(true);
  };

  return (
    <>
      {/* 80: the relation chips — the same narrowing the badge names, in the same order the
          server ranks them. The row is only rendered when the registry actually holds one,
          and tapping a chip resets the window because the answer's rows changed. */}
      {(relations.data ?? []).length > 0 ? (
        <section
          className="flex flex-wrap items-center gap-1.5"
          role="group"
          aria-label={t("networking.relationFilter")}
        >
          <Button
            type="button"
            size="sm"
            variant={state.relation ? "ghost" : "secondary"}
            onClick={() => setUrl({ relation: undefined, page: 0 })}
          >
            {t("networking.relationFilterAll")}
          </Button>
          {relations.data?.map(({ relation, count }) => (
            <Button
              key={relation}
              type="button"
              size="sm"
              variant={state.relation === relation ? "secondary" : "ghost"}
              onClick={() => pickRelation(relation)}
              aria-pressed={state.relation === relation}
            >
              {relation}
              <span className="ml-1 tabular-nums text-muted-foreground">{count}</span>
            </Button>
          ))}
        </section>
      ) : null}
      <ModuleView
        title={t("networking.title")}
        description={t("networking.description")}
        query={contacts}
        ctaHref="/copilot"
        ctaLabel={t("networking.draftWithCopilot")}
        actions={
          <div className="flex flex-wrap items-center justify-end gap-2">
            {/* The question 70.3 gave this route. It is the server's search, not a filter over the
                rows in hand: since 72.1 those rows are one window of the matches, so filtering them
                here would hide the people the server found on another page. The characters are read
                as characters, which is what lets a person whose company really carries an
                underscore be found by spelling the underscore. */}
            <form
              role="search"
              className="flex items-center gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                ask(word);
              }}
            >
              <div className="relative">
                <Search
                  aria-hidden
                  className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
                />
                <Input
                  value={word}
                  onChange={(event) => setWord(event.target.value)}
                  placeholder={t("networking.searchPlaceholder")}
                  aria-label={t("networking.searchLabel")}
                  autoComplete="off"
                  className="w-40 pl-9 sm:w-60"
                />
              </div>
              <Button type="submit" size="sm" variant="outline">
                {t("chrome.search")}
              </Button>
              {state.q ? (
                <Button
                  type="button"
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setWord("");
                    ask("");
                  }}
                >
                  {t("networking.clearSearch")}
                </Button>
              ) : null}
            </form>
            <Button variant="ai" size="sm" onClick={startCreate}>
              <Users aria-hidden />
              {t("networking.addContact")}
            </Button>
          </div>
        }
        // Two different empties (49.2): a registry nobody has started, and a registry full of
        // people none of whom spells the word the reader typed. The second one's way out is the
        // box, not a button that opens a create form — the reader was not trying to add a person.
        emptyHint={
          state.q || state.relation
            ? {
                title: state.relation
                  ? t("networking.noRelationContacts", { relation: state.relation })
                  : t("networking.noMatch", { query: state.q ?? "" }),
                description: t("networking.noMatchDescription"),
                action: (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setWord("");
                      setUrl({ q: undefined, relation: undefined, page: 0 });
                    }}
                  >
                    {t("networking.clearSearch")}
                  </Button>
                ),
              }
            : {
                title: t("networking.noContacts"),
                description: t("networking.noContactsDescription"),
              }
        }
        renderItem={(c) => (
          <Card key={c.id}>
            <CardContent className="flex items-center gap-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <Users className="size-4.5" aria-hidden />
              </span>
              <button
                type="button"
                onClick={() => startEdit(c)}
                className="min-w-0 flex-1 text-left focus-visible:ring-[3px] focus-visible:ring-ring/35 rounded-sm"
              >
                <p className="truncate text-sm font-medium">
                  {c.name}
                  {c.company && (
                    <span className="font-normal text-muted-foreground"> · {c.company}</span>
                  )}
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {[c.role, c.relation].filter(Boolean).join(" · ") || "—"}
                  {c.lastTouchAt &&
                    t("networking.lastTouchLine", { when: formatDate(c.lastTouchAt, locale) })}
                </p>
              </button>
              {c.relation && (
                <Badge variant="secondary" className="shrink-0 capitalize">
                  {c.relation}
                </Badge>
              )}
              <Button
                variant="outline"
                size="xs"
                className="shrink-0"
                loading={draft.isPending && draftFor?.id === c.id}
                onClick={() => {
                  setDraftFor(c);
                  draft.mutate({
                    name: c.name,
                    role: c.role ?? "",
                    company: c.company ?? "",
                    purpose: "referral",
                  });
                }}
              >
                {t("networking.draft")}
              </Button>
            </CardContent>
          </Card>
        )}
      />
      {total > PAGE_SIZE && (
        <Pagination
          page={contacts.data?.page ?? state.page}
          size={PAGE_SIZE}
          total={total}
          label={t("networking.title")}
          onPageChange={(page) => {
            setUrl({ page });
            window.scrollTo({ top: 0, behavior: "smooth" });
          }}
        />
      )}
      {draft.data?.body && (
        <Card>
          <CardContent className="space-y-2">
            <p className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
              {t("networking.draftFor", { name: draftFor?.name ?? "" })}
            </p>
            <Textarea readOnly value={draft.data.body} rows={4} aria-label={t("networking.draftMessage")} />
          </CardContent>
        </Card>
      )}
      <ContactDialog
        open={open}
        editing={editing}
        onClose={() => setOpen(false)}
      />
    </>
  );
}

interface ContactDialogProps {
  open: boolean;
  editing: Contact | null;
  onClose: () => void;
}

function ContactDialog({ open, editing, onClose }: ContactDialogProps) {
  const { t } = useLocale();
  const create = useCreateContact();
  const update = useUpdateContact();
  const remove = useDeleteContact();
  const [confirming, setConfirming] = React.useState(false);

  // Local form state, re-seeded whenever the dialog opens: a stale draft never
  // leaks from one open into the next.
  const [name, setName] = React.useState("");
  const [role, setRole] = React.useState("");
  const [company, setCompany] = React.useState("");
  const [relation, setRelation] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [notes, setNotes] = React.useState("");
  const [lastTouch, setLastTouch] = React.useState("");

  React.useEffect(() => {
    if (!open) return;
    setName(editing?.name ?? "");
    setRole(editing?.role ?? "");
    setCompany(editing?.company ?? "");
    setRelation(editing?.relation ?? "");
    setEmail(editing?.email ?? "");
    setNotes(editing?.notes ?? "");
    setLastTouch(editing?.lastTouchAt ? editing.lastTouchAt.slice(0, 10) : "");
  }, [open, editing]);

  const pending = create.isPending || update.isPending;
  const submitting = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || pending) return;
    const body = {
      name,
      role,
      company,
      relation,
      email,
      notes,
      // A date input answers at midnight local; the wire wants an instant.
      lastTouchAt: lastTouch ? new Date(`${lastTouch}T00:00:00`).toISOString() : undefined,
    };
    if (editing) {
      update.mutate({ id: editing.id, ...body }, { onSuccess: onClose });
    } else {
      create.mutate(body, { onSuccess: onClose });
    }
  };

  return (
    <>
      <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
        <DialogContent className="sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {editing ? t("networking.editContactTitle", { name: editing.name }) : t("networking.addContactTitle")}
            </DialogTitle>
            <DialogDescription>
              {t("networking.onlyNameRequired")}
            </DialogDescription>
          </DialogHeader>
          <form className="space-y-3" onSubmit={submitting}>
            <div className="space-y-2">
              <Label htmlFor="ct-name">{t("networking.name")}</Label>
              <Input
                id="ct-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoComplete="off"
                required
              />
            </div>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="ct-role">{t("networking.role")}</Label>
                <Input id="ct-role" value={role} onChange={(e) => setRole(e.target.value)} autoComplete="off" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ct-company">{t("networking.company")}</Label>
                <Input id="ct-company" value={company} onChange={(e) => setCompany(e.target.value)} autoComplete="off" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ct-relation">{t("networking.relation")}</Label>
                <Input
                  id="ct-relation"
                  value={relation}
                  onChange={(e) => setRelation(e.target.value)}
                  placeholder={t("networking.relationPlaceholder")}
                  autoComplete="off"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="ct-email">{t("networking.email")}</Label>
                <Input id="ct-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="off" />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="ct-touch">{t("networking.lastTouch")}</Label>
              <Input id="ct-touch" type="date" value={lastTouch} onChange={(e) => setLastTouch(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="ct-notes">{t("networking.notes")}</Label>
              <Textarea
                id="ct-notes"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder={t("networking.notesPlaceholder")}
                rows={3}
              />
            </div>
            <DialogFooter className="gap-2 sm:gap-0">
              {editing && (
                <Button
                  type="button"
                  variant="ghost"
                  className="text-destructive mr-auto"
                  onClick={() => setConfirming(true)}
                >
                  {t("networking.delete")}
                </Button>
              )}
              <Button type="button" variant="outline" onClick={onClose}>
                {t("networking.cancel")}
              </Button>
              <Button type="submit" variant="ai" loading={pending} disabled={pending}>
                {editing ? t("networking.save") : t("networking.add")}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
      {editing && (
        <ConfirmDialog
          open={confirming}
          onOpenChange={setConfirming}
          title={t("networking.deleteContactTitle", { name: editing.name })}
          description={t("networking.deleteContact")}
          confirmLabel={t("networking.delete")}
          destructive
          loading={remove.isPending}
          onConfirm={() => remove.mutate(editing.id, { onSuccess: onClose })}
        />
      )}
    </>
  );
}
