import { createFileRoute } from "@tanstack/react-router";
import { Globe } from "lucide-react";

export const Route = createFileRoute("/project/$projectId/settings/dns")({
  component: DnsSettings,
});

function DnsSettings() {
  return (
    <div className="max-w-2xl space-y-10">
      <div>
        <h2 className="text-lg font-semibold">DNS</h2>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Custom domain routing for deployments.
        </p>
      </div>

      <div className="rounded-lg border border-dashed p-8 text-center space-y-3">
        <Globe className="mx-auto h-8 w-8 text-muted-foreground" />
        <div>
          <p className="text-sm font-medium">Coming soon</p>
          <p className="text-sm text-muted-foreground mt-1">
            Custom domain configuration will be available in a future update.
          </p>
        </div>
      </div>
    </div>
  );
}
