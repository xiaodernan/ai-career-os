"use client";

import * as React from "react";
import Link from "next/link";
import {
  ArrowRight,
  MessageSquare,
  Plus,
  Quote,
  Send,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { EmptyState } from "@/components/common/empty-state";
import { ErrorState } from "@/components/common/error-state";
import { LoadingChatSkeleton } from "@/components/common/loading-skeletons";
import { isEndpointMissing } from "@/components/common/query-boundary";
import { ProcessingSteps, type ProcessingStep } from "@/components/ai/processing-steps";
import { StreamingText } from "@/components/ai/streaming-text";
import { AIBadge } from "@/components/ai/ai-badge";
import { EvidenceList } from "@/components/ai/evidence-list";
import { ArtifactCard } from "@/components/copilot/artifacts";
import {
  useConversations,
  useConversationMessages,
} from "@/lib/hooks/resources";
import { useCopilotChat, useCreateConversation } from "@/lib/hooks/actions";
import { relativeTime } from "@/lib/format";
import type { ChatMessage } from "@/lib/api/types";

const PENDING_STAGES = [
  "Reading the conversation",
  "Retrieving from your knowledge base",
  "Reasoning with citations",
];

function localStages(active: number): ProcessingStep[] {
  return PENDING_STAGES.map((label, i) => ({
    id: `cstage-${i}`,
    label,
    status: (i < active ? "done" : i === active ? "active" : "pending") as ProcessingStep["status"],
  }));
}

export default function CopilotPage() {
  const conversations = useConversations();
  const createConversation = useCreateConversation();

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
                    Chats
                  </Button>
                </SheetTrigger>
                <SheetContent side="left" className="flex w-72 flex-col gap-0 p-0">
                  <SheetHeader className="border-b border-border/60 py-3">
                    <SheetTitle className="text-sm">Conversations</SheetTitle>
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
  className,
}: {
  query: ReturnType<typeof useConversations>;
  activeId: string | null;
  onSelect: (id: string | null) => void;
  onCreate: () => void;
  creating: boolean;
  className?: string;
}) {
  const items = query.data?.items ?? [];
  return (
    <aside className={cn("min-h-0 flex-col gap-2", className)} aria-label="Conversations">
      <Button variant="ai" size="sm" onClick={onCreate} loading={creating}>
        <Plus aria-hidden />
        New chat
      </Button>
      <ScrollArea className="min-h-0 flex-1">
        {query.isPending ? (
          <div className="space-y-2 py-2 pr-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <Skeleton key={i} className="h-14 rounded-lg" />
            ))}
          </div>
        ) : query.isError ? (
          <p className="px-1 py-3 text-xs text-muted-foreground">
            {isEndpointMissing(query.error)
              ? "Conversations aren't served by the backend yet."
              : "Couldn't load conversations."}
          </p>
        ) : !items.length ? (
          <p className="px-1 py-3 text-xs text-muted-foreground">
            No conversations yet — start one above.
          </p>
        ) : (
          <ul className="space-y-1 pr-2">
            {items.map((c) => (
              <li key={c.id}>
                <button
                  type="button"
                  onClick={() => onSelect(c.id)}
                  aria-current={activeId === c.id ? "true" : undefined}
                  className={cn(
                    "w-full rounded-lg border px-3 py-2 text-left transition-colors duration-150 focus-visible:ring-[3px] focus-visible:ring-primary/30",
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
              </li>
            ))}
          </ul>
        )}
      </ScrollArea>
    </aside>
  );
}

/* ------------------------------------------------------------------ */
/* New chat (no conversation selected)                                  */
/* ------------------------------------------------------------------ */

function NewChat({ onStart, pending }: { onStart: (message: string) => void; pending: boolean }) {
  const [value, setValue] = React.useState("");
  return (
    <div className="flex flex-1 items-center justify-center">
      <div className="w-full max-w-xl animate-fade-up space-y-6">
        <div className="text-center">
          <span className="mx-auto mb-3 flex size-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Sparkles className="size-6" aria-hidden />
          </span>
          <h1 className="font-serif text-display-md font-medium">Ask your career agent</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Grounded in your resumes, notes and saved jobs — every claim it makes is cited.
          </p>
        </div>
        <Card>
          <CardContent className="space-y-3">
            <Textarea
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="e.g. Which of my projects should I lead with for an LLM-platform role?"
              rows={3}
              className="resize-none"
              aria-label="First message to Copilot"
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey && value.trim()) {
                  e.preventDefault();
                  onStart(value.trim());
                }
              }}
            />
            <div className="flex items-center justify-between gap-2">
              <p className="text-2xs text-muted-foreground">Enter to send · Shift+Enter for a new line</p>
              <Button
                variant="ai"
                size="sm"
                disabled={!value.trim()}
                loading={pending}
                onClick={() => onStart(value.trim())}
              >
                <Send aria-hidden />
                Start chat
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
  const messages = useConversationMessages(conversationId);
  const chat = useCopilotChat();
  const [draft, setDraft] = React.useState("");
  const [transcript, setTranscript] = React.useState<ChatMessage[]>([]);
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
  }, [transcript.length, chat.isPending]);

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
                title="Chat history isn't connected yet"
                description="The /conversations endpoint isn't live — the API will populate this transcript as soon as it is. Nothing here is pre-filled."
                action={
                  <Button variant="outline" size="sm" onClick={() => void messages.refetch()}>
                    Check again
                  </Button>
                }
              />
            ) : (
              <ErrorState
                title="Couldn't load this conversation"
                error={messages.error}
                onRetry={() => void messages.refetch()}
                retrying={messages.isFetching}
              />
            )
          ) : transcript.length === 0 ? (
            <EmptyState
              icon={<Sparkles aria-hidden />}
              title="Ask anything about your search"
              description="Requests that mention experience, skills or jobs are answered from your knowledge base with citations — try “match my resume to my last saved job”."
            />
          ) : (
            transcript.map((m) => <MessageRow key={m.id} message={m} />)
          )}

          {chat.isPending && (
            <div className="flex animate-fade-up flex-col gap-2">
              <p className="flex items-center gap-1.5 text-2xs font-medium tracking-wide text-muted-foreground uppercase">
                <AIBadge label="copilot" /> thinking
              </p>
              <ProcessingSteps steps={localStages(1)} />
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
            placeholder="Message Copilot…"
            rows={1}
            className="max-h-40 min-h-10 resize-none"
            aria-label="Message Copilot"
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
            aria-label="Send message"
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
          {actions.map((a, i) => (
            <Button key={i} variant="outline" size="xs" asChild>
              <Link href={a.href!}>
                {a.label}
                <ArrowRight aria-hidden />
              </Link>
            </Button>
          ))}
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
