import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Play } from "lucide-react";

export interface EpicHeaderProps {
  projectId: string;
  epicId: string;
  title: string;
  status: string;
  statusColors: Record<string, string>;
  onRun: () => void;
  isRunPending: boolean;
}

export function EpicHeader({
  projectId,
  epicId,
  title,
  status,
  statusColors,
  onRun,
  isRunPending,
}: EpicHeaderProps) {
  return (
    <div className="flex items-center gap-3">
      <Button variant="ghost" size="icon" asChild>
        <Link to="/project/$projectId/epics" params={{ projectId }}>
          <ArrowLeft className="h-4 w-4" />
        </Link>
      </Button>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold tracking-tight truncate">
            {title}
          </h2>
          <Badge className={statusColors[status] ?? ""}>{status}</Badge>
        </div>
        <p className="text-sm text-muted-foreground mt-1">{epicId}</p>
      </div>
      <Button size="sm" onClick={onRun} disabled={isRunPending}>
        <Play className="h-3.5 w-3.5 mr-1" />
        Run Epic
      </Button>
    </div>
  );
}
