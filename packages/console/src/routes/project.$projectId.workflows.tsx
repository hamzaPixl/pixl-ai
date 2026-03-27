/**
 * Workflows page — flat list grouped by tier with inline DAG expansion.
 *
 * Clicking a workflow row expands the pipeline DAG + metadata directly below.
 * Clicking a node inside the DAG opens the StageDetailSheet.
 */

import { createFileRoute } from "@tanstack/react-router";
import { useState, useMemo, useEffect } from "react";
import { useWorkflows, useWorkflowDetail } from "@/hooks/queries";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { EmptyState } from "@/components/empty-state";
import { PageHeader } from "@/components/page-header";
import { TooltipProvider } from "@/components/ui/tooltip";
import {
  Workflow,
  GitBranch,
  ClipboardList,
  Wrench,
  Bug,
  Layers,
  ChevronRight,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { WorkflowPipeline } from "@/components/WorkflowPipeline";
import { NODE_TYPES, NODE_STYLE, type NodeType } from "@/lib/dag-layout";
import { StageDetailPanel } from "@/components/workflows/StageDetailPanel";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import type { WorkflowSummary } from "@/types/workflows";

export const Route = createFileRoute("/project/$projectId/workflows")({
  component: WorkflowsPage,
});

const TIER_META: Record<
  string,
  { icon: typeof Workflow; dot: string; label: string }
> = {
  orchestration: { icon: GitBranch, dot: "bg-violet-500", label: "Orchestration" },
  planning: { icon: ClipboardList, dot: "bg-blue-500", label: "Planning" },
  task: { icon: Layers, dot: "bg-emerald-500", label: "Task" },
  utility: { icon: Wrench, dot: "bg-amber-500", label: "Utility" },
  meta: { icon: Bug, dot: "bg-rose-500", label: "Meta" },
  other: { icon: Workflow, dot: "bg-muted-foreground", label: "Other" },
};

const TIER_ORDER = Object.keys(TIER_META);

export function WorkflowsPageContent({ projectId }: { projectId: string }) {
  return <WorkflowsPageInner projectId={projectId} />;
}

function WorkflowsPage() {
  const { projectId } = Route.useParams();
  return <WorkflowsPageInner projectId={projectId} />;
}

function WorkflowsPageInner({ projectId }: { projectId: string }) {
  const { data: workflowList, isLoading } = useWorkflows(projectId);

  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(
    new Set(),
  );

  // Node-level state for DAG interaction
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [activeType, setActiveType] = useState<NodeType | null>(null);

  // Reset node state when switching workflows
  useEffect(() => {
    setSelectedNode(null);
    setHoveredNode(null);
    setActiveType(null);
  }, [selectedId]);

  const grouped = useMemo(() => {
    if (!workflowList) return null;
    const map: Record<string, WorkflowSummary[]> = {};
    for (const t of TIER_ORDER) map[t] = [];
    for (const wf of workflowList) {
      const tier = (wf.tier as string) || "other";
      if (!map[tier]) map[tier] = [];
      map[tier].push(wf);
    }
    for (const key of TIER_ORDER) {
      map[key].sort((a, b) => (a.name || a.id).localeCompare(b.name || b.id));
    }
    return map;
  }, [workflowList]);

  const tierSummary = useMemo(() => {
    if (!grouped) return "";
    return TIER_ORDER.filter((t) => grouped[t].length > 0)
      .map((t) => `${grouped[t].length} ${TIER_META[t].label.toLowerCase()}`)
      .join(" \u00b7 ");
  }, [grouped]);

  const toggleSection = (key: string) => {
    setCollapsedSections((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleWorkflow = (id: string) => {
    setSelectedId((prev) => (prev === id ? null : id));
  };

  return (
    <TooltipProvider>
      <div className="space-y-4">
        <PageHeader
          title="Workflows"
          description={`Visualize workflow pipelines and stage details.${tierSummary ? ` ${tierSummary}` : ""}`}
        />

        {isLoading ? (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-lg border p-4">
                <Skeleton className="h-5 w-48 mb-2" />
                <Skeleton className="h-4 w-full" />
              </div>
            ))}
          </div>
        ) : !grouped ? (
          <EmptyState
            icon={Workflow}
            title="No workflows found"
            description="Create workflows in your project's .pixl/workflows/ directory."
          />
        ) : (
          <div className="space-y-1">
            {TIER_ORDER.map((tier) => {
              const tierWorkflows = grouped[tier];
              if (tierWorkflows.length === 0) return null;
              const meta = TIER_META[tier];
              const collapsed = collapsedSections.has(tier);

              return (
                <div key={tier}>
                  <button
                    type="button"
                    onClick={() => toggleSection(tier)}
                    className="flex items-center gap-2 w-full px-2 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
                  >
                    {collapsed ? (
                      <ChevronRight className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5" />
                    )}
                    <span className={cn("h-2 w-2 rounded-full shrink-0", meta.dot)} />
                    <span className="uppercase tracking-wider">{meta.label}</span>
                    <span className="text-muted-foreground/60 tabular-nums">
                      {tierWorkflows.length}
                    </span>
                  </button>

                  {!collapsed && (
                    <div className="space-y-px">
                      {tierWorkflows.map((wf) => {
                        const isOpen = selectedId === wf.id;
                        return (
                          <div
                            key={wf.id}
                            className={cn(
                              "rounded-lg transition-all duration-200",
                              isOpen && "border border-highlight/20 bg-card",
                            )}
                          >
                            <WorkflowRow
                              workflow={wf}
                              isOpen={isOpen}
                              onToggle={() => toggleWorkflow(wf.id)}
                            />
                            {isOpen && (
                              <WorkflowInlineDetail
                                projectId={projectId}
                                workflowId={wf.id}
                                selectedNode={selectedNode}
                                hoveredNode={hoveredNode}
                                activeType={activeType}
                                onSelectNode={setSelectedNode}
                                onHoverNode={setHoveredNode}
                                onActiveType={setActiveType}
                              />
                            )}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </TooltipProvider>
  );
}

/* ── Workflow row ─────────── */

function WorkflowRow({
  workflow,
  isOpen,
  onToggle,
}: {
  workflow: WorkflowSummary;
  isOpen: boolean;
  onToggle: () => void;
}) {
  const tier = (workflow.tier as string) || "other";
  const meta = TIER_META[tier] ?? TIER_META.other;
  const TierIcon = meta.icon;

  return (
    <div
      onClick={onToggle}
      className={cn(
        "group flex items-center gap-3 px-3 py-2.5 rounded-md cursor-pointer transition-all duration-200 border",
        isOpen
          ? "bg-transparent border-transparent"
          : "border-transparent hover:bg-muted/50 hover:border-border",
      )}
    >
      {/* Icon */}
      <div
        className={cn(
          "shrink-0 p-1.5 rounded-md transition-colors",
          isOpen ? "bg-highlight/10" : "bg-muted",
        )}
      >
        <TierIcon
          className={cn(
            "h-4 w-4",
            isOpen ? "text-highlight" : "text-muted-foreground",
          )}
        />
      </div>

      {/* Name + description */}
      <div className="flex-1 min-w-0">
        <span
          className={cn("font-medium text-sm", isOpen && "text-highlight")}
        >
          {workflow.name || workflow.id}
        </span>
        {workflow.description && (
          <p className="text-xs text-muted-foreground/60 truncate mt-0.5">
            {workflow.description}
          </p>
        )}
      </div>

      {/* Right metadata */}
      <div className="flex items-center gap-2.5 shrink-0 opacity-70 group-hover:opacity-100 transition-opacity">
        {workflow.version && (
          <Badge variant="outline" className="text-[10px] h-4 px-1.5 py-0">
            v{workflow.version}
          </Badge>
        )}
        {workflow.tags && workflow.tags.length > 0 && (
          <span className="text-xs text-muted-foreground tabular-nums">
            {workflow.tags.length} tag{workflow.tags.length !== 1 ? "s" : ""}
          </span>
        )}
        {isOpen ? (
          <ChevronDown className="h-4 w-4 text-highlight" />
        ) : (
          <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
        )}
      </div>
    </div>
  );
}

/* ── Inline detail panel (expands below row) ─────────── */

function WorkflowInlineDetail({
  projectId,
  workflowId,
  selectedNode,
  hoveredNode,
  activeType,
  onSelectNode,
  onHoverNode,
  onActiveType,
}: {
  projectId: string;
  workflowId: string;
  selectedNode: string | null;
  hoveredNode: string | null;
  activeType: NodeType | null;
  onSelectNode: (id: string | null) => void;
  onHoverNode: (id: string | null) => void;
  onActiveType: (type: NodeType | null) => void;
}) {
  const { data: workflow, isLoading } = useWorkflowDetail(
    projectId,
    workflowId,
  );

  const selectedNodeInfo =
    selectedNode && workflow ? workflow.nodes?.[selectedNode] : null;

  const availableTypes = useMemo(() => {
    if (!workflow?.nodes) return [];
    const types = new Set<NodeType>();
    for (const n of Object.values(workflow.nodes)) {
      types.add(n.type as NodeType);
    }
    return NODE_TYPES.filter((t) => types.has(t));
  }, [workflow]);

  const nodeCount = workflow?.nodes ? Object.keys(workflow.nodes).length : 0;
  const gateCount = workflow?.nodes
    ? Object.values(workflow.nodes).filter((n) => n.type === "gate").length
    : 0;
  const loopCount = workflow?.loops?.length ?? 0;

  return (
    <div className="px-5 pb-5 pt-2 space-y-4 animate-in slide-in-from-top-2 fade-in duration-200">
      {isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-4 w-16 mx-auto" />
          <Skeleton className="h-12 w-full rounded-lg" />
        </div>
      ) : workflow ? (
        <>
          {/* Stats + type filter bar */}
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <span className="tabular-nums">
                {nodeCount} stages
                {gateCount > 0 &&
                  ` \u00b7 ${gateCount} gate${gateCount !== 1 ? "s" : ""}`}
                {loopCount > 0 &&
                  ` \u00b7 ${loopCount} loop${loopCount !== 1 ? "s" : ""}`}
              </span>
              {workflow.tags && workflow.tags.length > 0 && (
                <div className="flex items-center gap-1">
                  {workflow.tags.map((tag) => (
                    <Badge
                      key={tag}
                      variant="secondary"
                      className="text-[10px] h-4 px-1.5 py-0"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            {availableTypes.length > 1 && (
              <ToggleGroup
                type="single"
                value={activeType ?? ""}
                onValueChange={(v) =>
                  onActiveType(v ? (v as NodeType) : null)
                }
              >
                {availableTypes.map((nt) => {
                  const st = NODE_STYLE[nt];
                  return (
                    <ToggleGroupItem
                      key={nt}
                      value={nt}
                      size="sm"
                      className="gap-1 text-[10px] h-7 px-2.5 data-[state=on]:bg-accent"
                    >
                      <span
                        className="inline-block h-1.5 w-1.5 rounded-full shrink-0"
                        style={{ backgroundColor: st.fill }}
                      />
                      {st.label}
                    </ToggleGroupItem>
                  );
                })}
              </ToggleGroup>
            )}
          </div>

          {/* DAG pipeline */}
          <div className="min-h-[300px]">
            <WorkflowPipeline
              workflow={workflow}
              selectedNode={selectedNode}
              hoveredNode={hoveredNode}
              onSelect={(id) =>
                onSelectNode(selectedNode === id ? null : id)
              }
              onHover={onHoverNode}
              activeType={activeType}
            />
          </div>

          {/* Node detail sheet */}
          <Sheet
            open={!!selectedNodeInfo}
            onOpenChange={(open) => {
              if (!open) onSelectNode(null);
            }}
          >
            <SheetContent className="w-full sm:w-[400px] md:w-[440px] p-0 overflow-hidden">
              <SheetHeader className="sr-only">
                <SheetTitle>Stage Detail</SheetTitle>
              </SheetHeader>
              {selectedNodeInfo && workflow && (
                <StageDetailPanel
                  nodeId={selectedNode!}
                  node={selectedNodeInfo}
                  workflow={workflow}
                  onClose={() => onSelectNode(null)}
                />
              )}
            </SheetContent>
          </Sheet>
        </>
      ) : null}
    </div>
  );
}
