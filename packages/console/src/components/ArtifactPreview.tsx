/**
 * Multi-format artifact previewer: code diff, HTML iframe, image, test summary table.
 */

import { TestSummary, type TestResult } from "@/components/TestSummary";
import { Separator } from "@/components/ui/separator";
import { Badge } from "@/components/ui/badge";

export type ArtifactType = "diff" | "html" | "image" | "test-summary" | "text";

export interface Artifact {
  type: ArtifactType;
  content: string;
  mimeType?: string;
  // For test-summary type
  tests?: TestResult[];
  confidenceScore?: number;
}

interface ArtifactPreviewProps {
  artifact: Artifact;
  className?: string;
}

export function ArtifactPreview({ artifact, className }: ArtifactPreviewProps) {
  return (
    <div className={className} data-testid="artifact-preview">
      <div className="flex items-center gap-2 mb-2">
        <Badge variant="outline" className="text-[10px] px-1.5 py-0">
          {artifact.type}
        </Badge>
      </div>
      <Separator className="mb-3" />
      <ArtifactContent artifact={artifact} />
    </div>
  );
}

function ArtifactContent({ artifact }: { artifact: Artifact }) {
  switch (artifact.type) {
    case "diff":
      return <DiffPreview content={artifact.content} />;
    case "html":
      return <HtmlPreview content={artifact.content} />;
    case "image":
      return <ImagePreview src={artifact.content} />;
    case "test-summary":
      return (
        <TestSummary
          tests={artifact.tests ?? []}
          confidenceScore={artifact.confidenceScore}
        />
      );
    default:
      return (
        <pre className="text-xs overflow-auto rounded-md bg-muted p-3 max-h-64 whitespace-pre-wrap break-words">
          {artifact.content}
        </pre>
      );
  }
}

function DiffPreview({ content }: { content: string }) {
  const lines = content.split("\n");
  return (
    <div className="rounded-md border overflow-auto max-h-64 font-mono text-xs">
      {lines.map((line, i) => {
        const isAdded = line.startsWith("+") && !line.startsWith("+++");
        const isRemoved = line.startsWith("-") && !line.startsWith("---");
        return (
          <div
            key={i}
            className={
              isAdded
                ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300 px-3 py-0.5"
                : isRemoved
                  ? "bg-red-50 text-red-800 dark:bg-red-950/30 dark:text-red-300 px-3 py-0.5"
                  : "px-3 py-0.5 text-muted-foreground"
            }
          >
            {line || " "}
          </div>
        );
      })}
    </div>
  );
}

function HtmlPreview({ content }: { content: string }) {
  return (
    <iframe
      srcDoc={content}
      className="w-full rounded-md border bg-white"
      style={{ height: 240 }}
      sandbox=""
      title="HTML preview"
    />
  );
}

function ImagePreview({ src }: { src: string }) {
  return (
    <div className="flex items-center justify-center rounded-md border bg-muted/30 p-2">
      <img
        src={src}
        alt="Artifact preview"
        className="max-h-64 max-w-full rounded object-contain"
      />
    </div>
  );
}
