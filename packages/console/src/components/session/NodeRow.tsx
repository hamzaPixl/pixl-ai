import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ToolCallExpansion } from "@/components/ToolCallExpansion";
import { TraceEventRow } from "@/components/session";
import { computeNodeStats } from "@/hooks/use-node-stats";
import { formatModelName, getModelBadgeColor } from "@/lib/utils";
import {
  Clock,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Check,
  X,
  RotateCcw,
} from "lucide-react";
import type { UnifiedNode } from "@/lib/session-constants";
import { STATE_ICONS } from "@/lib/session-constants";
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
import { NodeContextSlices } from "@/components/session/BatonDetail";

export interface NodeRowProps {
  node: UnifiedNode;
  structuredOutput?: StageOutputPayload;
  batonEntry?: BatonHistoryEntry;
  contextAudit?: ContextAuditEntry;
  onApprove?: () => void;
  onReject?: () => void;
  onRetryNode?: () => void;
}

export function NodeRow({
  node,
  structuredOutput,
  batonEntry,
  contextAudit,
  onApprove,
  onReject,
  onRetryNode,
}: NodeRowProps) {
  const [expanded, setExpanded] = useState(false);
  type SectionKey = "events" | "output" | "baton";
  const [activeSection, setActiveSection] = useState<SectionKey | null>(null);
  const [didAutoSelect, setDidAutoSelect] = useState(false);

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
  const hasContent =
    hasEvents || hasOutput || hasError || !!structuredOutput || !!batonEntry;
  const isGateWaiting = node.state === "waiting" && onApprove;
  const isActive = node.state === "running";

  const subSectionCount =
    (hasEvents ? 1 : 0) + (structuredOutput ? 1 : 0) + (batonEntry ? 1 : 0);

  const borderClass = isGateWaiting
    ? "border-yellow-500/30 bg-yellow-500/5"
    : isActive
      ? "border-blue-500/20"
      : "border-border";

  const hasStats =
    eventCount > 0 ||
    duration !== undefined ||
    inputTokens != null ||
    outputTokens != null ||
    costUsd !== undefined ||
    ctxPct !== null;

  return (
    <div className={`border rounded-md ${borderClass}`}>
      <button
        className="w-full text-left hover:bg-muted/30 transition-colors px-3 py-2.5"
        onClick={() => {
          if (!hasContent) return;
          setExpanded((v) => {
            const next = !v;
            if (next && !didAutoSelect) {
              const first: SectionKey | null = hasEvents
                ? "events"
                : structuredOutput
                  ? "output"
                  : batonEntry
                    ? "baton"
                    : null;
              setActiveSection(first);
              setDidAutoSelect(true);
            }
            return next;
          });
        }}
      >
        <div className="flex items-center gap-3">
          <div className="flex-1 min-w-0 space-y-1.5">
            <div className="flex items-center gap-2">
              <span
                className={`text-sm truncate ${isActive ? "font-semibold" : "font-medium"}`}
              >
                {node.nodeId}
              </span>
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
                  className="text-[11px] px-1.5 py-0 h-5 font-medium hidden sm:inline-flex"
                >
                  {agentName}
                </Badge>
              )}
              {node.attempt > 1 && (
                <Badge variant="outline" className="text-[10px] px-1">
                  #{node.attempt}
                </Badge>
              )}
              {isGateWaiting && (
                <Badge
                  variant="outline"
                  className="text-[10px] px-1 text-yellow-600 border-yellow-500/50"
                >
                  Pending
                </Badge>
              )}
            </div>

            {hasStats && (
              <div className="flex items-center text-[11px] text-muted-foreground">
                {duration !== undefined && (
                  <span className="flex items-center gap-1 tabular-nums">
                    <Clock className="h-3 w-3" />
                    {duration < 0.1 ? "<0.1" : duration.toFixed(1)}s
                  </span>
                )}
                {eventCount > 0 && (
                  <>
                    <span className="mx-2 h-3 w-px bg-border" />
                    <span className="tabular-nums">{eventCount} events</span>
                  </>
                )}
                {(inputTokens != null || outputTokens != null) && (
                  <>
                    <span className="mx-2 h-3 w-px bg-border" />
                    <span className="tabular-nums hidden sm:inline">
                      {inputTokens != null && (
                        <>{inputTokens.toLocaleString()} in</>
                      )}
                      {inputTokens != null && outputTokens != null && (
                        <span className="mx-1 text-muted-foreground/50">/</span>
                      )}
                      {outputTokens != null && (
                        <>{outputTokens.toLocaleString()} out</>
                      )}
                    </span>
                  </>
                )}
                {costUsd !== undefined && costUsd > 0 && (
                  <>
                    <span className="mx-2 h-3 w-px bg-border hidden md:inline" />
                    <span className="tabular-nums hidden md:inline">
                      ${costUsd.toFixed(4)}
                    </span>
                  </>
                )}
              </div>
            )}

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
                <span className="text-muted-foreground/50">
                  {contextAudit.slice_count} slices
                </span>
              </div>
            )}
          </div>

          <div className="flex items-center gap-2.5 flex-shrink-0">
            {STATE_ICONS[node.state]}
            {hasContent &&
              (expanded ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              ))}
          </div>
        </div>
      </button>

      {contextAudit && contextAudit.slices.length > 0 && (
        <NodeContextSlices slices={contextAudit.slices} />
      )}

      {hasError && !expanded && (
        <div className="px-3 pb-2.5 flex items-start gap-2 text-xs">
          <AlertTriangle className="h-3 w-3 text-red-500 flex-shrink-0 mt-0.5" />
          <span className="text-red-500 break-words line-clamp-2 flex-1">
            {task?.errorMessage || inst?.error_message}
          </span>
          {onRetryNode && (
            <Button
              size="sm"
              variant="outline"
              className="h-6 text-[11px] px-2 flex-shrink-0"
              onClick={(e) => {
                e.stopPropagation();
                onRetryNode();
              }}
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Retry
            </Button>
          )}
        </div>
      )}

      {isGateWaiting && (
        <div className="border-t px-3 py-2 flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="flex-1 text-destructive hover:bg-destructive hover:text-destructive-foreground h-7 text-xs"
            onClick={onReject}
          >
            <X className="h-3 w-3 mr-1" />
            Reject
          </Button>
          <Button
            size="sm"
            className="flex-1 bg-green-600 hover:bg-green-700 h-7 text-xs"
            onClick={onApprove}
          >
            <Check className="h-3 w-3 mr-1" />
            Approve
          </Button>
        </div>
      )}

      {expanded && (
        <div className="border-t">
          {hasError && (
            <div className="flex items-start gap-2 p-2 mx-3 mt-2 rounded-md bg-red-500/10 border border-red-500/30">
              <AlertTriangle className="h-3.5 w-3.5 text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-xs text-red-500 break-words">
                  {task?.errorMessage || inst?.error_message}
                </p>
                <div className="flex items-center gap-2 mt-1">
                  {inst?.failure_kind && (
                    <Badge variant="outline" className="text-[10px]">
                      {inst.failure_kind}
                    </Badge>
                  )}
                  {onRetryNode && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="h-6 text-[11px] px-2"
                      onClick={(e) => {
                        e.stopPropagation();
                        onRetryNode();
                      }}
                    >
                      <RotateCcw className="h-3 w-3 mr-1" />
                      Retry
                    </Button>
                  )}
                </div>
              </div>
            </div>
          )}

          {hasOutput && (
            <div className="bg-muted/30 rounded-md p-2 mx-3 mt-2 text-xs">
              <InlineOutput output={(inst as any).output} />
            </div>
          )}

          {subSectionCount > 0 && (
            <div className="flex min-h-[120px]">
              <div className="w-28 flex-shrink-0 border-r bg-muted/20 py-1">
                {hasEvents && (
                  <SidebarTab
                    active={activeSection === "events"}
                    onClick={() =>
                      setActiveSection(
                        activeSection === "events" ? null : "events",
                      )
                    }
                  >
                    Events
                    <span className="ml-auto text-[10px] tabular-nums opacity-60">
                      {eventCount}
                    </span>
                  </SidebarTab>
                )}
                {structuredOutput && (
                  <SidebarTab
                    active={activeSection === "output"}
                    onClick={() =>
                      setActiveSection(
                        activeSection === "output" ? null : "output",
                      )
                    }
                  >
                    Output
                    <span
                      className={`ml-auto text-[10px] ${structuredOutput.status === "ok" ? "text-green-500" : "text-red-500"}`}
                    >
                      {structuredOutput.status === "ok" ? "\u2713" : "\u2717"}
                    </span>
                  </SidebarTab>
                )}
                {batonEntry && (
                  <SidebarTab
                    active={activeSection === "baton"}
                    onClick={() =>
                      setActiveSection(
                        activeSection === "baton" ? null : "baton",
                      )
                    }
                  >
                    Baton
                  </SidebarTab>
                )}
              </div>

              <div className="flex-1 min-w-0 p-2 overflow-y-auto max-h-[400px]">
                {activeSection === null && (
                  <div className="flex items-center justify-center h-full text-xs text-muted-foreground">
                    Select a section
                  </div>
                )}

                {activeSection === "events" &&
                  task &&
                  task.children.length > 0 && (
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
          )}
        </div>
      )}
    </div>
  );
}

export function SidebarTab({
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
      className={`flex items-center gap-1.5 w-full px-3 py-1.5 text-[11px] font-medium transition-colors ${
        active
          ? "bg-background text-foreground border-r-2 border-r-foreground"
          : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
      }`}
      onClick={onClick}
    >
      {children}
    </button>
  );
}
