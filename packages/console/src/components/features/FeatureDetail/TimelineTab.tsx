import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/empty-state";
import { Clock, Circle, ArrowRight } from "lucide-react";
import {
  statusColors,
  timelineStatusIcon,
  timelineStatusColor,
} from "./constants";
import type { TransitionRecord } from "@/types/api";

export interface TimelineTabProps {
  history: TransitionRecord[] | undefined;
}

export function TimelineTab({ history }: TimelineTabProps) {
  if (!history || history.length === 0) {
    return <EmptyState icon={Clock} title="No state transitions recorded." />;
  }

  return (
    <div className="relative">
      {history.map((t, i) => {
        const isLast = i === history.length - 1;
        const icon = timelineStatusIcon[t.to_status] ?? (
          <Circle className="h-4 w-4 text-muted-foreground" />
        );
        const borderColor = timelineStatusColor[t.to_status] ?? "border-muted";

        return (
          <div key={t.id} className="flex gap-4 pb-0">
            {/* Vertical line + icon */}
            <div className="flex flex-col items-center w-8 shrink-0">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full border-2 bg-background z-10 ${borderColor}`}
              >
                {icon}
              </div>
              {!isLast && (
                <div className="w-px flex-1 bg-border min-h-[24px]" />
              )}
            </div>
            {/* Content */}
            <div className="flex-1 pb-6 pt-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                {t.from_status && (
                  <>
                    <Badge variant="outline" className="text-xs font-normal">
                      {t.from_status}
                    </Badge>
                    <ArrowRight className="h-3 w-3 text-muted-foreground shrink-0" />
                  </>
                )}
                <Badge className={`text-xs ${statusColors[t.to_status] ?? ""}`}>
                  {t.to_status}
                </Badge>
              </div>
              <div className="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
                <span>{new Date(t.created_at).toLocaleString()}</span>
                {t.triggered_by && (
                  <span className="flex items-center gap-1">
                    <span className="text-muted-foreground/60">by</span>
                    <span className="font-medium text-foreground/70">
                      {t.triggered_by}
                    </span>
                  </span>
                )}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
