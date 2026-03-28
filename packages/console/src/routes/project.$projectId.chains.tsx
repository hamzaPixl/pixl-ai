/**
 * Execution Chains page.
 *
 * Lists all chains with their epic, status, progress, and controls.
 * Clicking a chain shows detail with wave breakdown, signals, and quality.
 */

import { createFileRoute, redirect } from "@tanstack/react-router";
import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { chains, control } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { PageHeader } from "@/components/page-header";
import { EmptyState } from "@/components/empty-state";
import { LoadingSkeletons } from "@/components/loading-skeletons";
import { PaginationControls } from "@/components/pagination-controls";
import { toast } from "sonner";
import { GitBranch } from "lucide-react";
import { ChainTable } from "@/components/chains/ChainTable";
import { ChainDetailSheet } from "@/components/chains/ChainDetailSheet";
import type { ExecutionChainSummary } from "@/types/api";

export const Route = createFileRoute("/project/$projectId/chains")({
  beforeLoad: ({ params }) => {
    throw redirect({ to: "/project/$projectId/sessions", params });
  },
  component: ChainsPage,
});

const PAGE_SIZE = 30;

function ChainsPage() {
  const { projectId } = Route.useParams();
  const queryClient = useQueryClient();
  const [selectedChainId, setSelectedChainId] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  const { data: chainList, isLoading } = useQuery({
    queryKey: queryKeys.chains.list(projectId),
    queryFn: () => chains.list(),
    enabled: !!projectId,
  });

  // Client-side pagination (API returns all chains)
  const paginatedChains = useMemo(() => {
    if (!chainList) return undefined;
    const start = page * PAGE_SIZE;
    return chainList.slice(start, start + PAGE_SIZE);
  }, [chainList, page]);

  const hasNextPage = (chainList?.length ?? 0) > (page + 1) * PAGE_SIZE;

  // Signals for selected chain
  const { data: signals } = useQuery({
    queryKey: queryKeys.chains.signals(projectId, selectedChainId ?? ""),
    queryFn: () => control.getChainSignals(selectedChainId!),
    enabled: !!selectedChainId,
  });

  // Quality for selected chain
  const { data: quality } = useQuery({
    queryKey: queryKeys.chains.quality(projectId, selectedChainId ?? ""),
    queryFn: () => control.getChainQuality(selectedChainId!),
    enabled: !!selectedChainId,
  });

  const invalidateChains = () => {
    queryClient.invalidateQueries({
      queryKey: queryKeys.chains.all(projectId),
    });
  };

  const startMutation = useMutation({
    mutationFn: (id: string) => control.startChain(id),
    onSuccess: () => {
      invalidateChains();
      toast.success("Chain started");
    },
    onError: () => toast.error("Failed to start chain"),
  });

  const pauseMutation = useMutation({
    mutationFn: (id: string) => control.pauseChain(id),
    onSuccess: () => {
      invalidateChains();
      toast.success("Chain paused");
    },
  });

  const resumeMutation = useMutation({
    mutationFn: (id: string) => control.resumeChain(id),
    onSuccess: () => {
      invalidateChains();
      toast.success("Chain resumed");
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => control.cancelChain(id),
    onSuccess: () => {
      invalidateChains();
      toast.success("Chain cancelled");
    },
  });

  const resetMutation = useMutation({
    mutationFn: (id: string) => control.resetChain(id),
    onSuccess: () => {
      invalidateChains();
      toast.success("Chain reset");
    },
  });

  const selectedChain = chainList?.find(
    (c: ExecutionChainSummary) => c.chain_id === selectedChainId,
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Execution Chains"
        description="Epic execution chains with wave-based node orchestration"
      />

      {isLoading ? (
        <LoadingSkeletons count={4} />
      ) : paginatedChains && paginatedChains.length > 0 ? (
        <ChainTable
          chains={paginatedChains}
          onSelectChain={setSelectedChainId}
          startMutation={startMutation}
          pauseMutation={pauseMutation}
          resumeMutation={resumeMutation}
          cancelMutation={cancelMutation}
          resetMutation={resetMutation}
        />
      ) : (
        <EmptyState
          icon={GitBranch}
          title="No execution chains. Run an epic to create a chain."
        />
      )}

      {chainList && chainList.length > PAGE_SIZE && (
        <PaginationControls
          page={page}
          onPageChange={setPage}
          hasNextPage={hasNextPage}
        />
      )}

      <ChainDetailSheet
        projectId={projectId}
        chain={selectedChain}
        open={!!selectedChainId}
        onOpenChange={(open) => !open && setSelectedChainId(null)}
        signals={signals}
        quality={quality}
      />
    </div>
  );
}
