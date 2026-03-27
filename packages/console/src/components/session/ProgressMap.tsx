import { Skeleton } from '@/components/ui/skeleton';
import { Progress } from '@/components/ui/progress';
import { StageCard } from './StageCard';
import type { StageInfo } from '@/lib/session-utils';
import type { NodeInstance } from '@/types/api';

interface ProgressMapProps {
  stages: StageInfo[];
  currentStageId: string | undefined;
  nodeInstances: Record<string, NodeInstance> | undefined;
  selectedStageId: string | null;
  onSelectStage: (stageId: string) => void;
  isLoading: boolean;
}

export function ProgressMap({
  stages,
  currentStageId,
  nodeInstances,
  selectedStageId,
  onSelectStage,
  isLoading,
}: ProgressMapProps) {
  const completedCount = stages.filter((s) => s.state === 'completed').length;
  const progressPercent = stages.length > 0 ? Math.round((completedCount / stages.length) * 100) : 0;

  return (
    <div className="hidden md:flex md:flex-col min-w-[14rem] max-w-[18rem] flex-shrink-0 overflow-y-auto">
      <div className="text-sm font-medium text-muted-foreground mb-2">
        STAGES ({stages.length})
      </div>

      {stages.length > 0 && (
        <div className="flex items-center gap-2 mb-3">
          <Progress value={progressPercent} className="h-1.5 flex-1" />
          <span className="text-xs text-muted-foreground">{progressPercent}%</span>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      ) : stages.length === 0 ? (
        <p className="text-sm text-muted-foreground">No stages yet</p>
      ) : (
        <div className="space-y-1">
          {stages.map((stage) => (
            <StageCard
              key={stage.nodeId}
              stage={stage}
              isActive={stage.nodeId === currentStageId}
              isSelected={stage.nodeId === selectedStageId}
              nodeInstance={nodeInstances?.[stage.nodeId]}
              onClick={() => onSelectStage(stage.nodeId)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
