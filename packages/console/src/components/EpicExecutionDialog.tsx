/**
 * Epic Execution Dialog - Shows progress when running an epic.
 *
 * Detects already-running chains so re-opening the dialog
 * after a chain was started (e.g. via EpicExecutionPlanPanel)
 * correctly shows the progress view instead of the config form.
 *
 * Failed/cancelled chains can be retried — the backend auto-resets
 * the chain back to plan_ready and starts fresh execution.
 */

import { useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { useProjectStore, selectCurrentProjectId } from "@/stores/project";
import { Waves } from "lucide-react";
import { ConfigPanel } from "@/components/epics/execution/ConfigPanel";
import { ProgressPanel } from "@/components/epics/execution/ProgressPanel";
import { ExecutionFooter } from "@/components/epics/execution/ExecutionFooter";

interface EpicExecutionDialogProps {
  epicId: string;
  epicTitle: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete?: () => void;
}

/** Statuses that indicate a chain is (or was) active. */
const ACTIVE_STATUSES = new Set([
  "running",
  "paused",
  "completed",
  "failed",
  "cancelled",
]);

export function EpicExecutionDialog({
  epicId,
  epicTitle,
  open,
  onOpenChange,
  onComplete,
}: EpicExecutionDialogProps) {
  const projectId = useProjectStore(selectCurrentProjectId);

  const [workflowId, setWorkflowId] = useState<string>("tdd");
  const [skipApproval, setSkipApproval] = useState<boolean>(false);
  const [parallel, setParallel] = useState<boolean>(false);
  // Set to true when the user clicks "Start" or "Retry" in this dialog session
  const [justStarted, setJustStarted] = useState(false);

  const { data: waves } = useQuery({
    queryKey: ["epic-waves", projectId, epicId],
    queryFn: () => api.control.getEpicWaves(epicId),
    enabled: !!projectId && !!epicId && open,
  });

  // Always query execution progress when dialog is open.
  // If no chain exists yet the endpoint returns 404 → progress stays undefined.
  const { data: progress, refetch } = useQuery({
    queryKey: ["epic-execution", projectId, epicId],
    queryFn: () => api.control.getEpicExecution(epicId),
    enabled: !!projectId && !!epicId && open,
    retry: (failureCount, error) => {
      // Don't retry on 404 (no chain yet) — just leave progress undefined
      if (
        error &&
        typeof error === "object" &&
        "status" in error &&
        (error as { status: number }).status === 404
      ) {
        return false;
      }
      return failureCount < 2;
    },
    refetchInterval: (query) => {
      const data = query.state.data as { status: string } | undefined;
      const status = data?.status;
      if (status === "running") return 2000;
      if (
        status === "completed" ||
        status === "failed" ||
        status === "cancelled"
      )
        return false;
      if (status === "paused") return 5000;
      return 5000;
    },
  });

  // Derive whether a chain is active — either the user just clicked Start,
  // or the progress query returned a known active/terminal status.
  const isActive =
    justStarted || (progress != null && ACTIVE_STATUSES.has(progress.status));

  const isTerminal =
    progress?.status === "completed" ||
    progress?.status === "failed" ||
    progress?.status === "cancelled";
  const isFailed =
    progress?.status === "failed" || progress?.status === "cancelled";
  const chainId = progress?.chain_id;

  useEffect(() => {
    if (!open) {
      setJustStarted(false);
    }
  }, [open]);

  // Auto-close only on successful completion (not on failure — user needs retry option)
  useEffect(() => {
    if (progress?.status === "completed") {
      onComplete?.();
      const timer = setTimeout(() => {
        onOpenChange(false);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [progress?.status, onComplete, onOpenChange]);

  // Start execution mutation (also used for retry — backend auto-resets failed chains)
  const runMutation = useMutation({
    mutationFn: () =>
      api.control.runEpic(epicId, {
        workflow_id: workflowId,
        skip_approval: skipApproval,
        parallel,
        max_parallel: 3,
        stop_on_failure: true,
      }),
    onSuccess: (response) => {
      setJustStarted(true);
      refetch();
      if (response.status === "already_running") {
        setJustStarted(true);
      }
    },
  });

  // Cancel execution mutation
  const cancelMutation = useMutation({
    mutationFn: () => api.control.cancelEpicExecution(epicId),
    onSuccess: () => {
      refetch();
    },
  });

  // Pause chain mutation
  const pauseMutation = useMutation({
    mutationFn: () => {
      if (chainId) {
        return api.control.pauseChain(chainId);
      }
      return Promise.reject(new Error("No chain_id available for pause"));
    },
    onSuccess: () => {
      refetch();
    },
  });

  // Resume chain mutation
  const resumeMutation = useMutation({
    mutationFn: () => {
      if (chainId) {
        return api.control.resumeChain(chainId);
      }
      return Promise.reject(new Error("No chain_id available for resume"));
    },
    onSuccess: () => {
      refetch();
    },
  });

  const handleStart = () => runMutation.mutate();
  const handleRetry = () => runMutation.mutate();
  const handleCancel = () => cancelMutation.mutate();
  const handlePause = () => pauseMutation.mutate();
  const handleResume = () => resumeMutation.mutate();

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[700px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Waves className="h-5 w-5 text-primary" />
            {isActive ? "Epic Execution Progress" : "Run Epic"}
          </DialogTitle>
          <DialogDescription>{epicTitle}</DialogDescription>
        </DialogHeader>

        {!isActive ? (
          <ConfigPanel
            projectId={projectId!}
            workflowId={workflowId}
            onWorkflowIdChange={setWorkflowId}
            parallel={parallel}
            onParallelChange={setParallel}
            skipApproval={skipApproval}
            onSkipApprovalChange={setSkipApproval}
            waves={waves}
          />
        ) : (
          <ProgressPanel projectId={projectId!} progress={progress} />
        )}

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <ExecutionFooter
            isActive={isActive}
            isTerminal={isTerminal}
            isFailed={isFailed}
            status={progress?.status}
            chainId={chainId}
            onStart={handleStart}
            onRetry={handleRetry}
            onCancel={handleCancel}
            onPause={handlePause}
            onResume={handleResume}
            onClose={() => onOpenChange(false)}
            isStartPending={runMutation.isPending}
            isCancelPending={cancelMutation.isPending}
            isPausePending={pauseMutation.isPending}
            isResumePending={resumeMutation.isPending}
          />
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
