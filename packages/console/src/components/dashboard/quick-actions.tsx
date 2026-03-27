/**
 * QuickActions — inline text links, not button cards.
 */

import { useRouter } from "@tanstack/react-router";

interface QuickActionsProps {
  projectId: string;
  hasPendingGates: boolean;
}

export function QuickActions({
  projectId,
  hasPendingGates,
}: QuickActionsProps) {
  const router = useRouter();

  return (
    <div className="flex items-center gap-3 text-xs">
      <button
        onClick={() =>
          router.navigate({
            to: "/project/$projectId/roadmap",
            params: { projectId },
          })
        }
        className="text-muted-foreground hover:text-foreground transition-colors"
      >
        Delegate
      </button>
      {hasPendingGates && (
        <button
          onClick={() =>
            router.navigate({
              to: "/project/$projectId/sessions",
              params: { projectId },
              search: { tab: "gates" },
            })
          }
          className="text-amber-600 dark:text-amber-400 hover:opacity-70 transition-opacity"
        >
          Review Gates
        </button>
      )}
      <button
        onClick={() =>
          router.navigate({
            to: "/project/$projectId/features",
            params: { projectId },
          })
        }
        className="text-muted-foreground hover:text-foreground transition-colors"
      >
        Features
      </button>
    </div>
  );
}
