import { Button } from "@/components/ui/button";
import { Loader2, Play, Pause, RotateCcw, X } from "lucide-react";

export interface ExecutionFooterProps {
  isActive: boolean;
  isTerminal: boolean;
  isFailed: boolean;
  status: string | undefined;
  chainId: string | undefined;
  onStart: () => void;
  onRetry: () => void;
  onCancel: () => void;
  onPause: () => void;
  onResume: () => void;
  onClose: () => void;
  isStartPending: boolean;
  isCancelPending: boolean;
  isPausePending: boolean;
  isResumePending: boolean;
}

export function ExecutionFooter({
  isActive,
  isTerminal,
  isFailed,
  status,
  chainId,
  onStart,
  onRetry,
  onCancel,
  onPause,
  onResume,
  onClose,
  isStartPending,
  isCancelPending,
  isPausePending,
  isResumePending,
}: ExecutionFooterProps) {
  return (
    <>
      {/* Cancel button — visible when chain is running */}
      {isActive && status === "running" && (
        <Button
          variant="destructive"
          onClick={onCancel}
          disabled={isCancelPending}
          className="w-full sm:w-auto"
        >
          {isCancelPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Cancelling...
            </>
          ) : (
            <>
              <X className="h-4 w-4 mr-2" />
              Cancel
            </>
          )}
        </Button>
      )}

      {/* Pause button — visible when chain is running */}
      {isActive && status === "running" && chainId && (
        <Button
          variant="outline"
          onClick={onPause}
          disabled={isPausePending}
          className="w-full sm:w-auto"
        >
          {isPausePending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Pausing...
            </>
          ) : (
            <>
              <Pause className="h-4 w-4 mr-2" />
              Pause
            </>
          )}
        </Button>
      )}

      {/* Resume button — visible when chain is paused */}
      {isActive && status === "paused" && chainId && (
        <Button
          variant="default"
          onClick={onResume}
          disabled={isResumePending}
          className="w-full sm:w-auto"
        >
          {isResumePending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Resuming...
            </>
          ) : (
            <>
              <RotateCcw className="h-4 w-4 mr-2" />
              Resume
            </>
          )}
        </Button>
      )}

      <div className="flex-1" />

      {/* Retry button — visible when chain failed or was cancelled */}
      {isActive && isFailed && (
        <Button
          onClick={onRetry}
          disabled={isStartPending}
          className="w-full sm:w-auto"
        >
          {isStartPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Resetting...
            </>
          ) : (
            <>
              <RotateCcw className="h-4 w-4 mr-2" />
              Retry
            </>
          )}
        </Button>
      )}

      {/* Start button — only when no active chain */}
      {!isActive && (
        <Button
          onClick={onStart}
          disabled={isStartPending}
          className="w-full sm:w-auto"
        >
          {isStartPending ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Starting...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Start Epic Execution
            </>
          )}
        </Button>
      )}

      {/* Close button — visible when chain is terminal */}
      {isActive && isTerminal && (
        <Button
          variant="outline"
          onClick={onClose}
          className="w-full sm:w-auto"
        >
          Close
        </Button>
      )}
    </>
  );
}
