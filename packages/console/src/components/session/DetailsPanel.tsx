import { X, Clock, Brain, Cpu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { StepOutputViewer } from '@/components/StepOutputViewer';
import { formatModelName, getModelBadgeColor } from '@/lib/utils';
import type { NodeInstance } from '@/types/api';

interface DetailsPanelProps {
  selectedStageId: string;
  nodeInstance?: NodeInstance;
  onClose: () => void;
}

export function DetailsPanel({
  selectedStageId,
  nodeInstance,
  onClose,
}: DetailsPanelProps) {
  const duration = nodeInstance?.started_at && nodeInstance?.ended_at
    ? ((new Date(nodeInstance.ended_at).getTime() - new Date(nodeInstance.started_at).getTime()) / 1000).toFixed(1)
    : null;

  return (
    <div className="w-80 flex-shrink-0 overflow-y-auto border-l pl-4 hidden lg:block">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm font-medium text-muted-foreground">DETAILS</span>
        <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={onClose}>
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="space-y-4">
        {/* Stage Identity */}
        <div>
          <h3 className="font-medium text-sm">{selectedStageId}</h3>
          {nodeInstance?.state && (
            <Badge variant="outline" className="text-xs mt-1">{nodeInstance.state}</Badge>
          )}
        </div>

        <Separator />

        {/* Timing */}
        <div className="space-y-2">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            Timing
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {nodeInstance?.started_at && (
              <div>
                <span className="text-muted-foreground">Started</span>
                <br />
                <span className="font-mono">
                  {new Date(nodeInstance.started_at).toLocaleTimeString('en-US', {
                    hour12: false,
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
                </span>
              </div>
            )}
            {nodeInstance?.ended_at && (
              <div>
                <span className="text-muted-foreground">Ended</span>
                <br />
                <span className="font-mono">
                  {new Date(nodeInstance.ended_at).toLocaleTimeString('en-US', {
                    hour12: false,
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
                </span>
              </div>
            )}
            {duration && (
              <div>
                <span className="text-muted-foreground">Duration</span>
                <br />
                <span className="font-mono">{duration}s</span>
              </div>
            )}
            {nodeInstance?.attempt && nodeInstance.attempt > 1 && (
              <div>
                <span className="text-muted-foreground">Attempt</span>
                <br />
                <span className="font-mono">#{nodeInstance.attempt}</span>
              </div>
            )}
          </div>
        </div>

        <Separator />

        {/* Model / Agent */}
        {nodeInstance?.model_name && (
          <>
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Cpu className="h-3 w-3" />
                Model
              </div>
              <div className="flex items-center gap-1.5">
                <span className={`inline-flex items-center px-1.5 py-0.5 rounded-md text-xs font-medium ${getModelBadgeColor(nodeInstance.model_name)}`}>
                  {formatModelName(nodeInstance.model_name)}
                </span>
                {nodeInstance.agent_name && (
                  <span className="text-xs text-muted-foreground">via {nodeInstance.agent_name}</span>
                )}
              </div>
            </div>
            <Separator />
          </>
        )}

        {/* Token Usage */}
        {(nodeInstance?.input_tokens || nodeInstance?.output_tokens) && (
          <>
            <div className="space-y-2">
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Brain className="h-3 w-3" />
                Tokens
              </div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div>
                  <span className="text-muted-foreground">Input</span>
                  <br />
                  <span className="font-mono">{nodeInstance.input_tokens?.toLocaleString()}</span>
                </div>
                <div>
                  <span className="text-muted-foreground">Output</span>
                  <br />
                  <span className="font-mono">{nodeInstance.output_tokens?.toLocaleString()}</span>
                </div>
                {nodeInstance.cost_usd !== undefined && nodeInstance.cost_usd > 0 && (
                  <div className="col-span-2">
                    <span className="text-muted-foreground">Cost</span>
                    <br />
                    <span className="font-mono">${nodeInstance.cost_usd.toFixed(4)}</span>
                  </div>
                )}
              </div>
            </div>
            <Separator />
          </>
        )}

        {/* Error */}
        {nodeInstance?.error_message && (
          <>
            <div className="space-y-2">
              <span className="text-xs font-medium text-red-500">Error</span>
              <p className="text-xs text-red-400 break-words">{nodeInstance.error_message}</p>
              {nodeInstance.failure_kind && (
                <Badge variant="outline" className="text-[10px]">{nodeInstance.failure_kind}</Badge>
              )}
            </div>
            <Separator />
          </>
        )}

        {/* Step Output */}
        {nodeInstance && (
          <div className="space-y-2">
            <span className="text-xs text-muted-foreground">Output</span>
            <StepOutputViewer node={nodeInstance} />
          </div>
        )}
      </div>
    </div>
  );
}
