/**
 * Full-screen component shown when no project is selected.
 *
 * Displays a project selection UI with the list of available projects.
 * This is the first screen users see after loading the console.
 */

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "@tanstack/react-router";
import { FolderGit2, Loader2, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { CreateProjectDialog } from "@/components/CreateProjectDialog";
import { projects, setApiProjectContext } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import type { Project } from "@/types/api";

export function ProjectRequiredScreen() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data: projectList, isLoading, error, refetch } = useQuery({
    queryKey: queryKeys.projects.list(),
    queryFn: () => projects.list(),
  });

  const handleDeleteProject = async (e: React.MouseEvent, project: Project) => {
    e.stopPropagation();
    if (!window.confirm(`Delete project "${project.project_name}"? This will remove all project data and cannot be undone.`)) {
      return;
    }
    try {
      await projects.delete(project.project_id);
      queryClient.invalidateQueries({ queryKey: queryKeys.projects.list() });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to delete project";
      alert(message);
    }
  };

  const handleSelectProject = (project: Project) => {
    setApiProjectContext(project.project_id);
    router.navigate({
      to: '/project/$projectId',
      params: { projectId: project.project_id },
    });
  };

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background p-8">
      <div className="max-w-2xl w-full">
        <div className="text-center mb-8">
          <FolderGit2 className="h-16 w-16 text-primary mx-auto mb-4" />
          <h1 className="text-3xl font-bold mb-2">Pixl Factory Console</h1>
          <p className="text-muted-foreground">
            Select a project to view workflows, features, and dashboards.
          </p>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            <span className="ml-2 text-muted-foreground">Loading projects...</span>
          </div>
        ) : error ? (
          <div className="text-center py-8">
            <p className="text-destructive mb-4">
              Failed to load projects. Make sure the Pixl API is running.
            </p>
            <Button variant="outline" onClick={() => refetch()}>
              Retry
            </Button>
          </div>
        ) : projectList && projectList.length === 0 ? (
          <div className="text-center">
            <Button size="lg" onClick={() => setDialogOpen(true)}>
              <Plus className="h-4 w-4" />
              Create Your First Project
            </Button>
          </div>
        ) : (
          <div className="space-y-2">
            {projectList?.map((project) => (
              <div
                key={project.project_id}
                className="relative flex items-center gap-2"
              >
                <button
                  onClick={() => handleSelectProject(project)}
                  className="flex-1 text-left p-4 rounded-lg border bg-card hover:bg-accent hover:border-primary/50 transition-colors"
                >
                  <div className="font-medium">{project.project_name}</div>
                  <div className="text-sm text-muted-foreground truncate">
                    {project.project_root || project.storage_dir}
                  </div>
                </button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="shrink-0 text-muted-foreground hover:text-destructive"
                  onClick={(e) => handleDeleteProject(e, project)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            ))}
            <div className="text-center pt-4">
              <Button variant="outline" onClick={() => setDialogOpen(true)}>
                <Plus className="h-4 w-4" />
                New Project
              </Button>
            </div>
          </div>
        )}
      </div>

      <CreateProjectDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </div>
  );
}
