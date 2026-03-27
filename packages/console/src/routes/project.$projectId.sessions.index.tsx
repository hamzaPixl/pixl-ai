/**
 * Sessions page — single page with sessions list + gates section.
 */

import { createFileRoute } from "@tanstack/react-router";
import { useGateInbox } from "@/hooks/queries";
import { Badge } from "@/components/ui/badge";
import { PageHeader } from "@/components/page-header";
import { SessionsListContent } from "@/components/sessions/SessionsListContent";
import { GatesTabContent } from "@/components/sessions/GatesTabContent";
import { RecoverySection } from "@/components/sessions/RecoverySection";
import { ShieldCheck } from "lucide-react";

export const Route = createFileRoute("/project/$projectId/sessions/")({
  component: SessionsPage,
});

function SessionsPage() {
  const { projectId } = Route.useParams();
  const { data: gateInbox } = useGateInbox(projectId);
  const gateCount = gateInbox?.gates?.length ?? 0;

  return (
    <div className="space-y-8">
      <PageHeader title="Sessions" description="Workflow execution history" />

      {/* Sessions list */}
      <SessionsListContent projectId={projectId} />

      {/* Gates section */}
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-4 w-4 text-muted-foreground" />
          <h2 className="text-sm font-medium">Gates</h2>
          {gateCount > 0 && (
            <Badge
              variant="destructive"
              className="h-4 min-w-[16px] px-1 text-[10px]"
            >
              {gateCount}
            </Badge>
          )}
        </div>
        <GatesTabContent projectId={projectId} />
      </section>

      {/* Recovery section */}
      <RecoverySection projectId={projectId} />
    </div>
  );
}
