/**
 * Markdown renderer — based on prompt-kit/ibelick pattern.
 *
 * Uses marked for block-level tokenization + react-markdown for rendering.
 * Each block is memoized so only changed blocks re-render during streaming.
 *
 * Styling: @tailwindcss/typography `prose` classes with shadcn token overrides.
 * Code blocks: shiki syntax highlighting via CodeBlock component.
 */

import { cn } from "@/lib/utils";
import { marked } from "marked";
import { memo, useId, useMemo, type ComponentPropsWithoutRef } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkBreaks from "remark-breaks";
import remarkGfm from "remark-gfm";
import { CodeBlock, CodeBlockCode, CodeBlockHeader } from "./code-block";

export type MarkdownProps = {
  children: string;
  id?: string;
  className?: string;
  components?: Partial<Components>;
};

function parseMarkdownIntoBlocks(markdown: string): string[] {
  const tokens = marked.lexer(markdown);
  return tokens.map((token) => token.raw);
}

function extractLanguage(className?: string): string {
  if (!className) return "plaintext";
  const match = className.match(/language-(\w+)/);
  return match ? match[1] : "plaintext";
}

function extractCodeString(children: unknown): string {
  if (typeof children === "string") return children.replace(/\n$/, "");
  if (Array.isArray(children)) return children.map(extractCodeString).join("");
  return String(children ?? "");
}

const COMPONENTS: Partial<Components> = {
  code(props: ComponentPropsWithoutRef<"code">) {
    const { className, children, ...rest } = props;
    const isBlock =
      typeof className === "string" && className.startsWith("language-");

    if (!isBlock) {
      return (
        <code
          className={cn(
            "rounded-md border border-border/50 bg-muted/70 px-1.5 py-0.5 font-mono text-[13px] text-foreground",
            className
          )}
          {...rest}
        >
          {children}
        </code>
      );
    }

    const language = extractLanguage(className);
    const code = extractCodeString(children);

    return (
      <CodeBlock className="my-4">
        <CodeBlockHeader language={language} code={code} />
        <CodeBlockCode code={code} language={language} />
      </CodeBlock>
    );
  },

  pre({ children }) {
    // Unwrap <pre> — CodeBlock renders its own wrapper
    return <>{children}</>;
  },

  a({ href, children, ...props }) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="font-medium text-primary underline underline-offset-4 decoration-primary/40 hover:decoration-primary transition-colors"
        {...props}
      >
        {children}
      </a>
    );
  },

  ol({ children, ...props }) {
    return (
      <ol className="my-3 ml-6 list-decimal space-y-1.5 text-sm" {...props}>
        {children}
      </ol>
    );
  },

  ul({ children, ...props }) {
    return (
      <ul className="my-3 ml-6 list-disc space-y-1.5 text-sm" {...props}>
        {children}
      </ul>
    );
  },

  li({ children, ...props }) {
    return (
      <li className="leading-relaxed" {...props}>
        {children}
      </li>
    );
  },

  blockquote({ children, ...props }) {
    return (
      <blockquote
        className="my-3 border-l-2 border-border pl-4 text-muted-foreground not-italic"
        {...props}
      >
        {children}
      </blockquote>
    );
  },

  hr() {
    return <hr className="my-6 border-border" />;
  },

  table({ children }) {
    return (
      <div className="not-prose my-4 w-full overflow-x-auto rounded-lg border">
        <table className="w-full text-sm">{children}</table>
      </div>
    );
  },

  thead({ children }) {
    return <thead className="bg-muted/50">{children}</thead>;
  },

  th({ children, ...props }) {
    return (
      <th
        className="px-3 py-2 text-left text-xs font-semibold text-foreground border-b"
        {...props}
      >
        {children}
      </th>
    );
  },

  td({ children, ...props }) {
    return (
      <td
        className="px-3 py-2 text-sm border-b border-border/50"
        {...props}
      >
        {children}
      </td>
    );
  },
};

const MemoizedMarkdownBlock = memo(
  function MarkdownBlock({
    content,
    components,
  }: {
    content: string;
    components: Partial<Components>;
  }) {
    return (
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={components}>
        {content}
      </ReactMarkdown>
    );
  },
  (prev, next) => prev.content === next.content
);

MemoizedMarkdownBlock.displayName = "MemoizedMarkdownBlock";

function MarkdownComponent({
  children,
  id,
  className,
  components,
}: MarkdownProps) {
  const generatedId = useId();
  const blockId = id ?? generatedId;
  const blocks = useMemo(() => parseMarkdownIntoBlocks(children), [children]);
  const merged = useMemo(
    () => (components ? { ...COMPONENTS, ...components } : COMPONENTS),
    [components]
  );

  return (
    <div
      className={cn(
        "prose prose-sm dark:prose-invert max-w-none",
        // Fine-tune prose defaults
        "prose-headings:font-semibold prose-headings:tracking-tight",
        "prose-h1:text-xl prose-h1:border-b prose-h1:border-border prose-h1:pb-2",
        "prose-h2:text-lg prose-h2:border-b prose-h2:border-border/50 prose-h2:pb-1.5",
        "prose-h3:text-base",
        "prose-p:leading-relaxed",
        "prose-li:leading-relaxed",
        "prose-blockquote:border-l-border prose-blockquote:not-italic prose-blockquote:text-muted-foreground",
        "prose-hr:border-border",
        "prose-img:rounded-lg prose-img:border prose-img:border-border",
        "prose-strong:font-semibold",
        className
      )}
    >
      {blocks.map((block, index) => (
        <MemoizedMarkdownBlock
          key={`${blockId}-block-${index}`}
          content={block}
          components={merged}
        />
      ))}
    </div>
  );
}

const Markdown = memo(MarkdownComponent);
Markdown.displayName = "Markdown";

export { Markdown };
