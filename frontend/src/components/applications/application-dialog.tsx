"use client";

import * as React from "react";
import { CalendarClock, Trash2 } from "lucide-react";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { field } from "@/lib/api/body";
import { ApiError } from "@/lib/api/client";
import { fromReminderInput, reminderPatch, toReminderInput } from "@/lib/application-edit";
import { relativeTime } from "@/lib/format";
import {
  useCreateApplication,
  useDeleteApplication,
  useUpdateApplication,
} from "@/lib/hooks/actions";
import { useApplicationEvents } from "@/lib/hooks/resources";
import { pickerStages, stageMeta } from "@/lib/pipeline";
import type { Application, ApplicationEvent, ApplicationStatus } from "@/lib/api/types";

/**
 * The application drawer — the one place the pipeline's own fields are editable.
 *
 * The board could move a card between columns and nothing else: notes and reminders were
 * stored, rendered on the card, and counted by the dashboard's attention query, but no
 * surface could write them, and creating an application asked for a title through
 * `window.prompt`. Both halves of that gap close here.
 *
 * One component serves both modes because they are the same form: `application === null` is
 * the create case. Two things differ beyond the copy — the create route names the note
 * `notes` where the update route names it `note` (Jackson drops the wrong one silently), and
 * only an existing row can be deleted or has a history to show.
 */
export interface ApplicationDialogProps {
  /** The row to edit, or null to open the create form. */
  application: Application | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

/** What one audit row says, given the kind it carries and the payload it was read from. */
function eventText(event: ApplicationEvent): string {
  if (event.type === "status") {
    return event.status ? `Moved to ${stageMeta(event.status).label}` : "Stage changed";
  }
  if (event.type === "note") return "Note saved";
  if (event.type === "reminder") {
    if (event.cleared) return "Reminder cleared";
    return event.reminderAt ? `Reminder set for ${relativeTime(event.reminderAt)}` : "Reminder set";
  }
  if (event.type === "outcome") {
    return event.field === "offer_compensation"
      ? "Offer compensation saved"
      : event.field === "rejection_reason"
        ? "Rejection reason saved"
        : "Outcome recorded";
  }
  // The kinds above are the ones `writeEvent` writes; anything else is shown by its kind.
  return event.type ?? "Update";
}

/**
 * One pipeline link in the drawer: the id the match / tailor / JD-analysis route stored on this row.
 *
 * Renders nothing without an id, so a card that has never been matched does not carry three dashes,
 * and the full uuid is shown rather than a prefix — it is the only handle the reader has on the
 * artifact, and a truncated one cannot be copied into a query.
 */
function PipelineLink({ label, id }: { label: string; id?: string | null }) {
  if (!id) return null;
  return (
    <div className="flex items-baseline gap-2">
      <dt className="shrink-0 text-muted-foreground">{label}</dt>
      <dd className="min-w-0 font-mono text-xs break-all">{id}</dd>
    </div>
  );
}

export function ApplicationDialog({ application, open, onOpenChange }: ApplicationDialogProps) {
  const editing = application !== null;
  const createApp = useCreateApplication();
  const updateApp = useUpdateApplication();
  const deleteApp = useDeleteApplication();
  const events = useApplicationEvents(editing && open ? application.id : null);

  const [title, setTitle] = React.useState("");
  const [companyName, setCompanyName] = React.useState("");
  const [status, setStatus] = React.useState<string>("saved");
  const [notes, setNotes] = React.useState("");
  const [reminder, setReminder] = React.useState("");
  const [offerCompensation, setOfferCompensation] = React.useState("");
  const [rejectionReason, setRejectionReason] = React.useState("");
  const [confirmingDelete, setConfirmingDelete] = React.useState(false);

  // The form is a copy of the row, so it is rebuilt whenever a different card opens — and on
  // every open, so a cancelled edit never leaks into the next one.
  React.useEffect(() => {
    if (!open) return;
    setTitle(application?.title ?? "");
    setCompanyName(application?.company?.name ?? application?.companyName ?? "");
    setStatus(application?.status ?? "saved");
    setNotes(application?.note ?? "");
    setReminder(toReminderInput(application?.reminderAt));
    setOfferCompensation(application?.offerCompensation ?? "");
    setRejectionReason(application?.rejectionReason ?? "");
    setConfirmingDelete(false);
    createApp.reset();
    updateApp.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, application?.id]);

  const pending = createApp.isPending || updateApp.isPending;
  const error = createApp.error ?? updateApp.error;

  const save = () => {
    if (!editing) {
      const trimmed = title.trim();
      if (!trimmed) return;
      createApp.mutate(
        {
          title: trimmed,
          status: status as ApplicationStatus,
          ...field("companyName", companyName.trim()),
          ...field("notes", notes.trim()),
          ...field("reminderAt", fromReminderInput(reminder) ?? undefined),
        },
        { onSuccess: () => onOpenChange(false) },
      );
      return;
    }

    // Only what actually changed travels: an untouched form closing with no request keeps the
    // audit log honest, and the reminder comparison is the reason reminderPatch exists.
    //
    // The three pipeline links are deliberately not here. They are written by the routes that mint
    // them (match / tailor / JD analysis) through `ApplicationService.linkJobActivity`, and the PATCH
    // record has no component for them -- a key this body sent would be dropped by Jackson without a
    // word, which is a write the screen only pretends to make.
    const patch = {
      ...(status !== application.status ? { status: status as ApplicationStatus } : {}),
      ...(notes !== (application.note ?? "") ? { note: notes } : {}),
      ...reminderPatch(application.reminderAt, reminder),
      // Outcome fields follow the same only-what-changed rule; an emptied input sends an
      // empty string, which the PATCH route reads as "clear it" (null means "leave alone").
      ...(offerCompensation !== (application.offerCompensation ?? "")
        ? { offerCompensation: offerCompensation.trim() }
        : {}),
      ...(rejectionReason !== (application.rejectionReason ?? "")
        ? { rejectionReason: rejectionReason.trim() }
        : {}),
    };
    if (Object.keys(patch).length === 0) {
      onOpenChange(false);
      return;
    }
    updateApp.mutate({ id: application.id, patch }, { onSuccess: () => onOpenChange(false) });
  };

  const meta = stageMeta(status);

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle className="text-base">
              {editing ? application.title : "Track an application"}
            </DialogTitle>
            <DialogDescription>
              {editing
                ? [application.company?.name ?? application.companyName, meta.label]
                    .filter(Boolean)
                    .join(" · ")
                : "Anything you add here starts in the stage you choose, no job link required."}
            </DialogDescription>
          </DialogHeader>

          {!editing && (
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="app-title">Role</Label>
                <Input
                  id="app-title"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  maxLength={300}
                  placeholder="Senior Backend Engineer"
                  autoComplete="off"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="app-company">Company</Label>
                <Input
                  id="app-company"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="Optional"
                  autoComplete="off"
                />
              </div>
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="app-stage">Stage</Label>
            <Select value={status} onValueChange={setStatus} disabled={pending}>
              <SelectTrigger id="app-stage" className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {pickerStages(status).map((s) => (
                  <SelectItem key={s.value} value={s.value}>
                    {s.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">{meta.blurb}</p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="app-notes">Notes</Label>
            <Textarea
              id="app-notes"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Recruiter name, take-home, salary range, anything you will want next week…"
              rows={3}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="app-reminder">Reminder</Label>
            <div className="flex items-center gap-2">
              <Input
                id="app-reminder"
                type="datetime-local"
                value={reminder}
                onChange={(e) => setReminder(e.target.value)}
                className="flex-1"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setReminder("")}
                disabled={!reminder}
              >
                Clear
              </Button>
            </div>
            <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <CalendarClock className="size-3.5" aria-hidden />
              The dashboard counts a due reminder as needing your attention.
            </p>
          </div>
          {editing && (status === "offer" || status === "rejected") && (
            <section className="space-y-3 rounded-lg border border-border/60 bg-muted/30 p-3">
              <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                Outcome
              </h4>
              <div className="space-y-2">
                <Label htmlFor="app-comp">Offer compensation</Label>
                <Input
                  id="app-comp"
                  value={offerCompensation}
                  onChange={(e) => setOfferCompensation(e.target.value)}
                  placeholder="e.g. 40k/mo · 16 months, or 550k + equity"
                  autoComplete="off"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="app-reject">Rejection / feedback reason</Label>
                <Textarea
                  id="app-reject"
                  value={rejectionReason}
                  onChange={(e) => setRejectionReason(e.target.value)}
                  placeholder="Why it didn't proceed — this is what feeds back into what to improve."
                  rows={3}
                />
              </div>
              <p className="text-xs text-muted-foreground">
                Captured here, it closes the loop: a rejection reason tells you what to strengthen,
                and an offer&apos;s number is what to compare and negotiate against.
              </p>
            </section>
          )}

        {editing && (
          <>
            <section className="space-y-2">
              <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                History
              </h4>
              {events.isLoading && (
                <p className="text-sm text-muted-foreground">Loading history…</p>
              )}
              {events.data?.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  Nothing recorded yet — stages you move, notes you save and reminders you set
                  all land here.
                </p>
              )}
              <ol className="space-y-2">
                {(events.data ?? []).map((event) => (
                  <li key={event.id} className="flex items-baseline gap-2 text-sm">
                    <Badge
                      variant={event.type === "reminder" ? "warning" : "secondary"}
                      className="shrink-0 font-normal"
                    >
                      {eventText(event)}
                    </Badge>
                    {event.note && event.type !== "note" && (
                      <span className="min-w-0 truncate text-muted-foreground">{event.note}</span>
                    )}
                    <span className="ml-auto shrink-0 text-xs text-muted-foreground">
                      {relativeTime(event.createdAt)}
                    </span>
                  </li>
                ))}
              </ol>
            </section>

            {/* Read-only, and only when there is something to read: these three are written by the
                match / tailor / JD-analysis routes, never here, so an empty row of UUID inputs would
                be a form pretending to be editable. */}
            {(application.resumeVersionId || application.jdId || application.matchId) && (
              <section className="space-y-2">
                <h4 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
                  Pipeline links
                </h4>
                <dl className="space-y-1 text-sm">
                  <PipelineLink label="Resume version" id={application.resumeVersionId} />
                  <PipelineLink label="JD analysis" id={application.jdId} />
                  <PipelineLink label="Match" id={application.matchId} />
                </dl>
                <p className="text-xs text-muted-foreground">
                  Recorded by the route that produced each one — match, tailor, or JD analysis.
                </p>
              </section>
            )}
          </>
        )}

          {error != null && (
            <div
              role="alert"
              className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
            >
              {error instanceof ApiError && error.isNotFound
                ? "That application no longer exists."
                : error instanceof Error
                  ? error.message
                  : "Couldn't save the application."}
            </div>
          )}

          <DialogFooter className="gap-2 sm:justify-between">
            {editing ? (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setConfirmingDelete(true)}
                disabled={pending}
              >
                <Trash2 aria-hidden />
                Delete
              </Button>
            ) : (
              <span />
            )}
            <div className="flex flex-col-reverse gap-2 sm:flex-row">
              <Button
                type="button"
                variant="outline"
                onClick={() => onOpenChange(false)}
                disabled={pending}
              >
                Cancel
              </Button>
              <Button
                type="button"
                variant="primary"
                onClick={save}
                loading={pending}
                disabled={!editing && !title.trim()}
              >
                {editing ? "Save changes" : "Add to pipeline"}
              </Button>
            </div>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmingDelete}
        onOpenChange={setConfirmingDelete}
        title="Delete this application?"
        description={
          editing
            ? `"${application.title}" and its history are removed from the board. This cannot be undone.`
            : undefined
        }
        confirmLabel="Delete"
        destructive
        loading={deleteApp.isPending}
        onConfirm={() => {
          if (!editing) return;
          deleteApp.mutate(application.id, {
            onSuccess: () => {
              setConfirmingDelete(false);
              onOpenChange(false);
            },
          });
        }}
      />
    </>
  );
}
