/**
 * Index route — Home page at /.
 *
 * Auto-redirects to last project if one is stored/available.
 * Otherwise shows project selection with the unified DockBar layout.
 */

import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AuthGuard } from "@/components/AuthGuard";
import { ProjectRequiredScreen } from "@/components/ProjectRequiredScreen";
import { DockBar } from "@/components/DockBar";
import { CommandPalette } from "@/components/CommandPalette";
import { RunModal } from "@/components/RunModal";
import { Toaster } from "@/components/ui/sonner";
import { projects, setApiProjectContext } from "@/lib/api";
import { queryKeys } from "@/lib/query-keys";
import { useProjectStore } from "@/stores/project";
import { useAuthStore } from "@/stores/auth";
import { toast } from "sonner";
import { useRouter } from "@tanstack/react-router";
import type { RunStartResponse } from "@/types/api";

export const Route = createFileRoute("/")({
  component: IndexComponent,
} as any);

function IndexComponent() {
  return (
    <AuthGuard>
      <IndexContent />
    </AuthGuard>
  );
}

function IndexContent() {
  const navigate = useNavigate();
  const router = useRouter();
  const [isReady, setIsReady] = useState(false);
  const [runModalOpen, setRunModalOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);
  const projectId = useProjectStore((s) => s.currentProjectId) ?? "";
  const workspaceId = useAuthStore((s) => s.workspaceId);

  const {
    data: projectList,
    isLoading,
    isError,
  } = useQuery({
    queryKey: queryKeys.projects.list(),
    queryFn: () => projects.list(),
    enabled: !!workspaceId,
  });

  useEffect(() => {
    if (isLoading || isReady || isError || !workspaceId) return;
    if (!projectList) return;

    const params = new URLSearchParams(window.location.search);
    const sessionParam = params.get("session");
    if (sessionParam) {
      sessionStorage.setItem("pendingSessionRedirect", sessionParam);
    }

    const projectParam = params.get("project");
    if (
      projectParam &&
      projectList.some((p: any) => p.project_id === projectParam)
    ) {
      setApiProjectContext(projectParam);
      navigate({
        to: "/project/$projectId",
        params: { projectId: projectParam },
        replace: true,
      });
      setIsReady(true);
      return;
    }

    const storedProjectId = localStorage.getItem(
      "pixl-project-currentProjectId",
    );
    if (
      storedProjectId &&
      projectList.some((p: any) => p.project_id === storedProjectId)
    ) {
      setApiProjectContext(storedProjectId);
      navigate({
        to: "/project/$projectId",
        params: { projectId: storedProjectId },
        replace: true,
      });
      setIsReady(true);
      return;
    }

    if (projectList.length === 1) {
      const singleProject = projectList[0];
      setApiProjectContext((singleProject as any).project_id);
      navigate({
        to: "/project/$projectId",
        params: { projectId: (singleProject as any).project_id },
        replace: true,
      });
      setIsReady(true);
      return;
    }

    setIsReady(true);
  }, [projectList, isLoading, isReady, isError, workspaceId, navigate]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandOpen(true);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const handleRunSuccess = (result: RunStartResponse) => {
    toast.success("Workflow started", {
      description: `Started ${result.entity_kind} workflow for ${result.entity_id}`,
    });
    if (projectId) {
      router.navigate({
        to: "/project/$projectId/sessions/$sessionId" as const,
        params: { projectId, sessionId: result.session_id },
      });
    }
  };

  if (!isReady || isLoading || !workspaceId) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="text-center">
          <div className="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
          <p className="text-muted-foreground">Loading Pixl Console...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="flex h-screen w-full flex-col">
        <div className="flex-1 overflow-auto pb-20">
          <ProjectRequiredScreen />
        </div>
      </div>

      <DockBar
        projectId={projectId}
        onOpenCommandPalette={() => setCommandOpen(true)}
        onOpenRunModal={() => setRunModalOpen(true)}
      />

      <CommandPalette
        open={commandOpen}
        onOpenChange={setCommandOpen}
        onOpenRunModal={() => setRunModalOpen(true)}
      />

      <RunModal
        open={runModalOpen}
        onOpenChange={setRunModalOpen}
        onSuccess={handleRunSuccess}
        projectId={projectId}
      />

      <Toaster />
    </>
  );
}
