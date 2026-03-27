import { AlertTriangle, ShieldQuestion, Play, Check, X, RefreshCw, SkipForward, XCircle, Ban } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import type { NodeInstance } from '@/types/api';

/** Structured error detail returned by 409 resume responses. */
export interface ResumeErrorDetail {
  suggestion?: 'approve_gate' | 'wait' | 'force_resume';
  waiting_gates?: string[];
  running_tasks?: string[];
  current_status?: string;
}

interface NeedsAttentionRailProps {
  isStalled: boolean;
  isOrphaned: boolean;
  pendingGates: Array<{
    nodeId: string;
    nodeInstance?: NodeInstance;
  }>;
  failedNodes: Array<{
    nodeId: string;
    errorMessage?: string;
    failureKind?: string;
  }>;
  blockedNodes: Array<{
    nodeId: string;
    blockedReason?: string;
  }>;
  onResume: () => void;
  isResumePending: boolean;
  onApproveGate: (gateId: string) => void;
  onRejectGate: (gateId: string) => void;
  onRetryNode: (nodeId: string) => void;
  onRetryBlockedNode: (nodeId: string) => void;
  onSkipNode: (nodeId: string) => void;
  isRetryPending: boolean;
  /** Called when user clicks the force-resume button. */
  onForceResume?: () => void;
  isForceResumePending?: boolean;
  /** Structured 409 error from a failed resume attempt. */
  resumeError?: ResumeErrorDetail | null;
}

export function NeedsAttentionRail({
  isStalled,
  isOrphaned,
  pendingGates,
  failedNodes,
  blockedNodes,
  onResume,
  isResumePending,
  onApproveGate,
  onRejectGate,
  onRetryNode,
  onRetryBlockedNode,
  onSkipNode,
  isRetryPending,
  onForceResume,
  isForceResumePending,
  resumeError,
}: NeedsAttentionRailProps) {
  const showForceResume = resumeError?.suggestion === 'force_resume' && onForceResume;
  const hasItems = isStalled || isOrphaned || pendingGates.length > 0 || failedNodes.length > 0 || blockedNodes.length > 0 || !!showForceResume;
  if (!hasItems) return null;

  const hasTopBanner = isStalled || isOrphaned;
  const showSeparatorBeforeGates = hasTopBanner && pendingGates.length > 0;
  const showSeparatorBeforeFailed = (hasTopBanner || pendingGates.length > 0) && failedNodes.length > 0;
  const showSeparatorBeforeBlocked = (hasTopBanner || pendingGates.length > 0 || failedNodes.length > 0) && blockedNodes.length > 0;

  return (
    <div className="sticky top-0 z-10 bg-background/95 backdrop-blur-sm border-b rounded-md mt-2 overflow-hidden">
      {isStalled && !isOrphaned && (
        <div className="flex items-center gap-3 px-4 py-3 bg-orange-500/10">
          <AlertTriangle className="h-5 w-5 text-orange-500 flex-shrink-0" />
          <div className="flex-1 text-sm">
            <span className="font-medium text-orange-600">Session stalled.</span>{' '}
            <span className="text-muted-foreground">
              No activity detected recently. The executor may have crashed.
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onResume}
            disabled={isResumePending}
          >
            <Play className="h-4 w-4 mr-2" />
            Resume
          </Button>
        </div>
      )}

      {isOrphaned && (
        <div className="flex items-center gap-3 px-4 py-3 bg-red-500/10">
          <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0" />
          <div className="flex-1 text-sm">
            <span className="font-medium text-red-600">Session executor died.</span>{' '}
            <span className="text-muted-foreground">
              The execution lease is stale — the background process is no longer running. Click Resume to restart.
            </span>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={onResume}
            disabled={isResumePending}
          >
            <Play className="h-4 w-4 mr-2" />
            Resume
          </Button>
        </div>
      )}

      {showSeparatorBeforeGates && <Separator />}

      {pendingGates.map((gate, idx) => (
        <div key={gate.nodeId}>
          {idx > 0 && <Separator />}
          <div className="flex items-center gap-3 px-4 py-3 bg-yellow-500/5">
            <ShieldQuestion className="h-5 w-5 text-yellow-500 flex-shrink-0" />
            <div className="flex-1 text-sm">
              <span className="font-medium text-yellow-600">Gate awaiting approval</span>{' '}
              <span className="font-mono text-xs text-muted-foreground">{gate.nodeId}</span>
              {gate.nodeInstance?.agent_name && (
                <span className="text-xs text-muted-foreground"> via {gate.nodeInstance.agent_name}</span>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                className="text-destructive hover:bg-destructive hover:text-destructive-foreground h-7 text-xs"
                onClick={() => onRejectGate(gate.nodeId)}
              >
                <X className="h-3 w-3 mr-1" />
                Reject
              </Button>
              <Button
                size="sm"
                className="bg-green-600 hover:bg-green-700 h-7 text-xs"
                onClick={() => onApproveGate(gate.nodeId)}
              >
                <Check className="h-3 w-3 mr-1" />
                Approve
              </Button>
            </div>
          </div>
        </div>
      ))}

      {showSeparatorBeforeFailed && <Separator />}

      {failedNodes.map((node, idx) => (
        <div key={node.nodeId}>
          {idx > 0 && <Separator />}
          <div className="flex items-center gap-3 px-4 py-3 bg-red-500/10">
            <XCircle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <div className="flex-1 text-sm min-w-0">
              <span className="font-medium text-red-600">Node failed</span>{' '}
              <span className="font-mono text-xs text-muted-foreground">{node.nodeId}</span>
              {node.errorMessage && (
                <p className="text-xs text-muted-foreground mt-0.5 truncate">{node.errorMessage}</p>
              )}
              {node.failureKind && (
                <span className="text-[10px] text-muted-foreground"> ({node.failureKind})</span>
              )}
            </div>
            <Button
              size="sm"
              variant="outline"
              className="h-7 text-xs"
              onClick={() => onRetryNode(node.nodeId)}
              disabled={isRetryPending}
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Retry
            </Button>
          </div>
        </div>
      ))}

      {showForceResume && (
        <>
          {(hasTopBanner || pendingGates.length > 0 || failedNodes.length > 0) && <Separator />}
          <div className="flex items-center gap-3 px-4 py-3 bg-red-500/10">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <div className="flex-1 text-sm">
              <span className="font-medium text-red-600">Session stuck.</span>{' '}
              <span className="text-muted-foreground">
                The executor crashed while a gate was waiting. Force resume will reset stuck gates and restart.
                {resumeError?.waiting_gates && resumeError.waiting_gates.length > 0 && (
                  <> Stuck gates: <span className="font-mono text-xs">{resumeError.waiting_gates.join(', ')}</span></>
                )}
              </span>
            </div>
            <Button
              variant="destructive"
              size="sm"
              onClick={onForceResume}
              disabled={isForceResumePending}
            >
              <Play className="h-4 w-4 mr-2" />
              Force Resume
            </Button>
          </div>
        </>
      )}

      {showSeparatorBeforeBlocked && <Separator />}

      {blockedNodes.map((node, idx) => (
        <div key={node.nodeId}>
          {idx > 0 && <Separator />}
          <div className="flex items-center gap-3 px-4 py-3 bg-orange-500/10">
            <Ban className="h-5 w-5 text-orange-500 flex-shrink-0" />
            <div className="flex-1 text-sm min-w-0">
              <span className="font-medium text-orange-600">Node blocked</span>{' '}
              <span className="font-mono text-xs text-muted-foreground">{node.nodeId}</span>
              {node.blockedReason && (
                <p className="text-xs text-muted-foreground mt-0.5 truncate">{node.blockedReason}</p>
              )}
            </div>
            <div className="flex items-center gap-2">
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => onSkipNode(node.nodeId)}
                disabled={isRetryPending}
              >
                <SkipForward className="h-3 w-3 mr-1" />
                Skip
              </Button>
              <Button
                size="sm"
                variant="outline"
                className="h-7 text-xs"
                onClick={() => onRetryBlockedNode(node.nodeId)}
                disabled={isRetryPending}
              >
                <RefreshCw className="h-3 w-3 mr-1" />
                Retry
              </Button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
