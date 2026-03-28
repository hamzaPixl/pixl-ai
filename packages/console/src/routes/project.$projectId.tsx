/**
 * Project layout route — full-width content with unified floating DockBar.
 *
 * This route:
 * - Sets the API context deterministically in beforeLoad when projectId is available
 * - Syncs projectId to localStorage for persistence
 * - Renders full-width content + floating DockBar + child routes via Outlet
 * - Handles Cmd+K for CommandPalette
 */

import { createFileRoute, useRouter, Outlet } from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { useEventStream } from "@/hooks/use-event-stream";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { Toaster } from "@/components/ui/sonner";
import { toast } from "sonner";
import { RunModal } from "@/components/RunModal";
import { CommandPalette } from "@/components/CommandPalette";
import { AuthGuard } from "@/components/AuthGuard";
import { DockBar } from "@/components/DockBar";
import { SandboxStatus } from "@/components/sandbox-status";
import { setApiProjectContext } from "@/lib/api";
import { useProjectStore } from "@/stores/project";
import type { RunStartResponse } from "@/types/api";

export const Route = createFileRoute("/project/$projectId")({
  beforeLoad: ({ params }) => {
    if (params.projectId) {
      setApiProjectContext(params.projectId);
    }
  },
  component: ProjectLayout,
});

function ProjectLayout() {
  const router = useRouter();
  const { projectId } = Route.useParams();
  const [runModalOpen, setRunModalOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);

  useEffect(() => {
    if (projectId) {
      useProjectStore.setState({ currentProjectId: projectId });
    }
  }, [projectId]);

  useEventStream({ projectId });

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

    router.navigate({
      to: "/project/$projectId/sessions/$sessionId" as const,
      params: { projectId, sessionId: result.session_id },
    });
  };

  return (
    <AuthGuard>
      <div className="flex h-screen w-full flex-col">
        <div className="flex items-center justify-end px-4 pt-2 md:px-6">
          <SandboxStatus />
        </div>
        <div className="flex-1 overflow-auto p-4 pb-20 md:p-6 md:pb-20">
          <div className="mx-auto max-w-6xl">
            <ErrorBoundary>
              <Outlet />
            </ErrorBoundary>
          </div>
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
    </AuthGuard>
  );
}
