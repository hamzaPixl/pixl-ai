import * as React from "react";
import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Check, AlertTriangle, X, ChevronRight } from "lucide-react";
import type { Event } from "@/types/api";

type ContractResult = "passed" | "warning" | "violation";

interface ContractCheck {
  id: string;
  result: ContractResult;
  message: string;
  details: Record<string, unknown>;
  timestamp: string;
}

const RESULT_CONFIG: Record<
  ContractResult,
  { icon: typeof Check; className: string; label: string }
> = {
  passed: {
    icon: Check,
    className: "text-green-600 dark:text-green-400",
    label: "Passed",
  },
  warning: {
    icon: AlertTriangle,
    className: "text-amber-500 dark:text-amber-400",
    label: "Warning",
  },
  violation: {
    icon: X,
    className: "text-red-600 dark:text-red-400",
    label: "Violation",
  },
};

function mapEventToCheck(event: Event): ContractCheck | null {
  let result: ContractResult;
  if (event.type === "contract_passed") result = "passed";
  else if (event.type === "contract_warning") result = "warning";
  else if (event.type === "contract_violation") result = "violation";
  else return null;

  return {
    id: event.id,
    result,
    message:
      typeof event.data?.message === "string"
        ? event.data.message
        : typeof event.data?.rule === "string"
          ? event.data.rule
          : event.type.replace(/_/g, " "),
    details: event.data ?? {},
    timestamp: event.timestamp,
  };
}

function CheckRow({ check }: { check: ContractCheck }) {
  const [open, setOpen] = React.useState(false);
  const config = RESULT_CONFIG[check.result];
  const Icon = config.icon;

  return (
    <Collapsible open={open} onOpenChange={setOpen}>
      <CollapsibleTrigger className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm hover:bg-accent/50">
        <Icon className={cn("h-4 w-4 shrink-0", config.className)} />
        <span className="min-w-0 flex-1 truncate">{check.message}</span>
        <Badge variant="outline" className="shrink-0 text-[10px]">
          {config.label}
        </Badge>
        <ChevronRight
          className={cn(
            "h-3 w-3 shrink-0 text-muted-foreground transition-transform",
            open && "rotate-90"
          )}
        />
      </CollapsibleTrigger>
      <CollapsibleContent>
        <pre className="mt-1 ml-6 overflow-auto rounded bg-muted p-2 text-xs">
          {JSON.stringify(check.details, null, 2)}
        </pre>
      </CollapsibleContent>
    </Collapsible>
  );
}

export function ContractPanel({ events }: { events: Event[] }) {
  const checks = React.useMemo(
    () =>
      events
        .map(mapEventToCheck)
        .filter((c): c is ContractCheck => c !== null),
    [events]
  );

  if (checks.length === 0) {
    return (
      <Card>
        <CardContent className="py-6">
          <p className="text-center text-sm text-muted-foreground">
            No contract checks recorded
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-1" data-testid="contract-panel">
      {checks.map((check) => (
        <CheckRow key={check.id} check={check} />
      ))}
    </div>
  );
}
