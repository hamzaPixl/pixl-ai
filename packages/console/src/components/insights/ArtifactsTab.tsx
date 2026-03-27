import { useState, useMemo } from "react";
import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Cell } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  type ChartConfig,
} from "@/components/ui/chart";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { artifacts } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { EmptyState } from "@/components/empty-state";
import { LoadingSkeletons } from "@/components/loading-skeletons";
import { Markdown } from "@/components/ui/markdown";
import {
  CodeBlock,
  CodeBlockCode,
  CodeBlockHeader,
} from "@/components/ui/code-block";
import { FileText, ExternalLink, Eye, FileCode } from "lucide-react";
import { Button } from "@/components/ui/button";
import { FileTypeIcon, getExtColor } from "@/components/file-type-icon";

function getExtension(path: string | null, name: string): string {
  const source = path ?? name;
  const dot = source.lastIndexOf(".");
  return dot >= 0 ? source.slice(dot).toLowerCase() : "other";
}

export interface ArtifactsTabProps {
  projectId: string;
}

type ArtifactEntry = {
  id: string;
  name: string;
  path: string | null;
  type: string;
  ext: string;
  sizeKb: number;
  sessionId: string;
  taskId: string;
  createdAt: string;
  tags: string[];
  mimeType: string | null;
};

export function ArtifactsTab({ projectId }: ArtifactsTabProps) {
  const [selected, setSelected] = useState<ArtifactEntry | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.artifacts.list(projectId, { limit: 200, offset: 0 }),
    queryFn: () => artifacts.list({ limit: 200, offset: 0 }),
  });

  const chartData = useMemo((): ArtifactEntry[] => {
    if (!data || data.length === 0) return [];
    return data.map((a) => ({
      id: a.id,
      name: a.name,
      path: a.path,
      type: a.type,
      ext: getExtension(a.path, a.name),
      sizeKb: Math.max((a.size_bytes ?? 0) / 1024, 0.1),
      sessionId: a.session_id,
      taskId: a.task_id,
      createdAt: a.created_at,
      tags: a.tags ?? [],
      mimeType: a.mime_type,
    }));
  }, [data]);

  // Treemap: group by file extension (GitHub-style language breakdown)
  const { treemapData, extColorMap } = useMemo(() => {
    if (chartData.length === 0)
      return { treemapData: [], extColorMap: new Map<string, string>() };
    const counts = new Map<string, { count: number; bytes: number }>();
    for (const a of chartData) {
      const prev = counts.get(a.ext) ?? { count: 0, bytes: 0 };
      prev.count += 1;
      prev.bytes += a.sizeKb;
      counts.set(a.ext, prev);
    }
    const sorted = [...counts.entries()].sort(
      (a, b) => b[1].bytes - a[1].bytes,
    );
    const colorMap = new Map<string, string>();
    const items = sorted.map(([ext, { count, bytes }]) => {
      const color = getExtColor(ext);
      colorMap.set(ext, color);
      return { name: ext, size: bytes, count, fill: color };
    });
    return { treemapData: items, extColorMap: colorMap };
  }, [chartData]);

  const chartConfig = useMemo<ChartConfig>(
    () => ({
      artifacts: { label: "Artifacts" },
      sizeKb: { label: "Size (KB)" },
    }),
    [],
  );

  return (
    <div className="space-y-6">
      {isLoading ? (
        <LoadingSkeletons count={4} />
      ) : chartData.length > 0 ? (
        <div className="rounded-lg border border-border p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-medium text-muted-foreground">
              All artifacts
            </h3>
            <span className="text-xs text-muted-foreground/70 tabular-nums">
              {chartData.length} total
            </span>
          </div>
          <ChartContainer config={chartConfig} className="h-64 w-full">
            <BarChart data={chartData}>
              <XAxis dataKey="name" hide />
              <YAxis
                tick={{ fontSize: 10 }}
                tickLine={false}
                axisLine={false}
                width={36}
                tickFormatter={(v: number) => `${v.toFixed(0)}`}
                label={{
                  value: "KB",
                  position: "insideTopLeft",
                  offset: -4,
                  style: { fontSize: 9, fill: "var(--muted-foreground)" },
                }}
              />
              <ChartTooltip
                cursor={false}
                content={({ active, payload }) => {
                  if (!active || !payload?.[0]) return null;
                  const d = payload[0].payload as ArtifactEntry;
                  return (
                    <div className="rounded-lg border border-border bg-background px-3 py-2 text-xs shadow-md space-y-1">
                      <div className="flex items-center gap-1.5">
                        <FileTypeIcon
                          ext={d.ext}
                          className="h-3.5 w-3.5 shrink-0"
                        />
                        <p className="font-medium">{d.name}</p>
                      </div>
                      <p className="text-muted-foreground">
                        {d.ext} · {d.sizeKb.toFixed(1)} KB
                      </p>
                    </div>
                  );
                }}
              />
              <Bar
                dataKey="sizeKb"
                radius={[3, 3, 0, 0]}
                className="cursor-pointer"
                onClick={(_: unknown, index: number) =>
                  setSelected(chartData[index])
                }
              >
                {chartData.map((entry) => (
                  <Cell
                    key={entry.id}
                    fill={extColorMap.get(entry.ext) ?? "#6b7280"}
                  />
                ))}
              </Bar>
            </BarChart>
          </ChartContainer>

          {/* GitHub-style language bar */}
          {(() => {
            const totalSize = treemapData.reduce((s, t) => s + t.size, 0);
            return (
              <div className="space-y-3">
                <div className="flex h-2 w-full overflow-hidden rounded-full">
                  {treemapData.map((t) => (
                    <div
                      key={t.name}
                      className="h-full transition-all"
                      style={{
                        backgroundColor: t.fill,
                        width: `${(t.size / totalSize) * 100}%`,
                      }}
                    />
                  ))}
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1.5">
                  {treemapData.map((t) => (
                    <div
                      key={t.name}
                      className="flex items-center gap-1.5 text-xs"
                    >
                      <FileTypeIcon
                        ext={t.name}
                        className="h-3.5 w-3.5 shrink-0"
                      />
                      <span className="font-medium">{t.name}</span>
                      <span className="text-muted-foreground tabular-nums">
                        {((t.size / totalSize) * 100).toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            );
          })()}
        </div>
      ) : (
        <EmptyState icon={FileText} title="No artifacts yet" />
      )}

      {/* Artifact detail sidebar */}
      <Sheet
        open={!!selected}
        onOpenChange={(open) => !open && setSelected(null)}
      >
        <SheetContent className="overflow-y-auto sm:max-w-2xl">
          {selected && (
            <ArtifactSheetBody artifact={selected} projectId={projectId} />
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

/** Map extension string (e.g. ".yml") to a shiki language id. */
const EXT_TO_LANG: Record<string, string> = {
  ".py": "python", ".ts": "typescript", ".tsx": "tsx", ".js": "javascript",
  ".jsx": "jsx", ".rs": "rust", ".go": "go", ".java": "java", ".sh": "bash",
  ".json": "json", ".yaml": "yaml", ".yml": "yaml", ".toml": "toml",
  ".css": "css", ".html": "html", ".sql": "sql", ".rb": "ruby", ".php": "php",
  ".c": "c", ".cpp": "cpp", ".swift": "swift", ".kt": "kotlin",
  ".scala": "scala", ".r": "r", ".lua": "lua", ".zig": "zig",
  ".prisma": "prisma", ".graphql": "graphql", ".xml": "xml",
};

const MARKDOWN_EXTS = new Set([".md", ".mdx", ".markdown"]);
const CODE_EXTS = new Set(Object.keys(EXT_TO_LANG));

function ArtifactSheetBody({
  artifact,
  projectId,
}: {
  artifact: ArtifactEntry;
  projectId: string;
}) {
  const [showRaw, setShowRaw] = useState(false);

  const { data: contentData, isLoading: contentLoading } = useQuery({
    queryKey: queryKeys.artifacts.content(projectId, artifact.id),
    queryFn: () => artifacts.getContent(artifact.id),
  });

  const isMarkdown = MARKDOWN_EXTS.has(artifact.ext) ||
    artifact.type === "plan" || artifact.type === "review" || artifact.type === "document";
  const isCode = CODE_EXTS.has(artifact.ext) && !isMarkdown;
  const shikiLang = EXT_TO_LANG[artifact.ext] ?? "plaintext";

  return (
    <>
      <SheetHeader>
        <div className="flex items-center gap-2">
          <FileTypeIcon ext={artifact.ext} className="h-5 w-5 shrink-0" />
          <SheetTitle className="truncate">{artifact.name}</SheetTitle>
        </div>
      </SheetHeader>

      <div className="mt-6 space-y-5">
        {/* Metadata */}
        <dl className="space-y-3 text-sm">
          <MetaRow label="ID" value={artifact.id} mono />
          {artifact.path && <MetaRow label="Path" value={artifact.path} mono />}
          <MetaRow label="Extension" value={artifact.ext} />
          <MetaRow label="Type" value={artifact.type} />
          {artifact.mimeType && (
            <MetaRow label="MIME" value={artifact.mimeType} mono />
          )}
          <MetaRow label="Size" value={`${artifact.sizeKb.toFixed(1)} KB`} />
          <MetaRow
            label="Created"
            value={new Date(artifact.createdAt).toLocaleString()}
          />
          <MetaRow label="Task" value={artifact.taskId} mono />
        </dl>

        {/* Tags */}
        {artifact.tags.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs font-medium text-muted-foreground">Tags</p>
            <div className="flex flex-wrap gap-1.5">
              {artifact.tags.map((tag) => (
                <Badge key={tag} variant="outline" className="text-xs">
                  {tag}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Session link */}
        <div className="pt-2 border-t border-border">
          <Link
            to="/project/$projectId/sessions/$sessionId"
            params={{ projectId, sessionId: artifact.sessionId }}
            className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
          >
            <ExternalLink className="h-3.5 w-3.5" />
            View session {artifact.sessionId.slice(0, 12)}…
          </Link>
        </div>

        {/* File content */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-muted-foreground">Content</p>
            {isMarkdown && contentData?.content && (
              <Button
                variant={showRaw ? "outline" : "default"}
                size="sm"
                className="h-6 text-[10px] px-2"
                onClick={() => setShowRaw((v) => !v)}
              >
                {showRaw ? <Eye className="h-3 w-3 mr-1" /> : <FileCode className="h-3 w-3 mr-1" />}
                {showRaw ? "Rendered" : "Raw"}
              </Button>
            )}
          </div>
          {contentLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-5/6" />
            </div>
          ) : contentData?.content ? (
            isMarkdown && !showRaw ? (
              <div className="max-h-[60vh] overflow-y-auto rounded-md border border-border p-4">
                <Markdown>{contentData.content}</Markdown>
              </div>
            ) : isCode ? (
              <div className="max-h-[60vh] overflow-y-auto">
                <CodeBlock>
                  <CodeBlockHeader language={shikiLang} code={contentData.content} />
                  <CodeBlockCode code={contentData.content} language={shikiLang} />
                </CodeBlock>
              </div>
            ) : (
              <pre className="rounded-md border border-border bg-muted/50 p-3 text-xs font-mono overflow-x-auto max-h-[60vh] overflow-y-auto whitespace-pre-wrap break-words">
                {contentData.content}
              </pre>
            )
          ) : (
            <p className="text-xs text-muted-foreground italic">
              No content available (chunked or binary)
            </p>
          )}
        </div>
      </div>
    </>
  );
}

function MetaRow({
  label,
  value,
  mono,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-muted-foreground shrink-0">{label}</dt>
      <dd className={`text-right truncate ${mono ? "font-mono" : ""}`}>
        {value}
      </dd>
    </div>
  );
}
