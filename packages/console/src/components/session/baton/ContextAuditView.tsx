import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { ContextAuditEntry, ContextSliceInfo } from "@/types/api";

export interface ContextAuditViewProps {
  entries: ContextAuditEntry[];
}

export function ContextAuditView({ entries }: ContextAuditViewProps) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No context audit data recorded yet
      </p>
    );
  }

  return (
    <div className="space-y-3">
      {entries.map((entry, i) => (
        <ContextAuditCard key={i} entry={entry} />
      ))}
    </div>
  );
}

function ContextAuditCard({ entry }: { entry: ContextAuditEntry }) {
  const [expanded, setExpanded] = useState(false);
  const pct = Math.round(entry.utilization * 100);
  const progressValue = Math.min(pct, 100);

  const colorClass =
    pct > 95 ? "text-red-500" : pct > 80 ? "text-yellow-500" : "text-green-500";

  const progressColor =
    pct > 95
      ? "[&>div]:bg-red-500"
      : pct > 80
        ? "[&>div]:bg-yellow-500"
        : "[&>div]:bg-green-500";

  return (
    <Card>
      <CardHeader className="py-3 px-4">
        <button
          className="flex items-center justify-between w-full"
          onClick={() => setExpanded((v) => !v)}
        >
          <div className="flex items-center gap-2">
            {expanded ? (
              <ChevronDown className="h-3 w-3" />
            ) : (
              <ChevronRight className="h-3 w-3" />
            )}
            <Badge variant="secondary" className="text-[10px] px-1">
              {entry.stage_id}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {entry.slice_count} slices
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-24">
              <Progress value={progressValue} className={progressColor} />
            </div>
            <span className={`text-xs font-mono font-medium ${colorClass}`}>
              {pct}%
            </span>
            <span className="text-xs text-muted-foreground">
              {entry.total_tokens.toLocaleString()} /{" "}
              {entry.budget_tokens.toLocaleString()} tokens
            </span>
          </div>
        </button>
      </CardHeader>

      {expanded && entry.slices.length > 0 && (
        <CardContent className="pt-0 px-4 pb-3">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="text-xs">Artifact</TableHead>
                <TableHead className="text-xs">Layer</TableHead>
                <TableHead className="text-xs">Reason</TableHead>
                <TableHead className="text-xs text-right">Tokens</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {entry.slices.map((slice, i) => (
                <SliceRow key={i} slice={slice} />
              ))}
            </TableBody>
          </Table>
        </CardContent>
      )}
    </Card>
  );
}

const layerColors: Record<string, string> = {
  summary: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  diff: "bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300",
  excerpt:
    "bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300",
  full: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
};

function SliceRow({ slice }: { slice: ContextSliceInfo }) {
  return (
    <TableRow>
      <TableCell className="text-xs font-mono py-1.5">
        {slice.artifact_id}
        <span className="text-muted-foreground ml-1">
          {slice.hash.slice(0, 8)}
        </span>
      </TableCell>
      <TableCell className="py-1.5">
        <span
          className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${layerColors[slice.layer] || ""}`}
        >
          {slice.layer}
        </span>
      </TableCell>
      <TableCell className="text-xs text-muted-foreground py-1.5">
        {slice.reason}
        {slice.excerpt_range && (
          <span className="ml-1 font-mono">
            L{slice.excerpt_range[0]}-{slice.excerpt_range[1]}
          </span>
        )}
      </TableCell>
      <TableCell className="text-xs text-right font-mono py-1.5">
        {slice.token_estimate.toLocaleString()}
      </TableCell>
    </TableRow>
  );
}
