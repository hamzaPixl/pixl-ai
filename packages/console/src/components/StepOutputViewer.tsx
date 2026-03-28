/**
 * Step Output Viewer - Expandable step details with stdout/stderr.
 */

import { useState } from "react";
import { CheckCircle2, XCircle, ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { NodeInstance } from "@/types/api";

// Extended NodeInstance with output property
interface NodeInstanceWithOutput extends NodeInstance {
  output?: Record<string, unknown>;
}

interface StepOutputViewerProps {
  node: NodeInstance;
}

export function StepOutputViewer({ node }: StepOutputViewerProps) {
  const nodeWithOutput = node as NodeInstanceWithOutput;
  const [expanded, setExpanded] = useState(false);

  const statusConfig = {
    completed: { icon: <CheckCircle2 className="h-4 w-4 text-green-500" />, label: "Completed" },
    failed: { icon: <XCircle className="h-4 w-4 text-red-500" />, label: "Failed" },
    running: { icon: <div className="h-4 w-4 text-blue-500" />, label: "Running" },
    pending: { icon: <div className="h-4 w-4 text-muted-foreground" />, label: "Pending" },
    gate_waiting: { icon: <div className="h-4 w-4 text-yellow-500" />, label: "Awaiting Approval" },
    gate_approved: { icon: <CheckCircle2 className="h-4 w-4 text-green-500" />, label: "Approved" },
    gate_rejected: { icon: <XCircle className="h-4 w-4 text-red-500" />, label: "Rejected" },
    task_skipped: { icon: <ChevronRight className="h-4 w-4 text-muted-foreground" />, label: "Skipped" },
  };

  const config = statusConfig[node.state as keyof typeof statusConfig] || statusConfig.pending;

  const duration = node.started_at && node.ended_at
    ? `${Math.round((new Date(node.ended_at).getTime() - new Date(node.started_at).getTime()) / 1000)}s`
    : null;

  return (
    <div className="border rounded-md bg-card overflow-hidden">
      {/* Header - always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 p-3 text-left hover:bg-muted/50 transition-colors"
      >
        <div className="flex-shrink-0 text-muted-foreground">
          {expanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
        </div>

        {config.icon}

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{node.node_id}</span>
            <Badge variant="outline" className="text-xs">
              {config.label}
            </Badge>
            {node.attempt > 1 && (
              <Badge variant="secondary" className="text-xs">
                Attempt {node.attempt}
              </Badge>
          )}
          </div>
          {node.started_at && (
            <div className="text-xs text-muted-foreground mt-0.5">
              Started: {new Date(node.started_at).toLocaleTimeString()}
              {duration && ` • Duration: ${duration}`}
            </div>
          )}
        </div>

        {node.blocked_reason && (
          <div className="text-xs text-destructive max-w-[200px] truncate">
            {node.blocked_reason}
          </div>
        )}
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t p-3 bg-muted/20 space-y-3">
          {/* Error details for failed nodes */}
          {node.state?.includes("failed") && node.error_message && (
            <div className="flex items-start gap-2 p-3 rounded-md bg-red-500/10 border border-red-500/30">
              <AlertTriangle className="h-4 w-4 text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-sm font-medium text-red-600">Error</span>
                  {node.failure_kind && (
                    <Badge variant="outline" className="text-[10px] px-1 text-red-600 border-red-500/50">
                      {node.failure_kind}
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-red-500 break-words whitespace-pre-wrap">
                  {node.error_message}
                </p>
              </div>
            </div>
          )}

          {/* Output section */}
          {nodeWithOutput.output && typeof nodeWithOutput.output === "object" && (
            <div className="space-y-3">
              <div className="text-xs font-medium text-muted-foreground uppercase">
                Output
              </div>
              <OutputContent output={nodeWithOutput.output} />
            </div>
          )}

          {/* No output message (only when no error and no output) */}
          {!nodeWithOutput.output && !(node.state?.includes("failed") && node.error_message) && (
            <p className="text-sm text-muted-foreground italic">No output available</p>
          )}
        </div>
      )}
    </div>
  );
}

interface OutputContentProps {
  output: Record<string, unknown>;
}

function OutputContent({ output }: OutputContentProps) {
  const entries = Object.entries(output);

  if (entries.length === 0) {
    return <p className="text-sm text-muted-foreground italic">Empty output</p>;
  }

  return (
    <div className="space-y-2">
      {entries.map(([key, value]) => (
        <div key={key} className="text-sm">
          <div className="font-medium text-muted-foreground mb-1">{key}:</div>
          <OutputValue value={value} />
        </div>
      ))}
    </div>
  );
}

function OutputValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) {
    return <span className="text-muted-foreground italic">null</span>;
  }

  if (typeof value === "boolean") {
    return <span className={value ? "text-green-600" : "text-red-600"}>{String(value)}</span>;
  }

  if (typeof value === "number") {
    return <span className="font-mono">{value}</span>;
  }

  if (typeof value === "string") {
    return <code className="block bg-muted p-2 rounded text-xs overflow-x-auto">
      {value}
    </code>;
  }

  if (Array.isArray(value)) {
    return (
      <div className="space-y-1">
        {value.map((item, i) => (
          <div key={i} className="pl-4 border-l border-muted-foreground/30">
            <OutputValue value={item} />
          </div>
        ))}
      </div>
    );
  }

  if (typeof value === "object") {
    return (
      <div className="space-y-1 pl-4 border-l border-muted-foreground/30">
        {Object.entries(value as Record<string, unknown>).map(([k, v]) => (
          <div key={k}>
            <span className="font-medium text-muted-foreground">{k}:</span>{" "}
            <OutputValue value={v} />
          </div>
        ))}
      </div>
    );
  }

  return <span className="text-muted-foreground">{String(value)}</span>;
}
