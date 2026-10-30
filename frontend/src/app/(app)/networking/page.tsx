"use client";

import * as React from "react";
import { Users } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
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
import { useContacts } from "@/lib/hooks/resources";
import { useOutreachDraft } from "@/lib/hooks/growth";
import { useLocale } from "@/lib/i18n/locale-context";
import { formatDate } from "@/lib/format";
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
export default function NetworkingPage() {
  const { t, locale } = useLocale();
  const contacts = useContacts();
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
      <ModuleView
        title={t("networking.title")}
        description={t("networking.description")}
        query={contacts}
        ctaHref="/copilot"
        ctaLabel={t("networking.draftWithCopilot")}
        actions={
          <Button variant="ai" size="sm" onClick={startCreate}>
            <Users aria-hidden />
            {t("networking.addContact")}
          </Button>
        }
        emptyHint={{
          title: t("networking.noContacts"),
          description: t("networking.noContactsDescription"),
        }}
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
