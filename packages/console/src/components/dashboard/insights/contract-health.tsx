import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import type { DashboardOverview } from "@/types/api";

export interface ContractHealthProps {
  data: DashboardOverview | undefined;
}

export function ContractHealth({ data }: ContractHealthProps) {
  const contracts = data?.contracts;

  if (!contracts) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">Contract Health</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground">
            No contract data available
          </p>
        </CardContent>
      </Card>
    );
  }

  const overallPct = Math.round(contracts.overall.ratio * 100);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Contract Health</CardTitle>
          <Badge
            variant={
              overallPct > 80
                ? "success"
                : overallPct > 50
                  ? "warning"
                  : "destructive"
            }
            className="text-[10px] h-5 px-1.5"
          >
            {overallPct}%
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <ContractBar
          label="Features"
          complete={contracts.features.complete}
          total={contracts.features.total}
          ratio={contracts.features.ratio}
        />
        <ContractBar
          label="Epics"
          complete={contracts.epics.complete}
          total={contracts.epics.total}
          ratio={contracts.epics.ratio}
        />
      </CardContent>
    </Card>
  );
}

function ContractBar({
  label,
  complete,
  total,
  ratio,
}: {
  label: string;
  complete: number;
  total: number;
  ratio: number;
}) {
  const pct = Math.round(ratio * 100);
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className="tabular-nums font-medium">
          {complete}/{total} ({pct}%)
        </span>
      </div>
      <Progress
        value={pct}
        className={`h-1.5 ${
          pct > 80
            ? "[&>div]:bg-green-500"
            : pct > 50
              ? "[&>div]:bg-amber-500"
              : "[&>div]:bg-red-500"
        }`}
      />
    </div>
  );
}
