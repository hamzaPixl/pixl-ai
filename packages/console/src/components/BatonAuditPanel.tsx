/**
 * Baton Audit Panel - Inspect baton context, history, and context budget.
 *
 * Three sections toggled via buttons:
 * A) Current Baton State
 * B) Baton History Timeline
 * C) Context Budget Audit
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import {
  ChevronDown,
  ChevronRight,
  Target,
  History,
  BarChart3,
} from "lucide-react";
import type {
  BatonState,
  BatonHistoryEntry,
  ContextAuditEntry,
} from "@/types/api";
import { BatonStateView } from "@/components/session/baton/BatonStateView";
import { BatonHistoryView } from "@/components/session/baton/BatonHistoryView";
import { ContextAuditView } from "@/components/session/baton/ContextAuditView";

type Section = "state" | "history" | "audit";

interface BatonAuditPanelProps {
  baton: BatonState;
  batonHistory: BatonHistoryEntry[];
  contextAudit: ContextAuditEntry[];
}

export function BatonAuditPanel({
  baton,
  batonHistory,
  contextAudit,
}: BatonAuditPanelProps) {
  const [activeSection, setActiveSection] = useState<Section>("state");
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="pt-4 border-t mt-4">
      <div className="flex items-center justify-between mb-3">
        <button
          className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground"
          onClick={() => setCollapsed((v) => !v)}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronDown className="h-4 w-4" />
          )}
          BATON CONTEXT
        </button>
        {!collapsed && (
          <div className="flex gap-1">
            <Button
              variant={activeSection === "state" ? "default" : "outline"}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setActiveSection("state")}
            >
              <Target className="h-3 w-3 mr-1" />
              State
            </Button>
            <Button
              variant={activeSection === "history" ? "default" : "outline"}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setActiveSection("history")}
            >
              <History className="h-3 w-3 mr-1" />
              History ({batonHistory.length})
            </Button>
            <Button
              variant={activeSection === "audit" ? "default" : "outline"}
              size="sm"
              className="h-7 text-xs"
              onClick={() => setActiveSection("audit")}
            >
              <BarChart3 className="h-3 w-3 mr-1" />
              Budget ({contextAudit.length})
            </Button>
          </div>
        )}
      </div>

      {!collapsed && (
        <>
          {activeSection === "state" && <BatonStateView baton={baton} />}
          {activeSection === "history" && (
            <BatonHistoryView entries={batonHistory} />
          )}
          {activeSection === "audit" && (
            <ContextAuditView entries={contextAudit} />
          )}
        </>
      )}
    </div>
  );
}
