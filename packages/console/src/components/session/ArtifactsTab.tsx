import { ArtifactCard } from './ArtifactCard';
import type { ArtifactMetadata } from '@/types/api';

interface ArtifactsTabProps {
  artifacts: ArtifactMetadata[] | undefined;
  frozenArtifacts: Record<string, string> | undefined;
  onArtifactClick: (artifact: ArtifactMetadata) => void;
}

export function ArtifactsTab({
  artifacts,
  frozenArtifacts,
  onArtifactClick,
}: ArtifactsTabProps) {
  if (!artifacts || artifacts.length === 0) {
    return <p className="text-sm text-muted-foreground py-2">No artifacts generated yet</p>;
  }

  return (
    <div className="flex flex-wrap gap-3 py-2">
      {artifacts.map((artifact) => (
        <ArtifactCard
          key={artifact.id}
          artifact={artifact}
          isFrozen={artifact.path ? frozenArtifacts?.[artifact.path] !== undefined : false}
          onClick={() => onArtifactClick(artifact)}
        />
      ))}
    </div>
  );
}
