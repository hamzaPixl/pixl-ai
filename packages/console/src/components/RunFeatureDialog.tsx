/**
 * Dialog to launch a workflow session on an existing feature.
 */

import { useState, useEffect, useMemo } from "react";
import { Link } from "@tanstack/react-router";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { RunStartResponse, WorkflowSummary } from "@/types/api";
import { Loader2, AlertTriangle, Zap, ChevronRight, Check } from "lucide-react";
import { cn } from "@/lib/utils";

/* ── Workflow categories ───────────────────────────────────────────── */

type WorkflowCategory =
  | "core"
  | "scaffold"
  | "content"
  | "planning"
  | "operations";

const WORKFLOW_CATEGORY_ORDER: WorkflowCategory[] = [
  "core",
  "scaffold",
  "content",
  "planning",
  "operations",
];

const WORKFLOW_CATEGORY_LABELS: Record<WorkflowCategory, string> = {
  core: "Core",
  scaffold: "Scaffold & Setup",
  content: "Content",
  planning: "Planning",
  operations: "Operations",
};

const WORKFLOW_CATEGORY_MAP: Record<string, WorkflowCategory> = {
  tdd: "core",
  simple: "core",
  debug: "core",
  consolidate: "operations",
  decompose: "planning",
  roadmap: "planning",
  "project-setup": "scaffold",
  "knowledge-build": "content",
  docs: "content",
  "doc-update": "content",
  api: "scaffold",
  migration: "operations",
  refactor: "core",
  security: "operations",
  performance: "operations",
  "e2e-test": "core",
  frontend: "core",
  "frontend-debug": "core",
  spike: "planning",
  review: "operations",
  release: "operations",
};

function deriveCategory(id: string): WorkflowCategory {
  if (WORKFLOW_CATEGORY_MAP[id]) return WORKFLOW_CATEGORY_MAP[id];
  const hay = id.toLowerCase();
  if (
    hay.includes("test") ||
    hay.includes("tdd") ||
    hay.includes("debug") ||
    hay.includes("fix")
  )
    return "core";
  if (hay.includes("doc") || hay.includes("knowledge")) return "content";
  if (
    hay.includes("plan") ||
    hay.includes("roadmap") ||
    hay.includes("decompose")
  )
    return "planning";
  if (hay.includes("setup") || hay.includes("scaffold") || hay.includes("init"))
    return "scaffold";
  return "operations";
}

interface RunFeatureDialogProps {
  featureId: string;
  featureTitle: string;
  projectId: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (result: RunStartResponse) => void;
}

export function RunFeatureDialog({
  featureId,
  featureTitle,
  projectId,
  open,
  onOpenChange,
  onSuccess,
}: RunFeatureDialogProps) {
  const [selectedWorkflow, setSelectedWorkflow] = useState("");
  const [skipApproval, setSkipApproval] = useState(false);

  const { data: workflows = [], isLoading: workflowsLoading } = useQuery({
    queryKey: queryKeys.workflows.list(projectId || ""),
    queryFn: () => api.workflows.list(),
    enabled: !!projectId && open,
  });

  // Auto-select first workflow
  useEffect(() => {
    if (workflows.length > 0 && !selectedWorkflow) {
      setSelectedWorkflow(workflows[0].id);
    }
  }, [workflows, selectedWorkflow]);

  useEffect(() => {
    if (!open) {
      setSelectedWorkflow("");
      setSkipApproval(false);
    }
  }, [open]);

  const runMutation = useMutation({
    mutationFn: () =>
      api.run.runFeature(featureId, {
        workflow_id: selectedWorkflow,
        skip_approval: skipApproval,
      }),
    onSuccess: (result) => {
      onOpenChange(false);
      onSuccess?.(result);
    },
  });

  const handleRun = () => {
    if (selectedWorkflow) {
      runMutation.mutate();
    }
  };

  const groupedWorkflows = useMemo(() => {
    const groups: Record<WorkflowCategory, WorkflowSummary[]> = {
      core: [],
      scaffold: [],
      content: [],
      planning: [],
      operations: [],
    };
    for (const wf of workflows) {
      groups[deriveCategory(wf.id)].push(wf);
    }
    return WORKFLOW_CATEGORY_ORDER.filter((cat) => groups[cat].length > 0).map(
      (cat) => ({
        category: cat,
        label: WORKFLOW_CATEGORY_LABELS[cat],
        items: groups[cat],
      }),
    );
  }, [workflows]);

  const selectedWf = workflows.find(
    (w: WorkflowSummary) => w.id === selectedWorkflow,
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[calc(100vw-2rem)] sm:max-w-[900px] max-h-[85vh] gap-0 p-0 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 pt-6 pb-4 shrink-0">
          <DialogHeader className="space-y-1">
            <DialogTitle className="text-lg font-semibold">
              Run Workflow
            </DialogTitle>
            <DialogDescription asChild>
              <div className="flex items-center gap-2 text-sm">
                <Link
                  to="/project/$projectId/features/$featureId"
                  params={{ projectId, featureId }}
                  className="text-foreground/80 font-medium truncate hover:underline"
                >
                  {featureTitle}
                </Link>
                <code className="text-[11px] bg-muted/80 text-muted-foreground px-1.5 py-0.5 rounded font-mono shrink-0">
                  {featureId}
                </code>
              </div>
            </DialogDescription>
          </DialogHeader>
        </div>

        {/* Body */}
        <div className="px-6 pb-5 space-y-4 overflow-y-auto min-h-0 flex-1">
          {/* Workflow selection as inline grid */}
          <div className="space-y-2">
            <Label className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Workflow
            </Label>
            {workflowsLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                {[1, 2, 3, 4, 5, 6].map((i) => (
                  <div
                    key={i}
                    className="h-14 rounded-lg bg-muted/50 animate-pulse"
                  />
                ))}
              </div>
            ) : workflows.length === 0 ? (
              <p className="text-sm text-muted-foreground py-3">
                No workflows available
              </p>
            ) : (
              <div className="space-y-4">
                {groupedWorkflows.map(({ category, label, items }) => (
                  <div key={category}>
                    <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                      {label}
                    </p>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-1.5">
                      {items.map((wf: WorkflowSummary) => {
                        const isSelected = selectedWorkflow === wf.id;
                        return (
                          <button
                            key={wf.id}
                            type="button"
                            onClick={() => setSelectedWorkflow(wf.id)}
                            className={cn(
                              "text-left px-3 py-2 rounded-lg border transition-all",
                              "hover:bg-muted/50",
                              isSelected
                                ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                                : "border-border",
                            )}
                          >
                            <div className="flex items-center gap-2">
                              <div
                                className={cn(
                                  "flex items-center justify-center w-4 h-4 rounded-full border shrink-0 transition-colors",
                                  isSelected
                                    ? "border-primary bg-primary text-primary-foreground"
                                    : "border-muted-foreground/30",
                                )}
                              >
                                {isSelected && (
                                  <Check className="h-2.5 w-2.5" />
                                )}
                              </div>
                              <div className="min-w-0 flex-1">
                                <div className="text-sm font-medium truncate">
                                  {wf.name || wf.id}
                                </div>
                                {wf.description && (
                                  <div className="text-[11px] text-muted-foreground line-clamp-2 leading-snug">
                                    {wf.description}
                                  </div>
                                )}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Options */}
          <div className="flex items-center justify-between rounded-lg border px-3.5 py-2.5">
            <div className="flex items-center gap-3">
              <Label
                htmlFor="skipApprovalFeature"
                className="text-sm font-medium cursor-pointer"
              >
                Auto-approve gates
              </Label>
              <span className="text-xs text-muted-foreground">
                Skip human review
              </span>
            </div>
            <Switch
              id="skipApprovalFeature"
              checked={skipApproval}
              onCheckedChange={setSkipApproval}
            />
          </div>

          {/* Error */}
          {runMutation.isError && (
            <div className="flex items-start gap-2.5 text-sm bg-destructive/10 text-destructive rounded-lg px-3.5 py-3">
              <AlertTriangle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>
                {runMutation.error instanceof Error
                  ? runMutation.error.message
                  : "Failed to start workflow"}
              </span>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t bg-muted/30 px-6 py-3.5 shrink-0">
          <DialogFooter className="gap-2 sm:gap-2">
            <Button
              variant="ghost"
              onClick={() => onOpenChange(false)}
              disabled={runMutation.isPending}
              className="text-muted-foreground"
            >
              Cancel
            </Button>
            <Button
              onClick={handleRun}
              disabled={!selectedWorkflow || runMutation.isPending}
              className="min-w-[140px] gap-2"
            >
              {runMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Starting...
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" />
                  Run {selectedWf?.name || "Workflow"}
                  <ChevronRight className="h-3.5 w-3.5 -mr-1" />
                </>
              )}
            </Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  );
}
