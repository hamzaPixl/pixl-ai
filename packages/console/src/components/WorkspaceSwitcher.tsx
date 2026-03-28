import { useEffect, useState } from "react";
import { useAuthStore } from "@/stores/auth";
import { setApiWorkspaceContext } from "@/lib/api";
import { SidebarMenuButton, useSidebar } from "@/components/ui/sidebar";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Building2, Check, ChevronsUpDown } from "lucide-react";

interface Workspace {
  id: string;
  name: string;
  slug: string;
  role: string;
}

export function WorkspaceSwitcher() {
  const { workspaceId, setWorkspaceId } = useAuthStore();
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const { isMobile, state } = useSidebar();

  useEffect(() => {
    fetch("/api/workspaces", { credentials: "include" })
      .then((r) => r.json())
      .then((data) => {
        setWorkspaces(data.workspaces || []);
        // Auto-select first workspace if none selected
        if (!workspaceId && data.workspaces?.length > 0) {
          const first = data.workspaces[0];
          setWorkspaceId(first.id);
          setApiWorkspaceContext(first.id);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync workspace context
  useEffect(() => {
    setApiWorkspaceContext(workspaceId);
  }, [workspaceId]);

  const current = workspaces.find((w) => w.id === workspaceId);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <SidebarMenuButton
          size="lg"
          tooltip={current?.name || "Workspace"}
          className="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
        >
          <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground">
            {current ? (
              <span className="text-xs font-semibold">
                {current.name.charAt(0).toUpperCase()}
              </span>
            ) : (
              <Building2 className="size-4" />
            )}
          </div>
          <div className="grid flex-1 text-left text-sm leading-tight">
            <span className="truncate font-semibold">
              {current?.name || "Select workspace"}
            </span>
            <span className="truncate text-xs text-muted-foreground">
              {current?.role || "No workspace"}
            </span>
          </div>
          <ChevronsUpDown className="ml-auto size-4" />
        </SidebarMenuButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        className="w-[--radix-dropdown-menu-trigger-width] min-w-56 rounded-lg"
        side={isMobile ? "bottom" : state === "collapsed" ? "right" : "bottom"}
        align={state === "collapsed" ? "start" : "start"}
        sideOffset={4}
      >
        <DropdownMenuLabel className="text-xs text-muted-foreground">
          Workspaces
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {workspaces.length === 0 ? (
          <DropdownMenuItem disabled>No workspaces found</DropdownMenuItem>
        ) : (
          workspaces.map((ws) => (
            <DropdownMenuItem
              key={ws.id}
              onClick={() => {
                setWorkspaceId(ws.id);
                setApiWorkspaceContext(ws.id);
              }}
              className="gap-2 p-2"
            >
              <div className="flex size-6 items-center justify-center rounded-sm border">
                <span className="text-xs font-medium">
                  {ws.name.charAt(0).toUpperCase()}
                </span>
              </div>
              <span className="flex-1 truncate">{ws.name}</span>
              <span className="text-xs text-muted-foreground">{ws.role}</span>
              {ws.id === workspaceId && (
                <Check className="size-4 shrink-0 text-primary" />
              )}
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
