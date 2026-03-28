import { createFileRoute } from "@tanstack/react-router";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { sandboxes, type SandboxInfo } from "@/lib/api/sandboxes";
import { Container, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { toast } from "sonner";

export const Route = createFileRoute("/settings/sandboxes")({
  component: SandboxesSettings,
});

function SandboxesSettings() {
  const queryClient = useQueryClient();

  const { data: items = [], isLoading } = useQuery<SandboxInfo[]>({
    queryKey: ["sandboxes"],
    queryFn: () => sandboxes.list(),
    refetchInterval: 10_000,
  });

  const destroyMutation = useMutation({
    mutationFn: (sandboxId: string) => sandboxes.destroy(sandboxId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sandboxes"] });
      toast.success("Sandbox destroyed");
    },
    onError: () => toast.error("Failed to destroy sandbox"),
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Sandboxes</h2>
        <p className="text-muted-foreground">
          Active sandbox containers across all projects.
        </p>
      </div>

      {isLoading ? (
        <p className="text-sm text-muted-foreground">Loading...</p>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center gap-2 py-12 text-muted-foreground">
          <Container className="h-8 w-8" />
          <p className="text-sm">No active sandboxes</p>
        </div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Sandbox</TableHead>
              <TableHead>Project</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Created</TableHead>
              <TableHead className="w-20" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {items.map((s) => (
              <TableRow key={s.id}>
                <TableCell className="font-mono text-xs">
                  {s.id.slice(0, 12)}
                </TableCell>
                <TableCell className="text-sm">{s.project_id || "\u2014"}</TableCell>
                <TableCell>
                  <Badge
                    variant={s.status === "running" ? "default" : "secondary"}
                  >
                    {s.status}
                  </Badge>
                </TableCell>
                <TableCell className="text-sm">
                  {new Date(s.created_at).toLocaleString()}
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => destroyMutation.mutate(s.id)}
                    disabled={destroyMutation.isPending}
                  >
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
