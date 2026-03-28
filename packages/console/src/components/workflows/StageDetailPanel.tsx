import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ScrollArea } from "@/components/ui/scroll-area";
import { X, ArrowRight, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { NODE_STYLE, type NodeType } from "@/lib/dag-layout";
import type { WorkflowDetail, WorkflowNodeDetail } from "@/types/api";

export interface StageDetailPanelProps {
  nodeId: string;
  node: WorkflowNodeDetail;
  workflow: WorkflowDetail;
  onClose: () => void;
}

export function StageDetailPanel({
  nodeId,
  node,
  workflow,
  onClose,
}: StageDetailPanelProps) {
  const style = NODE_STYLE[node.type as NodeType] ?? NODE_STYLE.task;

  const stageConfig = (workflow.stages ?? []).find(
    (s: unknown) => (s as Record<string, unknown>)?.id === nodeId,
  ) as Record<string, unknown> | undefined;

  const contract = stageConfig?.contract as Record<string, unknown> | undefined;

  return (
    <div className="h-full flex flex-col">
      {/* Panel header */}
      <div className="shrink-0 flex items-center justify-between px-4 py-3 border-b">
        <div className="flex items-center gap-2.5 min-w-0">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
            style={{ backgroundColor: style.fill }}
          />
          <span className="font-semibold text-sm truncate">{nodeId}</span>
          <Badge
            variant="secondary"
            className="text-[10px] px-1.5 py-0 h-4 shrink-0"
            style={{ backgroundColor: `${style.fill}15`, color: style.fill }}
          >
            {style.label}
          </Badge>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="h-6 w-6 p-0"
          onClick={onClose}
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Panel body */}
      <ScrollArea className="flex-1">
        <div className="px-4 py-3 space-y-5">
          {/* Task config */}
          {node.type === "task" && node.task_config && (
            <div className="space-y-2">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Task Config
              </h4>
              <div className="grid grid-cols-2 gap-2">
                <div className="rounded-md border px-3 py-2">
                  <p className="text-[10px] text-muted-foreground">Agent</p>
                  <p className="text-sm font-medium">
                    {node.task_config.agent}
                  </p>
                </div>
                <div className="rounded-md border px-3 py-2">
                  <p className="text-[10px] text-muted-foreground">Max turns</p>
                  <p className="text-sm font-medium">
                    {node.task_config.max_turns}
                  </p>
                </div>
              </div>
              {node.task_config.retry_policy != null && (
                <div className="rounded-md border px-3 py-2">
                  <p className="text-[10px] text-muted-foreground">
                    Retry policy
                  </p>
                  <p className="text-sm font-medium">Configured</p>
                </div>
              )}
            </div>
          )}

          {/* Gate config */}
          {node.type === "gate" && node.gate_config && (
            <div className="space-y-2">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Gate Config
              </h4>
              {node.gate_config.description && (
                <p className="text-sm text-foreground leading-relaxed">
                  {node.gate_config.description}
                </p>
              )}
              <div className="grid grid-cols-2 gap-2">
                {node.gate_config.name && (
                  <div className="rounded-md border px-3 py-2">
                    <p className="text-[10px] text-muted-foreground">Name</p>
                    <p className="text-sm font-medium">
                      {node.gate_config.name}
                    </p>
                  </div>
                )}
                {node.gate_config.timeout_minutes && (
                  <div className="rounded-md border px-3 py-2">
                    <p className="text-[10px] text-muted-foreground">Timeout</p>
                    <p className="text-sm font-medium">
                      {node.gate_config.timeout_minutes}m
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Hook config */}
          {node.type === "hook" && node.hook_config && (
            <div className="space-y-2">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Hook Config
              </h4>
              <div className="rounded-md border px-3 py-2">
                <p className="text-[10px] text-muted-foreground">Hook</p>
                <p className="text-sm font-medium">
                  {String(
                    (node.hook_config as Record<string, unknown>).hook_id ??
                      (node.hook_config as Record<string, unknown>).hook ??
                      nodeId,
                  )}
                </p>
              </div>
            </div>
          )}

          {/* Sub-workflow config */}
          {node.type === "sub_workflow" && node.metadata?.sub_workflow && (
            <div className="space-y-2">
              <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                Sub-Workflow
              </h4>
              <div className="rounded-md border px-3 py-2">
                <p className="text-[10px] text-muted-foreground">
                  Target workflow
                </p>
                <p className="text-sm font-medium font-mono">
                  {node.metadata.sub_workflow}
                </p>
              </div>
            </div>
          )}

          {/* Contract */}
          {contract && (
            <>
              <Separator />
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Contract
                </h4>
                {contract.must_write != null && (
                  <div className="space-y-1">
                    <p className="text-[10px] text-muted-foreground font-medium">
                      must_write
                    </p>
                    <div className="flex flex-wrap gap-1">
                      {(Array.isArray(contract.must_write)
                        ? (contract.must_write as string[])
                        : [String(contract.must_write)]
                      ).map((path, i) => (
                        <span
                          key={i}
                          className="inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-mono"
                        >
                          {path}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {contract.output_schema != null && (
                  <div className="rounded-md border px-3 py-2">
                    <p className="text-[10px] text-muted-foreground">
                      Output schema
                    </p>
                    <p className="text-sm font-medium">Defined</p>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Edges */}
          {(workflow.edges?.[nodeId]?.length ?? 0) > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Edges
                </h4>
                <div className="space-y-1.5">
                  {workflow.edges[nodeId]!.map((e, i) => {
                    const edgeColor =
                      e.on === "success"
                        ? "text-green-600 dark:text-green-400"
                        : e.on === "failure"
                          ? "text-red-600 dark:text-red-400"
                          : "text-muted-foreground";
                    const dotColor =
                      e.on === "success"
                        ? "bg-green-500"
                        : e.on === "failure"
                          ? "bg-red-500"
                          : "bg-gray-400";
                    return (
                      <div
                        key={i}
                        className="flex items-center gap-2 rounded-md border px-3 py-1.5"
                      >
                        <span
                          className={`h-2 w-2 rounded-full shrink-0 ${dotColor}`}
                        />
                        <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                        <span className="text-sm font-medium flex-1 truncate">
                          {e.to}
                        </span>
                        <span
                          className={cn("text-[10px] font-medium", edgeColor)}
                        >
                          {e.on}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </>
          )}

          {/* Loops */}
          {(workflow.loops ?? []).filter(
            (lp) => lp.from_node === nodeId || lp.to_node === nodeId,
          ).length > 0 && (
            <>
              <Separator />
              <div className="space-y-2">
                <h4 className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                  Loops
                </h4>
                {(workflow.loops ?? [])
                  .filter(
                    (lp) => lp.from_node === nodeId || lp.to_node === nodeId,
                  )
                  .map((lp) => (
                    <div
                      key={lp.id}
                      className="flex items-center gap-2 rounded-md border border-dashed px-3 py-2"
                    >
                      <RefreshCw className="h-3 w-3 text-muted-foreground shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">
                          {lp.from_node} &rarr; {lp.to_node}
                        </p>
                        <p className="text-[10px] text-muted-foreground">
                          max {lp.max_iterations} iterations &middot; trigger:{" "}
                          {lp.edge_trigger}
                        </p>
                      </div>
                    </div>
                  ))}
              </div>
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
