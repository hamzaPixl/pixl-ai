import { Link } from "@tanstack/react-router";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { statusColors } from "./chain-status-colors";
import type {
  ExecutionChainSummary,
  ChainSignal,
  ChainSignalListResponse,
} from "@/types/api";

export interface ChainDetailSheetProps {
  projectId: string;
  chain: ExecutionChainSummary | undefined;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  signals: ChainSignalListResponse | undefined;
  quality: { scores: Record<string, number> } | undefined;
}

export function ChainDetailSheet({
  projectId,
  chain,
  open,
  onOpenChange,
  signals,
  quality,
}: ChainDetailSheetProps) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full sm:w-[500px] md:w-[600px] overflow-y-auto">
        {chain && (
          <>
            <SheetHeader>
              <SheetTitle>Chain: {chain.chain_id}</SheetTitle>
            </SheetHeader>
            <div className="mt-4 space-y-4">
              <div className="grid grid-cols-2 gap-2 text-sm">
                <div>
                  <span className="text-muted-foreground">Epic:</span>{" "}
                  {chain.epic_title ?? chain.epic_id}
                </div>
                <div>
                  <span className="text-muted-foreground">Status:</span>{" "}
                  <Badge className={statusColors[chain.status] ?? ""}>
                    {chain.status.replace(/_/g, " ")}
                  </Badge>
                </div>
                <div>
                  <span className="text-muted-foreground">Progress:</span>{" "}
                  {chain.completed_nodes}/{chain.total_nodes} nodes (
                  {chain.progress_pct.toFixed(0)}%)
                </div>
                <div>
                  <span className="text-muted-foreground">Wave:</span>{" "}
                  {chain.current_wave}/{chain.total_waves}
                </div>
              </div>

              {/* Wave breakdown */}
              {chain.waves && chain.waves.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Waves</h4>
                  <div className="space-y-2">
                    {chain.waves.map((wave) => (
                      <Card key={wave.wave}>
                        <CardContent className="py-3 px-4">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant="outline" className="text-xs">
                              Wave {wave.wave}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {wave.nodes.length} node
                              {wave.nodes.length !== 1 ? "s" : ""}
                            </span>
                          </div>
                          <div className="space-y-1">
                            {wave.nodes.map((node) => (
                              <div
                                key={node.node_id}
                                className="flex items-center gap-2 text-xs"
                              >
                                <Badge
                                  variant="outline"
                                  className={`text-[10px] ${
                                    node.status === "completed"
                                      ? "bg-green-50 dark:bg-green-900/20"
                                      : node.status === "failed"
                                        ? "bg-red-50 dark:bg-red-900/20"
                                        : node.status === "running"
                                          ? "bg-yellow-50 dark:bg-yellow-900/20"
                                          : ""
                                  }`}
                                >
                                  {node.status ?? "pending"}
                                </Badge>
                                <span className="font-mono">
                                  {node.feature_ref}
                                </span>
                                {node.session_id && (
                                  <Link
                                    to="/project/$projectId/sessions/$sessionId"
                                    params={{
                                      projectId,
                                      sessionId: node.session_id,
                                    }}
                                    className="text-primary underline"
                                  >
                                    {node.session_id}
                                  </Link>
                                )}
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}

              {/* Quality scores */}
              {quality?.scores && Object.keys(quality.scores).length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">Quality Scores</h4>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(quality.scores).map(([metric, value]) => (
                      <div
                        key={metric}
                        className="flex items-center justify-between text-xs border rounded-md px-3 py-2"
                      >
                        <span className="text-muted-foreground">{metric}</span>
                        <span className="font-medium">
                          {(value as number).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Signals feed */}
              {signals?.signals && signals.signals.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">
                    Signals ({signals.signals.length})
                  </h4>
                  <div className="space-y-1 max-h-64 overflow-y-auto">
                    {signals.signals.map((sig: ChainSignal) => (
                      <div
                        key={sig.id}
                        className="flex items-center gap-2 text-xs border-l-2 border-muted pl-3 py-1"
                      >
                        <Badge variant="outline" className="text-[10px]">
                          {sig.signal_type}
                        </Badge>
                        <span className="text-muted-foreground">
                          from {sig.from_node}
                        </span>
                        <span className="text-muted-foreground">
                          {new Date(sig.created_at).toLocaleTimeString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  );
}
