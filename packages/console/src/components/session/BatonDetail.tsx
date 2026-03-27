import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, ChevronDown, ChevronRight } from "lucide-react";
import type { BatonHistoryEntry, ContextAuditEntry } from "@/types/api";

export function NodeBatonDetail({ entry }: { entry: BatonHistoryEntry }) {
  const [showRaw, setShowRaw] = useState(false);
  const patchKeys = Object.keys(entry.patch_applied || {});
  const b = entry.baton;

  return (
    <div className="rounded-md border bg-muted/20 p-3 text-xs space-y-3">
      {patchKeys.length > 0 && (
        <div className="flex items-center gap-1.5 flex-wrap">
          <span className="text-[10px] font-medium text-muted-foreground uppercase">
            Changed:
          </span>
          {patchKeys.map((key) => (
            <Badge
              key={key}
              variant="outline"
              className="text-[10px] px-1.5 h-4"
            >
              {key}
            </Badge>
          ))}
        </div>
      )}

      {b.goal && (
        <div>
          <span className="text-[10px] font-medium text-muted-foreground uppercase block mb-0.5">
            Goal
          </span>
          <p className="text-xs text-foreground">{b.goal}</p>
        </div>
      )}

      {b.current_state.length > 0 && (
        <div>
          <span className="text-[10px] font-medium text-muted-foreground uppercase block mb-0.5">
            Current State
          </span>
          <ul className="space-y-0.5">
            {b.current_state.map((item, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs">
                <span className="text-muted-foreground/60 mt-0.5">-</span>
                <span>{item}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {b.decision_log.length > 0 && (
        <div>
          <span className="text-[10px] font-medium text-muted-foreground uppercase block mb-0.5">
            Decisions
          </span>
          <ol className="space-y-0.5 list-decimal list-inside">
            {b.decision_log.map((item, i) => (
              <li key={i} className="text-xs">
                {item}
              </li>
            ))}
          </ol>
        </div>
      )}

      {b.open_questions.length > 0 && (
        <div>
          <span className="text-[10px] font-medium text-yellow-600 uppercase block mb-0.5">
            Open Questions
          </span>
          <ul className="space-y-0.5">
            {b.open_questions.map((item, i) => (
              <li
                key={i}
                className="text-xs text-yellow-700 dark:text-yellow-400"
              >
                - {item}
              </li>
            ))}
          </ul>
        </div>
      )}

      {b.constraints.length > 0 && (
        <div>
          <span className="text-[10px] font-medium text-muted-foreground uppercase block mb-0.5">
            Constraints
          </span>
          <div className="flex flex-wrap gap-1">
            {b.constraints.map((item, i) => (
              <Badge key={i} variant="outline" className="text-[10px] px-1.5">
                {item}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {b.artifacts.length > 0 && (
        <div>
          <span className="text-[10px] font-medium text-muted-foreground uppercase block mb-0.5">
            Artifact Refs
          </span>
          <div className="flex flex-wrap gap-1.5">
            {b.artifacts.map((ref) => (
              <span
                key={ref.id}
                className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-muted border text-[10px] font-mono"
              >
                <Badge variant="secondary" className="text-[9px] px-0.5 h-3">
                  {ref.type}
                </Badge>
                {ref.id}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-3">
        {b.work_scope.length > 0 && (
          <div>
            <span className="text-[10px] font-medium text-muted-foreground uppercase block mb-0.5">
              Work Scope
            </span>
            <ul className="space-y-0.5">
              {b.work_scope.map((item, i) => (
                <li
                  key={i}
                  className="text-[10px] font-mono text-muted-foreground"
                >
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
        {b.acceptance.length > 0 && (
          <div>
            <span className="text-[10px] font-medium text-muted-foreground uppercase block mb-0.5">
              Acceptance
            </span>
            <ul className="space-y-0.5">
              {b.acceptance.map((item, i) => (
                <li key={i} className="flex items-start gap-1 text-xs">
                  <CheckCircle2 className="h-3 w-3 mt-0.5 text-muted-foreground flex-shrink-0" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <button
        className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground pt-1 border-t"
        onClick={() => setShowRaw((v) => !v)}
      >
        {showRaw ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        Raw JSON
      </button>
      {showRaw && (
        <pre className="p-2 bg-muted rounded text-[10px] font-mono overflow-x-auto max-h-48 overflow-y-auto">
          {JSON.stringify(entry, null, 2)}
        </pre>
      )}
    </div>
  );
}

export function NodeContextSlices({
  slices,
}: {
  slices: ContextAuditEntry["slices"];
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="px-3 pb-2">
      <button
        className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
      >
        {open ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        View slices
      </button>
      {open && (
        <div className="mt-1 space-y-0.5">
          {slices.map((slice, i) => (
            <div
              key={i}
              className="flex items-center gap-2 text-[10px] text-muted-foreground"
            >
              <span className="font-mono truncate max-w-[160px]">
                {slice.artifact_id}
              </span>
              <Badge variant="outline" className="text-[9px] px-1 h-3.5">
                {slice.layer}
              </Badge>
              <span className="truncate flex-1">{slice.reason}</span>
              <span className="font-mono tabular-nums flex-shrink-0">
                {slice.token_estimate.toLocaleString()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
