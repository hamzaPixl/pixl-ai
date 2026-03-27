import { FileText, FileCode, TestTube, ExternalLink, Lock } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import type { ArtifactMetadata } from '@/types/api';

export function ArtifactCard({
  artifact,
  isFrozen,
  onClick,
}: {
  artifact: ArtifactMetadata;
  isFrozen: boolean;
  onClick?: () => void;
}) {
  const typeIcons: Record<string, React.ReactNode> = {
    document: <FileText className="h-4 w-4" />,
    code: <FileCode className="h-4 w-4" />,
    test: <TestTube className="h-4 w-4" />,
    review: <FileText className="h-4 w-4" />,
  };

  const icon = typeIcons[artifact.type] || <FileText className="h-4 w-4" />;

  const displayPath = artifact.path || artifact.name;
  const filename = displayPath.split('/').pop() || displayPath;

  return (
    <button
      onClick={onClick}
      className="flex-shrink-0 w-40 p-3 rounded-md border bg-card hover:bg-muted/50 transition-colors text-left cursor-pointer group">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-sm font-medium truncate flex-1" title={displayPath}>
          {filename}
        </span>
        <ExternalLink className="h-3 w-3 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground" />
      </div>
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Badge variant="outline" className="text-[10px] px-1">
          {artifact.type}
        </Badge>
        {isFrozen && (
          <span className="flex items-center gap-1 text-green-600">
            <Lock className="h-3 w-3" />
            frozen
          </span>
        )}
      </div>
    </button>
  );
}
