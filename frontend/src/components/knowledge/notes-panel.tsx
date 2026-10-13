"use client";

import * as React from "react";
import { Check, Pencil, StickyNote, Trash2, X } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Pagination } from "@/components/common/pagination";
import { lastPageOf } from "@/lib/page-window";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useNoteMutations } from "@/lib/hooks/actions";
import { useKnowledgeNotes } from "@/lib/hooks/resources";
import { useUrlState } from "@/lib/hooks/use-url-state";
import type { KnowledgeNote } from "@/lib/api/types";

/**
 * Notes CRUD for the knowledge page. The backend has shipped `GET/POST
 * /knowledge/notes` and `PATCH/DELETE /knowledge/notes/{id}` since the start
 * (`KnowledgeService.listNotes/createNote/updateNote/deleteNote`), and the
 * `useKnowledgeNotes` + `useNoteMutations` hooks existed unmounted — this panel
 * is the first screen to mount either, so the `["knowledge", "notes"]`
 * invalidation ledger in `actions.ts` finally reaches a live query.
 *
 * `NoteRequest` validates title ≤ 200 chars and `content` `@NotBlank` on the
 * server, so the forms mirror both: a maxLength input, and a save button gated
 * on non-blank content rather than an error round-trip. Tags are accepted by
 * the backend but no mutation sends them yet — the row renders what exists.
 */

/** Mirrors `NoteRequest`'s `@Size(max = 200)` on the title. */
const MAX_TITLE = 200;

// The route's own default window: `GET /knowledge/notes` binds `size` with
// `defaultValue = "20"`, so this number asks for exactly what the server would have
// chosen anyway -- the hook's own 50 literal never reaches the wire on this path.
// `npage` rather than the page's own `page`: the sources list above keeps its index
// under `?page=`, and two lists on one screen need two questions.
const PAGE_SIZE = 20;
const PAGE_DEFAULTS: { npage: number } = { npage: 0 };

export function NoteCreateCard() {
  const [title, setTitle] = React.useState("");
  const [content, setContent] = React.useState("");
  const { create } = useNoteMutations();

  const saveable = content.trim().length > 0;
  const submit = React.useCallback(() => {
    if (!saveable || create.isPending) return;
    create.mutate(
      { title: title.trim(), content },
      {
        onSuccess: () => {
          setTitle("");
          setContent("");
        },
      }
    );
  }, [create, content, saveable, title]);

  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label htmlFor="note-title">Title (optional)</Label>
          <Input
            id="note-title"
            value={title}
            maxLength={MAX_TITLE}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Answers for the “why us” question"
            autoComplete="off"
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="note-content">Content</Label>
          <Textarea
            id="note-content"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            placeholder="Write it down — the agents can quote this back with a citation."
            rows={4}
          />
        </div>
        <div className="flex justify-end">
          <Button variant="ai" size="sm" loading={create.isPending} disabled={!saveable || create.isPending} onClick={submit}>
            <StickyNote aria-hidden />
            Save note
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

function NoteRow({ note }: { note: KnowledgeNote }) {
  const [editing, setEditing] = React.useState(false);
  const [title, setTitle] = React.useState(note.title);
  const [content, setContent] = React.useState(note.content ?? "");
  const [confirming, setConfirming] = React.useState(false);
  const { update, remove } = useNoteMutations();

  const start = () => {
    setTitle(note.title);
    setContent(note.content ?? "");
    setEditing(true);
  };
  // The row mapper only falls back to "Untitled note" when the title is absent;
  // a note saved with a blank title arrives as the empty string, so the display
  // needs its own fallback.
  const displayTitle = note.title || "Untitled note";
  const saveable = content.trim().length > 0;
  const save = () => {
    if (!saveable || update.isPending) return;
    update.mutate(
      { id: note.id, title: title.trim(), content },
      { onSuccess: () => setEditing(false) }
    );
  };

  return (
    <Card>
      <CardContent className="space-y-2">
        {editing ? (
          <>
            <Input
              aria-label="Note title"
              value={title}
              maxLength={MAX_TITLE}
              onChange={(e) => setTitle(e.target.value)}
              autoComplete="off"
            />
            <Textarea
              aria-label="Note content"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={5}
            />
            <div className="flex justify-end gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setEditing(false)}
                disabled={update.isPending}
                title={update.isPending ? "Saving…" : undefined}
              >
                <X aria-hidden />
                Cancel
              </Button>
              <Button variant="ai" size="sm" loading={update.isPending} disabled={!saveable || update.isPending} onClick={save}>
                <Check aria-hidden />
                Save
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-start gap-3">
              <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                <StickyNote className="size-4.5" aria-hidden />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{displayTitle}</p>
                <p className="text-xs text-muted-foreground">
                  {note.updatedAt ? `Updated ${new Date(note.updatedAt).toLocaleDateString()}` : null}
                </p>
              </div>
              <Button variant="ghost" size="icon-sm" aria-label={`Edit ${displayTitle}`} onClick={start}>
                <Pencil aria-hidden />
              </Button>
              <Button variant="ghost" size="icon-sm" aria-label={`Delete ${displayTitle}`} onClick={() => setConfirming(true)}>
                <Trash2 aria-hidden />
              </Button>
            </div>
            {note.content && (
              <p className="whitespace-pre-wrap text-sm text-muted-foreground">{note.content}</p>
            )}
            {note.tags && note.tags.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {note.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">
                    {tag}
                  </Badge>
                ))}
              </div>
            )}
          </>
        )}
        <ConfirmDialog
          open={confirming}
          onOpenChange={setConfirming}
          title={`Delete “${displayTitle}”?`}
          description="The note row is removed and its chunks stop being cited. This cannot be undone."
          confirmLabel="Delete"
          destructive
          loading={remove.isPending}
          onConfirm={() =>
            remove.mutate(note.id, {
              onSuccess: () => setConfirming(false),
            })
          }
        />
      </CardContent>
    </Card>
  );
}

export function NotesPanel() {
  // The page index lives in the URL, so a reload or a shared list link opens the same window.
  const [state, setUrl] = useUrlState<{ npage: number }>(
    PAGE_DEFAULTS,
    { numericKeys: ["npage"] }
  );
  const notes = useKnowledgeNotes({ page: state.npage, size: PAGE_SIZE });

  const total = notes.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total, not an empty list: the answer's
  // own window is the divisor (`data.size`), so the URL is corrected to the last page that
  // exists -- `lastPageOf` (lib/page-window.ts) is that rule in one place. A layout effect,
  // because the stale commit paints its empty copy first -- React flushes this update before
  // the browser paints, so the wrong screen is replaced, not seen.
  const lastPage = notes.data ? lastPageOf(total, notes.data.size) : 0;
  React.useLayoutEffect(() => {
    if (notes.data && state.npage > lastPage) setUrl({ npage: lastPage });
  }, [notes.data, state.npage, lastPage, setUrl]);

  return (
    <section aria-label="Notes" className="space-y-4">
      <NoteCreateCard />
      <ModuleView
        title="Notes"
        description="Short reference notes the agents can quote back at you — talking points, salary research, follow-ups."
        query={notes}
        emptyHint={{
          title: "No notes yet",
          description: "Write the first one above — it lands straight in the knowledge base the agents can cite.",
        }}
        footer={
          total > PAGE_SIZE && (
            <Pagination
              page={notes.data?.page ?? state.npage}
              size={PAGE_SIZE}
              total={total}
              label="notes"
              onPageChange={(page) => {
                setUrl({ npage: page });
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            />
          )
        }
        renderItem={(n) => <NoteRow key={n.id} note={n} />}
      />
    </section>
  );
}
