import { Link } from '@tanstack/react-router';
import { ArrowLeft, Play, Pause } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { StatusBadge } from '@/components/status-badge';
import { ConnectionBadge } from './ConnectionBadge';

interface SessionHeaderProps {
  projectId: string;
  sessionId: string;
  session: any;
  executionFeature: any;
  epic: any;
  roadmap: any;
  isLive: boolean;
  connectionState: string;
  canPause: boolean;
  canResume: boolean;
  onPause: () => void;
  onResume: () => void;
  isPausePending: boolean;
  isResumePending: boolean;
}

export function SessionHeader({
  projectId,
  sessionId,
  session,
  executionFeature,
  epic,
  roadmap,
  isLive,
  connectionState,
  canPause,
  canResume,
  onPause,
  onResume,
  isPausePending,
  isResumePending,
}: SessionHeaderProps) {
  return (
    <div className="flex items-center justify-between pb-4 border-b">
      <div className="flex items-center gap-4">
        <Link to="/project/$projectId/sessions" params={{ projectId }}>
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back
          </Button>
        </Link>
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-bold">Session Trace</h2>
            {session && <StatusBadge status={session.status} />}
            {executionFeature && (executionFeature as any).type === 'execution' && (
              <Badge variant="outline" className="text-[10px] px-1">
                Execution Feature
              </Badge>
            )}
          </div>
          <p className="text-muted-foreground font-mono text-sm">
            {sessionId} {session?.feature_id && (
              <>
                ·{' '}
                <Link
                  to="/project/$projectId/features/$featureId"
                  params={{ projectId, featureId: session.feature_id }}
                  className="hover:underline"
                >
                  {session.feature_id}
                </Link>
              </>
            )}
          </p>
          {(executionFeature?.epic_id || executionFeature?.roadmap_id) && (
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground mt-1">
              {executionFeature?.epic_id && (
                <span className="flex items-center gap-1">
                  <Badge variant="secondary" className="text-[10px] px-1">
                    Epic
                  </Badge>
                  <span className="font-mono">{executionFeature.epic_id}</span>
                  {epic?.title && (
                    <span className="truncate max-w-[240px]">{epic.title}</span>
                  )}
                </span>
              )}
              {executionFeature?.roadmap_id && (
                <span className="flex items-center gap-1">
                  <Badge variant="secondary" className="text-[10px] px-1">
                    Roadmap
                  </Badge>
                  <span className="font-mono">{executionFeature.roadmap_id}</span>
                  {roadmap?.title && (
                    <span className="truncate max-w-[240px]">{roadmap.title}</span>
                  )}
                </span>
              )}
            </div>
          )}
        </div>
      </div>
      <div className="flex items-center gap-2">
        {canPause && (
          <Button
            variant="outline"
            size="sm"
            onClick={onPause}
            disabled={isPausePending}
          >
            <Pause className="h-4 w-4 mr-2" />
            Pause
          </Button>
        )}
        {canResume && (
          <Button
            variant="outline"
            size="sm"
            onClick={onResume}
            disabled={isResumePending}
          >
            <Play className="h-4 w-4 mr-2" />
            Resume
          </Button>
        )}
        {isLive && <ConnectionBadge state={connectionState} />}
      </div>
    </div>
  );
}
