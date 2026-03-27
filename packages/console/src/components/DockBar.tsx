/**
 * Unified floating dock bar with animated icons, highlight color accents,
 * and expandable rows.
 *
 * Design system:
 *   - Hover: icons turn highlight (red) color
 *   - Active: highlight bottom dot indicator + subtle highlight bg tint
 *   - Run button: highlight bg with pulse ring on hover
 *   - Expanded rows: slide-up entrance animation
 *   - Project avatar: highlight border on active project
 *   - AI Lab toggle: highlight sparkle when open
 */

import { useState, useEffect, useCallback } from "react";
import { useRouterState, useRouter } from "@tanstack/react-router";
import { Link } from "@tanstack/react-router";
import { useProjectStore } from "@/stores/project";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useGateInbox } from "@/hooks/queries";
import { useAuthStore } from "@/stores/auth";
import { useUIStore } from "@/stores/ui";

import {
  LogOut,
  Sun,
  Moon,
  Monitor,
  Check,
  Settings,
  Workflow,
  Bot,
  FolderGit2,
  ChevronsUpDown,
  Plus,
  MoreHorizontal,
} from "lucide-react";

import { HouseIcon } from "@/components/ui/house-icon";
import { MapPinIcon } from "@/components/ui/map-pin-icon";
import { ActivityIcon } from "@/components/ui/activity-icon";
import { TrendingUpIcon } from "@/components/ui/trending-up-icon";
import { ZapIcon } from "@/components/ui/zap-icon";
import { SearchIcon } from "@/components/ui/search-icon";
import { PlayIcon } from "@/components/ui/play-icon";
import { SettingsIcon } from "@/components/ui/settings-icon";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { UserAvatar } from "@/components/user-avatar";
import { CreateProjectDialog } from "@/components/CreateProjectDialog";
import { projects, setApiProjectContext } from "@/lib/api";
import { queryKeys, projectQueryPrefix } from "@/lib/query-keys";
import type { Project } from "@/types/api";

interface DockBarProps {
  projectId: string;
  onOpenCommandPalette: () => void;
  onOpenRunModal: () => void;
}

function isRouteActive(
  currentPath: string,
  itemPath: string,
  projectId: string,
): boolean {
  if (itemPath.endsWith(`/project/${projectId}`)) {
    return (
      currentPath === `/project/${projectId}` ||
      currentPath === `/project/${projectId}/`
    );
  }
  return (
    currentPath === itemPath ||
    currentPath.startsWith(`${itemPath}/`) ||
    currentPath.startsWith(`${itemPath}?`)
  );
}

export function DockBar({
  projectId,
  onOpenCommandPalette,
  onOpenRunModal,
}: DockBarProps) {
  const { user, logout } = useAuthStore();
  const { theme, setTheme } = useUIStore();
  const router = useRouter();
  const queryClient = useQueryClient();
  const currentPath = useRouterState({ select: (s) => s.location.pathname });
  const storedProjectId = useProjectStore((s) => s.currentProjectId);
  const activeProjectId = projectId || storedProjectId || "";
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [labOpen, setLabOpen] = useState(false);
  const [projectsOpen, setProjectsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

  const closeAllRows = useCallback(() => {
    setLabOpen(false);
    setProjectsOpen(false);
    setProfileOpen(false);
    setMoreOpen(false);
  }, []);

  // Close expanded rows on route change
  useEffect(() => {
    closeAllRows();
  }, [currentPath, closeAllRows]);

  const { data: projectList } = useQuery({
    queryKey: queryKeys.projects.list(),
    queryFn: () => projects.list(),
    staleTime: 60000,
  });

  const { data: gateInbox } = useGateInbox(activeProjectId || undefined);
  const gateCount = gateInbox?.gates?.length ?? 0;

  const currentProject = projectList?.find(
    (p) => p.project_id === activeProjectId,
  );

  const handleSelectProject = (project: Project) => {
    if (activeProjectId !== project.project_id) {
      if (activeProjectId) {
        queryClient.invalidateQueries({
          queryKey: projectQueryPrefix(activeProjectId),
        });
      }
      setApiProjectContext(project.project_id);
      router.navigate({
        to: "/project/$projectId",
        params: { projectId: project.project_id },
      });
    }
    setProjectsOpen(false);
  };

  const fullName = [user?.first_name, user?.last_name]
    .filter(Boolean)
    .join(" ");

  const labActive =
    isRouteActive(
      currentPath,
      `/project/${activeProjectId}/workflows`,
      activeProjectId,
    ) ||
    isRouteActive(
      currentPath,
      `/project/${activeProjectId}/agents`,
      activeProjectId,
    );

  return (
    <TooltipProvider delayDuration={300}>
      <div className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 flex flex-col items-center gap-2">
        {/* ── Profile expanded row ── */}
        {profileOpen && (
          <div className="dock-row-enter flex items-center gap-1 rounded-2xl border border-highlight/20 bg-muted/60 px-3 py-1.5 shadow-lg shadow-highlight/5 backdrop-blur-md max-w-[calc(100vw-2rem)] overflow-x-auto">
            <div className="flex items-center gap-2 px-2 py-1">
              <UserAvatar
                firstName={user?.first_name}
                lastName={user?.last_name}
                size="sm"
              />
              <div className="text-left text-sm leading-tight">
                <span className="font-semibold">{fullName || "User"}</span>
                <span className="block text-xs text-muted-foreground">
                  {user?.email}
                </span>
              </div>
            </div>

            <Link
              to="/settings/profile"
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-muted-foreground transition-all duration-200 hover:bg-highlight/10 hover:text-highlight"
            >
              <Settings className="h-4 w-4" />
              Settings
            </Link>

            {/* Theme toggle */}
            <button
              onClick={() =>
                setTheme(
                  theme === "dark"
                    ? "light"
                    : theme === "light"
                      ? "system"
                      : "dark",
                )
              }
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-muted-foreground transition-all duration-200 hover:bg-highlight/10 hover:text-highlight"
            >
              {theme === "dark" ? (
                <Moon className="h-4 w-4" />
              ) : theme === "light" ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Monitor className="h-4 w-4" />
              )}
              {theme === "dark" ? "Dark" : theme === "light" ? "Light" : "System"}
            </button>

            <button
              onClick={logout}
              className="flex items-center gap-2 rounded-full border border-destructive/30 bg-destructive/10 px-4 py-1.5 text-sm font-medium text-destructive transition-all duration-200 hover:bg-destructive hover:text-destructive-foreground hover:border-destructive hover:shadow-md"
            >
              <LogOut className="h-4 w-4" />
              Sign out
            </button>
          </div>
        )}

        {/* ── Projects expanded row ── */}
        {projectsOpen && (
          <div className="dock-row-enter flex items-center gap-1 rounded-2xl border border-highlight/20 bg-muted/60 px-3 py-1.5 shadow-lg shadow-highlight/5 backdrop-blur-md max-w-[calc(100vw-2rem)] overflow-x-auto">
            {projectList && projectList.length === 0 ? (
              <span className="px-3 py-1.5 text-sm text-muted-foreground">
                No projects
              </span>
            ) : (
              (projectList ?? []).map((project) => {
                const isActive = project.project_id === activeProjectId;
                return (
                  <button
                    key={project.project_id}
                    onClick={() => handleSelectProject(project)}
                    className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-all duration-200 ${
                      isActive
                        ? "bg-highlight/10 font-medium text-highlight"
                        : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
                    }`}
                  >
                    <div
                      className={`flex size-5 items-center justify-center rounded text-[9px] font-semibold ${
                        isActive
                          ? "bg-highlight text-highlight-foreground"
                          : "bg-primary text-primary-foreground"
                      }`}
                    >
                      {project.project_name.charAt(0).toUpperCase()}
                    </div>
                    <span className="max-w-[120px] truncate">
                      {project.project_name}
                    </span>
                    {isActive && (
                      <Check className="size-3 shrink-0 text-highlight" />
                    )}
                  </button>
                );
              })
            )}
            <button
              onClick={() => {
                setProjectsOpen(false);
                setCreateDialogOpen(true);
              }}
              className="flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm text-muted-foreground transition-all duration-200 hover:bg-highlight/10 hover:text-highlight"
            >
              <div className="flex size-5 items-center justify-center rounded border border-dashed border-muted-foreground/40 transition-colors group-hover:border-highlight">
                <Plus className="size-3" />
              </div>
              New
            </button>
          </div>
        )}

        {/* ── AI Lab expanded row ── */}
        {labOpen && activeProjectId && (
          <div className="dock-row-enter flex items-center gap-1 rounded-2xl border border-highlight/20 bg-muted/60 px-3 py-1.5 shadow-lg shadow-highlight/5 backdrop-blur-md max-w-[calc(100vw-2rem)] overflow-x-auto">
            <Link
              to={`/project/${activeProjectId}/workflows` as string}
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-all duration-200 ${
                isRouteActive(
                  currentPath,
                  `/project/${activeProjectId}/workflows`,
                  activeProjectId,
                )
                  ? "bg-highlight/10 font-medium text-highlight"
                  : "text-muted-foreground hover:bg-highlight/10 hover:text-highlight"
              }`}
            >
              <Workflow className="h-4 w-4" />
              Workflows
            </Link>
            <Link
              to={`/project/${activeProjectId}/agents` as string}
              className={`flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm transition-all duration-200 ${
                isRouteActive(
                  currentPath,
                  `/project/${activeProjectId}/agents`,
                  activeProjectId,
                )
                  ? "bg-highlight/10 font-medium text-highlight"
                  : "text-muted-foreground hover:bg-highlight/10 hover:text-highlight"
              }`}
            >
              <Bot className="h-4 w-4" />
              Agents
            </Link>
          </div>
        )}

        {/* ── Mobile "More" expanded row ── */}
        {moreOpen && activeProjectId && (
          <div className="dock-row-enter sm:hidden flex items-center gap-1 rounded-2xl border border-highlight/20 bg-muted/60 px-2 py-1.5 shadow-lg shadow-highlight/5 backdrop-blur-md max-w-[calc(100vw-2rem)] overflow-x-auto">
            <Tooltip>
              <TooltipTrigger asChild>
                <Link
                  to={`/project/${activeProjectId}/insights` as string}
                  className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-200 ${
                    isRouteActive(currentPath, `/project/${activeProjectId}/insights`, activeProjectId)
                      ? "bg-highlight/10 text-highlight"
                      : "text-muted-foreground hover:bg-highlight/10 hover:text-highlight"
                  }`}
                >
                  <TrendingUpIcon size={18} duration={1.5} className="dock-icon" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="top" sideOffset={8}>Insights</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={() => {
                    setMoreOpen(false);
                    onOpenCommandPalette();
                  }}
                  className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-all duration-200 hover:bg-highlight/10 hover:text-highlight"
                >
                  <SearchIcon size={18} duration={1.5} className="dock-icon" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" sideOffset={8}>Search</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Link
                  to={`/project/${activeProjectId}/settings` as string}
                  className="flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-all duration-200 hover:bg-highlight/10 hover:text-highlight"
                >
                  <SettingsIcon size={18} duration={1.5} className="dock-icon" />
                </Link>
              </TooltipTrigger>
              <TooltipContent side="top" sideOffset={8}>Settings</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={() => {
                    setMoreOpen(false);
                    setLabOpen((v) => !v);
                  }}
                  className={`flex h-9 w-9 items-center justify-center rounded-lg transition-all duration-200 ${
                    labActive
                      ? "bg-highlight/10 text-highlight"
                      : "text-muted-foreground hover:bg-highlight/10 hover:text-highlight"
                  }`}
                >
                  <ZapIcon size={18} duration={1.5} className="dock-icon" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" sideOffset={8}>AI Lab</TooltipContent>
            </Tooltip>
          </div>
        )}

        {/* ── Main Dock ── */}
        <div className="flex items-center rounded-2xl border shadow-lg backdrop-blur-md max-w-[calc(100vw-2rem)]">
          {/* ── Nav Section (left) ── */}
          <div className="flex items-center gap-0.5 sm:gap-1 rounded-l-2xl bg-muted/60 px-2 sm:px-3 py-2">
            {/* Home */}
            <DockAnimatedLink
              tooltip="Home"
              to={`/project/${activeProjectId}`}
            >
              <HouseIcon size={20} duration={1.5} className="dock-icon" />
            </DockAnimatedLink>

            {/* Project Switcher */}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={() => {
                    setProjectsOpen((v) => !v);
                    if (!projectsOpen) { setLabOpen(false); setProfileOpen(false); setMoreOpen(false); }
                  }}
                  className={`flex h-10 items-center gap-1.5 rounded-xl px-2.5 transition-all duration-200 hover:bg-accent ${
                    projectsOpen ? "bg-accent text-accent-foreground" : ""
                  }`}
                >
                  <div
                    className={`flex size-7 items-center justify-center rounded-md transition-all duration-200 ${
                      projectsOpen
                        ? "bg-highlight text-highlight-foreground ring-2 ring-highlight/30"
                        : "bg-primary text-primary-foreground"
                    }`}
                  >
                    {currentProject ? (
                      <span className="text-[10px] font-semibold">
                        {currentProject.project_name.charAt(0).toUpperCase()}
                      </span>
                    ) : (
                      <FolderGit2 className="size-3" />
                    )}
                  </div>
                  <ChevronsUpDown className="size-3 text-muted-foreground" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" sideOffset={8}>
                {currentProject?.project_name ?? "Switch Project"}
              </TooltipContent>
            </Tooltip>

            {/* Roadmap */}
            {activeProjectId && (
              <DockNavLink
                tooltip="Roadmap"
                to={`/project/${activeProjectId}/roadmap`}
                active={isRouteActive(
                  currentPath,
                  `/project/${activeProjectId}/roadmap`,
                  activeProjectId,
                )}
              >
                <MapPinIcon size={20} duration={1.5} className="dock-icon" />
                <span className="hidden md:inline">Roadmap</span>
              </DockNavLink>
            )}

            {/* Sessions */}
            {activeProjectId && (
              <DockNavLink
                tooltip="Sessions"
                to={`/project/${activeProjectId}/sessions`}
                active={isRouteActive(
                  currentPath,
                  `/project/${activeProjectId}/sessions`,
                  activeProjectId,
                )}
                badge={gateCount > 0 ? gateCount : undefined}
              >
                <ActivityIcon size={20} duration={1.5} className="dock-icon" />
                <span className="hidden md:inline">Sessions</span>
              </DockNavLink>
            )}

            {/* Insights — desktop only */}
            {activeProjectId && (
              <div className="hidden sm:flex">
                <DockNavLink
                  tooltip="Insights"
                  to={`/project/${activeProjectId}/insights`}
                  active={isRouteActive(
                    currentPath,
                    `/project/${activeProjectId}/insights`,
                    activeProjectId,
                  )}
                  iconOnly
                >
                  <TrendingUpIcon size={20} duration={1.5} className="dock-icon" />
                </DockNavLink>
              </div>
            )}

            {/* AI Lab toggle — desktop only */}
            {activeProjectId && (
              <div className="hidden sm:flex">
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => {
                      setLabOpen((v) => !v);
                      if (!labOpen) { setProjectsOpen(false); setProfileOpen(false); }
                    }}
                    className={`dock-item-hover relative flex h-10 w-10 items-center justify-center rounded-lg transition-all duration-200 ${
                      labOpen || labActive
                        ? "text-highlight dock-active-dot"
                        : "text-muted-foreground hover:text-highlight"
                    }`}
                  >
                    <ZapIcon size={20} duration={1.5} className="dock-icon" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top" sideOffset={8}>
                  AI Lab
                </TooltipContent>
              </Tooltip>
              </div>
            )}
          </div>

          {/* ── Actions Section (right) ── */}
          <div className="flex items-center gap-0.5 sm:gap-1 rounded-r-2xl bg-background/80 px-2 sm:px-3 py-2">
            {/* Search — desktop only */}
            <div className="hidden sm:flex">
              <DockAnimatedButton
                tooltip="Search (⌘K)"
                onClick={onOpenCommandPalette}
              >
                <SearchIcon size={20} duration={1.5} className="dock-icon" />
              </DockAnimatedButton>
            </div>

            {/* Run — always visible */}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={onOpenRunModal}
                  className="dock-run-btn flex h-10 w-10 items-center justify-center rounded-xl transition-all duration-200 hover:bg-highlight hover:text-highlight-foreground"
                >
                  <PlayIcon size={20} duration={1.5} />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" sideOffset={8}>
                Run Workflow
              </TooltipContent>
            </Tooltip>

            {/* More button — mobile only */}
            {activeProjectId && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    onClick={() => {
                      setMoreOpen((v) => !v);
                      if (!moreOpen) { setProjectsOpen(false); setLabOpen(false); setProfileOpen(false); }
                    }}
                    className={`sm:hidden dock-item-hover flex h-10 w-10 items-center justify-center rounded-xl transition-all duration-200 ${
                      moreOpen ? "text-highlight" : "text-muted-foreground"
                    }`}
                  >
                    <MoreHorizontal className="h-5 w-5" />
                  </button>
                </TooltipTrigger>
                <TooltipContent side="top" sideOffset={8}>
                  More
                </TooltipContent>
              </Tooltip>
            )}

            {/* Project Settings — desktop only */}
            <div className="hidden sm:flex">
              <DockAnimatedLink
                tooltip="Project Settings"
                to={`/project/${activeProjectId}/settings`}
              >
                <SettingsIcon size={20} duration={1.5} className="dock-icon" />
              </DockAnimatedLink>
            </div>

            {/* Profile toggle — always visible */}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={() => {
                    setProfileOpen((v) => !v);
                    if (!profileOpen) {
                      setLabOpen(false);
                      setProjectsOpen(false);
                      setMoreOpen(false);
                    }
                  }}
                  className={`flex h-10 w-10 items-center justify-center rounded-xl transition-all duration-200 ${
                    profileOpen
                      ? "ring-2 ring-highlight/40"
                      : "hover:ring-2 hover:ring-highlight/30"
                  }`}
                >
                  <UserAvatar
                    firstName={user?.first_name}
                    lastName={user?.last_name}
                    size="sm"
                  />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" sideOffset={8}>
                {fullName || "Profile"}
              </TooltipContent>
            </Tooltip>
          </div>
        </div>
      </div>

      <CreateProjectDialog
        open={createDialogOpen}
        onOpenChange={setCreateDialogOpen}
      />
    </TooltipProvider>
  );
}

/* ── Shared dock sub-components ── */

function DockAnimatedButton({
  tooltip,
  onClick,
  children,
}: {
  tooltip: string;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          onClick={onClick}
          className="dock-item-hover flex h-10 w-10 items-center justify-center rounded-xl transition-all duration-200"
        >
          {children}
        </button>
      </TooltipTrigger>
      <TooltipContent side="top" sideOffset={8}>
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}

function DockAnimatedLink({
  tooltip,
  to,
  children,
}: {
  tooltip: string;
  to: string;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Link
          to={to}
          className="dock-item-hover flex h-10 w-10 items-center justify-center rounded-xl transition-all duration-200"
        >
          {children}
        </Link>
      </TooltipTrigger>
      <TooltipContent side="top" sideOffset={8}>
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}

function DockNavLink({
  tooltip,
  to,
  active,
  badge,
  iconOnly,
  children,
}: {
  tooltip: string;
  to: string;
  active: boolean;
  badge?: number;
  iconOnly?: boolean;
  children: React.ReactNode;
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Link
          to={to}
          aria-label={tooltip}
          className={`dock-item-hover relative flex items-center gap-1.5 rounded-lg text-sm transition-all duration-200 ${
            iconOnly ? "h-10 w-10 justify-center" : "h-10 px-3"
          } ${
            active
              ? "text-highlight dock-active-dot font-medium"
              : "text-muted-foreground"
          }`}
        >
          {children}
          {badge != null && badge > 0 && (
            <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-highlight px-1 text-[10px] font-medium text-highlight-foreground">
              {badge}
            </span>
          )}
        </Link>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={8}
        className={iconOnly ? "" : "md:hidden"}
      >
        {tooltip}
      </TooltipContent>
    </Tooltip>
  );
}
