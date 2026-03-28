/**
 * Individual stage card for the workflow pipeline.
 *
 * Layout:
 * ┌──────────────────────────────────────────────────────────┐
 * │ [StatusIcon]  stage-name                  [TYPE BADGE]   │
 * │               agent: implementer  [model] [duration]     │
 * └──────────────────────────────────────────────────────────┘
 */

import { motion } from 'framer-motion';
import { Badge } from '@/components/ui/badge';
import { WorkflowStatusIcon, type NodeExecutionState } from './WorkflowStatusIcon';
import { getNodeLabel, NODE_STYLE, type NodeType } from '@/lib/dag-layout';
import { cn, formatModelName, getModelBadgeColor } from '@/lib/utils';
import type { WorkflowNodeDetail, NodeInstance } from '@/types/api';

interface WorkflowPipelineNodeProps {
  nodeId: string;
  node: WorkflowNodeDetail;
  executionState?: NodeExecutionState;
  isSelected: boolean;
  isHovered: boolean;
  activeType: NodeType | null;
  nodeInstance?: NodeInstance;
  hasExecutionStates: boolean;
  onSelect: (nodeId: string) => void;
  onHover: (nodeId: string | null) => void;
}

/** Compute human-readable duration from start/end timestamps. */
function formatDuration(startedAt: string | null, endedAt: string | null): string | null {
  if (!startedAt) return null;
  const start = new Date(startedAt).getTime();
  const end = endedAt ? new Date(endedAt).getTime() : Date.now();
  const ms = end - start;
  if (ms < 1000) return `${ms}ms`;
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const remSecs = secs % 60;
  return `${mins}m ${remSecs}s`;
}

export function WorkflowPipelineNode({
  nodeId,
  node,
  executionState,
  isSelected,
  isHovered,
  activeType,
  nodeInstance,
  hasExecutionStates,
  onSelect,
  onHover,
}: WorkflowPipelineNodeProps) {
  const style = NODE_STYLE[node.type as NodeType] ?? NODE_STYLE.task;
  const state = executionState?.state ?? 'pending';
  const dimmed = activeType !== null && node.type !== activeType;
  const isGateWaiting = node.type === 'gate' && state === 'waiting';
  const sublabel = getNodeLabel(node);
  const formattedModel = node.type === 'task' ? formatModelName(nodeInstance?.model_name) : null;
  const modelColor = formattedModel ? getModelBadgeColor(nodeInstance?.model_name) : null;
  const duration = nodeInstance ? formatDuration(nodeInstance.started_at, nodeInstance.ended_at) : null;
  const attempt = executionState?.attempt;

  const card = (
    <div
      className={cn(
        'relative flex items-start gap-2.5 rounded-lg border bg-popover px-3 py-2 cursor-pointer transition-all',
        'hover:bg-accent/50',
        isSelected && 'ring-2 ring-primary',
        isHovered && 'bg-accent/30',
        isGateWaiting && 'bg-amber-500/5 border-amber-500/30',
        dimmed && 'opacity-25',
        state === 'skipped' && 'opacity-30',
      )}
      onClick={() => onSelect(nodeId)}
      onMouseEnter={() => onHover(nodeId)}
      onMouseLeave={() => onHover(null)}
    >
      {/* Status icon */}
      <div className="shrink-0 mt-0.5">
        {hasExecutionStates ? (
          <WorkflowStatusIcon state={state} size="sm" />
        ) : (
          <div
            className="h-3.5 w-3.5 rounded-full opacity-60"
            style={{ backgroundColor: style.fill }}
          />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* First row: node ID + type badge */}
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold truncate">{nodeId}</span>
          <Badge
            variant="secondary"
            className="text-[10px] px-1.5 py-0 h-4 shrink-0"
            style={{ backgroundColor: `${style.fill}20`, color: style.fill }}
          >
            {style.label}
          </Badge>
          {attempt != null && attempt > 1 && (
            <Badge variant="outline" className="text-[10px] px-1 py-0 h-4 shrink-0 text-amber-600 border-amber-300">
              attempt {attempt}
            </Badge>
          )}
        </div>

        {/* Second row: sublabel + model + duration */}
        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
          {sublabel && (
            <span className="text-xs text-muted-foreground truncate">
              {node.type === 'task' ? `agent: ${sublabel}` : sublabel}
            </span>
          )}
          {formattedModel && modelColor && (
            <span className={cn('text-[10px] px-1.5 py-0 rounded font-medium', modelColor)}>
              {formattedModel}
            </span>
          )}
          {duration && (
            <span className="text-[10px] text-muted-foreground tabular-nums">{duration}</span>
          )}
          {isGateWaiting && (
            <span className="text-[10px] text-amber-600 font-medium">Awaiting Approval</span>
          )}
        </div>
      </div>
    </div>
  );

  // Wrap running nodes in a framer-motion pulse
  if (state === 'running') {
    return (
      <motion.div
        animate={{ backgroundColor: ['rgba(59,130,246,0)', 'rgba(59,130,246,0.04)', 'rgba(59,130,246,0)'] }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
        className="rounded-lg"
      >
        {card}
      </motion.div>
    );
  }

  return card;
}
