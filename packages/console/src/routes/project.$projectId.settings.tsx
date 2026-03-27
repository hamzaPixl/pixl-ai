import {
  createFileRoute,
  Outlet,
  Link,
  useRouterState,
} from "@tanstack/react-router";
import { cn } from "@/lib/utils";
import { Settings2, Variable, GitBranch, Globe } from "lucide-react";

export const Route = createFileRoute("/project/$projectId/settings")({
  component: ProjectSettingsLayout,
});

function ProjectSettingsLayout() {
  const { projectId } = Route.useParams();
  const currentPath = useRouterState({
    select: (s) => s.location.pathname,
  });

  const navItems = [
    {
      to: `/project/${projectId}/settings/general`,
      label: "General",
      icon: Settings2,
    },
    {
      to: `/project/${projectId}/settings/environment`,
      label: "Environment",
      icon: Variable,
    },
    {
      to: `/project/${projectId}/settings/github`,
      label: "GitHub",
      icon: GitBranch,
    },
    {
      to: `/project/${projectId}/settings/dns`,
      label: "DNS",
      icon: Globe,
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Project Settings</h1>
      </div>

      {/* Mobile nav */}
      <div className="md:hidden">
        <nav className="-mb-px flex gap-1 overflow-x-auto border-b">
          {navItems.map((item) => {
            const active =
              currentPath === item.to || currentPath.startsWith(item.to + "/");
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
          <div className="sticky top-6 space-y-0.5">
            {navItems.map((item) => {
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
        </nav>

        {/* Content */}
        <div className="min-w-0 flex-1">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
