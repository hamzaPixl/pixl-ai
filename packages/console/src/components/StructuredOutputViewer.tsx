/**
 * Structured Output Viewer - Inspect parsed structured output from a stage.
 *
 * Displays:
 * - Status badge
 * - Summary bullets
 * - Artifacts table
 * - Included sources
 * - Payload JSON tree (collapsible)
 *
 * Follows the BatonAuditPanel collapsible panel pattern.
 */

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  FileText,
  Code,
  ArrowRight,
} from "lucide-react";
import type { StageOutputPayload } from "@/types/api";

interface StructuredOutputViewerProps {
  nodeId: string;
  output: StageOutputPayload;
}

export function StructuredOutputViewer({ nodeId, output }: StructuredOutputViewerProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [payloadExpanded, setPayloadExpanded] = useState(false);

  return (
    <div className="pt-4 border-t mt-4">
      <button
        className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground w-full"
        onClick={() => setCollapsed((v) => !v)}
      >
        {collapsed ? (
          <ChevronRight className="h-4 w-4" />
        ) : (
          <ChevronDown className="h-4 w-4" />
        )}
        <Code className="h-4 w-4" />
        STRUCTURED OUTPUT
        <Badge
          variant={output.status === "ok" ? "default" : "destructive"}
          className="ml-2 text-[10px] px-1.5 py-0"
        >
          {output.status}
        </Badge>
        <span className="text-xs text-muted-foreground ml-auto">
          {nodeId} · v{output.schema_version}
        </span>
      </button>

      {!collapsed && (
        <div className="mt-3 space-y-4">
          {/* Summary */}
          {output.summary.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-1">Summary</h4>
              <ul className="space-y-0.5">
                {output.summary.map((bullet, i) => (
                  <li key={i} className="text-sm flex items-start gap-2">
                    <CheckCircle2 className="h-3 w-3 mt-1 text-green-500 shrink-0" />
                    {bullet}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Error */}
          {output.error && (
            <div className="bg-destructive/10 rounded p-3">
              <div className="flex items-center gap-2 text-sm font-medium text-destructive">
                <XCircle className="h-4 w-4" />
                {output.error.code}: {output.error.message}
              </div>
              {output.error.recoverable && (
                <Badge variant="outline" className="mt-1 text-[10px]">Recoverable</Badge>
              )}
            </div>
          )}

          {/* Artifacts Written */}
          {output.artifacts_written.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-1">
                Artifacts Written ({output.artifacts_written.length})
              </h4>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="text-xs">Path</TableHead>
                    <TableHead className="text-xs">Purpose</TableHead>
                    <TableHead className="text-xs w-32">SHA256</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {output.artifacts_written.map((art, i) => (
                    <TableRow key={i}>
                      <TableCell className="text-xs font-mono">
                        <FileText className="h-3 w-3 inline mr-1" />
                        {art.path}
                      </TableCell>
                      <TableCell className="text-xs">{art.purpose}</TableCell>
                      <TableCell className="text-xs font-mono text-muted-foreground">
                        {art.sha256.slice(0, 12)}...
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {/* Included Sources */}
          {output.included_sources.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-muted-foreground mb-1">
                Included Sources ({output.included_sources.length})
              </h4>
              <div className="space-y-1">
                {output.included_sources.map((src, i) => (
                  <div key={i} className="text-xs flex items-center gap-2 text-muted-foreground">
                    <ArrowRight className="h-3 w-3" />
                    <span className="font-mono">{src.artifact_id}</span>
                    <span>— {src.reason}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Next Recommendation */}
          {output.next && (
            <div className="text-xs text-muted-foreground">
              <span className="font-medium">Next:</span>{" "}
              {output.next.recommended_stage}
              {output.next.inputs_needed.length > 0 && (
                <span> (needs: {output.next.inputs_needed.join(", ")})</span>
              )}
            </div>
          )}

          {/* Payload (collapsible JSON tree) */}
          {Object.keys(output.payload).length > 0 && (
            <div>
              <button
                className="flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-foreground"
                onClick={() => setPayloadExpanded((v) => !v)}
              >
                {payloadExpanded ? (
                  <ChevronDown className="h-3 w-3" />
                ) : (
                  <ChevronRight className="h-3 w-3" />
                )}
                Payload ({Object.keys(output.payload).length} keys)
              </button>
              {payloadExpanded && (
                <pre className="mt-1 p-2 bg-muted rounded text-xs font-mono overflow-x-auto max-h-64 overflow-y-auto">
                  {JSON.stringify(output.payload, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
