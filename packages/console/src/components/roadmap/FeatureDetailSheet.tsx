/**
 * FeatureDetailSheet — slide-out panel for feature details.
 *
 * Shows feature metadata, sessions list, and a Run button.
 * Used by the Roadmap view when clicking a feature card.
 */

import { Link } from "@tanstack/react-router";
import { StatusBadge, type Status } from "@/components/status-badge";
import { StatusDot } from "@/components/status-dot";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Separator } from "@/components/ui/separator";
import { formatTimeAgo, formatTokens } from "@/lib/format-utils";
import { Play, ExternalLink } from "lucide-react";
import type { Feature, SessionListEntry } from "@/types/api";

interface FeatureDetailSheetProps {
  feature: Feature | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  projectId: string;
  onRun: (feature: Feature) => void;
  sessionsByFeature: Map<string, SessionListEntry[]>;
}

export function FeatureDetailSheet({
  feature,
  open,
  onOpenChange,
  projectId,
  onRun,
  sessionsByFeature,
}: FeatureDetailSheetProps) {
  if (!feature) return null;

  const sessions = sessionsByFeature.get(feature.id) ?? [];

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:w-[480px] md:w-[540px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-left">
            <Link
              to="/project/$projectId/features/$featureId"
              params={{ projectId, featureId: feature.id }}
              className="text-primary hover:underline"
            >
              {feature.title}
            </Link>
          </SheetTitle>
        </SheetHeader>

        <div className="mt-4 space-y-5">
          {/* Status + Priority + Type */}
          <div className="flex items-center gap-2 flex-wrap">
            <StatusBadge status={feature.status as Status} />
            <Badge variant="outline">{feature.priority}</Badge>
            <Badge variant="secondary" className="text-xs">
              {feature.type}
            </Badge>
            {feature.branch_name && (
              <Badge variant="outline" className="text-xs font-mono">
                {feature.branch_name}
              </Badge>
            )}
          </div>

          {/* Description */}
          {feature.description && (
            <p className="text-sm text-muted-foreground leading-relaxed">
              {feature.description}
            </p>
          )}

          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">Created</p>
              <p>{formatTimeAgo(feature.created_at)}</p>
            </div>
            {feature.started_at && (
              <div>
                <p className="text-xs text-muted-foreground">Started</p>
                <p>{formatTimeAgo(feature.started_at)}</p>
              </div>
            )}
            <div>
              <p className="text-xs text-muted-foreground">Cost</p>
              <p className="font-mono">
                {feature.total_cost_usd > 0
                  ? `$${feature.total_cost_usd.toFixed(2)}`
                  : "-"}
              </p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Tokens</p>
              <p className="font-mono">
                {feature.total_tokens > 0
                  ? formatTokens(feature.total_tokens)
                  : "-"}
              </p>
            </div>
          </div>

          {/* PR link */}
          {feature.pr_url && (
            <a
              href={feature.pr_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              Pull Request
            </a>
          )}

          {/* Run button */}
          <Button onClick={() => onRun(feature)} className="w-full gap-2">
            <Play className="h-4 w-4" />
            Run Feature
          </Button>

          <Separator />

          {/* Sessions list */}
          <div>
            <h4 className="text-sm font-medium mb-3">
              Sessions ({sessions.length})
            </h4>
            {sessions.length > 0 ? (
              <div className="space-y-2">
                {sessions.map((session) => (
                  <Link
                    key={session.id}
                    to="/project/$projectId/sessions/$sessionId"
                    params={{ projectId, sessionId: session.id }}
                    className="flex items-center gap-3 rounded-md border p-3 hover:bg-muted/50 transition-colors"
                  >
                    <StatusDot status={session.status ?? ""} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {session.display_title || session.id.slice(-8)}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatTimeAgo(session.created_at)}
                      </p>
                    </div>
                    {session.workflow_name && (
                      <Badge variant="outline" className="text-[10px]">
                        {session.workflow_name}
                      </Badge>
                    )}
                  </Link>
                ))}
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                No sessions yet for this feature.
              </p>
            )}
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
