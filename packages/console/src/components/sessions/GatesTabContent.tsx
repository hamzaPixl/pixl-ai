/**
 * Gates list — compact rows matching session row style.
 */

import { Link } from "@tanstack/react-router";
import { useGateInbox, useApproveGate, useRejectGate } from "@/hooks/queries";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle2, XCircle, ShieldCheck } from "lucide-react";
import type { GateInboxItem } from "@/types/api";

export interface GatesTabContentProps {
  projectId: string;
}

export function GatesTabContent({ projectId }: GatesTabContentProps) {
  const { data: inbox, isLoading } = useGateInbox(projectId);
  const pendingGates: GateInboxItem[] = inbox?.gates || [];
  const approveGate = useApproveGate(projectId);
  const rejectGate = useRejectGate(projectId);

  if (isLoading) {
    return (
      <div className="space-y-px">
        {[1, 2].map((i) => (
          <div key={i} className="flex items-center gap-3 px-3 py-2">
            <Skeleton className="h-3.5 w-3.5 rounded" />
            <Skeleton className="h-4 w-32" />
            <div className="flex-1" />
            <Skeleton className="h-6 w-16" />
          </div>
        ))}
      </div>
    );
  }

  if (pendingGates.length === 0) {
    return (
      <p className="px-3 py-2 text-xs text-muted-foreground">
        No gates pending approval.
      </p>
    );
  }

  return (
    <div className="space-y-px">
      {pendingGates.map((gate: GateInboxItem) => {
        const sessionId = gate.session_id || "";
        const nodeId = gate.gate_id || "";
        const autonomyMode = gate.autonomy_mode || "assist";
        const autonomyProfile = gate.autonomy_profile;

        return (
          <div
            key={`${sessionId}-${nodeId}`}
            className="group flex items-center gap-3 px-3 py-1.5 rounded-md border border-transparent hover:border-border hover:bg-muted/50 transition-colors"
          >
            <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-amber-500" />

            <span className="text-sm font-medium truncate">{nodeId}</span>

            <Badge
              variant="outline"
              className="text-[10px] px-1.5 py-0 h-5 text-amber-600 border-amber-500/30 bg-amber-500/5"
            >
              Awaiting
            </Badge>

            <span className="text-[10px] text-muted-foreground">
              {autonomyMode}
              {autonomyProfile
                ? ` · L${autonomyProfile.level} · ${Math.round(autonomyProfile.confidence * 100)}%`
                : ""}
            </span>

            <Link
              to="/project/$projectId/sessions/$sessionId"
              params={{ projectId, sessionId }}
              className="text-[10px] font-mono text-muted-foreground/50 hover:text-primary transition-colors hover:underline"
            >
              {sessionId.slice(-8)}
            </Link>

            <div className="flex-1" />

            <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs text-destructive hover:text-destructive"
                onClick={() => rejectGate.mutate({ sessionId, gateId: nodeId })}
              >
                <XCircle className="h-3.5 w-3.5 mr-1" />
                Reject
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 px-2 text-xs text-green-600 hover:text-green-600"
                onClick={() =>
                  approveGate.mutate({ sessionId, gateId: nodeId })
                }
              >
                <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                Approve
              </Button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
