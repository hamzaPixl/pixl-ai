import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, ChevronRight } from "lucide-react";
import type { BatonHistoryEntry } from "@/types/api";
import { BatonStateView } from "./BatonStateView";

export interface BatonHistoryViewProps {
  entries: BatonHistoryEntry[];
}

export function BatonHistoryView({ entries }: BatonHistoryViewProps) {
  if (entries.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No baton history recorded yet
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {entries.map((entry, i) => (
        <HistoryEntry key={i} entry={entry} />
      ))}
    </div>
  );
}

function HistoryEntry({ entry }: { entry: BatonHistoryEntry }) {
  const [expanded, setExpanded] = useState(false);
  const patchKeys = Object.keys(entry.patch_applied || {});
  const ts = new Date(entry.timestamp).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div className="border-l-2 border-muted pl-3">
      <button
        className="flex items-center gap-2 w-full text-left text-sm"
        onClick={() => setExpanded((v) => !v)}
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3 flex-shrink-0" />
        ) : (
          <ChevronRight className="h-3 w-3 flex-shrink-0" />
        )}
        <Badge variant="secondary" className="text-[10px] px-1">
          {entry.stage_id}
        </Badge>
        <span className="text-xs text-muted-foreground font-mono">{ts}</span>
        {patchKeys.length > 0 && (
          <span className="text-xs text-muted-foreground">
            changed: {patchKeys.join(", ")}
          </span>
        )}
      </button>

      {expanded && (
        <div className="mt-2 ml-5 space-y-3">
          {/* Patch applied */}
          {patchKeys.length > 0 && (
            <div>
              <span className="text-xs font-medium text-muted-foreground">
                Patch Applied
              </span>
              <pre className="mt-1 text-xs bg-muted/50 rounded p-2 overflow-x-auto">
                {JSON.stringify(entry.patch_applied, null, 2)}
              </pre>
            </div>
          )}

          {/* Full baton snapshot */}
          <div>
            <span className="text-xs font-medium text-muted-foreground">
              Baton Snapshot
            </span>
            <div className="mt-1 border rounded p-2">
              <BatonStateView baton={entry.baton} />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
