import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { recovery } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/empty-state";
import { LoadingSkeletons } from "@/components/loading-skeletons";
import { TrendingUp } from "lucide-react";
import type {
  FailureSignature,
  RecoveryActionRate,
  RecoveryTrendDay,
  HumanGateTrigger,
} from "@/types/api";

export interface LabTabProps {
  projectId: string;
}

export function LabTab({ projectId }: LabTabProps) {
  const { data, isLoading } = useQuery({
    queryKey: queryKeys.recovery.lab(projectId),
    queryFn: () => recovery.lab(),
    enabled: !!projectId,
  });

  if (isLoading) {
    return <LoadingSkeletons count={4} />;
  }

  if (!data) {
    return (
      <EmptyState icon={TrendingUp} title="No recovery analytics data yet" />
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Failure Signatures */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Failure Signatures</CardTitle>
        </CardHeader>
        <CardContent>
          {data.failure_signatures.length > 0 ? (
            <div className="space-y-2">
              {data.failure_signatures.map((sig: FailureSignature) => (
                <div
                  key={sig.error_type}
                  className="flex items-center justify-between text-sm"
                >
                  <span className="font-mono text-xs truncate">
                    {sig.error_type}
                  </span>
                  <div className="flex items-center gap-2 shrink-0">
                    <Badge variant="outline">{sig.count}x</Badge>
                    <span className="text-xs text-muted-foreground">
                      {new Date(sig.last_seen).toLocaleDateString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No failures recorded
            </p>
          )}
        </CardContent>
      </Card>

      {/* Recovery Success Rates */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recovery Success Rates</CardTitle>
        </CardHeader>
        <CardContent>
          {data.recovery_success_rate.length > 0 ? (
            <div className="space-y-2">
              {data.recovery_success_rate.map((rate: RecoveryActionRate) => (
                <div
                  key={rate.recovery_action}
                  className="flex items-center justify-between text-sm"
                >
                  <span>{rate.recovery_action}</span>
                  <div className="flex items-center gap-2">
                    <div className="w-24 bg-muted rounded-full h-2">
                      <div
                        className="bg-primary rounded-full h-2"
                        style={{ width: `${rate.rate * 100}%` }}
                      />
                    </div>
                    <span className="text-xs w-12 text-right">
                      {(rate.rate * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No recovery actions recorded
            </p>
          )}
        </CardContent>
      </Card>

      {/* Daily Trend */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Daily Trend</CardTitle>
        </CardHeader>
        <CardContent>
          {data.trend.length > 0 ? (
            <div className="space-y-1">
              {data.trend.slice(-14).map((day: RecoveryTrendDay) => (
                <div key={day.day} className="flex items-center gap-2 text-xs">
                  <span className="w-20 text-muted-foreground">{day.day}</span>
                  <div className="flex gap-1">
                    {day.succeeded > 0 && (
                      <Badge
                        variant="outline"
                        className="text-[10px] bg-green-50 dark:bg-green-900/20"
                      >
                        {day.succeeded} ok
                      </Badge>
                    )}
                    {day.failed > 0 && (
                      <Badge
                        variant="outline"
                        className="text-[10px] bg-red-50 dark:bg-red-900/20"
                      >
                        {day.failed} fail
                      </Badge>
                    )}
                    {day.escalated > 0 && (
                      <Badge
                        variant="outline"
                        className="text-[10px] bg-orange-50 dark:bg-orange-900/20"
                      >
                        {day.escalated} esc
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No trend data
            </p>
          )}
        </CardContent>
      </Card>

      {/* Human Gate Triggers */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Human Gate Triggers</CardTitle>
        </CardHeader>
        <CardContent>
          {data.human_gate_triggers.length > 0 ? (
            <div className="space-y-2">
              {data.human_gate_triggers.map((trigger: HumanGateTrigger) => (
                <div
                  key={trigger.feature_id}
                  className="flex items-center justify-between text-sm"
                >
                  <Link
                    to="/project/$projectId/features/$featureId"
                    params={{ projectId, featureId: trigger.feature_id }}
                    className="truncate hover:underline"
                  >
                    {trigger.feature_title}
                  </Link>
                  <Badge variant="outline">
                    {trigger.escalation_count} escalations
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              No human escalations
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
