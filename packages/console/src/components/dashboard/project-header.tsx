/**
 * ProjectHeader — minimal project name with greeting subtitle.
 */

import { Skeleton } from "@/components/ui/skeleton";
import { greeting } from "./helpers";
import type { DashboardOverview } from "@/types/api";

interface ProjectHeaderProps {
  data: DashboardOverview | undefined;
  isLoading: boolean;
}

export function ProjectHeader({ data, isLoading }: ProjectHeaderProps) {
  if (isLoading) {
    return (
      <div className="space-y-1">
        <Skeleton className="h-7 w-48" />
        <Skeleton className="h-4 w-28" />
      </div>
    );
  }

  const projectName = data?.project_name ?? "Project";

  return (
    <div>
      <h1 className="text-xl font-semibold tracking-tight">{projectName}</h1>
      <p className="text-xs text-muted-foreground mt-0.5">{greeting()}</p>
    </div>
  );
}
