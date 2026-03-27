import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ToolCallExpansion } from "@/components/ToolCallExpansion";
import { TraceEventRow } from "@/components/session";
import { computeNodeStats } from "@/hooks/use-node-stats";
import { formatModelName, getModelBadgeColor } from "@/lib/utils";
import { Clock, AlertTriangle, RefreshCw, Check, X } from "lucide-react";
import type { UnifiedNode } from "@/lib/session-constants";
import type {
  StageOutputPayload,
  BatonHistoryEntry,
  ContextAuditEntry,
} from "@/types/api";
import {
  NodeStructuredOutput,
  InlineOutput,
  hasNodeOutput,
} from "@/components/session/OutputRenderer";
import { NodeBatonDetail } from "@/components/session/BatonDetail";

export interface NodeDetailDrawerProps {
  node: UnifiedNode;
  structuredOutput?: StageOutputPayload;
  batonEntry?: BatonHistoryEntry;
  contextAudit?: ContextAuditEntry;
  onApprove?: () => void;
  onReject?: () => void;
  onRetryNode?: () => void;
}

export function NodeDetailDrawer({
  node,
  structuredOutput,
  batonEntry,
  contextAudit,
  onApprove,
  onReject,
  onRetryNode,
}: NodeDetailDrawerProps) {
  type SectionKey = "events" | "output" | "baton";
  const [activeSection, setActiveSection] = useState<SectionKey | null>(
    "events",
  );

  const inst = node.nodeInstance;
  const task = node.taskNode;
  const {
    modelName,
    agentName,
    duration,
    eventCount,
    inputTokens,
    outputTokens,
    costUsd,
    ctxPct,
    ctxColor,
  } = computeNodeStats(node, contextAudit);
  const hasEvents = eventCount > 0;
  const hasOutput = inst && hasNodeOutput(inst);
  const hasError =
    node.state === "failed" && !!(task?.errorMessage || inst?.error_message);

  return (
    <div className="flex flex-col flex-1 min-h-0">
      <div className="px-6 py-3 border-b space-y-2 shrink-0">
        <div className="flex items-center gap-2 flex-wrap">
          {modelName && (
            <span
              className={`inline-flex items-center px-1.5 py-0.5 rounded-md text-[11px] font-medium ${getModelBadgeColor(modelName)}`}
            >
              {formatModelName(modelName)}
            </span>
          )}
          {agentName && (
            <Badge
              variant="secondary"
              className="text-[11px] px-1.5 py-0 h-5 font-medium"
            >
              {agentName}
            </Badge>
          )}
          {node.attempt > 1 && (
            <Badge variant="outline" className="text-[10px] px-1">
              Attempt #{node.attempt}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-3 text-[11px] text-muted-foreground flex-wrap">
          {duration !== undefined && (
            <span className="flex items-center gap-1 tabular-nums">
              <Clock className="h-3 w-3" />
              {duration < 0.1 ? "<0.1" : duration.toFixed(1)}s
            </span>
          )}
          {eventCount > 0 && (
            <span className="tabular-nums">{eventCount} events</span>
          )}
          {(inputTokens != null || outputTokens != null) && (
            <span className="tabular-nums">
              {inputTokens != null && <>{inputTokens.toLocaleString()} in</>}
              {inputTokens != null && outputTokens != null && (
                <span className="mx-1 text-muted-foreground/50">/</span>
              )}
              {outputTokens != null && <>{outputTokens.toLocaleString()} out</>}
            </span>
          )}
          {costUsd !== undefined && costUsd > 0 && (
            <span className="tabular-nums">${costUsd.toFixed(4)}</span>
          )}
        </div>

        {contextAudit && ctxPct !== null && (
          <div className="flex items-center gap-2.5 text-[11px] text-muted-foreground">
            <span className="text-muted-foreground/70">ctx</span>
            <div className="w-24 flex-shrink-0">
              <Progress
                value={Math.min(ctxPct, 100)}
                className={`h-1.5 ${ctxPct > 95 ? "[&>div]:bg-red-500" : ctxPct > 80 ? "[&>div]:bg-yellow-500" : "[&>div]:bg-green-500"}`}
              />
            </div>
            <span className={`tabular-nums font-medium ${ctxColor}`}>
              {ctxPct}%
            </span>
            <span className="tabular-nums">
              {contextAudit.total_tokens.toLocaleString()} /{" "}
              {contextAudit.budget_tokens.toLocaleString()}
            </span>
          </div>
        )}
      </div>

      {hasError && (
        <div className="flex items-start gap-2 p-3 mx-4 mt-3 rounded-md bg-red-500/10 border border-red-500/30">
          <AlertTriangle className="h-3.5 w-3.5 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-xs text-red-500 break-words">
              {task?.errorMessage || inst?.error_message}
            </p>
            {inst?.failure_kind && (
              <Badge variant="outline" className="text-[10px] mt-1">
                {inst.failure_kind}
              </Badge>
            )}
          </div>
        </div>
      )}
      {node.state === "failed" && onRetryNode && (
        <div className="border-t mx-4 mt-3 pt-3 flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs"
            onClick={onRetryNode}
          >
            <RefreshCw className="h-3 w-3 mr-1" />
            Retry this node
          </Button>
        </div>
      )}

      {hasOutput && (
        <div className="bg-muted/30 rounded-md p-2 mx-4 mt-3 text-xs">
          <InlineOutput output={(inst as any).output} />
        </div>
      )}

      {node.state === "waiting" && onApprove && (
        <div className="border-t mx-4 mt-3 pt-3 flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-destructive hover:bg-destructive hover:text-destructive-foreground h-8 text-xs"
            onClick={onReject}
          >
            <X className="h-3 w-3 mr-1" />
            Reject
          </Button>
          <Button
            size="sm"
            className="flex-1 bg-green-600 hover:bg-green-700 h-8 text-xs"
            onClick={onApprove}
          >
            <Check className="h-3 w-3 mr-1" />
            Approve
          </Button>
        </div>
      )}

      <div className="mt-3 border-t flex-1 min-h-0 flex flex-col">
        <div className="flex border-b px-4 shrink-0">
          {hasEvents && (
            <TabButton
              active={activeSection === "events"}
              onClick={() =>
                setActiveSection(activeSection === "events" ? null : "events")
              }
            >
              Events{" "}
              <span className="ml-1 text-[10px] tabular-nums opacity-60">
                {eventCount}
              </span>
            </TabButton>
          )}
          {structuredOutput && (
            <TabButton
              active={activeSection === "output"}
              onClick={() =>
                setActiveSection(activeSection === "output" ? null : "output")
              }
            >
              Output
              <span
                className={`ml-1 text-[10px] ${structuredOutput.status === "ok" ? "text-green-500" : "text-red-500"}`}
              >
                {structuredOutput.status === "ok" ? "\u2713" : "\u2717"}
              </span>
            </TabButton>
          )}
          {batonEntry && (
            <TabButton
              active={activeSection === "baton"}
              onClick={() =>
                setActiveSection(activeSection === "baton" ? null : "baton")
              }
            >
              Baton
            </TabButton>
          )}
        </div>

        <div className="p-4 overflow-y-auto flex-1 min-h-0">
          {activeSection === null && (
            <div className="flex items-center justify-center py-8 text-xs text-muted-foreground">
              Select a section above
            </div>
          )}

          {activeSection === "events" && task && task.children.length > 0 && (
            <div className="space-y-1">
              {[...task.children].reverse().map((child) =>
                child.kind === "tool" ? (
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
                ),
              )}
            </div>
          )}

          {activeSection === "output" && structuredOutput && (
            <NodeStructuredOutput output={structuredOutput} />
          )}

          {activeSection === "baton" && batonEntry && (
            <NodeBatonDetail entry={batonEntry} />
          )}
        </div>
      </div>
    </div>
  );
}

export function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      className={`flex items-center gap-1 px-3 py-2 text-[11px] font-medium transition-colors border-b-2 -mb-px ${
        active
          ? "border-foreground text-foreground"
          : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/30"
      }`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
