import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { recovery } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/empty-state";
import { LoadingSkeletons } from "@/components/loading-skeletons";
import { PaginationControls } from "@/components/pagination-controls";
import { AlertTriangle } from "lucide-react";
import type { IncidentRecord } from "@/types/api";

const PAGE_SIZE = 30;

export interface IncidentsTabProps {
  projectId: string;
}

export function IncidentsTab({ projectId }: IncidentsTabProps) {
  const [page, setPage] = useState(0);

  const { data, isLoading } = useQuery({
    queryKey: queryKeys.recovery.incidents(projectId, {
      limit: PAGE_SIZE,
      offset: page * PAGE_SIZE,
    }),
    queryFn: () =>
      recovery.incidents({ limit: PAGE_SIZE, offset: page * PAGE_SIZE }),
    enabled: !!projectId,
  });

  const hasNextPage = (data?.length ?? 0) === PAGE_SIZE;

  if (isLoading) {
    return <LoadingSkeletons count={5} />;
  }

  if (!data || data.length === 0) {
    return (
      <EmptyState icon={AlertTriangle} title="No recovery incidents recorded" />
    );
  }

  return (
    <div className="space-y-4">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Error Type</TableHead>
            <TableHead>Outcome</TableHead>
            <TableHead>Session</TableHead>
            <TableHead>Node</TableHead>
            <TableHead>Attempts</TableHead>
            <TableHead>Created</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {data.map((inc: IncidentRecord) => (
            <TableRow key={inc.id}>
              <TableCell className="text-xs font-mono">
                {inc.error_type}
              </TableCell>
              <TableCell>
                <Badge
                  variant={
                    inc.outcome === "resolved" ? "default" : "destructive"
                  }
                  className="text-xs"
                >
                  {inc.outcome}
                </Badge>
              </TableCell>
              <TableCell className="text-xs font-mono">
                {inc.session_id}
              </TableCell>
              <TableCell className="text-xs font-mono">
                {inc.node_id ?? "—"}
              </TableCell>
              <TableCell className="text-center">{inc.attempt_count}</TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {new Date(inc.created_at).toLocaleString()}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <PaginationControls
        page={page}
        onPageChange={setPage}
        hasNextPage={hasNextPage}
      />
    </div>
  );
}
