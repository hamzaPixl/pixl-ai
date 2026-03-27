import { Button } from "@/components/ui/button";
import { Command, Zap, Play, Loader2 } from "lucide-react";
import type { Phase } from "./types";

export interface BottomBarProps {
  phase: Phase;
  workflowCount: number;
  promptEmpty: boolean;
  classifyPending: boolean;
  selectedWorkflow: string;
  onClassify: () => void;
  onConfirm: () => void;
}

export function BottomBar({
  phase,
  workflowCount,
  promptEmpty,
  classifyPending,
  selectedWorkflow,
  onClassify,
  onConfirm,
}: BottomBarProps) {
  const isInputActive = phase === "input";
  const showReview = phase === "review" || phase === "launching";

  return (
    <>
      <div className="h-px bg-border" />
      <div className="flex items-center justify-between px-5 py-3">
        {/* Left - context info */}
        <div className="flex items-center gap-2">
          {isInputActive && workflowCount > 0 && (
            <span className="text-[11px] text-muted-foreground/70 bg-muted/50 rounded-full px-2.5 py-0.5">
              {workflowCount} workflow{workflowCount !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {/* Right - actions */}
        <div className="flex items-center gap-2">
          {(isInputActive || showReview) && phase !== "launching" && (
            <kbd className="hidden sm:inline-flex items-center gap-1 text-[10px] text-muted-foreground/50 select-none">
              <Command className="h-3 w-3" />
              Enter
            </kbd>
          )}

          {isInputActive && (
            <Button
              size="sm"
              onClick={onClassify}
              disabled={promptEmpty || classifyPending}
              className="h-8 gap-1.5 px-4"
            >
              <Zap className="h-3.5 w-3.5" />
              Classify
            </Button>
          )}

          {showReview && (
            <Button
              size="sm"
              onClick={onConfirm}
              disabled={!selectedWorkflow || phase === "launching"}
              className="h-8 gap-1.5 px-4"
            >
              {phase === "launching" ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Launching...
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5" />
                  Launch
                </>
              )}
            </Button>
          )}
        </div>
      </div>
    </>
  );
}
