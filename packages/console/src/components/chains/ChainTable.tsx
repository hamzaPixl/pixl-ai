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
import { ChainActions } from "./ChainActions";
import { statusColors } from "./chain-status-colors";
import type { ExecutionChainSummary } from "@/types/api";
import type { UseMutationResult } from "@tanstack/react-query";

export interface ChainTableProps {
  chains: ExecutionChainSummary[];
  onSelectChain: (chainId: string) => void;
  startMutation: UseMutationResult<unknown, unknown, string>;
  pauseMutation: UseMutationResult<unknown, unknown, string>;
  resumeMutation: UseMutationResult<unknown, unknown, string>;
  cancelMutation: UseMutationResult<unknown, unknown, string>;
  resetMutation: UseMutationResult<unknown, unknown, string>;
}

export function ChainTable({
  chains,
  onSelectChain,
  startMutation,
  pauseMutation,
  resumeMutation,
  cancelMutation,
  resetMutation,
}: ChainTableProps) {
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Chain</TableHead>
          <TableHead>Epic</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Progress</TableHead>
          <TableHead>Wave</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {chains.map((chain: ExecutionChainSummary) => (
          <TableRow
            key={chain.chain_id}
            className="cursor-pointer"
            onClick={() => onSelectChain(chain.chain_id)}
          >
            <TableCell className="font-mono text-xs">
              {chain.chain_id}
            </TableCell>
            <TableCell>
              <span className="text-sm">
                {chain.epic_title ?? chain.epic_id}
              </span>
            </TableCell>
            <TableCell>
              <Badge className={statusColors[chain.status] ?? ""}>
                {chain.status.replace(/_/g, " ")}
              </Badge>
            </TableCell>
            <TableCell>
              <div className="flex items-center gap-2 min-w-[120px]">
                <Progress value={chain.progress_pct} className="h-1.5 flex-1" />
                <span className="text-xs text-muted-foreground w-10 text-right">
                  {chain.completed_nodes}/{chain.total_nodes}
                </span>
              </div>
            </TableCell>
            <TableCell className="text-xs">
              {chain.current_wave}/{chain.total_waves}
            </TableCell>
            <TableCell>
              <ChainActions
                chainId={chain.chain_id}
                status={chain.status}
                startMutation={startMutation}
                pauseMutation={pauseMutation}
                resumeMutation={resumeMutation}
                cancelMutation={cancelMutation}
                resetMutation={resetMutation}
              />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
