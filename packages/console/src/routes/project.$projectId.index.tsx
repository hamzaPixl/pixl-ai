/**
 * Project Home — Linear-inspired command center dashboard.
 *
 * Flat layout with subtle section dividers instead of card-heavy UI.
 * Sections: Header + Metrics strip → Attention bar → Progress + Sessions → Activity + Stats
 */

import { createFileRoute } from "@tanstack/react-router";
import { useFactoryHome, useStalledRuns } from "@/hooks/queries";
import { ProjectHeader } from "@/components/dashboard/project-header";
import { MetricCards } from "@/components/dashboard/MetricCards";
import { NeedsAttention } from "@/components/dashboard/needs-attention";
import { ActiveSessionsPanel } from "@/components/dashboard/ActiveSessionsPanel";
import { FeatureDistributionChart } from "@/components/dashboard/feature-distribution-chart";
import { CostAndTiming } from "@/components/dashboard/insights/cost-and-timing";
import { RecoveryAndAutonomy } from "@/components/dashboard/insights/recovery-and-autonomy";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { SessionsOverview } from "@/components/dashboard/sessions-overview";
import { WorkflowUsageChart } from "@/components/dashboard/workflow-usage-chart";

// ─── Route ──────────────────────────────────────────────────────────

export const Route = createFileRoute("/project/$projectId/")({
  component: HomePage,
});

function HomePage() {
  const { projectId } = Route.useParams();
  const { data, isLoading, error } = useFactoryHome(projectId);
  const { data: stalledRuns } = useStalledRuns(projectId);

  if (error) {
    return (
      <div className="text-center py-12">
        <p className="text-destructive">
          Error loading dashboard: {error.message}
        </p>
      </div>
    );
  }

  const activeSessions = data?.active_sessions ?? [];
  const pendingGates = data?.pending_gates ?? [];

  return (
    <div className="space-y-1">
      {/* Header + inline metrics */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <ProjectHeader data={data} isLoading={isLoading} />
        <QuickActions
          projectId={projectId}
          hasPendingGates={pendingGates.length > 0}
        />
      </div>

      {data?.stats && (
        <MetricCards
          stats={data.stats}
          cost={data.cost}
          completionPct={data.completion_pct}
          activeSessionCount={activeSessions.length}
          isLoading={isLoading}
        />
      )}

      <NeedsAttention data={data} projectId={projectId} isLoading={isLoading} />

      {/* Main content — 3-column on wide, stacks down */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 pt-2">
        {/* LEFT — wide: sessions + recent */}
        <div className="lg:col-span-7 space-y-8">
          <ActiveSessionsPanel
            sessions={activeSessions}
            projectId={projectId}
            stalledRuns={stalledRuns}
          />
          <SessionsOverview data={data} projectId={projectId} />
          <WorkflowUsageChart data={data} />
        </div>

        {/* RIGHT — narrow: stats sidebar */}
        <div className="lg:col-span-5 space-y-8">
          <FeatureDistributionChart data={data} />
          <CostAndTiming data={data} />
          <RecoveryAndAutonomy data={data} />
        </div>
      </div>
    </div>
  );
}
