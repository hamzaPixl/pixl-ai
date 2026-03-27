/**
 * Test results visualization: pass/fail counts, test names, confidence score bar.
 */

import { CheckCircle2, XCircle } from "lucide-react";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";

export interface TestResult {
  name: string;
  passed: boolean;
  duration?: number;
}

interface TestSummaryProps {
  tests: TestResult[];
  confidenceScore?: number;
}

export function TestSummary({ tests, confidenceScore }: TestSummaryProps) {
  const passed = tests.filter((t) => t.passed).length;
  const failed = tests.length - passed;
  const passRate = tests.length > 0 ? Math.round((passed / tests.length) * 100) : 0;

  return (
    <div className="space-y-3" data-testid="test-summary">
      {/* Counts row */}
      <div className="flex items-center gap-3">
        <Badge
          variant="secondary"
          className="gap-1 bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400"
        >
          <CheckCircle2 className="h-3 w-3" />
          {passed} passed
        </Badge>
        <Badge
          variant="secondary"
          className="gap-1 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
        >
          <XCircle className="h-3 w-3" />
          {failed} failed
        </Badge>
        {confidenceScore !== undefined && (
          <div className="ml-auto flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Confidence</span>
            <ConfidenceBadge score={confidenceScore} />
          </div>
        )}
      </div>

      {/* Pass rate bar */}
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Pass rate</span>
          <span>{passRate}%</span>
        </div>
        <Progress value={passRate} className="h-1.5" />
      </div>

      {/* Test list */}
      {tests.length > 0 && (
        <ul className="space-y-1 max-h-48 overflow-y-auto">
          {tests.map((test, i) => (
            <li
              key={i}
              className="flex items-center gap-2 rounded-md px-2 py-1 text-xs hover:bg-muted/50"
            >
              {test.passed ? (
                <CheckCircle2 className="h-3 w-3 shrink-0 text-emerald-500" />
              ) : (
                <XCircle className="h-3 w-3 shrink-0 text-red-500" />
              )}
              <span className="truncate flex-1">{test.name}</span>
              {test.duration !== undefined && (
                <span className="text-muted-foreground shrink-0">
                  {test.duration}ms
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
