/**
 * Gates inbox page.
 */

import { createFileRoute, Link, redirect } from "@tanstack/react-router";
import { useGateInbox, useApproveGate, useRejectGate } from "@/hooks/queries";
import { Card, CardContent } from "@/components/ui/card";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { LoadingSkeletons } from "@/components/loading-skeletons";
import { GateApprovalButtons } from "@/components/shared/GateApprovalButtons";
import { Workflow } from "@/components/icons";
import type { GateInboxItem } from "@/types/api";

export const Route = createFileRoute("/project/$projectId/gates")({
  beforeLoad: ({ params }) => {
    throw redirect({
      to: "/project/$projectId/sessions",
      params,
      search: { tab: "gates" },
    });
  },
  component: GatesPage,
});

function GatesPage() {
  const { projectId } = Route.useParams();
  const { data: inbox, isLoading } = useGateInbox(projectId);

  const pendingGates: GateInboxItem[] = inbox?.gates || [];
  const approveGate = useApproveGate(projectId);
  const rejectGate = useRejectGate(projectId);

  const handleApprove = (sessionId: string, gateId: string) => {
    approveGate.mutate({ sessionId, gateId });
  };

  const handleReject = (sessionId: string, gateId: string) => {
    rejectGate.mutate({ sessionId, gateId });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <PageHeader
        title="Gate Inbox"
        description="Workflow gates awaiting approval"
      />

      {/* Gates list */}
      {isLoading ? (
        <LoadingSkeletons count={3} variant="card" />
      ) : pendingGates.length > 0 ? (
        <div className="space-y-3">
          {pendingGates.map((gate: GateInboxItem) => {
            const sessionId = gate.session_id || "";
            const nodeId = gate.gate_id || "";
            const autonomyMode = gate.autonomy_mode || "assist";
            const autonomyProfile = gate.autonomy_profile;

            return (
              <Card key={`${sessionId}-${nodeId}`}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <Workflow className="h-4 w-4 text-muted-foreground" />
                        <span className="font-medium">{nodeId}</span>
                        <span className="text-xs text-amber-600">
                          Awaiting Approval
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {autonomyMode}
                          {autonomyProfile
                            ? ` • L${autonomyProfile.level} • ${Math.round(autonomyProfile.confidence * 100)}%`
                            : ""}
                        </span>
                      </div>
                      <div className="text-sm text-muted-foreground">
                        <Link
                          to="/project/$projectId/sessions/$sessionId"
                          params={{ projectId, sessionId }}
                          className="font-mono hover:text-primary transition-colors hover:underline"
                        >
                          {sessionId}
                        </Link>
                      </div>
                    </div>
                    <GateApprovalButtons
                      onApprove={() => handleApprove(sessionId, nodeId)}
                      onReject={() => handleReject(sessionId, nodeId)}
                    />
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      ) : (
        <EmptyState icon={Workflow} title="No gates pending approval." />
      )}
    </div>
  );
}
