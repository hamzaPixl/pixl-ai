/**
 * ArtifactDrawerContent — Artifact list + viewer for the unified drawer.
 *
 * Replaces both the inline ArtifactsPanel and the ArtifactInspector Dialog.
 * Shows a scrollable artifact list at the top, with selected artifact content
 * rendered below (markdown or raw).
 */

import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Markdown } from '@/components/ui/markdown';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { api } from '@/lib/api';
import {
  FileText,
  FileCode,
  TestTube,
  Lock,
  Eye,
  ChevronDown,
} from 'lucide-react';
import type { ArtifactMetadata } from '@/types/api';

const TYPE_ICONS: Record<string, React.ReactNode> = {
  document: <FileText className="h-3.5 w-3.5" />,
  code: <FileCode className="h-3.5 w-3.5" />,
  test: <TestTube className="h-3.5 w-3.5" />,
  review: <FileText className="h-3.5 w-3.5" />,
};

interface ArtifactDrawerContentProps {
  artifacts: ArtifactMetadata[];
  frozenArtifacts?: Record<string, string>;
  selectedArtifactId?: string;
  onSelectArtifact?: (artifactId: string) => void;
  sessionId: string;
}

export function ArtifactDrawerContent({
  artifacts,
  frozenArtifacts,
  selectedArtifactId,
  sessionId,
}: ArtifactDrawerContentProps) {
  const [selectedId, setSelectedId] = useState<string | null>(selectedArtifactId ?? null);
  const [showRaw, setShowRaw] = useState(false);

  const selectedArtifact = useMemo(
    () => artifacts.find(a => a.id === selectedId) ?? null,
    [artifacts, selectedId],
  );

  const { data: versions } = useQuery({
    queryKey: ['artifact-versions', selectedArtifact?.path, sessionId],
    queryFn: () =>
      selectedArtifact?.path
        ? api.artifacts.getVersions(selectedArtifact.path, sessionId)
        : Promise.resolve(selectedArtifact ? [selectedArtifact] : []),
    enabled: !!selectedArtifact,
  });

  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const activeVersionId = selectedVersionId ?? selectedId;

  const { data: content, isLoading: contentLoading } = useQuery({
    queryKey: ['artifact-content', activeVersionId],
    queryFn: () => api.artifacts.getContent(activeVersionId!),
    enabled: !!activeVersionId,
  });

  // Detect markdown
  const isMarkdown = useMemo(() => {
    const path = selectedArtifact?.path || selectedArtifact?.name || '';
    if (/\.(md|mdx|markdown)$/i.test(path)) return true;
    const text = content?.content;
    if (!text) return false;
    const lines = text.slice(0, 500).split('\n');
    let mdSignals = 0;
    for (const line of lines) {
      if (/^#{1,6}\s/.test(line)) mdSignals++;
      if (/^[-*]\s/.test(line)) mdSignals++;
      if (/^\d+\.\s/.test(line)) mdSignals++;
      if (/\[.+\]\(.+\)/.test(line)) mdSignals++;
      if (/^```/.test(line)) mdSignals++;
    }
    return mdSignals >= 2;
  }, [selectedArtifact?.path, selectedArtifact?.name, content?.content]);

  const currentVersionIndex = useMemo(() => {
    if (!versions || !activeVersionId) return 0;
    return versions.findIndex(v => v.id === activeVersionId);
  }, [versions, activeVersionId]);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      {/* Artifact list (scrollable) */}
      <div className="px-4 py-3 border-b shrink-0">
        <div className="text-xs font-medium text-muted-foreground mb-2">
          Artifacts ({artifacts.length})
        </div>
        <div className="max-h-[180px] overflow-y-auto space-y-0.5">
          {artifacts.map(artifact => {
            const displayPath = artifact.path || artifact.name;
            const filename = displayPath.split('/').pop() || displayPath;
            const icon = TYPE_ICONS[artifact.type] || <FileText className="h-3.5 w-3.5" />;
            const frozen = artifact.path ? frozenArtifacts?.[artifact.path] !== undefined : false;
            const isSelected = artifact.id === selectedId;

            return (
              <button
                key={artifact.id}
                onClick={() => {
                  setSelectedId(artifact.id);
                  setSelectedVersionId(null);
                  setShowRaw(false);
                }}
                className={`flex items-center gap-2 px-2 py-1.5 rounded-md w-full text-left transition-colors ${
                  isSelected ? 'bg-primary/10 border border-primary/30' : 'hover:bg-muted/50'
                }`}
              >
                <span className="text-muted-foreground flex-shrink-0">{icon}</span>
                <span className="text-[11px] font-medium truncate flex-1" title={displayPath}>
                  {filename}
                </span>
                <div className="flex items-center gap-1 flex-shrink-0">
                  <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5">
                    {artifact.type}
                  </Badge>
                  {frozen && <Lock className="h-3 w-3 text-green-600" />}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Selected artifact content */}
      {selectedArtifact ? (
        <div className="flex-1 flex flex-col min-h-0">
          {/* Toolbar */}
          <div className="flex items-center gap-2 px-4 py-2 border-b shrink-0">
            {/* Version selector */}
            {versions && versions.length > 1 && (
              <div className="relative">
                <select
                  value={activeVersionId ?? ''}
                  onChange={e => setSelectedVersionId(e.target.value)}
                  className="text-[11px] bg-muted/50 border rounded px-2 py-1 pr-6 appearance-none cursor-pointer"
                >
                  {versions.map((v, i) => (
                    <option key={v.id} value={v.id}>
                      v{i + 1}
                    </option>
                  ))}
                </select>
                <ChevronDown className="h-3 w-3 absolute right-1.5 top-1/2 -translate-y-1/2 pointer-events-none text-muted-foreground" />
              </div>
            )}
            {versions && versions.length > 1 && (
              <span className="text-[10px] text-muted-foreground">
                {currentVersionIndex + 1} of {versions.length}
              </span>
            )}

            {/* Raw/Rendered toggle */}
            {isMarkdown && (
              <Button
                variant={showRaw ? 'outline' : 'default'}
                size="sm"
                className="h-6 text-[10px] px-2 ml-auto"
                onClick={() => setShowRaw(v => !v)}
              >
                {showRaw ? <Eye className="h-3 w-3 mr-1" /> : <FileCode className="h-3 w-3 mr-1" />}
                {showRaw ? 'Rendered' : 'Raw'}
              </Button>
            )}
          </div>

          {/* Content area */}
          <div className="flex-1 overflow-auto p-4">
            {contentLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-5/6" />
              </div>
            ) : content?.content ? (
              isMarkdown && !showRaw ? (
                <Markdown id={activeVersionId ?? undefined}>
                  {content.content}
                </Markdown>
              ) : (
                <pre className="text-xs font-mono whitespace-pre-wrap break-words">
                  {content.content}
                </pre>
              )
            ) : (
              <p className="text-muted-foreground text-center py-8 text-xs">
                No content available
              </p>
            )}
          </div>
        </div>
      ) : (
        <div className="flex-1 flex items-center justify-center text-xs text-muted-foreground">
          Select an artifact to view
        </div>
      )}
    </div>
  );
}
