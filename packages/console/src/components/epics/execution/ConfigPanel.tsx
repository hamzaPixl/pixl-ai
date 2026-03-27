import { Link } from "@tanstack/react-router";
import { StatusBadge } from "@/components/status-badge";
import type { EpicWavesResponse } from "@/types/api";

export interface ConfigPanelProps {
  projectId: string;
  workflowId: string;
  onWorkflowIdChange: (value: string) => void;
  parallel: boolean;
  onParallelChange: (value: boolean) => void;
  skipApproval: boolean;
  onSkipApprovalChange: (value: boolean) => void;
  waves: EpicWavesResponse | undefined;
}

export function ConfigPanel({
  projectId,
  workflowId,
  onWorkflowIdChange,
  parallel,
  onParallelChange,
  skipApproval,
  onSkipApprovalChange,
  waves,
}: ConfigPanelProps) {
  return (
    <div className="space-y-4 py-4">
      {/* Workflow selection */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Workflow</label>
        <select
          className="w-full px-3 py-2 border rounded-md bg-background"
          value={workflowId}
          onChange={(e) => onWorkflowIdChange(e.target.value)}
        >
          <option value="tdd">TDD (Test-Driven Development)</option>
          <option value="simple">Simple</option>
        </select>
      </div>

      {/* Execution mode */}
      <div className="space-y-2">
        <label className="text-sm font-medium">Execution Mode</label>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => onParallelChange(false)}
            className={`px-4 py-2 rounded-md border transition-colors ${
              !parallel
                ? "bg-primary text-primary-foreground"
                : "bg-muted hover:bg-muted/80"
            }`}
          >
            Sequential
          </button>
          <button
            type="button"
            onClick={() => onParallelChange(true)}
            className={`px-4 py-2 rounded-md border transition-colors ${
              parallel
                ? "bg-primary text-primary-foreground"
                : "bg-muted hover:bg-muted/80"
            }`}
          >
            Parallel
          </button>
        </div>
      </div>

      {/* Skip approval */}
      <div className="flex items-center space-x-2">
        <input
          type="checkbox"
          id="skip-approval"
          checked={skipApproval}
          onChange={(e) => onSkipApprovalChange(e.target.checked)}
          className="h-4 w-4 rounded border-gray-300"
        />
        <label htmlFor="skip-approval" className="text-sm">
          Auto-approve gates (skip human review)
        </label>
      </div>

      {/* Waves preview */}
      {waves && waves.total_waves > 0 && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-muted-foreground">
            Execution Plan ({waves.total_waves} wave
            {waves.total_waves > 1 ? "s" : ""})
          </label>
          <div className="space-y-2">
            {waves.waves.map((wave, i) => (
              <div key={i} className="pl-4 border-l-2 border-muted">
                <div className="text-xs text-muted-foreground mb-1">
                  Wave {i + 1}
                </div>
                <div className="space-y-1">
                  {wave.map((feature) => (
                    <div
                      key={feature.id}
                      className="flex items-center gap-2 text-sm"
                    >
                      <StatusBadge status={feature.status as any} />
                      <Link
                        to="/project/$projectId/features/$featureId"
                        params={{ projectId, featureId: feature.id }}
                        className="truncate hover:underline"
                      >
                        {feature.title}
                      </Link>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
