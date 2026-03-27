import {
  Clock,
  Play,
  CheckCircle2,
  XCircle,
  ChevronRight,
  ShieldQuestion,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { formatModelName, getModelBadgeColor } from '@/lib/utils';
import type { StageInfo } from '@/lib/session-utils';
import type { NodeInstance } from '@/types/api';

export function StageCard({ stage, isActive, isSelected, nodeInstance, onClick }: {
  stage: StageInfo;
  isActive: boolean;
  isSelected?: boolean;
  nodeInstance?: NodeInstance;
  onClick?: () => void;
}) {
  const icons: Record<StageInfo['state'], React.ReactNode> = {
    pending: <Clock className="h-4 w-4 text-muted-foreground" />,
    running: <Play className="h-4 w-4 text-blue-500" />,
    completed: <CheckCircle2 className="h-4 w-4 text-green-500" />,
    failed: <XCircle className="h-4 w-4 text-red-500" />,
    waiting: <ShieldQuestion className="h-4 w-4 text-yellow-500" />,
    skipped: <ChevronRight className="h-4 w-4 text-muted-foreground" />,
  };

  return (
    <button
      onClick={onClick}
      className={`w-full text-left border rounded-md bg-card transition-colors hover:bg-muted/50 ${
        isSelected
          ? 'ring-2 ring-ring'
          : stage.state === 'waiting'
          ? 'border-yellow-500/30 bg-yellow-500/5'
          : isActive
          ? 'border-blue-500/30 bg-blue-500/5'
          : 'border-transparent'
      }`}
    >
      <div className="flex items-center gap-2 px-3 py-2">
        {icons[stage.state]}
        <div className="flex-1 flex flex-col gap-1 min-w-0">
          <span className={`text-sm truncate ${isActive ? 'font-medium' : ''}`}>
            {stage.nodeId}
          </span>
          {nodeInstance?.model_name && (
            <div className="flex items-center gap-1">
              <span
                className={`inline-flex items-center px-1.5 py-0.5 rounded-md text-xs font-medium ${getModelBadgeColor(nodeInstance.model_name)}`}
              >
                {formatModelName(nodeInstance.model_name)}
              </span>
              {nodeInstance.agent_name && (
                <span className="text-xs text-muted-foreground">
                  via {nodeInstance.agent_name}
                </span>
              )}
            </div>
          )}
        </div>
        {stage.state === 'waiting' && (
          <Badge variant="outline" className="text-[10px] px-1 text-yellow-600 border-yellow-500/50">
            Awaiting
          </Badge>
        )}
        {stage.attempt > 1 && (
          <Badge variant="outline" className="text-xs px-1">
            #{stage.attempt}
          </Badge>
        )}
      </div>
    </button>
  );
}
