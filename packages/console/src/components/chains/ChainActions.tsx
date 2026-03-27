import { Button } from "@/components/ui/button";
import { Play, Pause, RotateCcw, XCircle } from "lucide-react";
import type { UseMutationResult } from "@tanstack/react-query";

export interface ChainActionsProps {
  chainId: string;
  status: string;
  startMutation: UseMutationResult<unknown, unknown, string>;
  pauseMutation: UseMutationResult<unknown, unknown, string>;
  resumeMutation: UseMutationResult<unknown, unknown, string>;
  cancelMutation: UseMutationResult<unknown, unknown, string>;
  resetMutation: UseMutationResult<unknown, unknown, string>;
}

export function ChainActions({
  chainId,
  status,
  startMutation,
  pauseMutation,
  resumeMutation,
  cancelMutation,
  resetMutation,
}: ChainActionsProps) {
  return (
    <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
      {status === "plan_ready" && (
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7"
          onClick={() => startMutation.mutate(chainId)}
          title="Start"
        >
          <Play className="h-3 w-3" />
        </Button>
      )}
      {status === "running" && (
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7"
          onClick={() => pauseMutation.mutate(chainId)}
          title="Pause"
        >
          <Pause className="h-3 w-3" />
        </Button>
      )}
      {status === "paused" && (
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7"
          onClick={() => resumeMutation.mutate(chainId)}
          title="Resume"
        >
          <Play className="h-3 w-3" />
        </Button>
      )}
      {["running", "paused"].includes(status) && (
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7"
          onClick={() => cancelMutation.mutate(chainId)}
          title="Cancel"
        >
          <XCircle className="h-3 w-3" />
        </Button>
      )}
      {["failed", "cancelled"].includes(status) && (
        <Button
          size="icon"
          variant="ghost"
          className="h-7 w-7"
          onClick={() => resetMutation.mutate(chainId)}
          title="Reset"
        >
          <RotateCcw className="h-3 w-3" />
        </Button>
      )}
    </div>
  );
}
