/**
 * Vertical connector line between pipeline nodes.
 *
 * Color is driven by the source node's execution state. Supports
 * loop, branching, and merging indicators.
 */

import { RefreshCw, GitBranch, GitMerge } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { ExecutionState } from './WorkflowStatusIcon';

interface WorkflowPipelineConnectorProps {
  sourceState?: ExecutionState;
  type?: 'normal' | 'loop' | 'failure';
  loopLabel?: string;
  isBranching?: boolean;
  isMerging?: boolean;
}

const STATE_LINE_COLOR: Partial<Record<ExecutionState, string>> = {
  completed: 'bg-green-500/60',
  failed: 'bg-red-500/60',
  running: 'bg-blue-500/60',
};

export function WorkflowPipelineConnector({
  sourceState,
  type = 'normal',
  loopLabel,
  isBranching,
  isMerging,
}: WorkflowPipelineConnectorProps) {
  const lineColor = (sourceState && STATE_LINE_COLOR[sourceState]) ?? 'bg-border';
  const isLoop = type === 'loop';
  const isFailure = type === 'failure';

  return (
    <div className="flex flex-col items-center gap-0.5 py-0.5">
      {/* Branching indicator */}
      {isBranching && (
        <div className="flex items-center gap-1 text-muted-foreground mb-0.5">
          <GitBranch className="h-3 w-3" />
          <span className="text-[10px]">parallel</span>
        </div>
      )}

      {/* Merging indicator */}
      {isMerging && (
        <div className="flex items-center gap-1 text-muted-foreground mb-0.5">
          <GitMerge className="h-3 w-3" />
          <span className="text-[10px]">merge</span>
        </div>
      )}

      {/* Vertical line */}
      <div
        className={cn(
          'w-0.5 h-6 mx-auto rounded-full transition-colors',
          lineColor,
          isLoop && 'border border-dashed border-muted-foreground/40 bg-transparent w-px',
          isFailure && 'bg-red-500/30',
        )}
      />

      {/* Loop label */}
      {isLoop && loopLabel && (
        <div className="flex items-center gap-1 text-muted-foreground">
          <RefreshCw className="h-2.5 w-2.5" />
          <span className="text-[10px]">{loopLabel}</span>
        </div>
      )}
    </div>
  );
}
