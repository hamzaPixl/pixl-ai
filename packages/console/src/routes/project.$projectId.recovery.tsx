/**
 * Recovery Dashboard — replaces the previous stub.
 *
 * Three tabs:
 * - Inbox: Blocked nodes needing retry/skip
 * - Incidents: Searchable incident table
 * - Lab: Failure signatures, recovery rates, trends
 */

import { createFileRoute, redirect } from "@tanstack/react-router";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageHeader } from "@/components/page-header";
import { InboxTab, IncidentsTab, LabTab } from "@/components/recovery";

export const Route = createFileRoute("/project/$projectId/recovery")({
  beforeLoad: ({ params }) => {
    throw redirect({ to: "/project/$projectId/sessions", params });
  },
  component: RecoveryPage,
});

function RecoveryPage() {
  const { projectId } = Route.useParams();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Recovery"
        description="Manage blocked nodes, review incidents, and analyze failure patterns"
      />

      <Tabs defaultValue="inbox">
        <TabsList>
          <TabsTrigger value="inbox">Inbox</TabsTrigger>
          <TabsTrigger value="incidents">Incidents</TabsTrigger>
          <TabsTrigger value="lab">Lab</TabsTrigger>
        </TabsList>

        <TabsContent value="inbox" className="mt-4">
          <InboxTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="incidents" className="mt-4">
          <IncidentsTab projectId={projectId} />
        </TabsContent>
        <TabsContent value="lab" className="mt-4">
          <LabTab projectId={projectId} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
