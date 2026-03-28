/**
 * Settings layout route — shares the same full-width + DockBar pattern as project layout.
 *
 * Uses stored projectId from zustand since settings routes are not project-scoped.
 * Keeps the settings sidebar nav for navigating between settings pages.
 */

import {
  createFileRoute,
  Outlet,
  Link,
  useRouterState,
} from "@tanstack/react-router";
import { useState, useEffect } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { Toaster } from "@/components/ui/sonner";
import { DockBar } from "@/components/DockBar";
import { CommandPalette } from "@/components/CommandPalette";
import { RunModal } from "@/components/RunModal";
import { useProjectStore } from "@/stores/project";
import { cn } from "@/lib/utils";
import { User, Building2, Container } from "lucide-react";
import { toast } from "sonner";
import type { RunStartResponse } from "@/types/api";
import { useRouter } from "@tanstack/react-router";

export const Route = createFileRoute("/settings")({
  component: SettingsLayout,
});

const navGroups = [
  {
    label: "Account",
    items: [{ to: "/settings/profile", label: "Profile", icon: User }],
  },
  {
    label: "Workspace",
    items: [
      { to: "/settings/workspace", label: "General", icon: Building2 },
    ],
  },
  {
    label: "Developer",
    items: [
      { to: "/settings/sandboxes", label: "Sandboxes", icon: Container },
    ],
  },
];

const allNavItems = navGroups.flatMap((g) => g.items);

function SettingsLayout() {
  const currentPath = useRouterState({ select: (s) => s.location.pathname });
  const router = useRouter();
  const projectId = useProjectStore((s) => s.currentProjectId) ?? "";
  const [runModalOpen, setRunModalOpen] = useState(false);
  const [commandOpen, setCommandOpen] = useState(false);

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

  return (
    <AuthGuard>
      <div className="flex h-screen w-full flex-col">
        <div className="flex-1 overflow-auto p-4 pb-20 md:p-6 md:pb-20">
          <div className="mx-auto max-w-6xl">
            {/* Header */}
            <div className="mb-8">
              <h1 className="text-lg font-semibold">Settings</h1>
            </div>

            {/* Mobile nav */}
            <div className="mb-6 md:hidden">
              <nav className="-mb-px flex gap-1 overflow-x-auto border-b">
                {allNavItems.map((item) => {
                  const active =
                    currentPath === item.to ||
                    currentPath.startsWith(item.to + "/");
                  return (
                    <Link
                      key={item.to}
                      to={item.to}
                      className={cn(
                        "inline-flex items-center gap-1.5 whitespace-nowrap border-b-2 px-3 py-2.5 text-sm transition-colors",
                        active
                          ? "border-primary font-medium text-foreground"
                          : "border-transparent text-muted-foreground hover:border-border hover:text-foreground",
                      )}
                    >
                      <item.icon className="h-3.5 w-3.5" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>

            {/* Two-column layout */}
            <div className="flex gap-8 md:gap-12">
              {/* Sidebar nav */}
              <nav className="hidden w-48 shrink-0 md:block">
                <div className="sticky top-6 space-y-6">
                  {navGroups.map((group) => (
                    <div key={group.label}>
                      <p className="mb-1 px-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
                        {group.label}
                      </p>
                      <div className="space-y-0.5">
                        {group.items.map((item) => {
                          const active =
                            currentPath === item.to ||
                            currentPath.startsWith(item.to + "/");
                          return (
                            <Link
                              key={item.to}
                              to={item.to}
                              className={cn(
                                "flex items-center gap-2 rounded-md px-2 py-1.5 text-sm transition-colors",
                                active
                                  ? "bg-accent font-medium text-foreground"
                                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
                              )}
                            >
                              <item.icon className="h-4 w-4" />
                              {item.label}
                            </Link>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </nav>

              {/* Content */}
              <div className="min-w-0 flex-1">
                <Outlet />
              </div>
            </div>
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
