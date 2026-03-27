import { useState } from "react";
import { ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { CostBreakdownEntry } from "@/types/api";

interface CostBreakdownTableProps {
  breakdown: CostBreakdownEntry[];
  className?: string;
}

type SortKey = keyof CostBreakdownEntry;
type SortDir = "asc" | "desc";

function formatTokens(tokens: number): string {
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  if (tokens >= 1_000) return `${(tokens / 1_000).toFixed(1)}K`;
  return String(tokens);
}

export function CostBreakdownTable({ breakdown, className }: CostBreakdownTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("cost_usd");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  }

  const sorted = [...breakdown].sort((a, b) => {
    const av = a[sortKey];
    const bv = b[sortKey];
    if (typeof av === "string" && typeof bv === "string") {
      return sortDir === "asc" ? av.localeCompare(bv) : bv.localeCompare(av);
    }
    return sortDir === "asc" ? (av as number) - (bv as number) : (bv as number) - (av as number);
  });

  const columns: { key: SortKey; label: string; align?: "right" }[] = [
    { key: "adapter", label: "Adapter" },
    { key: "model", label: "Model" },
    { key: "session_count", label: "Sessions", align: "right" },
    { key: "total_tokens", label: "Tokens", align: "right" },
    { key: "cost_usd", label: "Cost (USD)", align: "right" },
  ];

  return (
    <div className={cn("rounded-md border", className)}>
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((col) => (
              <TableHead key={col.key} className={col.align === "right" ? "text-right" : undefined}>
                <Button
                  variant="ghost"
                  size="sm"
                  className="-ml-3 h-8 text-xs font-medium"
                  onClick={() => toggleSort(col.key)}
                >
                  {col.label}
                  <ArrowUpDown className="ml-1 h-3 w-3" />
                </Button>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.length === 0 ? (
            <TableRow>
              <TableCell colSpan={columns.length} className="text-center text-muted-foreground text-sm py-6">
                No cost data available.
              </TableCell>
            </TableRow>
          ) : (
            sorted.map((entry, i) => (
              <TableRow key={`${entry.adapter}-${entry.model}-${i}`}>
                <TableCell className="text-sm">{entry.adapter}</TableCell>
                <TableCell className="text-sm font-mono">{entry.model}</TableCell>
                <TableCell className="text-sm text-right tabular-nums">{entry.session_count}</TableCell>
                <TableCell className="text-sm text-right tabular-nums">{formatTokens(entry.total_tokens)}</TableCell>
                <TableCell className="text-sm text-right tabular-nums font-medium">
                  ${entry.cost_usd.toFixed(4)}
                </TableCell>
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  );
}
