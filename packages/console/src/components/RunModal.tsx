/**
 * Run Modal - Modern command-palette style workflow launcher.
 *
 * Single-surface flow with animated transitions:
 *   1. Prompt input (command bar)
 *   2. Classification with progress bar
 *   3. Review & launch (slides in below prompt)
 */

import { useState, useEffect, useRef } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type {
  ClassificationResponse,
  ConfirmRunRequest,
  RunStartResponse,
  WorkflowSummary,
} from "@/types/api";
import { AlertTriangle, Pencil } from "lucide-react";
import { VisuallyHidden } from "@radix-ui/react-visually-hidden";

import type { Phase } from "./run/types";
import {
  ClassifyingProgress,
  STATUS_MESSAGES,
} from "./run/ClassifyingProgress";
import { ReviewPanel } from "./run/ReviewPanel";
import { BottomBar } from "./run/BottomBar";

interface RunModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: (result: RunStartResponse) => void;
  projectId: string;
}

export function RunModal({
  open,
  onOpenChange,
  onSuccess,
  projectId,
}: RunModalProps) {
  const [phase, setPhase] = useState<Phase>("input");
  const [prompt, setPrompt] = useState("");
  const [classification, setClassification] =
    useState<ClassificationResponse | null>(null);
  const [selectedWorkflow, setSelectedWorkflow] = useState("");
  const [skipApproval, setSkipApproval] = useState(false);
  const [statusIndex, setStatusIndex] = useState(0);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!open) {
      const timer = setTimeout(() => {
        setPhase("input");
        setPrompt("");
        setClassification(null);
        setSelectedWorkflow("");
        setSkipApproval(false);
        setStatusIndex(0);
      }, 200);
      return () => clearTimeout(timer);
    }
  }, [open]);

  useEffect(() => {
    if (open && phase === "input") {
      const timer = setTimeout(() => textareaRef.current?.focus(), 150);
      return () => clearTimeout(timer);
    }
  }, [open, phase]);

  useEffect(() => {
    if (phase !== "classifying") return;
    setStatusIndex(0);
    const interval = setInterval(() => {
      setStatusIndex((prev) => Math.min(prev + 1, STATUS_MESSAGES.length - 1));
    }, 800);
    return () => clearInterval(interval);
  }, [phase]);

  const { data: workflows = [] } = useQuery({
    queryKey: queryKeys.workflows.list(projectId || ""),
    queryFn: () => api.workflows.list(),
    enabled: !!projectId,
  });

  const resolveWorkflowId = (
    suggested?: string | null,
    list?: WorkflowSummary[],
  ) => {
    const items = list ?? workflows;
    if (!items.length) return suggested || "";
    if (suggested && items.some((wf) => wf.id === suggested)) return suggested;
    return items[0].id;
  };

  useEffect(() => {
    if (!classification || workflows.length === 0) return;
    const hasSelection =
      selectedWorkflow && workflows.some((wf) => wf.id === selectedWorkflow);
    if (!hasSelection) {
      setSelectedWorkflow(
        resolveWorkflowId(classification.suggested_workflow, workflows),
      );
    }
  }, [classification, workflows, selectedWorkflow]);

  const classifyMutation = useMutation({
    mutationFn: () => api.run.classify({ prompt }),
    onMutate: () => setPhase("classifying"),
    onSuccess: (data) => {
      setClassification(data);
      setSelectedWorkflow(
        resolveWorkflowId(data.suggested_workflow, workflows),
      );
      setPhase("review");
    },
    onError: () => setPhase("input"),
  });

  const confirmMutation = useMutation({
    mutationFn: (data: ConfirmRunRequest) => api.run.confirm(data),
    onMutate: () => setPhase("launching"),
    onSuccess: (result) => {
      onOpenChange(false);
      onSuccess?.(result);
    },
    onError: () => setPhase("review"),
  });

  const handleClassify = () => {
    if (prompt.trim()) classifyMutation.mutate();
  };

  const handleConfirm = () => {
    if (classification && selectedWorkflow) {
      confirmMutation.mutate({
        prompt,
        kind: classification.kind,
        title: classification.title,
        workflow_id: selectedWorkflow,
        skip_approval: skipApproval,
      });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      if (phase === "input" && prompt.trim()) handleClassify();
      else if (phase === "review") handleConfirm();
    }
  };

  const showReview = phase === "review" || phase === "launching";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="max-w-[calc(100vw-2rem)] sm:max-w-[640px] p-0 gap-0 overflow-hidden bg-background/95 backdrop-blur-xl border-border/50 shadow-2xl"
        onKeyDown={handleKeyDown}
      >
        <VisuallyHidden>
          <DialogTitle>Start Workflow</DialogTitle>
        </VisuallyHidden>

        {/* Prompt Section - always visible */}
        <div className="relative">
          <div className="px-5 pt-5 pb-4">
            {showReview ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="group flex items-start gap-3"
              >
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-muted-foreground line-clamp-2">
                    {prompt}
                  </p>
                </div>
                <button
                  onClick={() => {
                    setPhase("input");
                    setClassification(null);
                  }}
                  className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground p-1 rounded-md hover:bg-accent"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
              </motion.div>
            ) : (
              <textarea
                ref={textareaRef}
                className="w-full min-h-[100px] max-h-[200px] resize-none bg-transparent text-[15px] leading-relaxed placeholder:text-muted-foreground/60 focus:outline-none disabled:opacity-60"
                placeholder="What do you want to build?"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                disabled={phase === "classifying"}
              />
            )}
          </div>

          <AnimatePresence>
            {phase === "classifying" && (
              <ClassifyingProgress statusIndex={statusIndex} />
            )}
          </AnimatePresence>

          <div className="h-px bg-border" />
        </div>

        {/* Review Section & errors */}
        <AnimatePresence mode="wait">
          {showReview && classification && (
            <ReviewPanel
              classification={classification}
              workflows={workflows}
              selectedWorkflow={selectedWorkflow}
              onSelectWorkflow={setSelectedWorkflow}
              skipApproval={skipApproval}
              onSkipApprovalChange={setSkipApproval}
              confirmError={
                confirmMutation.isError
                  ? confirmMutation.error instanceof Error
                    ? confirmMutation.error
                    : new Error("Failed to start workflow")
                  : null
              }
            />
          )}

          {phase === "input" && classifyMutation.isError && (
            <motion.div
              key="error"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="px-5 py-3"
            >
              <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                {classifyMutation.error instanceof Error
                  ? classifyMutation.error.message
                  : "Classification failed. Try again."}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Bottom bar */}
        <BottomBar
          phase={phase}
          workflowCount={workflows.length}
          promptEmpty={!prompt.trim()}
          classifyPending={classifyMutation.isPending}
          selectedWorkflow={selectedWorkflow}
          onClassify={handleClassify}
          onConfirm={handleConfirm}
        />
      </DialogContent>
    </Dialog>
  );
}
