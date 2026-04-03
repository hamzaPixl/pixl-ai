/**
 * SandboxStatus -- compact badge showing active sandbox state.
 *
 * Displays container status and quick destroy action.
 * Polls every 10s. Sandboxes are ephemeral -- they exist only during execution.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sandboxes, type SandboxInfo } from "@/lib/api/sandboxes";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from "@/components/ui/dropdown-menu";
import { Container, Square } from "lucide-react";
import { toast } from "sonner";

const statusColors: Record<string, string> = {
  running: "bg-green-500",
  created: "bg-yellow-500",
  started: "bg-green-500",
};

export function SandboxStatus() {
  const queryClient = useQueryClient();

  const { data: sandboxList = [] } = useQuery<SandboxInfo[]>({
    queryKey: ["sandboxes"],
    queryFn: () => sandboxes.list(),
    refetchInterval: (query) =>
      query.state.error ? false : 10_000,
    retry: false,
  });

  const destroyMutation = useMutation({
    mutationFn: (sandboxId: string) => sandboxes.destroy(sandboxId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sandboxes"] });
      toast.success("Sandbox destroyed");
    },
    onError: () => toast.error("Failed to destroy sandbox"),
  });

  if (sandboxList.length === 0) {
    return (
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Container className="h-3.5 w-3.5" />
        <span>No active sandboxes</span>
      </div>
    );
  }

  const sandbox = sandboxList[0];
  const dotColor = statusColors[sandbox.status] || "bg-gray-500";

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors">
          <span className={`h-2 w-2 rounded-full ${dotColor}`} />
          <Container className="h-3.5 w-3.5" />
          <span>{sandbox.status}</span>
          {sandboxList.length > 1 && (
            <span className="text-muted-foreground/60">
              +{sandboxList.length - 1}
            </span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">
          <code>{sandbox.id.slice(0, 12)}</code>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onClick={() => destroyMutation.mutate(sandbox.id)}
          disabled={destroyMutation.isPending}
        >
          <Square className="h-3.5 w-3.5 mr-2" />
          Destroy Sandbox
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
