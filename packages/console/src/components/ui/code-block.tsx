/**
 * Code block with syntax highlighting via shiki.
 *
 * Based on prompt-kit pattern. Highlights asynchronously, shows
 * plain code as fallback while loading.
 */

import { cn } from "@/lib/utils";
import { Check, Clipboard } from "lucide-react";
import { useEffect, useState, type HTMLAttributes, type ReactNode } from "react";
import { codeToHtml } from "shiki";

function useIsDark() {
  const [isDark, setIsDark] = useState(() =>
    typeof document !== "undefined"
      ? document.documentElement.classList.contains("dark")
      : true
  );

  useEffect(() => {
    const el = document.documentElement;
    const observer = new MutationObserver(() => {
      setIsDark(el.classList.contains("dark"));
    });
    observer.observe(el, { attributes: true, attributeFilter: ["class"] });
    return () => observer.disconnect();
  }, []);

  return isDark;
}

// CodeBlock wrapper

export type CodeBlockProps = {
  children?: ReactNode;
  className?: string;
} & HTMLAttributes<HTMLDivElement>;

function CodeBlock({ children, className, ...props }: CodeBlockProps) {
  return (
    <div
      className={cn(
        "not-prose flex w-full flex-col overflow-clip border",
        "border-border bg-card text-card-foreground rounded-lg",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

// CodeBlockCode — highlighted code area

export type CodeBlockCodeProps = {
  code: string;
  language?: string;
  theme?: string;
  className?: string;
} & HTMLAttributes<HTMLDivElement>;

function CodeBlockCode({
  code,
  language = "plaintext",
  theme: themeProp,
  className,
  ...props
}: CodeBlockCodeProps) {
  const isDark = useIsDark();
  const theme = themeProp ?? (isDark ? "github-dark-default" : "github-light-default");
  const [highlightedHtml, setHighlightedHtml] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function highlight() {
      if (!code) {
        setHighlightedHtml("<pre><code></code></pre>");
        return;
      }
      try {
        const html = await codeToHtml(code, { lang: language, theme });
        if (!cancelled) setHighlightedHtml(html);
      } catch {
        // Language not supported — render plain
        if (!cancelled) setHighlightedHtml(null);
      }
    }
    highlight();
    return () => { cancelled = true; };
  }, [code, language, theme]);

  const classNames = cn(
    "w-full overflow-x-auto text-[13px] [&>pre]:px-4 [&>pre]:py-3 [&_pre]:!bg-transparent",
    className
  );

  return highlightedHtml ? (
    <div
      className={classNames}
      dangerouslySetInnerHTML={{ __html: highlightedHtml }}
      {...props}
    />
  ) : (
    <div className={classNames} {...props}>
      <pre className="px-4 py-3">
        <code>{code}</code>
      </pre>
    </div>
  );
}

// CodeBlockHeader — language label + copy button

function CodeBlockHeader({
  language,
  code,
  className,
}: {
  language: string;
  code: string;
  className?: string;
}) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={cn(
        "flex items-center justify-between bg-muted/60 px-3 py-1.5 text-[11px] text-muted-foreground border-b",
        className
      )}
    >
      <span className="font-medium">{language}</span>
      <button
        onClick={handleCopy}
        className="flex items-center gap-1 hover:text-foreground transition-colors"
      >
        {copied ? (
          <Check className="h-3 w-3 text-green-500" />
        ) : (
          <Clipboard className="h-3 w-3" />
        )}
      </button>
    </div>
  );
}

export { CodeBlock, CodeBlockCode, CodeBlockHeader };
