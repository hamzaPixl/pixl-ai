import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { AlertTriangle, ShieldCheck } from "lucide-react";
import type { ClassificationResponse, WorkflowSummary } from "@/types/api";

export interface ReviewPanelProps {
  classification: ClassificationResponse;
  workflows: WorkflowSummary[];
  selectedWorkflow: string;
  onSelectWorkflow: (id: string) => void;
  skipApproval: boolean;
  onSkipApprovalChange: (value: boolean) => void;
  confirmError: Error | null;
}

export function ReviewPanel({
  classification,
  workflows,
  selectedWorkflow,
  onSelectWorkflow,
  skipApproval,
  onSkipApprovalChange,
  confirmError,
}: ReviewPanelProps) {
  const confidenceColor = (c: number) =>
    c >= 0.8
      ? "text-emerald-500"
      : c >= 0.6
        ? "text-amber-500"
        : "text-red-500";

  const confidenceBg = (c: number) =>
    c >= 0.8 ? "bg-emerald-500" : c >= 0.6 ? "bg-amber-500" : "bg-red-500";

  return (
    <motion.div
      key="review"
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 12 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className="px-5 py-4 space-y-4"
    >
      {/* Classification result card */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <Badge
            variant="secondary"
            className="shrink-0 uppercase text-[10px] tracking-wider font-semibold"
          >
            {classification.kind}
          </Badge>
          <span className="font-medium text-sm truncate">
            {classification.title}
          </span>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <div className="flex items-center gap-1.5">
            <div
              className={`h-2 w-2 rounded-full ${confidenceBg(classification.confidence)}`}
            />
            <span
              className={`text-xs font-medium tabular-nums ${confidenceColor(classification.confidence)}`}
            >
              {Math.round(classification.confidence * 100)}%
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            {classification.estimated_features} feature
            {classification.estimated_features !== 1 ? "s" : ""}
          </span>
        </div>
      </div>

      {/* Risk flags */}
      {classification.risk_flags.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
          className="flex flex-wrap gap-1.5"
        >
          {classification.risk_flags.map((flag, i) => (
            <span
              key={i}
              className="inline-flex items-center gap-1 text-[11px] text-amber-600 dark:text-amber-400 bg-amber-500/10 rounded-full px-2.5 py-0.5"
            >
              <AlertTriangle className="h-3 w-3" />
              {flag}
            </span>
          ))}
        </motion.div>
      )}

      {/* Workflow selection - pill buttons */}
      <div className="space-y-2">
        <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          Workflow
        </p>
        <div className="flex flex-wrap gap-2">
          {workflows.map((wf) => {
            const isSelected = wf.id === selectedWorkflow;
            const isSuggested = wf.id === classification.suggested_workflow;
            return (
              <button
                key={wf.id}
                onClick={() => onSelectWorkflow(wf.id)}
                className={`
                  relative px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-150
                  ${
                    isSelected
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground"
                  }
                `}
                title={wf.description || wf.name || wf.id}
              >
                {wf.name || wf.id}
                {isSuggested && !isSelected && (
                  <span className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-primary" />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Auto-approve toggle */}
      <div className="flex items-center justify-between py-1">
        <label
          htmlFor="skip-approval"
          className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer"
        >
          <ShieldCheck className="h-4 w-4" />
          Auto-approve gates
        </label>
        <Switch
          id="skip-approval"
          checked={skipApproval}
          onCheckedChange={onSkipApprovalChange}
        />
      </div>

      {/* Error display */}
      {confirmError && (
        <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-lg px-3 py-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          {confirmError.message || "Failed to start workflow"}
        </div>
      )}
    </motion.div>
  );
}
