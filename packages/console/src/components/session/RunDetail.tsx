import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { formatDuration, formatTokens } from "@/lib/format-utils";
import { formatModelName } from "@/lib/utils";
import { BatonViewer } from "./BatonViewer";
import { ContractPanel } from "./ContractPanel";
import type { HeartbeatRun, WorkflowSession, BatonState } from "@/types/api";

function computeDuration(run: HeartbeatRun): string {
  const start = new Date(run.started_at).getTime();
  const end = run.ended_at ? new Date(run.ended_at).getTime() : Date.now();
  return formatDuration(Math.max(0, Math.floor((end - start) / 1000)));
}

function MetadataRow({
  label,
  value,
}: {
  label: string;
  value: React.ReactNode;
}) {
  return (
    <div className="flex items-baseline justify-between py-1.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="text-sm font-medium">{value}</span>
    </div>
  );
}

function OverviewTab({ run }: { run: HeartbeatRun }) {
  return (
    <div className="space-y-1">
      {run.adapter && <MetadataRow label="Adapter" value={run.adapter} />}
      {run.model && (
        <MetadataRow
          label="Model"
          value={formatModelName(run.model) ?? run.model}
        />
      )}
      <MetadataRow label="Tokens" value={formatTokens(run.total_tokens)} />
      <MetadataRow
        label="Cost"
        value={
          run.cost_usd > 0
            ? run.cost_usd < 0.01
              ? "< $0.01"
              : `$${run.cost_usd.toFixed(2)}`
            : "-"
        }
      />
      <MetadataRow label="Duration" value={computeDuration(run)} />
      <MetadataRow label="Status" value={<Badge variant="outline" className="text-xs">{run.status}</Badge>} />
      {run.error_message && (
        <div className="mt-3 rounded-md border border-red-200 bg-red-50 p-3 text-xs text-red-700 dark:border-red-800 dark:bg-red-950 dark:text-red-300">
          {run.error_message}
        </div>
      )}
    </div>
  );
}

export function RunDetail({
  run,
  session,
}: {
  run: HeartbeatRun;
  session: WorkflowSession;
}) {
  const batonState = run.baton as BatonState | null;

  return (
    <Tabs defaultValue="overview" className="w-full">
      <TabsList className="w-full">
        <TabsTrigger value="overview" className="flex-1">
          Overview
        </TabsTrigger>
        <TabsTrigger value="baton" className="flex-1">
          Baton
        </TabsTrigger>
        <TabsTrigger value="artifacts" className="flex-1">
          Artifacts
        </TabsTrigger>
        <TabsTrigger value="contracts" className="flex-1">
          Contracts
        </TabsTrigger>
      </TabsList>

      <TabsContent value="overview" className="mt-4">
        <OverviewTab run={run} />
      </TabsContent>

      <TabsContent value="baton" className="mt-4">
        <BatonViewer
          baton={batonState ?? session.baton}
          history={session.baton_history}
        />
      </TabsContent>

      <TabsContent value="artifacts" className="mt-4">
        <p className="text-sm text-muted-foreground">
          Artifacts for this run
        </p>
      </TabsContent>

      <TabsContent value="contracts" className="mt-4">
        <ContractPanel events={[]} />
      </TabsContent>
    </Tabs>
  );
}
