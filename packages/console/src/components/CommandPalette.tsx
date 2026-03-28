import { useCallback } from "react";
import { useRouter, useParams } from "@tanstack/react-router";
import { useFeatures, useSessions } from "@/hooks/queries";
import { useUIStore } from "@/stores/ui";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
  CommandShortcut,
} from "@/components/ui/command";
import {
  LayoutDashboard,
  Layers,
  CheckSquare,
  List,
  Workflow,
  Settings,
  Play,
  Sun,
  Moon,
  Monitor,
} from "lucide-react";

interface CommandPaletteProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onOpenRunModal: () => void;
}

export function CommandPalette({ open, onOpenChange, onOpenRunModal }: CommandPaletteProps) {
  const router = useRouter();
  const params = useParams({ strict: false }) as Record<string, string | undefined>;
  const projectId = params.projectId;
  const { setTheme } = useUIStore();

  const { data: features } = useFeatures(undefined, projectId);
  const { data: sessions } = useSessions(undefined, projectId);

  const navigate = useCallback(
    (to: string) => {
      onOpenChange(false);
      router.navigate({ to });
    },
    [router, onOpenChange]
  );

  const pages = projectId
    ? [
        { label: "Factory Home", icon: LayoutDashboard, path: `/project/${projectId}` },
        { label: "Features", icon: CheckSquare, path: `/project/${projectId}/features` },
        { label: "Epics", icon: Layers, path: `/project/${projectId}/epics` },
        { label: "Sessions", icon: List, path: `/project/${projectId}/sessions` },
        { label: "Workflows", icon: Workflow, path: `/project/${projectId}/workflows` },
        { label: "Settings", icon: Settings, path: "/settings" },
      ]
    : [{ label: "Settings", icon: Settings, path: "/settings" }];

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Type a command or search..." />
      <CommandList>
        <CommandEmpty>No results found.</CommandEmpty>

        {/* Actions */}
        <CommandGroup heading="Actions">
          <CommandItem
            onSelect={() => {
              onOpenChange(false);
              onOpenRunModal();
            }}
          >
            <Play className="mr-2 h-4 w-4" />
            Run workflow
            <CommandShortcut>Enter</CommandShortcut>
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* Navigation */}
        <CommandGroup heading="Navigation">
          {pages.map((page) => (
            <CommandItem key={page.path} onSelect={() => navigate(page.path)}>
              <page.icon className="mr-2 h-4 w-4" />
              {page.label}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />

        {/* Theme */}
        <CommandGroup heading="Theme">
          <CommandItem onSelect={() => { setTheme("light"); onOpenChange(false); }}>
            <Sun className="mr-2 h-4 w-4" />
            Light mode
          </CommandItem>
          <CommandItem onSelect={() => { setTheme("dark"); onOpenChange(false); }}>
            <Moon className="mr-2 h-4 w-4" />
            Dark mode
          </CommandItem>
          <CommandItem onSelect={() => { setTheme("system"); onOpenChange(false); }}>
            <Monitor className="mr-2 h-4 w-4" />
            System theme
          </CommandItem>
        </CommandGroup>

        {/* Recent features */}
        {features && features.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Features">
              {features.slice(0, 8).map((f) => (
                <CommandItem
                  key={f.id}
                  onSelect={() => navigate(`/project/${projectId}/features`)}
                >
                  <CheckSquare className="mr-2 h-4 w-4" />
                  <span className="truncate">{f.title}</span>
                  <CommandShortcut>{f.status}</CommandShortcut>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}

        {/* Recent sessions */}
        {sessions && sessions.length > 0 && (
          <>
            <CommandSeparator />
            <CommandGroup heading="Sessions">
              {sessions.slice(0, 5).map((s) => (
                <CommandItem
                  key={s.id}
                  onSelect={() =>
                    navigate(`/project/${projectId}/sessions/${s.id}`)
                  }
                >
                  <List className="mr-2 h-4 w-4" />
                  <span className="truncate">{String(s.workflow_id)}: {String(s.feature_id || s.id)}</span>
                  <CommandShortcut>{String(s.status ?? "")}</CommandShortcut>
                </CommandItem>
              ))}
            </CommandGroup>
          </>
        )}
      </CommandList>
    </CommandDialog>
  );
}
