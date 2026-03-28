/**
 * Session Extras — Artifacts section.
 *
 * Renders below the unified timeline as a collapsible section.
 * Only appears when there are artifacts to show.
 *
 * Structured outputs, baton history, and context audit are per-stage
 * and rendered inside each NodeRow instead.
 */

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import {
  ChevronDown,
  ChevronRight,
  FileText,
  FileCode,
  TestTube,
  Lock,
  Package,
} from 'lucide-react';
import type { ArtifactMetadata } from '@/types/api';

interface SessionExtrasProps {
  artifacts: ArtifactMetadata[] | undefined;
  frozenArtifacts: Record<string, string> | undefined;
  onArtifactClick: (artifact: ArtifactMetadata) => void;
}

export function SessionExtras({
  artifacts,
  frozenArtifacts,
  onArtifactClick,
}: SessionExtrasProps) {
  const [open, setOpen] = useState(true);
  const hasArtifacts = artifacts && artifacts.length > 0;

  if (!hasArtifacts) return null;

  return (
    <div className="mt-4">
      <div className="rounded-md border bg-card">
        <button
          className="flex items-center gap-2 px-3 py-2 w-full text-left hover:bg-muted/30 transition-colors"
          onClick={() => setOpen((v) => !v)}
        >
          {open
            ? <ChevronDown className="h-3 w-3 text-muted-foreground" />
            : <ChevronRight className="h-3 w-3 text-muted-foreground" />}
          <span className="text-muted-foreground">
            <Package className="h-3.5 w-3.5" />
          </span>
          <span className="text-xs font-medium">Artifacts</span>
          <Badge variant="secondary" className="text-[10px] px-1 h-4 min-w-[1rem]">
            {artifacts.length}
          </Badge>
        </button>
        {open && (
          <div className="border-t px-3 py-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-1.5">
              {artifacts.map((artifact) => {
                const displayPath = artifact.path || artifact.name;
                const filename = displayPath.split('/').pop() || displayPath;
                const icon = TYPE_ICONS[artifact.type] || <FileText className="h-3.5 w-3.5" />;
                const frozen = artifact.path
                  ? frozenArtifacts?.[artifact.path] !== undefined
                  : false;

                return (
                  <button
                    key={artifact.id}
                    onClick={() => onArtifactClick(artifact)}
                    className="flex items-center gap-2 px-2.5 py-1.5 rounded-md hover:bg-muted/50 transition-colors text-left group"
                  >
                    <span className="text-muted-foreground flex-shrink-0">{icon}</span>
                    <div className="flex-1 min-w-0">
                      <span className="text-xs font-medium truncate block" title={displayPath}>
                        {filename}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 flex-shrink-0">
                      <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5">
                        {artifact.type}
                      </Badge>
                      {frozen && (
                        <Lock className="h-3 w-3 text-green-600" />
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

const TYPE_ICONS: Record<string, React.ReactNode> = {
  document: <FileText className="h-3.5 w-3.5" />,
  code: <FileCode className="h-3.5 w-3.5" />,
  test: <TestTube className="h-3.5 w-3.5" />,
  review: <FileText className="h-3.5 w-3.5" />,
};
