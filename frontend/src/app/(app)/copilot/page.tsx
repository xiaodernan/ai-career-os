"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  MessageSquare,
  Pencil,
  Plus,
  Quote,
  Send,
  Sparkles,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Pagination } from "@/components/common/pagination";
import { lastPageOf } from "@/lib/page-window";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingChatSkeleton } from "@/components/common/loading-skeletons";
import { isEndpointMissing } from "@/components/common/query-boundary";
import { ProcessingSteps, type ProcessingStep } from "@/components/ai/processing-steps";
import dynamic from "next/dynamic";
import { AIBadge } from "@/components/ai/ai-badge";
import { EvidenceList } from "@/components/ai/evidence-list";
import { ArtifactCard } from "@/components/copilot/artifacts";
import {
  useConversations,
  useConversationMessages,
} from "@/lib/hooks/resources";
import {
  useCopilotChat,
  useCreateConversation,
  useDeleteConversation,
  useRenameConversation,
} from "@/lib/hooks/actions";
import { useUrlState } from "@/lib/hooks/use-url-state";
import { useLocale } from "@/lib/i18n/locale-context";
import { relativeTime } from "@/lib/format";
import { actionLabelKey } from "@/lib/api/normalize";
import type { ChatMessage } from "@/lib/api/types";

// The route's own default window: `GET /conversations` binds `size` with
// `defaultValue = "20"`, so this number asks for exactly what the server would have
// chosen anyway -- the hook's own 50 literal never reaches the wire on this path.
const PAGE_SIZE = 20;

/* Code-split, not a static import: the react-markdown stack is only needed
 * once a message actually renders, so it stays out of the copilot's first load. */
const StreamingText = dynamic(() =>
  import("@/components/ai/streaming-text").then((m) => m.StreamingText)
);

/** The turn's own `status` frames, in arrival order — every step before the last one is done. */
function stepsFromTrail(trail: string[]): ProcessingStep[] {
  return trail.map((label, i) => ({
    id: `cstage-${i}`,
    label,
    status: (i === trail.length - 1 ? "active" : "done") as ProcessingStep["status"],
  }));
}

export default function CopilotPage() {
  const { t } = useLocale();
  // The sidebar's page index lives in the URL beside `?c=`, so a reload or a shared link
  // opens the same window of chats. `cpage`, not `page`: the page already spends `c` on the
  // selected conversation, and two numbers under one letter would be a collision.
  const [pageState, setPageUrl] = useUrlState<{ cpage: number }>(
    { cpage: 0 },
    { numericKeys: ["cpage"] }
  );
  const conversations = useConversations({ page: pageState.cpage, size: PAGE_SIZE });
  const createConversation = useCreateConversation();

  const total = conversations.data?.total ?? 0;
  // A past-the-end page is an empty window over a real total, not an empty list: the answer's
  // own window is the divisor (`data.size`), so the URL is corrected to the last page that
  // exists -- `lastPageOf` (lib/page-window.ts) is that rule in one place. A layout effect,
  // because the stale commit paints its empty copy first -- React flushes this update before
  // the browser paints, so the wrong screen is replaced, not seen.
  const lastPage = conversations.data ? lastPageOf(total, conversations.data.size) : 0;
  React.useLayoutEffect(() => {
    if (conversations.data && pageState.cpage > lastPage) setPageUrl({ cpage: lastPage });
  }, [conversations.data, pageState.cpage, lastPage, setPageUrl]);

  // Selected conversation lives in the URL (?c=id) so reloads and shared
  // links work; read/written via the history API to stay prerender-safe.
  const [activeId, setActiveId] = React.useState<string | null>(null);
  const [autoSend, setAutoSend] = React.useState<string | null>(null);

  React.useEffect(() => {
    const q = new URLSearchParams(window.location.search).get("c");
    if (q) {
      setActiveId((cur) => cur ?? q);
    } else {
      setActiveId((cur) => cur ?? conversations.data?.items[0]?.id ?? null);
    }
  }, [conversations.data]);

  const selectConversation = React.useCallback((id: string | null) => {
    setActiveId(id);
    const url = new URL(window.location.href);
    if (id) url.searchParams.set("c", id);
    else url.searchParams.delete("c");
    window.history.replaceState(null, "", url.toString());
  }, []);

  const newConversation = React.useCallback(
    (firstMessage?: string) => {
      createConversation.mutate(firstMessage ? firstMessage.slice(0, 48) : undefined, {
        onSuccess: (c) => {
          const id = c?.id;
          if (!id) {
            toast.error("The API didn't return a conversation id.");
            return;
          }
          void conversations.refetch();
          selectConversation(id);
          if (firstMessage) setAutoSend(firstMessage);
        },
      });
    },
    [createConversation, conversations, selectConversation]
  );

  const listPanel = (className: string) => (
    <ConversationList
      query={conversations}
      activeId={activeId}
      onSelect={selectConversation}
      onCreate={() => newConversation()}
      creating={createConversation.isPending}
      onDeleted={selectConversation}
      page={conversations.data?.page ?? pageState.cpage}
      total={total}
      onPageChange={(page) => {
        setPageUrl({ cpage: page });
        window.scrollTo({ top: 0, behavior: "smooth" });
      }}
      className={className}
    />
  );

  return (
    <div className="flex h-[calc(100dvh-7.5rem)] gap-6">
      {listPanel("hidden w-64 shrink-0 lg:flex")}

      <main className="flex min-w-0 flex-1 flex-col">
        {activeId ? (
          <ChatPanel
            key={activeId}
            conversationId={activeId}
            autoSendMessage={autoSend ?? undefined}
            onAutoSent={() => setAutoSend(null)}
            onNewConversation={() => newConversation()}
            creating={createConversation.isPending}
            listTrigger={
              <Sheet>
                <SheetTrigger asChild>
                  <Button variant="ghost" size="sm" className="lg:hidden">
                    <MessageSquare aria-hidden />
                    {t("copilot.chatsButton")}
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="flex w-72 flex-col gap-0 p-0">
                  <SheetHeader className="border-b border-border/60 py-3">
                    <SheetTitle className="text-sm">{t("copilot.conversationsSheet")}</SheetTitle>
                  </SheetHeader>
                  {listPanel("flex min-h-0 flex-1")}
                </SheetContent>
              </Sheet>
            }
          />
        ) : (
          <NewChat onStart={(msg) => newConversation(msg)} pending={createConversation.isPending} />
        )}
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Conversation list                                                    */
/* ------------------------------------------------------------------ */

function ConversationList({
  query,
  activeId,
  onSelect,
  onCreate,
  creating,
  onDeleted,
  page,
  total,
  onPageChange,
  className,
}: {
  query: ReturnType<typeof useConversations>;
  activeId: string | null;
  onSelect: (id: string | null) => void;
  onCreate: () => void;
  creating: boolean;
  /** Fired before the delete request settles, with the id going away — the page
   * deselects it so the transcript of a chat that no longer exists never shows. */
  onDeleted?: (id: string) => void;
  /** The answer's page index, its row count, and the URL writer — the pager the rows earn. */
  page: number;
  total: number;
  onPageChange: (page: number) => void;
  className?: string;
}) {
  const { t } = useLocale();
  const rename = useRenameConversation();
  const remove = useDeleteConversation();
  const [editingId, setEditingId] = React.useState<string | null>(null);
  const [draft, setDraft] = React.useState("");
  const [confirmId, setConfirmId] = React.useState<string | null>(null);
  // Stable identity across renders keeps the rename callback below from being
  // rebuilt every time; `?? []` alone would hand it a fresh array each render.
  const items = React.useMemo(() => query.data?.items ?? [], [query.data]);

  const commitRename = React.useCallback(() => {
    const id = editingId;
    if (!id || rename.isPending) return;
    setEditingId(null);
    const title = draft.trim();
    const current = items.find((c) => c.id === id);
    // Blank would be ignored by the backend anyway (`!isBlank()`); sending it
    // would only make a no-op look like a save.
    if (!title || title === (current?.title ?? "")) return;
    rename.mutate({ id, title });
  }, [draft, editingId, items, rename]);

  const confirmDelete = React.useCallback(() => {
    if (!confirmId) return;
    const id = confirmId;
    if (id === activeId) onDeleted?.(id);
    remove.mutate(id, { onSettled: () => setConfirmId(null) });
  }, [activeId, confirmId, onDeleted, remove]);

  return (
    <aside className={cn("min-h-0 flex-col gap-2", className)} aria-label={t("copilot.conversations")}>
      <Button variant="ai" size="sm" onClick={onCreate} loading={creating}>
        <Plus aria-hidden />
        New chat
      </Button>
      <ScrollArea className="min-h-0 flex-1">
        {query.isPending ? (
          <div className="space-y-2 py-2 pr-3" role="status">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14 rounded-lg" />
            ))}
            <span className="sr-only">{t("copilot.loadingConversations")}</span>
          </div>
        ) : query.isError ? (
          <div className="px-1 py-3">
            <ErrorState
              title={
                isEndpointMissing(query.error)
                  ? t("copilot.conversationsNotServed")
                  : t("copilot.couldNotLoadConversations")
              }
              error={isEndpointMissing(query.error) ? undefined : query.error}
              onRetry={() => void query.refetch()}
              retrying={query.isFetching}
            />
          </div>
        ) : !items.length ? (
          <div className="px-1 py-3">
            <EmptyState
              icon={<MessageSquare aria-hidden />}
              title={t("copilot.noConversations")}
              description={t("copilot.noConversationsDescription")}
              action={
                <Button variant="ai" size="sm" onClick={onCreate} loading={creating}>
                  <Plus aria-hidden />
                  {t("copilot.newChat")}
                </Button>
              }
            />
          </div>
        ) : (
          <ul className="space-y-1 pr-2">
            {items.map((c) => (
              <li key={c.id} className="group relative">
                {editingId === c.id ? (
                  <Input
                    value={draft}
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") commitRename();
                      if (e.key === "Escape") setEditingId(null);
                    }}
                    onBlur={commitRename}
                    autoFocus
                    maxLength={200}
                    aria-label={t("copilot.conversationTitle")}
                    className="h-9"
                    autoComplete="off"
                  />
                ) : (
                  <div className="flex items-stretch gap-0.5">
                    <button
                      type="button"
                      onClick={() => onSelect(c.id)}
                      aria-current={activeId === c.id ? "true" : undefined}
                      className={cn(
                        "min-w-0 flex-1 rounded-lg border px-3 py-2 text-left transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-primary/30",
                        activeId === c.id
                          ? "border-primary/40 bg-primary/5"
                          : "border-transparent hover:bg-accent/50"
                      )}
                    >
                      <p className="truncate text-sm font-medium">{c.title || "Untitled chat"}</p>
                      <p className="truncate text-xs text-muted-foreground">
                        {c.lastMessagePreview ?? "—"}
                      </p>
                      <p className="mt-0.5 text-2xs text-muted-foreground/80">
                        {relativeTime(c.updatedAt ?? c.createdAt)}
                      </p>
                    </button>
                    {/* Touch has no hover and no focus until tapped, so the actions stay
                        visible below the lg breakpoint and reveal on hover above it. */}
                    <div className="flex items-center opacity-100 transition-opacity duration-150 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Rename "${c.title || "Untitled chat"}"`}
                        onClick={() => {
                          setEditingId(c.id);
                          setDraft(c.title || "");
                        }}
                      >
                        <Pencil aria-hidden />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label={`Delete "${c.title || "Untitled chat"}"`}
                        onClick={() => setConfirmId(c.id)}
                      >
                        <Trash2 aria-hidden />
                      </Button>
                    </div>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </ScrollArea>
      {total > PAGE_SIZE && (
        <Pagination
          page={page}
          size={PAGE_SIZE}
          total={total}
          label={t("copilot.paginationLabel")}
          onPageChange={onPageChange}
          className="px-1"
        />
      )}
      <ConfirmDialog
        open={confirmId !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmId(null);
        }}
        title={t("copilot.deleteChat")}
        description={t("copilot.deleteChatDescription")}
        confirmLabel={t("copilot.delete")}
        destructive
        loading={remove.isPending}
        onConfirm={confirmDelete}
      />
    </aside>
  );
}

/* ------------------------------------------------------------------ */
/* New chat (no conversation selected)                                  */
/* ------------------------------------------------------------------ */

function NewChat({ onStart, pending }: { onStart: (message: string) => void; pending: boolean }) {
  const { t } = useLocale();
  const [value, setValue] = React.useState("");
  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="w-full max-w-xl animate-fade-up space-y-6">
        <div className="text-center">
          <span className="mx-auto mb-3 flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Sparkles className="size-6" aria-hidden />
          </span>
          <h1 className="font-serif text-display-md font-medium">{t("copilot.title")}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {t("copilot.groundedIn")}
          </p>
        </div>
        <Card>
          <CardContent className="space-y-3">
            <Textarea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={t("copilot.firstMessagePlaceholder")}
              rows={3}
              className="resize-none"
              aria-label={t("copilot.firstMessage")}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && value.trim()) {
                  e.preventDefault();
                  onStart(value.trim());
                }
              }}
            />
            <div className="flex items-center justify-between gap-2">
              <p className="text-2xs text-muted-foreground">{t("copilot.enterToSend")}</p>
              <Button
                variant="ai"
                size="sm"
                disabled={!value.trim()}
                loading={pending}
                onClick={() => onStart(value.trim())}
              >
                <Send aria-hidden />
                {t("copilot.startChat")}
              </Button>
            </div>
          </CardContent>
        </Card>
        <ul className="grid gap-2 text-xs sm:grid-cols-2">
          {[
            "Compare my resume against this JD",
            "What should I prepare for a RAG-system design interview?",
            "Draft a cover letter for the company I applied to",
            "Which experience best demonstrates ownership?",
          ].map((s) => (
            <li key={s}>
              <button
                type="button"
                onClick={() => setValue(s)}
                className="w-full rounded-lg border border-border/70 bg-muted/20 px-3 py-2 text-left text-muted-foreground transition-colors duration-150 hover:border-primary/40 hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-primary/30"
              >
                “{s}”
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Chat panel for one conversation                                      */
/* ------------------------------------------------------------------ */

function ChatPanel({
  conversationId,
  autoSendMessage,
  onAutoSent,
  onNewConversation,
  creating,
  listTrigger,
}: {
  conversationId: string;
  autoSendMessage?: string;
  onAutoSent?: () => void;
  onNewConversation: () => void;
  creating: boolean;
  listTrigger: React.ReactNode;
}) {
  const { t } = useLocale();
  const messages = useConversationMessages(conversationId);
  const [draft, setDraft] = React.useState("");
  const [transcript, setTranscript] = React.useState<ChatMessage[]>([]);
  // The reply while it is being written: deltas as they arrive, and the steps the agent reports
  // between them. Both are cleared the moment the stored answer lands, so nothing shows twice.
  const [streamText, setStreamText] = React.useState("");
  const [streamSteps, setStreamSteps] = React.useState<string[]>([]);
  const chat = useCopilotChat({
    onToken: (token) => setStreamText((t) => t + token),
    onStatus: ({ step }) => {
      if (!step) return;
      setStreamSteps((prev) => (prev[prev.length - 1] === step ? prev : [...prev, step]));
    },
  });
  const bottomRef = React.useRef<HTMLDivElement>(null);
  const hydratedRef = React.useRef(Boolean(autoSendMessage));
  const autoSentRef = React.useRef(false);

  // Hydrate once from the API; later turns live locally so the optimistic
  // user row and the fresh reply never flicker away on refetch.
  React.useEffect(() => {
    if (hydratedRef.current || !messages.data) return;
    hydratedRef.current = true;
    setTranscript(
      messages.data.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        createdAt: m.createdAt,
        artifacts: m.artifacts,
        sources: m.sources,
        actions: m.actions,
      }))
    );
  }, [messages.data]);

  const send = React.useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || chat.isPending) return;
      setDraft("");
      setStreamText("");
      setStreamSteps([]);
      setTranscript((prev) => [
        ...prev,
        { id: `local-${Date.now()}`, role: "user", content: trimmed, createdAt: new Date().toISOString() },
      ]);
      chat.mutate(
        { message: trimmed, conversationId },
        {
          onSuccess: (reply) => {
            setTranscript((prev) => [
              ...prev,
              {
                id: `reply-${Date.now()}`,
                role: "assistant",
                content: reply.answer,
                artifacts: reply.artifacts,
                sources: reply.sources,
                actions: reply.actions,
                createdAt: new Date().toISOString(),
              },
            ]);
          },
        }
      );
    },
    [chat, conversationId]
  );

  // First-message handoff from the "New chat" composer.
  React.useEffect(() => {
    if (autoSendMessage && !autoSentRef.current) {
      autoSentRef.current = true;
      send(autoSendMessage);
      onAutoSent?.();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSendMessage]);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [transcript.length, streamText.length, chat.isPending]);

  const error = chat.error;

  return (
    <div className="flex h-full min-h-0 flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 border-b border-border/60 py-3">
        {listTrigger}
        <Button variant="ghost" size="sm" onClick={onNewConversation} loading={creating} className="ml-auto">
          <Plus aria-hidden />
          New chat
        </Button>
      </div>

      {/* Transcript */}
      <ScrollArea className="min-h-0 flex-1">
        <div className="mx-auto w-full max-w-3xl space-y-6 px-1 py-6">
          {messages.isPending && transcript.length === 0 && !hydratedRef.current ? (
            <LoadingChatSkeleton />
          ) : messages.isError && transcript.length === 0 ? (
            isEndpointMissing(messages.error) ? (
              <EmptyState
                icon={<MessageSquare aria-hidden />}
                title={t("copilot.noHistory")}
                description={t("copilot.noHistoryDescription")}
                action={
                  <Button variant="outline" size="sm" onClick={() => void messages.refetch()}>
                    Check again
                  </Button>
                }
              />
            ) : (
              <ErrorState
                title={t("copilot.couldNotLoad")}
                error={messages.error}
                onRetry={() => void messages.refetch()}
                retrying={messages.isFetching}
              />
            )
          ) : transcript.length === 0 ? (
            <EmptyState
              icon={<Sparkles aria-hidden />}
              title={t("copilot.askAnything")}
              description={t("copilot.askAnythingDescription")}
            />
          ) : (
            transcript.map((m) => <MessageRow key={m.id} message={m} />)
          )}

          {chat.isPending && (
            <div className="flex animate-fade-up flex-col gap-2">
              <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                <AIBadge label={t("copilot.badge")} />{" "}
                {streamSteps[streamSteps.length - 1] ??
                  (streamText ? t("copilot.writing") : t("copilot.thinking"))}
              </p>
              {streamText ? (
                <div className="max-w-[85%] rounded-2xl border border-border/70 bg-card px-4 py-2.5 text-sm">
                  <StreamingText content={streamText} />
                </div>
              ) : (
                streamSteps.length > 0 && <ProcessingSteps steps={stepsFromTrail(streamSteps)} />
              )}
            </div>
          )}

          {error != null && (
            <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 p-3">
              <p className="text-sm text-destructive">
                {error instanceof Error && error.message ? error.message : "Copilot couldn't answer."}
              </p>
              <Button
                variant="outline"
                size="xs"
                className="mt-2"
                onClick={() => {
                  const lastUser = [...transcript].reverse().find((m) => m.role === "user");
                  if (lastUser) {
                    setTranscript((prev) => prev.slice(0, prev.lastIndexOf(lastUser)));
                    send(lastUser.content);
                  }
                }}
              >
                Retry last message
              </Button>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </ScrollArea>

      {/* Composer */}
      <div className="border-t border-border/60 py-3">
        <div className="mx-auto flex w-full max-w-3xl items-end gap-2">
          <Textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={t("copilot.messagePlaceholder")}
            rows={1}
            className="max-h-40 min-h-10 resize-none"
            aria-label={t("copilot.messageLabel")}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey && draft.trim()) {
                e.preventDefault();
                send(draft);
              }
            }}
          />
          <Button
            variant="ai"
            size="icon"
            disabled={!draft.trim() || chat.isPending}
            loading={chat.isPending}
            onClick={() => send(draft)}
            aria-label={t("copilot.send")}
          >
            <Send aria-hidden />
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Message row                                                          */
/* ------------------------------------------------------------------ */

function MessageRow({ message }: { message: ChatMessage }) {
  const { t } = useLocale();
  const isUser = message.role === "user";
  const actions = (message.actions ?? []).filter((a) => a.href && a.label);
  const sources = message.sources ?? [];

  return (
    <div className={cn("flex animate-fade-up flex-col gap-2", isUser && "items-end")}>
      <div
        className={cn(
          "max-w-[85%] rounded-2xl px-4 py-2.5 text-sm",
          isUser ? "bg-primary text-primary-foreground" : "border border-border/70 bg-card"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : (
          <StreamingText content={message.content} />
        )}
      </div>

      {!isUser && (message.artifacts?.length ?? 0) > 0 && (
        <div className="w-full max-w-[85%] space-y-3">
          {message.artifacts!.map((a, i) => (
            <ArtifactCard key={`${message.id}-art-${i}`} artifact={a} />
          ))}
        </div>
      )}

      {!isUser && sources.some((s) => s.quote) && (
        <EvidenceList
          items={sources}
          limit={2}
          dense
          className="w-full max-w-[85%]"
          hrefFor={(e) => (e.source?.docId ? `/knowledge?src=${e.source.docId}` : undefined)}
        />
      )}

      {!isUser && actions.length > 0 && (
        <div className="flex max-w-[85%] flex-wrap gap-1.5">
          {actions.map((a, i) => {
            // The orchestrator writes the label in English; the browser says it
            // in the reader's language when the kind fixes the phrase. An
            // `open_job` chip keeps the backend's label, because it carries the
            // job's own title and company -- data, not copy.
            const key = actionLabelKey(a.kind);
            const label = key ? t(key) : a.label;
            return (
              <Button key={i} variant="outline" size="xs" asChild>
                <Link href={a.href!}>
                  {label}
                  <ArrowRight aria-hidden />
                </Link>
              </Button>
            );
          })}
        </div>
      )}

      {message.createdAt && (
        <p className={cn("text-2xs text-muted-foreground/70", isUser ? "pr-1" : "pl-1")}>
          {relativeTime(message.createdAt)}
        </p>
      )}
      {!isUser && (
        <p className="sr-only">
          <Quote className="inline size-3" aria-hidden /> answers cite your knowledge base
        </p>
      )}
    </div>
  );
}
