import { Badge } from "@/components/ui/badge";
import {
  Target,
  FileText,
  HelpCircle,
  Shield,
  CheckSquare,
  FolderOpen,
} from "lucide-react";
import type { BatonState } from "@/types/api";

export interface BatonStateViewProps {
  baton: BatonState;
}

export function BatonStateView({ baton }: BatonStateViewProps) {
  return (
    <div className="space-y-4">
      {/* Goal */}
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Target className="h-4 w-4 text-blue-500" />
          <span className="text-sm font-medium">Goal</span>
        </div>
        <p className="text-sm text-foreground pl-6">{baton.goal}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Current State */}
        {baton.current_state.length > 0 && (
          <div>
            <span className="text-xs font-medium text-muted-foreground uppercase">
              Current State
            </span>
            <ul className="mt-1 space-y-0.5">
              {baton.current_state.map((item, i) => (
                <li key={i} className="text-sm flex items-start gap-1.5">
                  <span className="text-muted-foreground mt-0.5">-</span>
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Decision Log */}
        {baton.decision_log.length > 0 && (
          <div>
            <span className="text-xs font-medium text-muted-foreground uppercase">
              Decisions
            </span>
            <ol className="mt-1 space-y-0.5 list-decimal list-inside">
              {baton.decision_log.map((item, i) => (
                <li key={i} className="text-sm">
                  {item}
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Open Questions */}
        {baton.open_questions.length > 0 && (
          <div>
            <span className="text-xs font-medium text-yellow-600 uppercase flex items-center gap-1">
              <HelpCircle className="h-3 w-3" />
              Open Questions
            </span>
            <ul className="mt-1 space-y-0.5">
              {baton.open_questions.map((item, i) => (
                <li
                  key={i}
                  className="text-sm text-yellow-700 dark:text-yellow-400"
                >
                  - {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Constraints */}
        {baton.constraints.length > 0 && (
          <div>
            <span className="text-xs font-medium text-muted-foreground uppercase flex items-center gap-1">
              <Shield className="h-3 w-3" />
              Constraints
            </span>
            <div className="mt-1 flex flex-wrap gap-1">
              {baton.constraints.map((item, i) => (
                <Badge key={i} variant="outline" className="text-xs">
                  {item}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Artifacts */}
      {baton.artifacts.length > 0 && (
        <div>
          <span className="text-xs font-medium text-muted-foreground uppercase flex items-center gap-1">
            <FileText className="h-3 w-3" />
            Artifact Refs
          </span>
          <div className="mt-1 flex flex-wrap gap-2">
            {baton.artifacts.map((ref) => (
              <div
                key={ref.id}
                className="flex items-center gap-1.5 border rounded px-2 py-1 text-xs bg-muted/30"
              >
                <Badge variant="secondary" className="text-[10px] px-1">
                  {ref.type}
                </Badge>
                <span className="font-mono">{ref.id}</span>
                <span className="text-muted-foreground">
                  {ref.hash.slice(0, 12)}...
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Work Scope */}
        {baton.work_scope.length > 0 && (
          <div>
            <span className="text-xs font-medium text-muted-foreground uppercase flex items-center gap-1">
              <FolderOpen className="h-3 w-3" />
              Work Scope
            </span>
            <ul className="mt-1 space-y-0.5">
              {baton.work_scope.map((item, i) => (
                <li key={i} className="text-sm font-mono text-muted-foreground">
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Acceptance Criteria */}
        {baton.acceptance.length > 0 && (
          <div>
            <span className="text-xs font-medium text-muted-foreground uppercase flex items-center gap-1">
              <CheckSquare className="h-3 w-3" />
              Acceptance
            </span>
            <ul className="mt-1 space-y-0.5">
              {baton.acceptance.map((item, i) => (
                <li key={i} className="text-sm flex items-start gap-1.5">
                  <CheckSquare className="h-3 w-3 mt-0.5 text-muted-foreground flex-shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
