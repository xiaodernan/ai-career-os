"use client";

import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ThemeProvider } from "next-themes";
import { Toaster } from "@/components/ui/sonner";
import { registerServiceWorker } from "@/lib/pwa";

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        // Retry with backoff lives in `request` (lib/api/client.ts), which is the only
        // layer that can space the attempts out and the only one that covers mutations
        // as well as queries. Retrying here too would multiply it: one failing GET would
        // spend 7-10s in the client, then React Query would send it round again twice
        // more, so the reader would wait half a minute before seeing an error. The
        // policy itself is unchanged from the one that used to live here — the client
        // still refuses 4xx (401 refreshes, 408/429 and 5xx are the transient ones).
        retry: false,
      },
    },
  });
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(makeQueryClient);

  // The offline shell (19.7), registered once for the whole app. `registerServiceWorker` is a
  // no-op on the dev server and in browsers without one, and swallows a failed install: a
  // worker is a shell for the shipped product, never a requirement for it to open.
  useEffect(() => {
    void registerServiceWorker();
  }, []);

  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem disableTransitionOnChange>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
      <Toaster position="bottom-right" />
    </ThemeProvider>
  );
}
