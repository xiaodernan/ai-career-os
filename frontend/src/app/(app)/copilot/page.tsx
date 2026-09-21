"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { MessageSquare, Plus } from "lucide-react";
import { ModuleView } from "@/components/common/module-view";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import { endpoints } from "@/lib/api/endpoints";
import type { Conversation } from "@/lib/api/types";
import { useConversations } from "@/lib/hooks/resources";

export default function CopilotPage() {
  const conversations = useConversations();
  const qc = useQueryClient();
  const router = useRouter();

  const createChat = useMutation({
    mutationFn: () => api.create<Conversation>(endpoints.conversations, { title: "New chat" }),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ["conversations"] });
      toast.success("Chat started.");
      router.push(`/copilot?c=${c.id}`);
    },
    onError: (err) =>
      toast.error(err instanceof Error && err.message ? err.message : "The conversation API isn't live yet."),
  });

  return (
    <ModuleView
      title="Copilot"
      description="The career agent — grounded in your knowledge base, streaming its reasoning and citing evidence."
      query={conversations}
      emptyHint={{
        title: "No conversations yet",
        description: "Ask about a JD, request a match breakdown or plan interview prep.",
      }}
      actions={
        <Button variant="ai" size="sm" onClick={() => createChat.mutate()} loading={createChat.isPending}>
          <Plus aria-hidden />
          New chat
        </Button>
      }
      renderItem={(c) => (
        <Card key={c.id} className="cursor-pointer transition-shadow duration-150 hover:shadow-pop"
          onClick={() => router.push(`/copilot?c=${c.id}`)}
        >
          <CardContent className="flex items-center gap-3">
            <span className="flex size-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <MessageSquare className="size-4.5" aria-hidden />
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{c.title}</p>
              {c.lastMessagePreview && (
                <p className="truncate text-xs text-muted-foreground">{c.lastMessagePreview}</p>
              )}
            </div>
            {c.updatedAt && (
              <span className="shrink-0 text-xs text-muted-foreground">
                {new Date(c.updatedAt).toLocaleDateString()}
              </span>
            )}
          </CardContent>
        </Card>
      )}
    />
  );
}
