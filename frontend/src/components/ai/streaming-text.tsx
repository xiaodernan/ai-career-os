"use client";

import * as React from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import { cn } from "@/lib/utils";

/**
 * StreamingText — renders AI token streams as sanitized markdown.
 * Security (architecture.md §8): rehype-sanitize whitelist, raw HTML is
 * stripped — AI output and retrieved documents are untrusted input.
 */
const COMPONENTS: Components = {
  p: ({ children }) => <p className="leading-relaxed [&:not(:first-child)]:mt-2">{children}</p>,
  h1: ({ children }) => <h3 className="mt-4 mb-1.5 text-base font-semibold">{children}</h3>,
  h2: ({ children }) => <h4 className="mt-3.5 mb-1.5 text-sm font-semibold">{children}</h4>,
  h3: ({ children }) => <h5 className="mt-3 mb-1 text-sm font-semibold">{children}</h5>,
  ul: ({ children }) => (
    <ul className="my-2 ml-4 list-disc space-y-1 marker:text-muted-foreground">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="my-2 ml-4 list-decimal space-y-1 marker:text-muted-foreground">{children}</ol>
  ),
  li: ({ children }) => <li className="pl-0.5 leading-relaxed">{children}</li>,
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-primary/40 pl-3 text-muted-foreground italic">
      {children}
    </blockquote>
  ),
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer nofollow"
      className="font-medium text-primary underline-offset-4 hover:underline"
    >
      {children}
    </a>
  ),
  code: ({ className, children, ...props }) => {
    const isBlock = /language-/.test(className ?? "");
    if (isBlock) return <code {...props} className={className}>{children}</code>;
    return (
      <code
        {...props}
        className="rounded-md border border-border/70 bg-muted px-1.5 py-0.5 font-mono text-[0.85em]"
      >
        {children}
      </code>
    );
  },
  pre: ({ children }) => (
    <pre className="my-3 overflow-x-auto rounded-lg border border-border/70 bg-muted/60 p-3 text-[0.8125rem] leading-relaxed">
      {children}
    </pre>
  ),
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-sm">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border-b border-border px-3 py-1.5 text-left font-medium">{children}</th>
  ),
  td: ({ children }) => <td className="border-b border-border/60 px-3 py-1.5">{children}</td>,
  hr: () => <hr className="my-4 border-border" />,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
};

const SANITIZE_SCHEMA = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    code: [...(defaultSchema.attributes?.code ?? []), ["className", /^language-/]],
  },
};

export interface StreamingTextProps extends React.ComponentProps<"div"> {
  content: string;
  /** Show a blinking caret while tokens are still arriving */
  streaming?: boolean;
}

function StreamingText({ content, streaming = false, className, ...props }: StreamingTextProps) {
  return (
    <div
      aria-live={streaming ? "polite" : undefined}
      className={cn("text-sm [&>*:first-child]:mt-0", className)}
      {...props}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, SANITIZE_SCHEMA]]}
        components={COMPONENTS}
      >
        {content + (streaming ? " ▍" : "")}
      </ReactMarkdown>
    </div>
  );
}

export { StreamingText };
