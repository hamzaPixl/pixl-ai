/**
 * ArtifactsTab — Aggregated artifact list with inline Sheet viewer.
 *
 * Groups artifacts by name/path (multiple versions → single row with count).
 * Click opens a Sheet with content viewer + version selector.
 */

import { useState, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { artifacts as artifactsApi } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Markdown } from "@/components/ui/markdown";
import {
  CodeBlock,
  CodeBlockCode,
  CodeBlockHeader,
} from "@/components/ui/code-block";
import { EmptyState } from "@/components/empty-state";
import {
  FileText,
  FileCode,
  FileJson,
  FileType,
  TestTube,
  ScrollText,
  Image,
  Database,
  Terminal,
  Eye,
  ChevronDown,
  Layers,
} from "lucide-react";
import type { ArtifactMetadata } from "@/types/api";

/* ── File extension → icon mapping ───────────────────────── */

const EXT_ICONS: Record<string, React.ReactNode> = {
  py: <FileCode className="h-4 w-4 text-yellow-500" />,
  ts: <FileCode className="h-4 w-4 text-blue-500" />,
  tsx: <FileCode className="h-4 w-4 text-blue-500" />,
  js: <FileCode className="h-4 w-4 text-yellow-400" />,
  jsx: <FileCode className="h-4 w-4 text-yellow-400" />,
  rs: <FileCode className="h-4 w-4 text-orange-500" />,
  go: <FileCode className="h-4 w-4 text-cyan-500" />,
  java: <FileCode className="h-4 w-4 text-red-500" />,
  rb: <FileCode className="h-4 w-4 text-red-400" />,
  php: <FileCode className="h-4 w-4 text-purple-400" />,
  swift: <FileCode className="h-4 w-4 text-orange-400" />,
  md: <FileText className="h-4 w-4 text-muted-foreground" />,
  mdx: <FileText className="h-4 w-4 text-muted-foreground" />,
  json: <FileJson className="h-4 w-4 text-yellow-600" />,
  yaml: <FileType className="h-4 w-4 text-pink-500" />,
  yml: <FileType className="h-4 w-4 text-pink-500" />,
  toml: <FileType className="h-4 w-4 text-gray-500" />,
  sql: <Database className="h-4 w-4 text-blue-400" />,
  sh: <Terminal className="h-4 w-4 text-green-500" />,
  bash: <Terminal className="h-4 w-4 text-green-500" />,
  css: <FileCode className="h-4 w-4 text-purple-500" />,
  html: <FileCode className="h-4 w-4 text-orange-500" />,
  png: <Image className="h-4 w-4 text-green-400" />,
  jpg: <Image className="h-4 w-4 text-green-400" />,
  svg: <Image className="h-4 w-4 text-green-400" />,
};

const TYPE_FALLBACK_ICONS: Record<string, React.ReactNode> = {
  code: <FileCode className="h-4 w-4 text-blue-500" />,
  test: <TestTube className="h-4 w-4 text-green-500" />,
  plan: <ScrollText className="h-4 w-4 text-amber-500" />,
  review: <FileText className="h-4 w-4 text-purple-500" />,
  document: <FileText className="h-4 w-4 text-cyan-500" />,
};

function getArtifactIcon(artifact: ArtifactMetadata): React.ReactNode {
  const name = (artifact.path || artifact.name || "").toLowerCase();
  const ext = name.split(".").pop() ?? "";
  return (
    EXT_ICONS[ext] ??
    TYPE_FALLBACK_ICONS[artifact.type] ?? (
      <FileText className="h-4 w-4 text-muted-foreground" />
    )
  );
}

/* ── Language inference (reused from artifact detail page) ── */

function inferLanguage(
  artifact: ArtifactMetadata,
): "markdown" | "code" | "json" | "yaml" | "plain" {
  const name = (artifact.name || artifact.path || "").toLowerCase();
  if (name.endsWith(".md") || name.endsWith(".mdx")) return "markdown";
  if (name.endsWith(".json")) return "json";
  if (name.endsWith(".yaml") || name.endsWith(".yml")) return "yaml";
  if (/\.(py|ts|tsx|js|jsx|rs|go|java|sh|rb|php|css|html|sql|swift|c|cpp|kt|scala|zig|toml)$/.test(name))
    return "code";
  if (artifact.type === "code" || artifact.type === "test") return "code";
  if (artifact.type === "plan" || artifact.type === "review" || artifact.type === "document")
    return "markdown";
  return "plain";
}

function inferShikiLanguage(artifact: ArtifactMetadata): string {
  const name = (artifact.name || artifact.path || "").toLowerCase();
  const ext = name.split(".").pop() ?? "";
  const map: Record<string, string> = {
    py: "python", ts: "typescript", tsx: "tsx", js: "javascript", jsx: "jsx",
    rs: "rust", go: "go", java: "java", sh: "bash", json: "json",
    yaml: "yaml", yml: "yaml", toml: "toml", css: "css", html: "html",
    sql: "sql", rb: "ruby", php: "php", c: "c", cpp: "cpp", swift: "swift",
    kt: "kotlin", scala: "scala", r: "r", lua: "lua", zig: "zig", md: "markdown",
  };
  return map[ext] ?? "plaintext";
}

/* ── Aggregation: group artifacts by name/path ───────────── */

interface ArtifactGroup {
  key: string;
  filename: string;
  latest: ArtifactMetadata;
  versions: ArtifactMetadata[];
}

function aggregateArtifacts(artifacts: ArtifactMetadata[]): ArtifactGroup[] {
  const groups = new Map<string, ArtifactMetadata[]>();
  for (const a of artifacts) {
    const key = a.path || a.name || a.id;
    const existing = groups.get(key);
    if (existing) {
      existing.push(a);
    } else {
      groups.set(key, [a]);
    }
  }

  return Array.from(groups.entries()).map(([key, versions]) => {
    const sorted = versions.sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    const displayName = key;
    const filename = displayName.split("/").pop() || displayName;
    return { key, filename, latest: sorted[0], versions: sorted };
  });
}

/* ── Content Viewer ──────────────────────────────────────── */

function ContentViewer({
  content,
  artifact,
  showRaw,
}: {
  content: string;
  artifact: ArtifactMetadata;
  showRaw: boolean;
}) {
  const language = inferLanguage(artifact);

  if (language === "markdown" && !showRaw) {
    return <Markdown>{content}</Markdown>;
  }

  if (language === "code" || language === "json" || language === "yaml") {
    const lang = inferShikiLanguage(artifact);
    return (
      <CodeBlock>
        <CodeBlockHeader language={lang} code={content} />
        <CodeBlockCode code={content} language={lang} />
      </CodeBlock>
    );
  }

  return (
    <pre className="bg-muted rounded-md p-4 text-xs overflow-x-auto whitespace-pre-wrap break-words font-mono">
      {content}
    </pre>
  );
}

/* ── Artifact Sheet Viewer ───────────────────────────────── */

function ArtifactSheet({
  group,
  open,
  onOpenChange,
}: {
  group: ArtifactGroup;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [showRaw, setShowRaw] = useState(false);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);

  const activeId = selectedVersionId ?? group.latest.id;
  const activeArtifact = group.versions.find((v) => v.id === activeId) ?? group.latest;

  const { data: contentData, isLoading } = useQuery({
    queryKey: ["artifact-content", activeId],
    queryFn: () => artifactsApi.getContent(activeId),
    enabled: open,
  });

  const language = inferLanguage(activeArtifact);
  const isMarkdown = language === "markdown";

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent
        side="right"
        className="w-full sm:max-w-2xl p-0 flex flex-col"
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b shrink-0">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2 font-mono text-sm pr-8">
              {getArtifactIcon(activeArtifact)}
              <span className="truncate">{group.filename}</span>
            </SheetTitle>
            <SheetDescription className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline" className="text-[10px]">
                {activeArtifact.type}
              </Badge>
              {activeArtifact.size_bytes && (
                <span className="text-[10px]">
                  {(activeArtifact.size_bytes / 1024).toFixed(1)} KB
                </span>
              )}
              <span className="text-[10px]">
                {new Date(activeArtifact.created_at).toLocaleString()}
              </span>
            </SheetDescription>
          </SheetHeader>
        </div>

        {/* Toolbar: version selector + raw toggle */}
        {(group.versions.length > 1 || isMarkdown) && (
          <div className="flex items-center gap-2 px-6 py-2 border-b shrink-0">
            {group.versions.length > 1 && (
              <>
                <div className="relative">
                  <select
                    value={activeId}
                    onChange={(e) => setSelectedVersionId(e.target.value)}
                    className="text-[11px] bg-muted/50 border rounded px-2 py-1 pr-6 appearance-none cursor-pointer"
                  >
                    {group.versions.map((v, i) => (
                      <option key={v.id} value={v.id}>
                        v{group.versions.length - i}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="h-3 w-3 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground" />
                </div>
                <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <Layers className="h-3 w-3" />
                  {group.versions.length} versions
                </span>
              </>
            )}
            {isMarkdown && (
              <Button
                variant={showRaw ? "outline" : "default"}
                size="sm"
                className="h-6 text-[10px] px-2 ml-auto"
                onClick={() => setShowRaw((v) => !v)}
              >
                {showRaw ? (
                  <Eye className="h-3 w-3 mr-1" />
                ) : (
                  <FileCode className="h-3 w-3 mr-1" />
                )}
                {showRaw ? "Rendered" : "Raw"}
              </Button>
            )}
          </div>
        )}

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          {isLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          ) : contentData?.content ? (
            <ContentViewer
              content={contentData.content}
              artifact={activeArtifact}
              showRaw={showRaw}
            />
          ) : (
            <p className="text-muted-foreground text-center py-8 text-xs">
              No content available
            </p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}

/* ── Main component ──────────────────────────────────────── */

export interface ArtifactsTabProps {
  artifacts: ArtifactMetadata[] | undefined;
  projectId: string;
}

export function ArtifactsTab({ artifacts }: ArtifactsTabProps) {
  const [selectedGroup, setSelectedGroup] = useState<ArtifactGroup | null>(null);

  const groups = useMemo(
    () => (artifacts ? aggregateArtifacts(artifacts) : []),
    [artifacts],
  );

  if (!artifacts || artifacts.length === 0) {
    return <EmptyState icon={FileText} title="No artifacts yet." />;
  }

  return (
    <>
      <div className="space-y-0.5">
        {groups.map((group) => (
          <button
            key={group.key}
            onClick={() => setSelectedGroup(group)}
            className="flex items-center gap-3 w-full px-2 py-2 rounded-md text-left transition-colors hover:bg-muted/50 group"
          >
            <span className="shrink-0">{getArtifactIcon(group.latest)}</span>
            <span
              className="text-sm font-medium truncate flex-1"
              title={group.key}
            >
              {group.filename}
            </span>
            <div className="flex items-center gap-2 shrink-0">
              {group.versions.length > 1 && (
                <Badge variant="outline" className="text-[10px] px-1.5 gap-0.5">
                  <Layers className="h-2.5 w-2.5" />
                  {group.versions.length}
                </Badge>
              )}
              <Badge variant="outline" className="text-[10px] px-1.5">
                {group.latest.type}
              </Badge>
              {group.latest.size_bytes && (
                <span className="text-[10px] text-muted-foreground">
                  {(group.latest.size_bytes / 1024).toFixed(1)} KB
                </span>
              )}
            </div>
          </button>
        ))}
      </div>

      {selectedGroup && (
        <ArtifactSheet
          group={selectedGroup}
          open={!!selectedGroup}
          onOpenChange={(open) => {
            if (!open) setSelectedGroup(null);
          }}
        />
      )}
    </>
  );
}
