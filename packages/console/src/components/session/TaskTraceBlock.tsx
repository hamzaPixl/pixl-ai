import { useState } from 'react';
import {
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  Loader2,
} from 'lucide-react';
import { cn, formatModelName, getModelBadgeColor } from '@/lib/utils';
import { ToolCallExpansion } from '@/components/ToolCallExpansion';
import { TraceEventRow } from '@/components/session/TraceEventRow';
import type { TaskTreeNode } from '@/lib/session-utils';

export function TaskTraceBlock({ task }: { task: TaskTreeNode }) {
  const [expanded, setExpanded] = useState(false);

  const statusConfig = {
    pending: { icon: <Clock className="h-4 w-4" />, color: 'text-muted-foreground', border: 'border-muted' },
    running: { icon: <Loader2 className="h-4 w-4 animate-spin" />, color: 'text-blue-500', border: 'border-blue-500/30' },
    completed: { icon: <CheckCircle2 className="h-4 w-4" />, color: 'text-green-500', border: 'border-green-500/30' },
    failed: { icon: <XCircle className="h-4 w-4" />, color: 'text-red-500', border: 'border-red-500/30' },
  };

  const { icon, color, border } = statusConfig[task.status];
  const hasChildren = task.children.length > 0;
  const isTerminal = task.status === 'completed' || task.status === 'failed';
  const isExpandable = hasChildren || isTerminal;

  const previewEvent = !expanded && hasChildren
    ? task.children.find((c) => c.kind === 'error')
      || task.children.find((c) => c.kind === 'tool')
      || task.children.find((c) => c.kind === 'gate')
      || task.children[0]
    : null;

  return (
    <div className={cn("border-l-2 pl-4 pb-2 transition-colors", border)}>
      <button
        className={cn("flex items-center gap-2 font-medium w-full text-left", color)}
        onClick={() => isExpandable && setExpanded((v) => !v)}
      >
        {isExpandable && (
          expanded
            ? <ChevronDown className="h-3 w-3 flex-shrink-0" />
            : <ChevronRight className="h-3 w-3 flex-shrink-0" />
        )}
        {icon}
        <div className="flex flex-col min-w-0">
          <span className="truncate">{task.nodeId}</span>
          {task.effectiveModel && (
            <div className="flex items-center gap-1 text-xs">
              <span
                className={cn("inline-flex items-center px-1.5 py-0.5 rounded-md font-medium", getModelBadgeColor(task.effectiveModel))}
              >
                {formatModelName(task.effectiveModel)}
              </span>
              {task.agentName && (
                <span className="text-muted-foreground">
                  via {task.agentName}
                </span>
              )}
            </div>
          )}
        </div>
        {task.status === 'running' && (
          <span className="text-xs text-muted-foreground">(running)</span>
        )}
        {hasChildren && (
          <span className="text-xs text-muted-foreground">
            ({task.children.length})
          </span>
        )}
        {task.durationSeconds !== undefined && (
          <span className="text-xs text-muted-foreground ml-auto flex-shrink-0 tabular-nums">
            {task.durationSeconds.toFixed(1)}s
          </span>
        )}
      </button>

      {/* Error message for failed tasks */}
      {task.status === 'failed' && task.errorMessage && (
        <div className="mt-1 flex items-start gap-2 text-xs">
          <AlertTriangle className="h-3 w-3 text-red-500 flex-shrink-0 mt-0.5" />
          <span className="text-red-500 break-words">{task.errorMessage}</span>
        </div>
      )}

      {/* Collapsed preview: show first high-signal event */}
      {previewEvent && !expanded && (
        <div className="mt-1 pl-1 text-xs text-muted-foreground italic truncate">
          {previewEvent.kind === 'tool' && `Tool: ${previewEvent.toolName}`}
          {previewEvent.kind === 'thinking' && `Thinking: "${previewEvent.text?.slice(0, 100)}..."`}
          {previewEvent.kind === 'text' && previewEvent.text?.slice(0, 120)}
          {previewEvent.kind === 'error' && <span className="text-red-400">{previewEvent.error?.slice(0, 120)}</span>}
          {previewEvent.kind === 'gate' && <span className="text-amber-500">Gate: {previewEvent.gateAction}</span>}
          {previewEvent.kind === 'query' && <span>Query: {previewEvent.model}</span>}
          {previewEvent.kind === 'recovery' && <span className="text-orange-500">Recovery: {previewEvent.recoveryAction}</span>}
          {previewEvent.kind === 'contract' && <span>Contract: {previewEvent.contractAction}</span>}
        </div>
      )}

      {/* Children (expanded) */}
      {expanded && hasChildren && (
        <div className="mt-2 space-y-2">
          {task.children.map((child) =>
            child.kind === 'tool' ? (
              <ToolCallExpansion
                key={child.id}
                toolCall={{
                  id: child.id,
                  toolName: child.toolName,
                  toolInput: child.toolInput || {},
                  timestamp: child.timestamp,
                  isError: child.isError,
                  errorMessage: child.errorMessage,
                  lifecycle: child.lifecycle,
                  duration: child.duration,
                }}
              />
            ) : (
              <TraceEventRow key={child.id} event={child} />
            )
          )}
        </div>
      )}

      {expanded && !hasChildren && isTerminal && (
        <div className="mt-2 text-xs text-muted-foreground italic pl-1">
          No trace events recorded for this task
        </div>
      )}
    </div>
  );
}
