import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { github, projectSettings } from "@/lib/api";
import type { GitHubRepo } from "@/lib/api/github";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { toast } from "sonner";
import { GitBranch, ExternalLink, Unlink } from "lucide-react";

export const Route = createFileRoute(
  "/project/$projectId/settings/github",
)({
  component: GitHubSettings,
});

function GitHubSettings() {
  const { projectId } = Route.useParams();
  const queryClient = useQueryClient();

  const { data: status } = useQuery({
    queryKey: ["github", "status"],
    queryFn: () => github.status(),
  });

  const { data: linkedRepo, isLoading: loadingRepo } = useQuery({
    queryKey: ["project-settings", "github", projectId],
    queryFn: () => projectSettings.getLinkedRepo(projectId),
  });

  const { data: repos = [] } = useQuery({
    queryKey: ["github", "repos"],
    queryFn: () => github.repos({ per_page: 100 }),
    enabled: !!status?.connected && !linkedRepo,
  });

  const [selectedRepo, setSelectedRepo] = useState("");
  const [autoPush, setAutoPush] = useState(false);

  const linkMutation = useMutation({
    mutationFn: () =>
      projectSettings.linkRepo(projectId, {
        repo_full_name: selectedRepo,
        auto_push: autoPush,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["project-settings", "github", projectId],
      });
      toast.success("Repository linked");
    },
    onError: () => toast.error("Failed to link repository"),
  });

  const unlinkMutation = useMutation({
    mutationFn: () => projectSettings.unlinkRepo(projectId),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: ["project-settings", "github", projectId],
      });
      toast.success("Repository unlinked");
    },
    onError: () => toast.error("Failed to unlink repository"),
  });

  if (loadingRepo) {
    return (
      <div className="max-w-2xl space-y-6">
        <div>
          <h2 className="text-lg font-semibold">GitHub</h2>
          <p className="mt-0.5 text-sm text-muted-foreground">Loading...</p>
        </div>
        <div className="h-20 w-full animate-pulse rounded-md bg-muted" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl space-y-10">
      <div>
        <h2 className="text-lg font-semibold">GitHub</h2>
        <p className="mt-0.5 text-sm text-muted-foreground">
          Link a repository to set it as the remote origin for this project.
        </p>
      </div>

      {!status?.connected ? (
        <div className="rounded-lg border border-dashed p-8 text-center space-y-3">
          <GitBranch className="mx-auto h-8 w-8 text-muted-foreground" />
          <div>
            <p className="text-sm font-medium">GitHub not connected</p>
            <p className="text-sm text-muted-foreground mt-1">
              Connect your GitHub account to link repositories.
            </p>
          </div>
          <Button
            variant="outline"
            onClick={() => {
              window.location.href = "/api/github/connect";
            }}
          >
            Connect GitHub
          </Button>
        </div>
      ) : linkedRepo ? (
        <section className="space-y-5">
          <div>
            <h3 className="text-sm font-medium">Linked repository</h3>
          </div>
          <div className="rounded-lg border p-4 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium text-sm">
                  {linkedRepo.repo_full_name}
                </span>
              </div>
              <a
                href={linkedRepo.repo_url.replace(".git", "")}
                target="_blank"
                rel="noopener noreferrer"
                className="text-muted-foreground hover:text-foreground"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span>Branch: {linkedRepo.default_branch}</span>
              <span>Auto-push: {linkedRepo.auto_push ? "On" : "Off"}</span>
              <span>
                Linked: {new Date(linkedRepo.linked_at).toLocaleDateString()}
              </span>
            </div>
          </div>
          <Button
            variant="outline"
            size="sm"
            className="text-destructive"
            onClick={() => unlinkMutation.mutate()}
            disabled={unlinkMutation.isPending}
          >
            <Unlink className="mr-1 h-3.5 w-3.5" />
            Unlink repository
          </Button>
        </section>
      ) : (
        <section className="space-y-5">
          <div>
            <h3 className="text-sm font-medium">Link a repository</h3>
            <p className="mt-0.5 text-sm text-muted-foreground">
              Connected as <strong>{status.github_username}</strong>
            </p>
          </div>
          <div className="space-y-2">
            <Label>Repository</Label>
            <Select value={selectedRepo} onValueChange={setSelectedRepo}>
              <SelectTrigger>
                <SelectValue placeholder="Select a repository..." />
              </SelectTrigger>
              <SelectContent>
                {repos.map((r: GitHubRepo) => (
                  <SelectItem key={r.full_name} value={r.full_name}>
                    {r.full_name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <div className="flex items-center gap-2">
            <Switch
              checked={autoPush}
              onCheckedChange={setAutoPush}
              id="auto-push"
            />
            <Label htmlFor="auto-push" className="text-sm">
              Auto-push completed feature branches
            </Label>
          </div>
          <div className="flex justify-end">
            <Button
              onClick={() => linkMutation.mutate()}
              disabled={!selectedRepo || linkMutation.isPending}
            >
              {linkMutation.isPending ? "Linking..." : "Link repository"}
            </Button>
          </div>
        </section>
      )}
    </div>
  );
}
