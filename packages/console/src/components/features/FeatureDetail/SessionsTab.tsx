import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import type { SessionListEntry } from "@/types/api";

export interface SessionsTabProps {
  sessions: SessionListEntry[] | undefined;
  projectId: string;
}

export function SessionsTab({ sessions, projectId }: SessionsTabProps) {
  if (!sessions || sessions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-8 text-center">
        No sessions for this feature yet.
      </p>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Session</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Workflow</TableHead>
          <TableHead>Created</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {sessions.map((s) => (
          <TableRow key={s.id}>
            <TableCell>
              <Link
                to="/project/$projectId/sessions/$sessionId"
                params={{ projectId, sessionId: s.id }}
                className="text-primary underline font-mono text-xs"
              >
                {s.id}
              </Link>
            </TableCell>
            <TableCell>
              <Badge variant="outline">{s.status ?? "unknown"}</Badge>
            </TableCell>
            <TableCell>{s.workflow_name ?? "\u2014"}</TableCell>
            <TableCell className="text-xs text-muted-foreground">
              {new Date(s.created_at).toLocaleString()}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
